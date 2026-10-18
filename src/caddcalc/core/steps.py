"""Steps of "show work", the lines a result's work is shown as (ADR-0004)."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from caddcalc.core.errors import InputError, SpecError
from caddcalc.core.units import Dimension, TypedValue, get_unit


@dataclass(frozen=True)
class Step:
    """One line of "show work": ``symbol = expression = value``."""

    symbol: str
    label: str
    dimension: Dimension
    value: float
    expression: str | None = None
    """The evaluated formula, or None when the value was computed in code (see ``note``)."""
    note: str = ""
    substitution: Mapping[str, str] | None = None
    """The text shown for each of the expression's symbols, when they aren't the
    calculator's own, as in a derived value's work. ``None`` shows the calculator's values
    for its symbols."""
    expression_unit: str | None = None
    """The unit the expression yields, e.g. ``"in"``, when it isn't the base unit, as in a
    derived value's work. The work is shown in it, then converted to the display unit
    (ADR-0014, amendments; KI-005)."""
    stated: str | None = None
    """The value as its source states it, e.g. ``"0.109375 in"``, shown as the expression's
    result instead of a figure rounded for display. It needs an ``expression_unit``, in
    which it must state ``value`` exactly."""

    def __post_init__(self) -> None:
        if self.expression_unit is None:
            if self.stated is not None:
                raise SpecError(f"Step {self.symbol}: a stated value needs an expression_unit")
            return
        if self.expression is None:
            raise SpecError(f"Step {self.symbol}: only a formula step has an expression_unit")
        try:
            unit = get_unit(self.expression_unit, self.dimension)
        except InputError as exc:
            raise SpecError(f"Step {self.symbol}: {exc}") from None
        if unit.dimension is not self.dimension:
            raise SpecError(
                f"Step {self.symbol}: {self.expression_unit!r} doesn't measure "
                f"{self.dimension.with_article}"
            )
        if self.stated is None:
            return
        try:
            stated = TypedValue.parse(self.stated, self.dimension)
        except InputError as exc:
            raise SpecError(f"Step {self.symbol}: stated value: {exc}") from None
        if (
            not stated.explicit_unit
            or stated.unit.symbol != unit.symbol
            or stated.value != self.value
        ):
            raise SpecError(
                f"Step {self.symbol}: stated {self.stated!r} isn't its value in "
                f"{self.expression_unit}"
            )
