"""The area and its squares, and outputs shown in a fixed unit (ADR-0018 §3, ADR-0019 §2)."""

from __future__ import annotations

from dataclasses import replace
from fractions import Fraction
from pathlib import Path
from typing import Any, override

import pytest

from caddcalc.core import (
    Calculator,
    Context,
    Domain,
    Method,
    Output,
    Param,
    Registry,
    SpecError,
    UsageError,
    Verification,
)
from caddcalc.core.formatting import (
    POINT,
    CopyForm,
    DisplayPrefs,
    NumberSymbols,
    ValueParts,
    copy_output,
    display_unit,
    format_output,
    format_significant,
    format_value,
    output_parts,
    results_tsv,
    spoken_value,
    unit_suffix,
    value_parts,
)
from caddcalc.core.i18n import use
from caddcalc.core.units import (
    Derivation,
    Dimension,
    Precision,
    Unit,
    UnitRegistry,
    UnitSystem,
    builtin,
    get_unit,
    parse_quantity_detailed,
    registry,
    units_for,
)
from tests.catalogs import shipped

L, AREA, A = Dimension.LENGTH, Dimension.AREA, Dimension.ANGLE
SQUARES = {"mm": "mm²", "cm": "cm²", "m": "m²", "in": "in²", "ft": "ft²"}
"""Each length unit's square, as SP 811 writes it."""


def test_the_area_is_a_length_squared_with_a_base_of_square_millimetres() -> None:
    spec = registry().dimension(AREA)
    assert (spec.base, spec.article, spec.derivation) == ("mm²", "an area", Derivation(L, 2))
    assert spec.follows_length
    assert [u.symbol for u in units_for(AREA)] == list(SQUARES.values())


def test_every_square_is_its_length_unit_squared_in_exact_arithmetic() -> None:
    for root, symbol in SQUARES.items():
        square, length = get_unit(symbol), get_unit(root)
        assert isinstance(square.exact, Fraction) and square.exact == length.exact**2
        assert square.factor == float(square.exact), "rounded once"
        assert (square.power_of, square.system) == (root, length.system)
    foot = get_unit("ft²")
    assert foot.exact == Fraction("92903.04") and foot.factor == 92903.04
    assert 304.8**2 != 92903.04, "why it's never computed in floats"
    assert get_unit("in²").exact == Fraction("645.16")


def test_every_square_cites_sp_811_and_the_inch_pound_ones_the_1959_notice() -> None:
    for symbol in SQUARES.values():
        unit = get_unit(symbol)
        assert unit.sources[0].publication is builtin.SP_811 and unit.reference is not None
        assert unit.reference.locator
        primary = builtin.FR_1959 in {s.publication for s in unit.sources}
        assert primary == (unit.system is UnitSystem.US_CUSTOMARY), symbol


@pytest.mark.parametrize(
    ("typed", "symbol"),
    [
        ("3 in²", "in²"),
        ("3 in^2", "in²"),
        ("3in2", "in²"),
        ("3 sq in", "in²"),
        ("3 SQ IN", "in²"),
        ("3 sq  in", "in²"),
        ("3 square inches", "in²"),
        ("1 square inch", "in²"),
        ("2 sq ft", "ft²"),
        ("2 square feet", "ft²"),
        ("2 ft2", "ft²"),
        ("5 mm²", "mm²"),
        ("5 sq mm", "mm²"),
        ("5 square millimetres", "mm²"),
        ("5 cm^2", "cm²"),
        ("5 square centimetre", "cm²"),
        ("5 m2", "m²"),
        ("5 square metres", "m²"),
    ],
)
def test_an_area_reads_in_any_of_the_forms_people_type(typed: str, symbol: str) -> None:
    got = parse_quantity_detailed(typed, AREA)
    number = float(typed[0])
    assert (got.unit.symbol, got.explicit_unit) == (symbol, True)
    assert got.value == pytest.approx(number * get_unit(symbol).factor)


def test_an_area_is_refused_where_a_length_is_expected_and_the_other_way() -> None:
    from caddcalc.core.errors import InputError

    with pytest.raises(InputError, match="'3 sq in' is an area, but a length is expected"):
        parse_quantity_detailed("3 sq in", L)
    with pytest.raises(InputError, match="'3 in' is a length, but an area is expected"):
        parse_quantity_detailed("3 in", AREA)
    bare = parse_quantity_detailed("3", AREA)
    assert (bare.unit.symbol, bare.value, bare.explicit_unit) == ("mm²", 3.0, False)


def test_the_typed_forms_are_input_only_and_display_writes_sp_811s_symbol() -> None:
    """SP 811 §6.1.8: "sq in" is an abbreviation, never written; in² is."""
    for symbol in SQUARES.values():
        unit = get_unit(symbol)
        assert unit.written == symbol and symbol.endswith("²") and not unit.close_up
        assert unit.written not in unit.aliases
        assert {f"sq {unit.power_of}", f"{unit.power_of}^2", f"{unit.power_of}2"} <= set(
            unit.aliases
        )


@pytest.mark.parametrize(("length", "square"), SQUARES.items())
def test_an_area_is_shown_in_the_square_of_the_length_choice(length: str, square: str) -> None:
    prefs = DisplayPrefs(length_unit=length, fraction_denominator=64)
    assert display_unit(AREA, prefs).symbol == square
    assert unit_suffix(AREA, prefs) == f" {square}"
    parts = value_parts(get_unit(square).factor, AREA, prefs)
    assert parts == ValueParts("1.00000", square), "never with an inch fraction"
    assert prefs.precision_for(AREA) == Precision(6, significant=True), "there's no preference"
    with pytest.raises(UsageError, match="area is shown to significant figures"):
        prefs.decimals_for(AREA)


@pytest.mark.parametrize(
    ("value", "length", "shown"),
    [
        (6451.6, "mm", "6451.60 mm²"),
        (6451.6, "in", "10.0000 in²"),
        (6451.6, "m", "0.00645160 m²"),
        (92903.04 * 1234.5, "ft", "1234.50 ft²"),
        (0.0, "in", "0.00000 in²"),
    ],
)
def test_an_area_shows_six_significant_figures_whatever_its_size(
    value: float, length: str, shown: str
) -> None:
    """4 decimals would give 6451.6000 mm² and 0.0065 m²."""
    assert format_value(value, AREA, DisplayPrefs(length_unit=length, decimals=2)) == shown


def test_an_area_reads_the_users_decimal_mark_and_says_its_unit_in_full() -> None:
    prefs = DisplayPrefs(symbols=NumberSymbols(","))
    assert format_value(92903.04 * 2.5, AREA, replace(prefs, length_unit="ft")) == "2,50000 ft²"
    assert spoken_value(value_parts(645.16, AREA, DisplayPrefs())) == "1.00000 square inches"
    assert spoken_value(ValueParts("1", "ft²")) == "1 square foot"
    assert spoken_value(ValueParts("2", "ft²")) == "2 square feet"


@pytest.mark.parametrize(
    ("tag", "symbol", "shown", "spoken"),
    [
        ("en_GB", "mm²", "2", "2 square millimetres"),
        ("en_GB", "m²", "1", "1 square metre"),
        ("en_AU", "cm²", "0.5", "0.5 square centimetres"),
        ("en_CA", "mm²", "2", "2 square millimetres"),
        ("en_GB", "in²", "2", "2 square inches"),
        ("en_US", "mm²", "2", "2 square millimeters"),
    ],
)
def test_the_british_catalog_spells_the_metric_squares_its_way(
    tmp_path: Path, tag: str, symbol: str, shown: str, spoken: str
) -> None:
    use([tag], directories=[shipped(shipped(tmp_path, "en_001"), "en_CA")])
    assert spoken_value(ValueParts(shown, symbol)) == spoken


def _fresh() -> UnitRegistry:
    test = UnitRegistry(builtin.DIMENSIONS)
    for unit in builtin.UNITS:
        test.register(unit)
    return test


def _yard(**changes: Any) -> Unit:
    fields: dict[str, Any] = {
        "symbol": "yd",
        "name": "yard",
        "dimension": L,
        "factor": 914.4,
        "aliases": ("yard", "yards"),
        "spoken_plural": "yards",
        "exact": Fraction("914.4"),
        "system": UnitSystem.US_CUSTOMARY,
        "sources": get_unit("ft").sources,
    }
    return Unit(**(fields | changes))


def _square_yard(**changes: Any) -> Unit:
    return _yard(
        **{
            "symbol": "yd²",
            "name": "square yard",
            "dimension": AREA,
            "factor": 836127.36,
            "aliases": ("sq yd",),
            "spoken_plural": "square yards",
            "exact": Fraction("914.4") ** 2,
            "power_of": "yd",
        }
        | changes
    )


def test_a_length_without_a_square_shows_areas_in_the_base_until_one_is_registered() -> None:
    test = _fresh()
    yard = _yard()
    test.register(yard)
    assert test.shown_unit(AREA, yard).symbol == "mm²"
    test.register(_square_yard())
    assert test.shown_unit(AREA, yard).symbol == "yd²"


@pytest.mark.parametrize(
    ("changes", "problem"),
    [
        ({"exact": Fraction("836127.37"), "factor": 836127.37}, "exact factor to the power 2"),
        ({"power_of": "furlong"}, "which isn't a length unit registered before it"),
        ({"power_of": "deg"}, "which isn't a length unit registered before it"),
        ({"dimension": L, "aliases": ()}, "length isn't a power of a dimension"),
    ],
)
def test_registration_refuses_a_square_that_isnt_its_roots_square(
    changes: dict[str, Any], problem: str
) -> None:
    test = _fresh()
    test.register(_yard())
    with pytest.raises(SpecError, match=problem):
        test.register(_square_yard(**changes))


def test_a_precision_is_some_decimal_places_or_at_least_one_significant_figure() -> None:
    assert Precision(0).digits == 0 and Precision(1, significant=True).significant
    with pytest.raises(SpecError, match="0 or more decimal places, not -1"):
        Precision(-1)
    with pytest.raises(SpecError, match="at least 1 significant figure, not 0"):
        Precision(0, significant=True)
    with pytest.raises(SpecError):
        Precision(True)  # type: ignore[arg-type]  # a bool isn't a count, as the test means
    for dimension in Dimension:
        assert registry().dimension(dimension).fixed == Precision(6, significant=True)


@pytest.mark.parametrize(
    ("value", "digits", "text"),
    [
        (25.4, 6, "25.4000"),
        (0.0254, 6, "0.0254000"),
        (2.54, 6, "2.54000"),
        (1 / 12, 6, "0.0833333"),
        (6.894757293168361, 6, "6.89476"),
        (92903.04, 6, "92903.0"),
        (1234567.0, 6, "1234570"),
        (1e9, 6, "1000000000"),
        (9.999997, 6, "10.0000"),
        (999999.7, 6, "1000000"),
        (0.000999999, 3, "0.00100"),
        (-0.5, 6, "-0.500000"),
        (0.0, 6, "0.00000"),
        (-0.0, 6, "0.00000"),
        (1e-6, 2, "0.0000010"),
        (1e-9, 2, "1.0e-09"),
        (0.125, 2, "0.12"),
        (123.4575, 6, "123.457"),
        (0.375, 2, "0.38"),
        (5.0, 1, "5"),
    ],
)
def test_significant_figures_keep_their_zeros_and_carry(
    value: float, digits: int, text: str
) -> None:
    assert format_significant(value, digits) == text
    assert format_significant(value, digits, ",") == text.replace(".", ",")


class _Rows(Calculator):
    """A test converter: one length in, its rows fixed in a unit each."""

    id = "test.rows"
    name = "Rows"
    domain = "test"
    summary = "Shows a length in fixed units."
    params = (Param("length", "X", "Length", L, default="1 in"),)
    outputs = (
        Output("mm", "MM", "Millimeters", L, unit="mm"),
        Output("in", "IN", "Inches", L, unit="in"),
        Output("shown", "S", "As preferred", L),
        Output("area", "SQ", "Square", AREA, unit="ft²"),
        Output("angle", "AN", "Angle", A, unit="rad"),
    )
    methods = (Method("only", "Only", "Rows of X", Verification.UNVERIFIED),)

    @override
    def compute(self, ctx: Context) -> None:
        for key, symbol in (("mm", "MM"), ("in", "IN"), ("shown", "S")):
            ctx.calc(symbol, "X", label=key, dimension=L, output=key)
        ctx.calc("SQ", "X*X", label="Square", dimension=AREA, output="area")
        ctx.calc("AN", "180", label="Angle", dimension=A, output="angle")


def test_a_fixed_unit_output_is_shown_in_it_whatever_the_preference() -> None:
    calc = _Rows()
    result = calc.run()
    for length in ("in", "mm", "ft"):
        prefs = DisplayPrefs(length_unit=length, decimals=2)
        shown = {o.key: output_parts(o, result.outputs[o.key], prefs) for o in calc.outputs}
        assert shown["mm"] == ValueParts("25.4000", "mm"), "six significant figures"
        assert shown["in"] == ValueParts("1.00000", "in")
        assert shown["area"] == ValueParts("0.00694444", "ft²")
        assert shown["angle"] == ValueParts("3.14159", "rad")
        assert shown["shown"] == value_parts(25.4, L, prefs), "the others follow the preference"


def test_a_fixed_inch_row_shows_the_fraction_when_its_preferred() -> None:
    calc = _Rows()
    output = calc.output("in")
    prefs = DisplayPrefs(length_unit="mm", fraction_denominator=16)
    parts = output_parts(output, 7.9375, prefs)
    assert parts == ValueParts("0.312500", "in", "5/16")
    assert format_output(output, 7.9375, prefs) == '0.312500 in  (≈ 5/16")'
    assert output_parts(calc.output("mm"), 7.9375, prefs).fraction is None


def test_a_fixed_unit_output_copies_in_its_own_unit() -> None:
    calc = _Rows()
    output = calc.output("mm")
    prefs = DisplayPrefs(symbols=NumberSymbols(","))
    copies = {
        form: copy_output(output, 1 / 3, prefs, form)
        for form in CopyForm
        if form.name != "FRACTION"
    }
    assert copies == {
        CopyForm.VALUE: "0.333333",
        CopyForm.SHOWN: "0,333333",
        CopyForm.WITH_UNIT: "0.333333 mm",
        CopyForm.FULL: "0.3333333333",
    }
    assert (
        copy_output(
            calc.output("in"), 7.9375, DisplayPrefs(fraction_denominator=16), CopyForm.FRACTION
        )
        == '5/16"'
    )


def test_fixed_rows_tabulate_and_go_to_json_in_base_units() -> None:
    calc = _Rows()
    result = calc.run()
    rows = results_tsv(calc, result, DisplayPrefs(length_unit="mm")).splitlines()
    assert rows[0] == "MM\tMillimeters\t25.4000\tmm"
    assert rows[1] == "IN\tInches\t1.00000\tin"
    assert rows[3] == "SQ\tSquare\t0.00694444\tft²"
    data = result.to_dict()["outputs"]
    assert data["area"] == {"value": pytest.approx(645.16), "unit": "mm²", "dimension": "area"}


@pytest.mark.parametrize(
    ("unit", "problem"),
    [
        ("furlong", "has a bad unit: Unknown unit 'furlong'"),
        ("deg", "names 'deg', which isn't the key symbol of a length unit"),
        ("inches", "names 'inches', which isn't the key symbol of a length unit"),
        ("ft²", "names 'ft²', which isn't the key symbol of a length unit"),
    ],
)
def test_an_output_naming_a_unit_it_cant_be_shown_in_is_a_definition_error(
    unit: str, problem: str
) -> None:
    class Bad(_Rows):
        outputs = (Output("mm", "MM", "Millimeters", L, unit=unit),)

    with pytest.raises(SpecError, match=problem):
        Bad.validate_spec()


TEST = Domain("test", "Test", "A domain for tests.")


@pytest.mark.gui
@pytest.mark.usefixtures("qt")
def test_a_result_field_shows_copies_and_says_a_fixed_unit_with_no_code_of_its_own() -> None:
    from PySide6.QtGui import QGuiApplication

    from caddcalc.gui.window import MainWindow

    calculators = Registry()
    calculators.register_domain(TEST)
    calculators.register(_Rows)
    window = MainWindow(registry=calculators, symbols=POINT)
    window.select_calculator("test.rows")
    fields = window.results.fields
    assert (fields["mm"].value.text(), fields["mm"].unit.text()) == ("25.4000", "mm")
    assert (fields["shown"].value.text(), fields["shown"].unit.text()) == ("1.0000", "in")
    assert (fields["area"].value.text(), fields["area"].unit.text()) == ("0.00694444", "ft²")
    assert fields["area"].accessibleName() == "Square, SQ: 0.00694444 square feet"
    fields["mm"].copy_button.click()
    assert QGuiApplication.clipboard().text() == "25.4000"
    window.close()


@pytest.mark.parametrize(
    ("value", "shown"),
    [
        (1e300, "1.00000e+300"),
        (-1e308, "-1.00000e+308"),
        (5e-324, "4.94066e-324"),
        (1.23e-7, "1.23000e-07"),
        (9.999997e15, "1.00000e+16"),
        (1.23e-6, "0.00000123000"),
        (999999999999999.0, "1000000000000000"),
        (1234567.0, "1234570"),
    ],
)
def test_significant_figures_take_an_exponent_outside_the_plain_range(
    value: float, shown: str
) -> None:
    """From 1e-6 up to 1e16 a value is plain decimals; outside, an exponent, never 301 digits."""
    from caddcalc.core.formatting import PLAIN_EXPONENTS, format_significant

    assert PLAIN_EXPONENTS == (-6, 16)
    assert format_significant(value, 6) == shown
    assert format_significant(value, 6, ",") == shown.replace(".", ",")
