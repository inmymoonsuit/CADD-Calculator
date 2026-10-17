"""Turning base-unit values into display text. Rounding happens only here (ADR-0005)."""

from __future__ import annotations

import math
from dataclasses import dataclass
from fractions import Fraction

from caddcalc.core import expr
from caddcalc.core.calculator import Result, Step
from caddcalc.core.errors import CaddCalcError
from caddcalc.core.provenance import InputSource, SourceKind
from caddcalc.core.spec import OutOfRangeError
from caddcalc.core.units import Dimension, from_base, get_unit

DISCLAIMER = (
    "Results are for drafting and education. Verify against your shop's tooling, "
    "material data, and test bends before manufacturing."
)


@dataclass(frozen=True)
class DisplayPrefs:
    """How values are shown: length unit, decimals, and optional inch fractions."""

    length_unit: str = "in"
    decimals: int = 4
    angle_decimals: int = 2
    fraction_denominator: int | None = None
    """When set (e.g. 64) and the length unit is inches, also show the nearest fraction."""


def unit_suffix(dimension: Dimension, prefs: DisplayPrefs) -> str:
    """Return the unit text shown after a value, e.g. ``" in"`` or ``"°"``."""
    if dimension is Dimension.LENGTH:
        return f" {prefs.length_unit}"
    if dimension is Dimension.ANGLE:
        return "°"
    return ""


def display_value(value: float, dimension: Dimension, prefs: DisplayPrefs) -> float:
    """Convert a base-unit value to the display unit, without rounding."""
    if dimension is Dimension.LENGTH:
        return from_base(value, prefs.length_unit)
    return value  # angles display in degrees, ratios as-is


def format_number(value: float, decimals: int) -> str:
    """Return ``value`` rounded to ``decimals`` places, never as negative zero."""
    text = f"{value:.{decimals}f}"
    return "0" + text[2:] if text.startswith("-0") and float(text) == 0 else text


def format_value(
    value: float, dimension: Dimension, prefs: DisplayPrefs, *, unit: bool = True
) -> str:
    """Return a base-unit value as display text, e.g. ``0.3119 in``.

    Args:
        value: The value in base units.
        dimension: What the value measures.
        prefs: The display unit, decimals, and fraction preference.
        unit: Append the unit (and the nearest fraction, when enabled).
    """
    shown = display_value(value, dimension, prefs)
    decimals = prefs.angle_decimals if dimension is Dimension.ANGLE else prefs.decimals
    text = format_number(shown, decimals)
    if unit:
        text += unit_suffix(dimension, prefs)
    if (
        unit
        and dimension is Dimension.LENGTH
        and prefs.fraction_denominator
        and get_unit(prefs.length_unit).symbol == "in"
    ):
        text += f'  (≈ {to_fraction(shown, prefs.fraction_denominator)}")'
    return text


def to_fraction(value: float, denominator: int = 64) -> str:
    """Nearest drafting fraction: ``1.015625`` → ``1-1/64``, ``0.5`` → ``1/2``."""
    if not math.isfinite(value):
        return str(value)
    sign = "-" if value < 0 else ""
    frac = Fraction(round(abs(value) * denominator), denominator)
    whole, rem = divmod(frac.numerator, frac.denominator)
    if rem == 0:
        return f"{sign}{whole}"
    part = f"{rem}/{frac.denominator}"
    return f"{sign}{whole}-{part}" if whole else f"{sign}{part}"


def render_step(step: Step, result: Result, prefs: DisplayPrefs) -> tuple[str, str | None, str]:
    """Return (symbolic, substituted, value) text for one step of the work.

    Substitution shows each symbol in display units, which is only meaningful for formulas
    that are dimensionally homogeneous. All built-in formulas are (see known-issues KI-005).
    """
    value_text = format_value(step.value, step.dimension, prefs)
    if step.expression is None:
        return (step.note, None, value_text)
    symbolic = expr.render_symbolic(step.expression)
    values: dict[str, str] = {}
    for name in expr.names(step.expression):
        v, dim = result.symbols[name]
        text = format_value(v, dim, prefs, unit=dim is Dimension.ANGLE)
        values[name] = f"({text})" if text.startswith("-") else text
    return (symbolic, expr.render_numeric(step.expression, values), value_text)


def describe_source(source: InputSource) -> str:
    """Return how an input's source is shown to users, e.g. ``"Sheet Metal settings"``.

    The GUI and the CLI both use this, so they word sources the same way (ADR-0013 §5).
    """
    if source.kind is SourceKind.EXPLICIT:
        return "entered"
    if source.kind is SourceKind.DEFAULT:
        return "default"
    label = source.label or ("domain settings" if source.kind is SourceKind.DOMAIN else "derived")
    return label if source.reference is None else f"{label}, {source.reference}"


def describe_error(error: CaddCalcError, prefs: DisplayPrefs) -> str:
    """Return an error's message for users, with any values in display units.

    The GUI and the CLI both use this, so an error reads the same in both.
    """
    if isinstance(error, OutOfRangeError):
        dimension = error.param.dimension
        return error.describe(lambda v: _quantity_text(v, dimension, prefs))
    return str(error)


def _quantity_text(value: float, dimension: Dimension, prefs: DisplayPrefs) -> str:
    """Write a value for a message, e.g. ``0.393701 in``.

    It keeps six significant digits rather than the display decimals, so a bound in a
    message isn't rounded to a value the rejected input seems to satisfy.
    """
    return f"{display_value(value, dimension, prefs):g}{unit_suffix(dimension, prefs)}"
