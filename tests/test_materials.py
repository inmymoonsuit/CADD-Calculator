"""The materials table: its values as the sources state them, and its bands (ADR-0014 §3).

Spot checks use isolated values from the materials data brief, each read from its source.
"""

from __future__ import annotations

from fractions import Fraction
from functools import cache
from importlib import resources
from itertools import pairwise

import pytest

from caddcalc.calculators import REFERENCE_TABLES
from caddcalc.calculators.sheet_metal import DOMAIN, BendAllowance
from caddcalc.calculators.sheet_metal.gauges import GAUGE_TABLE, load_gauges
from caddcalc.calculators.sheet_metal.materials import (
    LISTED_TOLERANCE,
    MATERIAL_TABLE,
    Materials,
    RadiusSource,
    listed_bands,
    load_materials,
)
from caddcalc.core import (
    Basis,
    ClearedChoice,
    DomainSettings,
    SpecError,
    TrustLevel,
    parse_table,
)
from caddcalc.core.units import get_unit

IN = 25.4
"""Millimetres per inch."""
INCH = get_unit("in")
MATERIAL_KEYS = ("al:5052", "al:6061", "cs:a1008", "cs:a653", "cs:a1011", "ss:304")


@cache
def materials() -> Materials:
    return load_materials(MATERIAL_TABLE.load())


def table_text() -> str:
    """The shipped table's TOML text."""
    files = resources.files(MATERIAL_TABLE.package)
    return files.joinpath(MATERIAL_TABLE.filename).read_text(encoding="utf-8")


def edited(old: str, new: str) -> Materials:
    """Load the table with one edit, which must apply exactly once."""
    text = table_text()
    assert text.count(old) == 1, old
    spec = MATERIAL_TABLE
    edit = parse_table(text.replace(old, new), "test", spec.content_keys, spec.quantities)
    return load_materials(edit)


def source(material: str, temper: str, source_id: str) -> RadiusSource:
    return next(r for r in materials().radius_sources(material, temper) if r.source.id == source_id)


def test_the_table_ships_and_offers_the_starter_set() -> None:
    assert MATERIAL_TABLE in REFERENCE_TABLES
    assert tuple(m.key for m in materials().materials) == MATERIAL_KEYS
    assert materials().by_key["ss:304"].label == "304, annealed (2B finish)"
    tempers = {m.key: [t.key for t in m.tempers] for m in materials().materials}
    assert tempers == {
        "al:5052": ["temper:5052_h32"],
        "al:6061": ["temper:6061_t6"],
        "cs:a1008": ["temper:a1008_as_supplied"],
        "cs:a653": ["temper:a653_as_supplied"],
        "cs:a1011": ["temper:a1011_as_supplied"],
        "ss:304": ["temper:304_annealed"],
    }


@pytest.mark.parametrize(
    ("material", "temper", "source_id", "thickness_in", "stated"),
    [
        ("al:5052", "temper:5052_h32", "ac_radii_aluminum", 0.064, "½T–1T"),
        ("al:5052", "temper:5052_h32", "ac_radii_aluminum", 0.032, "0, a sharp bend"),
        ("al:5052", "temper:5052_h32", "ac_radii_aluminum", 0.258, "½T–1½T"),
        ("al:6061", "temper:6061_t6", "ac_radii_aluminum", 0.064, "1T–2T"),
        ("al:6061", "temper:6061_t6", "ac_radii_aluminum", 0.016, "0–1T"),
        ("al:6061", "temper:6061_t6", "to_standard_radii_aluminum", 0.063, "0.16 in"),
        ("al:6061", "temper:6061_t6", "to_standard_radii_aluminum", 0.190, "0.69 in"),
        ("cs:a1008", "temper:a1008_as_supplied", "to_radii_carbon_steel", 0.016, "2T"),
        ("cs:a1008", "temper:a1008_as_supplied", "to_radii_carbon_steel", 0.187, "2T"),
        ("ss:304", "temper:304_annealed", "to_radii_stainless", 0.051, "2T"),
    ],
)
def test_minimum_radii_read_as_their_sources_state_them(
    material: str, temper: str, source_id: str, thickness_in: float, stated: str
) -> None:
    value = source(material, temper, source_id).at(thickness_in * IN)
    assert value is not None
    assert value.stated == stated


def test_a_range_is_held_to_its_upper_bound_and_a_radius_is_absolute() -> None:
    """The maintainer's decision D2: warn below the upper bound."""
    ac = source("al:6061", "temper:6061_t6", "ac_radii_aluminum").at(0.064 * IN)
    to = source("al:6061", "temper:6061_t6", "to_standard_radii_aluminum").at(0.063 * IN)
    assert ac is not None and to is not None
    assert ac.minimum(0.064 * IN) == pytest.approx(2 * 0.064 * IN)
    assert to.minimum(0.063 * IN) == pytest.approx(0.16 * IN)


def test_listed_thicknesses_read_within_two_percent_else_at_the_next_listing_up() -> None:
    """The maintainer's decision D4, in its one place."""
    listed = [Fraction("0.032"), Fraction("0.064"), Fraction("0.128")]
    bands = listed_bands(listed, INCH)

    def column(thickness_in: float) -> int | None:
        return next((i for i, b in enumerate(bands) if b.contains(thickness_in * IN)), None)

    assert Fraction(2, 100) == LISTED_TOLERANCE
    assert column(0.063) == 1, "0.063 in reads at the listed 0.064 in"
    assert column(0.064 * 1.02) == 1 and column(0.0654) == 2
    assert column(0.050) == 1, "between listings, the next one up"
    assert column(0.032 * 0.98) == 0 and column(0.031) is None, "below the first: none"
    assert column(0.128 * 1.02) == 2 and column(0.131) is None, "above the last: none"
    assert all(not a.overlaps(b) for a, b in pairwise(bands))
    with pytest.raises(SpecError, match="within 2% of each other"):
        listed_bands([Fraction("0.063"), Fraction("0.064")], INCH)
    with pytest.raises(SpecError, match="within 2% of each other"):
        listed_bands([Fraction("0.064"), Fraction("0.032")], INCH)


def test_304s_bands_follow_the_maintainers_reading_of_table_2_16() -> None:
    """0.012–0.051 in inclusive, then over 0.051 to 0.090 in; the gap has no value."""
    to = source("ss:304", "temper:304_annealed", "to_radii_stainless")
    assert [v.column for v in to.values] == [
        "0.012–0.051 in",
        "over 0.051 to 0.090 in",
        "0.190–0.250 in",
    ]
    assert to.at(0.051 * IN) is to.values[0]
    assert to.at(0.0511 * IN) is to.values[1]
    assert to.at(0.100 * IN) is None and to.at(0.189 * IN) is None
    assert to.coverage == "0.012–0.090 in and 0.190–0.250 in"
    assert "½ Hard" in to.label and to.see_also[0].id == "to_2015_annealed_stainless"


def test_6061_has_a_thickness_each_source_alone_covers() -> None:
    """Where only one source covers a thickness, the other has no value there (flag 5)."""
    ac = source("al:6061", "temper:6061_t6", "ac_radii_aluminum")
    to = source("al:6061", "temper:6061_t6", "to_standard_radii_aluminum")
    assert ac.at(0.012 * IN) is None and to.at(0.012 * IN) is not None
    assert to.at(0.256 * IN) is None and ac.at(0.256 * IN) is not None


def test_strengths_carry_their_basis() -> None:
    def ksi(material: str, temper: str) -> tuple[Basis, list[str]]:
        (strength,) = materials().strengths_of(material, temper)
        texts = [v.text for v in (*strength.ultimate, *strength.tensile_yield)]
        return strength.basis, texts

    assert ksi("al:5052", "temper:5052_h32") == (
        Basis.SPEC_MINIMUM,
        ["31 ksi", "31 ksi", "23 ksi", "22 ksi"],
    )
    assert ksi("al:6061", "temper:6061_t6") == (
        Basis.A_BASIS,
        ["42 ksi", "42 ksi", "36 ksi", "35 ksi"],
    )
    assert ksi("cs:a1008", "temper:a1008_as_supplied") == (
        Basis.SPEC_MINIMUM,
        ["55 ksi", "55 ksi", "36 ksi", "36 ksi"],
    )
    assert ksi("ss:304", "temper:304_annealed") == (
        Basis.SPEC_MINIMUM,
        ["73 ksi", "75 ksi", "26 ksi", "30 ksi"],
    )
    (steel,) = materials().strengths_of("cs:a1008", "temper:a1008_as_supplied")
    assert steel.band is None and "stand-in" in steel.note


def test_k_starting_values_are_rules_of_thumb_offered_per_material() -> None:
    by_value = {k.value.text: k for k in materials().k_starts}
    assert by_value["0.445"].source.id == "faa_neutral_axis"
    assert by_value["0.4"].source.id == "edd5_k"
    assert [k.value.text for k in materials().k_starts_for("al:6061")] == ["0.445", "0.4"]
    assert [k.value.text for k in materials().k_starts_for("ss:304")] == ["0.4"]
    assert materials().k_starts_for("cs:a653") == ()
    k_values = [v for v in materials().values if v.quantity == "k_start"]
    assert len(k_values) == 2
    assert {(v.basis, v.trust) for v in k_values} == {
        (Basis.RULE_OF_THUMB, TrustLevel.RULE_OF_THUMB)
    }


def test_edd5_defines_only_its_one_cite_only_value() -> None:
    edd = [v for v in materials().values if v.source == "edd5_k"]
    assert [v.value for v in edd] == [0.4]


def test_materials_without_a_source_say_why() -> None:
    for key in ("cs:a653", "cs:a1011"):
        material = materials().by_key[key]
        (temper,) = material.tempers
        assert materials().radius_sources(key, temper.key) == ()
        assert "No public-domain source" in material.radius_note
    assert "zinc coating" in materials().by_key["cs:a653"].radius_note


def test_every_materials_gauge_systems_are_in_the_gauge_table() -> None:
    systems = {s.id for s in load_gauges(GAUGE_TABLE.load()).systems}
    for material in materials().materials:
        assert material.gauges <= systems, material.key


@pytest.mark.parametrize(
    ("old", "new", "message"),
    [
        ('radius = [\n  "0.03", "0.03"', 'radius = [\n  "0.06", "0.03"', "below the one before it"),
        ('["1/2", "3/2"], ["1", "2"]', '["1/2", "3/2"], ["1/2", "1"]', "below the one before it"),
        ('["3/2", "3"], ["2", "4"]', '["3", "3/2"], ["2", "4"]', "lower bound is above"),
        (
            'angle = "not_stated"\nunit = "in"\nthicknesses',
            'angle = "45"\nunit = "in"\nthicknesses',
            "angle",
        ),
        ('times_t = [["2"], ["2"], ["2"]]', 'times_t = [["2"], ["2"]]', "2 values for 3"),
        (
            'temper = "temper:a1008_as_supplied"\nsource = "to_radii',
            'temper = "temper:6061_t6"\nsource = "to_radii',
            "has tempers",
        ),
        ('basis = "a_basis"', 'basis = "typical"', "specification minimum or A-basis"),
        (
            'radius_note = "No public-domain source gives a minimum bend radius for galvanized',
            'label_note = "No',
            "unknown keys",
        ),
    ],
)
def test_the_loader_refuses_malformed_rows(old: str, new: str, message: str) -> None:
    with pytest.raises(SpecError, match=message):
        edited(old, new)


# --- The material and temper choices (2b.5) -----------------------------------------------


def test_the_domain_offers_material_then_its_temper() -> None:
    assert [c.key for c in DOMAIN.ordered_choices()] == ["gauge", "material", "temper"]
    options = DOMAIN.options("material")
    assert [o.key for o in options] == list(MATERIAL_KEYS)
    assert list(dict.fromkeys(o.group for o in options)) == [
        "Aluminum",
        "Carbon steel",
        "Stainless steel",
    ]
    assert DOMAIN.options("temper") == ()
    (t6,) = DOMAIN.options("temper", {"material": "al:6061"})
    assert (t6.key, t6.label, t6.default) == ("temper:6061_t6", "T6", True)
    (supplied,) = DOMAIN.options("temper", {"material": "cs:a1008"})
    assert (supplied.key, supplied.label) == ("temper:a1008_as_supplied", "As supplied")


def test_a_material_selects_its_only_temper_and_follows_a_change() -> None:
    fresh = DomainSettings()
    assert fresh.choice(DOMAIN, "material") is None and fresh.choice(DOMAIN, "temper") is None
    aluminum = fresh.set_choice(DOMAIN, "material", "al:6061")
    assert aluminum.choice(DOMAIN, "temper") == "temper:6061_t6"
    stainless = aluminum.set_choice(DOMAIN, "material", "ss:304")
    assert stainless.choice(DOMAIN, "temper") == "temper:304_annealed"
    assert stainless.cleared_choices(DOMAIN, aluminum) == ()
    chosen = aluminum.set_choice(DOMAIN, "temper", "temper:6061_t6")
    steel = chosen.set_choice(DOMAIN, "material", "cs:a1008")
    assert steel.choice(DOMAIN, "temper") == "temper:a1008_as_supplied"
    assert steel.cleared_choices(DOMAIN, chosen) == (ClearedChoice("temper", "default"),)


def test_each_temper_is_keyed_by_its_material() -> None:
    """Review L1: a material change can never carry a temper across silently."""
    keys = [t.key for m in materials().materials for t in m.tempers]
    assert len(set(keys)) == len(keys)
    with pytest.raises(SpecError, match="belongs to 'al:5052' and 'al:6061'"):
        edited('key = "temper:6061_t6"', 'key = "temper:5052_h32"')


def test_every_condition_naming_a_choice_is_an_option_the_domain_offers() -> None:
    """Review M3: catches a typo such as "al:6O61" in any shipped table."""
    choices = {c.key: c for c in DOMAIN.choices}
    checked = 0
    for spec in REFERENCE_TABLES:
        for value in spec.values(spec.load()):
            for key, option in value.conditions.items():
                if key in choices:
                    parents = {p: value.conditions[p] for p in choices[key].depends_on}
                    assert option in {o.key for o in DOMAIN.options(key, parents)}, value
                    checked += 1
    assert checked > 200, "the gauge thicknesses and the materials' values"


def test_a_material_sets_no_value() -> None:
    """ADR-0014 M2: the material informs checks; the user's values stay in charge."""
    settings = DomainSettings().set_choice(DOMAIN, "material", "al:6061")
    values = settings.for_domain(DOMAIN)
    assert dict(values.derived) == {}
    assert dict(values.selections) == {"material": "al:6061", "temper": "temper:6061_t6"}
    plain = BendAllowance().run(method="k_factor")
    chosen = BendAllowance().run(method="k_factor", settings=values)
    assert chosen.inputs == plain.inputs and chosen.outputs == plain.outputs
    gauged = settings.set_choice(DOMAIN, "gauge", "awg:16").for_domain(DOMAIN)
    assert set(gauged.derived) == {"thickness"}


def test_a_material_without_rows_must_say_why() -> None:
    lines = table_text().splitlines(keepends=True)
    note = next(line for line in lines if line.startswith("radius_note") and "hot-rolled" in line)
    with pytest.raises(SpecError, match="radius_note"):
        edited(note, "")
