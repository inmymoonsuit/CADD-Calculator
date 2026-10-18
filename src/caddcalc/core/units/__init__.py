"""Units: dimensions, units, conversion, and parsing, from one registry (ADR-0019).

Standard library only. The built-in units are declared, with their citations, in
``units.builtin``; ``units.unit_registry`` checks and holds them, with any plugin's; and
``units.parsing`` reads what people type. Every name the old ``core.units`` module had is
here still.
"""

from caddcalc.core.units.compound import CompoundForm, CompoundText
from caddcalc.core.units.model import (
    CLOSE_UP_SYMBOLS,
    Derivation,
    Dimension,
    DimensionSpec,
    Exact,
    Precision,
    Unit,
    UnitSystem,
)
from caddcalc.core.units.parsing import (
    BASE_UNITS,
    UNITS,
    ParsedQuantity,
    TypedValue,
    base_text,
    base_unit_names,
    convert,
    from_base,
    get_unit,
    parse_number,
    parse_quantity,
    parse_quantity_detailed,
    to_base,
    units_for,
)
from caddcalc.core.units.unit_registry import (
    ENTRY_POINT_GROUP,
    UnitRegistry,
    build_registry,
    clear_registry,
    registry,
)

__all__ = [
    "BASE_UNITS",
    "CLOSE_UP_SYMBOLS",
    "ENTRY_POINT_GROUP",
    "UNITS",
    "CompoundForm",
    "CompoundText",
    "Derivation",
    "Dimension",
    "DimensionSpec",
    "Exact",
    "ParsedQuantity",
    "Precision",
    "TypedValue",
    "Unit",
    "UnitRegistry",
    "UnitSystem",
    "base_text",
    "base_unit_names",
    "build_registry",
    "clear_registry",
    "convert",
    "from_base",
    "get_unit",
    "parse_number",
    "parse_quantity",
    "parse_quantity_detailed",
    "registry",
    "to_base",
    "units_for",
]
