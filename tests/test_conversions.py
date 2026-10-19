"""The Conversions family: one value, in every unit of its kind at once (ADR-0018 §3)."""

from __future__ import annotations

import json
import math
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
    assert (rows["nearest_16"], rows["error_16"]) == ('5/16"', "0.002500 in")
    rows = _shown(LengthConverter(), "23.984375 in")  # 23 63/64
    assert rows["ft_in"] == "2'-0\"", "1'-11 63/64\" carries at 1/16"
    assert (rows["nearest_16"], rows["error_16"]) == ('24"', "0.015625 in")
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


def test_a_half_way_length_takes_the_even_fraction_in_every_row() -> None:
    """3/32 in is half-way from 1/16 to 1/8 in, and 7/32 in from 3/16 to 1/4 in."""
    for typed, nearest, ft_in in (
        ("3/32 in", '1/8"', "0'-0 1/8\""),
        ("7/32 in", '1/4"', "0'-0 1/4\""),
    ):
        rows = _shown(LengthConverter(), typed)
        assert (rows["nearest_16"], rows["ft_in"]) == (nearest, ft_in), typed
    assert _shown(LengthConverter(), "3/128 in")["nearest_64"] == '1/32"'
