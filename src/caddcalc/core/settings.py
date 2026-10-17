"""The domain settings a user sets during a session (ADR-0013 §7).

Settings live only in memory: the GUI holds one ``DomainSettings`` for the life of its
window, and nothing is saved. The model is immutable; every change returns a new one.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from types import MappingProxyType

from caddcalc.core.domain import Domain, DomainValues
from caddcalc.core.errors import SpecError, UsageError
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
        """Return the option selected for ``key``, or ``None`` if there is none.

        The selection is the option the user chose, else the choice's default where the
        selections it depends on offer it.

        Raises:
            UsageError: ``domain`` has no choice with that key.
        """
        domain.choice(key)
        return _resolve(domain, self._choices.get(domain.id, {}))[0].get(key)

    def set_choice(self, domain: Domain, key: str, option: str) -> DomainSettings:
        """Return a copy with ``option`` chosen for the choice ``key``.

        ``option`` must be offered under the current selections. A choice that depends on
        ``key`` keeps its option where the new selection still offers it and loses it
        otherwise, so the change is never refused; ``cleared_choices`` names the ones lost.

        Raises:
            UsageError: ``domain`` has no choice with that key, or the choice offers no
                such option under the current selections.
        """
        domain.choice(key)
        _, kept = _resolve(domain, {**self._choices.get(domain.id, {}), key: option})
        if kept.get(key) != option:
            raise UsageError(f"Choice {key!r} of domain {domain.id!r} has no option {option!r}")
        return self._with(domain.id, choices=kept)

    def clear_choice(self, domain: Domain, key: str) -> DomainSettings:
        """Return a copy with the choice ``key`` back to its default.

        A choice that depends on ``key`` loses its option where the default doesn't offer
        it, as in ``set_choice``.

        Raises:
            UsageError: ``domain`` has no choice with that key.
        """
        domain.choice(key)
        remaining = {k: v for k, v in self._choices.get(domain.id, {}).items() if k != key}
        return self._with(domain.id, choices=_resolve(domain, remaining)[1])

    def cleared_choices(self, domain: Domain, before: DomainSettings) -> tuple[str, ...]:
        """Return the choices whose option the user chose in ``before`` and this lost.

        Only choices cleared because a selection they depend on changed are named, in
        dependency order, so a front end can announce them after ``set_choice`` or
        ``clear_choice``. The choice the user changed is never among them.
        """
        old_chosen = before._choices.get(domain.id, {})
        new_chosen = self._choices.get(domain.id, {})
        old = _resolve(domain, old_chosen)[0]
        new = _resolve(domain, new_chosen)[0]
        return tuple(
            c.key
            for c in domain.ordered_choices()
            if c.key in old_chosen
            and c.key not in new_chosen
            and any(old.get(p) != new.get(p) for p in c.depends_on)
        )

    def clear_domain(self, domain: Domain) -> DomainSettings:
        """Return a copy with ``domain``'s settings unset and its choices at their defaults.

        This is Clear all: each choice goes back to its default, not to no selection.
        """
        return self._with(domain.id, values={}, choices={})

    def for_domain(self, domain: Domain) -> DomainValues:
        """Return the values set for ``domain`` and those its choices derive, for ``run``."""
        values = domain.values(
            **{key: entry.value for key, entry in self._values.get(domain.id, {}).items()}
        )
        selections = _resolve(domain, self._choices.get(domain.id, {}))[0]
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


def _resolve(domain: Domain, chosen: Mapping[str, str]) -> tuple[dict[str, str], dict[str, str]]:
    """Return the selections in effect, and the chosen options that are still offered.

    Each choice is resolved after the choices it depends on, so its options are computed
    from their selections. A choice takes the option chosen for it if offered, else its
    default if offered, else nothing.

    Raises:
        SpecError: A choice that depends on nothing has a default it doesn't offer, a bug
            in the domain.
    """
    selections: dict[str, str] = {}
    kept: dict[str, str] = {}
    for choice in domain.ordered_choices():
        offered = {o.key for o in domain.options(choice.key, selections)}
        picked = chosen.get(choice.key)
        if picked is not None and picked in offered:
            selections[choice.key] = kept[choice.key] = picked
        elif choice.default is not None and choice.default in offered:
            selections[choice.key] = choice.default
        elif choice.default is not None and not choice.depends_on:
            raise SpecError(
                f"Domain {domain.id!r}: the default {choice.default!r} of {choice.key!r} "
                "isn't one of its options"
            )
    return selections, kept
