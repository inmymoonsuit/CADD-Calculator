"""Core framework: units, formulas, the calculator model, and the registry.

Standard library only. Nothing here may import ``caddcalc.gui``, ``caddcalc.cli``,
or any third-party package (ADR-0003).
"""

from caddcalc.core.calculator import Calculator, Context, Result, Step
from caddcalc.core.domain import Domain, DomainValues
from caddcalc.core.errors import (
    CaddCalcError,
    CalculationError,
    InputError,
    SpecError,
    UnknownCalculatorError,
    UnknownDomainError,
    UsageError,
)
from caddcalc.core.provenance import InputSource, SourceKind
from caddcalc.core.reference import Reference
from caddcalc.core.registry import Registry
from caddcalc.core.settings import DomainSettings
from caddcalc.core.spec import Method, OutOfRangeError, Output, Param, Verification
from caddcalc.core.units import (
    Dimension,
    ParsedQuantity,
    TypedValue,
    parse_quantity,
    parse_quantity_detailed,
)

__all__ = [
    "CaddCalcError",
    "CalculationError",
    "Calculator",
    "Context",
    "Dimension",
    "Domain",
    "DomainSettings",
    "DomainValues",
    "InputError",
    "InputSource",
    "Method",
    "OutOfRangeError",
    "Output",
    "Param",
    "ParsedQuantity",
    "Reference",
    "Registry",
    "Result",
    "SourceKind",
    "SpecError",
    "Step",
    "TypedValue",
    "UnknownCalculatorError",
    "UnknownDomainError",
    "UsageError",
    "Verification",
    "parse_quantity",
    "parse_quantity_detailed",
]
