"""Sheet-metal calculators: bends, flat patterns, press-brake tooling, and developments."""

from caddcalc.calculators.sheet_metal.bends import (
    BendAllowance,
    FormedSegmentFlatLength,
    VDieOpening,
)
from caddcalc.calculators.sheet_metal.cone import TruncatedConeLayout
from caddcalc.calculators.sheet_metal.domain import DOMAIN

CALCULATORS = (BendAllowance, FormedSegmentFlatLength, VDieOpening, TruncatedConeLayout)

__all__ = [
    "CALCULATORS",
    "DOMAIN",
    "BendAllowance",
    "FormedSegmentFlatLength",
    "TruncatedConeLayout",
    "VDieOpening",
]
