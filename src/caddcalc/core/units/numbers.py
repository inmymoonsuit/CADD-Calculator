"""Reading the number in what people type: decimals and drafting fractions (ADR-0005).

Standard library only. It knows no units: ``units.parsing`` finds the unit, and the
compound forms (``units.compound``) the parts, and each reads its numbers here.
"""

from __future__ import annotations

import math
import re
from decimal import Decimal
from fractions import Fraction

from caddcalc.core.errors import InputError

_MIXED = re.compile(r"([-+]?)(\d+)[\s-]+(\d+)/(\d+)")
_FRACTION = re.compile(r"([-+]?)(\d+)/(\d+)")


MINUS_SIGN = "\u2212"
"""U+2212, the minus sign: it's read as ``-`` (ADR-0020 §4)."""


def comma_error(text: str, decimal: str) -> InputError:
    """The error for ``text`` with a comma where the decimal mark is ``decimal``, not ","."""
    return InputError(
        f"{text!r} has a comma, which isn't a decimal mark here: the decimal mark is "
        f"{decimal!r}, and digits aren't grouped"
    )


def parse_number(text: str, decimal: str = ".") -> float:
    """Parse a decimal or drafting-style fraction: ``0.1046``, ``1/8``, ``1-1/2``, ``1 1/2``.

    The decimal mark is ``"."`` or ``decimal``, the locale's, and a number has one at
    most. Digits are never grouped, so ``1.234`` is 1.234 in every locale, and a comma
    that isn't the locale's mark is refused, never read as grouping (ADR-0020 §4).

    A fraction or mixed number is exact, rounded once, and zero has one sign, +0.0, so
    ``-0`` and ``-0/16`` read as ``0``: as a field picked in a unit reads them
    (``core.units.entry``), bit for bit.

    Raises:
        InputError: The text isn't a number.
    """
    s = text.strip().replace(MINUS_SIGN, "-")
    if decimal != ".":
        if s.count(".") + s.count(decimal) > 1:
            raise InputError(f"{text!r} has more than one decimal mark; digits aren't grouped")
        s = s.replace(decimal, ".")
    if "," in s:
        raise comma_error(text, decimal)
    if "_" in s:
        raise InputError(f"{text!r} is not a number; digits aren't grouped")
    for pattern in (_MIXED, _FRACTION):
        m = pattern.fullmatch(s)
        if m:
            groups = m.groups()
            sign = -1.0 if groups[0] == "-" else 1.0
            numbers = [int(g) for g in groups[1:]]
            den = numbers[-1]
            if den == 0:
                raise InputError(f"Fraction {text!r} has a zero denominator")
            whole = numbers[0] if len(numbers) == 3 else 0
            # Exactly, then rounded once: 3 78/100 is the double nearest 3.78, as a
            # picked field reads it (ADR-0024 E2), not 3 + 0.78 rounded twice.
            exact = Fraction(whole) + Fraction(numbers[-2], den)
            return float(exact if sign > 0 else -exact)
    try:
        value = float(s)
    except ValueError:
        raise InputError(f"{text!r} is not a number") from None
    if math.isnan(value) or s.lstrip("+-").lower().startswith(("inf", "nan")):
        raise InputError(f"{text!r} is not a finite number")
    if not math.isfinite(value):
        raise InputError(f"{text!r} is too large a number to calculate with")
    return value + 0.0  # "-0" is 0.0: zero has one sign, as an exact value's has


_EXACT = re.compile(
    r"(?P<whole>\d+)(?P<join>[ -])(?P<numerator>\d+)/(?P<denominator>\d+)"
    r"|(?P<top>\d+)/(?P<bottom>\d+)"
    r"|(?P<decimal>\d+(?:\.\d*)?|\.\d+)"
)


def exact_number(text: str, decimal: str = ".") -> Fraction:
    """Read an unsigned number exactly: ``3``, ``0.1046``, ``3/16``, ``1 3/16``, ``1-3/16``.

    It's a part of a compound form typed into its own field, such as the inches of
    feet and inches, so it takes no sign and no exponent. A mixed number's fraction is
    proper, as AutoCAD's mixed-number rule has it (ADR-0024 D7); the decimal mark is
    ``"."`` or ``decimal``.

    Raises:
        InputError: The text isn't such a number, or a fraction has a zero denominator.
    """
    if decimal == "." and "," in text:
        raise comma_error(text, decimal)
    m = _EXACT.fullmatch(text.replace(decimal, ".") if decimal != "." else text)
    if m is None:
        raise InputError(f"{text!r} is not a number")
    if m["decimal"] is not None:
        return Fraction(Decimal(m["decimal"]))
    top, bottom = (m["numerator"], m["denominator"]) if m["whole"] else (m["top"], m["bottom"])
    if int(bottom) == 0:
        raise InputError(f"Fraction {text!r} has a zero denominator")
    fraction = Fraction(int(top), int(bottom))
    if m["whole"] is None:
        return fraction
    if fraction >= 1:
        raise InputError(f"{text!r} has an improper fraction after its whole number")
    return int(m["whole"]) + fraction
