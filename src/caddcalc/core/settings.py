"""The domain settings a user sets during a session (ADR-0013 §7).

Settings live only in memory: the GUI holds one ``DomainSettings`` for the life of its
window, and nothing is saved. The model is immutable; every change returns a new one.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from types import MappingProxyType

from caddcalc.core.domain import Domain, DomainValues
from caddcalc.core.errors import UsageError
from caddcalc.core.units import TypedValue


@dataclass(frozen=True)
class DomainSettings:
    """The values a user has set, and the options they have chosen, per domain.

    ``DomainSettings()`` is empty, and the methods that set values or choose options are
    the only way to add one, so everything in it has been checked against its domain.
    Models compare equal when they hold the same values and choices.
    """

    _values: Mapping[str, Mapping[str, TypedValue]] = field(default_factory=dict, init=False)
    _choices: Mapping[str, Mapping[str, str]] = field(default_factory=dict, init=False)
    """The option key chosen for each choice, by domain id and choice key."""
    __hash__ = None  # type: ignore[assignment]  # equal by value, and the values are dicts

    def get(self, domain: Domain, key: str) -> TypedValue | None:
        """Return the value set for ``key``, or ``None`` if it is unset.

        Raises:
            UsageError: ``domain`` has no setting with that key.
        """
        domain.setting(key)
        return self._values.get(domain.id, {}).get(key)

    def values(self, domain: Domain) -> Mapping[str, TypedValue]:
        """Return every value set in ``domain``, by setting key (read-only)."""
        return MappingProxyType(dict(self._values.get(domain.id, {})))

    def set_text(
        self, domain: Domain, key: str, text: str, default_unit: str | None = None
    ) -> DomainSettings:
        """Return a copy with ``key`` set from the user's text.

        Args:
            domain: The domain the setting belongs to.
            key: The setting key, e.g. ``"thickness"``.
            text: What the user typed, e.g. ``"1/8"`` or ``"3 mm"``.
            default_unit: The unit for text typed without one.

        Raises:
            UsageError: ``domain`` has no setting with that key.
            InputError: The text isn't a valid value of the setting's dimension.
            OutOfRangeError: The value is outside the setting's range.
        """
        setting = domain.setting(key)
        return self.set(domain, key, TypedValue.parse(text, setting.dimension, default_unit))

    def set(self, domain: Domain, key: str, entry: TypedValue) -> DomainSettings:
        """Return a copy with ``key`` set to ``entry``.

        Raises:
            UsageError: ``domain`` has no setting with that key, or ``entry`` measures
                something else.
            OutOfRangeError: The value is outside the setting's range.
        """
        setting = domain.setting(key)
        if entry.dimension is not setting.dimension:
            raise UsageError(
                f"Setting {key!r} of domain {domain.id!r} is {setting.dimension.with_article}, "
                f"but {entry.text!r} is {entry.dimension.with_article}"
            )
        setting.check(entry.value)
        return self._with(domain.id, values={**self._values.get(domain.id, {}), key: entry})

    def clear(self, domain: Domain, key: str) -> DomainSettings:
        """Return a copy with ``key`` unset.

        Raises:
            UsageError: ``domain`` has no setting with that key.
        """
        domain.setting(key)
        remaining = {k: v for k, v in self._values.get(domain.id, {}).items() if k != key}
        return self._with(domain.id, values=remaining)

    def choice(self, domain: Domain, key: str) -> str | None:
        """Return the option chosen for ``key``, its default if none was, or ``None``.

        Raises:
            UsageError: ``domain`` has no choice with that key.
        """
        default = domain.choice(key).default
        return self._choices.get(domain.id, {}).get(key, default)

    def set_choice(self, domain: Domain, key: str, option: str) -> DomainSettings:
        """Return a copy with ``option`` chosen for the choice ``key``.

        Raises:
            UsageError: ``domain`` has no choice with that key, or the choice has no such
                option.
        """
        if option not in {o.key for o in domain.options(key)}:
            raise UsageError(f"Choice {key!r} of domain {domain.id!r} has no option {option!r}")
        return self._with(domain.id, choices={**self._choices.get(domain.id, {}), key: option})

    def clear_choice(self, domain: Domain, key: str) -> DomainSettings:
        """Return a copy with the choice ``key`` back to its default.

        Raises:
            UsageError: ``domain`` has no choice with that key.
        """
        domain.choice(key)
        remaining = {k: v for k, v in self._choices.get(domain.id, {}).items() if k != key}
        return self._with(domain.id, choices=remaining)

    def clear_domain(self, domain: Domain) -> DomainSettings:
        """Return a copy with every setting and choice of ``domain`` unset."""
        return self._with(domain.id, values={}, choices={})

    def for_domain(self, domain: Domain) -> DomainValues:
        """Return the values set for ``domain`` and those its choices derive, for ``run``."""
        values = domain.values(
            **{key: entry.value for key, entry in self._values.get(domain.id, {}).items()}
        )
        selections = {
            c.key: option for c in domain.choices if (option := self.choice(domain, c.key))
        }
        return replace(values, derived=domain.derived(selections))

    def _with(
        self,
        domain_id: str,
        *,
        values: Mapping[str, TypedValue] | None = None,
        choices: Mapping[str, str] | None = None,
    ) -> DomainSettings:
        """Return a copy with ``domain_id``'s values or choices replaced, already checked."""
        settings = DomainSettings()
        # The fields are frozen and not in __init__, so they are set directly.
        object.__setattr__(settings, "_values", _replaced(self._values, domain_id, values))
        object.__setattr__(settings, "_choices", _replaced(self._choices, domain_id, choices))
        return settings


def _replaced[V](
    by_domain: Mapping[str, Mapping[str, V]], domain_id: str, entries: Mapping[str, V] | None
) -> dict[str, Mapping[str, V]]:
    """Return ``by_domain`` with ``domain_id``'s entries replaced, or unchanged if ``None``.

    A domain left with no entries is dropped, so emptied models compare equal to new ones.
    """
    updated = dict(by_domain)
    if entries is None:
        return updated
    updated.pop(domain_id, None)
    if entries:
        updated[domain_id] = dict(entries)
    return updated
