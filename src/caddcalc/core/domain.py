"""Calculator families (domains) and the settings their calculators can share (ADR-0013)."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from types import MappingProxyType

from caddcalc.core import expr
from caddcalc.core.choices import OPTION_KEY, Choice, ChoiceResolver, DerivedValue, Option
from caddcalc.core.errors import InputError, SpecError, UsageError
from caddcalc.core.reference import Reference
from caddcalc.core.spec import Param

_DOMAIN_ID = re.compile(r"[a-z][a-z0-9_]*")


@dataclass(frozen=True)
class Domain:
    """A family of calculators, such as sheet metal, and the settings they can share.

    A setting is a ``Param`` that a user may set once for the whole family. Settings have
    no default: an unset setting means each calculator uses its own default (ADR-0013).
    """

    id: str
    """Stable identifier, e.g. ``"sheet_metal"``. Calculators name their domain by it."""
    name: str
    """Display name, e.g. ``"Sheet Metal"``."""
    summary: str
    settings: tuple[Param, ...] = ()
    references: tuple[Reference, ...] = ()
    choices: tuple[Choice, ...] = ()
    """Selections the domain offers, such as a gauge, that derive setting values."""
    resolver: ChoiceResolver | None = field(default=None, compare=False)
    """Supplies the choices' options and derived values; required when there are choices."""

    @property
    def settings_label(self) -> str:
        """The source label of a value from these settings, e.g. ``"Sheet Metal settings"``."""
        return f"{self.name} settings"

    def find_setting(self, key: str) -> Param | None:
        """Return the setting with ``key``, or ``None`` if the domain has no such setting."""
        return next((s for s in self.settings if s.key == key), None)

    def setting(self, key: str) -> Param:
        """Return the setting with ``key``.

        Raises:
            UsageError: The domain has no such setting. The message lists the ones it has.
        """
        setting = self.find_setting(key)
        if setting is None:
            known = ", ".join(s.key for s in self.settings) or "none"
            raise UsageError(
                f"Domain {self.id!r} has no setting {key!r}; its settings are: {known}"
            )
        return setting

    def choice(self, key: str) -> Choice:
        """Return the choice with ``key``.

        Raises:
            UsageError: The domain has no such choice.
        """
        found = next((c for c in self.choices if c.key == key), None)
        if found is None:
            known = ", ".join(c.key for c in self.choices) or "none"
            raise UsageError(f"Domain {self.id!r} has no choice {key!r}; its choices are: {known}")
        return found

    def options(self, key: str) -> Sequence[Option]:
        """Return the options of the choice with ``key``, in display order.

        Raises:
            UsageError: The domain has no such choice.
        """
        self.choice(key)
        return () if self.resolver is None else self.resolver.options(key)

    def derived(self, selections: Mapping[str, str]) -> Mapping[str, DerivedValue]:
        """Return the values ``selections`` give this domain's settings, checked.

        Raises:
            SpecError: The resolver gives a value for a key that isn't a setting, or one
                outside its setting's range. Either is a bug in the domain.
        """
        if not selections or self.resolver is None:
            return MappingProxyType({})
        derived = dict(self.resolver.derive(selections))
        for key, value in derived.items():
            setting = self.find_setting(key)
            if setting is None:
                raise SpecError(f"Domain {self.id!r} derives {key!r}, which isn't a setting")
            try:
                setting.check(value.value, value.source)
            except InputError as exc:
                raise SpecError(f"Domain {self.id!r} derives a bad {key!r}: {exc}") from exc
        return MappingProxyType(derived)

    def values(self, **by_key: float) -> DomainValues:
        """Return checked setting values for ``Calculator.run``, e.g. ``values(thickness=2.0)``.

        Args:
            **by_key: Values by setting key, in base units.

        Raises:
            UsageError: A key isn't a setting of this domain.
            OutOfRangeError: A value is outside its setting's range.
        """
        for key, value in by_key.items():
            self.setting(key).check(value)
        return DomainValues(self.id, self.settings_label, by_key)

    def validate(self) -> None:
        """Check the definition. Registration calls this so plugin mistakes fail early.

        Raises:
            SpecError: The ID is malformed, the name is empty, a setting key or symbol
                repeats, a symbol isn't usable in formulas, or a setting has a default or
                is limited to particular methods.
        """
        if not _DOMAIN_ID.fullmatch(self.id):
            raise SpecError(
                f"Domain id {self.id!r} must be lowercase letters, digits, and underscores"
            )
        if not self.name.strip():
            raise SpecError(f"Domain {self.id!r} needs a name")
        keys: set[str] = set()
        symbols: set[str] = set()
        for setting in self.settings:
            if setting.key in keys:
                raise SpecError(f"Domain {self.id!r}: duplicate setting {setting.key!r}")
            keys.add(setting.key)
            if not expr.is_usable_symbol(setting.symbol):
                raise SpecError(
                    f"Domain {self.id!r}: setting symbol {setting.symbol!r} is not usable "
                    "in formulas"
                )
            if setting.symbol in symbols:
                raise SpecError(f"Domain {self.id!r}: duplicate setting symbol {setting.symbol!r}")
            symbols.add(setting.symbol)
            if setting.default is not None:
                raise SpecError(
                    f"Domain {self.id!r}: setting {setting.key!r} must not have a default; "
                    "unset means each calculator uses its own"
                )
            if setting.methods:
                raise SpecError(
                    f"Domain {self.id!r}: setting {setting.key!r} must not be limited to methods"
                )

    def validate_choices(self) -> None:
        """Check the choices and their options. Registration calls this after ``validate``.

        Choices have their own check because, unlike a setting, a choice may have a
        default (ADR-0014 §2).

        Raises:
            SpecError: A choice key is malformed, repeats, or is also a setting key; there
                is no resolver; or an option key is malformed or repeats, an option has no
                label, or a default isn't one of the choice's options.
        """
        if self.choices and self.resolver is None:
            raise SpecError(f"Domain {self.id!r} has choices but no resolver for them")
        keys: set[str] = {s.key for s in self.settings}
        for choice in self.choices:
            if not choice.key.isidentifier() or choice.key in keys:
                raise SpecError(
                    f"Domain {self.id!r}: choice key {choice.key!r} is malformed or already used"
                )
            keys.add(choice.key)
            option_keys: set[str] = set()
            for option in self.options(choice.key):
                if not OPTION_KEY.fullmatch(option.key) or option.key in option_keys:
                    raise SpecError(
                        f"Domain {self.id!r}: option key {option.key!r} of {choice.key!r} is "
                        "malformed or repeats; option keys look like 'group:item'"
                    )
                if not option.label.strip():
                    raise SpecError(f"Domain {self.id!r}: option {option.key!r} needs a label")
                option_keys.add(option.key)
            if choice.default is not None and choice.default not in option_keys:
                raise SpecError(
                    f"Domain {self.id!r}: default {choice.default!r} of {choice.key!r} is not "
                    "one of its options"
                )


@dataclass(frozen=True)
class DomainValues:
    """The setting values a user has set for one domain, as ``Calculator.run`` takes them.

    ``Domain.values()`` and ``DomainSettings.for_domain()`` build checked ones. Building one
    directly checks only that it has a label: keys and ranges aren't checked against the
    domain, and ``run`` ignores a key that no shared parameter uses.
    """

    domain_id: str
    """The domain these values belong to. ``run`` refuses values for another domain."""
    label: str
    """Where the values come from, as shown to users. ``Domain.settings_label`` gives it."""
    values: Mapping[str, float]
    """Setting values by setting key, in base units. Unset settings are absent.

    Stored as a read-only copy, so changing the mapping passed in doesn't change these.
    """
    derived: Mapping[str, DerivedValue] = field(default_factory=dict)
    """Values the domain's choices derive, by setting key. A set value above takes
    precedence over a derived one (ADR-0013 §4). Stored as a read-only copy.
    """

    def __post_init__(self) -> None:
        if not self.label.strip():
            raise UsageError(
                f"DomainValues for {self.domain_id!r} needs a label; use Domain.values()"
            )
        object.__setattr__(self, "values", MappingProxyType(dict(self.values)))
        object.__setattr__(self, "derived", MappingProxyType(dict(self.derived)))
