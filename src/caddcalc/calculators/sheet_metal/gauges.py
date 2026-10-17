"""Gauge systems: the gauge choice and the thickness each gauge gives (ADR-0014 §2).

``data/gauges.toml`` holds each system's definition: the statute's weights, the cited
constants, and each system's range and published precision. The formulas live here, each
written once: ``expr.evaluate_exact`` evaluates it, the derived value's work shows it, and
``nominal()`` states the result at its system's precision, so a derived thickness is the
system's own published value.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from decimal import (
    ROUND_DOWN,
    ROUND_HALF_EVEN,
    ROUND_HALF_UP,
    Decimal,
    InvalidOperation,
    localcontext,
)
from fractions import Fraction
from functools import cached_property
from types import MappingProxyType
from typing import Any

from caddcalc.core import (
    Basis,
    Choice,
    DerivedValue,
    InputSource,
    Note,
    NoteKind,
    Option,
    Param,
    ReferenceTable,
    ReferenceValue,
    SourceKind,
    SpecError,
    Step,
    TablePublication,
    TableSpec,
    TrustLevel,
    TypedValue,
    UsageError,
    expr,
    nominal,
)

GAUGE = Choice(
    "gauge",
    "Gauge",
    help=(
        "A gauge system and number. Choosing one fills the thickness with the gauge's "
        "nominal value, and a thickness you set takes precedence. The system matters: "
        "12 ga is a different thickness in each."
    ),
)
"""The sheet-metal domain's gauge choice. Its option keys, e.g. ``"msg:12"``, are public."""


def caution(standards: Sequence[TablePublication]) -> str:
    """Return the note a result carries whenever it uses a gauge's thickness (ADR-0014 §5.5).

    It points to the system's tolerance standards, e.g. "Nominal thickness; mill
    tolerances apply (see ASTM A568/A568M, 2025, rev. a). Check the material's
    specification or measure before cutting."
    """
    cited = " and ".join(f"{s.title}, {s.edition}" for s in standards)
    return (
        f"Nominal thickness; mill tolerances apply (see {cited}). "
        "Check the material's specification or measure before cutting."
    )


FORMULA_UNIT = "in"
"""The unit every gauge formula yields, and the stated thicknesses' unit."""

WORKING_DIGITS = 40
"""Significant digits for a thickness with no exact form, such as AWG's, before rounding."""


@dataclass(frozen=True)
class Formula:
    """How a kind of gauge system turns a gauge into a thickness in inches.

    The expression is written once: it is evaluated exactly and shown as the work.
    """

    expression: str
    constants: frozenset[str]
    """The symbols a system supplies from the table's constants."""
    per_gauge: str
    """The symbol each gauge supplies: ``"w"``, its weight, or ``"n"``, its index."""
    defaults: Mapping[str, Decimal] = MappingProxyType({})
    """Constants a system may leave out, e.g. no coating."""

    def evaluate(self, symbols: Mapping[str, Decimal]) -> Fraction:
        """Return the thickness in inches, evaluated exactly (ADR-0014, amendments)."""
        return expr.evaluate_exact(self.expression, symbols, digits=WORKING_DIGITS)


FORMULAS: Mapping[str, Formula] = MappingProxyType(
    {
        "weight": Formula(
            "(w + c) / 16 / B",
            frozenset({"B", "c"}),
            "w",
            MappingProxyType({"c": Decimal(0)}),
        ),
        "awg": Formula(
            "d36 * (d0000 / d36) ** ((36 - n) / 39)",
            frozenset({"d0000", "d36"}),
            "n",
        ),
    }
)
"""The formulas by name, as a system's ``formula`` names them.

* ``weight``: a weight gauge. ``w`` is the gauge's weight and ``c`` its coating, in
  oz/ft²; 16 is ounces per pound; ``B`` is the basis, in lb/ft² per inch of thickness.
* ``awg``: AWG size ``n``, where No. 0000 is ``n = -3``: 39 equal ratios from No. 0000
  (``d0000``) down to No. 36 (``d36``).
"""

_ROUNDING = MappingProxyType(
    {"half_up": ROUND_HALF_UP, "half_even": ROUND_HALF_EVEN, "down": ROUND_DOWN}
)
_SIZE = re.compile(r"0+|[1-9][0-9]*")
_MULTI_ZERO = re.compile(r"([1-9])/0")


def designation(text: str) -> str:
    """Return a gauge size as its item key, e.g. ``"0000000"`` for MH29's ``"7/0"``.

    Raises:
        UsageError: ``text`` isn't a gauge size.
    """
    size = text.strip()
    if match := _MULTI_ZERO.fullmatch(size):
        return "0" * int(match.group(1))
    if _SIZE.fullmatch(size):
        return size
    raise UsageError(f"{text!r} isn't a gauge size, e.g. 12, 0000, or 4/0")


def _index(size: str) -> int:
    """Return a size's place in the sequence: 0 is 0, 00 is -1, 0000 is -3, 12 is 12."""
    return 1 - len(size) if set(size) == {"0"} else int(size)


def _label(size: str, suffix: str) -> str:
    """Return how a size reads, e.g. ``"12 ga"``, or ``"4/0 AWG"`` for 0000."""
    shown = f"{len(size)}/0" if len(size) > 1 and set(size) == {"0"} else size
    return f"{shown} {suffix}"


@dataclass(frozen=True)
class Precision:
    """How a system states its thicknesses: its published decimals and rounding."""

    decimals: int | None
    """Decimal places; ``None`` states the exact terminating decimal."""
    rounding: str = ROUND_HALF_UP
    below: Decimal | None = None
    """Thicknesses under this are stated with ``decimals_below`` places instead."""
    decimals_below: int | None = None

    def places(self, exact: Fraction) -> int:
        """Return how many decimal places the system states ``exact`` inches with."""
        if self.decimals is None:
            return _terminating_places(exact)
        if self.below is not None and self.decimals_below is not None and exact < self.below:
            return self.decimals_below
        return self.decimals

    def state(self, exact: Fraction) -> TypedValue:
        """Return ``exact`` inches as the system states it, e.g. ``"0.1046 in"``."""
        return nominal(exact, FORMULA_UNIT, self.places(exact), self.rounding)

    def explain(self, exact: Fraction) -> str:
        """Say how ``exact`` inches became the stated value, for the derived value's work."""
        if self.decimals is None:
            return "exact, as the system states it"
        return f"{_approx(exact)} in before rounding to {self.places(exact)} decimal places"


def _approx(value: Fraction) -> str:
    """Return ``value`` to 10 significant digits, with an ellipsis if that isn't exact."""
    with localcontext() as context:
        context.prec = 10
        shown = Decimal(value.numerator) / Decimal(value.denominator)
    return f"{shown:f}" + ("" if Fraction(shown) == value else "…")


def _terminating_places(value: Fraction) -> int:
    for places in range(16):
        if (value * 10**places).denominator == 1:
            return places
    raise SpecError(f"{value} has no short exact decimal; give the system a precision")


@dataclass(frozen=True)
class Gauge:
    """One gauge of a system: its option and its thickness."""

    key: str
    """The option key, e.g. ``"msg:12"``."""
    label: str
    """How it reads, e.g. ``"12 ga"``."""
    symbols: Mapping[str, Decimal]
    """The formula's inputs for this gauge, for show-work."""
    exact: Fraction
    """The thickness in inches, evaluated exactly (to ``WORKING_DIGITS`` for a non-integer
    power)."""
    stated: TypedValue
    """The thickness at its system's precision, e.g. ``"0.1046 in"``."""


@dataclass(frozen=True)
class GaugeSystem:
    """A gauge system: its formula, its gauges, and the caution its thicknesses carry."""

    id: str
    name: str
    scope: str
    formula: Formula
    precision: Precision
    gauges: tuple[Gauge, ...]
    note: Note

    @property
    def group(self) -> str:
        """The system as its options' group, e.g. ``"Manufacturers' Standard"``."""
        return f"{self.name}, {self.scope}" if self.scope else self.name


@dataclass(frozen=True)
class GaugeSystems:
    """Every gauge system the table defines, in its order."""

    table: ReferenceTable
    systems: tuple[GaugeSystem, ...]
    options: tuple[Option, ...]
    by_key: Mapping[str, tuple[GaugeSystem, Gauge]]
    values: tuple[ReferenceValue, ...]
    """Every value the table defines, constants and thicknesses, as checked (ADR-0014 §5)."""

    def key(self, system: str, size: str) -> str:
        """Return the option key of ``size`` in ``system``, e.g. ``key("uss", "7/0")``.

        Raises:
            UsageError: ``size`` isn't a gauge size, or the system doesn't define it.
        """
        key = f"{system}:{designation(size)}"
        if key not in self.by_key:
            raise UsageError(f"Gauge system {system!r} has no gauge {size!r}")
        return key


def load_gauges(table: ReferenceTable) -> GaugeSystems:
    """Build every gauge system from the gauge table, and check its values (ADR-0014 §5).

    Raises:
        SpecError: The table's content is malformed or inconsistent.
    """
    constants, values = _constants(table)
    weights = _weights(table)
    systems: list[GaugeSystem] = []
    for entry in _list(table.data, "system"):
        system, thicknesses = _system(table, entry, constants, weights)
        systems.append(system)
        values.extend(thicknesses)
    ids = [s.id for s in systems]
    if len(set(ids)) != len(ids):
        raise SpecError(f"{table.name}: a gauge system id repeats in {ids}")
    table.check_values(values)
    by_key = {gauge.key: (system, gauge) for system in systems for gauge in system.gauges}
    options = tuple(
        Option(gauge.key, gauge.label, system.group)
        for system in systems
        for gauge in system.gauges
    )
    return GaugeSystems(table, tuple(systems), options, MappingProxyType(by_key), tuple(values))


def _constants(table: ReferenceTable) -> tuple[dict[str, Decimal], list[ReferenceValue]]:
    constants: dict[str, Decimal] = {}
    values: list[ReferenceValue] = []
    for name, entry in _table(table.data, "constant").items():
        where = f"{table.name}: constant {name!r}"
        _check_keys(where, entry, {"value", "unit", "source", "trust"})
        constants[name] = _decimal(where, entry["value"])
        source = _source(table, where, entry["source"])
        trust = _trust(where, entry["trust"])
        values.append(
            ReferenceValue(float(constants[name]), source, Basis.NOMINAL_DEFINITION, trust)
        )
    return constants, values


def _weights(table: ReferenceTable) -> dict[str, Decimal]:
    entry = _table(table.data, "weights")
    where = f"{table.name}: weights"
    _check_keys(where, entry, {"source", "oz_per_sq_ft"})
    _source(table, where, entry["source"])
    weights: dict[str, Decimal] = {}
    for size, weight in _table(entry, "oz_per_sq_ft").items():
        if not _SIZE.fullmatch(size):
            raise SpecError(f"{where}: {size!r} isn't a gauge size")
        weights[size] = _decimal(f"{where} {size!r}", weight)
    return weights


_SYSTEM_KEYS = frozenset(
    {"id", "name", "size_label", "formula", "constants", "first", "last", "precision"}
    | {"defined_by", "checked_against", "tolerances"}
)


def _system(
    table: ReferenceTable,
    entry: Any,
    constants: Mapping[str, Decimal],
    weights: Mapping[str, Decimal],
) -> tuple[GaugeSystem, list[ReferenceValue]]:
    system_key = entry.get("id", "?") if isinstance(entry, dict) else "?"
    where = f"{table.name}: system {system_key!r}"
    _check_keys(where, entry, _SYSTEM_KEYS, optional={"scope"})
    system_id, name, suffix = (_text(where, entry, k) for k in ("id", "name", "size_label"))
    formula_name = _text(where, entry, "formula")
    formula = FORMULAS.get(formula_name)
    if formula is None:
        raise SpecError(f"{where}: no formula {formula_name!r}; known: {sorted(FORMULAS)}")
    supplied = _table(entry, "constants")
    if not set(formula.constants) - set(formula.defaults) <= set(supplied) <= formula.constants:
        raise SpecError(f"{where}: formula {formula_name!r} takes {sorted(formula.constants)}")
    fixed = dict(formula.defaults)
    for symbol, constant in supplied.items():
        if not isinstance(constant, str) or constant not in constants:
            raise SpecError(f"{where}: {symbol} names no constant {constant!r}")
        fixed[symbol] = constants[constant]
    precision = _precision(table, where, _table(entry, "precision"))
    defined_by = _source(table, where, entry["defined_by"])
    checked = tuple(_source(table, where, s) for s in _list(entry, "checked_against"))
    tolerances = [table.sources[_source(table, where, s)] for s in _list(entry, "tolerances")]
    if not tolerances:
        raise SpecError(f"{where}: name the system's tolerance standards")
    note = Note(
        NoteKind.WARNING,
        caution([s.publication for s in tolerances]),
        references=(table.reference, *(s.reference for s in tolerances)),
    )
    gauges: list[Gauge] = []
    values: list[ReferenceValue] = []
    first, last = (_index(_size(where, entry, k)) for k in ("first", "last"))
    if first > last:
        raise SpecError(f"{where}: first comes after last")
    for size in _sizes(first, last):
        symbols = dict(fixed)
        if formula.per_gauge == "w":
            if size not in weights:
                raise SpecError(f"{where}: the weights don't define gauge {size!r}")
            symbols["w"] = weights[size]
        else:
            symbols["n"] = Decimal(_index(size))
        exact = formula.evaluate(symbols)
        stated = precision.state(exact)
        gauges.append(
            Gauge(
                f"{system_id}:{size}",
                _label(size, suffix),
                MappingProxyType(symbols),
                exact,
                stated,
            )
        )
        values.append(
            ReferenceValue(
                stated.value,
                defined_by,
                Basis.NOMINAL_DEFINITION,
                TrustLevel.VERIFIED_DERIVATION,
                checked,
                stated,
            )
        )
    scope = str(entry.get("scope", ""))
    system = GaugeSystem(system_id, name, scope, formula, precision, tuple(gauges), note)
    return system, values


def _size(where: str, entry: Mapping[str, Any], key: str) -> str:
    size = _text(where, entry, key)
    if not _SIZE.fullmatch(size):
        raise SpecError(f"{where}: {key} {size!r} isn't a gauge size")
    return size


def _sizes(first: int, last: int) -> Iterable[str]:
    """Yield the sizes from ``first`` to ``last`` by index, e.g. 0000, 000, 00, 0, 1, 2."""
    for index in range(first, last + 1):
        yield "0" * (1 - index) if index <= 0 else str(index)


def _precision(table: ReferenceTable, where: str, entry: Mapping[str, Any]) -> Precision:
    where = f"{where} precision"
    _source(table, where, entry.get("source"))
    if entry.get("exact") is True:
        _check_keys(where, entry, {"exact", "source"})
        return Precision(None)
    _check_keys(
        where, entry, {"decimals", "rounding", "source"}, optional={"below", "decimals_below"}
    )
    if entry["rounding"] not in _ROUNDING:
        raise SpecError(f"{where}: rounding must be one of {sorted(_ROUNDING)}")
    below = entry.get("below")
    if (below is None) != ("decimals_below" not in entry):
        raise SpecError(f"{where}: below and decimals_below go together")
    return Precision(
        _places(where, entry["decimals"]),
        _ROUNDING[entry["rounding"]],
        None if below is None else _decimal(where, below),
        None if below is None else _places(where, entry["decimals_below"]),
    )


def _places(where: str, value: Any) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or not 0 <= value <= 12:
        raise SpecError(f"{where}: decimals must be a whole number from 0 to 12")
    return value


def _source(table: ReferenceTable, where: str, source: Any) -> str:
    if not isinstance(source, str) or source not in table.sources:
        raise SpecError(f"{where} cites {source!r}, which isn't a declared source")
    return source


def _trust(where: str, value: Any) -> TrustLevel:
    try:
        return TrustLevel(value)
    except ValueError:
        raise SpecError(f"{where}: trust {value!r} isn't a trust level") from None


def _decimal(where: str, text: Any) -> Decimal:
    """Read exact decimal text. A TOML float is refused, since its value isn't exact."""
    if not isinstance(text, str):
        raise SpecError(f'{where}: write {text!r} as exact text, e.g. "41.82"')
    try:
        value = Decimal(text)
    except InvalidOperation:
        raise SpecError(f"{where}: {text!r} isn't a number") from None
    if not value.is_finite() or value < 0:
        raise SpecError(f"{where}: {text!r} must be a finite number from 0")
    return value


def _text(where: str, entry: Mapping[str, Any], key: str) -> str:
    value = entry[key]
    if not isinstance(value, str) or not value.strip():
        raise SpecError(f"{where} needs a {key}")
    return value


def _table(data: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    value = data.get(key)
    if not isinstance(value, dict):
        raise SpecError(f"Gauge table: {key!r} must be a table")
    return value


def _list(data: Mapping[str, Any], key: str) -> list[Any]:
    value = data.get(key)
    if not isinstance(value, list):
        raise SpecError(f"Gauge table: {key!r} must be a list")
    return value


def _check_keys(
    where: str, entry: Any, required: Iterable[str], *, optional: Iterable[str] = ()
) -> None:
    if not isinstance(entry, dict):
        raise SpecError(f"{where} must be a table")
    allowed = set(required) | set(optional)
    unknown = sorted(set(entry) - allowed)
    missing = sorted(set(required) - set(entry))
    if unknown or missing:
        raise SpecError(f"{where}: unknown keys {unknown}, missing {missing}")


GAUGE_TABLE = TableSpec(
    "caddcalc.calculators.sheet_metal",
    "data/gauges.toml",
    frozenset({"constant", "weights", "system"}),
    lambda table: load_gauges(table).values,
)
"""The gauge table, as ``caddcalc.calculators.REFERENCE_TABLES`` lists it."""


class GaugeResolver:
    """The sheet-metal domain's resolver: the gauge options and the thickness each gives.

    The table loads on first use and is kept for the life of the process.
    """

    def __init__(self, domain: str, setting: Param, spec: TableSpec = GAUGE_TABLE) -> None:
        """Resolve the gauge choice of ``domain`` into its ``setting``, from ``spec``."""
        self._domain = domain
        self._setting = setting
        self._spec = spec

    @cached_property
    def gauges(self) -> GaugeSystems:
        """Every gauge system, loaded and checked."""
        return load_gauges(self._spec.load())

    def options(self, choice: str, _parents: Mapping[str, str]) -> Sequence[Option]:
        """Return every gauge, grouped by system, for the gauge choice."""
        return self.gauges.options if choice == GAUGE.key else ()

    def derive(self, selections: Mapping[str, str]) -> Mapping[str, DerivedValue]:
        """Return the selected gauge's nominal thickness, with its caution and its work."""
        key = selections.get(GAUGE.key)
        if key is None:
            return {}
        system, gauge = self.gauges.by_key[key]
        source = InputSource(
            SourceKind.DERIVED,
            f"{gauge.label}, {system.group} (nominal)",
            domain=self._domain,
            reference=self.gauges.table.reference,
        )
        work = Step(
            self._setting.symbol,
            f"{self._setting.label} ({gauge.label}, {system.name})",
            self._setting.dimension,
            gauge.stated.value,
            system.formula.expression,
            note=system.precision.explain(gauge.exact),
            substitution=MappingProxyType({k: _shown(v) for k, v in gauge.symbols.items()}),
            expression_unit=FORMULA_UNIT,
        )
        return {
            self._setting.key: DerivedValue(
                gauge.stated.value, source, gauge.stated, system.note, work
            )
        }


def _shown(value: Decimal) -> str:
    """Return a formula input as the work shows it, e.g. ``"41.82"`` or ``"(-3)"``."""
    text = f"{value:f}"
    return f"({text})" if value < 0 else text
