"""The units module and display rules as they were before the registry (ADR-0019 §7).

Kept only so the identity test can hold the registry to them: every parse and every
display rule must give what these gave, except psi's factor, now rounded once from its
exact definition. Not used by the app.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from enum import Enum
from typing import NamedTuple

from caddcalc.core.errors import InputError, UsageError


class Dimension(Enum):
    """What a quantity measures. Each dimension has one base unit (``BASE_UNITS``)."""

    LENGTH = "length"
    ANGLE = "angle"
    RATIO = "ratio"
    STRESS = "stress"

    @property
    def with_article(self) -> str:
        """The name with its indefinite article, for messages, e.g. ``"an angle"``."""
        return _WITH_ARTICLE[self]


_WITH_ARTICLE = {
    Dimension.LENGTH: "a length",
    Dimension.ANGLE: "an angle",
    Dimension.RATIO: "a ratio",
    Dimension.STRESS: "a stress",
}


@dataclass(frozen=True)
class Unit:
    """A unit of measure and its conversion factor to the base unit."""

    symbol: str
    name: str
    dimension: Dimension
    factor: float
    """Multiply a value in this unit by ``factor`` to get base units."""
    aliases: tuple[str, ...] = ()
    spoken_plural: str = ""
    """The unit's name for any amount but exactly one, e.g. ``"inches"``, as a screen reader
    says it (ADR-0017 §5). A unitless ratio has none: only its number is spoken."""

    def spoken(self, shown: str) -> str:
        """Return the unit's name as spoken after the number ``shown``, e.g. ``"inches"``.

        It's singular only after a shown ``1``. Any visible decimal takes the plural, as
        CLDR's English plural rule has it, so ``1.0000 in`` is "1.0000 inches".
        """
        if not self.symbol:
            return ""
        return self.name if shown.lstrip("+-") == "1" else self.spoken_plural


_PSI_IN_MPA = 0.45359237 * 9.80665 / 25.4**2
"""One pound-force per square inch in N/mm², from the exact pound, standard gravity, and
inch (NIST SP 811, Appendix B)."""

UNITS: tuple[Unit, ...] = (
    Unit(
        "mm",
        "millimetre",
        Dimension.LENGTH,
        1.0,
        ("millimeter", "millimeters", "millimetres"),
        "millimetres",
    ),
    Unit(
        "cm",
        "centimetre",
        Dimension.LENGTH,
        10.0,
        ("centimeter", "centimeters", "centimetres"),
        "centimetres",
    ),
    Unit("m", "metre", Dimension.LENGTH, 1000.0, ("meter", "meters", "metres"), "metres"),
    Unit("in", "inch", Dimension.LENGTH, 25.4, ('"', "″", "inch", "inches"), "inches"),
    Unit("ft", "foot", Dimension.LENGTH, 304.8, ("'", "′", "foot", "feet"), "feet"),
    Unit("deg", "degree", Dimension.ANGLE, 1.0, ("°", "degree", "degrees"), "degrees"),
    Unit("rad", "radian", Dimension.ANGLE, 180.0 / math.pi, ("radian", "radians"), "radians"),
    Unit("", "ratio", Dimension.RATIO, 1.0),
    Unit("%", "percent", Dimension.RATIO, 0.01, ("percent",), "percent"),
    Unit("MPa", "megapascal", Dimension.STRESS, 1.0, ("megapascal", "megapascals"), "megapascals"),
    Unit(
        "kPa", "kilopascal", Dimension.STRESS, 0.001, ("kilopascal", "kilopascals"), "kilopascals"
    ),
    Unit(
        "GPa", "gigapascal", Dimension.STRESS, 1000.0, ("gigapascal", "gigapascals"), "gigapascals"
    ),
    Unit(
        "psi", "pound per square inch", Dimension.STRESS, _PSI_IN_MPA, (), "pounds per square inch"
    ),
    Unit(
        "ksi",
        "kip per square inch",
        Dimension.STRESS,
        1000 * _PSI_IN_MPA,
        (),
        "kips per square inch",
    ),
)

BASE_UNITS: dict[Dimension, str] = {
    Dimension.LENGTH: "mm",
    Dimension.ANGLE: "deg",
    Dimension.RATIO: "",
    Dimension.STRESS: "MPa",
}


def base_text(value: float, dimension: Dimension) -> str:
    """Write a base-unit value with its unit for developer and API messages, e.g. ``127 mm``.

    Front ends show values in display units through ``core.formatting`` instead.
    """
    return f"{value:g} {BASE_UNITS[dimension]}".rstrip()


def base_unit_names() -> str:
    """Name every base unit, e.g. ``"mm, deg, ratio, MPa"``, for messages about base units."""
    return ", ".join(unit or dimension.value for dimension, unit in BASE_UNITS.items())


_LOOKUP: dict[str, Unit] = {}
for _unit in UNITS:
    for _name in (_unit.symbol, *_unit.aliases):
        _LOOKUP[_name.lower()] = _unit


def get_unit(symbol: str) -> Unit:
    """Return the unit for a symbol or alias such as ``in``, ``"`` or ``mm``.

    Raises:
        InputError: The unit is unknown.
    """
    try:
        return _LOOKUP[symbol.strip().lower()]
    except KeyError:
        raise InputError(f"Unknown unit {symbol!r}") from None


def units_for(dimension: Dimension) -> tuple[Unit, ...]:
    """Return every unit of ``dimension``."""
    return tuple(u for u in UNITS if u.dimension is dimension)


def to_base(value: float, unit: str | Unit) -> float:
    """Convert ``value`` from ``unit`` to base units."""
    u = unit if isinstance(unit, Unit) else get_unit(unit)
    return value * u.factor


def from_base(value: float, unit: str | Unit) -> float:
    """Convert ``value`` from base units to ``unit``."""
    u = unit if isinstance(unit, Unit) else get_unit(unit)
    return value / u.factor


_MIXED = re.compile(r"([-+]?)(\d+)[\s-]+(\d+)/(\d+)")
_FRACTION = re.compile(r"([-+]?)(\d+)/(\d+)")
_QUANTITY = re.compile(r"\s*(?P<number>.*?)\s*(?P<unit>[A-Za-z°%\"'″′]+)?\s*")


def parse_number(text: str) -> float:
    """Parse a decimal or drafting-style fraction: ``0.1046``, ``1/8``, ``1-1/2``, ``1 1/2``."""
    s = text.strip()
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
    if not math.isfinite(value):
        raise InputError(f"{text!r} is not a finite number")
    return value


class ParsedQuantity(NamedTuple):
    """A parsed quantity, and the unit that was applied to read it."""

    value: float
    """The value, in base units."""
    unit: Unit
    """The unit applied: the one the text named, or else the default unit."""
    explicit_unit: bool
    """Whether the text named its unit, as in ``"3 mm"``."""


def parse_quantity(text: str, dimension: Dimension, default_unit: str | None = None) -> float:
    """Parse text such as ``0.1046 in``, ``3mm``, ``1-1/2"``, ``90°`` and return base units.

    ``default_unit`` applies when the text has no unit. It defaults to the base unit.

    Raises:
        InputError: The text isn't a valid value of ``dimension``.
    """
    return parse_quantity_detailed(text, dimension, default_unit).value


def parse_quantity_detailed(
    text: str, dimension: Dimension, default_unit: str | None = None
) -> ParsedQuantity:
    """Parse text like ``parse_quantity``, and also report the unit that was applied.

    Raises:
        InputError: The text isn't a valid value of ``dimension``.
    """
    m = _QUANTITY.fullmatch(text)
    if not m or not m.group("number"):
        raise InputError(f"Cannot read a value from {text!r}")
    number = parse_number(m.group("number"))
    unit_text = m.group("unit")
    explicit = unit_text is not None
    if unit_text is None:
        unit_text = default_unit if default_unit is not None else BASE_UNITS[dimension]
    unit = get_unit(unit_text)
    if unit.dimension is not dimension:
        raise InputError(
            f"{text!r} is {unit.dimension.with_article}, but {dimension.with_article} is expected"
        )
    return ParsedQuantity(number * unit.factor, unit, explicit)


@dataclass(frozen=True)
class TypedValue:
    """A value the user typed: the text, its exact parse, and the unit that was applied.

    This is the *intent* tier of ADR-0013 §9: the base-unit ``value`` is parsed once from
    the user's own ``text`` and never re-read from rounded display text. A front end may
    show ``text`` verbatim when it named its unit, or when ``unit`` is the display unit;
    otherwise it shows ``value`` in the display unit. Build one with ``parse``; building
    one directly checks that ``text`` read in ``unit`` gives ``value`` and ``explicit_unit``.
    """

    value: float
    """The exact parse, in base units."""
    text: str
    """What the user typed, stripped of surrounding space."""
    unit: Unit
    """The unit applied: the one the text named, or else the default unit."""
    explicit_unit: bool
    """Whether the text named its unit, as in ``"3 mm"``."""

    def __post_init__(self) -> None:
        # Re-reading the user's own text is safe; re-reading rounded display text isn't (§9).
        try:
            parsed = parse_quantity_detailed(self.text, self.dimension, self.unit.symbol)
        except InputError as exc:
            raise UsageError(f"TypedValue text {self.text!r} is not a value: {exc}") from None
        agrees = (
            parsed.unit == self.unit
            and parsed.explicit_unit == self.explicit_unit
            and abs(parsed.value - self.value) <= math.ulp(parsed.value)
        )
        if not agrees:
            raise UsageError(
                f"TypedValue text {self.text!r} doesn't read as {self.value!r} "
                f"{BASE_UNITS[self.dimension]} with unit {self.unit.symbol!r} "
                f"({'named' if self.explicit_unit else 'default'}); use TypedValue.parse()"
            )

    @property
    def dimension(self) -> Dimension:
        """What the value measures: the dimension of its unit."""
        return self.unit.dimension

    @classmethod
    def parse(cls, text: str, dimension: Dimension, default_unit: str | None = None) -> TypedValue:
        """Parse ``text`` as a ``dimension`` value; ``default_unit`` applies if it has no unit.

        Raises:
            InputError: The text isn't a valid value of that dimension.
        """
        parsed = parse_quantity_detailed(text, dimension, default_unit)
        return cls(parsed.value, text.strip(), parsed.unit, parsed.explicit_unit)


# The display rules core.formatting held before the registry.

_SHOWN_IN = {Dimension.ANGLE: "deg", Dimension.RATIO: ""}
_STRESS_WITH_LENGTH = {"in": "ksi", "ft": "ksi"}


def display_unit(dimension: Dimension, length_unit: str) -> Unit:
    """The unit values of ``dimension`` were shown in, for a length preference."""
    if dimension is Dimension.LENGTH:
        return get_unit(length_unit)
    if dimension is Dimension.STRESS:
        length = get_unit(length_unit).symbol
        return get_unit(_STRESS_WITH_LENGTH.get(length, "MPa"))
    return get_unit(_SHOWN_IN[dimension])


def shown_symbol(dimension: Dimension, length_unit: str) -> str:
    """The symbol written after a value: "°" for angles, else the display unit's."""
    return "°" if dimension is Dimension.ANGLE else display_unit(dimension, length_unit).symbol


def suffix(unit: str) -> str:
    """A symbol as written after a number: a degree sign close up, others spaced."""
    if unit == "°":
        return unit
    return f" {unit}" if unit else ""


def shows_fraction(dimension: Dimension, length_unit: str) -> bool:
    """Whether a value of ``dimension`` could show an inch fraction."""
    return dimension is Dimension.LENGTH and get_unit(length_unit).symbol == "in"
