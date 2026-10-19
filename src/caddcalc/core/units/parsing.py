"""Reading quantities people type, and converting between units (ADR-0005, ADR-0019 §3).

Every calculation runs in canonical *base units*: millimetres for length, degrees for
angle, plain numbers for ratios, and megapascals for stress. Values are converted only
at the edges, when input is parsed and when output is formatted (ADR-0005).

A unit in typed text is found by the registry, never by a list of characters here: the
longest registered symbol or alias that ends the text, as a whole word, names it, and the
rest is the number. So a unit parses as soon as it's registered. A dimension's compound
forms, such as feet and inches, are tried before that (``units.compound``).
"""

from __future__ import annotations

import math
import re
import sys
from dataclasses import dataclass
from fractions import Fraction
from typing import NamedTuple

from caddcalc.core.errors import InputError, UsageError
from caddcalc.core.units.builtin import DIMENSIONS
from caddcalc.core.units.builtin import UNITS as UNITS
from caddcalc.core.units.entry import read as read_entry
from caddcalc.core.units.model import COUNT_LIMIT, Dimension, Exact, Unit
from caddcalc.core.units.numbers import MINUS_SIGN as MINUS_SIGN
from caddcalc.core.units.numbers import parse_number as parse_number
from caddcalc.core.units.unit_registry import registry

BASE_UNITS: dict[Dimension, str] = {spec.dimension: spec.base for spec in DIMENSIONS}
"""Each dimension's base unit, by key symbol: every calculation runs in these."""


def base_text(value: float, dimension: Dimension) -> str:
    """Write a base-unit value with its unit for developer and API messages, e.g. ``127 mm``.

    Front ends show values in display units through ``core.formatting`` instead.
    """
    if dimension is Dimension.COUNT and value.is_integer():
        return f"{value:.0f}"  # a count is whole, never "1e+06"
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
            With none given, a length wins: ``'`` and ``"`` are the foot and inch.

    Raises:
        InputError: The unit is unknown.
        UsageError: Units of several dimensions have that name, and none is of
            ``dimension``, or, with none given, a length.
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


def convert(amount: Exact | int, source: Unit, target: Unit) -> Fraction:
    """Convert an exact ``amount`` of ``source`` to ``target``, exactly, from their definitions.

    For checks and an exact amount (ADR-0019 §2): 3/16 in is 4.7625 mm, and 1 psi is
    6.894 757 293 168 361 336 … kPa. A typed value is a double already, so a calculator
    converts it with ``from_base``.

    Raises:
        UsageError: The units measure different things, or one has no exact factor.
    """
    if source.dimension is not target.dimension:
        raise UsageError(f"{source.symbol!r} and {target.symbol!r} measure different things")
    if source.exact is None or target.exact is None:
        raise UsageError(f"{source.symbol!r} or {target.symbol!r} has no exact factor")
    return Fraction(amount) * Fraction(source.exact) / Fraction(target.exact)


class ParsedQuantity(NamedTuple):
    """A parsed quantity, and the unit that was applied to read it."""

    value: float
    """The value, in base units."""
    unit: Unit
    """The unit applied: the one the text named, or else the default unit."""
    explicit_unit: bool
    """Whether the text named its unit, as in ``"3 mm"``."""


def parse_quantity(
    text: str, dimension: Dimension, default_unit: str | None = None, *, decimal: str = "."
) -> float:
    """Parse text such as ``0.1046 in``, ``3mm``, ``1-1/2"``, ``90°`` and return base units.

    ``default_unit`` applies when the text has no unit. It defaults to the base unit.
    ``decimal`` is the locale's decimal mark, read besides ``"."`` (``parse_number``).

    Raises:
        InputError: The text isn't a valid value of ``dimension``.
    """
    return parse_quantity_detailed(text, dimension, default_unit, decimal=decimal).value


_SPACES = re.compile(r"\s+")
"""A run of spaces of any kind, a no-break space among them: it reads as one space, so a
unit named in two words, such as "per cent", reads however they're spaced."""


def parse_quantity_detailed(
    text: str, dimension: Dimension, default_unit: str | None = None, *, decimal: str = "."
) -> ParsedQuantity:
    """Parse text like ``parse_quantity``, and also report the unit that was applied.

    Raises:
        InputError: The text isn't a valid value of ``dimension``.
    """
    units = registry()
    stripped = _SPACES.sub(" ", text).strip()
    signed = stripped.replace(MINUS_SIGN, "-")
    for form in units.compounds_for(dimension):  # tried first, and only for their own
        value = form.parse(signed, decimal)
        if value is not None:
            return ParsedQuantity(value, units.find(form.full_unit, dimension), True)
    named = units.ending(stripped, dimension)
    # Without a registered name at its end, any word there is an unknown unit, said as typed.
    word = "" if named is not None else units.trailing_word(stripped)
    number_text = stripped[: len(stripped) - (named[1] if named else len(word))].rstrip()
    if not number_text:
        raise InputError(f"Cannot read a value from {text!r}")
    number = parse_number(number_text, decimal)
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
    if dimension is Dimension.COUNT and not float(number).is_integer():
        raise InputError(f"{text!r} isn't a whole number, and a count is")
    if dimension is Dimension.COUNT and abs(number) >= COUNT_LIMIT:
        raise InputError(f"{text!r} is too large a count to hold exactly: give one under 2^53")
    value = number * unit.factor
    if not math.isfinite(value):
        # A finite number in a large unit, as 1e308 ft is, can overflow in the base unit.
        raise InputError(
            f"{text!r} is too large to calculate with: its size in {BASE_UNITS[dimension]} "
            f"must be under {sys.float_info.max:.6g}"
        )
    return ParsedQuantity(value, unit, explicit)


@dataclass(frozen=True)
class TypedValue:
    """A value the user typed: the text, its exact parse, and the unit that was applied.

    This is the *intent* tier of ADR-0013 §9: the base-unit ``value`` is parsed once from
    the user's own ``text`` and never re-read from rounded display text. A value typed
    into a field picked in a unit or form is built with ``read``, and its ``choice`` is
    the pick (ADR-0024 E2); text with its unit in it, from the command line or a
    declaration, is built with ``parse``, and its ``choice`` is ``None``. Building one
    directly checks that ``text`` read so gives ``value``, ``unit`` and ``explicit_unit``.
    """

    value: float
    """The exact parse, in base units."""
    text: str
    """What the user typed, stripped of surrounding space."""
    unit: Unit
    """The unit applied: the one the text named, or else the default unit."""
    explicit_unit: bool
    """Whether the text named its unit, as in ``"3 mm"``."""
    decimal: str = "."
    """The locale's decimal mark the text was read with, besides ``"."``: ``","`` for
    ``"0,0625"`` typed in a comma locale (ADR-0020 §4)."""
    choice: str | None = None
    """The id of the unit or form the field was picked in, e.g. ``"mm"``, ``"ft_in"``, or
    ``""`` for a ratio's unnamed unit; ``None`` for text read by ``parse``, which names
    its own unit or takes the default."""

    def __post_init__(self) -> None:
        # Re-reading the user's own text is safe; re-reading rounded display text isn't (§9).
        try:
            if self.choice is not None:
                value, unit = read_entry(
                    self.text, self.choice, self.dimension, decimal=self.decimal
                )
                parsed = ParsedQuantity(value, unit, False)
            else:
                parsed = parse_quantity_detailed(
                    self.text, self.dimension, self.unit.symbol, decimal=self.decimal
                )
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
    def parse(
        cls,
        text: str,
        dimension: Dimension,
        default_unit: str | None = None,
        *,
        decimal: str = ".",
    ) -> TypedValue:
        """Parse ``text`` as a ``dimension`` value; ``default_unit`` applies if it has no unit.

        ``decimal`` is the locale's decimal mark, read besides ``"."``.

        Raises:
            InputError: The text isn't a valid value of that dimension.
        """
        parsed = parse_quantity_detailed(text, dimension, default_unit, decimal=decimal)
        return cls(parsed.value, text.strip(), parsed.unit, parsed.explicit_unit, decimal)

    @classmethod
    def read(
        cls, text: str, choice: str, dimension: Dimension, *, decimal: str = "."
    ) -> TypedValue:
        """Read a field's ``text``, picked in ``choice``, as a ``dimension`` value.

        A plain number reads bit for bit as ``parse_quantity`` reads it in that unit; a
        form's text by the form's grammar, with its marks optional; and a text that
        names a unit is refused with its fix (``core.units.entry``).

        Raises:
            UnitInTextError: The text names a unit, which goes in the picker.
            InputError: The text isn't a value in the choice.
            UsageError: ``choice`` isn't one of ``dimension``'s.
        """
        value, unit = read_entry(text, choice, dimension, decimal=decimal)
        return cls(value, text.strip(), unit, False, decimal, choice)
