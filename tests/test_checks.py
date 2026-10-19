"""The bend check: inside radius against the material's cited minimum (ADR-0014 §3).

The cases follow the maintainer's decisions D1–D4 and D10 and the 2b plan's flags, with
thicknesses and radii in inches.
"""

from __future__ import annotations

import pytest

from caddcalc.calculators.sheet_metal import (
    DOMAIN,
    BendAllowance,
    FormedSegmentFlatLength,
    TruncatedConeLayout,
    VDieOpening,
    checks,
)
from caddcalc.calculators.sheet_metal.materials import MATERIAL_TABLE, load_materials
from caddcalc.core import (
    DomainSettings,
    InputSource,
    Note,
    NoteKind,
    Result,
    SourceKind,
    ValueOrigin,
)
from caddcalc.core.formatting import DisplayPrefs, describe_note, value_parts

IN = 25.4
PRACTICE = "Form across the grain where possible"
LIMIT, GAP, WARNING = NoteKind.LIMIT_EXCEEDED, NoteKind.NO_APPLICABLE_VALUE, NoteKind.WARNING


def bend(
    thickness: float | None,
    radius: float,
    material: str | None = None,
    *,
    angle: float = 90.0,
    gauge: str | None = None,
) -> Result:
    """Run the bend allowance with the family's material and gauge, if any.

    A thickness of ``None`` takes the family's: the gauge's, when one is chosen.
    """
    settings = DomainSettings()
    if material is not None:
        settings = settings.set_choice(DOMAIN, "material", material)
    if gauge is not None:
        settings = settings.set_choice(DOMAIN, "gauge", gauge)
    inputs = {"inside_radius": radius * IN, "bend_angle": angle}
    if thickness is not None:
        inputs["thickness"] = thickness * IN
    return BendAllowance().run(inputs, "k_factor", settings=settings.for_domain(DOMAIN))


def kinds(result: Result) -> list[NoteKind]:
    return [n.kind for n in result.notes]


def notes(result: Result, kind: NoteKind) -> list[Note]:
    return [n for n in result.notes if n.kind is kind]


def said(note: Note, prefs: DisplayPrefs | None = None) -> str:
    """The note as users read it: heading and lead, detail, and sources, one per line."""
    return "\n".join(describe_note(note, prefs or DisplayPrefs()).lines)


def lead(note: Note, prefs: DisplayPrefs | None = None) -> str:
    return describe_note(note, prefs or DisplayPrefs()).lead


def detail(note: Note) -> str:
    return describe_note(note, DisplayPrefs()).detail


def rule_of_thumb(result: Result) -> bool:
    return any(n.text == checks.RULE_OF_THUMB for n in result.notes)


def test_only_the_bend_calculators_check_the_radius() -> None:
    """V-die opening and the cone take no check (flag 4)."""
    assert BendAllowance.checks and FormedSegmentFlatLength.checks
    assert VDieOpening.checks == () and TruncatedConeLayout.checks == ()


def test_without_a_material_the_rule_of_thumb_speaks_as_before() -> None:
    tight = bend(0.25, 0.1)
    assert [(n.kind, n.subjects) for n in tight.notes] == [
        (WARNING, ("inside_radius", "thickness"))
    ]
    assert rule_of_thumb(tight)
    (note,) = tight.notes
    assert said(note) == (
        "Inside radius 0.1000 in is less than the thickness 0.2500 in. This is a rule of "
        "thumb, not a cited limit.\n"
        "Check the material's minimum bend radius; tight bends can crack, especially in hard "
        "tempers."
    )
    assert bend(0.25, 0.3).notes == ()


@pytest.mark.parametrize(
    ("thickness", "radius", "exceeded"),
    [
        (0.063, 0.15, True),  # TO's 0.16 in governs AC's 2T, 0.126 in (D1)
        (0.063, 0.16, False),  # a radius equal to the minimum passes
        (0.182, 0.70, True),  # AC's 4T, 0.728 in, governs TO's 0.69 in (D1)
        (0.182, 0.73, False),
    ],
)
def test_6061_is_held_to_the_larger_source_at_each_thickness(
    thickness: float, radius: float, exceeded: bool
) -> None:
    result = bend(thickness, radius, "al:6061")
    limits = notes(result, LIMIT)
    assert bool(limits) == exceeded
    assert not rule_of_thumb(result), "a referenced check replaces the rule of thumb"
    practice = any(said(n).startswith(PRACTICE) for n in notes(result, WARNING))
    assert practice == exceeded, "bending practice only beside a limit"
    if exceeded:
        (limit,) = limits
        assert [r.short_title for r in limit.references] == [
            "AC 43.13-1B (2024 ed. update)",
            "TO 1-1A-9 (2020 Change 3)",
        ]
        minimum = "0.1600 in" if thickness == 0.063 else "0.7280 in"
        assert lead(limit) == (
            f"inside radius {radius:.4f} in is below {minimum}, the recommended minimum this "
            f"check uses, for 6061-T6 aluminum at {thickness:.4f} in, in aerospace bending "
            "practice."
        ), "the verdict and its numbers first, with its scope (ADR-0017 F1)"
        shown = said(limit)
        assert shown.startswith("Limit exceeded: inside radius ")
        assert shown.count("AC 43.13-1B (2024 ed. update), Table 4-6, p. 4-17: ") == 1, "once"
        assert detail(limit).count("TO 1-1A-9 (2020 Change 3) gives") == 1
        assert "p. 4-14" not in shown, "a reviewer's remark is never rendered"
        assert "Engineering Series for Aircraft Repair" not in shown, "short"
        assert "Engineering Series for Aircraft Repair" in limit.references[1].title, "in full"
        assert len(shown) < 800, "short references keep it short (ADR-0014, phase 2b.7d)"
        assert "The larger minimum governs" in detail(limit)
        assert limit.subjects == ("inside_radius", "thickness")
        assert "aircraft repair practice" in shown, "each source's scope"


def test_a_range_is_checked_at_its_upper_bound_and_shown_whole() -> None:
    """5052-H32 at 0.064 in is ½T–1T: below 1T exceeds (D2)."""
    (limit,) = notes(bend(0.064, 0.05, "al:5052"), LIMIT)
    assert "½T–1T" in detail(limit) and "upper bound" in detail(limit)
    assert notes(bend(0.064, 0.064, "al:5052"), LIMIT) == []


def test_a_zero_minimum_allows_a_sharp_bend() -> None:
    result = bend(0.032, 0.0, "al:5052")
    assert notes(result, LIMIT) == [] and not rule_of_thumb(result)


def test_304_uses_the_half_hard_row_as_a_labelled_stand_in() -> None:
    """D3: 2T, from TO's only 304 row, with the generic annealed figure in the note."""
    (limit,) = notes(bend(0.05, 0.09, "ss:304"), LIMIT)
    assert "½ Hard" in detail(limit) and "about 1T" in detail(limit)
    assert (
        "TO 1-1A-9 (2020 Change 3) gives 2T for sheet 0.012–0.051 in, from TO's only "
        "304 row, for ½ Hard; a conservative stand-in for annealed 2B sheet."
    ) in detail(limit), "where the value applies, as the source states it"
    assert "Change 14" in limit.references[-1].edition, "the 2015 edition's row is cited"


@pytest.mark.parametrize(
    ("material", "thickness", "listed"),
    [
        ("ss:304", 0.10, "0.012–0.090 in and 0.190–0.250 in"),  # Table 2-16's gap
        ("cs:a1008", 0.25, "0.016–0.187 in"),  # mild steel stops at 0.187 in (D4)
        ("al:6061", 0.30, "0.016–0.258 in. TO 1-1A-9 (2020 Change 3) lists 0.012–0.250 in."),
    ],
)
def test_a_thickness_no_source_lists_is_said_aloud(
    material: str, thickness: float, listed: str
) -> None:
    result = bend(thickness, 0.01, material)
    (gap,) = notes(result, GAP)
    assert "is outside every minimum-radius source" in lead(gap) and listed in detail(gap)
    assert gap.subjects == ("thickness",)
    assert notes(result, LIMIT) == []
    assert rule_of_thumb(result), "no referenced check applies, so the rule of thumb does"


def test_where_one_source_covers_the_thickness_it_is_used_alone() -> None:
    """Flag 5: AC lists nothing as thin as 0.012 in, so TO checks it alone."""
    result = bend(0.012, 0.02, "al:6061")
    assert notes(result, GAP) == [], "the check applied, through TO"
    (gap,) = [n for n in notes(result, WARNING) if n.text == checks.PARTIAL]
    assert said(gap) == (
        "Checked against TO 1-1A-9 (2020 Change 3) only: AC 43.13-1B (2024 ed. update) lists "
        "6061-T6 aluminum for 0.016–0.258 in, and 0.0120 in is outside that."
    )
    (limit,) = notes(result, LIMIT)
    assert "0.03 in" in detail(limit) and "larger" not in detail(limit)


def test_a_bend_past_90_degrees_has_no_applicable_value() -> None:
    """D10: up to 90° takes the 90° value; past it, and hems, nothing applies."""
    result = bend(0.063, 0.05, "al:6061", angle=120)
    (gap,) = notes(result, GAP)
    assert lead(gap) == (
        "bend angle A = 120.00° is past 90°, and the minimum radii for 6061-T6 aluminum are "
        "for bends up to 90°."
    )
    assert detail(gap) == "No source covers larger bends or hems."
    assert gap.subjects == ("bend_angle",)
    assert notes(result, LIMIT) == [] and rule_of_thumb(result)
    assert notes(bend(0.063, 0.05, "al:6061", angle=45), LIMIT), "under 90° takes the 90° value"

    settings = DomainSettings().set_choice(DOMAIN, "material", "al:6061").for_domain(DOMAIN)
    segment = FormedSegmentFlatLength().run(
        {"thickness": 0.063 * IN, "inside_radius": 0.2 * IN, "bend_angle_2": 135.0},
        "k_factor",
        settings=settings,
    )
    (gap,) = notes(segment, GAP)
    assert "A2 = 135.00° is past 90°" in lead(gap) and gap.subjects == ("bend_angle_2",)


@pytest.mark.parametrize(
    ("material", "says"),
    [
        ("cs:a653", "zinc coating can flake or crack"),
        ("cs:a1011", "hot-rolled pickled and oiled"),
    ],
)
def test_a_material_without_a_source_says_so(material: str, says: str) -> None:
    result = bend(0.06, 0.03, material)
    (gap,) = notes(result, GAP)
    assert lead(gap).startswith("no minimum radius to check for ")
    assert says in detail(gap) and "No public-domain source" in detail(gap), "the data's own"
    assert rule_of_thumb(result)


@pytest.mark.parametrize(
    ("material", "gauge", "warned"),
    [
        ("al:6061", "msg:16", True),
        ("ss:304", "msg:16", True),
        ("cs:a1008", "galv:16", True),
        ("cs:a653", "msg:16", True),
        ("cs:a1008", "awg:16", True),
        ("al:6061", "awg:16", False),
        ("cs:a1008", "msg:16", False),
        ("cs:a653", "galv:16", False),
        ("ss:304", "uss:16", False),
    ],
)
def test_a_gauge_from_another_materials_system_is_warned_about(
    material: str, gauge: str, warned: bool
) -> None:
    """Flag 9: a warning, never a block, naming both and suggesting a decimal thickness."""

    def mismatch(result: Result) -> list[Note]:
        return [n for n in result.notes if n.text == checks.GAUGE_MISMATCH]

    warning = mismatch(bend(None, 0.2, material, gauge=gauge))
    assert bool(warning) == warned
    if warned:
        (note,) = warning
        assert note.kind is WARNING and note.subjects == ("thickness",)
        shown = said(note)
        assert shown.startswith("The gauge system may not suit the material: 16 ")
        assert "gives a nominal 0." in shown, "a gauge's thickness is nominal (§5.5)"
        assert "enter it as a decimal" in shown
    assert mismatch(bend(0.06, 0.2, material, gauge=gauge)) == [], "a typed thickness"


def test_a_typed_thickness_equal_to_the_gauges_isnt_warned_about() -> None:
    """The warning goes by the thickness's source, not its value."""
    gauge_thickness = 0.0598  # Manufacturers' Standard 16 ga, as the system states it
    typed = bend(gauge_thickness, 0.2, "al:6061", gauge="msg:16")
    assert typed.source_of("thickness").kind.value == "explicit"
    assert [n for n in typed.notes if n.text == checks.GAUGE_MISMATCH] == []


K_FOR_304 = (
    "K = 0.445 is a starting value FAA-H-8083-31B gives for 5052-H32 aluminum and 6061-T6 "
    "aluminum, not for 304 stainless, annealed (2B finish).\n"
    "Confirm it with a test bend, or apply a starting value given for this material."
)
"""The warning when FAA's K is applied and 304 is chosen: EDD gives 304 a starting value."""


def applied_k(material: str, source: str) -> Result:
    """Run a K-factor bend with ``material`` chosen and a K starting value applied."""
    table = MATERIAL_TABLE.load()
    entry = next(v for v in MATERIAL_TABLE.values(table) if v.source == source)
    assert entry.stated is not None
    origin = ValueOrigin.of(table, entry)
    settings = (
        DomainSettings()
        .set(DOMAIN, "k_factor", entry.stated, origin=origin)
        .set_choice(DOMAIN, "material", material)
    )
    inputs = {"thickness": 0.05 * IN, "inside_radius": 0.2 * IN}
    return BendAllowance().run(inputs, "k_factor", settings=settings.for_domain(DOMAIN))


def test_a_calculators_copy_of_an_applied_k_is_checked_too() -> None:
    """A copy keeps its citation as an explicit source's reference, and warns the same way."""
    table = MATERIAL_TABLE.load()
    faa = table.sources["faa_neutral_axis"].reference
    copied = InputSource(SourceKind.EXPLICIT, "copied from Sheet Metal settings", reference=faa)
    settings = DomainSettings().set_choice(DOMAIN, "material", "ss:304").for_domain(DOMAIN)
    inputs = {"thickness": 0.05 * IN, "inside_radius": 0.2 * IN, "k_factor": 0.445}
    result = BendAllowance().run(
        inputs, "k_factor", settings=settings, explicit_sources={"k_factor": copied}
    )
    assert [said(n) for n in result.notes if n.text == checks.K_MISMATCH] == [K_FOR_304]


def test_an_applied_k_given_for_other_materials_is_warned_about() -> None:
    """An applied value keeps its citation when the material changes."""
    stainless = applied_k("ss:304", "faa_neutral_axis")
    (warning,) = [n for n in stainless.notes if n.text == checks.K_MISMATCH]
    assert said(warning) == K_FOR_304
    assert warning.subjects == ("k_factor",)
    for material, source in (("al:6061", "faa_neutral_axis"), ("ss:304", "edd5_k")):
        covered = applied_k(material, source)
        assert all(n.text != checks.K_MISMATCH for n in covered.notes)


def test_the_k_warning_offers_a_starting_value_only_where_one_is_given() -> None:
    """Galvanized has no K starting value, so the warning doesn't offer one."""
    (warning,) = [
        n for n in applied_k("cs:a653", "faa_neutral_axis").notes if n.text == checks.K_MISMATCH
    ]
    assert detail(warning) == "Confirm it with a test bend."


def test_every_source_a_check_cites_states_its_scope() -> None:
    """ADR-0014 §1: a note says how far its source applies."""
    materials = load_materials(MATERIAL_TABLE.load())
    cited = [r.source for r in materials.radii]
    cited += [s for r in materials.radii for s in r.see_also]
    cited.append(materials.practice.source)
    assert all(source.reference.scope for source in cited)


def segment(radius: float, angles: tuple[float, float], material: str = "al:6061") -> Result:
    """Run the formed segment, T = 0.063 in, with the family's material."""
    settings = DomainSettings().set_choice(DOMAIN, "material", material).for_domain(DOMAIN)
    inputs = {
        "thickness": 0.063 * IN,
        "inside_radius": radius * IN,
        "bend_angle_1": angles[0],
        "bend_angle_2": angles[1],
    }
    return FormedSegmentFlatLength().run(inputs, "k_factor", settings=settings)


def test_a_part_with_bends_on_both_sides_of_90_degrees_checks_those_up_to_it() -> None:
    """6061-T6 at 0.063 in needs 0.16 in: the 90° bend is checked, the 120° one isn't covered."""
    part = segment(0.15, (90.0, 120.0))
    (limit,) = notes(part, LIMIT)
    assert limit.subjects == ("inside_radius", "thickness")
    (gap,) = notes(part, GAP)
    assert lead(gap).startswith("bend angle A2 = 120.00° is past 90°")
    assert gap.subjects == ("bend_angle_2",)
    assert not rule_of_thumb(part), "a cited check applied, so the rule of thumb is quiet"


def test_a_part_with_every_bend_past_90_degrees_is_checked_as_before() -> None:
    part = segment(0.05, (120.0, 135.0))
    (gap,) = notes(part, GAP)
    assert lead(gap).startswith("bend angles A1 = 120.00° and A2 = 135.00° are past 90°")
    assert gap.subjects == ("bend_angle_1", "bend_angle_2")
    assert notes(part, LIMIT) == [] and rule_of_thumb(part), "R < T: the rule of thumb speaks"


@pytest.mark.parametrize(
    ("material", "thickness", "radius"),
    [
        ("al:6061", 0.063, 0.05),
        ("al:6061", 0.182, 0.70),
        ("al:5052", 0.064, 0.05),
        ("cs:a1008", 0.04, 0.05),
        ("ss:304", 0.05, 0.09),
        ("ss:304", 0.06, 0.10),  # the band over 0.051 to 0.090 in
    ],
)
def test_each_limit_detail_states_every_covering_sources_value_where_it_applies(
    material: str, thickness: float, radius: float
) -> None:
    """Each source's stated value and its column or band, as it states them."""
    data = load_materials(MATERIAL_TABLE.load())
    temper = data.by_key[material].tempers[0].key
    (limit,) = notes(bend(thickness, radius, material), LIMIT)
    covering = [
        (source, value)
        for source in data.radius_sources(material, temper)
        if (value := source.at(thickness * IN)) is not None
    ]
    assert covering
    for source, value in covering:
        where = "at" if source.listed else "for sheet"
        assert f"gives {value.stated} {where} {value.column}" in detail(limit), source.label
        if source.label:
            assert f", from {source.label}" in detail(limit), "the stand-in label, verbatim"


LEAD_WORDS = 85
"""Characters a limit lead's template may use besides its values, name, and practice."""
LEAD_BUDGET = 150
"""A 6061-T6 limit lead in inches, with room for "the recommended minimum this check uses"."""


@pytest.mark.parametrize("unit", ["in", "mm"])
@pytest.mark.parametrize("fraction", [None, 64])
@pytest.mark.parametrize(
    ("material", "thickness", "radius"),
    [("al:6061", 0.063, 0.05), ("ss:304", 0.05, 0.09), ("cs:a1008", 0.04, 0.05)],
)
def test_a_limit_lead_keeps_its_scope_words_within_its_budget(
    material: str, thickness: float, radius: float, unit: str, fraction: int | None
) -> None:
    """The scope stays in the lead, and the lead's own words stay short.

    The budget holds the wording, not the data: a longer material name, or inch fractions,
    may take the lead past it, but the scope words never go to make room.
    """
    data = load_materials(MATERIAL_TABLE.load())
    name = data.by_key[material].tempers[0].name
    prefs = DisplayPrefs(length_unit=unit, fraction_denominator=fraction)
    (limit,) = notes(bend(thickness, radius, material), LIMIT)
    text = lead(limit, prefs)
    assert "the recommended minimum this check uses" in text, "the scope words"
    assert f"for {name} at " in text, "the material named as the data names it"
    assert limit.phrases["practice"] in text and "practice" in limit.phrases["practice"]
    shown = [value_parts(v, d, prefs).with_unit for v, d in limit.quantities.values()]
    own = len(text) - sum(map(len, shown)) - len(name) - len(limit.phrases["practice"])
    assert own <= LEAD_WORDS, "the template's own words"
    if (material, unit, fraction) == ("al:6061", "in", None):
        assert len(text) <= LEAD_BUDGET, "the usual case"


def test_a_notes_values_are_named_fields_shown_in_the_display_units() -> None:
    """ADR-0017 F1, with the localization notes: named fields, never a formatted number."""
    (limit,) = notes(bend(0.063, 0.05, "al:6061"), LIMIT)
    assert set(limit.quantities) == {"R", "minimum", "T"}
    assert "0." not in limit.text, "the template holds no number"
    fractions = DisplayPrefs(fraction_denominator=64)
    assert "≈" not in said(limit, fractions), "no fraction inside a sentence"
    assert "inside radius 0.0500 in is below 0.1600 in," in lead(limit, fractions)
    assert "1.2700 mm" in lead(limit, DisplayPrefs(length_unit="mm"))
    data = limit.to_dict()
    assert data["quantities"]["R"] == {"value": 0.05 * IN, "unit": "mm", "dimension": "length"}
    assert "1.27 mm" in data["text"], "JSON fills the fields in base units"
