"""The Conversions family: one value in, the same value out in another unit (ADR-0024 §7).

Length, Fraction to decimal, Angle, Area, and Stress and pressure each take one value in
their input's picked unit and give it in their output's own picker's unit; Decimal to
fraction gives a length's nearest inch fraction, to a fineness, and the fraction's error.
"""

from __future__ import annotations

import json
import math
from decimal import Decimal
from fractions import Fraction

import pytest

from caddcalc.calculators import BUILTIN_DOMAINS, default_registry
from caddcalc.calculators.conversions import (
    CALCULATORS,
    AngleConverter,
    AreaConverter,
    DecimalToFraction,
    FractionToDecimal,
    LengthConverter,
    StressConverter,
)
from caddcalc.core import Calculator, Dimension, InputError, Output, UsageError, Verification
from caddcalc.core.formatting import (
    CopyForm,
    DisplayPrefs,
    NumberSymbols,
    ShownUnits,
    copy_output,
    format_output,
    output_parts,
    result_json,
    results_tsv,
    spoken_value,
)
from caddcalc.core.units import TypedValue, convert, get_unit, parse_quantity

L, A, S, AR = Dimension.LENGTH, Dimension.ANGLE, Dimension.STRESS, Dimension.AREA
IN = ShownUnits.generated()
PREFS = DisplayPrefs()
UNIT_TO_UNIT = (LengthConverter, FractionToDecimal, AngleConverter, AreaConverter, StressConverter)


def _units(choice: str = "", pick: str = "") -> ShownUnits:
    """The units a converter shows in: its input picked in ``choice``, its output in ``pick``."""
    picks = {"value": pick} if pick else {}
    return ShownUnits(IN.choices, picks, {"value": choice} if choice else {}, key="")


def _converted(
    calc: Calculator, typed: str, *, choice: str = "", pick: str = "", prefs: DisplayPrefs = PREFS
) -> str:
    """The converted value's text for ``typed``, as every front end shows it."""
    param = calc.params[0]
    result = calc.run({"value": parse_quantity(typed, param.dimension)})
    output = calc.output("value")
    return format_output(output, result.outputs["value"], _units(choice, pick), prefs)


def _copied(calc: Calculator, typed: str, pick: str, form: CopyForm = CopyForm.FULL) -> str:
    result = calc.run({"value": parse_quantity(typed, calc.params[0].dimension)})
    return copy_output(calc.output("value"), result.outputs["value"], _units("", pick), PREFS, form)


def _fraction(typed: str, fineness: int = 16, units: ShownUnits = IN) -> tuple[str, str]:
    """Decimal to fraction's two rows for ``typed``: the nearest fraction and its error."""
    calc = DecimalToFraction()
    result = calc.run({"value": parse_quantity(typed, L), "fineness": float(fineness)})
    return tuple(  # type: ignore[return-value]
        format_output(calc.output(key), result.outputs[key], units, PREFS)
        for key in ("nearest", "error")
    )


def test_conversions_comes_after_geometry_with_six_converters() -> None:
    assert [d.id for d in BUILTIN_DOMAINS] == ["geometry", "conversions", "sheet_metal"]
    registry = default_registry(load_plugins=False)
    ids = [c.id for c in registry if c.domain == "conversions"]
    assert sorted(ids) == [
        "conversions.angle",
        "conversions.area",
        "conversions.decimal_to_fraction",
        "conversions.fraction_to_decimal",
        "conversions.length",
        "conversions.stress",
    ]
    assert [c.id for c in CALCULATORS] == [
        "conversions.length",
        "conversions.fraction_to_decimal",
        "conversions.decimal_to_fraction",
        "conversions.angle",
        "conversions.area",
        "conversions.stress",
    ], "in the ADR's order"
    assert registry.domain("conversions").settings == ()


@pytest.mark.parametrize("calc", UNIT_TO_UNIT)
def test_each_unit_converter_has_one_input_and_one_output_with_its_own_picker(
    calc: type[Calculator],
) -> None:
    """ADR-0024 E7: input ``value`` and output ``value``, each in a unit of its own."""
    (param,) = calc.params
    (output,) = calc.outputs
    assert (param.key, output.key) == ("value", "value")
    assert len(param.choices) > 1, "a picker"
    assert output.picks and not output.follows_set, "its own picker, not a set"
    assert calc.unit_sets() == (), "no Show in picker"


def test_decimal_to_fraction_takes_a_fineness_and_gives_the_fraction_and_its_error() -> None:
    (value, fineness) = DecimalToFraction.params
    assert (value.key, fineness.key) == ("value", "fineness")
    assert fineness.allowed == ((16.0, "1/16"), (32.0, "1/32"), (64.0, "1/64"))
    assert [o.key for o in DecimalToFraction.outputs] == ["nearest", "error"]
    assert DecimalToFraction.output("nearest").form == "in_64"
    assert DecimalToFraction.output("error").signed
    with pytest.raises(InputError, match="Fineness \\(F\\) must be one of 1/16, 1/32, 1/64"):
        DecimalToFraction().run({"fineness": 12.0})


def test_the_exact_definitions_brief_values() -> None:
    """1 in = 25.4 mm and 1 ft² = 92 903.04 mm², both exact; 1 psi = 6.894757293168361 kPa."""
    inch, mm = get_unit("in"), get_unit("mm")
    assert convert(1, inch, mm) == Fraction("25.4")
    assert convert(1, get_unit("ft²"), get_unit("mm²")) == Fraction("92903.04")
    assert float(convert(1, get_unit("psi"), get_unit("kPa"))) == 6.894757293168361
    assert convert(Fraction(3, 16), inch, mm) == Fraction("4.7625"), "ADR-0019 §2's example"
    with pytest.raises(UsageError, match="measure different things"):
        convert(1, inch, get_unit("deg"))


def test_the_outputs_show_the_brief_values() -> None:
    assert _converted(LengthConverter(), "1 in", pick="mm") == "25.4000 mm"
    assert _converted(LengthConverter(), "1 in", pick="m") == "0.0254000 m"
    assert _copied(LengthConverter(), "1 in", "mm") == "25.4"
    assert _copied(AreaConverter(), "1 ft²", "mm²") == "92903.04"
    assert _converted(AreaConverter(), "1 ft²", pick="mm²") == "92903.0 mm²"
    assert _converted(StressConverter(), "1 psi", pick="kPa") == "6.89476 kPa"
    assert _copied(StressConverter(), "1 psi", "kPa") == "6.894757293"


def test_three_sixteenths_inch_is_4_7625_mm_to_1e_15() -> None:
    """ADR-0024 U3: 3/16 in → 0.1875 in, and the double nearest 4.7625 mm (E3)."""
    entry = TypedValue.read("3/16", "in", L)
    result = FractionToDecimal().run({"value": entry.value})
    assert result.outputs["value"] == pytest.approx(4.7625, abs=1e-15)
    assert _converted(FractionToDecimal(), "3/16 in") == "0.187500 in", "decimal inches first"
    assert _converted(FractionToDecimal(), "3/16 in", pick="mm") == "4.76250 mm"
    assert _copied(LengthConverter(), "3/16 in", "mm") == "4.7625"
    assert _converted(LengthConverter(), "4.7625 mm", pick="in") == "0.187500 in"


@pytest.mark.parametrize(
    ("calc", "choice", "counterpart"),
    [
        (LengthConverter, "in", "mm"),
        (LengthConverter, "ft_in", "mm"),
        (LengthConverter, "ft", "m"),
        (LengthConverter, "mm", "in"),
        (LengthConverter, "cm", "in"),
        (LengthConverter, "m", "ft"),
        (AngleConverter, "deg", "rad"),
        (AngleConverter, "dms", "rad"),
        (AngleConverter, "rad", "deg"),
        (AreaConverter, "in²", "mm²"),
        (AreaConverter, "m²", "ft²"),
        (StressConverter, "ksi", "MPa"),
        (StressConverter, "MPa", "ksi"),
        (StressConverter, "psi", "kPa"),
    ],
)
def test_the_output_follows_the_input_to_its_counterpart_until_picked(
    calc: type[Calculator], choice: str, counterpart: str
) -> None:
    """ADR-0024 §6, Q9: in → mm and mm → in, until the output's own picker is set."""
    output = calc.output("value")
    assert _units(choice).output_choice(output) == counterpart
    other = next(p for p in output.picks if p not in (choice, counterpart))
    assert _units(choice, other).output_choice(output) == other, "once picked, it's the user's"


def test_fraction_to_decimal_reads_a_fraction_in_inches_and_follows_nothing() -> None:
    (param,) = FractionToDecimal.params
    assert param.default_choice == "in"
    output = FractionToDecimal.output("value")
    assert output.picks[0] == "in" and not output.follows
    assert _units("mm").output_choice(output) == "in"
    assert "ft_in" not in output.picks, "a decimal"


def test_an_angle_in_dms_converts_to_radians() -> None:
    """ADR-0024 U3: 40°30′15″ → rad."""
    entry = TypedValue.read("40 30 15", "dms", A)
    result = AngleConverter().run({"value": entry.value})
    output = AngleConverter.output("value")
    assert format_output(output, result.outputs["value"], _units("dms"), PREFS) == "0.706931 rad"
    assert _converted(AngleConverter(), "29.99999999", pick="dms") == "30°0′0.00″"
    assert _converted(AngleConverter(), "1 rad", pick="deg") == "57.2958°"


def test_the_area_and_stress_values() -> None:
    expected = {"in²": "3.00000 in²", "ft²": "0.0208333 ft²", "mm²": "1935.48 mm²"}
    for pick, shown in expected.items():
        assert _converted(AreaConverter(), "3 sq in", pick=pick) == shown
    assert _converted(StressConverter(), "36 ksi", pick="psi") == "36000.0 psi"
    assert _converted(StressConverter(), "36 ksi", pick="kPa") == "248211 kPa"
    assert _converted(StressConverter(), "36 ksi", choice="ksi") == "248.211 MPa"


def test_a_length_in_feet_and_inches() -> None:
    assert _converted(LengthConverter(), "1'-4 3/16\"", pick="in") == "16.1875 in"
    assert _converted(LengthConverter(), "1'-4 3/16\"", pick="mm") == "411.162 mm"
    assert _converted(LengthConverter(), "411.1625 mm", pick="ft_in") == "1'-4 3/16\""


def test_0_1875_in_is_three_sixteenths_with_no_error() -> None:
    """ADR-0024 U3: 0.1875 in → 3/16" with an error of 0, at every fineness."""
    for fineness in (16, 32, 64):
        assert _fraction("0.1875 in", fineness) == ('3/16"', "0.000000 in")
    result = DecimalToFraction().run({"value": parse_quantity("0.1875 in", L)})
    assert result.outputs["error"] == 0.0


def test_the_nearest_fraction_and_its_error() -> None:
    """The error is the fraction less the value: positive where the fraction is longer."""
    assert _fraction("0.31 in") == ('5/16"', "+0.002500 in")
    assert _fraction("0.315 in") == ('5/16"', "-0.002500 in")
    assert _fraction("23.984375 in") == ('24"', "+0.015625 in")
    assert _fraction("23.984375 in", 64) == ('23 63/64"', "0.000000 in")
    assert _fraction("0.31 in", units=ShownUnits.generated("mm"))[1] == "+0.063500 mm", (
        "the error in the set's unit"
    )
    calc = DecimalToFraction()
    result = calc.run({"value": parse_quantity("1.19 in", L)})
    nearest = calc.output("nearest")
    assert copy_output(nearest, result.outputs["nearest"], IN, PREFS, CopyForm.VALUE) == '1-3/16"'
    parts = output_parts(nearest, result.outputs["nearest"], IN, PREFS)
    assert spoken_value(parts) == "1 and 3 sixteenths inches"


def test_a_typed_fraction_has_no_error_typed_in_inches_or_millimetres() -> None:
    """The nearest fraction is built as the parser builds a length typed in inches."""
    for typed in ("5/16 in", "0.3125 in", "1'-4 3/16\"", "7.9375 mm", "411.1625 mm"):
        for fineness in (16, 32, 64):
            result = DecimalToFraction().run(
                {"value": parse_quantity(typed, L), "fineness": float(fineness)}
            )
            assert result.outputs["error"] == 0.0, (typed, fineness)


@pytest.mark.parametrize(
    ("typed", "even"),
    [("3/32 in", '1/8"'), ("2.38125 mm", '1/8"'), ("7/32 in", '1/4"'), ("5.55625 mm", '1/4"')],
)
def test_a_tie_typed_in_inches_or_millimetres_takes_the_even_sixteenth(
    typed: str, even: str
) -> None:
    assert _fraction(typed)[0] == even
    assert _fraction("3/128 in", 64)[0] == '1/32"'


def test_a_value_and_its_negative_show_the_same_error_digits() -> None:
    """Every odd 1/128 inch to 4 ft, either sign, typed in inches or exactly in mm."""
    for k in range(1, 4 * 12 * 128, 2):
        for text in (f"{k}/128 in", f"{Decimal(k) * Decimal('25.4') / 128} mm"):
            for fineness in (16, 64):
                errors = [_fraction(sign + text, fineness)[1] for sign in ("", "-")]
                assert errors[0].lstrip("+-") == errors[1].lstrip("+-"), text


def test_a_length_that_rounds_to_zero_has_no_minus_sign() -> None:
    """−0.01 in is 0" to the nearest 1/16 inch, never -0"; to the 1/64, -1/64"."""
    assert _fraction("-0.01 in") == ('0"', "+0.010000 in")
    assert _fraction("-0.01 in", 64)[0] == '-1/64"'


def test_the_fraction_s_work_shows_it_and_its_error() -> None:
    result = DecimalToFraction().run({"value": parse_quantity("0.31 in", L), "fineness": 32.0})
    assert [s.symbol for s in result.steps] == ["N", "E"]
    assert result.steps[1].expression == "N - X"
    assert "nearest 1/32 inch" in result.steps[0].note


@pytest.mark.parametrize("calc", CALCULATORS)
def test_zero_and_negative_values_convert(calc: type[Calculator]) -> None:
    """Only a value that isn't finite is refused (ADR-0018 §3)."""
    for value in (0.0, -0.0, -12.5, 1e-9, 1e9):
        result = calc().run({"value": value})
        assert all(math.isfinite(v) for v in result.outputs.values())
        assert result.notes == ()
    for bad in (math.inf, -math.inf, math.nan):
        with pytest.raises(InputError, match="must be a finite number"):
            calc().run({"value": bad})


def test_a_negative_keeps_its_sign_and_is_spoken_minus() -> None:
    assert _converted(LengthConverter(), "-0.31 in", pick="mm") == "-7.87400 mm"
    assert _converted(AngleConverter(), "-0.5", pick="dms") == "-0°30′0.00″"
    assert _converted(StressConverter(), "-36 ksi", pick="MPa") == "-248.211 MPa"
    assert _converted(LengthConverter(), "0", pick="in") == "0.00000 in"
    calc = LengthConverter()
    result = calc.run({"value": parse_quantity("-0.31 in", L)})
    parts = output_parts(calc.output("value"), result.outputs["value"], _units("", "mm"), PREFS)
    assert spoken_value(parts) == "minus 7.87400 millimeters"


def test_a_comma_locale_shows_its_mark_and_copies_a_point() -> None:
    prefs = DisplayPrefs(symbols=NumberSymbols(","))
    assert _converted(LengthConverter(), "1 in", pick="mm", prefs=prefs) == "25,4000 mm"
    calc = LengthConverter()
    result = calc.run({"value": 25.4})
    copied = copy_output(
        calc.output("value"), result.outputs["value"], _units("", "mm"), prefs, CopyForm.VALUE
    )
    assert copied == "25.4000"


def test_each_converter_is_verified_against_sp_811_for_its_scope() -> None:
    for calc in CALCULATORS:
        (method,) = calc.methods
        assert method.verification is Verification.VERIFIED and method.scope, calc.id
        assert "Appendix B.8," in method.verification_note, calc.id
        assert any(
            "SP 811" in r.title or "Special Publication 811" in r.title for r in method.references
        )


def test_the_cli_and_json_need_no_code_of_their_own(capsys: pytest.CaptureFixture[str]) -> None:
    from caddcalc.cli import main

    assert main(["run", "conversions.length", "X=4.7625mm", "--no-work"]) == 0
    assert "0.187500 in" in capsys.readouterr().out, "mm follows to inches"
    assert main(["run", "conversions.length", "X=3/16in", "--output-unit", "Y=ft_in"]) == 0
    assert "0'-0 3/16\"" in capsys.readouterr().out
    assert main(["run", "conversions.stress", "X=1 psi", "--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["output_set"] is None
    assert data["outputs"]["value"]["base"] == {
        "value": pytest.approx(0.006894757293168361),
        "unit": "MPa",
    }
    assert data["outputs"]["value"]["shown"]["unit"] == "kPa", "psi's counterpart"
    assert main(["run", "conversions.decimal_to_fraction", "X=0.31in", "F=32"]) == 0
    out = capsys.readouterr().out
    assert '5/16"' in out and "+0.0025 in" in out and "1/32" in out
    assert main(["run", "conversions.length", "X=inf"]) != 0


@pytest.mark.parametrize("calc", UNIT_TO_UNIT)
@pytest.mark.parametrize(
    "value", [1.7976931348623157e308, -1.7976931348623157e308, 1e308, 5e-324, -5e-324]
)
def test_no_output_is_ever_infinite_or_not_a_number(calc: type[Calculator], value: float) -> None:
    """A unit smaller than the base can overflow: then the value is refused."""
    try:
        result = calc().run({"value": value})
    except InputError as exc:
        # Refused if it would overflow in any unit it can be picked in: kPa beside MPa,
        # and arcsec beside the degree.
        smallest = {StressConverter: "kPa", AngleConverter: "arcsec"}[calc]  # type: ignore[index]
        assert f"too large to show in {smallest}: its size must be under 1.79769e+308" in str(exc)
        return
    output = calc.output("value")
    for pick in output.picks:
        text = format_output(output, result.outputs["value"], _units("", pick), PREFS)
        assert "inf" not in text and "nan" not in text, (pick, text)
        assert len(text) < 30, ("no form's 150 digits at 1e308 (PR #1's Low 7)", pick, text)


def test_a_form_too_fine_for_a_huge_value_shows_its_full_unit() -> None:
    """At 1e308 mm, feet and inches would print hundreds of digits a double doesn't hold."""
    assert _converted(LengthConverter(), "1e300 mm", pick="ft_in") == "3.93701e+298 in"
    assert _converted(AngleConverter(), "1e300", pick="dms") == "1.00000e+300°"
    # Hundredths of a second count 360,000 a degree, so the form holds to 2.5e10°.
    assert _converted(AngleConverter(), "1e10", pick="dms") == "10000000000°0′0.00″"
    assert _converted(AngleConverter(), "1e12", pick="dms") == "1000000000000°"
    assert _fraction("1e300 mm")[0] == "3.93701e+298 in"
    assert _converted(LengthConverter(), "100 ft", pick="ft_in") == "100'-0\"", "below it, the form"


def test_a_subnormal_shows_no_digits_it_doesn_t_hold() -> None:
    """5e-324 MPa holds one bit; in psi, eight, so two figures (PR #1's final review, Low 7)."""
    assert _converted(StressConverter(), "5e-324 MPa", pick="MPa") == "5e-324 MPa"
    assert _converted(StressConverter(), "5e-324 MPa", pick="psi") == "7.2e-322 psi"
    assert _converted(StressConverter(), "1e-300 MPa", pick="MPa") == "1.00000e-300 MPa"


def test_a_radian_is_180_over_pi_degrees_to_every_digit_copied() -> None:
    assert _copied(AngleConverter(), "1 rad", "deg", CopyForm.FULL) == "57.29577951"
    assert _copied(AngleConverter(), "180", "rad", CopyForm.FULL) == "3.141592654"
    assert convert(1, get_unit("rad"), get_unit("deg")) == pytest.approx(180 / math.pi, rel=1e-15)


def test_an_error_s_sign_shows_in_its_work_and_tsv_but_not_json() -> None:
    from caddcalc.core.formatting import render_step

    calc = DecimalToFraction()
    for typed, shown in (("0.31 in", "+0.0025 in"), ("0.315 in", "-0.0025 in")):
        result = calc.run({"value": parse_quantity(typed, L)})
        step = next(s for s in result.steps if s.symbol == "E")
        assert step.signed and render_step(step, result, IN, PREFS)[2] == shown, typed
    result = calc.run({"value": parse_quantity("0.31 in", L)})
    row = next(r for r in results_tsv(calc, result, IN, PREFS).splitlines() if r.startswith("E"))
    assert row.split("\t")[2] == "+0.002500", "a number, not quoted as text"
    data = result_json(calc, result, IN, PREFS)
    assert "signed" not in data["steps"][0], "JSON's shape has no sign of its own"
    assert data["inputs"]["fineness"]["shown"]["text"] == "1/16"


def _one_output(output: Output, *, forms_in_sets: bool = True) -> type[Calculator]:
    """A calculator of one length input and ``output``, for its definition's checks."""
    from caddcalc.core import Method, Param

    class OneOutput(Calculator):
        id = "test.one_output"
        name = "One output"
        domain = "test"
        summary = "One output."
        params = (Param("value", "X", "Value", L, default="1 in"),)
        outputs = (output,)
        methods = (Method("only", "Only", "R", Verification.UNVERIFIED),)

        def compute(self, ctx: object) -> None:  # pragma: no cover - never run
            raise AssertionError(ctx)

    OneOutput.forms_in_sets = forms_in_sets
    return OneOutput


def test_a_signed_output_is_never_in_a_form_fixed_picked_or_set() -> None:
    """A form rounds an error to its fineness: 1/32 in out shows 0" (UI/UX's PR #3 M1)."""
    from caddcalc.core import Output, SpecError
    from caddcalc.core.units import Precision

    error = Output("error", "E", "Error", L, signed=True, precision=Precision(6))
    with pytest.raises(SpecError, match="output set 'in_16' shows it in the form 'in_16'"):
        _one_output(error).validate_spec()
    _one_output(error, forms_in_sets=False).validate_spec()  # decimal sets only
    assert [s.key for s in _one_output(error, forms_in_sets=False).unit_sets()] == [
        "in",
        "ft",
        "mm",
        "cm",
        "m",
    ]
    picked = Output("error", "E", "Error", L, signed=True, picks=("in", "in_16"))
    with pytest.raises(SpecError, match="can't be picked in a form such as 'in_16'"):
        _one_output(picked).validate_spec()
    with pytest.raises(SpecError, match="is signed and in a form"):
        _one_output(Output("error", "E", "Error", L, signed=True, form="in_64")).validate_spec()
    unsigned = Output("value", "V", "Value", L, precision=Precision(6))
    _one_output(unsigned).validate_spec()  # a precision in a set's unit; a form keeps its own


def test_every_set_shows_decimal_to_fraction_s_error_as_a_decimal() -> None:
    """At every set and fineness, never a fraction or feet and inches (UI/UX's PR #3 M1)."""
    calc = DecimalToFraction()
    output = calc.output("error")
    for unit_set in DecimalToFraction.unit_sets():
        units = ShownUnits.of(unit_set)
        for fineness in (16.0, 32.0, 64.0):
            result = calc.run({"value": parse_quantity("0.09375 in", L), "fineness": fineness})
            parts = output_parts(output, result.outputs["error"], units, PREFS)
            assert parts.compound is None and parts.unit == unit_set.key, (unit_set.key, fineness)
            if fineness == 16.0:  # 1/8" is 1/32 in longer than 0.09375 in
                assert parts.number == {"in": "+0.031250", "mm": "+0.793750"}.get(
                    unit_set.key, parts.number
                )
                assert parts.number.strip("+0.") != "", "never a false zero"


def test_a_follow_needs_its_input() -> None:
    from caddcalc.core import Output, SpecError

    cases = [
        (Output("row", "R", "Row", L, follows="value"), "follows 'value', which must be"),
        (Output("row", "R", "Row", L, picks=("in",), follows="gap"), "follows 'gap'"),
        (
            Output("row", "R", "Row", L, picks=("in",), follows="value", counterparts={"mm": "cm"}),
            "counterpart 'mm' → 'cm'",
        ),
        (Output("row", "R", "Row", L, picks=("in",), counterparts={"mm": "in"}), "follows nothing"),
    ]
    for output, why in cases:
        with pytest.raises(SpecError, match=why):
            _one_output(output).validate_spec()


def test_allowed_values_must_differ_and_each_have_a_label() -> None:
    from caddcalc.core import Method, Output, Param, SpecError

    for allowed in (((16.0, "1/16"), (16.0, "1/16 again")), ((16.0, " "),)):

        class Bad(Calculator):
            id = "test.bad"
            name = "Bad"
            domain = "test"
            summary = "Bad allowed values."
            params = (Param("f", "F", "F", Dimension.COUNT, default="16", allowed=allowed),)
            outputs = (Output("y", "Y", "Y", Dimension.COUNT),)
            methods = (Method("only", "Only", "Y", Verification.UNVERIFIED),)

            def compute(self, ctx: object) -> None:  # pragma: no cover - never run
                raise AssertionError(ctx)

        with pytest.raises(SpecError, match="allowed values must differ, each with a label"):
            Bad.validate_spec()


def test_a_typed_plain_decimal_is_listed_as_typed() -> None:
    """The Inputs list gives ``0.09375 in``, not ``0.0938 in`` (UI/UX's PR #3 call, §5)."""
    from caddcalc.core.formatting import NumberSymbols, param_parts

    calc = DecimalToFraction()
    param = calc.params[0]

    def listed(text: str, choice: str = "in", mark: str = ".", picked: str = "in") -> str:
        entry = TypedValue.read(text, choice, L, decimal=mark)
        units = _units(picked)
        prefs = DisplayPrefs(symbols=NumberSymbols(mark))
        return param_parts(param, entry.value, units, prefs, entry).with_unit

    assert listed("0.09375") == "0.09375 in"
    assert listed("−0.09375") == "-0.09375 in", "an ASCII sign, as every number shown"
    assert listed("+0.09375") == "0.09375 in"
    assert listed("0,09375", mark=",") == "0,09375 in", "the screen's own mark"
    assert listed("3/32") == "0.0938 in", "a fraction is listed as read; its echo reads it"
    assert listed("0.1 - 0.00625") == "0.0938 in", "so is an expression"
    assert listed("2.38125", "mm", picked="mm") == "2.38125 mm"
    entry = TypedValue.read("0.09375", "in", L)
    other = param_parts(param, entry.value * 2, IN, PREFS, entry).with_unit
    assert other == "0.1875 in", "only what the run used"
    comma = DisplayPrefs(symbols=NumberSymbols(","))
    app_s = param_parts(param, entry.value, IN, comma, entry).with_unit
    assert app_s == "0,0938 in", "text read in another mark than the screen's is the app's"
    converted = param_parts(param, entry.value, _units("mm"), PREFS, entry).with_unit
    assert converted == "2.3812 mm", "listed in another unit, converted (a tie, to even)"


def test_the_cli_lists_a_typed_decimal_as_typed(capsys: pytest.CaptureFixture[str]) -> None:
    from caddcalc.cli import main

    assert main(["run", "conversions.decimal_to_fraction", "X=0.09375"]) == 0
    out = capsys.readouterr().out
    assert "0.09375 in" in out and "+0.031250 in" in out
    assert main(["run", "conversions.decimal_to_fraction", "X=0.09375", "--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["inputs"]["value"]["shown"]["text"] == "0.09375 in"
    assert data["outputs"]["error"]["shown"]["text"] == "+0.031250 in"


@pytest.mark.parametrize("calc", CALCULATORS)
def test_no_converter_s_help_asks_for_a_typed_unit(calc: type[Calculator]) -> None:
    """Pick, then type: a field refuses a typed unit (ADR-0024 Q5; S&R's and UI/UX's Low).

    Only a form's own example, after "; in", may give the form's marks, its grammar.
    """
    import re

    from caddcalc.core.units import registry

    value = next(p for p in calc.params if p.key == "value")
    assert value.help.startswith("Pick its unit, then type "), value.help
    examples = value.help.split("; in ", 1)[0]
    for unit in registry().units_for(value.dimension):
        for key in unit.keys:
            typed = re.search(rf"\d\s*{re.escape(key)}(?!\w)", examples, re.IGNORECASE)
            assert typed is None, f"{calc.id}: {typed and typed.group()!r} in {value.help!r}"
