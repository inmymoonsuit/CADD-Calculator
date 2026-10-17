"""Declarative pieces of a calculator definition: parameters, outputs, and methods."""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum

from caddcalc.core.errors import InputError
from caddcalc.core.provenance import EXPLICIT, InputSource, SourceKind
from caddcalc.core.reference import Reference
from caddcalc.core.units import BASE_UNITS, Dimension, parse_quantity


class Verification(Enum):
    """Whether a method has been checked against a published source (ADR-0004).

    This is independent of ``Method.legacy``: a method can reproduce the course spreadsheets
    and also be verified against a handbook.
    """

    UNVERIFIED = "unverified"
    """No published worked example has been checked yet."""
    VERIFIED = "verified"
    """Checked against at least one cited published source, with a worked example as a test."""


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
    """Lower bound in base units (mm, deg, ratio)."""
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

    def check(self, value: float, source: InputSource = EXPLICIT) -> None:
        """Check that ``value`` is finite and within the allowed range.

        Args:
            value: The value, in base units.
            source: Where the value came from, so an error can say so.

        Raises:
            InputError: The value is not finite.
            OutOfRangeError: The value is out of range.
        """
        if not math.isfinite(value):
            raise InputError(f"{self.label} ({self.symbol}) must be a finite number")
        lo, hi = self.minimum, self.maximum
        if lo is not None and (value < lo or (value == lo and not self.min_inclusive)):
            raise OutOfRangeError(self, value, bound=lo, above=False, source=source)
        if hi is not None and (value > hi or (value == hi and not self.max_inclusive)):
            raise OutOfRangeError(self, value, bound=hi, above=True, source=source)


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
        unit = BASE_UNITS[param.dimension]
        super().__init__(self.describe(lambda v: f"{v:g} {unit}".rstrip()))

    def describe(self, show: Callable[[float], str]) -> str:
        """Return the message, with ``show`` writing each base-unit value as text."""
        p = self.param
        inclusive = p.max_inclusive if self.above else p.min_inclusive
        need = f"{_RELATION[self.above, inclusive]} {show(self.bound)}"
        if self.source.kind is SourceKind.DOMAIN:
            return (
                f"{p.label} ({p.symbol}) from {self.source.label} is {show(self.value)}, "
                f"but this calculator needs {need}. Override it in this calculator."
            )
        return f"{p.label} ({p.symbol}) must be {need}"


@dataclass(frozen=True)
class Output:
    """One result a calculator produces."""

    key: str
    symbol: str
    label: str
    dimension: Dimension
    help: str = ""


@dataclass(frozen=True)
class Method:
    """One way of computing a calculator's outputs, such as a K-factor or an empirical formula."""

    key: str
    label: str
    summary: str
    verification: Verification
    references: tuple[Reference, ...] = ()
    notes: tuple[str, ...] = field(default_factory=tuple)
    legacy: bool = False
    """Reproduces the original course spreadsheets exactly (pinned by golden tests, ADR-0010)."""

    @property
    def status(self) -> str:
        """Display text, e.g. ``"unverified · reproduces legacy"``."""
        return self.verification.value + (" · reproduces legacy" if self.legacy else "")
