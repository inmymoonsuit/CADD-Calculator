"""What the units registry holds: dimensions, units, and how each dimension is shown.

Standard library only (ADR-0003). The registry (``units.unit_registry``) validates every unit
it takes; the built-ins are declared in ``units.builtin`` (ADR-0019 §2, §4).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from fractions import Fraction
from types import MappingProxyType

from caddcalc.core.citations import Source
from caddcalc.core.errors import SpecError
from caddcalc.core.i18n import npgettext_shown
from caddcalc.core.reference import Reference

type Exact = Fraction | Decimal
"""A unit's factor as its exact definition: a rational where one exists, and otherwise a
high-precision decimal (the radian's 180/π)."""


class Dimension(Enum):
    """What a quantity measures. Each dimension has one base unit (``BASE_UNITS``)."""

    LENGTH = "length"
    ANGLE = "angle"
    RATIO = "ratio"
    STRESS = "stress"
    AREA = "area"

    @property
    def with_article(self) -> str:
        """The name with its indefinite article, for messages, e.g. ``"an angle"``."""
        # The registry declares it; it imports this module, so it's asked here, late.
        from caddcalc.core.units.unit_registry import registry

        return registry().dimension(self).article


class UnitSystem(Enum):
    """The system a unit belongs to (ADR-0019 §2)."""

    SI = "si"
    ACCEPTED = "accepted"
    """Outside the SI but accepted for use with it: the degree, minute, and second (NIST
    SP 811, Table 6)."""
    US_CUSTOMARY = "us_customary"
    NONE = "none"
    """No system: a plain ratio, or the percent."""


CLOSE_UP_SYMBOLS = frozenset({"°", "′", "″"})
"""The only symbols written against their number, as in ``90°`` (NIST SP 811 §7.2)."""
NAME_CONTEXT = "unit"
"""The translation context of units' names, so "degree" and "foot" are the units. Each
declaration names it literally, ``NP_("unit", …)``, for the extractor to read."""


@dataclass(frozen=True)
class Unit:
    """A unit of measure: how it's written and named, and its factor to the base unit.

    A unit the registry takes declares everything below; a bare ``Unit`` built with only
    the first fields still converts, as it always has.
    """

    symbol: str
    """Its key symbol, public in JSON, e.g. ``"mm"`` or ``"deg"``; ``""`` for a ratio."""
    name: str
    dimension: Dimension
    factor: float
    """Multiply a value in this unit by ``factor`` to get base units: ``exact``, rounded
    once to the nearest double."""
    aliases: tuple[str, ...] = ()
    """Other texts it's typed as, e.g. ``"inches"`` or ``'"'``."""
    spoken_plural: str = ""
    """The unit's name for any amount but exactly one, e.g. ``"inches"``, as a screen reader
    says it (ADR-0017 §5). A unitless ratio has none: only its number is spoken."""
    written: str = ""
    """The symbol written after a number, e.g. ``"°"`` for ``"deg"``; the key symbol when
    empty."""
    exact: Exact | None = None
    """The factor's exact definition, e.g. ``Fraction("25.4")``, for checks and exact
    conversion, never for arithmetic at run time (ADR-0013 §9)."""
    system: UnitSystem | None = None
    close_up: bool = False
    """Written against its number, as ``90°`` is; only for °, ′, and ″ (SP 811 §7.2)."""
    fractions: bool = False
    """Whether values in it may also show the nearest drafting fraction (the inch)."""
    sources: tuple[Source, ...] = ()
    """Its citations: where its definition and factor come from."""
    case_sensitive: bool = False
    """Whether its symbol and aliases match only in their own case, as a future ``Mm``
    beside ``mm`` would need to; units match in any case otherwise."""
    power_of: str = ""
    """The key symbol of the unit this one is a power of, e.g. ``"in"`` for in², in a
    dimension declared as a power of another (``DimensionSpec.derivation``). Its factor
    is then that unit's exact factor to the power, which the registry checks."""

    def __post_init__(self) -> None:
        if not self.written:
            object.__setattr__(self, "written", self.symbol)

    @property
    def keys(self) -> tuple[str, ...]:
        """The texts it's found by: its key symbol, when it has one, and its aliases."""
        return tuple(dict.fromkeys(k for k in (self.symbol, *self.aliases) if k))

    @property
    def reference(self) -> Reference | None:
        """Its first citation, if it has one."""
        return self.sources[0].reference if self.sources else None

    def spoken(self, shown: str) -> str:
        """Return the unit's name as spoken after the number ``shown``, e.g. ``"inches"``.

        It's in the language text is shown in, and its form follows the number's plural
        category there (ADR-0020 §5): in English, singular only after a shown ``1``, so
        ``1.0000 in`` is "1.0000 inches".
        """
        if not self.symbol:
            return ""
        return npgettext_shown(NAME_CONTEXT, self.name, self.spoken_plural, shown)


@dataclass(frozen=True)
class Precision:
    """How many digits a value is shown with: decimal places, or significant figures.

    Raises:
        SpecError: ``digits`` is negative, or zero significant figures.
    """

    digits: int
    significant: bool = False
    """Whether ``digits`` counts significant figures, rather than decimal places."""

    def __post_init__(self) -> None:
        least = 1 if self.significant else 0
        if isinstance(self.digits, bool) or not isinstance(self.digits, int) or self.digits < least:
            kind = "significant figures" if self.significant else "decimal places"
            raise SpecError(f"A precision needs at least {least} {kind}, not {self.digits!r}")


@dataclass(frozen=True)
class Derivation:
    """A dimension that is a power of another, as an area is a length squared."""

    of: Dimension
    power: int


@dataclass(frozen=True)
class DimensionSpec:
    """A dimension's declaration: its base unit, how it's shown, and its precision."""

    dimension: Dimension
    article: str
    """Its name with its indefinite article, e.g. ``"an angle"``."""
    base: str
    """Its base unit's key symbol: every calculation runs in it (ADR-0005)."""
    precision: Precision
    """The precision it's shown with when no preference says otherwise: decimal places,
    or, for an area, significant figures, since one area may be 6451.60 mm² and another
    10.0000 in²."""
    follows_length: bool = False
    """Shown in the length unit the user chose, or, for a power of a length, in that
    unit's power: a length in inches, an area in square inches."""
    shown_with: Mapping[UnitSystem, str] = field(default_factory=dict)
    """The unit it's shown in, by the system of the length unit the user chose; the base
    unit for any other system. Stress shows ksi beside inch-pound lengths."""
    derivation: Derivation | None = None
    """What it's a power of, if anything: an area is a length squared, so its squares are
    generated from the lengths, and it's shown in the square of the length unit chosen."""
    fixed: Precision = Precision(6, significant=True)
    """The precision a value is shown with in a unit an output fixes, whatever the
    preferences, as a converter's rows are (ADR-0018 §3)."""

    def __post_init__(self) -> None:
        object.__setattr__(self, "shown_with", MappingProxyType(dict(self.shown_with)))
