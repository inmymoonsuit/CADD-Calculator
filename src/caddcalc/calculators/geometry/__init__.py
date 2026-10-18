"""Geometry calculators: one per plane figure, each giving every property at once."""

from caddcalc.calculators.geometry.domain import DOMAIN
from caddcalc.calculators.geometry.shapes import ArcSector, Circle, Rectangle, RegularPolygon
from caddcalc.calculators.geometry.triangles import RightTriangle, Triangle

CALCULATORS = (Circle, Rectangle, Triangle, RightTriangle, RegularPolygon, ArcSector)

__all__ = [
    "CALCULATORS",
    "DOMAIN",
    "ArcSector",
    "Circle",
    "Rectangle",
    "RegularPolygon",
    "RightTriangle",
    "Triangle",
]
