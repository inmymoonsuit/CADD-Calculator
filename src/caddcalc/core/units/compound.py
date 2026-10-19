"""Compound forms: a value written in two or three units at once (ADR-0019 §2, U3).

Feet and inches, ``1'-4 3/16"``, is a length's; degrees, minutes and seconds,
``40°30′15.00″``, an angle's. Each form reads what people type, and writes a value three
ways: as shown, as copied, and as spoken. Rounding happens once, on the whole value in
the form's finest part, so it carries: 1'-11 63/64" to the nearest 1/16 is 2'-0", never
1'-12", and 29.99999999° to hundredths of a second is 30°0′0.00″.

Their marks are the units' own keys, so ′ and ″ are the foot and inch in a length and
the minute and second in an angle, as the units are (SP 811 Table 6).
"""

from __future__ import annotations

import math
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from fractions import Fraction
from functools import cache
from typing import override

from caddcalc.core.errors import InputError, UsageError
from caddcalc.core.i18n import N_, NP_, _, npgettext
from caddcalc.core.units.builtin import INCH_MM, UNITS
from caddcalc.core.units.model import Dimension, Unit
from caddcalc.core.units.numbers import parse_number

MINUS = "-"
"""The sign a negative value is written with: an ASCII hyphen-minus (ADR-0020 §4)."""


@dataclass(frozen=True)
class CompoundText:
    """A value in a compound form, written for each use."""

    shown: str
    """As shown on screen, e.g. ``1'-4 3/16"``, in the locale's decimal mark."""
    copied: str
    """As copied, for typing into CAD, e.g. ``1'4-3/16"``, with ``"."`` for its point."""
    spoken: str
    """As a screen reader should say it, e.g. "1 foot 4 and 3 sixteenths inches"."""


class CompoundForm(ABC):
    """A way of writing a value of one dimension in several units at once."""

    key: str
    """Its public key, e.g. ``"ft_in"``, which an output names to be shown in it."""
    dimension: Dimension
    full_unit: str
    """The key symbol of the unit a full-precision copy is written in, e.g. ``"in"``."""
    fineness: int
    """How finely it's shown, in the form's own terms (each form's ``text`` says)."""

    @abstractmethod
    def parse(self, text: str, decimal: str = ".") -> float | None:
        """Return ``text`` in base units, or ``None`` if it isn't written in this form.

        ``text`` has its spaces already run together and stripped; ``decimal`` is the
        locale's decimal mark, read besides ``"."``.

        Raises:
            InputError: The text is written in this form, but its parts don't fit it,
                such as 75 minutes.
        """

    @abstractmethod
    def text(self, value: float, decimal: str = ".") -> CompoundText:
        """Return a base-unit value written in this form, rounded once, to ``fineness``."""


def round_half_even(value: float, scale: Fraction) -> int:
    """Return ``|value| · scale`` rounded to a whole number once, half to even.

    ``scale`` counts a base-unit value in a form's finest part, such as sixteenths of an
    inch. A value typed as a half-way one, as 3/32 in is between 1/16 and 1/8, is a double
    already, so it lands a little off the half, one way or the other. A count within one
    unit in the last place of the typed value, so counted, of a half is taken as that half,
    and rounds to even whichever way it landed.
    """
    parts = abs(Fraction(value)) * scale
    half = Fraction(math.floor(parts)) + Fraction(1, 2)
    if abs(parts - half) <= Fraction(math.ulp(value)) * scale:
        parts = half
    return round(parts)


def _marks(*units: Unit) -> str:
    """Return a regular expression for any key of ``units``, longest first."""
    keys = sorted({key for unit in units for key in unit.keys}, key=len, reverse=True)
    return "|".join(re.escape(key) for key in keys)


def _builtin(symbol: str) -> Unit:
    return next(u for u in UNITS if u.symbol == symbol)


# Translators: a number and its unit, spoken, e.g. "4 inches" or "30 minutes".
MEASURE_SPOKEN = N_("{number} {unit}")
# Translators: two spoken measures of one value said together, e.g. "1 foot" and "4 inches"
# as "1 foot 4 inches", as CLDR's unit list pattern joins them.
TOGETHER_SPOKEN = N_("{first} {second}")
# Translators: a negative value, spoken, e.g. "minus 1 foot 4 inches".
NEGATIVE_SPOKEN = N_("minus {value}")
# Translators: a mixed number of inches, spoken, e.g. "4 and 3 sixteenths inches"; {part}
# is the fraction's denominator as a word, such as "sixteenths".
INCHES_MIXED_SPOKEN = N_("{inches} and {numerator} {part} inches")
# Translators: a fraction of an inch, spoken, e.g. "3 sixteenths of an inch".
INCH_FRACTION_SPOKEN = N_("{numerator} {part} of an inch")


def _measure(number: str, unit: Unit) -> str:
    """Return a number and its unit's name as spoken, e.g. "4 inches"."""
    return _(MEASURE_SPOKEN).format(number=number, unit=unit.spoken(number))


def _said(measures: list[str], negative: bool) -> str:
    """Return a value's spoken measures said together, and as negative if it is."""
    text = measures[0]
    for measure in measures[1:]:
        text = _(TOGETHER_SPOKEN).format(first=text, second=measure)
    return _(NEGATIVE_SPOKEN).format(value=text) if negative else text


PARTS = {
    2: NP_("fraction", "half", "halves"),
    4: NP_("fraction", "quarter", "quarters"),
    8: NP_("fraction", "eighth", "eighths"),
    16: NP_("fraction", "sixteenth", "sixteenths"),
    32: NP_("fraction", "thirty-second", "thirty-seconds"),
    64: NP_("fraction", "sixty-fourth", "sixty-fourths"),
}
"""The words for an inch fraction's denominator, singular and plural, as spoken."""


class FeetInches(CompoundForm):
    """Feet and inches, the drafter's way: shown ``1'-4 3/16"``, copied ``1'4-3/16"``.

    The shown form is AutoCAD's report form and the copied one its input form, which
    takes no spaces (ADR-0019 U3). Both always give the feet and the inches, ``0'-4"``
    and ``2'-0"``. Its ``fineness`` is the inch fraction's denominator: a power of two
    up to 64, or 1 for whole inches.
    """

    key = "ft_in"
    dimension = Dimension.LENGTH
    full_unit = "in"

    def __init__(self, fineness: int = 16) -> None:
        if fineness != 1 and fineness not in PARTS:
            raise UsageError(f"Feet and inches are shown to 1, or 1/2 to 1/64, not 1/{fineness}")
        self.fineness = fineness

    @override
    def parse(self, text: str, decimal: str = ".") -> float | None:
        strict, attempt = _feet_inches_patterns()
        m = strict.fullmatch(text)
        if m is None:
            if attempt.match(text):
                raise InputError(
                    f"{text!r} isn't feet and inches: give whole feet, then the inches "
                    "with their mark, as 1'-4 3/16\""
                )
            return None
        inches = parse_number(m["inches"], decimal)
        if inches >= 12:
            raise InputError(f"{text!r} has {m['inches']} inches; give inches under 12")
        sign = -1.0 if m["sign"] == "-" else 1.0
        return sign * (int(m["feet"]) * 12 + inches) * float(INCH_MM)

    @override
    def text(self, value: float, decimal: str = ".") -> CompoundText:
        if not math.isfinite(value):
            raise UsageError(f"{value} can't be written in feet and inches")
        den = self.fineness
        units = round_half_even(value, den / INCH_MM)
        sign = MINUS if value < 0 and units else ""
        feet, rest = divmod(units, 12 * den)
        whole, part = divmod(rest, den)
        fraction = Fraction(part, den)
        if fraction:
            frac = f"{fraction.numerator}/{fraction.denominator}"
            shown = f"{sign}{feet}'-{whole} {frac}\""
            copied = f"{sign}{feet}'{whole}-{frac}\""
        else:
            shown = f"{sign}{feet}'-{whole}\""
            copied = f"{sign}{feet}'{whole}\""
        return CompoundText(shown, copied, _spoken_feet(bool(sign), feet, whole, fraction))


def _spoken_feet(negative: bool, feet: int, whole: int, fraction: Fraction) -> str:
    """Say feet and inches in words, leaving out a part that's zero: "4 inches"."""
    measures = [_measure(str(feet), _builtin("ft"))] if feet else []
    inches = _spoken_inches(whole, fraction)
    if inches:
        measures.append(inches)
    return _said(measures or [_measure("0", _builtin("in"))], negative)


def _spoken_inches(whole: int, fraction: Fraction) -> str:
    """Say whole inches and a fraction in words, or return ``""`` for none.

    For example "4 and 3 sixteenths inches", "3 sixteenths of an inch", or "4 inches".
    """
    if not fraction:
        return _measure(str(whole), _builtin("in")) if whole else ""
    singular, plural = PARTS[fraction.denominator]
    numerator = fraction.numerator
    part = npgettext("fraction", singular, plural, numerator)
    if whole:
        return _(INCHES_MIXED_SPOKEN).format(inches=whole, numerator=numerator, part=part)
    return _(INCH_FRACTION_SPOKEN).format(numerator=numerator, part=part)


@cache
def _feet_inches_patterns() -> tuple[re.Pattern[str], re.Pattern[str]]:
    """The form's pattern, and the start of anything written as an attempt at it."""
    feet, inches = _marks(_builtin("ft")), _marks(_builtin("in"))
    number = r"\d+(?:[ -]\d+/\d+)?|\d+/\d+|\d*[.,]\d+|\d+[.,]?"
    strict = re.compile(
        rf"(?P<sign>[-+]?)(?P<feet>\d+) ?(?:{feet}) ?-? ?(?P<inches>{number}) ?(?:{inches})",
        re.IGNORECASE,
    )
    attempt = re.compile(rf"[-+]?\d+ ?(?:{feet}) ?-? ?\S", re.IGNORECASE)
    return strict, attempt


class DegreesMinutesSeconds(CompoundForm):
    """Degrees, minutes and seconds: shown ``40°30′15.00″``, copied ``40d30'15.00"``.

    The copied form is the one AutoCAD takes for an angle in degrees, minutes and
    seconds, with ``d`` for the degree, which a keyboard has. One sign is written, before
    the degrees, and zero is never ``-0°0′0.00″``. Its ``fineness`` is the seconds'
    decimal places.
    """

    key = "dms"
    dimension = Dimension.ANGLE
    full_unit = "deg"

    def __init__(self, fineness: int = 2) -> None:
        if not 0 <= fineness <= 6:
            raise UsageError(f"Seconds are shown to 0 to 6 decimals, not {fineness}")
        self.fineness = fineness

    @override
    def parse(self, text: str, decimal: str = ".") -> float | None:
        strict, attempt = _dms_patterns()
        m = strict.fullmatch(text)
        given = 0 if m is None else sum(m[g] is not None for g in ("d", "m", "s"))
        if m is None or given < 2:
            if attempt.search(text):
                raise InputError(
                    f"{text!r} isn't degrees, minutes and seconds: give whole degrees and "
                    "minutes, each part with its mark and one sign at the front, as "
                    "40°30′15″"
                )
            return None
        minutes = int(m["m"] or 0)
        seconds = parse_number(m["s"], decimal) if m["s"] else 0.0
        if minutes >= 60 or seconds >= 60:
            raise InputError(
                f"{text!r} has a part of 60 or more; give minutes and seconds under 60"
            )
        sign = -1.0 if m["sign"] == "-" else 1.0
        return sign * (int(m["d"] or 0) + minutes / 60 + seconds / 3600)

    @override
    def text(self, value: float, decimal: str = ".") -> CompoundText:
        if not math.isfinite(value):
            raise UsageError(f"{value} can't be written in degrees, minutes and seconds")
        scale = 10**self.fineness
        units = round_half_even(value, Fraction(3600 * scale))
        sign = MINUS if value < 0 and units else ""
        degrees, rest = divmod(units, 3600 * scale)
        minutes, rest = divmod(rest, 60 * scale)
        seconds = f"{rest // scale}.{rest % scale:0{self.fineness}d}" if scale > 1 else str(rest)
        shown = f"{sign}{degrees}°{minutes}′{seconds.replace('.', decimal)}″"
        copied = f"{sign}{degrees}d{minutes}'{seconds}\""
        degree, minute, second = _builtin("deg"), _builtin("arcmin"), _builtin("arcsec")
        measures = [_measure(str(degrees), degree)] if degrees else []
        if minutes:
            measures.append(_measure(str(minutes), minute))
        if rest:
            measures.append(_measure(seconds.replace(".", decimal), second))
        spoken = _said(measures or [_measure("0", degree)], bool(sign))
        return CompoundText(shown, copied, spoken)


@cache
def _dms_patterns() -> tuple[re.Pattern[str], re.Pattern[str]]:
    """The form's pattern, and what marks anything written as an attempt at it."""
    degree = _marks(_builtin("deg")) + "|d"
    minute, second = _marks(_builtin("arcmin")), _marks(_builtin("arcsec"))
    strict = re.compile(
        rf"(?P<sign>[-+]?)(?:(?P<d>\d+) ?(?:{degree}) ?)?(?:(?P<m>\d+) ?(?:{minute}) ?)?"
        rf"(?:(?P<s>\d+(?:[.,]\d*)?|[.,]\d+) ?(?:{second}))?",
        re.IGNORECASE,
    )
    attempt = re.compile(rf"\d ?(?:{degree}|{minute}|{second}) ?[-+]?[\d.,]", re.IGNORECASE)
    return strict, attempt


def nearest_inches(value: float, denominator: int) -> Fraction:
    """Return a base-unit length's nearest 1/``denominator`` inch, in inches, exactly.

    It's rounded once, half to even (``round_half_even``), so a value halfway between two
    fractions takes the one with the even numerator.
    """
    sign = -1 if value < 0 else 1
    return Fraction(sign * round_half_even(value, denominator / INCH_MM), denominator)


class NearestInches(CompoundForm):
    """A length as its nearest drafting fraction of an inch: ``1 3/16"`` to the 1/16.

    Shown with a space and copied with a hyphen, ``1-3/16"``, as feet and inches are
    (ADR-0019 U3), with the inch mark, so a spreadsheet can't read ``3/16`` as a date.
    Its ``fineness`` is the denominator: a power of two from 2 to 64. It reads nothing,
    since the inch's own unit reads a typed fraction.
    """

    dimension = Dimension.LENGTH
    full_unit = "in"

    def __init__(self, fineness: int) -> None:
        if fineness not in PARTS:
            raise UsageError(f"An inch fraction is 1/2 to 1/64, not 1/{fineness}")
        self.fineness = fineness
        self.key = f"in_{fineness}"

    @override
    def parse(self, text: str, decimal: str = ".") -> float | None:
        return None

    @override
    def text(self, value: float, decimal: str = ".") -> CompoundText:
        if not math.isfinite(value):
            raise UsageError(f"{value} can't be written as a fraction of an inch")
        nearest = nearest_inches(value, self.fineness)
        sign = MINUS if nearest < 0 else ""
        whole, fraction = divmod(abs(nearest), 1)
        if fraction:
            frac = f"{fraction.numerator}/{fraction.denominator}"
            shown = f'{sign}{whole} {frac}"' if whole else f'{sign}{frac}"'
            copied = f'{sign}{whole}-{frac}"' if whole else shown
        else:
            shown = copied = f'{sign}{whole}"'
        spoken = _said(
            [_spoken_inches(int(whole), fraction) or _measure("0", _builtin("in"))], bool(sign)
        )
        return CompoundText(shown, copied, spoken)


FORMS: tuple[CompoundForm, ...] = (
    FeetInches(),
    DegreesMinutesSeconds(),
    NearestInches(16),
    NearestInches(32),
    NearestInches(64),
)
"""The built-in compound forms: feet and inches to 1/16 inch, degrees, minutes and seconds
to hundredths of a second, and the nearest 1/16, 1/32 and 1/64 inch."""
