"""Calculator families (domains) and the settings their calculators can share (ADR-0013)."""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass

from caddcalc.core import expr
from caddcalc.core.errors import SpecError
from caddcalc.core.spec import Param, Reference

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

    def find_setting(self, key: str) -> Param | None:
        """Return the setting with ``key``, or ``None`` if the domain has no such setting."""
        return next((s for s in self.settings if s.key == key), None)

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


@dataclass(frozen=True)
class DomainValues:
    """The setting values a user has set for one domain, as ``Calculator.run`` takes them.

    ``DomainSettings.for_domain()`` builds one; tests and API callers may build one directly.
    """

    domain_id: str
    """The domain these values belong to. ``run`` refuses values for another domain."""
    label: str
    """Where the values come from, as shown to users, e.g. ``"Sheet Metal settings"``."""
    values: Mapping[str, float]
    """Setting values by setting key, in base units. Unset settings are absent."""
