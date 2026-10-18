"""Reading quantities people type, and converting between units (ADR-0005, ADR-0019 §3).

Every calculation runs in canonical *base units*: millimetres for length, degrees for
angle, plain numbers for ratios, and megapascals for stress. Values are converted only
at the edges, when input is parsed and when output is formatted (ADR-0005).

A unit in typed text is found by the registry, never by a list of characters here: the
longest registered symbol or alias that ends the text, as a whole word, names it, and the
rest is the number. So a unit parses as soon as it's registered.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import NamedTuple

from caddcalc.core.errors import InputError, UsageError
from caddcalc.core.units.builtin import DIMENSIONS
from caddcalc.core.units.builtin import UNITS as UNITS
from caddcalc.core.units.model import Dimension, Unit
from caddcalc.core.units.unit_registry import registry

BASE_UNITS: dict[Dimension, str] = {spec.dimension: spec.base for spec in DIMENSIONS}
"""Each dimension's base unit, by key symbol: every calculation runs in these."""


def base_text(value: float, dimension: Dimension) -> str:
    """Write a base-unit value with its unit for developer and API messages, e.g. ``127 mm``.

    Front ends show values in display units through ``core.formatting`` instead.
    """
    return f"{value:g} {BASE_UNITS[dimension]}".rstrip()


def base_unit_names() -> str:
    """Name every base unit, e.g. ``"mm, deg, ratio, MPa"``, for messages about base units."""
    return ", ".join(unit or dimension.value for dimension, unit in BASE_UNITS.items())


def get_unit(symbol: str, dimension: Dimension | None = None) -> Unit:
    """Return the unit for a symbol or alias such as ``in``, ``"`` or ``mm``, in any case.

    Args:
        symbol: The symbol or alias.
        dimension: The dimension it's expected to be of. Give it wherever it's known: a
            unit of that dimension wins where units of several share the name, and with
            none of that dimension, the unit of whatever dimension has it is returned.

    Raises:
        InputError: The unit is unknown.
        UsageError: Units of several dimensions have that name, and none is of
            ``dimension``.
    """
    return registry().find(symbol, dimension)


def units_for(dimension: Dimension) -> tuple[Unit, ...]:
    """Return every unit of ``dimension``, built-in or from a plugin."""
    return registry().units_for(dimension)


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
    units = registry()
    stripped = text.strip()
    named = units.ending(stripped, dimension)
    # Without a registered name at its end, any word there is an unknown unit, said as typed.
    word = "" if named is not None else units.trailing_word(stripped)
    number_text = stripped[: len(stripped) - (named[1] if named else len(word))].rstrip()
    if not number_text:
        raise InputError(f"Cannot read a value from {text!r}")
    number = parse_number(number_text)
    if named is not None:
        unit = named[0]
    else:
        name = word or (BASE_UNITS[dimension] if default_unit is None else default_unit)
        unit = units.find(name, dimension)
    explicit = named is not None or bool(word)
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
