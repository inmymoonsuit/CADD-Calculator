"""Compound forms: feet and inches, and degrees, minutes and seconds (ADR-0019 §2, U3)."""

from __future__ import annotations

import math
import random
import re
from decimal import Decimal
from fractions import Fraction
from pathlib import Path
from typing import Any, override

import pytest

from caddcalc.core import (
    Calculator,
    Context,
    Domain,
    InputError,
    Method,
    Output,
    Param,
    Registry,
    SpecError,
    TypedValue,
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
    entry_text,
    format_output,
    output_parts,
    results_tsv,
    spoken_value,
    to_fraction,
    value_parts,
)
from caddcalc.core.i18n import use
from caddcalc.core.units import (
    CompoundText,
    Dimension,
    Precision,
    from_base,
    parse_quantity,
    parse_quantity_detailed,
    registry,
)
from caddcalc.core.units.compound import DegreesMinutesSeconds, FeetInches, nearest_inches
from tests.catalogs import shipped

L, A = Dimension.LENGTH, Dimension.ANGLE
IN = 25.4


def _inches(text: str, decimal: str = ".") -> float:
    return parse_quantity(text, L, decimal=decimal) / IN


@pytest.mark.parametrize(
    "typed",
    [
        "1'-4 3/16\"",
        "1'-4-3/16\"",
        "1'4-3/16\"",
        "1' 4 3/16\"",
        "1′ 4 3/16″",
        "1 ft 4 3/16 in",
        "1 FT 4 3/16 IN",
        "1 foot 4 3/16 inches",
        "1'  -  4 3/16\"",
        "1'-4.1875\"",
        "+1'-4 3/16\"",
    ],
)
def test_feet_and_inches_read_in_every_common_form(typed: str) -> None:
    """U3: AutoCAD's report and input forms, the spaced and prime forms, and words."""
    parsed = parse_quantity_detailed(typed, L)
    assert parsed.value / IN == pytest.approx(16.1875)
    assert (parsed.unit.symbol, parsed.explicit_unit) == ("in", True)


@pytest.mark.parametrize(
    ("typed", "inches"),
    [
        ("1'-4\"", 16),
        ("1'4\"", 16),
        ("1 ft 4 in", 16),
        ("0'-4\"", 4),
        ("2'-0\"", 24),
        ("1'-0 3/16\"", 12.1875),
        ("1'-3/16\"", 12.1875),
        ("-1'-4 3/16\"", -16.1875),
        ("−1'-4\"", -16),
        ("10'-11 63/64\"", 131.984375),
    ],
)
def test_feet_and_inches_read_whole_inches_fractions_and_one_sign(
    typed: str, inches: float
) -> None:
    assert _inches(typed) == pytest.approx(inches)


def test_feet_and_inches_take_the_locales_decimal_mark() -> None:
    assert _inches("1'-4,5\"", ",") == pytest.approx(16.5)
    assert _inches("1'-4.5\"", ",") == pytest.approx(16.5), "and '.' in any locale"
    with pytest.raises(InputError, match="has a comma"):
        _inches("1'-4,5\"")


@pytest.mark.parametrize(
    ("typed", "problem"),
    [
        ("1'-12\"", "has 12 inches; give inches under 12"),
        ("1'-13 1/2\"", "has 13 1/2 inches"),
        ("1'-4", "isn't feet and inches"),
        ("3 ft 4", "isn't feet and inches"),
        ("1.5'-4\"", "is not a number"),
        ("1'--4\"", "isn't feet and inches"),
        ("1'-+4\"", "isn't feet and inches"),
        ("1'-4 3/0\"", "zero denominator"),
    ],
)
def test_feet_and_inches_refuse_parts_that_dont_fit(typed: str, problem: str) -> None:
    with pytest.raises(InputError, match=problem):
        parse_quantity(typed, L)


def test_a_typed_feet_and_inches_keeps_its_text_and_reads_it_again() -> None:
    typed = TypedValue.parse("1'-4 3/16\"", L)
    assert typed.value == pytest.approx(16.1875 * IN) and typed.explicit_unit
    assert entry_text(typed, DisplayPrefs(length_unit="mm")) == "1'-4 3/16\"", "as typed"


@pytest.mark.parametrize(
    ("inches", "shown", "copied"),
    [
        (16.1875, "1'-4 3/16\"", "1'4-3/16\""),
        (16, "1'-4\"", "1'4\""),
        (12.1875, "1'-0 3/16\"", "1'0-3/16\""),
        (4.5, "0'-4 1/2\"", "0'4-1/2\""),
        (23 + 63 / 64, "2'-0\"", "2'0\""),
        (11.99, "1'-0\"", "1'0\""),
        (-16.1875, "-1'-4 3/16\"", "-1'4-3/16\""),
        (-0.001, "0'-0\"", "0'0\""),
        (0.0, "0'-0\"", "0'0\""),
        (100 * 12 + 0.03125, "100'-0\"", "100'0\""),
        (100 * 12 + 0.1, "100'-0 1/8\"", "100'0-1/8\""),
    ],
)
def test_feet_and_inches_show_and_copy_and_rounding_carries(
    inches: float, shown: str, copied: str
) -> None:
    """1'-11 63/64" at 1/16 is 2'-0", never 1'-12"; zero never "-0'-0"."""
    text = FeetInches(16).text(inches * IN)
    assert (text.shown, text.copied) == (shown, copied)


@pytest.mark.parametrize(
    ("typed", "denominator", "nearest"),
    [
        ("3/32 in", 16, Fraction(1, 8)),
        ("7/32 in", 16, Fraction(1, 4)),
        ("5/32 in", 16, Fraction(1, 8)),
        ("3/128 in", 64, Fraction(1, 32)),
        ("-3/32 in", 16, Fraction(-1, 8)),
        ("2.38125 mm", 16, Fraction(1, 8)),  # 3/32 in, typed in mm
        ("5.55625 mm", 16, Fraction(1, 4)),  # 7/32 in
    ],
)
def test_a_value_half_way_between_two_fractions_takes_the_even_one(
    typed: str, denominator: int, nearest: Fraction
) -> None:
    """3/32 in is half-way from 1/16 to 1/8 in; as a double it lands either side of it."""
    value = parse_quantity(typed, L)
    assert nearest_inches(value, denominator) == nearest
    if denominator == 16:
        shown = FeetInches(16).text(value).shown
        assert shown.endswith(f' {abs(nearest)}"') and shown.startswith("-" * (nearest < 0))


@pytest.mark.parametrize("denominator", [16, 32, 64])
@pytest.mark.parametrize("unit", ["in", "mm"])
def test_every_half_way_value_takes_the_even_fraction(denominator: int, unit: str) -> None:
    """Each odd 1/(2d) inch to 4 ft, typed in inches or exactly in mm, either sign.

    The nearest fraction, feet and inches, the ``(≈ …")`` hint and ``to_fraction`` all
    round by one rule, so they agree on every tie (the reviews' Major 5).
    """
    prefs = DisplayPrefs(length_unit="in", fraction_denominator=denominator)
    for odd in range(1, 4 * 12 * 2 * denominator, 2):
        half = Fraction(odd, 2 * denominator)
        text = (
            f"{half} in"
            if unit == "in"
            else f"{Decimal(half.numerator) * Decimal('25.4') / half.denominator} mm"
        )
        expected = Fraction(round(half * denominator), denominator)  # half to even, exactly
        for sign in (1, -1):
            value = sign * parse_quantity(text, L)
            assert nearest_inches(value, denominator) == sign * expected, (sign, text)
            hint = _copied_fraction(sign * expected)
            assert value_parts(value, L, prefs).fraction == hint, (sign, text)
            assert to_fraction(from_base(value, "in"), denominator) == hint, (sign, text)
            if denominator == 16:
                again = parse_quantity(FeetInches(16).text(value).copied, L)
                assert nearest_inches(again, 16) == sign * expected, (sign, text)


def _copied_fraction(inches: Fraction) -> str:
    """An inch fraction as the hint writes it, e.g. ``1-1/8`` or ``-3/16``."""
    whole, part = divmod(abs(inches), 1)
    text = "-".join(t for t in (str(whole) if whole else "", str(part) if part else "") if t)
    return ("-" if inches < 0 else "") + (text or "0")


@pytest.mark.parametrize(("seconds", "shown"), [(0.005, "0.00"), (0.015, "0.02"), (0.025, "0.02")])
def test_half_way_seconds_take_the_even_hundredth(seconds: float, shown: str) -> None:
    typed = parse_quantity(f"0°0′{seconds}″", A)
    assert DegreesMinutesSeconds(2).text(typed).shown == f"0°0′{shown}″"


def test_a_fineness_is_a_drafting_fraction_and_whole_inches_have_none() -> None:
    assert FeetInches(1).text(16.6 * IN).shown == "1'-5\""
    assert FeetInches(64).text(16.015625 * IN).shown == "1'-4 1/64\""
    assert FeetInches(2).text(16.8 * IN).shown == "1'-5\"", "16.8 to the half is 17"
    for bad in (0, 3, 10, 128):
        with pytest.raises(UsageError, match="1, or 1/2 to 1/64"):
            FeetInches(bad)


@pytest.mark.parametrize(
    ("inches", "spoken"),
    [
        (16.1875, "1 foot 4 and 3 sixteenths inches"),
        (16, "1 foot 4 inches"),
        (13, "1 foot 1 inch"),
        (24, "2 feet"),
        (4, "4 inches"),
        (1, "1 inch"),
        (0, "0 inches"),
        (0.1875, "3 sixteenths of an inch"),
        (4.5, "4 and a half inches"),
        (1.25, "1 and a quarter inches"),
        (1.5, "1 and a half inches"),
        (1.0625, "1 and a sixteenth inches"),
        (0.5, "a half inch"),
        (0.25, "a quarter inch"),
        (12.25, "1 foot and a quarter inch"),
        (12.1875, "1 foot and 3 sixteenths of an inch"),
        (12.0625, "1 foot and a sixteenth inch"),
        (16.5, "1 foot 4 and a half inches"),
        (16.75, "1 foot 4 and 3 quarters inches"),
        (16.125, "1 foot 4 and an eighth inches"),
        (-16.1875, "minus 1 foot 4 and 3 sixteenths inches"),
        (-4, "minus 4 inches"),
        (-0.001, "0 inches"),
    ],
)
def test_feet_and_inches_are_spoken_in_words(inches: float, spoken: str) -> None:
    """A zero part isn't said, and a negative is "minus" (UI/UX's u3 L2 and L3)."""
    assert FeetInches(16).text(inches * IN).spoken == spoken


def test_the_finest_fractions_have_their_words() -> None:
    assert FeetInches(32).text(12.03125 * IN).spoken == "1 foot and a thirty-second inch"
    assert FeetInches(64).text(12.046875 * IN).spoken == "1 foot and 3 sixty-fourths of an inch"
    assert FeetInches(32).text(13.03125 * IN).spoken == "1 foot 1 and a thirty-second inches"
    assert FeetInches(64).text(1.015625 * IN).spoken == "1 and a sixty-fourth inches"


@pytest.mark.parametrize(
    ("typed", "degrees"),
    [
        ("40°30′15″", 40 + 30 / 60 + 15 / 3600),
        ("40°30'15\"", 40 + 30 / 60 + 15 / 3600),
        ("40° 30′ 15.5″", 40 + 30 / 60 + 15.5 / 3600),
        ("40d30'15.5\"", 40 + 30 / 60 + 15.5 / 3600),
        ("40 deg 30 arcmin", 40.5),
        ("40 degrees 30 minutes 15 seconds", 40 + 30 / 60 + 15 / 3600),
        ("40°30′", 40.5),
        ("40°15″", 40 + 15 / 3600),
        ("30′15″", 30 / 60 + 15 / 3600),
        ("1'4\"", 1 / 60 + 4 / 3600),
        ("-0°30′", -0.5),
        ("−0°30′", -0.5),
        ("+0°30′", 0.5),
        ("400°0′", 400),
        ("0°0′59.999″", 59.999 / 3600),
    ],
)
def test_degrees_minutes_and_seconds_read_with_one_sign(typed: str, degrees: float) -> None:
    parsed = parse_quantity_detailed(typed, A)
    assert parsed.value == pytest.approx(degrees, abs=1e-12)
    assert (parsed.unit.symbol, parsed.explicit_unit) == ("deg", True)


def test_seconds_take_the_locales_decimal_mark() -> None:
    assert parse_quantity("0°0′15,5″", A, decimal=",") == pytest.approx(15.5 / 3600)
    with pytest.raises(InputError, match="has a comma"):
        parse_quantity("0°0′15,5″", A)


@pytest.mark.parametrize(
    ("typed", "problem"),
    [
        ("40°60′", "a part of 60 or more"),
        ("40°30′60″", "a part of 60 or more"),
        ("40°75′15″", "a part of 60 or more"),
        ("40.5°30′", "isn't degrees, minutes and seconds"),
        ("40°30.5′", "isn't degrees, minutes and seconds"),
        ("-1°-30′", "isn't degrees, minutes and seconds"),
        ("40°-30′", "isn't degrees, minutes and seconds"),
        ("40°30′15", "isn't degrees, minutes and seconds"),
        ("30″15′", "isn't degrees, minutes and seconds"),
        ("1'-4\"", "isn't degrees, minutes and seconds"),
    ],
)
def test_degrees_minutes_and_seconds_refuse_parts_that_dont_fit(typed: str, problem: str) -> None:
    """Whole degrees and minutes, minutes and seconds in [0, 60), in order, one sign."""
    with pytest.raises(InputError, match=problem):
        parse_quantity(typed, A)


def test_one_part_alone_is_a_plain_unit_and_marks_are_feet_and_inches_elsewhere() -> None:
    """In an angle, ′ and ″ are minutes and seconds; everywhere else, the foot and inch."""
    assert parse_quantity("40.5°", A) == 40.5
    assert parse_quantity("90′", A) == pytest.approx(1.5), "90 minutes, not a DMS form"
    assert parse_quantity("30″", A) == pytest.approx(30 / 3600)
    assert parse_quantity("3′", L) == pytest.approx(3 * 12 * IN)
    assert parse_quantity('3"', L) == pytest.approx(3 * IN)
    for dimension in (Dimension.RATIO, Dimension.STRESS, Dimension.AREA):
        with pytest.raises(InputError, match="is a length, but"):
            parse_quantity("3′", dimension)
    with pytest.raises(InputError, match="is not a number"):
        parse_quantity("40°30′", L), "a DMS form is only an angle's"


@pytest.mark.parametrize(
    ("degrees", "fineness", "shown", "copied"),
    [
        (40 + 30 / 60 + 15 / 3600, 2, "40°30′15.00″", "40d30'15.00\""),
        (29.99999999, 2, "30°0′0.00″", "30d0'0.00\""),
        (-0.5, 2, "-0°30′0.00″", "-0d30'0.00\""),
        (-1e-9, 2, "0°0′0.00″", "0d0'0.00\""),
        (0.0, 2, "0°0′0.00″", "0d0'0.00\""),
        (40 + 30 / 60 + 59.96 / 3600, 1, "40°31′0.0″", "40d31'0.0\""),
        (359.9999999, 0, "360°0′0″", "360d0'0\""),
        (-123.456789, 3, "-123°27′24.440″", "-123d27'24.440\""),
    ],
)
def test_degrees_minutes_and_seconds_show_carry_and_keep_their_sign(
    degrees: float, fineness: int, shown: str, copied: str
) -> None:
    """29.99999999° reads 30°0′0.00″; −0.5° reads -0°30′0.00″; zero is never -0°."""
    text = DegreesMinutesSeconds(fineness).text(degrees)
    assert (text.shown, text.copied) == (shown, copied)
    assert parse_quantity(text.copied, A) == pytest.approx(degrees, abs=0.6 / 10**fineness / 3600)


def test_seconds_are_shown_in_the_locales_mark_and_copied_with_a_point() -> None:
    text = DegreesMinutesSeconds(2).text(40.5 + 15.25 / 3600, ",")
    assert (text.shown, text.copied) == ("40°30′15,25″", "40d30'15.25\"")
    assert text.spoken == "40 degrees 30 minutes 15,25 seconds"
    with pytest.raises(UsageError, match="0 to 6 decimals"):
        DegreesMinutesSeconds(7)


@pytest.mark.parametrize(
    ("degrees", "fineness", "spoken"),
    [
        (40 + 30 / 60 + 15 / 3600, 2, "40 degrees 30 minutes 15.00 seconds"),
        (1 + 1 / 60, 2, "1 degree 1 minute"),
        (1 + 1 / 60 + 1 / 3600, 0, "1 degree 1 minute 1 second"),
        (1 + 1 / 3600, 0, "1 degree 1 second"),
        (90, 2, "90 degrees"),
        (-0.5, 2, "minus 30 minutes"),
        (-15.5 / 3600, 1, "minus 15.5 seconds"),
        (0.0, 2, "0 degrees"),
        (-1e-9, 2, "0 degrees"),
    ],
)
def test_degrees_minutes_and_seconds_are_spoken_in_words(
    degrees: float, fineness: int, spoken: str
) -> None:
    """A zero part isn't said, and a negative is "minus" (UI/UX's u3 L2 and L3)."""
    assert DegreesMinutesSeconds(fineness).text(degrees).spoken == spoken


def test_the_forms_are_registered_for_their_dimensions_only() -> None:
    units = registry()
    assert [f.key for f in units.compounds_for(L)] == ["ft_in", "in_16", "in_32", "in_64"]
    assert [f.key for f in units.compounds_for(A)] == ["dms"]
    assert units.compounds_for(Dimension.AREA) == ()
    assert (units.compound("ft_in").fineness, units.compound("dms").fineness) == (16, 2)
    with pytest.raises(UsageError, match="No compound form 'chains'"):
        units.compound("chains")


def test_registering_a_form_is_checked() -> None:
    from caddcalc.core.units import UnitRegistry, builtin

    test = UnitRegistry(builtin.DIMENSIONS)
    for unit in builtin.UNITS:
        test.register(unit)
    test.register_compound(FeetInches())
    with pytest.raises(SpecError, match="the key is taken"):
        test.register_compound(FeetInches(64))

    class Furlongs(FeetInches):
        key = "fur"
        full_unit = "deg"

    with pytest.raises(SpecError, match="'deg' isn't a length unit"):
        test.register_compound(Furlongs())
    test.freeze()
    with pytest.raises(UsageError, match="frozen"):
        test.register_compound(DegreesMinutesSeconds())


class _Forms(Calculator):
    """A test converter with rows in compound forms."""

    id = "test.forms"
    name = "Forms"
    domain = "test"
    summary = "Shows a length in feet and inches and an angle in DMS."
    params = (
        Param("length", "X", "Length", L, default="16.1875 in"),
        Param("angle", "B", "Angle", A, default="-0.5"),
    )
    outputs = (
        Output("ft_in", "FI", "Feet and inches", L, form="ft_in"),
        Output("dms", "D", "Degrees, minutes, seconds", A, form="dms"),
        Output("negative", "N", "Negative", L, form="ft_in"),
    )
    methods = (Method("only", "Only", "Rows", Verification.UNVERIFIED),)

    @override
    def compute(self, ctx: Context) -> None:
        ctx.calc("FI", "X", label="Feet and inches", dimension=L, output="ft_in")
        ctx.calc("D", "B", label="DMS", dimension=A, output="dms")
        ctx.calc("N", "-X", label="Negative", dimension=L, output="negative")


def test_an_output_in_a_compound_form_is_shown_copied_and_spoken_in_it() -> None:
    calc = _Forms()
    result = calc.run()
    out = calc.output("ft_in")
    prefs = DisplayPrefs(length_unit="mm", symbols=NumberSymbols(","))
    parts = output_parts(out, result.outputs["ft_in"], prefs)
    expected = CompoundText("1'-4 3/16\"", "1'4-3/16\"", "1 foot 4 and 3 sixteenths inches")
    assert parts == ValueParts("1'-4 3/16\"", "", None, expected)
    assert format_output(out, result.outputs["ft_in"], prefs) == "1'-4 3/16\""
    assert spoken_value(parts) == "1 foot 4 and 3 sixteenths inches"
    copies = {
        form: copy_output(out, result.outputs["ft_in"], prefs, form)
        for form in CopyForm
        if form is not CopyForm.FRACTION
    }
    assert copies == {
        CopyForm.VALUE: "1'4-3/16\"",
        CopyForm.SHOWN: "1'-4 3/16\"",
        CopyForm.WITH_UNIT: "1'4-3/16\"",
        CopyForm.FULL: "16.1875",
    }
    with pytest.raises(UsageError, match="without a fraction"):
        copy_output(out, result.outputs["ft_in"], prefs, CopyForm.FRACTION)
    dms = output_parts(calc.output("dms"), result.outputs["dms"], prefs)
    assert dms.number == "-0°30′0,00″" and dms.unit == ""
    assert copy_output(calc.output("dms"), -0.5, prefs, CopyForm.VALUE) == "-0d30'0.00\""


def test_copy_all_keeps_a_compound_value_from_being_read_as_a_formula() -> None:
    calc = _Forms()
    rows = results_tsv(calc, calc.run(), DisplayPrefs()).splitlines()
    assert rows == [
        "FI\tFeet and inches\t1'-4 3/16\"\t",
        "D\tDegrees, minutes, seconds\t'-0°30′0.00″\t",
        "N\tNegative\t'-1'-4 3/16\"\t",
    ]


@pytest.mark.parametrize(
    ("changes", "problem"),
    [
        ({"form": "chains"}, "has a bad form: No compound form 'chains'"),
        ({"form": "dms"}, "form 'dms' doesn't write a length"),
        ({"form": "ft_in", "unit": "in"}, "gives a unit and a form; give one"),
        ({"form": "ft_in", "precision": Precision(6)}, "gives a precision and a form"),
        ({"form": "ft_in", "signed": True}, "is signed and in a form"),
    ],
)
def test_an_output_naming_a_form_it_cant_be_shown_in_is_a_definition_error(
    changes: dict[str, Any], problem: str
) -> None:
    class Bad(_Forms):
        outputs = (Output("ft_in", "FI", "Feet and inches", L, **changes),)

    with pytest.raises(SpecError, match=problem):
        Bad.validate_spec()


@pytest.mark.parametrize(
    ("tag", "inches", "spoken"),
    [
        ("en_GB", 16.1875, "1 foot 4 and 3 sixteenths inches"),
        ("en_GB", 12.1875, "1 foot and 3 sixteenths of an inch"),
        ("en_CA", 24, "2 feet"),
        ("en_GB", -4, "minus 4 inches"),
    ],
)
def test_the_spoken_forms_are_marked_and_read_from_the_catalogs(
    tmp_path: Path, tag: str, inches: float, spoken: str
) -> None:
    use([tag], directories=[shipped(shipped(tmp_path, "en_001"), "en_CA")])
    assert FeetInches().text(inches * IN).spoken == spoken
    assert DegreesMinutesSeconds().text(1.5).spoken == "1 degree 30 minutes"


TEST = Domain("test", "Test", "A domain for tests.")


@pytest.mark.gui
@pytest.mark.usefixtures("qt")
def test_a_result_field_shows_copies_and_says_a_compound_form_with_no_code_of_its_own() -> None:
    from PySide6.QtGui import QGuiApplication

    from caddcalc.gui.window import MainWindow

    calculators = Registry()
    calculators.register_domain(TEST)
    calculators.register(_Forms)
    window = MainWindow(registry=calculators, symbols=POINT)
    window.select_calculator("test.forms")
    fields = window.results.fields
    feet, dms = fields["ft_in"], fields["dms"]
    assert (feet.value.text(), feet.unit.text()) == ("1'-4 3/16\"", "")
    assert (dms.value.text(), dms.unit.text()) == ("-0°30′0.00″", "")
    assert feet.accessibleName() == "Feet and inches, FI: 1 foot 4 and 3 sixteenths inches"
    feet.copy_button.click()
    assert QGuiApplication.clipboard().text() == "1'4-3/16\""
    # A compound form names its own units, so "with unit" would copy the same text, and
    # its full precision is a decimal in the form's own unit, which the item names.
    for units in ("in", "mm"):
        window.units_box.setCurrentText(units)
        feet, dms = window.results.fields["ft_in"], window.results.fields["dms"]
        for field, unit, full in ((feet, "inches", "16.1875"), (dms, "degrees", "-0.5")):
            menu = field.context_menu()
            assert [a.text() for a in menu.actions()] == [
                "Copy value",
                f"Copy full precision, in {unit}",
            ], units
            menu.actions()[1].trigger()
            assert QGuiApplication.clipboard().text() == full, (units, unit)
    window.close()


class _Mixed(_Forms):
    """The compound rows beside a decimal one, for alignment."""

    id = "test.mixed"
    outputs = (*_Forms.outputs, Output("plain", "P", "Plain", L, unit="in"))

    @override
    def compute(self, ctx: Context) -> None:
        super().compute(ctx)
        ctx.calc("P", "X", label="Plain", dimension=L, output="plain")


@pytest.mark.gui
@pytest.mark.usefixtures("qt")
def test_feet_and_inches_sit_flush_right_and_dms_aligns_on_its_seconds_point() -> None:
    """UI/UX's u3 M1: with no point to align on, feet and inches end at the column's edge."""
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QFontMetricsF

    from caddcalc.gui.window import MainWindow

    calculators = Registry()
    calculators.register_domain(TEST)
    calculators.register(_Mixed)
    window = MainWindow(registry=calculators, symbols=POINT)
    window.select_calculator("test.mixed")
    fields = window.results.fields
    feet, dms, plain = fields["ft_in"], fields["dms"], fields["plain"]
    assert plain.value.text() == "16.1875"
    metrics = QFontMetricsF(feet.value.font())
    for field in (feet, fields["negative"]):
        assert field.value.contentsMargins().right() == 0
        assert field.value.alignment() & Qt.AlignmentFlag.AlignRight
        assert field.value.width() == plain.value.width(), "one column for every value"
        assert metrics.horizontalAdvance(field.value.text()) <= field.value.width()
    # The DMS seconds and the plain value line up on their points.
    tails = {f: metrics.horizontalAdvance(t) for f, t in ((dms, ".00″"), (plain, ".1875"))}
    most = max(tails.values())
    for field, tail in tails.items():
        assert field.value.contentsMargins().right() == round(most - tail)
    window.close()


def test_a_language_can_join_its_last_measure_by_its_own_and(tmp_path: Path) -> None:
    """CLDR's list patterns: ", " between the earlier measures, "y" only before the last."""
    from babel.messages.catalog import Catalog
    from babel.messages.mofile import write_mo

    catalog = Catalog(locale="es")
    for context, pattern in (
        ("unit list, two", "{first} y {second}"),
        ("unit list, start", "{first}, {second}"),
        ("unit list, middle", "{first}, {second}"),
        ("unit list, end", "{first} y {second}"),
    ):
        catalog.add("{first} {second}", pattern, context=context)
    path = tmp_path / "es" / "LC_MESSAGES" / "caddcalc.mo"
    path.parent.mkdir(parents=True)
    with path.open("wb") as mo:
        write_mo(mo, catalog)
    use(["es"], directories=[tmp_path])
    try:
        three = DegreesMinutesSeconds(2).text(40 + 30 / 60 + 15.25 / 3600).spoken
        assert three == "40 degrees, 30 minutes y 15.25 seconds"
        assert DegreesMinutesSeconds().text(1.5).spoken == "1 degree y 30 minutes"
        assert FeetInches().text(16 * IN).spoken == "1 foot y 4 inches"
        assert DegreesMinutesSeconds().text(40.0).spoken == "40 degrees", "one measure alone"
        from caddcalc.core.units.compound import _listed

        assert _listed(["a", "b", "c", "d"]) == "a, b, c y d", "the middle pattern"
    finally:
        use([])


@pytest.mark.parametrize(
    ("typed", "dimension"),
    [("90°30,5'", A), ("40°30′15,5″", A), ("1'4,5\"", L), ("1'-4,5\"", L), ("1'4,5\"", A)],
)
def test_a_comma_in_a_compound_form_says_why_and_quotes_the_whole_value(
    typed: str, dimension: Dimension
) -> None:
    """ADR-0020 §4's reason, for the value as typed, not a part of it."""
    message = f"{typed!r} has a comma, which isn't a decimal mark here: the decimal mark is '.'"
    with pytest.raises(InputError, match=re.escape(message)):
        parse_quantity(typed, dimension)
    if "′" in typed or ('"' in typed and dimension is L):
        assert parse_quantity(typed, dimension, decimal=",") == pytest.approx(
            parse_quantity(typed.replace(",", "."), dimension)
        ), "where the comma is the mark, it reads"


@pytest.mark.parametrize("typed", ["3 ft.", "3'.", "3 ft x"])
def test_a_foot_mark_with_no_inches_after_it_is_no_attempt_at_feet_and_inches(typed: str) -> None:
    with pytest.raises(InputError, match="is not a number"):
        parse_quantity(typed, L)


@pytest.mark.parametrize(
    ("typed", "seconds"), [("40°30′.5″", 0.5), ("40°30′,5″", 0.5), ("-1°0′.25″", 0.25)]
)
def test_seconds_may_start_with_their_decimal_mark(typed: str, seconds: float) -> None:
    sign = -1 if typed.startswith("-") else 1
    degrees = abs(float(typed.split("°")[0])) + int(typed.split("°")[1].split("′")[0]) / 60
    decimal = "," if "," in typed else "."
    assert parse_quantity(typed, A, decimal=decimal) == sign * (degrees + seconds / 3600)


@pytest.mark.parametrize("denominator", [16, 32, 64])
def test_a_tie_typed_in_metres_or_foot_fractions_takes_the_even_fraction(denominator: int) -> None:
    """Typed in metres, or as a fraction of a foot, a tie is rounded twice on its way in.

    So it can land two units in its last place off the half: 0.12779375 m is 5 1/32 in,
    which takes 5", and 317/384 ft is 9 29/32 in, which takes 9 7/8".
    """
    for odd in range(1, 4 * 12 * 2 * denominator, 2):
        half = Fraction(odd, 2 * denominator)
        expected = Fraction(round(half * denominator), denominator)
        metres = Decimal(half.numerator) * Decimal("0.0254") / half.denominator
        for text in (f"{metres} m", f"{half / 12} ft"):
            for sign in (1, -1):
                value = sign * parse_quantity(text, L)
                assert nearest_inches(value, denominator) == sign * expected, (sign, text)
    assert nearest_inches(parse_quantity("0.12779375 m", L), 16) == 5
    assert nearest_inches(parse_quantity("317/384 ft", L), 16) == Fraction(79, 8)


def test_a_tie_in_seconds_takes_the_even_hundredth() -> None:
    """Seconds typed to the thousandth, ending in 5, are ties at hundredths."""
    rng = random.Random("dms ties")
    for _ in range(20_000):
        degrees, minutes = rng.randrange(0, 360), rng.randrange(0, 60)
        thousandths = rng.randrange(0, 6000) * 10 + 5
        typed = f"{degrees}°{minutes}′{Decimal(thousandths) / 1000}″"
        hundredths = round(Fraction(thousandths, 10))  # half to even, exactly
        expected = f"{hundredths // 100}.{hundredths % 100:02d}″"
        shown = DegreesMinutesSeconds(2).text(parse_quantity(typed, A)).shown
        assert shown.endswith(f"′{expected}") or hundredths == 6000, (typed, shown)
    assert DegreesMinutesSeconds(2).text(parse_quantity("1°35′3.405″", A)).shown == "1°35′3.40″"


def test_a_count_three_units_in_the_last_place_from_a_half_is_no_tie() -> None:
    """The tolerance is two units in the last place: three is a value, not a typed tie."""
    from caddcalc.core.units.compound import TIE_ULPS

    assert TIE_ULPS == 2
    tie = parse_quantity("1/32 in", L)  # between 0 and 1/16: a tie takes 0, the even one
    scale = Fraction(16) / Fraction("25.4")
    value = tie
    while (Fraction(value) * scale - Fraction(1, 2)) / (Fraction(math.ulp(value)) * scale) < 3:
        value = math.nextafter(value, math.inf)
    assert nearest_inches(tie, 16) == 0
    assert nearest_inches(value, 16) == Fraction(1, 16), "three units over: it rounds up"


def test_a_value_too_large_for_its_finest_part_is_never_all_ties() -> None:
    """At 2³³°, a unit in the last place is more than a hundredth of a second.

    Without the cap every count would be within two of them of a half; 2⁻⁶° is exactly
    56.25″, and stays so.
    """
    from caddcalc.core.units.compound import TIE_CAP

    assert Fraction(1, 4) == TIE_CAP
    assert DegreesMinutesSeconds(2).text(2.0**33 + 2.0**-6).shown == "8589934592°0′56.25″"
