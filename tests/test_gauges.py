"""Gauge systems: the table, the thicknesses it defines, and the gauge choice (ADR-0014 §2).

Spot checks are isolated published values: Manufacturers' Standard and galvanized from
Machinery's Handbook, 29th ed., Table 2, printed p. 2608; US Standard from 15 U.S.C. §206;
AWG from NBS Circular 391, Table 13. None is a reproduced table.
"""

from __future__ import annotations

from fractions import Fraction
from importlib import resources

import pytest

from caddcalc.calculators.sheet_metal import DOMAIN, BendAllowance
from caddcalc.calculators.sheet_metal.gauges import (
    GAUGE_TABLE,
    GaugeSystem,
    designation,
    load_gauges,
)
from caddcalc.core import (
    DomainSettings,
    NoteKind,
    SourceKind,
    SpecError,
    UsageError,
    expr,
    parse_table,
)
from caddcalc.core.formatting import DisplayPrefs, describe_note, describe_source, render_step

GAUGES = load_gauges(GAUGE_TABLE.load())
SYSTEMS = {system.id: system for system in GAUGES.systems}
TEXT = resources.files(GAUGE_TABLE.package).joinpath(GAUGE_TABLE.filename).read_text("utf-8")


@pytest.mark.parametrize(
    ("key", "stated"),
    [
        ("msg:3", "0.2391 in"),
        ("msg:10", "0.1345 in"),
        ("msg:12", "0.1046 in"),
        ("msg:20", "0.0359 in"),
        ("msg:38", "0.0060 in"),
        ("galv:8", "0.1681 in"),
        ("galv:12", "0.1084 in"),
        ("galv:16", "0.0635 in"),
        ("galv:20", "0.0396 in"),
        ("galv:30", "0.0157 in"),
        ("uss:10", "0.140625 in"),
        ("uss:12", "0.109375 in"),
        ("uss:14", "0.078125 in"),
        ("uss:16", "0.0625 in"),
        ("uss:26", "0.01875 in"),
        ("awg:0000", "0.4600 in"),
        ("awg:0", "0.3249 in"),
        ("awg:20", "0.0320 in"),
        ("awg:30", "0.0100 in"),
        ("awg:31", "0.00893 in"),
        ("awg:40", "0.00314 in"),
    ],
)
def test_a_gauge_states_its_published_thickness(key: str, stated: str) -> None:
    assert GAUGES.by_key[key][1].stated.text == stated


def test_each_system_covers_its_range_in_order() -> None:
    ranges = {s.id: (s.gauges[0].key, s.gauges[-1].key, len(s.gauges)) for s in GAUGES.systems}
    assert ranges == {
        "msg": ("msg:3", "msg:38", 36),
        "galv": ("galv:8", "galv:34", 27),
        "uss": ("uss:0000000", "uss:38", 45),
        "awg": ("awg:0000", "awg:40", 44),
    }
    assert [o.key for o in DOMAIN.options("gauge")] == list(GAUGES.by_key)


@pytest.mark.parametrize("system", GAUGES.systems, ids=lambda s: s.id)
def test_each_formula_agrees_in_floats_with_its_exact_evaluation(system: GaugeSystem) -> None:
    """``evaluate_exact`` against ``evaluate``: every gauge states the same either way."""
    for gauge in system.gauges:
        exact = expr.evaluate_exact(system.formula.expression, gauge.symbols, digits=40)
        assert exact == gauge.exact, gauge.key
        floats = {name: float(value) for name, value in gauge.symbols.items()}
        shown = expr.evaluate(system.formula.expression, floats)
        assert abs(shown - float(exact)) <= 1e-12 * float(exact), gauge.key
        assert system.precision.state(Fraction(repr(shown))) == gauge.stated, gauge.key


def test_a_derived_thickness_shows_its_work_ahead_of_the_calculators() -> None:
    settings = DomainSettings().set_choice(DOMAIN, "gauge", "msg:12").for_domain(DOMAIN)
    result = BendAllowance().run(settings=settings)
    work = result.steps[0]
    assert (work.symbol, work.label, work.value) == (
        "T",
        "Material thickness (12 ga, Manufacturers' Standard)",
        result.inputs["thickness"],
    )
    assert work.note == "0.1046150167… in before rounding to 4 decimal places"
    symbolic, numeric, _ = render_step(work, result, DisplayPrefs())
    assert (symbolic, numeric) == ("(w + c) / 16 / B", "(70 + 0) / 16 / 41.82")
    assert result.steps[1:] == BendAllowance().run().steps
    step = result.to_dict()["steps"][0]
    assert step["substitution"] == {"w": "70", "c": "0", "B": "41.82"}
    assert (step["expression_unit"], step["stated"]) == ("in", "0.1046 in")
    millimetres = render_step(work, result, DisplayPrefs(length_unit="mm"))
    assert millimetres[1:] == ("(70 + 0) / 16 / 41.82", "0.1046 in = 2.6568 mm")

    awg = DomainSettings().set_choice(DOMAIN, "gauge", "awg:0000").for_domain(DOMAIN)
    work = BendAllowance().run(settings=awg).steps[0]
    assert (
        render_step(work, result, DisplayPrefs())[1]
        == "0.005 · (0.46 / 0.005) ^ ((36 - (-3)) / 39)"
    )
    uss = DomainSettings().set_choice(DOMAIN, "gauge", "uss:26").for_domain(DOMAIN)
    assert BendAllowance().run(settings=uss).steps[0].note == "exact, as the system states it"


def test_no_work_is_shown_for_a_derived_value_not_used() -> None:
    settings = DomainSettings().set_choice(DOMAIN, "gauge", "msg:12")
    typed = settings.set_text(DOMAIN, "thickness", "0.125", "in").for_domain(DOMAIN)
    steps = BendAllowance().run(settings=typed).steps
    assert [s.symbol for s in steps] == [s.symbol for s in BendAllowance().run().steps]
    assert all(s.substitution is None for s in steps)


def test_us_standard_keeps_the_statutes_exact_decimals() -> None:
    """26 ga is exactly 0.01875 in, a tie at four decimals that a float would miss."""
    gauge = GAUGES.by_key["uss:26"][1]
    assert gauge.exact == Fraction(3, 160)
    assert GAUGES.by_key["uss:37"][1].stated.text == "0.006640625 in"


def test_galvanized_32_ships_as_computed() -> None:
    assert GAUGES.by_key["galv:32"][1].exact == Fraction(9, 16) / Fraction("41.82")


def test_multi_zero_sizes_read_and_parse_as_mh29_writes_them() -> None:
    assert GAUGES.key("uss", "7/0") == "uss:0000000"
    assert GAUGES.key("awg", "4/0") == GAUGES.key("awg", "0000") == "awg:0000"
    assert GAUGES.key("msg", " 12 ") == "msg:12"
    labels = [GAUGES.by_key[k][1].label for k in ("uss:0000000", "uss:0", "awg:0000", "msg:12")]
    assert labels == ["7/0 ga", "0 ga", "4/0 AWG", "12 ga"]
    with pytest.raises(UsageError, match="has no gauge '2'"):
        GAUGES.key("msg", "2")
    with pytest.raises(UsageError, match="isn't a gauge size"):
        designation("12 ga")


def test_each_system_cites_its_tolerance_standard() -> None:
    cited = {s.id: [r.title for r in s.note.references[1:]] for s in GAUGES.systems}
    assert cited == {
        "msg": ["ASTM A568/A568M"],
        "galv": ["ASTM A924/A924M"],
        "uss": ["ASTM A480/A480M"],
        "awg": ["ASTM B209/B209M", "ANSI H35.2"],
    }
    assert (
        SYSTEMS["uss"].group == "US Standard 1893, as commonly used for stainless; practice varies"
    )


def test_choosing_a_gauge_derives_the_thickness_with_its_caution() -> None:
    settings = DomainSettings().set_choice(DOMAIN, "gauge", "msg:12")
    derived = settings.for_domain(DOMAIN).derived["thickness"]
    assert derived.stated is not None and derived.stated.text == "0.1046 in"
    assert describe_source(derived.source) == (
        "12 ga, Manufacturers' Standard, steel sheet (nominal), Gauge systems, version 1"
    )

    gauged = BendAllowance().run(settings=settings.for_domain(DOMAIN))
    assert gauged.outputs == BendAllowance().run().outputs, "12 ga is the course default"
    assert gauged.source_of("thickness").kind is SourceKind.DERIVED
    (note,) = gauged.notes
    assert (note.kind, note.subjects) == (NoteKind.WARNING, ("thickness",))
    assert describe_note(note) == (
        "Nominal thickness; mill tolerances apply (see ASTM A568/A568M, 2025, rev. a). Check "
        "the material's specification or measure before cutting. (Gauge systems, version 1; "
        "ASTM A568/A568M, 2025, rev. a, scope: general requirements for carbon and HSLA "
        "steel sheet (A1008, A1011))"
    )


def test_each_caution_points_to_its_systems_tolerance_standards() -> None:
    cautions = {s.id: s.note.text.split("(see ")[1].split(")")[0] for s in GAUGES.systems}
    assert cautions == {
        "msg": "ASTM A568/A568M, 2025, rev. a",
        "galv": "ASTM A924/A924M, 2026",
        "uss": "ASTM A480/A480M, 2025, rev. b",
        "awg": "ASTM B209/B209M, 2021, rev. a and ANSI H35.2, 2024",
    }


def test_the_us_standard_label_keeps_its_scope() -> None:
    settings = DomainSettings().set_choice(DOMAIN, "gauge", "uss:12").for_domain(DOMAIN)
    assert settings.derived["thickness"].source.label == (
        "12 ga, US Standard 1893, as commonly used for stainless; practice varies (nominal)"
    )


def test_a_typed_thickness_beats_the_gauge_and_drops_the_caution() -> None:
    settings = DomainSettings().set_choice(DOMAIN, "gauge", "uss:12")
    typed = settings.set_text(DOMAIN, "thickness", "0.125", "in")
    result = BendAllowance().run(settings=typed.for_domain(DOMAIN))
    assert result.source_of("thickness").kind is SourceKind.DOMAIN
    assert result.notes == ()


def test_the_handbook_defines_only_the_steel_basis() -> None:
    """The cite-only cap: Machinery's Handbook defines one value, the 41.82 basis."""
    over = TEXT.replace('defined_by = "galvanized_rule"', 'defined_by = "steel_basis"')
    with pytest.raises(SpecError, match="'machinerys_handbook' defines 28 values; its cap is 1"):
        load_gauges(parse_table(over, "test", GAUGE_TABLE.content_keys))


@pytest.mark.parametrize(
    ("old", "new", "message"),
    [
        ('value = "41.82"', "value = 41.82", "as exact text"),
        ('formula = "awg"', 'formula = "wire"', "no formula 'wire'"),
        ('last = "38"\nprecision = { decimals', 'last = "39"\nprecision = { decimals', "39"),
        ('size_label = "AWG"', 'size_lable = "AWG"', "unknown keys"),
        ('constants = { B = "wrought_iron_basis" }', "constants = {}", "takes"),
        ('tolerances = ["stainless_tolerances"]', 'tolerances = ["vendor"]', "'vendor'"),
        ('rounding = "half_up", below', 'rounding = "ceiling", below', "rounding must be"),
        ('first = "0000"', 'first = "4/0"', "isn't a gauge size"),
    ],
)
def test_malformed_gauge_content_is_refused(old: str, new: str, message: str) -> None:
    assert TEXT.count(old) == 1, old
    with pytest.raises(SpecError, match=message):
        load_gauges(parse_table(TEXT.replace(old, new), "test", GAUGE_TABLE.content_keys))


@pytest.mark.parametrize(
    ("key", "stated", "millimetres"),
    [
        ("uss:12", "0.109375 in", "2.7781 mm"),
        ("awg:40", "0.00314 in", "0.0798 mm"),
        ("msg:12", "0.1046 in", "2.6568 mm"),
    ],
)
def test_the_work_shows_the_stated_thickness_never_a_rounded_one(
    key: str, stated: str, millimetres: str
) -> None:
    """Review M3: US Standard 12 ga's work said 0.1094 in, and 40 AWG's 0.0031 in."""
    settings = DomainSettings().set_choice(DOMAIN, "gauge", key).for_domain(DOMAIN)
    result = BendAllowance().run(settings=settings)
    work = result.steps[0]
    assert work.stated == stated
    assert render_step(work, result, DisplayPrefs())[2] == stated
    assert render_step(work, result, DisplayPrefs(length_unit="mm"))[2] == (
        f"{stated} = {millimetres}"
    )
