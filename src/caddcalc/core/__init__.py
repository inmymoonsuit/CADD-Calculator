"""Core framework: units, formulas, the calculator model, and the registry.

Standard library only. Nothing here may import ``caddcalc.gui``, ``caddcalc.cli``,
or any third-party package (ADR-0003).
"""

from caddcalc.core.calculator import Calculator, Context, Result, ResultCheck
from caddcalc.core.choices import Choice, ChoiceResolver, DerivedValue, Option
from caddcalc.core.citations import License, Publication, PublicationKind, Source
from caddcalc.core.domain import (
    Domain,
    DomainValues,
    Fact,
    SelectionDetails,
    StartingValue,
    ValueOrigin,
)
from caddcalc.core.errors import (
    CaddCalcError,
    CalculationError,
    InputError,
    SpecError,
    UnknownCalculatorError,
    UnknownDomainError,
    UsageError,
)
from caddcalc.core.notes import Note, NoteKind, Quantity
from caddcalc.core.provenance import InputSource, SourceKind
from caddcalc.core.refdata import (
    Band,
    Basis,
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
    "Fact",
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
    "Publication",
    "PublicationKind",
    "Quantity",
    "Reference",
    "ReferenceTable",
    "ReferenceValue",
    "Registry",
    "Result",
    "ResultCheck",
    "SelectionDetails",
    "Source",
    "SourceKind",
    "SpecError",
    "StartingValue",
    "Step",
    "TablePublication",
    "TableSource",
    "TableSpec",
    "TrustLevel",
    "TypedValue",
    "UnknownCalculatorError",
    "UnknownDomainError",
    "UsageError",
    "ValueOrigin",
    "Verification",
    "load_table",
    "nominal",
    "parse_quantity",
    "parse_quantity_detailed",
    "parse_table",
]
