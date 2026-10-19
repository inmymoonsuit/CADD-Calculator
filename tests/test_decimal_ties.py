"""A decimal half rounds to even in every unit it's shown in (KI-028, resolved).

A value typed as a decimal half in one unit, converted, lands a little off the half in
another; the shown text rounds it as the half it was typed as, half to even, as the inch
fractions round theirs (``formatting.round_tie``).
"""

from __future__ import annotations

import math
from decimal import ROUND_HALF_EVEN, Decimal
from fractions import Fraction

import pytest

from caddcalc.calculators.geometry import Circle
from caddcalc.core import Dimension
from caddcalc.core.formatting import DisplayPrefs, ShownUnits, format_output, format_value
from caddcalc.core.units import TypedValue

L = Dimension.LENGTH
PREFS = DisplayPrefs()
PLACES = 4
"""A length's decimal places, in every set."""


def _even(exact: Fraction, places: int) -> str:
    """The exact value rounded to ``places``, half to even: what a tie must show."""
    shown = Decimal(exact.numerator) / Decimal(exact.denominator)
    return format(shown.quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_EVEN), "f")


SWEEP = 4000
"""Decimal halves a pair is checked at, spread over sizes."""


@pytest.mark.parametrize(
    ("shown_in", "typed_in", "factor", "outside"),
    [
        ("cm", "mm", Fraction(10), 0),
        ("m", "mm", Fraction(1000), 0),
        ("mm", "cm", Fraction(1, 10), 0),
        ("in", "mm", Fraction(254, 10), 0),
        ("ft", "mm", Fraction(3048, 10), 0),
        ("ft", "in", Fraction(12), 50),
        ("m", "in", Fraction(10000, 254), 5),
    ],
)
def test_every_decimal_half_typed_in_another_unit_shows_to_even(
    shown_in: str, typed_in: str, factor: Fraction, outside: int
) -> None:
    """Each half, typed as the exact decimal it is in another unit, shows to even.

    Where three roundings put it more than ``TIE_ULPS`` of its own last places off the
    half, it rounds as its value does: 50 of 4,000 halves typed in inches and shown in
    feet, and 5 typed in inches and shown in metres (KI-030).
    """
    from caddcalc.core.units import from_base
    from caddcalc.core.units.compound import TIE_ULPS

    units = ShownUnits.generated(shown_in)
    missed = 0
    for k in range(SWEEP):
        half = Fraction(2 * k + 1, 2 * 10**PLACES) * (1 + k // 50)
        typed = half * factor
        exact = Decimal(typed.numerator) / Decimal(typed.denominator)
        if exact != Decimal(typed.numerator) / typed.denominator or len(str(exact)) > 30:
            continue  # not a finite decimal in the unit typed
        value = TypedValue.read(format(exact, "f"), typed_in, L).value
        shown = format_value(value, L, units, PREFS)
        landed = from_base(value, shown_in)
        if abs(Fraction(landed) - half) > TIE_ULPS * Fraction(math.ulp(landed)):
            missed += 1
            continue
        assert shown == f"{_even(half, PLACES)} {shown_in}", (exact, typed_in)
    assert missed == outside


def test_the_cloud_review_s_examples() -> None:
    """A 0.5 mm circle's radius is 0.00025 m, and 1/32 in is 0.79375 mm, both halves."""
    result = Circle().run({"diameter": 0.5}, "diameter")
    radius = Circle.output("radius")
    assert format_output(radius, result.outputs["radius"], ShownUnits.generated("m"), PREFS) == (
        "0.0002 m"
    )
    one_32 = TypedValue.read("1/32", "in", L).value
    assert format_value(one_32, L, ShownUnits.generated("mm"), PREFS) == "0.7938 mm"
    assert format_value(49.92751, L, ShownUnits.generated("in"), PREFS) == "1.9656 in", "KI-028's"


def test_a_value_off_a_half_by_more_than_its_last_places_rounds_as_it_is() -> None:
    """Three of its own last places off a half isn't one: it rounds as its value does."""
    from caddcalc.core.formatting import format_number

    half = 0.00025
    assert format_number(half, 4) == "0.0002"
    above = half + 3 * math.ulp(half)
    assert format_number(above, 4) == "0.0003", "rounded as it is: up"
    below = half - 3 * math.ulp(half)
    assert format_number(below, 4) == "0.0002"


def test_a_value_coarser_than_its_places_is_never_all_ties() -> None:
    """Past 2^52, a double's last place is a whole step: the cap keeps it from being a half."""
    from caddcalc.core.formatting import format_number

    assert format_number(2.0**53 - 1, 0) == "9007199254740991"
    assert format_number(-(2.0**53 - 1), 0) == "-9007199254740991"
