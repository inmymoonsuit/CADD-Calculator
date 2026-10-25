"""The domain settings a user sets during a session (ADR-0013 §7).

Settings live only in memory: the GUI holds one ``DomainSettings`` for the life of its
window, and nothing is saved. The model is immutable; every change returns a new one.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from types import MappingProxyType
from typing import Literal, NamedTuple

from caddcalc.core.domain import Domain, DomainValues, ValueOrigin
from caddcalc.core.errors import SpecError, UsageError
from caddcalc.core.units import TypedValue


class ClearedChoice(NamedTuple):
    """A choice that lost the user's option because a selection it depends on changed."""

    key: str
    outcome: Literal["default", "none"]
    """``"default"`` if it fell back to its default, ``"none"`` if nothing is selected."""


@dataclass(frozen=True)
class DomainSettings:
    """The values a user has set, and the options they have chosen, per domain.

    ``DomainSettings()`` is empty, and the methods that set values or choose options are
    the only way to add one, so everything in it has been checked against its domain.
    Models compare equal when they hold the same values, origins, choices, and pickers.
    """

    _values: Mapping[str, Mapping[str, TypedValue]] = field(default_factory=dict, init=False)
    _choices: Mapping[str, Mapping[str, str]] = field(default_factory=dict, init=False)
    """The option key chosen for each choice, by domain id and choice key."""
    _origins: Mapping[str, Mapping[str, ValueOrigin]] = field(default_factory=dict, init=False)
    """The citation of each set value the user applied, by domain id and setting key."""
    _field_choices: Mapping[str, Mapping[str, str]] = field(default_factory=dict, init=False)
    """The unit or form each setting's picker is set to, by domain id and setting key."""
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

    def origin(self, domain: Domain, key: str) -> ValueOrigin | None:
        """Return the citation of the value set for ``key``, if the user applied it.

        Raises:
            UsageError: ``domain`` has no setting with that key.
        """
        domain.setting(key)
        return self._origins.get(domain.id, {}).get(key)

    def field_choice(self, domain: Domain, key: str) -> str:
        """Return the unit or form ``key``'s picker is set to: the user's, else its first.

        A setting's picker starts as a calculator field's does (``Param.default_choice``,
        ADR-0024 E-5).

        Raises:
            UsageError: ``domain`` has no setting with that key.
        """
        setting = domain.setting(key)
        return self._field_choices.get(domain.id, {}).get(key) or setting.default_choice or ""

    def set_field_choice(self, domain: Domain, key: str, choice: str) -> DomainSettings:
        """Return a copy with ``key``'s picker set to ``choice``; its value is unchanged.

        A front end re-reads the text the user typed in the new choice, with
        ``set_text``, and shows any other value converted (ADR-0024 §2).

        Raises:
            UsageError: ``domain`` has no setting with that key, or the setting doesn't
                offer ``choice``.
        """
        setting = domain.setting(key)
        if choice not in setting.choices:
            offered = ", ".join(c or "''" for c in setting.choices)
            raise UsageError(
                f"Setting {key!r} of domain {domain.id!r} offers {offered}, not {choice!r}"
            )
        picked = {**self._field_choices.get(domain.id, {}), key: choice}
        return self._with(domain.id, field_choices=picked)

    def set_text(
        self, domain: Domain, key: str, text: str, *, decimal: str = "."
    ) -> DomainSettings:
        """Return a copy with ``key`` set from the user's text, read in its picker's choice.

        The text is read as a calculator field's is (``TypedValue.read``): its number,
        fraction or arithmetic in the picked unit, or in the picked form's grammar, and
        never with a unit of its own. A typed value has no origin, so typing over an
        applied value drops its citation.

        Args:
            domain: The domain the setting belongs to.
            key: The setting key, e.g. ``"thickness"``.
            text: What the user typed, e.g. ``"1/8"``.
            decimal: The locale's decimal mark, read besides ``"."``.

        Raises:
            UsageError: ``domain`` has no setting with that key.
            UnitInTextError: The text names a unit, which belongs in the picker.
            InputError: The text isn't a value in the picked choice.
            OutOfRangeError: The value is outside the setting's range.
        """
        setting = domain.setting(key)
        choice = self.field_choice(domain, key)
        entry = TypedValue.read(text, choice, setting.dimension, decimal=decimal)
        return self.set(domain, key, entry)

    def set(
        self,
        domain: Domain,
        key: str,
        entry: TypedValue,
        *,
        origin: ValueOrigin | None = None,
    ) -> DomainSettings:
        """Return a copy with ``key`` set to ``entry``.

        Args:
            domain: The domain the setting belongs to.
            key: The setting key, e.g. ``"k_factor"``.
            entry: The value.
            origin: The table entry of a cited value the user applied rather than typed,
                such as a K-factor starting value (ADR-0014 M2), with any note it carries.
                The value becomes the user's own and keeps the entry's citation in
                results. Without one, any earlier origin of ``key`` is dropped.

        Raises:
            UsageError: ``domain`` has no setting with that key, ``entry`` measures
                something else, or ``origin`` isn't an entry of one of the domain's
                tables that gives ``entry``'s value (``Domain.check_origin``).
            OutOfRangeError: The value is outside the setting's range.
        """
        setting = domain.setting(key)
        if origin is not None:
            domain.check_origin(origin, entry.value)
        if entry.dimension is not setting.dimension:
            raise UsageError(
                f"Setting {key!r} of domain {domain.id!r} is {setting.dimension.with_article}, "
                f"but {entry.text!r} is {entry.dimension.with_article}"
            )
        setting.check(entry.value)
        origins = _without(self._origins.get(domain.id, {}), key)
        if origin is not None:
            origins[key] = origin
        return self._with(
            domain.id, values={**self._values.get(domain.id, {}), key: entry}, origins=origins
        )

    def clear(self, domain: Domain, key: str) -> DomainSettings:
        """Return a copy with ``key`` unset.

        Raises:
            UsageError: ``domain`` has no setting with that key.
        """
        domain.setting(key)
        return self._with(
            domain.id,
            values=_without(self._values.get(domain.id, {}), key),
            origins=_without(self._origins.get(domain.id, {}), key),
        )

    def choice(self, domain: Domain, key: str) -> str | None:
        """Return the option selected for ``key``, or ``None`` if there is none.

        The selection is the option the user chose, else the choice's default where the
        selections it depends on offer it, else the offered option marked as the default
        (``Option.default``).

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

    def cleared_choices(self, domain: Domain, before: DomainSettings) -> tuple[ClearedChoice, ...]:
        """Return the choices whose option the user chose in ``before`` and this lost.

        Only choices cleared because a selection they depend on changed are named, in
        dependency order, with what each fell back to, so a front end can announce them
        after ``set_choice`` or ``clear_choice``. The choice the user changed is never
        among them.
        """
        old_chosen = before._choices.get(domain.id, {})
        new_chosen = self._choices.get(domain.id, {})
        old = _resolve(domain, old_chosen)[0]
        new = _resolve(domain, new_chosen)[0]
        return tuple(
            ClearedChoice(c.key, "default" if c.key in new else "none")
            for c in domain.ordered_choices()
            if c.key in old_chosen
            and c.key not in new_chosen
            and any(old.get(p) != new.get(p) for p in c.depends_on)
        )

    def clear_domain(self, domain: Domain) -> DomainSettings:
        """Return a copy with ``domain``'s settings unset and its choices at their defaults.

        This is Clear all: each choice goes back to its default, not to no selection. The
        pickers keep their units, as a calculator's do.
        """
        return self._with(domain.id, values={}, choices={}, origins={})

    def for_domain(self, domain: Domain) -> DomainValues:
        """Return what ``run`` takes for ``domain``.

        That is the values set, with the origins of those the user applied, the values
        its choices derive, and the selections in effect.
        """
        values = domain.values(
            **{key: entry.value for key, entry in self._values.get(domain.id, {}).items()}
        )
        selections = _resolve(domain, self._choices.get(domain.id, {}))[0]
        return replace(
            values,
            derived=domain.derived(selections),
            selections=selections,
            origins=self._origins.get(domain.id, {}),
        )

    def _with(
        self,
        domain_id: str,
        *,
        values: Mapping[str, TypedValue] | None = None,
        choices: Mapping[str, str] | None = None,
        origins: Mapping[str, ValueOrigin] | None = None,
        field_choices: Mapping[str, str] | None = None,
    ) -> DomainSettings:
        """Return a copy with some of ``domain_id``'s entries replaced, already checked."""
        settings = DomainSettings()
        # The fields are frozen and not in __init__, so they are set directly.
        object.__setattr__(settings, "_values", _replaced(self._values, domain_id, values))
        object.__setattr__(settings, "_choices", _replaced(self._choices, domain_id, choices))
        object.__setattr__(settings, "_origins", _replaced(self._origins, domain_id, origins))
        picked = _replaced(self._field_choices, domain_id, field_choices)
        object.__setattr__(settings, "_field_choices", picked)
        return settings


def _without[V](entries: Mapping[str, V], key: str) -> dict[str, V]:
    """Return a copy of ``entries`` without ``key``."""
    return {k: v for k, v in entries.items() if k != key}


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
    default if offered, else the offered option marked as the default, else nothing. A
    kept option may be offered under a different parent selection than the one it was
    chosen under.

    Raises:
        SpecError: A choice that depends on nothing has a default it doesn't offer, a bug
            in the domain.
    """
    selections: dict[str, str] = {}
    kept: dict[str, str] = {}
    for choice in domain.ordered_choices():
        options = domain.options(choice.key, selections)
        offered = {o.key for o in options}
        marked = next((o.key for o in options if o.default), None)
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
        elif marked is not None:
            selections[choice.key] = marked
    return selections, kept
