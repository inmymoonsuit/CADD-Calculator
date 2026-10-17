"""Steps of "show work", the lines a result's work is shown as (ADR-0004)."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from caddcalc.core.errors import InputError, SpecError
from caddcalc.core.units import Dimension, get_unit


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

    def __post_init__(self) -> None:
        if self.expression_unit is None:
            return
        if self.expression is None:
            raise SpecError(f"Step {self.symbol}: only a formula step has an expression_unit")
        try:
            unit = get_unit(self.expression_unit)
        except InputError as exc:
            raise SpecError(f"Step {self.symbol}: {exc}") from None
        if unit.dimension is not self.dimension:
            raise SpecError(
                f"Step {self.symbol}: {self.expression_unit!r} doesn't measure "
                f"{self.dimension.with_article}"
            )
