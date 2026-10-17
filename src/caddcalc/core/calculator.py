"""The Calculator base class, the per-run Context, and the Result it produces."""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, ClassVar

from caddcalc.core import expr
from caddcalc.core.domain import DomainValues
from caddcalc.core.errors import InputError, SpecError, UsageError
from caddcalc.core.provenance import DEFAULT, EXPLICIT, InputSource, SourceKind
from caddcalc.core.spec import Method, Output, Param
from caddcalc.core.units import BASE_UNITS, Dimension

_ID = re.compile(r"[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+")


@dataclass(frozen=True)
class Step:
    """One line of "show work": ``symbol = expression = value``."""

    symbol: str
    label: str
    dimension: Dimension
    value: float
    expression: str | None = None
    """The evaluated formula, or None when the value was computed in code (see ``note``)."""
    note: str = ""


@dataclass(frozen=True)
class Result:
    """The outcome of one run, with every value in base units."""

    calculator_id: str
    method: str
    inputs: Mapping[str, float]
    """Input values by parameter key, in base units."""
    outputs: Mapping[str, float]
    """Output values by output key, in base units."""
    steps: tuple[Step, ...]
    symbols: Mapping[str, tuple[float, Dimension]]
    """Every symbol known after the run (inputs and steps), for rendering the work."""
    dimensions: Mapping[str, Dimension]
    """Dimension of every input and output key."""
    warnings: tuple[str, ...]
    input_sources: Mapping[str, InputSource]
    """Where each input value came from, by parameter key (ADR-0013 §5)."""

    def to_dict(self) -> dict[str, Any]:
        """A JSON-serialisable form. Values are in base units, and each one names its unit."""

        def q(value: float, dim: Dimension) -> dict[str, Any]:
            return {"value": value, "unit": BASE_UNITS[dim], "dimension": dim.value}

        return {
            "calculator": self.calculator_id,
            "method": self.method,
            "inputs": {
                k: {**q(v, self.dimensions[k]), "source": self.source_of(k).to_dict()}
                for k, v in self.inputs.items()
            },
            "outputs": {k: q(v, self.dimensions[k]) for k, v in self.outputs.items()},
            "steps": [
                {
                    "symbol": s.symbol,
                    "label": s.label,
                    "expression": s.expression,
                    "note": s.note,
                    **q(s.value, s.dimension),
                }
                for s in self.steps
            ],
            "warnings": list(self.warnings),
        }

    def source_of(self, key: str) -> InputSource:
        """Return where the input ``key`` came from.

        Raises:
            KeyError: ``key`` is not an input of this run.
        """
        return self.input_sources[key]


class Context:
    """Passed to ``Calculator.compute``. It records each step so the work can be shown."""

    def __init__(self, calculator: Calculator, method: Method, inputs: Mapping[str, float]):
        self.calculator = calculator
        self.method = method.key
        self.inputs = dict(inputs)
        self.symbols: dict[str, tuple[float, Dimension]] = {
            p.symbol: (inputs[p.key], p.dimension) for p in calculator.params if p.key in inputs
        }
        self.steps: list[Step] = []
        self.warnings: list[str] = []
        self.outputs: dict[str, float] = {}

    def __getitem__(self, key: str) -> float:
        """An input value by parameter key, in base units."""
        return self.inputs[key]

    def value(self, symbol: str) -> float:
        """Return the value of ``symbol`` (an input or an earlier step), in base units."""
        return self.symbols[symbol][0]

    def calc(
        self,
        symbol: str,
        expression: str,
        *,
        label: str,
        dimension: Dimension,
        output: str | None = None,
    ) -> float:
        """Evaluate ``expression``, record it as a step, and optionally store it as an output."""
        values = {name: v for name, (v, _dim) in self.symbols.items()}
        result = expr.evaluate(expression, values)
        return self._record(Step(symbol, label, dimension, result, expression), output)

    def record(
        self,
        symbol: str,
        value: float,
        *,
        label: str,
        dimension: Dimension,
        note: str,
        output: str | None = None,
    ) -> float:
        """Record a value computed in Python (e.g. a table lookup), with a note explaining it."""
        return self._record(Step(symbol, label, dimension, value, None, note), output)

    def warn(self, message: str) -> None:
        """Add an engineering warning to the result."""
        self.warnings.append(message)

    def _record(self, step: Step, output: str | None) -> float:
        if step.symbol in self.symbols:
            raise SpecError(f"{self.calculator.id}: symbol {step.symbol!r} is defined twice")
        self.symbols[step.symbol] = (step.value, step.dimension)
        self.steps.append(step)
        if output is not None:
            self.outputs[output] = step.value
        return step.value


class Calculator(ABC):
    """Base class for every calculator, built-in or plugin.

    Subclasses declare their parameters, outputs, and methods as class attributes and
    implement ``compute``. ``compute`` gets a Context with inputs already parsed,
    defaulted, and range-checked, all in base units.
    """

    id: ClassVar[str]
    """Unique, lowercase, and dotted, with at least two parts.

    Built-ins use ``<domain>.<name>``, e.g. ``sheet_metal.bend_allowance``. A plugin may use
    its own prefix in any domain, e.g. ``acme.flange_check`` (ADR-0013).
    """
    name: ClassVar[str]
    domain: ClassVar[str]
    """Id of the ``Domain`` the calculator belongs to, e.g. ``"sheet_metal"`` (ADR-0013)."""
    summary: ClassVar[str]
    params: ClassVar[tuple[Param, ...]]
    outputs: ClassVar[tuple[Output, ...]]
    methods: ClassVar[tuple[Method, ...]]

    @abstractmethod
    def compute(self, ctx: Context) -> None:
        """Compute every declared output using ``ctx.calc``, ``ctx.record``, and ``ctx.warn``."""

    # --- lookup helpers -------------------------------------------------------------------

    @classmethod
    def get_method(cls, key: str | None = None) -> Method:
        """Return the method with ``key``, or the default (first) method if ``key`` is ``None``.

        Raises:
            InputError: The calculator has no method with that key.
        """
        if key is None:
            return cls.methods[0]
        for m in cls.methods:
            if m.key == key:
                return m
        known = ", ".join(m.key for m in cls.methods)
        raise InputError(f"{cls.id} has no method {key!r}; choose one of: {known}")

    @classmethod
    def params_for(cls, method_key: str) -> tuple[Param, ...]:
        """Return the parameters that ``method_key`` uses, in declaration order."""
        return tuple(p for p in cls.params if p.used_by(method_key))

    @classmethod
    def output(cls, key: str) -> Output:
        """Return the output declared with ``key``."""
        return next(o for o in cls.outputs if o.key == key)

    # --- running --------------------------------------------------------------------------

    def run(
        self,
        inputs: Mapping[str, float] | None = None,
        method: str | None = None,
        *,
        settings: DomainValues | None = None,
    ) -> Result:
        """Run the calculator and record the work.

        Each input the method uses comes from the first of: ``inputs``, a shared
        parameter's domain setting in ``settings``, or the parameter's default
        (ADR-0013 §4).

        Args:
            inputs: Values given for this run, by parameter key, in base units.
            method: The method key; the first method when ``None``.
            settings: The values the user has set for this calculator's domain.

        Raises:
            InputError: An input is unknown or missing.
            OutOfRangeError: An input is out of range. It names the input's source.
            UsageError: ``settings`` belongs to another domain.
        """
        inputs = dict(inputs or {})
        if settings is not None and settings.domain_id != self.domain:
            raise UsageError(
                f"{self.id} belongs to domain {self.domain!r}, "
                f"but was given settings for {settings.domain_id!r}"
            )
        m = self.get_method(method)
        known = {p.key for p in self.params}
        unknown = sorted(set(inputs) - known)
        if unknown:
            raise InputError(f"{self.id} has no input(s): {', '.join(unknown)}")

        values: dict[str, float] = {}
        sources: dict[str, InputSource] = {}
        for p in self.params_for(m.key):
            value, source = _resolve(p, inputs, settings)
            p.check(value, source)
            values[p.key] = value
            sources[p.key] = source

        ctx = Context(self, m, values)
        self.compute(ctx)

        missing = [o.key for o in self.outputs if o.key not in ctx.outputs]
        if missing:
            raise SpecError(f"{self.id} ({m.key}) did not produce: {', '.join(missing)}")

        dimensions = {p.key: p.dimension for p in self.params}
        dimensions.update({o.key: o.dimension for o in self.outputs})
        return Result(
            calculator_id=self.id,
            method=m.key,
            inputs=values,
            outputs={o.key: ctx.outputs[o.key] for o in self.outputs},
            steps=tuple(ctx.steps),
            symbols=dict(ctx.symbols),
            dimensions=dimensions,
            warnings=tuple(ctx.warnings),
            input_sources=sources,
        )

    # --- definition checks ----------------------------------------------------------------

    @classmethod
    def validate_spec(cls) -> None:
        """Check the class definition. Called on registration so plugin mistakes fail early."""
        for attr in ("id", "name", "domain", "summary", "params", "outputs", "methods"):
            if not hasattr(cls, attr):
                raise SpecError(f"{cls.__name__} is missing class attribute {attr!r}")
        if not _ID.fullmatch(cls.id):
            raise SpecError(
                f"Calculator id {cls.id!r} must be lowercase and dotted, with at least two "
                "parts, like 'sheet_metal.bend_allowance'"
            )
        if not cls.methods:
            raise SpecError(f"{cls.id} declares no methods")
        if not cls.outputs:
            raise SpecError(f"{cls.id} declares no outputs")
        method_keys = [m.key for m in cls.methods]
        _unique(cls.id, "method key", method_keys)
        _unique(cls.id, "parameter key", [p.key for p in cls.params])
        _unique(cls.id, "parameter symbol", [p.symbol for p in cls.params])
        _unique(cls.id, "output key", [o.key for o in cls.outputs])
        for p in cls.params:
            if not expr.is_usable_symbol(p.symbol):
                raise SpecError(
                    f"{cls.id}: parameter symbol {p.symbol!r} is not usable in formulas"
                )
            for mk in p.methods:
                if mk not in method_keys:
                    raise SpecError(f"{cls.id}: parameter {p.key!r} names unknown method {mk!r}")
            if p.default is not None:
                p.check(p.default_value() or 0.0, DEFAULT)


def _resolve(
    p: Param, inputs: Mapping[str, float], settings: DomainValues | None
) -> tuple[float, InputSource]:
    """Pick one input's value and source by the precedence rule (ADR-0013 §4)."""
    if p.key in inputs:
        return float(inputs[p.key]), EXPLICIT
    if p.shared and settings is not None and p.key in settings.values:
        source = InputSource(SourceKind.DOMAIN, settings.label, domain=settings.domain_id)
        return float(settings.values[p.key]), source
    default = p.default_value()
    if default is None:
        raise InputError(f"Missing input: {p.label} ({p.symbol})")
    return default, DEFAULT


def _unique(owner: str, what: str, items: list[str]) -> None:
    seen: set[str] = set()
    for item in items:
        if item in seen:
            raise SpecError(f"{owner}: duplicate {what} {item!r}")
        seen.add(item)
