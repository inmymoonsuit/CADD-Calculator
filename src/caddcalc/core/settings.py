"""The domain settings a user sets during a session (ADR-0013 §7).

Settings live only in memory: the GUI holds one ``DomainSettings`` for the life of its
window, and nothing is saved. The model is immutable; every change returns a new one.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType

from caddcalc.core.domain import Domain, DomainValues
from caddcalc.core.errors import UsageError
from caddcalc.core.units import TypedValue


@dataclass(frozen=True)
class DomainSettings:
    """The values a user has set, per domain and setting key.

    ``DomainSettings()`` is empty, and the methods that set values are the only way to
    add one, so every value has been checked against its setting. Models compare equal
    when they hold the same values.
    """

    _values: Mapping[str, Mapping[str, TypedValue]] = field(default_factory=dict, init=False)
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
        return self._with(domain.id, {**self._values.get(domain.id, {}), key: entry})

    def clear(self, domain: Domain, key: str) -> DomainSettings:
        """Return a copy with ``key`` unset.

        Raises:
            UsageError: ``domain`` has no setting with that key.
        """
        domain.setting(key)
        remaining = {k: v for k, v in self._values.get(domain.id, {}).items() if k != key}
        return self._with(domain.id, remaining)

    def clear_domain(self, domain: Domain) -> DomainSettings:
        """Return a copy with every setting of ``domain`` unset."""
        return self._with(domain.id, {})

    def for_domain(self, domain: Domain) -> DomainValues:
        """Return the values set for ``domain``, as ``Calculator.run`` takes them."""
        return domain.values(
            **{key: entry.value for key, entry in self._values.get(domain.id, {}).items()}
        )

    def _with(self, domain_id: str, entries: Mapping[str, TypedValue]) -> DomainSettings:
        """Return a copy with ``domain_id``'s values replaced by ``entries``, already checked."""
        values = {d: v for d, v in self._values.items() if d != domain_id}
        if entries:
            values[domain_id] = dict(entries)
        settings = DomainSettings()
        object.__setattr__(settings, "_values", values)  # the field is frozen and not in __init__
        return settings
