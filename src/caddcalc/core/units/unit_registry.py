"""The units registry: the one source of unit knowledge (ADR-0019).

It holds the declared dimensions and every unit, built-in or from a plugin, and answers
what parsing and display ask: which unit a text names, which unit a dimension is shown
in, and how a symbol is written. Each unit is checked as it's registered; the registry is
built once, on first use, frozen, and cached, with ``clear_registry`` for tests.
"""

from __future__ import annotations

import string
from collections.abc import Callable, Iterable
from decimal import Decimal
from fractions import Fraction
from functools import cache
from importlib import metadata

from caddcalc.core.errors import InputError, SpecError, UsageError
from caddcalc.core.plugins import EntryPointSource, PluginError, load_group
from caddcalc.core.units import builtin, compound
from caddcalc.core.units.compound import CompoundForm
from caddcalc.core.units.model import (
    CLOSE_UP_SYMBOLS,
    Dimension,
    DimensionSpec,
    Precision,
    Unit,
    UnitSystem,
)

ENTRY_POINT_GROUP = "caddcalc.units"
"""Where installed packages advertise units: a ``Unit``, or an iterable of them (U2)."""

_UNSAFE_STARTS = frozenset("+-/.eE") | frozenset(string.digits)
"""What no unit text may start with, so a number and its unit can't be read two ways:
digits, signs, a fraction's slash, a decimal point, and an exponent's e."""


class UnitRegistry:
    """Dimensions and units, checked as they're registered, then frozen for use."""

    def __init__(self, dimensions: Iterable[DimensionSpec]) -> None:
        self._dimensions = {spec.dimension: spec for spec in dimensions}
        missing = set(Dimension) - set(self._dimensions)
        if missing:
            raise SpecError(
                f"Every dimension needs a declaration: {sorted(d.value for d in missing)}"
            )
        self._units: list[Unit] = []
        self._frozen = False
        self.plugin_errors: list[PluginError] = []
        """Plugin units that failed to register, each with its reason (U2)."""
        self._word_chars = frozenset(string.ascii_letters)
        self._by_name: dict[str, list[Unit]] = {}
        """Units by each symbol and alias: casefolded, or as written for a case-sensitive
        unit, which ``_names`` then checks."""
        self._lengths: list[int] = []
        """Every name's length, longest first."""
        self._reserved: dict[str, Unit] = {}
        """The built-ins' names, casefolded: no later unit takes one, in any dimension."""
        self._compounds: dict[str, CompoundForm] = {}

    @property
    def frozen(self) -> bool:
        """Whether it takes no more units."""
        return self._frozen

    def freeze(self) -> None:
        """Take no more units; the registry is frozen before first use."""
        self._frozen = True

    def reserve(self) -> None:
        """Keep every name registered so far from any later unit, in any dimension.

        Called once the built-ins are in, so a plugin unit of another dimension can't take
        a built-in's name, which would make that name ambiguous wherever its dimension
        isn't given, and so break the built-in (U2: built-ins always win).
        """
        for unit in self._units:
            for key in unit.keys:
                self._reserved.setdefault(key.casefold(), unit)

    def register(self, unit: Unit) -> None:
        """Add ``unit``, after checking it (ADR-0019 §5).

        Raises:
            UsageError: The registry is frozen.
            SpecError: The unit lacks a part every unit declares, has an unsafe or taken
                symbol or alias, or its factor isn't its exact definition rounded once.
        """
        if self._frozen:
            raise UsageError(f"The units registry is frozen; {unit.symbol!r} came too late")
        self._check(unit)
        self._units.append(unit)
        for key in unit.keys:
            self._by_name.setdefault(key.casefold(), []).append(unit)
            self._word_chars |= {c for c in key if not c.isdigit() and not c.isspace()}
        self._lengths = sorted({len(name) for name in self._by_name}, reverse=True)

    def _check(self, unit: Unit) -> None:
        where = f"unit {unit.symbol!r} ({unit.name or '?'})"
        spec = self._dimensions.get(unit.dimension)
        if spec is None:
            raise SpecError(f"{where}: its dimension isn't declared")
        if not unit.symbol and spec.base != "":
            raise SpecError(f"{where}: only a dimension whose base unit is unnamed has one")
        if not unit.name or (unit.symbol and not unit.spoken_plural):
            raise SpecError(f"{where}: it needs a name and a plural")
        if unit.system is None:
            raise SpecError(f"{where}: it needs a system, or UnitSystem.NONE")
        if not unit.sources:
            raise SpecError(f"{where}: it needs a citation")
        if not isinstance(unit.exact, Fraction | Decimal):
            raise SpecError(f"{where}: its factor needs an exact definition")
        if float(unit.exact) != unit.factor:
            raise SpecError(f"{where}: its factor must be its exact definition, rounded once")
        if unit.written and unit.written not in unit.keys:
            raise SpecError(f"{where}: it must read back the symbol it's written with")
        if unit.close_up and unit.written not in CLOSE_UP_SYMBOLS:
            raise SpecError(f"{where}: only °, ′, and ″ are written close up (SP 811 §7.2)")
        self._check_power(unit, spec, where)
        if any(not alias for alias in unit.aliases):
            raise SpecError(f"{where}: an alias is empty")
        for key in unit.keys:
            if key != key.strip() or key[0] in _UNSAFE_STARTS:
                raise SpecError(f"{where}: {key!r} can't be told from the number before it")
            built_in = self._reserved.get(key.casefold())
            if built_in is not None:
                raise SpecError(
                    f"{where}: {key!r} is the built-in unit {built_in.symbol!r} "
                    f"({built_in.name}), in any dimension"
                )
        # An unnamed unit is its dimension's one, as a ratio's or a count's is, so "" is
        # taken only within a dimension.
        holders = [u for u in self._units if u.symbol == unit.symbol]
        if any(unit.symbol or u.dimension is unit.dimension for u in holders):
            raise SpecError(f"{where}: the symbol {unit.symbol!r} is taken")
        for other in self.units_for(unit.dimension):
            for key in unit.keys:
                for taken in other.keys:
                    both = unit.case_sensitive and other.case_sensitive
                    if key == taken or (not both and key.casefold() == taken.casefold()):
                        raise SpecError(
                            f"{where}: {key!r} is already {taken!r}, unit {other.symbol!r} "
                            f"({other.name})"
                        )

    def _check_power(self, unit: Unit, spec: DimensionSpec, where: str) -> None:
        """Check a unit declared as a power of another, such as in², against its root."""
        if not unit.power_of:
            return
        derivation = spec.derivation
        if derivation is None:
            raise SpecError(f"{where}: {unit.dimension.value} isn't a power of a dimension")
        root = next((u for u in self.units_for(derivation.of) if u.symbol == unit.power_of), None)
        if root is None or root.exact is None:
            raise SpecError(
                f"{where}: it's a power of {unit.power_of!r}, which isn't "
                f"{self._dimensions[derivation.of].article} unit registered before it"
            )
        if unit.exact != root.exact**derivation.power:
            raise SpecError(
                f"{where}: its factor must be {root.symbol!r}'s exact factor to the power "
                f"{derivation.power}"
            )

    def register_compound(self, form: CompoundForm) -> None:
        """Add a compound form, such as feet and inches, for its dimension (ADR-0019 §2).

        Raises:
            UsageError: The registry is frozen.
            SpecError: Its key is taken, or its full-precision unit isn't a unit of its
                dimension.
        """
        if self._frozen:
            raise UsageError(f"The units registry is frozen; {form.key!r} came too late")
        if form.key in self._compounds:
            raise SpecError(f"compound form {form.key!r}: the key is taken")
        if not any(u.symbol == form.full_unit for u in self.units_for(form.dimension)):
            raise SpecError(
                f"compound form {form.key!r}: {form.full_unit!r} isn't "
                f"{self._dimensions[form.dimension].article} unit"
            )
        self._compounds[form.key] = form

    def compounds_for(self, dimension: Dimension) -> tuple[CompoundForm, ...]:
        """Return the compound forms of ``dimension``, which the parser tries first."""
        return tuple(f for f in self._compounds.values() if f.dimension is dimension)

    def compound(self, key: str) -> CompoundForm:
        """Return the compound form ``key`` names, e.g. ``"ft_in"``.

        Raises:
            UsageError: No compound form has that key.
        """
        try:
            return self._compounds[key]
        except KeyError:
            known = ", ".join(self._compounds)
            raise UsageError(f"No compound form {key!r}; there's {known}") from None

    @property
    def units(self) -> tuple[Unit, ...]:
        """Every unit, in the order registered."""
        return tuple(self._units)

    def units_for(self, dimension: Dimension) -> tuple[Unit, ...]:
        """Return every unit of ``dimension``."""
        return tuple(u for u in self._units if u.dimension is dimension)

    def dimension(self, dimension: Dimension) -> DimensionSpec:
        """Return ``dimension``'s declaration."""
        return self._dimensions[dimension]

    def find(self, text: str, dimension: Dimension | None = None) -> Unit:
        """Return the unit ``text`` names, e.g. ``in``, ``"`` or ``mm``, in any case.

        Args:
            text: A symbol or alias.
            dimension: The dimension it's expected to be of. A unit of that dimension wins
                where units of several share the name; with none of that dimension, the
                unit of whatever dimension has it is returned, so the caller can say it
                measures the wrong thing. With none given, a length wins, so ``'`` is
                the foot, not the minute of arc.

        Raises:
            InputError: No unit has that name.
            UsageError: Units of several dimensions have it, and none is of ``dimension``
                (or, with none given, a length).
        """
        key = text.strip()
        if key:
            named = [u for u in self._by_name.get(key.casefold(), ()) if _names(u, key)]
        else:
            named = [u for u in self._units if not u.symbol]
        # With no dimension given, a length, so ' and " are the foot and inch, which
        # callers of the public lookups expect (ADR-0019, amendments).
        own = [u for u in named if u.dimension is (dimension or Dimension.LENGTH)]
        # A bare number where the dimension has no unnamed unit is the ratio's, so the
        # caller says it measures the wrong thing (ADR-0019, amendments).
        found = own or (named if key else [u for u in named if u.dimension is Dimension.RATIO])
        if not found:
            raise InputError(f"Unknown unit {text!r}")
        if len(found) > 1:
            dimensions = ", ".join(u.dimension.value for u in found)
            raise UsageError(f"{text!r} names units of several dimensions ({dimensions}); give one")
        return found[0]

    def written(self, written: str) -> Unit | None:
        """Return the unit written as ``written`` after a number, e.g. ``"°"``, if any."""
        return next((u for u in self._units if u.written == written), None)

    def shown_unit(self, dimension: Dimension, length: Unit) -> Unit:
        """Return the unit ``dimension`` is shown in, beside the length unit ``length``."""
        spec = self._dimensions[dimension]
        if spec.follows_length and spec.derivation is None:
            return length
        if spec.follows_length:
            # The power of the chosen length, or the base unit where it has none declared.
            power = next(
                (u for u in self.units_for(dimension) if u.power_of == length.symbol), None
            )
            return power or self.find(spec.base, dimension)
        system = length.system or UnitSystem.NONE
        return self.find(spec.shown_with.get(system, spec.base), dimension)

    def precision_for(self, unit: Unit) -> Precision:
        """Return the precision a value is shown with in ``unit`` when an output fixes it.

        That's its dimension's declared one, whatever the display preferences (ADR-0018
        §3): a converter's millimetre row reads the same when the app shows inches.
        """
        return self._dimensions[unit.dimension].fixed

    def ending(self, text: str, dimension: Dimension) -> tuple[Unit, int] | None:
        """Return the unit whose symbol or alias ends ``text``, and that name's length.

        The longest name wins, so "3mm" can't read as metres, and a unit of ``dimension``
        wins a tie. A name counts only as a whole word: one preceded by a letter, or by
        a character other units are written with, belongs to a longer unknown unit.
        """
        for n in self._lengths:
            if n > len(text) or (n < len(text) and text[-n - 1] in self._word_chars):
                continue
            tail = text[-n:]
            named = [u for u in self._by_name.get(tail.casefold(), ()) if _names(u, tail)]
            if named:
                return next((u for u in named if u.dimension is dimension), named[0]), n
        return None

    def trailing_word(self, text: str) -> str:
        """Return the run of unit characters that ends ``text``: an unknown unit's name."""
        end = len(text)
        start = end
        while start > 0 and text[start - 1] in self._word_chars:
            start -= 1
        return text[start:end]


def _names(unit: Unit, text: str) -> bool:
    """Whether ``text`` is one of ``unit``'s symbol or aliases, in its case rule."""
    if unit.case_sensitive:
        return text in unit.keys
    folded = text.casefold()
    return any(folded == key.casefold() for key in unit.keys)


def build_registry(
    *, load_plugins: bool = True, entry_points: EntryPointSource = metadata.entry_points
) -> UnitRegistry:
    """Return a frozen registry of the built-in units and, if asked, plugins' units.

    Built-ins always win: a plugin unit that takes a built-in's symbol or alias fails
    with an error naming both, and is skipped, never stopping the app (U2).
    """
    built = UnitRegistry(builtin.DIMENSIONS)
    for unit in builtin.UNITS:
        built.register(unit)
    for form in compound.FORMS:
        built.register_compound(form)
    built.reserve()
    if load_plugins:
        built.plugin_errors += load_group(entry_points, ENTRY_POINT_GROUP, Unit, _registrar(built))
    built.freeze()
    return built


def _registrar(target: UnitRegistry) -> Callable[[object], None]:
    def register(item: object) -> None:
        if not isinstance(item, Unit):
            raise SpecError(f"{item!r} isn't a Unit")
        target.register(item)

    return register


@cache
def registry() -> UnitRegistry:
    """Return the units registry, built once on first use with installed plugins' units."""
    return build_registry()


def clear_registry() -> None:
    """Forget the built registry, so the next use builds it again; for tests."""
    registry.cache_clear()
