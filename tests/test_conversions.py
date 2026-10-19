"""The Conversions family: one value, in every unit of its kind at once (ADR-0018 §3)."""

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
    LengthConverter,
    StressConverter,
)
from caddcalc.core import Calculator, Dimension, InputError, UsageError, Verification
from caddcalc.core.formatting import (
    CopyForm,
    DisplayPrefs,
    NumberSymbols,
    copy_output,
    format_output,
    output_parts,
    spoken_value,
    value_parts,
)
from caddcalc.core.units import convert, get_unit, parse_quantity

L, A, S, AR = Dimension.LENGTH, Dimension.ANGLE, Dimension.STRESS, Dimension.AREA


def _shown(calc: Calculator, typed: str, prefs: DisplayPrefs | None = None) -> dict[str, str]:
    """Each row's text for ``typed``, as every front end shows it."""
    prefs = prefs or DisplayPrefs()
    (param,) = calc.params
    result = calc.run({"value": parse_quantity(typed, param.dimension)})
    return {o.key: format_output(o, result.outputs[o.key], prefs) for o in calc.outputs}


def _copied(calc: Calculator, typed: str, row: str, form: CopyForm = CopyForm.FULL) -> str:
    (param,) = calc.params
    result = calc.run({"value": parse_quantity(typed, param.dimension)})
    return copy_output(calc.output(row), result.outputs[row], DisplayPrefs(), form)


def test_conversions_comes_after_geometry_with_one_converter_per_kind() -> None:
    assert [d.id for d in BUILTIN_DOMAINS] == ["geometry", "conversions", "sheet_metal"]
    registry = default_registry(load_plugins=False)
    ids = {c.id for c in registry if c.domain == "conversions"}
    assert ids == {
        "conversions.length",
        "conversions.angle",
        "conversions.area",
        "conversions.stress",
    }
    assert registry.domain("conversions").settings == ()


def test_the_exact_definitions_brief_values() -> None:
    """1 in = 25.4 mm and 1 ft² = 92 903.04 mm², both exact; 1 psi = 6.894757293168361 kPa."""
    inch, mm = get_unit("in"), get_unit("mm")
    assert convert(1, inch, mm) == Fraction("25.4")
    assert convert(1, get_unit("ft²"), get_unit("mm²")) == Fraction("92903.04")
    assert float(convert(1, get_unit("psi"), get_unit("kPa"))) == 6.894757293168361
    assert convert(Fraction(3, 16), inch, mm) == Fraction("4.7625"), "ADR-0019 §2's example"
    with pytest.raises(UsageError, match="measure different things"):
        convert(1, inch, get_unit("deg"))


def test_the_rows_show_the_brief_values() -> None:
    length = _shown(LengthConverter(), "1 in")
    assert (length["mm"], length["in"], length["m"]) == ("25.4000 mm", "1.00000 in", "0.0254000 m")
    assert _copied(LengthConverter(), "1 in", "mm") == "25.4"
    assert _copied(AreaConverter(), "1 ft²", "mm2") == "92903.04"
    assert _shown(AreaConverter(), "1 ft²")["mm2"] == "92903.0 mm²"
    assert _shown(StressConverter(), "1 psi")["kpa"] == "6.89476 kPa"
    assert _copied(StressConverter(), "1 psi", "kpa") == "6.894757293"


def test_a_typed_fraction_reads_as_its_exact_conversion_at_every_shown_digit() -> None:
    """3/16 in is 4.7625 mm: the typed double is 4.762499999999999 mm, copied 4.7625."""
    assert _copied(LengthConverter(), "3/16 in", "mm") == "4.7625"
    assert _shown(LengthConverter(), "4.7625 mm")["in"] == "0.187500 in"


@pytest.mark.parametrize("length", ["in", "mm", "ft", "m"])
def test_every_row_keeps_its_unit_whatever_the_unit_system(length: str) -> None:
    prefs = DisplayPrefs(length_unit=length, decimals=1, fraction_denominator=None)
    assert _shown(LengthConverter(), "1 in", prefs) == _shown(LengthConverter(), "1 in")
    assert _shown(AreaConverter(), "1 ft²", prefs) == _shown(AreaConverter(), "1 ft²")
    assert _shown(StressConverter(), "1 psi", prefs) == _shown(StressConverter(), "1 psi")


def test_the_length_rows() -> None:
    rows = _shown(LengthConverter(), "1'-4 3/16\"")
    assert rows == {
        "in": "16.1875 in",
        "ft": "1.34896 ft",
        "mm": "411.162 mm",
        "cm": "41.1162 cm",
        "m": "0.411162 m",
        "ft_in": "1'-4 3/16\"",
        "nearest_16": '16 3/16"',
        "error_16": "0.000000 in",
        "nearest_32": '16 3/16"',
        "error_32": "0.000000 in",
        "nearest_64": '16 3/16"',
        "error_64": "0.000000 in",
    }


def test_each_nearest_fraction_carries_its_error() -> None:
    """The error is the fraction less the value: positive where the fraction is longer."""
    rows = _shown(LengthConverter(), "0.31 in")
    assert (rows["nearest_16"], rows["error_16"]) == ('5/16"', "+0.002500 in")
    rows = _shown(LengthConverter(), "23.984375 in")  # 23 63/64
    assert rows["ft_in"] == "2'-0\"", "1'-11 63/64\" carries at 1/16"
    assert (rows["nearest_16"], rows["error_16"]) == ('24"', "+0.015625 in")
    assert (rows["nearest_64"], rows["error_64"]) == ('23 63/64"', "0.000000 in")
    assert _copied(LengthConverter(), "0.31 in", "nearest_16", CopyForm.VALUE) == '5/16"'
    assert _copied(LengthConverter(), "1.19 in", "nearest_16", CopyForm.VALUE) == '1-3/16"'
    assert _copied(LengthConverter(), "0.31 in", "nearest_16") == "0.3125", "full: the fraction"


def test_a_typed_fraction_has_no_error_in_any_unit() -> None:
    """The nearest fraction is built as the parser builds a length typed in inches.

    So typed in inches its error is exactly 0, and typed in mm it rounds to 0 as shown.
    """
    for typed in ("5/16 in", "0.3125 in", "1'-4 3/16\"", '16 3/16"'):
        result = LengthConverter().run({"value": parse_quantity(typed, L)})
        assert {result.outputs[f"error_{d}"] for d in (16, 32, 64)} == {0.0}, typed
    for typed in ("7.9375 mm", "411.1625 mm"):
        rows = _shown(LengthConverter(), typed)
        assert {rows[f"error_{d}"] for d in (16, 32, 64)} == {"0.000000 in"}, typed
        result = LengthConverter().run({"value": parse_quantity(typed, L)})
        assert {result.outputs[f"error_{d}"] for d in (16, 32, 64)} == {0.0}, "within its ulp"
        assert _copied(LengthConverter(), typed, "error_16", CopyForm.FULL) == "0"


def test_the_length_work_shows_each_fraction_and_its_error() -> None:
    result = LengthConverter().run({"value": parse_quantity("0.31 in", L)})
    assert [s.symbol for s in result.steps] == ["N16", "E16", "N32", "E32", "N64", "E64"]
    assert result.steps[1].expression == "N16 - X"
    assert "nearest 1/16 inch" in result.steps[0].note


def test_a_nearest_fraction_is_spoken_in_words() -> None:
    calc = LengthConverter()
    result = calc.run({"value": parse_quantity("1.19 in", L)})
    parts = output_parts(calc.output("nearest_16"), result.outputs["nearest_16"], DisplayPrefs())
    assert spoken_value(parts) == "1 and 3 sixteenths inches"


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


def test_an_error_shows_its_sign_both_ways_and_says_it() -> None:
    """A positive error has its "+", so its direction reads as the negative's does."""
    calc = LengthConverter()
    for typed, shown, spoken in (
        ("0.31 in", "+0.002500", "plus 0.002500 inches"),
        ("0.315 in", "-0.002500", "minus 0.002500 inches"),
        ("0.3125 in", "0.000000", "0.000000 inches"),
    ):
        result = calc.run({"value": parse_quantity(typed, L)})
        parts = output_parts(calc.output("error_16"), result.outputs["error_16"], DisplayPrefs())
        assert (parts.number, spoken_value(parts)) == (shown, spoken), typed
        assert _copied(calc, typed, "error_16", CopyForm.VALUE) == shown, "as shown"
    assert calc.output("error_16").help.endswith(
        "positive where the fraction is longer than the value."
    )
    assert not calc.output("mm").signed, "only a difference is signed"
    assert _shown(calc, "-0.31 in")["mm"] == "-7.87400 mm"


def test_every_negative_is_spoken_minus() -> None:
    """A plain value says its sign by the template a compound form's uses (UI/UX's L3)."""
    calc = LengthConverter()
    result = calc.run({"value": parse_quantity("-0.31 in", L)})
    parts = output_parts(calc.output("mm"), result.outputs["mm"], DisplayPrefs())
    assert spoken_value(parts) == "minus 7.87400 millimeters"
    assert spoken_value(value_parts(-25.4, L, DisplayPrefs())) == "minus 1.0000 inches"
    assert spoken_value(value_parts(-30.0, A, DisplayPrefs())) == "minus 30.00 degrees"
    assert spoken_value(value_parts(-0.25, Dimension.RATIO, DisplayPrefs())) == "minus 0.2500"


def test_a_negative_keeps_its_sign_in_every_row() -> None:
    rows = _shown(LengthConverter(), "-0.31 in")
    assert rows["in"] == "-0.310000 in" and rows["mm"] == "-7.87400 mm"
    assert (rows["nearest_16"], rows["error_16"]) == ('-5/16"', "-0.002500 in")
    assert _shown(AngleConverter(), "-0.5")["dms"] == "-0°30′0.00″"
    assert _shown(StressConverter(), "-36 ksi")["mpa"] == "-248.211 MPa"
    assert _shown(LengthConverter(), "0")["in"] == "0.00000 in"


def test_the_angle_rows() -> None:
    assert _shown(AngleConverter(), "29.99999999") == {
        "deg": "30.0000°",
        "rad": "0.523599 rad",
        "dms": "30°0′0.00″",
    }
    assert _shown(AngleConverter(), "1 rad")["deg"] == "57.2958°"
    assert _shown(AngleConverter(), "40°30′15″")["deg"] == "40.5042°"


def test_the_area_rows() -> None:
    assert _shown(AreaConverter(), "3 sq in") == {
        "in2": "3.00000 in²",
        "ft2": "0.0208333 ft²",
        "mm2": "1935.48 mm²",
        "cm2": "19.3548 cm²",
        "m2": "0.00193548 m²",
    }


def test_the_stress_rows() -> None:
    assert _shown(StressConverter(), "36 ksi") == {
        "psi": "36000.0 psi",
        "ksi": "36.0000 ksi",
        "kpa": "248211 kPa",
        "mpa": "248.211 MPa",
    }


def test_a_comma_locale_shows_its_mark_and_copies_a_point() -> None:
    prefs = DisplayPrefs(symbols=NumberSymbols(","))
    assert _shown(LengthConverter(), "1 in", prefs)["mm"] == "25,4000 mm"
    calc = LengthConverter()
    result = calc.run({"value": 25.4})
    assert copy_output(calc.output("mm"), result.outputs["mm"], prefs, CopyForm.VALUE) == "25.4000"


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

    assert main(["run", "conversions.length", "X=4.7625mm", "--units", "mm"]) == 0
    out = capsys.readouterr().out
    assert "0.187500 in" in out and '3/16"' in out and "0'-0 3/16\"" in out
    assert main(["run", "conversions.stress", "X=1 psi", "--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["outputs"]["kpa"]["unit"] == "MPa", "JSON is in base units"
    assert data["outputs"]["kpa"]["value"] == pytest.approx(0.006894757293168361)
    assert main(["run", "conversions.length", "X=inf"]) != 0
    capsys.readouterr()
    assert main(["run", "conversions.length", "X=0.31in"]) == 0
    assert "E16    Error of the nearest 1/16" in (out := capsys.readouterr().out)
    assert "+0.002500 in" in out, "the sign is display only; JSON keeps the number"


def test_a_half_way_length_takes_the_even_fraction_in_every_row() -> None:
    """3/32 in is half-way from 1/16 to 1/8 in, and 7/32 in from 3/16 to 1/4 in."""
    for typed, nearest, ft_in in (
        ("3/32 in", '1/8"', "0'-0 1/8\""),
        ("7/32 in", '1/4"', "0'-0 1/4\""),
    ):
        rows = _shown(LengthConverter(), typed)
        assert (rows["nearest_16"], rows["ft_in"]) == (nearest, ft_in), typed
    assert _shown(LengthConverter(), "3/128 in")["nearest_64"] == '1/32"'


@pytest.mark.parametrize("typed", ["3/32 in", "2.38125 mm", "7/32 in", "5.55625 mm"])
def test_the_hint_and_the_nearest_rows_round_a_tie_alike(typed: str) -> None:
    """The ``(≈ …")`` hint beside the inch row and the nearest 1/16 inch agree on a tie."""
    prefs = DisplayPrefs(length_unit="in", fraction_denominator=16)
    calc = LengthConverter()
    result = calc.run({"value": parse_quantity(typed, L)})
    hint = output_parts(calc.output("in"), result.outputs["in"], prefs).fraction
    nearest = copy_output(
        calc.output("nearest_16"), result.outputs["nearest_16"], prefs, CopyForm.VALUE
    )
    assert f'{hint}"' == nearest.replace("0-", ""), typed
    assert hint in ("1/8", "1/4"), typed


def test_an_error_row_takes_no_fraction_hint() -> None:
    prefs = DisplayPrefs(fraction_denominator=64)
    calc = LengthConverter()
    result = calc.run({"value": parse_quantity("0.31 in", L)})
    assert output_parts(calc.output("error_16"), result.outputs["error_16"], prefs).fraction is None
    assert output_parts(calc.output("in"), result.outputs["in"], prefs).fraction == "5/16"


def test_a_value_and_its_negative_show_the_same_error_digits() -> None:
    """Every odd 1/128 inch to 4 ft, either sign, typed in inches or exactly in mm."""
    calc = LengthConverter()
    for k in range(1, 4 * 12 * 128, 2):
        for text in (f"{k}/128 in", f"{Decimal(k) * Decimal('25.4') / 128} mm"):
            shown = []
            for sign in ("", "-"):
                result = calc.run({"value": parse_quantity(sign + text, L)})
                rows = [calc.output(f"error_{d}") for d in (16, 32, 64)]
                errors = [format_output(o, result.outputs[o.key], DisplayPrefs()) for o in rows]
                shown.append([e.lstrip("+-") for e in errors])
            assert shown[0] == shown[1], text


@pytest.mark.parametrize("calc", CALCULATORS)
@pytest.mark.parametrize(
    "value", [1.7976931348623157e308, -1.7976931348623157e308, 1e308, 5e-324, -5e-324]
)
def test_no_row_is_ever_infinite_or_not_a_number(calc: type[Calculator], value: float) -> None:
    """A row in a unit smaller than the base can overflow: then the value is refused."""
    try:
        result = calc().run({"value": value})
    except InputError as exc:
        assert calc is StressConverter, "only stress has rows smaller than its base"
        assert "is too large to show in kPa: its size must be under 1.79769e+308 kPa" in str(exc)
        return
    for output in calc.outputs:
        text = format_output(output, result.outputs[output.key], DisplayPrefs())
        assert "inf" not in text and "nan" not in text, (output.key, text)


@pytest.mark.parametrize("typed", ["1e308 ft", "-1e308 ft", "1e308 m", "1e400"])
def test_a_finite_number_too_large_to_calculate_with_says_so(typed: str) -> None:
    with pytest.raises(InputError, match="is too large"):
        parse_quantity(typed, L)


def test_a_length_that_rounds_to_zero_has_no_minus_sign() -> None:
    """−0.01 in is 0" to the nearest 1/16 and 1/32 inch, never -0"; to the 1/64, -1/64"."""
    rows = _shown(LengthConverter(), "-0.01 in")
    assert (rows["nearest_16"], rows["nearest_32"], rows["nearest_64"]) == ('0"', '0"', '-1/64"')
    assert _copied(LengthConverter(), "-0.01 in", "nearest_16", CopyForm.VALUE) == '0"'
    assert rows["error_16"] == "+0.010000 in"
    # The rows are given the fraction, already rounded; the form rounds a raw value too.
    from caddcalc.core.units.compound import NearestInches

    for value in (-0.01 * 25.4, -0.0):
        text = NearestInches(16).text(value)
        assert (text.shown, text.copied, text.spoken) == ('0"', '0"', "0 inches"), value


def test_an_output_with_a_precision_but_no_unit_is_a_definition_error() -> None:
    from caddcalc.core import Method, Output, Param, SpecError
    from caddcalc.core.units import Precision

    class Bad(Calculator):
        id = "test.bad"
        name = "Bad"
        domain = "test"
        summary = "An output with a precision of its own and no unit."
        params = (Param("value", "X", "Value", L, default="1 in"),)
        outputs = (Output("row", "R", "Row", L, precision=Precision(6)),)
        methods = (Method("only", "Only", "R", Verification.UNVERIFIED),)

        def compute(self, ctx: object) -> None:  # pragma: no cover - never run
            raise AssertionError(ctx)

    with pytest.raises(SpecError, match="output 'row' gives a precision but no unit"):
        Bad.validate_spec()


def test_a_radian_is_180_over_pi_degrees_to_every_digit_copied() -> None:
    """A radian of 57.2958° would still show 57.2958°; the full copy gives it away."""
    assert _copied(AngleConverter(), "1 rad", "deg", CopyForm.FULL) == "57.29577951"
    assert _copied(AngleConverter(), "180", "rad", CopyForm.FULL) == "3.141592654"
    assert convert(1, get_unit("rad"), get_unit("deg")) == pytest.approx(180 / math.pi, rel=1e-15)


def test_an_errors_work_line_shows_its_sign_as_its_row_does() -> None:
    from caddcalc.core.formatting import render_step

    calc = LengthConverter()
    cases = (("0.31 in", "+0.0025 in"), ("0.315 in", "-0.0025 in"), ("0.3125 in", "0.0000 in"))
    for typed, shown in cases:
        result = calc.run({"value": parse_quantity(typed, L)})
        step = next(s for s in result.steps if s.symbol == "E16")
        assert step.signed and render_step(step, result, DisplayPrefs())[2] == shown, typed
    n16 = next(s for s in result.steps if s.symbol == "N16")
    assert not n16.signed and render_step(n16, result, DisplayPrefs())[2] == "0.3125 in"
    assert "signed" not in result.to_dict()["steps"][0], "JSON's shape is unchanged"


def test_the_tsv_keeps_a_plus_value_a_number_and_full_precision_drops_the_plus() -> None:
    """A "+0.002500" cell pastes as a number, so it isn't quoted as text."""
    from caddcalc.core.formatting import results_tsv

    calc = LengthConverter()
    result = calc.run({"value": parse_quantity("0.31 in", L)})
    rows = results_tsv(calc, result, DisplayPrefs()).splitlines()
    row = next(r for r in rows if r.startswith("E16"))
    assert row.split("\t")[2] == "+0.002500", row
    assert _copied(calc, "0.31 in", "error_16", CopyForm.FULL) == "0.0025"
    assert _copied(calc, "0.31 in", "error_16", CopyForm.VALUE) == "+0.002500"
