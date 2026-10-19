"""A field picked in a unit or form reads its text in it (ADR-0024 D7, E2, E3).

The figures are the ADR's: ``1-3/16`` is 1 3/16, ``1 - 3/16`` is 13/16, and a plain
number reads bit for bit as ``parse_quantity`` reads it in that unit.
"""

from __future__ import annotations

import random
from fractions import Fraction

import pytest

import tests.test_units_identity as identity
from caddcalc.core import InputError, TypedValue, UsageError
from caddcalc.core.units import (
    Dimension,
    UnitInTextError,
    evaluate,
    parse_quantity,
    registry,
    units_for,
)
from caddcalc.core.units.entry import MAX_DEPTH, MAX_LENGTH, read

L, A, R, C = Dimension.LENGTH, Dimension.ANGLE, Dimension.RATIO, Dimension.COUNT
IN = Fraction("25.4")


def value(text: str, choice: str, dimension: Dimension = L, decimal: str = ".") -> float:
    return read(text, choice, dimension, decimal=decimal)[0]


def plain_choices() -> list[tuple[str, Dimension]]:
    """Every unit a field can be picked in, with its dimension."""
    return [
        (choice, d)
        for d in Dimension
        for choice in registry().entry_choices(d)
        if not registry().compounds_for(d)
        or choice not in {f.key for f in registry().compounds_for(d)}
    ]


@pytest.mark.parametrize(("choice", "dimension"), plain_choices())
def test_a_plain_number_reads_bit_for_bit_as_parse_quantity(
    choice: str, dimension: Dimension
) -> None:
    """Every number form of ADR-0019's identity corpus, in every unit a field takes."""
    for text in identity.NUMBERS:
        try:
            expected: float | str = parse_quantity(text, dimension, choice)
        except InputError as exc:
            expected = str(exc)  # a count's "1-1/2": both refuse it, in the same words
        try:
            got: float | str = value(text, choice, dimension)
        except InputError as exc:
            got = str(exc)
        assert got == expected, (text, choice)


def test_random_decimals_and_fractions_read_bit_for_bit_as_parse_quantity() -> None:
    rng = random.Random("entry identity")
    for _ in range(20_000):
        digits = rng.randrange(1, 18)
        text = f"{rng.randrange(10**digits) / 10 ** rng.randrange(0, digits + 1)!r}"
        if rng.random() < 0.3:
            text = f"{rng.randrange(1, 100)}/{rng.choice([2, 4, 8, 16, 32, 64, 3, 7])}"
        if rng.random() < 0.2:
            text = f"{rng.randrange(0, 100)} {rng.randrange(1, 15)}/16"
        for choice in ("in", "mm", "ft", "m"):
            assert value(text, choice) == parse_quantity(text, L, choice), (text, choice)


@pytest.mark.parametrize(
    ("text", "inches"),
    [
        ("1-3/16", Fraction(19, 16)),
        ("1 3/16", Fraction(19, 16)),
        ("1 - 3/16", Fraction(13, 16)),
        ("1 -3/16", Fraction(13, 16)),
        ("1- 3/16", Fraction(13, 16)),
        ("2-1", Fraction(1)),
        ("1-0.1875", Fraction(13, 16)),
        ("1-5/4", Fraction(-1, 4)),
        ("2 × 1 3/16", Fraction(19, 8)),
        ("2*1-3/16", Fraction(19, 8)),
        ("1 3/16 × 2", Fraction(19, 8)),
        ("-1-3/16", Fraction(-19, 16)),
        ("-1 3/16", Fraction(-19, 16)),
        ("2-1-3/16", Fraction(13, 16)),
        ("1/3*3", Fraction(1)),
        ("(1 + 2) × 3 ÷ 4", Fraction(9, 4)),
        ("10 − 2", Fraction(8)),
        ("0.1+0.2", Fraction(3, 10)),
        ("+2.5", Fraction(5, 2)),
        ("-(3)", Fraction(-3)),
        ("2*-3", Fraction(-6)),
        ("1e3", Fraction(1000)),
        (".5", Fraction(1, 2)),
    ],
)
def test_arithmetic_is_exact_with_the_mixed_number_rule(text: str, inches: Fraction) -> None:
    """A hyphen joins only with no space around it and a proper fraction after it."""
    assert evaluate(text) == inches
    assert value(text, "in") == float(inches) * 25.4, "rounded once in the unit, then the factor"


def test_a_value_is_rounded_once_in_its_unit() -> None:
    """0.1 + 0.2 is 0.3, never the doubles' 0.30000000000000004."""
    assert value("0.1+0.2", "mm") == 0.3 and 0.1 + 0.2 != 0.3
    assert value("1/3*3", "in") == 25.4
    # In its unit first, then the factor, as parse_quantity does: 3/16 in is the double
    # nearest 0.1875 × 25.4's product, not the double nearest 4.7625 exactly.
    assert value("3/16", "in") == parse_quantity("3/16 in", L) == 0.1875 * 25.4
    assert value("3/16", "in") == pytest.approx(4.7625, abs=1e-15)


@pytest.mark.parametrize(
    ("text", "inches"),
    [
        ("10-2", 122),
        ("10-2 3/16", Fraction(122) + Fraction(3, 16)),
        ("10-2-3/16", Fraction(122) + Fraction(3, 16)),
        ("10 2 3/16", Fraction(122) + Fraction(3, 16)),
        ("10'-2 3/16\"", Fraction(122) + Fraction(3, 16)),
        ("10′-2 3/16″", Fraction(122) + Fraction(3, 16)),
        ("10 ft 2 in", 122),
        ("10'", 120),
        ("10'2", 122),
        ("-10-2", -122),
        ("−10-2", -122),
        ("+10-2", 122),
        ("10", 10),
        ('10"', 10),
        ("30", 30),
        ("1-3/16", Fraction(19, 16)),
        ("1 3/16", Fraction(19, 16)),
        ("1-5/4", Fraction(12) + Fraction(5, 4)),
        ("10-11.5", Fraction(263, 2)),
        ("3/16", Fraction(3, 16)),
    ],
)
def test_feet_and_inches_read_with_their_marks_optional(text: str, inches: Fraction) -> None:
    """A bare number is inches, as AutoCAD reads one (Q2); a mixed number joins first."""
    assert value(text, "ft_in") == parse_quantity(f"{float(inches)!r} in", L)


@pytest.mark.parametrize(
    ("text", "why"),
    [
        ("10-12", "has 12 inches; give inches under 12"),
        ("1'12", "has 12 inches; give inches under 12"),
        ("10-+2", "isn't feet and inches"),
        ("10-2-", "isn't feet and inches"),
        ("10--2", "isn't feet and inches"),
        ("10 -2", "isn't feet and inches"),
        ("1.5-2", "isn't feet and inches"),
        ("10-2 3", "isn't feet and inches"),
        ("10-2,5", "has a comma"),
    ],
)
def test_feet_and_inches_refuse_what_their_grammar_doesnt_hold(text: str, why: str) -> None:
    """One sign, at the front; whole feet; inches after feet under 12."""
    with pytest.raises(InputError, match=why):
        read(text, "ft_in", L)


@pytest.mark.parametrize(
    ("text", "degrees"),
    [
        ("40 30 15", Fraction(40) + Fraction(30, 60) + Fraction(15, 3600)),
        ("40 30 15.5", Fraction(40) + Fraction(30, 60) + Fraction(155, 36000)),
        ("40°30′15″", Fraction(40) + Fraction(30, 60) + Fraction(15, 3600)),
        ("40d30'15\"", Fraction(40) + Fraction(30, 60) + Fraction(15, 3600)),
        ("40°30", Fraction(81, 2)),
        ("40 30", Fraction(81, 2)),
        ("40", Fraction(40)),
        ("30′", Fraction(1, 2)),
        ("-40 30 15", -(Fraction(40) + Fraction(30, 60) + Fraction(15, 3600))),
    ],
)
def test_degrees_minutes_and_seconds_read_with_their_marks_optional(
    text: str, degrees: Fraction
) -> None:
    assert value(text, "dms", A) == float(degrees)
    assert value("40 30 15", "dms", A) == pytest.approx(40.504166666666667, abs=1e-14)


@pytest.mark.parametrize(
    ("text", "why"),
    [
        ("40 60", "a part of 60 or more"),
        ("40 30 60", "a part of 60 or more"),
        ("40.5", "pick ° for decimal degrees"),
        ("40 30.5 15", "a decimal before its seconds"),
        ("30′ 40°", "isn't degrees, minutes and seconds"),
        ("40 -30", "isn't degrees, minutes and seconds"),
        ("40 30 15 2", "isn't degrees, minutes and seconds"),
    ],
)
def test_degrees_minutes_and_seconds_refuse_what_their_grammar_doesnt_hold(
    text: str, why: str
) -> None:
    with pytest.raises(InputError, match=why):
        read(text, "dms", A)


@pytest.mark.parametrize(
    ("text", "why"),
    [
        ("0x10", "names and units aren't read here"),
        ("1j", "names and units aren't read here"),
        ("inf", "names and units aren't read here"),
        ("sqrt(2)", "names and units aren't read here"),
        ("1_0", "digits aren't grouped"),
        ("1/0", "can't divide by zero"),
        ("1 3/0", "can't divide by zero"),
        ("2/(1-1)", "can't divide by zero"),
        ("--3", "two signs in a row"),
        ("2--3", "two signs in a row"),
        ("2**3", "isn't a number or arithmetic"),
        ("2(3)", "two numbers with nothing between them"),
        ("1/2 1/4", "two numbers with nothing between them"),
        ("2 3", "two numbers with nothing between them"),
        ("(2", "isn't closed"),
        ("2)", "isn't a number or arithmetic"),
        ("1-1/2-", "ends before its last number"),
        ("", "Cannot read a value"),
        ("1.2.3", "more than one decimal mark"),
        ("1,5", "has a comma"),
        ("1e99999999", "too large a number to calculate with"),
        ("1e400", "too large a number to calculate with"),
    ],
)
def test_text_that_isnt_arithmetic_is_refused(text: str, why: str) -> None:
    with pytest.raises(InputError, match=why):
        read(text, "in", L)


def test_a_text_is_bounded_in_length_depth_and_size() -> None:
    read("1" + "+1" * ((MAX_LENGTH - 1) // 2), "in", L)
    with pytest.raises(InputError, match=f"longer than {MAX_LENGTH} characters"):
        read("1" + "+1" * (MAX_LENGTH // 2), "in", L)
    read("(" * MAX_DEPTH + "1" + ")" * MAX_DEPTH, "in", L)
    with pytest.raises(InputError, match=f"nests deeper than {MAX_DEPTH}"):
        read("(" * (MAX_DEPTH + 1) + "1" + ")" * (MAX_DEPTH + 1), "in", L)
    with pytest.raises(InputError, match="too large a number"):
        read("*".join(["1e9999"] * 4), "in", L)
    with pytest.raises(InputError, match="too large to calculate with: its size in mm"):
        read("1e308", "ft", L)


@pytest.mark.parametrize(
    ("text", "choice", "dimension", "fix", "number"),
    [
        ("3 mm", "in", L, "mm", "3"),
        ("3mm", "in", L, "mm", "3"),
        ("3 in", "in", L, "in", "3"),
        ('1-3/16"', "in", L, "in", "1-3/16"),
        ("2 × 3 mm", "in", L, "mm", "2 × 3"),
        ("5'9", "in", L, "ft_in", "5'9"),
        ("1'-4 3/16\"", "mm", L, "ft_in", "1'-4 3/16\""),
        ("3 mm", "ft_in", L, "mm", "3"),
        ("90°", "rad", A, "deg", "90"),
        ("40°30′15″", "deg", A, "dms", "40°30′15″"),
        ("44 %", "", R, "", "0.44"),
        ("3 in + 2 in", "in", L, None, ""),
    ],
)
def test_a_unit_in_the_text_is_refused_with_its_fix(
    text: str, choice: str, dimension: Dimension, fix: str | None, number: str
) -> None:
    """Even the picked unit: the picker is the one author (ADR-0024 Q5)."""
    with pytest.raises(UnitInTextError) as refused:
        read(text, choice, dimension)
    assert (refused.value.choice, refused.value.number) == (fix, number)
    if fix:
        if number == text:
            assert f"pick {refused.value.shown} and type it there" in str(refused.value)
        elif fix != "":
            assert str(refused.value).endswith(f"pick {refused.value.shown} and type {number}")
        fixed = read(number, fix, dimension)[0]
        if text in ("3 mm", "3mm", "3 in", '1-3/16"', "90°", "44 %", "40°30′15″"):
            assert fixed == pytest.approx(parse_quantity(text, dimension), rel=1e-15)


@pytest.mark.parametrize(
    ("text", "dimension", "why"),
    [
        ("25 MPa", L, "'25 MPa' is a stress, but a length is expected"),
        ("600 %", C, "'600 %' is a ratio, but a count is expected"),
        ("3 deg", L, "'3 deg' is an angle, but a length is expected"),
    ],
)
def test_a_unit_of_another_dimension_is_refused_with_no_offer(
    text: str, dimension: Dimension, why: str
) -> None:
    with pytest.raises(InputError) as refused:
        read(text, registry().entry_choices(dimension)[0], dimension)
    assert str(refused.value) == why and not isinstance(refused.value, UnitInTextError)


def test_a_count_reads_whole_and_under_2_to_the_53() -> None:
    assert value("6", "", C) == 6.0 and value("12/2", "", C) == 6.0
    with pytest.raises(InputError, match="isn't a whole number"):
        read("6 1/2", "", C)
    with pytest.raises(InputError, match="too large a count"):
        read("2*4503599627370496", "", C)


def test_the_locale_decimal_mark_is_read_besides_the_point() -> None:
    for text in ("0,5", "1,25", "0.5"):
        assert value(text, "in", decimal=",") == parse_quantity(text, L, "in", decimal=",")
    assert evaluate("1,5+0.5", ",") == 2
    assert value("10-2,5", "ft_in", decimal=",") == parse_quantity("122.5 in", L)
    assert value("40 30 7,5", "dms", A, decimal=",") == value("40 30 7.5", "dms", A)
    with pytest.raises(InputError, match="more than one decimal mark"):
        read("1,2.5", "in", L, decimal=",")


def test_a_shown_only_form_or_another_dimensions_choice_isnt_a_field_choice() -> None:
    with pytest.raises(UsageError, match="'in_16' is shown only"):
        read("3/16", "in_16", L)
    with pytest.raises(UsageError, match="isn't a choice for length"):
        read("3", "deg", L)


def test_a_typed_value_keeps_its_text_and_its_pick() -> None:
    typed = TypedValue.read(" 2 × 1 3/16 ", "in", L)
    assert (typed.text, typed.choice, typed.unit.symbol, typed.explicit_unit) == (
        "2 × 1 3/16",
        "in",
        "in",
        False,
    )
    assert typed.value == float(Fraction(19, 8)) * 25.4
    form = TypedValue.read("10-2", "ft_in", L)
    assert (form.choice, form.unit.symbol, form.value) == ("ft_in", "in", 122 * 25.4)
    with pytest.raises(UsageError, match="doesn't read as"):
        TypedValue(1.0, "10-2", form.unit, False, ".", "ft_in")
    with pytest.raises(UnitInTextError):
        TypedValue.read("3 mm", "in", L)
    parsed = TypedValue.parse("3 mm", L)
    assert (parsed.choice, parsed.explicit_unit) == ("", True)


def test_every_unit_of_every_dimension_a_field_takes_is_a_choice() -> None:
    for dimension in (L, A, Dimension.STRESS, Dimension.AREA):
        symbols = {u.symbol for u in units_for(dimension)}
        assert symbols <= set(registry().entry_choices(dimension))
