"""Dimensions, units, and parsing of user-entered quantities.

Every calculation runs in canonical *base units*: millimetres for length, degrees for
angle, and plain numbers for ratios. Values are converted only at the edges, when
input is parsed and when output is formatted (ADR-0005).
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from enum import Enum

from caddcalc.core.errors import InputError


class Dimension(Enum):
    LENGTH = "length"
    ANGLE = "angle"
    RATIO = "ratio"


@dataclass(frozen=True)
class Unit:
    symbol: str
    name: str
    dimension: Dimension
    factor: float
    """Multiply a value in this unit by ``factor`` to get base units."""
    aliases: tuple[str, ...] = ()


UNITS: tuple[Unit, ...] = (
    Unit("mm", "millimetre", Dimension.LENGTH, 1.0, ("millimeter", "millimeters", "millimetres")),
    Unit("cm", "centimetre", Dimension.LENGTH, 10.0, ("centimeter", "centimeters", "centimetres")),
    Unit("m", "metre", Dimension.LENGTH, 1000.0, ("meter", "meters", "metres")),
    Unit("in", "inch", Dimension.LENGTH, 25.4, ('"', "″", "inch", "inches")),
    Unit("ft", "foot", Dimension.LENGTH, 304.8, ("'", "′", "foot", "feet")),
    Unit("deg", "degree", Dimension.ANGLE, 1.0, ("°", "degree", "degrees")),
    Unit("rad", "radian", Dimension.ANGLE, 180.0 / math.pi, ("radian", "radians")),
    Unit("", "ratio", Dimension.RATIO, 1.0),
    Unit("%", "percent", Dimension.RATIO, 0.01, ("percent",)),
)

BASE_UNITS: dict[Dimension, str] = {
    Dimension.LENGTH: "mm",
    Dimension.ANGLE: "deg",
    Dimension.RATIO: "",
}

_LOOKUP: dict[str, Unit] = {}
for _unit in UNITS:
    for _name in (_unit.symbol, *_unit.aliases):
        _LOOKUP[_name.lower()] = _unit


def get_unit(symbol: str) -> Unit:
    try:
        return _LOOKUP[symbol.strip().lower()]
    except KeyError:
        raise InputError(f"Unknown unit {symbol!r}") from None


def units_for(dimension: Dimension) -> tuple[Unit, ...]:
    return tuple(u for u in UNITS if u.dimension is dimension)


def to_base(value: float, unit: str | Unit) -> float:
    u = unit if isinstance(unit, Unit) else get_unit(unit)
    return value * u.factor


def from_base(value: float, unit: str | Unit) -> float:
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


def parse_quantity(text: str, dimension: Dimension, default_unit: str | None = None) -> float:
    """Parse text such as ``0.1046 in``, ``3mm``, ``1-1/2"``, ``90°`` and return base units.

    ``default_unit`` applies when the text has no unit. It defaults to the base unit.
    """
    m = _QUANTITY.fullmatch(text)
    if not m or not m.group("number"):
        raise InputError(f"Cannot read a value from {text!r}")
    number = parse_number(m.group("number"))
    unit_text = m.group("unit")
    if unit_text is None:
        unit_text = default_unit if default_unit is not None else BASE_UNITS[dimension]
    unit = get_unit(unit_text)
    if unit.dimension is not dimension:
        raise InputError(
            f"{text!r} is a {unit.dimension.value}, but a {dimension.value} is expected"
        )
    return number * unit.factor
