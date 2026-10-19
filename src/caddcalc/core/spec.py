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
from caddcalc.core.units import Dimension, Precision, base_text, parse_quantity


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
    "K-factor", isn't named by it.
    """
    if re.search(rf"(?<![\w-]){re.escape(symbol)}(?![\w-])", label):
        return label
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

    def default_value(self) -> float | None:
        """Return the default in base units, or ``None`` if there is no default."""
        return None if self.default is None else parse_quantity(self.default, self.dimension)

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
            InputError: The value is not finite, or a count's isn't whole.
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
    """The precision a fixed-unit output is shown with, where the unit's own doesn't suit
    it, such as an error shown to fixed decimals; ``None`` for the registry's. Only an
    output with a ``unit`` may give one: a form has its own fineness."""
    form: str = ""
    """The key of a compound form it's always shown in, e.g. ``"ft_in"`` for feet and
    inches or ``"dms"`` for degrees, minutes and seconds (ADR-0019 §2); empty for none.
    An output gives a unit or a form, not both."""
    signed: bool = False
    """Whether it's a difference whose direction matters, such as an error: a value shown
    above zero gets a plus sign, as ``+0.002500 in``, and it takes no inch fraction hint.
    A compound form writes its own sign, so it ignores this."""


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
