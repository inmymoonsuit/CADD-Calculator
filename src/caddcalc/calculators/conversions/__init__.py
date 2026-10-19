"""Unit converters: one value in, the same value out in another unit (ADR-0024 §7)."""

from caddcalc.calculators.conversions.converters import (
    AngleConverter,
    AreaConverter,
    DecimalToFraction,
    FractionToDecimal,
    LengthConverter,
    StressConverter,
)
from caddcalc.calculators.conversions.domain import DOMAIN

CALCULATORS = (
    LengthConverter,
    FractionToDecimal,
    DecimalToFraction,
    AngleConverter,
    AreaConverter,
    StressConverter,
)

__all__ = [
    "CALCULATORS",
    "DOMAIN",
    "AngleConverter",
    "AreaConverter",
    "DecimalToFraction",
    "FractionToDecimal",
    "LengthConverter",
    "StressConverter",
]
