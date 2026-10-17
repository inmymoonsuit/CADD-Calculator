"""Finding calculators and their domains (ADR-0006, ADR-0013).

Built-ins are listed explicitly; plugins use entry points. A calculator's domain must
already be registered when the calculator is, so ``default_registry()`` registers every
domain, built-in and plugin, before any calculator.
"""

from __future__ import annotations

import difflib
from collections.abc import Callable, Iterable, Iterator, Mapping
from dataclasses import dataclass, field
from importlib import metadata
from typing import Any, Protocol

from caddcalc.core.calculator import Calculator
from caddcalc.core.domain import Domain
from caddcalc.core.errors import SpecError, UnknownCalculatorError, UnknownDomainError
from caddcalc.core.spec import Method

ENTRY_POINT_GROUP = "caddcalc.calculators"
DOMAIN_ENTRY_POINT_GROUP = "caddcalc.domains"


class PluginEntryPoint(Protocol):
    """The parts of an installed package's entry point that the registry uses."""

    @property
    def name(self) -> str:
        """The entry point's name."""

    @property
    def value(self) -> str:
        """The object reference, e.g. ``"acme.tools:CALCULATORS"``."""

    def load(self) -> Any:
        """Import and return the object the entry point names."""


class EntryPointSource(Protocol):
    """Lists entry points by group, as ``importlib.metadata.entry_points`` does."""

    def __call__(self, *, group: str) -> Iterable[PluginEntryPoint]:
        """Return the entry points in ``group``."""


@dataclass
class PluginError:
    """A plugin that failed to load, and the reason."""

    source: str
    """The entry point, as ``name = value``. An item of an iterable adds its index: ``name[1]``."""
    message: str


@dataclass
class Registry:
    """Domains and calculators by ID.

    ``caddcalc.calculators.default_registry()`` builds the usual one, with the built-in
    domains and calculators and any installed plugins. A new registry is empty, and the
    ``register`` methods, which check each definition, are the only way to fill it.
    """

    _items: dict[str, Calculator] = field(default_factory=dict, init=False)
    _domains: dict[str, Domain] = field(default_factory=dict, init=False)
    plugin_errors: list[PluginError] = field(default_factory=list, init=False)
    entry_points: EntryPointSource = field(
        default=metadata.entry_points, kw_only=True, repr=False, compare=False
    )
    """Where the ``load_plugin_*`` methods find installed plugins."""
    _plugin_domain_ids: set[str] = field(default_factory=set, init=False, repr=False)

    def register_domain(self, domain: Domain) -> Domain:
        """Check a domain's definition and add it.

        Raises:
            SpecError: The definition or its choices are invalid, or its ID is already
                registered.
        """
        domain.validate()
        domain.validate_choices()
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
            hint = self._domain_hint(instance.domain)
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
            hint = _did_you_mean(calculator_id, {i: i for i in self._items})
            raise UnknownCalculatorError(f"No calculator {calculator_id!r}.{hint}") from None

    def domain(self, domain_id: str) -> Domain:
        """Return the domain with ``domain_id``.

        Raises:
            UnknownDomainError: No domain has that ID; the message suggests domains whose
                ID or name is close.
        """
        try:
            return self._domains[domain_id]
        except KeyError:
            hint = self._domain_hint(domain_id)
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

    def setting_uses(self, domain_id: str, key: str) -> list[tuple[Calculator, tuple[Method, ...]]]:
        """Return each calculator that shares the setting ``key``, with the methods using it.

        Calculators come in name order; a calculator whose parameter with that key isn't
        shared is not listed.

        Raises:
            UnknownDomainError: No domain has that ID.
            UsageError: The domain has no setting with that key.
        """
        self.domain(domain_id).setting(key)
        uses = []
        for calc in self:
            param = next((p for p in calc.params if p.key == key), None)
            if calc.domain == domain_id and param is not None and param.shared:
                uses.append((calc, tuple(m for m in calc.methods if param.used_by(m.key))))
        return uses

    def load_plugins(self) -> None:
        """Register plugin domains, then plugin calculators."""
        self.load_plugin_domains()
        self.load_plugin_calculators()

    def load_plugin_domains(self) -> None:
        """Register domains that installed packages advertise.

        Each entry point may name a ``Domain`` or an iterable of them. A plugin can't
        redefine a domain registered directly, such as a built-in. A broken plugin, or a
        broken item in its iterable, is recorded in ``plugin_errors`` and never stops the
        app from starting.
        """
        self._load_group(DOMAIN_ENTRY_POINT_GROUP, Domain, self._register_plugin_domain)

    def load_plugin_calculators(self) -> None:
        """Register calculators that installed packages advertise.

        Each entry point may name a ``Calculator`` subclass or an iterable of them. A broken
        plugin, or a broken item in its iterable, is recorded in ``plugin_errors`` and never
        stops the app from starting.
        """
        self._load_group(ENTRY_POINT_GROUP, type, self._register_plugin_calculator)

    def _register_plugin_domain(self, item: object) -> None:
        if not isinstance(item, Domain):
            raise SpecError(f"{item!r} is not a Domain")
        if item.id in self._domains and item.id not in self._plugin_domain_ids:
            raise SpecError(f"a plugin can't redefine built-in domain {item.id!r}")
        self.register_domain(item)
        self._plugin_domain_ids.add(item.id)

    def _register_plugin_calculator(self, item: object) -> None:
        if not (isinstance(item, type) and issubclass(item, Calculator)):
            raise SpecError(f"{item!r} is not a Calculator subclass")
        self.register(item)

    def _load_group(self, group: str, single: type, register: Callable[[object], None]) -> None:
        """Register what each entry point in ``group`` names, one item at a time.

        An entry point names one item, an instance of ``single``, or an iterable of items.
        """
        for ep in self.entry_points(group=group):
            source = f"{ep.name} = {ep.value}"
            try:
                loaded = ep.load()
                if isinstance(loaded, single):
                    items = [(source, loaded)]
                else:
                    items = [(f"{ep.name}[{i}] = {ep.value}", x) for i, x in enumerate(loaded)]
            except Exception as exc:  # noqa: BLE001 (isolation boundary: a plugin must never crash the app)
                self.plugin_errors.append(PluginError(source, str(exc)))
                continue
            for item_source, item in items:
                try:
                    register(item)
                except Exception as exc:  # noqa: BLE001 (isolation boundary: one bad item must not drop the rest)
                    self.plugin_errors.append(PluginError(item_source, str(exc)))

    def _domain_hint(self, wanted: str) -> str:
        """Suggest domains whose ID or display name is close to ``wanted``."""
        spellings = {d.id: d.id for d in self._domains.values()}
        spellings.update({d.name.lower(): d.id for d in self._domains.values()})
        return _did_you_mean(wanted.lower(), spellings)


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


def _did_you_mean(name: str, known: Mapping[str, str]) -> str:
    """Return a hint naming up to three IDs close to ``name``, or an empty string.

    Args:
        name: What was asked for.
        known: Each spelling to compare ``name`` with, mapped to the ID it suggests.
    """
    close = difflib.get_close_matches(name, list(known), n=3)
    ids = dict.fromkeys(known[c] for c in close)
    return f" Did you mean: {', '.join(ids)}?" if ids else ""
