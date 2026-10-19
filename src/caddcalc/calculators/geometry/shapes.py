"""The circle, the rectangle, the regular polygon, and the arc and sector (ADR-0018 §2).

Each calculator gives every property of its shape at once, from the dimensions that
define it. Formulas are MH31's "Dimensions of Plane Figures" (printed pp. 75-82); the
sagitta is arranged to keep its digits, as the method's notes say.
"""

from __future__ import annotations

from typing import override

from caddcalc.calculators.geometry.common import (
    ANGLE,
    AREA,
    COUNT,
    LENGTH,
    MH31_CIRCLE,
    MH31_POLYGON,
    MH31_POLYGON_TABLE,
    MH31_RECTANGLE,
    MH31_SEGMENT,
    POCKET_PLANE_FIGURES,
    POCKET_SEGMENTS,
    length,
    method,
)
from caddcalc.calculators.geometry.domain import DOMAIN
from caddcalc.core import N_, Calculator, Context, Output, Param


class Circle(Calculator):
    """A circle's circumference and area, from its diameter or its radius."""

    id = "geometry.circle"
    name = N_("Circle")
    domain = DOMAIN.id
    summary = N_("Circumference, area, radius, and diameter of a circle.")
    params = (
        length("diameter", "D", "Diameter", "2 in", "The circle's diameter.", "diameter"),
        length("radius", "r", "Radius", "1 in", "The circle's radius.", "radius"),
    )
    outputs = (
        Output("diameter", "D", "Diameter", LENGTH),
        Output("radius", "r", "Radius", LENGTH),
        Output("circumference", "C", "Circumference", LENGTH),
        Output("area", "S", "Area", AREA),
    )
    methods = (
        method(
            "diameter",
            "From the diameter",
            "C = π·D, S = π·D²/4",
            MH31_CIRCLE,
            POCKET_PLANE_FIGURES,
        ),
        method(
            "radius",
            "From the radius",
            "C = 2·π·r, S = π·r²",
            MH31_CIRCLE,
            POCKET_PLANE_FIGURES,
        ),
    )

    @override
    def compute(self, ctx: Context) -> None:
        if ctx.method == "diameter":
            ctx.given("D", output="diameter")
            ctx.calc("r", "D/2", label="Radius", dimension=LENGTH, output="radius")
            ctx.calc("C", "pi*D", label="Circumference", dimension=LENGTH, output="circumference")
            ctx.calc("S", "pi*D**2/4", label="Area", dimension=AREA, output="area")
        else:
            ctx.given("r", output="radius")
            ctx.calc("D", "2*r", label="Diameter", dimension=LENGTH, output="diameter")
            ctx.calc("C", "2*pi*r", label="Circumference", dimension=LENGTH, output="circumference")
            ctx.calc("S", "pi*r**2", label="Area", dimension=AREA, output="area")


class Rectangle(Calculator):
    """A rectangle's perimeter, area, and diagonal, from its length and width."""

    id = "geometry.rectangle"
    name = N_("Rectangle")
    domain = DOMAIN.id
    summary = N_("Perimeter, area, and diagonal of a rectangle.")
    params = (
        length("length", "L", "Length", "4 in", "One side of the rectangle."),
        length("width", "W", "Width", "3 in", "The side at right angles to the length."),
    )
    outputs = (
        Output("perimeter", "P", "Perimeter", LENGTH),
        Output("area", "S", "Area", AREA),
        Output("diagonal", "d", "Diagonal", LENGTH, "From one corner to the opposite one."),
    )
    methods = (
        method(
            "standard",
            "Length and width",
            "P = 2·(L + W), S = L·W, d = √(L² + W²)",
            MH31_RECTANGLE,
            POCKET_PLANE_FIGURES,
        ),
    )

    @override
    def compute(self, ctx: Context) -> None:
        ctx.calc("P", "2*(L + W)", label="Perimeter", dimension=LENGTH, output="perimeter")
        ctx.calc("S", "L*W", label="Area", dimension=AREA, output="area")
        ctx.calc("d", "sqrt(L**2 + W**2)", label="Diagonal", dimension=LENGTH, output="diagonal")


POLYGON_ODD = (
    "With an odd number of sides, no two flats are parallel, so a caliper across the "
    "polygon reads {reading}: the inscribed radius plus the circumscribed radius, r + R, "
    "not the across-flats size."
)


POLYGON_NOTES = (
    "Across flats is the inscribed circle's diameter, 2r, and across corners the "
    "circumscribed circle's, 2R. With an odd number of sides there are no parallel flats, "
    "so a caliper reads r + R; the result says what it reads.",
)


class RegularPolygon(Calculator):
    """A regular polygon's sizes, perimeter, and area, from its sides and one size."""

    id = "geometry.regular_polygon"
    name = N_("Regular polygon")
    domain = DOMAIN.id
    summary = N_("Side, across flats, across corners, perimeter, and area of a regular polygon.")
    params = (
        Param(
            "sides",
            "N",
            "Number of sides",
            COUNT,
            default="6",
            minimum=3.0,
            help="How many equal sides the polygon has: a whole number, 3 or more.",
        ),
        length("side", "a", "Side", "1 in", "The length of one side.", "side"),
        length(
            "across_flats",
            "AF",
            "Across flats (inscribed circle)",
            "1 in",
            "The inscribed circle's diameter: across two parallel flats when the number "
            "of sides is even.",
            "across_flats",
        ),
        length(
            "across_corners",
            "AC",
            "Across corners (circumscribed circle)",
            "1 in",
            "The circumscribed circle's diameter: across two opposite corners when the "
            "number of sides is even.",
            "across_corners",
        ),
    )
    outputs = (
        Output("side", "a", "Side", LENGTH),
        Output("across_flats", "AF", "Across flats (inscribed circle)", LENGTH),
        Output("across_corners", "AC", "Across corners (circumscribed circle)", LENGTH),
        Output("perimeter", "P", "Perimeter", LENGTH),
        Output("area", "S", "Area", AREA),
    )
    methods = (
        method(
            "side",
            "From the side",
            "AF = a/tan(180°/N), AC = a/sin(180°/N)",
            MH31_POLYGON,
            MH31_POLYGON_TABLE,
            POCKET_PLANE_FIGURES,
            notes=POLYGON_NOTES,
        ),
        method(
            "across_flats",
            "From across flats",
            "a = AF·tan(180°/N), AC = AF/cos(180°/N)",
            MH31_POLYGON,
            MH31_POLYGON_TABLE,
            POCKET_PLANE_FIGURES,
            notes=POLYGON_NOTES,
        ),
        method(
            "across_corners",
            "From across corners",
            "a = AC·sin(180°/N), AF = AC·cos(180°/N)",
            MH31_POLYGON,
            MH31_POLYGON_TABLE,
            POCKET_PLANE_FIGURES,
            notes=POLYGON_NOTES,
        ),
    )

    @override
    def compute(self, ctx: Context) -> None:
        sides = ctx["sides"]
        if ctx.method == "side":
            ctx.given("a", output="side")
            ctx.calc(
                "AF", "a/tand(180/N)", label="Across flats", dimension=LENGTH, output="across_flats"
            )
            ctx.calc(
                "AC",
                "a/sind(180/N)",
                label="Across corners",
                dimension=LENGTH,
                output="across_corners",
            )
        elif ctx.method == "across_flats":
            ctx.given("AF", output="across_flats")
            ctx.calc("a", "AF*tand(180/N)", label="Side", dimension=LENGTH, output="side")
            ctx.calc(
                "AC",
                "AF/cosd(180/N)",
                label="Across corners",
                dimension=LENGTH,
                output="across_corners",
            )
        else:
            ctx.given("AC", output="across_corners")
            ctx.calc("a", "AC*sind(180/N)", label="Side", dimension=LENGTH, output="side")
            ctx.calc(
                "AF",
                "AC*cosd(180/N)",
                label="Across flats",
                dimension=LENGTH,
                output="across_flats",
            )
        ctx.calc("P", "N*a", label="Perimeter", dimension=LENGTH, output="perimeter")
        ctx.calc("S", "N*a*AF/4", label="Area", dimension=AREA, output="area")
        if int(sides) % 2:
            reading = (ctx.value("AF") + ctx.value("AC")) / 2
            ctx.warn(
                POLYGON_ODD,
                subjects=("sides", "across_flats", "across_corners"),
                quantities={"reading": (reading, LENGTH)},
            )


class ArcSector(Calculator):
    """An arc's length, chord, and sagitta, and its sector's area."""

    id = "geometry.arc_sector"
    name = N_("Arc and sector")
    domain = DOMAIN.id
    summary = N_(
        "Arc length, chord, sagitta (rise), and sector area, from the radius and the "
        "included angle."
    )
    params = (
        length("radius", "r", "Radius", "2 in", "The arc's radius."),
        Param(
            "angle",
            "A",
            "Included angle",
            ANGLE,
            default="90 deg",
            minimum=0.0,
            min_inclusive=False,
            maximum=360.0,
            help=(
                "The angle the arc spans at its center, greater than 0° and up to 360°. "
                "Past 180°, the arc is the major arc."
            ),
        ),
    )
    outputs = (
        Output("arc_length", "L", "Arc length", LENGTH),
        Output("chord", "c", "Chord", LENGTH, "The straight line between the arc's ends."),
        Output(
            "sagitta",
            "h",
            "Sagitta (rise)",
            LENGTH,
            "From the chord's middle to the arc, at right angles to the chord.",
        ),
        Output("sector_area", "S", "Sector area", AREA),
    )
    methods = (
        method(
            "standard",
            "Radius and angle",
            "L = π·r·A/180°, c = 2·r·sin(A/2), h = 2·r·sin²(A/4), S = π·r²·A/360°",
            MH31_CIRCLE,
            MH31_SEGMENT,
            POCKET_PLANE_FIGURES,
            POCKET_SEGMENTS,
            notes=(
                "The sagitta is the Handbook's r·(1 − cos(A/2)) written as 2·r·sin²(A/4), "
                "the same value, which keeps its digits for a small angle, where "
                "1 − cos(A/2) loses them.",
            ),
        ),
    )

    @override
    def compute(self, ctx: Context) -> None:
        ctx.calc("L", "pi*r*A/180", label="Arc length", dimension=LENGTH, output="arc_length")
        ctx.calc("c", "2*r*sind(A/2)", label="Chord", dimension=LENGTH, output="chord")
        ctx.calc("h", "2*r*sind(A/4)**2", label="Sagitta", dimension=LENGTH, output="sagitta")
        ctx.calc("S", "pi*r**2*A/360", label="Sector area", dimension=AREA, output="sector_area")
