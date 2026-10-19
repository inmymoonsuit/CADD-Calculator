"""Reading the number in what people type: decimals and drafting fractions (ADR-0005).

Standard library only. It knows no units: ``units.parsing`` finds the unit, and the
compound forms (``units.compound``) the parts, and each reads its numbers here.
"""

from __future__ import annotations

import math
import re

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
            return sign * (whole + numbers[-2] / den)
    try:
        value = float(s)
    except ValueError:
        raise InputError(f"{text!r} is not a number") from None
    if math.isnan(value) or s.lstrip("+-").lower().startswith(("inf", "nan")):
        raise InputError(f"{text!r} is not a finite number")
    if not math.isfinite(value):
        raise InputError(f"{text!r} is too large a number to calculate with")
    return value
