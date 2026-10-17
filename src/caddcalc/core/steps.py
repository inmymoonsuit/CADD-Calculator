"""Steps of "show work", the lines a result's work is shown as (ADR-0004)."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from caddcalc.core.units import Dimension


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
    """The expression's symbols as shown, when they aren't the calculator's own, as in a
    derived value's work. ``None`` shows the calculator's values for its symbols."""
