"""Finding calculators: built-ins are listed explicitly; plugins use entry points (ADR-0006)."""

from __future__ import annotations

import difflib
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from importlib.metadata import entry_points

from caddcalc.core.calculator import Calculator
from caddcalc.core.errors import SpecError, UnknownCalculatorError

ENTRY_POINT_GROUP = "caddcalc.calculators"


@dataclass
class PluginError:
    """A plugin that failed to load, and the reason."""

    source: str
    message: str


@dataclass
class Registry:
    """Calculators by ID.

    ``caddcalc.calculators.default_registry()`` builds the usual one, with the built-in
    calculators and any installed plugins.
    """

    _items: dict[str, Calculator] = field(default_factory=dict)
    plugin_errors: list[PluginError] = field(default_factory=list)

    def register(self, calculator: Calculator | type[Calculator]) -> Calculator:
        """Check a calculator's definition and add it.

        Args:
            calculator: A ``Calculator`` subclass or instance.

        Returns:
            The registered instance.

        Raises:
            SpecError: The definition is invalid, or its ID is already registered.
        """
        instance = calculator() if isinstance(calculator, type) else calculator
        type(instance).validate_spec()
        if instance.id in self._items:
            raise SpecError(f"Calculator id {instance.id!r} is registered twice")
        self._items[instance.id] = instance
        return instance

    def get(self, calculator_id: str) -> Calculator:
        """Return the calculator with ``calculator_id``.

        Raises:
            UnknownCalculatorError: No calculator has that ID; the message suggests close ones.
        """
        try:
            return self._items[calculator_id]
        except KeyError:
            close = difflib.get_close_matches(calculator_id, self._items, n=3)
            hint = f" Did you mean: {', '.join(close)}?" if close else ""
            raise UnknownCalculatorError(f"No calculator {calculator_id!r}.{hint}") from None

    def __iter__(self) -> Iterator[Calculator]:
        return iter(sorted(self._items.values(), key=lambda c: (c.domain, c.name)))

    def __len__(self) -> int:
        return len(self._items)

    def by_domain(self) -> dict[str, list[Calculator]]:
        """Return the calculators grouped by domain, each group sorted by name."""
        grouped: dict[str, list[Calculator]] = {}
        for calc in self:
            grouped.setdefault(calc.domain, []).append(calc)
        return grouped

    def load_plugins(self) -> None:
        """Register calculators that installed packages advertise.

        Each entry point may name a Calculator subclass or an iterable of them. A broken
        plugin is recorded in ``plugin_errors`` and never stops the app from starting.
        """
        for ep in entry_points(group=ENTRY_POINT_GROUP):
            try:
                loaded = ep.load()
                items: Iterable[type[Calculator]] = (
                    [loaded] if isinstance(loaded, type) else list(loaded)
                )
                for item in items:
                    self.register(item)
            except Exception as exc:  # noqa: BLE001 (isolation boundary: a plugin must never crash the app)
                self.plugin_errors.append(PluginError(f"{ep.name} = {ep.value}", str(exc)))
