"""Sheet-metal calculators: bends, flat patterns, press-brake tooling, and developments."""

from caddcalc.calculators.sheet_metal.bends import (
    BendAllowance,
    FormedSegmentFlatLength,
    VDieOpening,
)
from caddcalc.calculators.sheet_metal.cone import TruncatedConeLayout

CALCULATORS = (BendAllowance, FormedSegmentFlatLength, VDieOpening, TruncatedConeLayout)

__all__ = [
    "CALCULATORS",
    "BendAllowance",
    "FormedSegmentFlatLength",
    "TruncatedConeLayout",
    "VDieOpening",
]
