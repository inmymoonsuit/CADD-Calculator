"""Declarative pieces of a calculator definition: parameters, outputs, methods, references."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum

from caddcalc.core.errors import InputError
from caddcalc.core.units import Dimension, parse_quantity


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
class Reference:
    """A citation. Cite edition, section, and page. Do not copy copyrighted text or tables."""

    title: str
    detail: str = ""
    url: str = ""

    def __str__(self) -> str:
        return f"{self.title}, {self.detail}" if self.detail else self.title


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

    def default_value(self) -> float | None:
        """Return the default in base units, or ``None`` if there is no default."""
        return None if self.default is None else parse_quantity(self.default, self.dimension)

    def used_by(self, method_key: str) -> bool:
        """Return whether the method ``method_key`` uses this parameter."""
        return not self.methods or method_key in self.methods

    def check(self, value: float) -> None:
        """Check that ``value`` (in base units) is finite and within the allowed range.

        Raises:
            InputError: The value is not finite or is out of range.
        """
        if not math.isfinite(value):
            raise InputError(f"{self.label} ({self.symbol}) must be a finite number")
        lo, hi = self.minimum, self.maximum
        if lo is not None and (value < lo or (value == lo and not self.min_inclusive)):
            word = "at least" if self.min_inclusive else "greater than"
            raise InputError(f"{self.label} ({self.symbol}) must be {word} {lo:g}")
        if hi is not None and (value > hi or (value == hi and not self.max_inclusive)):
            word = "at most" if self.max_inclusive else "less than"
            raise InputError(f"{self.label} ({self.symbol}) must be {word} {hi:g}")


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
