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
from decimal import Decimal
from fractions import Fraction
from functools import cache
from typing import override

from caddcalc.core.errors import InputError, UsageError
from caddcalc.core.i18n import N_, NP_, _, npgettext, npgettext_shown, pgettext
from caddcalc.core.units.builtin import INCH_MM, UNITS
from caddcalc.core.units.model import Dimension, Unit
from caddcalc.core.units.numbers import comma_error, exact_number, parse_number

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
    """Its public key, e.g. ``"ft_in"``, which an output names to be shown in it, and the
    id of its choice in a picker (ADR-0024 E1)."""
    symbol: str
    """What a closed picker shows for it, e.g. ``"ft-in"``; never translated."""
    name: str
    """Its name in a picker's open list, e.g. "feet and inches", marked for translation."""
    dimension: Dimension
    full_unit: str
    """The key symbol of the unit a full-precision copy is written in, e.g. ``"in"``."""
    fineness: int
    """How finely it's shown, in the form's own terms (each form's ``text`` says)."""
    reads: bool = False
    """Whether a field can be picked in it, to read what's typed by ``read``."""
    sets: bool = True
    """Whether a generated output set shows lengths in it (``registry.generated_sets``)."""

    def read(self, text: str, decimal: str = ".") -> Fraction:
        """Return a field's ``text``, picked in this form, exactly, in ``full_unit``.

        A picked field's grammar is the form's, with its marks optional, since the picker
        says what the parts are (ADR-0024 E2). ``text`` has its spaces run together and
        stripped, and its minus signs read as ``-``.

        Raises:
            InputError: The text isn't written in the form.
            UsageError: The form reads nothing (``reads`` is false).
        """
        del text, decimal  # a form that reads overrides this
        raise UsageError(f"{self.key!r} is shown only; a field can't be picked in it")

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


TIE_ULPS = 2
"""How many units in the last place of a value, so counted, a count may be from a half and
still be taken as that half (``round_half_even``)."""
TIE_CAP = Fraction(1, 4)
"""The most a count may be from a half and be taken as it, whatever the value's units in
the last place: under half a count, so a value too large to hold the finest part is never
all ties."""


def round_half_even(value: float, scale: Fraction, unit: Fraction = Fraction(1)) -> int:
    """Return ``|value| · scale`` rounded to a whole number once, half to even.

    ``scale`` counts a value in a form's finest part, such as sixteenths of an inch, and
    ``unit`` is the size of the unit it's shown in, in the value's own, such as
    ``INCH_MM`` for a base-unit length shown in inches. A value typed as a half-way one, as
    3/32 in is between 1/16 and 1/8, is a double already, rounded once as typed and again
    into the base unit, as 0.12779375 m is, so it lands a little off the half, one way or
    the other. A count within ``TIE_ULPS`` units in the last place of the value in the
    shown unit, so counted, of a half, and never more than ``TIE_CAP``, is taken as that
    half, and rounds to even whichever way it landed. The shown unit is the one a value is
    typed in, when it's typed as shown, so a value three of its own last places off a
    half isn't one (ADR-0019, amendments).
    """
    parts = abs(Fraction(value)) * scale
    half = Fraction(math.floor(parts)) + Fraction(1, 2)
    last_place = Fraction(math.ulp(value / unit)) * unit
    if abs(parts - half) <= min(TIE_ULPS * last_place * scale, TIE_CAP):
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
# Translators: feet and a fraction of an inch under one, said together, e.g. "1 foot" and
# "a quarter inch" as "1 foot and a quarter inch".
FEET_AND_FRACTION_SPOKEN = N_("{feet} and {fraction}")
# Translators: a negative value, spoken, e.g. "minus 1 foot 4 inches".
NEGATIVE_SPOKEN = N_("minus {value}")
# Translators: a value shown with its plus sign, spoken, e.g. "plus 0.0025 inches", as an
# error is, so its direction is heard as it's seen.
POSITIVE_SPOKEN = N_("plus {value}")
# Translators: a mixed number of inches, spoken, e.g. "4 and 3 sixteenths inches"; {part}
# is the fraction's denominator as a word, such as "sixteenths". The form follows the
# whole value as a decimal, 4.1875, so English's two forms are the same.
INCHES_MIXED_SPOKEN = NP_(
    "inches spoken",
    "{inches} and {numerator} {part} inches",
    "{inches} and {numerator} {part} inches",
)
# Translators: a fraction of an inch, spoken, e.g. "3 sixteenths of an inch".
INCH_FRACTION_SPOKEN = N_("{numerator} {part} of an inch")


def _measure(number: str, unit: Unit) -> str:
    """Return a number and its unit's name as spoken, e.g. "4 inches"."""
    return _(MEASURE_SPOKEN).format(number=number, unit=unit.spoken(number))


def _said(measures: list[str], negative: bool) -> str:
    """Return a value's spoken measures said together, and as negative if it is."""
    text = _listed(measures)
    return _(NEGATIVE_SPOKEN).format(value=text) if negative else text


def _listed(measures: list[str]) -> str:
    """Join spoken measures by CLDR's unit list patterns: two, or start, middle and end.

    Three measures are ``start(first, end(second, third))``, as CLDR's list patterns
    build a list (Unicode TR35, Part 2, "List Patterns"), so a language can put ", "
    between the earlier ones and its "and" only before the last.
    """
    if len(measures) == 1:
        return measures[0]
    if len(measures) == 2:
        # Translators: two spoken measures of one value, e.g. "1 foot 4 inches" or "40
        # degrees 30 minutes": CLDR's unit list pattern for two.
        return pgettext("unit list, two", "{first} {second}").format(
            first=measures[0], second=measures[1]
        )
    # Translators: the last two of three or more spoken measures of one value, e.g. "30
    # minutes 15 seconds" in "40 degrees 30 minutes 15 seconds": CLDR's "end" pattern.
    text = pgettext("unit list, end", "{first} {second}").format(
        first=measures[-2], second=measures[-1]
    )
    for measure in reversed(measures[1:-2]):
        # Translators: a spoken measure before the last two, CLDR's "middle" pattern.
        text = pgettext("unit list, middle", "{first} {second}").format(first=measure, second=text)
    # Translators: the first of three or more spoken measures and the rest, e.g. "40
    # degrees" and "30 minutes 15 seconds": CLDR's "start" pattern.
    return pgettext("unit list, start", "{first} {second}").format(first=measures[0], second=text)


PARTS = {
    2: NP_("fraction", "half", "halves"),
    4: NP_("fraction", "quarter", "quarters"),
    8: NP_("fraction", "eighth", "eighths"),
    16: NP_("fraction", "sixteenth", "sixteenths"),
    32: NP_("fraction", "thirty-second", "thirty-seconds"),
    64: NP_("fraction", "sixty-fourth", "sixty-fourths"),
}
"""The words for an inch fraction's denominator, singular and plural, as spoken."""

# Each is a whole phrase, so a language can give each part its own article or form, and a
# plural pair, whose form follows the whole value as a decimal, as 1.25 for "1 and a
# quarter inches"; a decimal takes English's plural, so its two forms are the same.
ONE_PART_SPOKEN = {
    # Translators: whole inches and 1/2 inch, spoken, e.g. "1 and a half inches".
    2: NP_("inches spoken", "{inches} and a half inches", "{inches} and a half inches"),
    # Translators: whole inches and 1/4 inch, spoken, e.g. "1 and a quarter inches".
    4: NP_("inches spoken", "{inches} and a quarter inches", "{inches} and a quarter inches"),
    # Translators: whole inches and 1/8 inch, spoken, e.g. "1 and an eighth inches".
    8: NP_("inches spoken", "{inches} and an eighth inches", "{inches} and an eighth inches"),
    # Translators: whole inches and 1/16 inch, spoken, e.g. "1 and a sixteenth inches".
    16: NP_("inches spoken", "{inches} and a sixteenth inches", "{inches} and a sixteenth inches"),
    # Translators: whole inches and 1/32 inch, spoken, e.g. "1 and a thirty-second inches".
    32: NP_(
        "inches spoken",
        "{inches} and a thirty-second inches",
        "{inches} and a thirty-second inches",
    ),
    # Translators: whole inches and 1/64 inch, spoken, e.g. "1 and a sixty-fourth inches".
    64: NP_(
        "inches spoken",
        "{inches} and a sixty-fourth inches",
        "{inches} and a sixty-fourth inches",
    ),
}
"""Whole inches and one 1/2, 1/4 and so on, as they're said: "1 and a quarter inches",
not "1 and 1 quarter inches"."""

ONE_PART_ALONE_SPOKEN = {
    # Translators: 1/2 inch alone, spoken.
    2: N_("a half inch"),
    # Translators: 1/4 inch alone, spoken.
    4: N_("a quarter inch"),
    # Translators: 1/8 inch alone, spoken.
    8: N_("an eighth inch"),
    # Translators: 1/16 inch alone, spoken.
    16: N_("a sixteenth inch"),
    # Translators: 1/32 inch alone, spoken.
    32: N_("a thirty-second inch"),
    # Translators: 1/64 inch alone, spoken.
    64: N_("a sixty-fourth inch"),
}
"""One 1/2, 1/4 and so on alone, as they're said, consistent with ``ONE_PART_SPOKEN``:
"a quarter inch", not "1 quarter of an inch"."""


FEET_INCHES_NAMES = {
    # Translators: a picker's choice for a length, as 1'-4 3/16".
    16: N_("feet and inches"),
    # Translators: a picker's choice for lengths shown in feet and inches to 1/32 inch.
    32: N_("feet and inches, nearest 1/32"),
    # Translators: a picker's choice for lengths shown in feet and inches to 1/64 inch.
    64: N_("feet and inches, nearest 1/64"),
}
"""Each feet-and-inches form's name in a picker's list, by its fineness."""

NEAREST_INCH_NAMES = {
    # Translators: a picker's choice for lengths shown as the nearest 1/16 inch.
    16: N_("inches, nearest 1/16"),
    # Translators: a picker's choice for lengths shown as the nearest 1/32 inch.
    32: N_("inches, nearest 1/32"),
    # Translators: a picker's choice for lengths shown as the nearest 1/64 inch.
    64: N_("inches, nearest 1/64"),
}
"""Each nearest-inch form's name in a picker's list, by its fineness."""


class FeetInches(CompoundForm):
    """Feet and inches, the drafter's way: shown ``1'-4 3/16"``, copied ``1'4-3/16"``.

    The shown form is AutoCAD's report form and the copied one its input form, which
    takes no spaces (ADR-0019 U3). Both always give the feet and the inches, ``0'-4"``
    and ``2'-0"``. Its ``fineness`` is the inch fraction's denominator: a power of two
    up to 64, or 1 for whole inches.
    """

    key = "ft_in"
    symbol = "ft-in"
    name = FEET_INCHES_NAMES[16]
    dimension = Dimension.LENGTH
    full_unit = "in"
    reads = True

    def __init__(self, fineness: int = 16) -> None:
        if fineness != 1 and fineness not in PARTS:
            raise UsageError(f"Feet and inches are shown to 1, or 1/2 to 1/64, not 1/{fineness}")
        self.fineness = fineness
        if fineness != 16:
            # A field reads any fraction typed, so only the 1/16 form, the default, is a
            # field's choice and a generated set's; a finer one is for a declared set.
            self.key, self.symbol = f"ft_in_{fineness}", f"ft-in 1/{fineness}"
            self.name = FEET_INCHES_NAMES.get(fineness, FEET_INCHES_NAMES[16])
            self.reads = self.sets = False

    @override
    def parse(self, text: str, decimal: str = ".") -> float | None:
        strict, attempt = _feet_inches_patterns()
        m = strict.fullmatch(text)
        if (m is not None or attempt.match(text)) and "," in text and decimal != ",":
            raise comma_error(text, decimal)  # the whole value, not just its inches
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
    def read(self, text: str, decimal: str = ".") -> Fraction:
        """Read feet and inches with their marks optional: ``10-2 3/16`` and ``10'-2 3/16"``.

        A bare number is inches, as AutoCAD reads one (ADR-0024 Q2), of any size; a whole
        number and a proper fraction are a mixed number of inches, ``1-3/16`` and
        ``1 3/16``. Feet are whole, and the inches after them under 12. One sign, at the
        front.
        """
        if not self.reads:
            return super().read(text, decimal)  # a finer one is shown only
        if decimal == "." and "," in text:
            raise comma_error(text, decimal)
        sign, body = (text[0], text[1:]) if text[:1] in ("-", "+") else ("", text)
        bare, marked, unmarked = _feet_inches_picked()
        for pattern in (bare, marked, unmarked):
            m = pattern.fullmatch(body)
            if m is None:
                continue
            try:
                inches = exact_number(m["inches"], decimal) if m["inches"] else Fraction(0)
            except InputError:
                continue  # an improper fraction after a whole number: the next reading
            feet = int(m["feet"]) if "feet" in m.groupdict() and m["feet"] else 0
            if pattern is not bare and inches >= 12:
                raise InputError(f"{text!r} has {m['inches']} inches; give inches under 12")
            return -(feet * 12 + inches) if sign == "-" else feet * 12 + inches
        raise InputError(
            f"{text!r} isn't feet and inches: give whole feet, then the inches, as 10-2 3/16 "
            "or 10'-2 3/16\", or the inches alone; one sign, at the front"
        )

    @override
    def text(self, value: float, decimal: str = ".") -> CompoundText:
        if not math.isfinite(value):
            raise UsageError(f"{value} can't be written in feet and inches")
        den = self.fineness
        units = round_half_even(value, den / INCH_MM, INCH_MM)
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
    if feet and inches and not whole:
        # Feet and a fraction alone are joined by "and": "1 foot and a quarter inch".
        joined = _(FEET_AND_FRACTION_SPOKEN).format(feet=measures[0], fraction=inches)
        return _said([joined], negative)
    if inches:
        measures.append(inches)
    return _said(measures or [_measure("0", _builtin("in"))], negative)


def _spoken_inches(whole: int, fraction: Fraction) -> str:
    """Say whole inches and a fraction in words, or return ``""`` for none.

    For example "4 and 3 sixteenths inches", "4 and a half inches", "3 sixteenths of an
    inch", "a quarter inch", or "4 inches".
    """
    if not fraction:
        return _measure(str(whole), _builtin("in")) if whole else ""
    singular, plural = PARTS[fraction.denominator]
    numerator = fraction.numerator
    part = npgettext("fraction", singular, plural, numerator)
    # The phrase's form follows the whole value, as a decimal: a power-of-two fraction's
    # is exact, as 4.1875 is.
    decimal = str(Decimal(whole) + Decimal(numerator) / Decimal(fraction.denominator))
    if whole and numerator == 1:
        template = npgettext_shown("inches spoken", *ONE_PART_SPOKEN[fraction.denominator], decimal)
        return template.format(inches=whole)
    if whole:
        template = npgettext_shown("inches spoken", *INCHES_MIXED_SPOKEN, decimal)
        return template.format(inches=whole, numerator=numerator, part=part)
    if numerator == 1:
        return _(ONE_PART_ALONE_SPOKEN[fraction.denominator])
    return _(INCH_FRACTION_SPOKEN).format(numerator=numerator, part=part)


@cache
def _feet_inches_picked() -> tuple[re.Pattern[str], re.Pattern[str], re.Pattern[str]]:
    """A picked field's readings of feet and inches, tried in turn.

    They're the inches alone, feet with their mark, and feet and inches without marks,
    joined by a hyphen or a space.
    """
    feet, inches = _marks(_builtin("ft")), _marks(_builtin("in"))
    number = r"\d+[ -]\d+/\d+|\d+/\d+|\d+(?:[.,]\d*)?|[.,]\d+"
    mark = rf"(?: ?(?:{inches}))?"
    return (
        re.compile(rf"(?P<inches>{number}){mark}", re.IGNORECASE),
        re.compile(
            rf"(?P<feet>\d+) ?(?:{feet})(?: ?-? ?(?P<inches>{number}){mark})?", re.IGNORECASE
        ),
        re.compile(rf"(?P<feet>\d+)[ -](?P<inches>{number}){mark}", re.IGNORECASE),
    )


@cache
def _feet_inches_patterns() -> tuple[re.Pattern[str], re.Pattern[str]]:
    """The form's pattern, and the start of anything written as an attempt at it."""
    feet, inches = _marks(_builtin("ft")), _marks(_builtin("in"))
    number = r"\d+(?:[ -]\d+/\d+)?|\d+/\d+|\d*[.,]\d+|\d+[.,]?"
    strict = re.compile(
        rf"(?P<sign>[-+]?)(?P<feet>\d+) ?(?:{feet}) ?-? ?(?P<inches>{number}) ?(?:{inches})",
        re.IGNORECASE,
    )
    # An attempt has inches, or a sign, after the feet: "5'9" and "1'--4\"" are attempts,
    # but "3 ft." is a number misread.
    attempt = re.compile(rf"[-+]?\d+ ?(?:{feet}) ?-? ?(?:\d|[.,]\d|[-+])", re.IGNORECASE)
    return strict, attempt


class DegreesMinutesSeconds(CompoundForm):
    """Degrees, minutes and seconds: shown ``40°30′15.00″``, copied ``40d30'15.00"``.

    The copied form is the one AutoCAD takes for an angle in degrees, minutes and
    seconds, with ``d`` for the degree, which a keyboard has. One sign is written, before
    the degrees, and zero is never ``-0°0′0.00″``. Its ``fineness`` is the seconds'
    decimal places.
    """

    key = "dms"
    symbol = "° ′ ″"
    # Translators: a picker's choice for an angle, as 40°30′15″.
    name = N_("degrees, minutes and seconds")
    dimension = Dimension.ANGLE
    full_unit = "deg"
    reads = True

    def __init__(self, fineness: int = 2) -> None:
        if not 0 <= fineness <= 6:
            raise UsageError(f"Seconds are shown to 0 to 6 decimals, not {fineness}")
        self.fineness = fineness

    @override
    def parse(self, text: str, decimal: str = ".") -> float | None:
        strict, attempt = _dms_patterns()
        m = strict.fullmatch(text)
        given = 0 if m is None else sum(m[g] is not None for g in ("d", "m", "s"))
        written = (m is not None and given >= 2) or attempt.search(text)
        if written and "," in text and decimal != ",":
            raise comma_error(text, decimal)  # ADR-0020 §4's why, for the whole value
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
    def read(self, text: str, decimal: str = ".") -> Fraction:
        """Read degrees, minutes and seconds with their marks optional: ``40 30 15``.

        An unmarked part is the one after the last, so ``40°30`` is 40°30′; marks go in
        order. Degrees and minutes are whole, seconds may have decimals, and minutes and
        seconds are under 60. One sign, at the front.
        """
        if decimal == "." and "," in text:
            raise comma_error(text, decimal)
        sign, body = (text[0], text[1:]) if text[:1] in ("-", "+") else ("", text)
        part, kinds = _dms_picked()
        parts: list[str | None] = [None, None, None]
        at = slot = 0
        while at < len(body):
            m = part.match(body, at)
            mark = None if m is None else next((k for k in kinds if m[k]), None)
            index = slot if m is None or mark is None else kinds.index(mark)
            if m is None or index < slot or index > 2:
                raise InputError(
                    f"{text!r} isn't degrees, minutes and seconds: give whole degrees and "
                    "minutes, then seconds, as 40 30 15 or 40°30′15″; one sign, at the front"
                )
            parts[index], slot, at = m["number"], index + 1, m.end()
        degrees, minutes, seconds = (
            exact_number(p, decimal) if p is not None else Fraction(0) for p in parts
        )
        if degrees.denominator != 1 or minutes.denominator != 1:
            raise InputError(
                f"{text!r} has a decimal before its seconds: give whole degrees and minutes, "
                "or pick ° for decimal degrees"
            )
        if minutes >= 60 or seconds >= 60:
            raise InputError(
                f"{text!r} has a part of 60 or more; give minutes and seconds under 60"
            )
        value = degrees + minutes / 60 + seconds / 3600
        return -value if sign == "-" else value

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
def _dms_picked() -> tuple[re.Pattern[str], tuple[str, str, str]]:
    """A picked field's part of degrees, minutes and seconds, and its marks' groups.

    A part is a number and its mark, if it has one; the groups are in the parts' order.
    """
    degree = _marks(_builtin("deg")) + "|d"
    minute, second = _marks(_builtin("arcmin")), _marks(_builtin("arcsec"))
    part = re.compile(
        rf"(?P<number>\d+(?:[.,]\d*)?|[.,]\d+) ?(?:(?P<d>{degree})|(?P<m>{minute})|"
        rf"(?P<s>{second}))? ?",
        re.IGNORECASE,
    )
    return part, ("d", "m", "s")


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
    return Fraction(sign * round_half_even(value, denominator / INCH_MM, INCH_MM), denominator)


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
        self.symbol = f"in 1/{fineness}"
        self.name = NEAREST_INCH_NAMES.get(fineness, NEAREST_INCH_NAMES[16])

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
    NearestInches(16),
    NearestInches(32),
    NearestInches(64),
    FeetInches(),
    FeetInches(32),
    FeetInches(64),
    DegreesMinutesSeconds(),
)
"""The built-in compound forms: the nearest 1/16, 1/32 and 1/64 inch; feet and inches to
1/16, 1/32 and 1/64 inch; and degrees, minutes and seconds to hundredths of a second. A
picker lists a dimension's forms after their full unit, in this order (ADR-0024 §1)."""
