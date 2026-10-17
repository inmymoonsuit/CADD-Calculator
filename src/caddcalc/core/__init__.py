"""Core framework: units, formulas, the calculator model, and the registry.

Standard library only. Nothing here may import ``caddcalc.gui``, ``caddcalc.cli``,
or any third-party package (ADR-0003).
"""

from caddcalc.core.calculator import Calculator, Context, Result, Step
from caddcalc.core.errors import (
    CaddCalcError,
    CalculationError,
    InputError,
    SpecError,
    UnknownCalculatorError,
)
from caddcalc.core.registry import Registry
from caddcalc.core.spec import Method, Output, Param, Reference, Verification
from caddcalc.core.units import Dimension, parse_quantity

__all__ = [
    "CaddCalcError",
    "CalculationError",
    "Calculator",
    "Context",
    "Dimension",
    "InputError",
    "Method",
    "Output",
    "Param",
    "Reference",
    "Registry",
    "Result",
    "SpecError",
    "Step",
    "UnknownCalculatorError",
    "Verification",
    "parse_quantity",
]
