"""The Calculator base class, the per-run Context, and the Result it produces."""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from types import MappingProxyType
from typing import Any, ClassVar, Protocol

from caddcalc.core import expr
from caddcalc.core.choices import DerivedValue
from caddcalc.core.domain import DomainValues, ValueOrigin
from caddcalc.core.errors import CaddCalcError, InputError, SpecError, UsageError
from caddcalc.core.notes import Note, NoteKind, Quantity
from caddcalc.core.provenance import DEFAULT, EXPLICIT, InputSource, SourceKind
from caddcalc.core.reference import Reference
from caddcalc.core.spec import Method, OutOfRangeError, Output, Param, UnitSet
from caddcalc.core.steps import Step
from caddcalc.core.units import (
    BASE_UNITS,
    Dimension,
    Unit,
    base_text,
    base_unit_names,
    get_unit,
    registry,
)

_ID = re.compile(r"[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+")


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
    notes: tuple[Note, ...]
    """Notes on the result: warnings, cited limits, gaps, and impossibilities, in order."""
    input_sources: Mapping[str, InputSource]
    """Where each input value came from, by parameter key (ADR-0013 §5)."""

    def to_dict(self) -> dict[str, Any]:
        """A JSON-serialisable form. Values are in base units, and each one names its unit."""

        def q(value: float, dim: Dimension) -> dict[str, Any]:
            number = int(value) if dim is Dimension.COUNT else value  # a count is whole
            return {"value": number, "unit": BASE_UNITS[dim], "dimension": dim.value}

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
                    "substitution": None if s.substitution is None else dict(s.substitution),
                    "expression_unit": s.expression_unit,
                    "stated": s.stated,
                }
                for s in self.steps
            ],
            "notes": [note.to_dict() for note in self.notes],
        }

    def source_of(self, key: str) -> InputSource:
        """Return where the input ``key`` came from.

        Raises:
            KeyError: ``key`` is not an input of this run.
        """
        return self.input_sources[key]


class Context:
    """Passed to ``Calculator.compute``, then to each result check, so the work can be shown.

    It records each step compute makes, and the notes compute and the checks add.
    """

    def __init__(
        self,
        calculator: Calculator,
        method: Method,
        inputs: Mapping[str, float],
        sources: Mapping[str, InputSource] | None = None,
    ):
        self.calculator = calculator
        self.method = method.key
        self.inputs = dict(inputs)
        self.sources: Mapping[str, InputSource] = MappingProxyType(dict(sources or {}))
        """Where each input came from (ADR-0013 §5), read-only, e.g. so a result check can
        tell a gauge's thickness from a typed one."""
        self.symbols: dict[str, tuple[float, Dimension]] = {
            p.symbol: (inputs[p.key], p.dimension) for p in calculator.params if p.key in inputs
        }
        self.steps: list[Step] = []
        self.notes: list[Note] = []
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
        """Evaluate ``expression``, record it as a step, and optionally store it as an output.

        Raises:
            SpecError: ``output`` has a value already, which would hide the first and its
                work.
        """
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

    def given(self, symbol: str, *, output: str) -> float:
        """Report the input ``symbol`` as the output ``output``, unchanged, and return it.

        For an output that a method takes as an input, such as a circle's diameter in its
        diameter method: it's shown with the results, and adds no work, since the inputs
        show it already.

        Raises:
            SpecError: ``symbol`` isn't an input of this run, ``output`` isn't an output
                of the calculator, the two measure different things, or the output has a
                value already.
        """
        param = next((p for p in self.calculator.params if p.symbol == symbol), None)
        if param is None or param.key not in self.inputs:
            raise SpecError(f"{self.calculator.id}: {symbol!r} isn't an input of this run")
        declared = next((o for o in self.calculator.outputs if o.key == output), None)
        if declared is None:
            raise SpecError(f"{self.calculator.id}: {output!r} isn't an output")
        if declared.dimension is not param.dimension:
            raise SpecError(
                f"{self.calculator.id}: input {symbol!r} isn't {declared.dimension.with_article}"
            )
        self._claim(output)
        self.outputs[output] = self.inputs[param.key]
        return self.outputs[output]

    def note(
        self,
        text: str,
        kind: NoteKind = NoteKind.WARNING,
        *,
        references: Sequence[Reference] = (),
        subjects: Sequence[str] = (),
        detail: str = "",
        quantities: Mapping[str, Quantity] | None = None,
        phrases: Mapping[str, str] | None = None,
    ) -> None:
        """Add a note to the result.

        Args:
            text: The lead: one sentence for users that leads with the verdict.
            kind: What the note tells the user.
            references: The sources of the limit or rule behind it. A limit-exceeded note
                needs at least one.
            subjects: The parameter or output keys the note concerns.
            detail: What follows the lead, if anything.
            quantities: Values the text and detail name as ``{fields}``, in base units;
                they're shown in the user's display units (``Note``).
            phrases: Data phrases the text and detail name as ``{fields}``.

        Raises:
            SpecError: A subject isn't a parameter or output of this calculator, a
                limit-exceeded note cites nothing, or a field isn't given (``Note``).
        """
        known = {p.key for p in self.calculator.params} | {o.key for o in self.calculator.outputs}
        unknown = [s for s in subjects if s not in known]
        if unknown:
            raise SpecError(
                f"{self.calculator.id}: note subjects {unknown} aren't parameters or outputs"
            )
        self.notes.append(
            Note(
                kind,
                text,
                tuple(references),
                tuple(subjects),
                detail,
                quantities or {},
                phrases or {},
            )
        )

    def warn(
        self,
        text: str,
        *,
        subjects: Sequence[str] = (),
        detail: str = "",
        quantities: Mapping[str, Quantity] | None = None,
        phrases: Mapping[str, str] | None = None,
    ) -> None:
        """Add a warning: something to check before using the result. Short for ``note``."""
        self.note(
            text,
            NoteKind.WARNING,
            subjects=subjects,
            detail=detail,
            quantities=quantities,
            phrases=phrases,
        )

    def _record(self, step: Step, output: str | None) -> float:
        if step.symbol in self.symbols:
            raise SpecError(f"{self.calculator.id}: symbol {step.symbol!r} is defined twice")
        if output is not None:
            self._claim(output)
            if any(o.key == output and o.signed for o in self.calculator.outputs):
                step = replace(step, signed=True)  # its work line shows the sign too
        self.symbols[step.symbol] = (step.value, step.dimension)
        self.steps.append(step)
        if output is not None:
            self.outputs[output] = step.value
        return step.value

    def _claim(self, output: str) -> None:
        """Check ``output`` has no value yet: a second would hide the first and its work."""
        if output in self.outputs:
            raise SpecError(f"{self.calculator.id}: output {output!r} is given a value twice")


class ResultCheck(Protocol):
    """A check a calculator declares, run over each of its finished runs (ADR-0014 §3).

    A check reads the run, through the context compute used, and adds notes through
    ``ctx.note``; it never records steps or outputs. It sees the choice selections of the
    run's domain settings, such as the chosen material, which compute never does, so
    formulas stay numeric and a run without settings still gets the checks that need none.
    """

    def __call__(self, ctx: Context, selections: Mapping[str, str], /) -> None:
        """Add notes about a finished run.

        Args:
            ctx: The run after compute: its method, inputs and their sources, and
                outputs.
            selections: The selections in effect for the run's domain, by choice key
                (``DomainValues.selections``); empty when the run has no settings.
        """


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
    checks: ClassVar[tuple[ResultCheck, ...]] = ()
    """Result checks run after every compute, in order, such as a minimum-radius check."""
    output_sets: ClassVar[tuple[UnitSet, ...]] = ()
    """The sets of units its results can be shown in, the first the default (ADR-0024
    E1); empty for the generated ones, one per length choice (``unit_sets``)."""

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
    def unit_sets(cls) -> tuple[UnitSet, ...]:
        """Return the sets its output picker offers: ``output_sets``, or the generated ones.

        A generated set is labelled by its choices for the dimensions its outputs show
        in a set, in their order: ``in · ° · in²`` on the right triangle, ``in`` on a
        sheet-metal page (ADR-0024 §5).
        """
        if cls.output_sets:
            return cls.output_sets
        units = registry()
        shown = list(dict.fromkeys(o.dimension for o in cls.outputs if o.follows_set))
        if not shown:
            return ()  # every output has its own unit, form or picks: there's nothing to set
        sets = []
        for key, choices in units.generated_sets():
            written = [_written(choices[d], d) for d in shown]
            sets.append(UnitSet(key, " · ".join(w for w in written if w), choices))
        return tuple(sets)

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
        explicit_sources: Mapping[str, InputSource] | None = None,
        explicit_notes: Mapping[str, Note] | None = None,
    ) -> Result:
        """Run the calculator and record the work.

        Each input the method uses comes from the first of: ``inputs``, a shared
        parameter's set domain value in ``settings``, its derived value there, or the
        parameter's default (ADR-0013 §4). A derived value's note, such as a nominal
        caution, is added to the result once whenever that value is used, and so are a
        note an applied domain value carries (``DomainValues.origins``) and a note an
        explicit input carries. After compute, each of ``checks`` runs and may add notes.

        Args:
            inputs: Values given for this run, by parameter key, in base units.
            method: The method key; the first method when ``None``.
            settings: The values the user has set for this calculator's domain.
            explicit_sources: Labels for some of ``inputs``, by parameter key, e.g.
                ``InputSource(SourceKind.EXPLICIT, "course example")``. Unlabelled
                inputs are plain explicit values. Labels never change precedence.
            explicit_notes: Notes some of ``inputs`` carry, by parameter key, such as the
                caution of a derived value an input was copied from (ADR-0014). Each is
                added like a derived value's note, naming the inputs that carry it.

        Raises:
            InputError: An input is unknown or missing.
            OutOfRangeError: An input is out of range. It names the input's source.
            UsageError: ``settings`` belongs to another domain; ``explicit_sources``
                labels a key that isn't in ``inputs`` or gives a kind other than explicit;
                or ``explicit_notes`` names a key that isn't in ``inputs``, or gives a note
                that already has subjects.
            SpecError: compute raised an error that isn't caddcalc's own, such as a
                plugin's ZeroDivisionError, or left an output unset; or a result check
                raised or changed the work.
        """
        inputs = dict(inputs or {})
        labels = dict(explicit_sources or {})
        carried = dict(explicit_notes or {})
        stray = sorted(set(labels) - set(inputs))
        if stray:
            raise UsageError(f"{self.id}: explicit_sources labels keys not in inputs: {stray}")
        stray = sorted(set(carried) - set(inputs))
        if stray:
            raise UsageError(f"{self.id}: explicit_notes names keys not in inputs: {stray}")
        if any(note.subjects for note in carried.values()):
            raise UsageError(f"{self.id}: run() names a carried note's subjects; give none")
        if any(source.kind is not SourceKind.EXPLICIT for source in labels.values()):
            raise UsageError(f"{self.id}: explicit_sources may only hold explicit sources")
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
        used_notes: dict[Note, list[str]] = {}
        derived_work: list[Step] = []
        for p in self.params_for(m.key):
            value, source = _resolve(p, inputs, settings, labels)
            p.check(value, source)
            values[p.key] = value
            sources[p.key] = source
            derived = _derived(p, source, settings)
            origin = _origin(p, source, settings)
            for note in (
                None if derived is None else derived.note,
                None if origin is None else origin.note,
                carried.get(p.key),
            ):
                if note is not None:
                    used_notes.setdefault(note, []).append(p.key)
            if derived is not None and derived.work is not None:
                derived_work.append(replace(derived.work, symbol=p.symbol))

        ctx = Context(self, m, values, sources)
        # One note per carried note used, naming every input that took it, and the work
        # of each derived value used, ahead of the calculator's own (ADR-0014).
        ctx.notes.extend(replace(n, subjects=tuple(keys)) for n, keys in used_notes.items())
        ctx.steps.extend(derived_work)
        try:
            self.compute(ctx)
        except CaddCalcError:
            raise  # an input or calculation error, worded for users
        except Exception as exc:
            # As a check's is: so every front end reports it, never a stale result.
            raise SpecError(
                f"{self.id} ({m.key}): compute failed: {type(exc).__name__}: {exc}"
            ) from exc

        missing = [o.key for o in self.outputs if o.key not in ctx.outputs]
        if missing:
            raise SpecError(f"{self.id} ({m.key}) did not produce: {', '.join(missing)}")
        self._run_checks(ctx, settings)

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
            notes=tuple(ctx.notes),
            input_sources=sources,
        )

    def _run_checks(self, ctx: Context, settings: DomainValues | None) -> None:
        """Run the declared result checks, which may append notes and change nothing else.

        The run's inputs, outputs, steps, and symbols are compared with copies taken before
        the checks, and its notes must keep their order and gain only new notes. A note
        the run already has is refused too: repeating one is a check's bug.

        Raises:
            SpecError: A check raised, changed the run, or repeated a note.
        """
        selections = MappingProxyType({}) if settings is None else settings.selections
        work = (dict(ctx.inputs), dict(ctx.outputs), tuple(ctx.steps), dict(ctx.symbols))
        notes = tuple(ctx.notes)
        for check in self.checks:
            name = getattr(check, "__name__", type(check).__name__)
            try:
                check(ctx, selections)
            except Exception as exc:
                raise SpecError(f"{self.id}: check {name} failed: {exc}") from exc
            after = (dict(ctx.inputs), dict(ctx.outputs), tuple(ctx.steps), dict(ctx.symbols))
            if after != work or tuple(ctx.notes[: len(notes)]) != notes:
                raise SpecError(f"{self.id}: check {name} changed the run; checks only add notes")
            seen = set(notes)
            for note in ctx.notes[len(notes) :]:
                if note in seen:
                    raise SpecError(f"{self.id}: check {name} repeated the note {note.text!r}")
                seen.add(note)
            notes = tuple(ctx.notes)

    # --- definition checks ----------------------------------------------------------------

    @classmethod
    def validate_spec(cls) -> None:
        """Check the class definition. Called on registration so plugin mistakes fail early.

        Raises:
            SpecError: The definition is invalid, including a default that doesn't parse
                or is out of range.
        """
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
        if not isinstance(cls.checks, tuple) or not all(callable(c) for c in cls.checks):
            raise SpecError(f"{cls.id}: checks must be a tuple of result checks")
        method_keys = [m.key for m in cls.methods]
        _unique(cls.id, "method key", method_keys)
        _unique(cls.id, "parameter key", [p.key for p in cls.params])
        _unique(cls.id, "parameter symbol", [p.symbol for p in cls.params])
        _unique(cls.id, "output key", [o.key for o in cls.outputs])
        for o in cls.outputs:
            _check_output_unit(cls.id, o)
            _check_picks(cls.id, o.dimension, o.picks, f"output {o.key!r}'s picks", output=True)
            if o.picks and (o.unit or o.form):
                raise SpecError(
                    f"{cls.id}: output {o.key!r} gives picks and a fixed unit or form; give one"
                )
        _check_sets(cls)
        for p in cls.params:
            if not expr.is_usable_symbol(p.symbol):
                raise SpecError(
                    f"{cls.id}: parameter symbol {p.symbol!r} is not usable in formulas"
                )
            for mk in p.methods:
                if mk not in method_keys:
                    raise SpecError(f"{cls.id}: parameter {p.key!r} names unknown method {mk!r}")
            if p.default is not None:
                try:
                    p.check(p.default_value() or 0.0, DEFAULT)
                except OutOfRangeError as exc:
                    raise SpecError(
                        f"{cls.id}: parameter {p.key!r} has a bad default {p.default!r} "
                        f"(= {base_text(exc.value, p.dimension)}), which must be "
                        f"{exc.relation} {base_text(exc.bound, p.dimension)}. Minimum and "
                        f"maximum are in base units ({base_unit_names()})."
                    ) from exc
                except InputError as exc:
                    raise SpecError(
                        f"{cls.id}: parameter {p.key!r} has a bad default {p.default!r}: {exc}"
                    ) from exc
            _check_param_choices(cls.id, p)


def _written(choice: str, dimension: Dimension) -> str:
    """Return a choice as a picker shows it: a unit's written symbol, or a form's."""
    picked = registry().choice(choice, dimension)
    return picked.written if isinstance(picked, Unit) else picked.symbol


def _check_picks(
    owner: str, dimension: Dimension, picks: tuple[str, ...], what: str, *, output: bool
) -> None:
    """Check that each id is a choice of ``dimension``, a field's or an output's."""
    units = registry()
    allowed = units.output_choices(dimension) if output else units.entry_choices(dimension)
    _unique(owner, f"choice in {what}", list(picks))
    for pick in picks:
        if pick not in allowed:
            known = ", ".join(c or "''" for c in allowed)
            raise SpecError(
                f"{owner}: {what} names {pick!r}, which isn't a choice for "
                f"{dimension.with_article}; there's {known}"
            )


def _check_param_choices(owner: str, p: Param) -> None:
    """Check a parameter's picker: its choices exist, and its default choice resolves.

    A parameter with more than one choice needs a default choice: ``Param.unit``, or a
    default that names its unit, as ``"0.1046 in"`` does (ADR-0024 E1).
    """
    _check_picks(owner, p.dimension, p.units, f"parameter {p.key!r}'s units", output=False)
    choice = p.default_choice
    if choice is None:
        raise SpecError(
            f"{owner}: parameter {p.key!r} has no default unit for its picker: give "
            "Param.unit, or a default that names its unit"
        )
    if choice not in p.choices:
        known = ", ".join(c or "''" for c in p.choices)
        raise SpecError(
            f"{owner}: parameter {p.key!r} starts its picker in {choice!r}, which it "
            f"doesn't offer; it offers {known}"
        )


def _check_sets(cls: type[Calculator]) -> None:
    """Check the declared output sets: unique keys, real choices, every dimension covered."""
    _unique(cls.id, "output set key", [s.key for s in cls.output_sets])
    for unit_set in cls.output_sets:
        if not unit_set.key.strip() or not unit_set.label.strip():
            raise SpecError(f"{cls.id}: an output set needs a key and a label")
    shown = {o.dimension for o in cls.outputs if o.follows_set}
    for unit_set in cls.output_sets:
        missing = sorted(d.value for d in shown if d not in unit_set.choices)
        if missing:
            raise SpecError(
                f"{cls.id}: output set {unit_set.key!r} has no choice for {', '.join(missing)}"
            )
        for dimension, choice in unit_set.choices.items():
            _check_picks(cls.id, dimension, (choice,), f"output set {unit_set.key!r}", output=True)


def _check_output_unit(owner: str, output: Output) -> None:
    """Check that an output's fixed unit or form, if it names one, is of its dimension."""
    if output.form:
        if output.unit:
            raise SpecError(f"{owner}: output {output.key!r} gives a unit and a form; give one")
        try:
            form = registry().compound(output.form)
        except UsageError as exc:
            raise SpecError(f"{owner}: output {output.key!r} has a bad form: {exc}") from None
        if form.dimension is not output.dimension:
            raise SpecError(
                f"{owner}: output {output.key!r}'s form {output.form!r} doesn't write "
                f"{output.dimension.with_article}"
            )
        if output.precision is not None:
            raise SpecError(
                f"{owner}: output {output.key!r} gives a precision and a form; a form has "
                "its own fineness"
            )
        if output.signed:
            raise SpecError(
                f"{owner}: output {output.key!r} is signed and in a form; a form writes its "
                "own sign"
            )
        return
    if not output.unit:
        if output.precision is not None:
            raise SpecError(f"{owner}: output {output.key!r} gives a precision but no unit")
        return
    try:
        unit = get_unit(output.unit, output.dimension)
    except (InputError, UsageError) as exc:
        raise SpecError(f"{owner}: output {output.key!r} has a bad unit: {exc}") from None
    if unit.dimension is not output.dimension or unit.symbol != output.unit:
        raise SpecError(
            f"{owner}: output {output.key!r} names {output.unit!r}, which isn't the key "
            f"symbol of {output.dimension.with_article} unit"
        )


def _resolve(
    p: Param,
    inputs: Mapping[str, float],
    settings: DomainValues | None,
    labels: Mapping[str, InputSource],
) -> tuple[float, InputSource]:
    """Pick one input's value and source by the precedence rule (ADR-0013 §4)."""
    if p.key in inputs:
        return float(inputs[p.key]), labels.get(p.key, EXPLICIT)
    if p.shared and settings is not None and p.key in settings.values:
        origin = settings.origins.get(p.key)
        source = InputSource(
            SourceKind.DOMAIN,
            settings.label,
            domain=settings.domain_id,
            reference=None if origin is None else origin.reference,
        )
        return float(settings.values[p.key]), source
    if p.shared and settings is not None and p.key in settings.derived:
        derived = settings.derived[p.key]
        return derived.value, derived.source
    default = p.default_value()
    if default is None:
        raise InputError(f"Missing input: {p.named}")
    return default, DEFAULT


def _derived(p: Param, source: InputSource, settings: DomainValues | None) -> DerivedValue | None:
    """The derived value ``p`` took, if it took one."""
    if source.kind is not SourceKind.DERIVED or settings is None:
        return None
    return settings.derived.get(p.key)


def _origin(p: Param, source: InputSource, settings: DomainValues | None) -> ValueOrigin | None:
    """The origin of the set value ``p`` took, if it took one the user applied."""
    if source.kind is not SourceKind.DOMAIN or settings is None:
        return None
    return settings.origins.get(p.key)


def _unique(owner: str, what: str, items: list[str]) -> None:
    seen: set[str] = set()
    for item in items:
        if item in seen:
            raise SpecError(f"{owner}: duplicate {what} {item!r}")
        seen.add(item)
