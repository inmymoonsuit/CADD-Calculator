"""Finding calculators and their domains (ADR-0006, ADR-0013).

Built-ins are listed explicitly; plugins use entry points. Every domain is registered
before any calculator, so a calculator can always find the domain it names.
"""

from __future__ import annotations

import difflib
from collections.abc import Callable, Iterable, Iterator
from dataclasses import dataclass, field
from importlib.metadata import entry_points
from typing import Any

from caddcalc.core.calculator import Calculator
from caddcalc.core.domain import Domain
from caddcalc.core.errors import SpecError, UnknownCalculatorError, UnknownDomainError

ENTRY_POINT_GROUP = "caddcalc.calculators"
DOMAIN_ENTRY_POINT_GROUP = "caddcalc.domains"


@dataclass
class PluginError:
    """A plugin that failed to load, and the reason."""

    source: str
    message: str


@dataclass
class Registry:
    """Domains and calculators by ID.

    ``caddcalc.calculators.default_registry()`` builds the usual one, with the built-in
    domains and calculators and any installed plugins.
    """

    _items: dict[str, Calculator] = field(default_factory=dict)
    _domains: dict[str, Domain] = field(default_factory=dict)
    plugin_errors: list[PluginError] = field(default_factory=list)

    def register_domain(self, domain: Domain) -> Domain:
        """Check a domain's definition and add it.

        Raises:
            SpecError: The definition is invalid, or its ID is already registered.
        """
        domain.validate()
        if domain.id in self._domains:
            raise SpecError(f"Domain id {domain.id!r} is registered twice")
        self._domains[domain.id] = domain
        return domain

    def register(self, calculator: Calculator | type[Calculator]) -> Calculator:
        """Check a calculator's definition and add it.

        Args:
            calculator: A ``Calculator`` subclass or instance. Its domain must already be
                registered.

        Returns:
            The registered instance.

        Raises:
            SpecError: The definition is invalid, its domain is unknown, a shared
                parameter doesn't match a setting of that domain, or its ID is already
                registered.
        """
        instance = calculator() if isinstance(calculator, type) else calculator
        type(instance).validate_spec()
        if instance.domain not in self._domains:
            hint = _did_you_mean(instance.domain, self._domains)
            raise SpecError(
                f"{instance.id}: unknown domain {instance.domain!r}.{hint} Register the domain "
                f"first; plugins provide domains through the {DOMAIN_ENTRY_POINT_GROUP!r} "
                "entry-point group."
            )
        _check_shared_params(instance, self._domains[instance.domain])
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
            hint = _did_you_mean(calculator_id, self._items)
            raise UnknownCalculatorError(f"No calculator {calculator_id!r}.{hint}") from None

    def domain(self, domain_id: str) -> Domain:
        """Return the domain with ``domain_id``.

        Raises:
            UnknownDomainError: No domain has that ID; the message suggests close ones.
        """
        try:
            return self._domains[domain_id]
        except KeyError:
            hint = _did_you_mean(domain_id, self._domains)
            raise UnknownDomainError(f"No domain {domain_id!r}.{hint}") from None

    def domains(self) -> list[Domain]:
        """Return every registered domain, sorted by name."""
        return sorted(self._domains.values(), key=lambda d: d.name)

    def __iter__(self) -> Iterator[Calculator]:
        return iter(
            sorted(self._items.values(), key=lambda c: (self._domains[c.domain].name, c.name))
        )

    def __len__(self) -> int:
        return len(self._items)

    def by_domain(self) -> dict[Domain, list[Calculator]]:
        """Return the calculators grouped by domain, with domains and calculators sorted by name."""
        grouped: dict[Domain, list[Calculator]] = {}
        for calc in self:
            grouped.setdefault(self._domains[calc.domain], []).append(calc)
        return grouped

    def load_plugins(self) -> None:
        """Register plugin domains, then plugin calculators."""
        self.load_plugin_domains()
        self.load_plugin_calculators()

    def load_plugin_domains(self) -> None:
        """Register domains that installed packages advertise.

        Each entry point may name a ``Domain`` or an iterable of them. A broken plugin is
        recorded in ``plugin_errors`` and never stops the app from starting.
        """
        self._load_group(DOMAIN_ENTRY_POINT_GROUP, self._register_plugin_domains)

    def load_plugin_calculators(self) -> None:
        """Register calculators that installed packages advertise.

        Each entry point may name a ``Calculator`` subclass or an iterable of them. A broken
        plugin is recorded in ``plugin_errors`` and never stops the app from starting.
        """
        self._load_group(ENTRY_POINT_GROUP, self._register_plugin_calculators)

    def _register_plugin_domains(self, loaded: Any) -> None:
        items = [loaded] if isinstance(loaded, Domain) else list(loaded)
        for item in items:
            if not isinstance(item, Domain):
                raise SpecError(f"{item!r} is not a Domain")
            self.register_domain(item)

    def _register_plugin_calculators(self, loaded: Any) -> None:
        items: Iterable[type[Calculator]] = [loaded] if isinstance(loaded, type) else list(loaded)
        for item in items:
            self.register(item)

    def _load_group(self, group: str, register: Callable[[Any], None]) -> None:
        for ep in entry_points(group=group):
            try:
                register(ep.load())
            except Exception as exc:  # noqa: BLE001 (isolation boundary: a plugin must never crash the app)
                self.plugin_errors.append(PluginError(f"{ep.name} = {ep.value}", str(exc)))


def _check_shared_params(calculator: Calculator, domain: Domain) -> None:
    """Each shared parameter must match a setting of the domain by key and dimension."""
    for p in calculator.params:
        if not p.shared:
            continue
        setting = domain.find_setting(p.key)
        if setting is None:
            raise SpecError(
                f"{calculator.id}: shared parameter {p.key!r} has no setting with that key "
                f"in domain {domain.id!r}"
            )
        if setting.dimension is not p.dimension:
            raise SpecError(
                f"{calculator.id}: shared parameter {p.key!r} measures {p.dimension.value}, "
                f"but the {domain.id!r} setting measures {setting.dimension.value}"
            )


def _did_you_mean(name: str, known: Iterable[str]) -> str:
    close = difflib.get_close_matches(name, list(known), n=3)
    return f" Did you mean: {', '.join(close)}?" if close else ""
