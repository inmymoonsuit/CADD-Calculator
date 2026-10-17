"""Core framework: units, formulas, the calculator model, and the registry.

Standard library only. Nothing here may import ``caddcalc.gui``, ``caddcalc.cli``,
or any third-party package (ADR-0003).
"""

from caddcalc.core.calculator import Calculator, Context, Result
from caddcalc.core.choices import Choice, ChoiceResolver, DerivedValue, Option
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
from caddcalc.core.notes import Note, NoteKind
from caddcalc.core.provenance import InputSource, SourceKind
from caddcalc.core.refdata import (
    Band,
    Basis,
    License,
    PublicationKind,
    ReferenceTable,
    ReferenceValue,
    TablePublication,
    TableSource,
    TableSpec,
    TrustLevel,
    load_table,
    nominal,
    parse_table,
)
from caddcalc.core.reference import Reference
from caddcalc.core.registry import Registry
from caddcalc.core.settings import ClearedChoice, DomainSettings
from caddcalc.core.spec import Method, OutOfRangeError, Output, Param, Verification
from caddcalc.core.steps import Step
from caddcalc.core.units import (
    Dimension,
    ParsedQuantity,
    TypedValue,
    parse_quantity,
    parse_quantity_detailed,
)

__all__ = [
    "Band",
    "Basis",
    "CaddCalcError",
    "CalculationError",
    "Calculator",
    "Choice",
    "ChoiceResolver",
    "ClearedChoice",
    "Context",
    "DerivedValue",
    "Dimension",
    "Domain",
    "DomainSettings",
    "DomainValues",
    "InputError",
    "InputSource",
    "License",
    "Method",
    "Note",
    "NoteKind",
    "Option",
    "OutOfRangeError",
    "Output",
    "Param",
    "ParsedQuantity",
    "PublicationKind",
    "Reference",
    "ReferenceTable",
    "ReferenceValue",
    "Registry",
    "Result",
    "SourceKind",
    "SpecError",
    "Step",
    "TablePublication",
    "TableSource",
    "TableSpec",
    "TrustLevel",
    "TypedValue",
    "UnknownCalculatorError",
    "UnknownDomainError",
    "UsageError",
    "Verification",
    "load_table",
    "nominal",
    "parse_quantity",
    "parse_quantity_detailed",
    "parse_table",
]
