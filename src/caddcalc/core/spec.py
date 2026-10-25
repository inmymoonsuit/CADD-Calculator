"""Declarative pieces of a calculator definition: parameters, outputs, and methods."""

from __future__ import annotations

import math
import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from enum import Enum
from types import MappingProxyType

from caddcalc.core.errors import InputError, SpecError
from caddcalc.core.notes import Quantity, check_template
from caddcalc.core.provenance import EXPLICIT, InputSource, SourceKind
from caddcalc.core.reference import Reference
from caddcalc.core.units import (
    CompoundForm,
    Dimension,
    Precision,
    base_text,
    parse_quantity,
    parse_quantity_detailed,
    registry,
)
from caddcalc.core.units.model import COUNT_LIMIT


class Verification(Enum):
    """Whether a method has been checked against a published source (ADR-0004).

    This is independent of ``Method.legacy``: a method can reproduce the course spreadsheets
    and also be verified against a handbook.
    """

    UNVERIFIED = "unverified"
    """No published worked example has been checked yet."""
    VERIFIED = "verified"
    """Checked against at least one cited published source, with a worked example as a test."""


def named(label: str, symbol: str) -> str:
    """Return a label with its symbol, ``Thickness (T)``, or the label alone if it has it.

    "Side a" and "Angle A (opposite a)" name their symbols already, so a message or a
    field says "Side a", not "Side a (a)". A symbol inside a word, such as K in
    "K-factor", isn't named by it. A label that ends in parentheses takes the symbol
    inside them: "Across flats (inscribed circle, AF)", never two pairs.
    """
    if re.search(rf"(?<![\w-]){re.escape(symbol)}(?![\w-])", label):
        return label
    if label.endswith(")") and "(" in label:
        return f"{label[:-1]}, {symbol})"
    return f"{label} ({symbol})"


@dataclass(frozen=True)
class Param:
    """One input to a calculator."""

    key: str
    """Stable identifier used in the CLI, saved files, and the Python API (snake_case)."""
    symbol: str
    """Short identifier used in formulas, e.g. ``T``. Must be a valid Python identifier."""
    label: str
    dimension: Dimension
    default: str | None = None
    """Default value as text with units, e.g. ``"0.1046 in"``. Parsed with ``parse_quantity``."""
    minimum: float | None = None
    """Lower bound in base units (mm, deg, ratio, MPa)."""
    maximum: float | None = None
    min_inclusive: bool = True
    max_inclusive: bool = True
    help: str = ""
    methods: tuple[str, ...] = ()
    """Method keys that use this parameter. Empty means all methods."""
    shared: bool = False
    """Inherit the domain setting with the same key when the user has set it (ADR-0013)."""
    unit: str = ""
    """The id of the unit or form its field's picker starts in, e.g. ``"mm"`` or
    ``"ft_in"`` (ADR-0024 E1); empty for the unit ``default`` names."""
    units: tuple[str, ...] = ()
    """The ids its picker offers, in order, where it offers fewer than its dimension's
    (``registry().entry_choices``); empty for all of them."""
    allowed: tuple[tuple[float, str], ...] = ()
    """The only values it takes, each with what a choice box shows for it, e.g.
    ``((16, "1/16"), (32, "1/32"))`` for a fineness (ADR-0024 E7); empty for any value
    in range. A front end offers them as a choice, not a field."""

    @property
    def choices(self) -> tuple[str, ...]:
        """The ids its field's picker offers; a unitless one has its unnamed unit alone."""
        return self.units or registry().entry_choices(self.dimension)

    @property
    def default_choice(self) -> str | None:
        """The id its picker starts in: ``unit``, else the unit or form ``default`` names.

        A field with one choice, as a ratio's is, starts in it, and a default written in
        a form that reads, as ``1'-4"`` is, starts it in that form. ``None`` means none can
        be resolved, which ``Calculator.validate_spec`` refuses.
        """
        if self.unit:
            return self.unit
        if len(self.choices) == 1:
            return self.choices[0]
        if self.default is None:
            return None
        for form in registry().compounds_for(self.dimension):
            try:
                written = form.reads and form.parse(self.default.strip()) is not None
            except InputError:
                written = False
            if written and form.key in self.choices:
                return form.key
        try:
            parsed = parse_quantity_detailed(self.default, self.dimension)
        except InputError:
            return None
        return parsed.unit.symbol if parsed.explicit_unit else None

    def default_value(self) -> float | None:
        """Return the default in base units, or ``None`` if there is no default.

        A default with no unit in its text is in the unit its picker starts in
        (``default_choice``), as a number typed in the field would be: ``"0.1046"`` with
        ``unit="in"`` is 0.1046 in, never 0.1046 mm.
        """
        if self.default is None:
            return None
        choice = self.default_choice
        unit = None
        if choice is not None and choice in self.choices:  # else validate_spec refuses it
            picked = registry().choice(choice, self.dimension)
            unit = picked.full_unit if isinstance(picked, CompoundForm) else picked.symbol
        return parse_quantity(self.default, self.dimension, unit)

    def used_by(self, method_key: str) -> bool:
        """Return whether the method ``method_key`` uses this parameter."""
        return not self.methods or method_key in self.methods

    @property
    def named(self) -> str:
        """The label with its symbol, as messages and fields name the input (``named``)."""
        return named(self.label, self.symbol)

    def check(self, value: float, source: InputSource = EXPLICIT) -> None:
        """Check that ``value`` is finite, within the allowed range, and whole for a count.

        Args:
            value: The value, in base units.
            source: Where the value came from, so an error can say so.

        Raises:
            InputError: The value is not finite, a count's isn't whole, or it isn't one
                of the ``allowed`` values.
            OutOfRangeError: The value is out of range.
        """
        if not math.isfinite(value):
            raise InputError(f"{self.named} must be a finite number")
        lo, hi = self.minimum, self.maximum
        if lo is not None and (value < lo or (value == lo and not self.min_inclusive)):
            raise OutOfRangeError(self, value, bound=lo, above=False, source=source)
        if hi is not None and (value > hi or (value == hi and not self.max_inclusive)):
            raise OutOfRangeError(self, value, bound=hi, above=True, source=source)
        if self.dimension is Dimension.COUNT and not value.is_integer():
            raise InputError(f"{self.named} must be a whole number")
        if self.dimension is Dimension.COUNT and abs(value) >= COUNT_LIMIT:
            raise InputError(f"{self.named} must be under 2^53, to be held exactly")
        if self.allowed and value not in {v for v, _label in self.allowed}:
            labels = ", ".join(label for _v, label in self.allowed)
            raise InputError(f"{self.named} must be one of {labels}")


_RELATION = {
    (True, True): "at most",
    (True, False): "less than",
    (False, True): "at least",
    (False, False): "greater than",
}
"""How a bound is worded, by (above the maximum, bound is inclusive)."""


class OutOfRangeError(InputError):
    """A value is outside its parameter's allowed range.

    It carries the parts of the message, so a front end can word it in display units with
    ``core.formatting.describe_error``. ``str()`` gives the message in base units.

    Attributes:
        param: The parameter whose range the value breaks.
        value: The value, in base units.
        bound: The bound it breaks, in base units.
        above: Whether the value is above the maximum, rather than below the minimum.
        source: Where the value came from.
    """

    def __init__(
        self, param: Param, value: float, *, bound: float, above: bool, source: InputSource
    ) -> None:
        self.param = param
        self.value = value
        self.bound = bound
        self.above = above
        self.source = source
        super().__init__(self.describe(lambda v: base_text(v, param.dimension)))

    @property
    def relation(self) -> str:
        """What the bound requires, e.g. ``"at most"`` or ``"greater than"``."""
        inclusive = self.param.max_inclusive if self.above else self.param.min_inclusive
        return _RELATION[self.above, inclusive]

    def describe(self, show: Callable[[float], str]) -> str:
        """Return the message, with ``show`` writing each base-unit value as text."""
        p = self.param
        need = f"{self.relation} {show(self.bound)}"
        if self.source.kind in (SourceKind.DOMAIN, SourceKind.DERIVED):
            return (
                f"{p.named} from {self.source.label} is {show(self.value)}, "
                f"but this calculator needs {need}. Override it in this calculator."
            )
        return f"{p.named} must be {need}"


@dataclass(frozen=True)
class Output:
    """One result a calculator produces."""

    key: str
    symbol: str
    label: str
    dimension: Dimension
    help: str = ""
    unit: str = ""
    """The key symbol of a unit it's always shown in, whatever the display preferences,
    e.g. ``"mm"`` for a converter's millimetre row (ADR-0018 §3); empty to follow them.
    It's shown with ``precision`` if it gives one, else the registry's precision for that
    unit (``precision_for``)."""
    precision: Precision | None = None
    """The precision it's shown with in a unit, where the unit's own doesn't suit it, such
    as an error to fixed decimals, or a converter's value to significant figures, in its
    fixed unit, its pick or its set's unit; ``None`` for the registry's, for a fixed unit,
    or else its dimension's. A form has its own fineness, so an output with a fixed form
    can't give one, and one picked or set in a form is shown to the form's."""
    form: str = ""
    """The key of a compound form it's always shown in, e.g. ``"ft_in"`` for feet and
    inches or ``"dms"`` for degrees, minutes and seconds (ADR-0019 §2); empty for none.
    An output gives a unit or a form, not both."""
    signed: bool = False
    """Whether it's a difference whose direction matters, such as an error: a value shown
    above zero gets a plus sign, as ``+0.002500 in``, in its row and its work line, and it
    takes no inch fraction hint. A compound form writes its own sign and rounds to its
    fineness, so a signed output can't be in one: not fixed, picked, or in a set."""
    picks: tuple[str, ...] = ()
    """The ids of its own picker's choices, the first its default, where it's shown in a
    choice of its own rather than its calculator's output set (ADR-0024 D3, E1); empty
    to follow the set. An output gives ``picks`` or a fixed ``unit`` or ``form``."""
    follows: str = ""
    """The key of the input whose choice it follows until it's picked, by
    ``counterparts``, as a converter's output does (ADR-0024 §6, Q9); empty for none."""
    counterparts: Mapping[str, str] = field(default_factory=dict, hash=False)
    """The pick it shows for each choice of the input it ``follows``, e.g. ``{"in": "mm",
    "mm": "in"}``: the other system's counterpart. A choice not named shows the first
    pick."""

    def __post_init__(self) -> None:
        object.__setattr__(self, "counterparts", MappingProxyType(dict(self.counterparts)))

    @property
    def follows_set(self) -> bool:
        """Whether it's shown in its calculator's output set: no fixed unit, form or picks."""
        return not (self.unit or self.form or self.picks)


@dataclass(frozen=True)
class UnitSet:
    """A choice of the units a calculator's results are shown in (ADR-0024 E1, §5).

    A calculator's output picker offers its sets; each names one choice for each
    dimension its outputs use.
    """

    key: str
    """Its public id, e.g. ``"in"``, ``"mm"`` or ``"in_dms"``, as ``--output-set`` takes."""
    label: str
    """What the picker shows for it, e.g. ``"in · ° · in²"``, or a declared name marked
    for translation, e.g. ``N_("Inches and DMS")``."""
    choices: Mapping[Dimension, str]
    """The id of a unit or form for each dimension, e.g. ``{LENGTH: "in", AREA: "in²"}``."""

    def __post_init__(self) -> None:
        object.__setattr__(self, "choices", MappingProxyType(dict(self.choices)))


@dataclass(frozen=True)
class Method:
    """One way of computing a calculator's outputs, such as a K-factor or an empirical formula."""

    key: str
    label: str
    summary: str
    verification: Verification
    references: tuple[Reference, ...] = ()
    notes: tuple[str, ...] = field(default_factory=tuple)
    """What to know about the method, one sentence or two each. A note that gives values
    writes them as named fields, filled from ``quantities`` where it's shown."""
    legacy: bool = False
    """Reproduces the original course spreadsheets exactly (pinned by golden tests, ADR-0010)."""
    quantities: Mapping[str, Quantity] = field(default_factory=dict, hash=False)
    """The values the notes' fields name, in base units, e.g. ``{"course": (132.70, ANGLE)}``.

    So a note's numbers read in the user's units and number format, as the work's do; the
    text never holds a formatted number of the app's own (ADR-0020 M4). Without any, the
    notes are plain text, braces and all.
    """
    scope: str = ""
    """What a verified method's worked example covers, in a few words the status writes
    after "verified", e.g. ``"at 90°"``; empty when it covers the method's whole use."""
    verification_note: str = ""
    """What the status rests on, or why the method isn't verified here: a sentence or two,
    shown as the status's tooltip and after the notes."""

    def __post_init__(self) -> None:
        object.__setattr__(self, "quantities", MappingProxyType(dict(self.quantities)))
        if self.quantities:
            for note in self.notes:
                check_template(note, self.quantities.keys(), f"Method {self.key!r} note")
        if self.scope and self.verification is not Verification.VERIFIED:
            raise SpecError(f"Method {self.key!r} has a scope, but isn't verified")

    def notes_shown(self, show: Callable[[float, Dimension], str]) -> tuple[str, ...]:
        """Return the notes with their values filled, each written by ``show``.

        The verification note, if there is one, comes last.
        """
        notes = self.notes
        if self.quantities:
            values = {name: show(*quantity) for name, quantity in self.quantities.items()}
            notes = tuple(note.format_map(values) for note in notes)
        return (*notes, self.verification_note) if self.verification_note else notes

    @property
    def status(self) -> str:
        """Display text, e.g. ``"verified at 90°"`` or ``"unverified · reproduces legacy"``."""
        verification = " ".join(filter(None, (self.verification.value, self.scope)))
        return verification + (" · reproduces legacy" if self.legacy else "")


def check_picks(
    owner: str, dimension: Dimension, picks: tuple[str, ...], what: str, *, output: bool
) -> None:
    """Check that each id is a choice of ``dimension``, a field's or an output's.

    Raises:
        SpecError: An id repeats, or isn't a choice of ``dimension``.
    """
    units = registry()
    allowed = units.output_choices(dimension) if output else units.entry_choices(dimension)
    seen: set[str] = set()
    for pick in picks:
        if pick in seen:
            raise SpecError(f"{owner}: duplicate choice in {what} {pick!r}")
        seen.add(pick)
    for pick in picks:
        if pick not in allowed:
            known = ", ".join(c or "''" for c in allowed)
            raise SpecError(
                f"{owner}: {what} names {pick!r}, which isn't a choice for "
                f"{dimension.with_article}; there's {known}"
            )


def check_param_choices(owner: str, p: Param, *, kind: str = "parameter") -> None:
    """Check a parameter's picker: its choices exist, and its default choice resolves.

    A parameter with more than one choice needs a default choice: ``Param.unit``, or a
    default that names its unit, as ``"0.1046 in"`` does (ADR-0024 E1). A calculator's
    parameters and a domain's settings are checked alike (E-5); a setting has no default,
    so it names its unit, and ``kind`` names it so in a message: "setting".

    Raises:
        SpecError: A choice isn't one, or none resolves as the picker's first.
    """
    check_picks(owner, p.dimension, p.units, f"{kind} {p.key!r}'s units", output=False)
    choice = p.default_choice
    if choice is None:
        raise SpecError(
            f"{owner}: {kind} {p.key!r} has no default unit for its picker: give "
            "Param.unit, or a default that names its unit"
        )
    if choice not in p.choices:
        known = ", ".join(c or "''" for c in p.choices)
        raise SpecError(
            f"{owner}: {kind} {p.key!r} starts its picker in {choice!r}, which it "
            f"doesn't offer; it offers {known}"
        )
