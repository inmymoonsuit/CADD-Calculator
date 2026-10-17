"""The domain settings a user sets during a session (ADR-0013 §7).

Settings live only in memory: the GUI holds one ``DomainSettings`` for the life of its
window, and nothing is saved. The model is immutable; every change returns a new one.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType

from caddcalc.core.domain import Domain, DomainValues
from caddcalc.core.errors import SpecError
from caddcalc.core.spec import Param
from caddcalc.core.units import TypedValue


@dataclass(frozen=True)
class DomainSettings:
    """The values a user has set, per domain id and setting key."""

    _values: Mapping[str, Mapping[str, TypedValue]] = field(default_factory=dict)

    def get(self, domain_id: str, key: str) -> TypedValue | None:
        """Return the value set for ``key`` in ``domain_id``, or ``None`` if it is unset."""
        return self._values.get(domain_id, {}).get(key)

    def values(self, domain_id: str) -> Mapping[str, TypedValue]:
        """Return every value set in ``domain_id``, by setting key (read-only)."""
        return MappingProxyType(dict(self._values.get(domain_id, {})))

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
            SpecError: ``domain`` has no setting with that key.
            InputError: The text isn't a valid value, or it is out of the setting's range.
        """
        setting = _setting(domain, key)
        return self.set(domain, key, TypedValue.parse(text, setting.dimension, default_unit))

    def set(self, domain: Domain, key: str, entry: TypedValue) -> DomainSettings:
        """Return a copy with ``key`` set to ``entry``.

        Raises:
            SpecError: ``domain`` has no setting with that key.
            InputError: The value is out of the setting's range.
        """
        _setting(domain, key).check(entry.value)
        updated = {**self._values.get(domain.id, {}), key: entry}
        return DomainSettings({**self._values, domain.id: updated})

    def clear(self, domain_id: str, key: str) -> DomainSettings:
        """Return a copy with ``key`` unset in ``domain_id``."""
        remaining = {k: v for k, v in self._values.get(domain_id, {}).items() if k != key}
        return DomainSettings({**self._values, domain_id: remaining})

    def clear_domain(self, domain_id: str) -> DomainSettings:
        """Return a copy with every setting of ``domain_id`` unset."""
        return DomainSettings({d: v for d, v in self._values.items() if d != domain_id})

    def for_domain(self, domain: Domain) -> DomainValues:
        """Return the values set for ``domain``, as ``Calculator.run`` takes them."""
        values = {key: entry.value for key, entry in self._values.get(domain.id, {}).items()}
        return DomainValues(domain.id, f"{domain.name} settings", values)


def _setting(domain: Domain, key: str) -> Param:
    setting = domain.find_setting(key)
    if setting is None:
        raise SpecError(f"Domain {domain.id!r} has no setting {key!r}")
    return setting
