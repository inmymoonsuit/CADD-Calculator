"""Unit converters: one value, shown in every unit of its kind at once (ADR-0018 §3)."""

from caddcalc.calculators.conversions.converters import (
    AngleConverter,
    AreaConverter,
    LengthConverter,
    StressConverter,
)
from caddcalc.calculators.conversions.domain import DOMAIN

CALCULATORS = (LengthConverter, AngleConverter, AreaConverter, StressConverter)

__all__ = [
    "CALCULATORS",
    "DOMAIN",
    "AngleConverter",
    "AreaConverter",
    "LengthConverter",
    "StressConverter",
]
