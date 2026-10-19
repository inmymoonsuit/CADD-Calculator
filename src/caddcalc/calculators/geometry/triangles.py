"""A triangle from its three sides, and a right triangle from any two of its parts.

Every angle of the three-sided triangle comes from Kahan's half-angle formula, the law
of cosines (MH31 p. 96) rearranged to keep its digits, where MH31's own three-sides
procedure (p. 101) takes one angle from the law of sines, which can't give an obtuse
angle: a deliberate departure (ADR-0018 §2). The area is Heron's in Kahan's arrangement,
and a leg from the hypotenuse is √((c − a)·(c + a)), both arranged to keep their digits.
"""

from __future__ import annotations

import sys
from typing import override

from caddcalc.calculators.geometry.common import (
    ANGLE,
    AREA,
    DLMF_TRIANGLES,
    KAHAN_NEEDLE,
    LENGTH,
    MH31_LAW_OF_COSINES,
    MH31_RIGHT_TRIANGLES,
    MH31_THREE_SIDES,
    MH31_TRIANGLE,
    POCKET_TRIANGLES,
    check_scale,
    length,
    method,
)
from caddcalc.calculators.geometry.domain import DOMAIN
from caddcalc.core import N_, Calculator, Context, InputError, Output, Param
from caddcalc.core.expr import tan_is_undefined

FLAT_GAP = 4 * sys.float_info.epsilon
"""How far over 0 the gap ``a + b − c`` may be, relative to the longest side c, and the
triangle still be flat (ADR-0018, amendments)."""

TRIANGLE_NOTES = (
    "Each angle comes from Kahan's formula for the tangent of half of it, the law of "
    "cosines rearranged so a small or nearly straight angle keeps its digits. The "
    "Handbook's procedure for three known sides (p. 101) takes its second angle from the "
    "law of sines, which can't give an obtuse angle, so this calculator departs from it "
    "there on purpose.",
    "The area is Heron's formula in Kahan's arrangement, with the sides sorted longest "
    "first, so a needle-thin triangle keeps its digits.",
)


def _kahan_angle(opposite: str, larger: str, smaller: str, smaller_first: bool) -> str:
    """The angle opposite ``opposite``, by Kahan's half-angle formula.

    ``larger`` and ``smaller`` are the other two sides, so ordered; ``smaller_first`` is
    whether the smaller is at least as long as ``opposite``, which picks how μ is
    arranged. Each factor is then 0 or more for any triangle the flat check passes, so
    the square root needs no clamp, and arctan takes any value (Kahan's lecture notes).
    """
    c, a, b = opposite, larger, smaller
    mu = f"({c} - ({a} - {b}))" if smaller_first else f"({b} - ({a} - {c}))"
    return f"2*atand(sqrt((({a} - {b}) + {c})*{mu}/(({a} + ({b} + {c}))*(({a} - {c}) + {b}))))"


class Triangle(Calculator):
    """A triangle's perimeter, area, and angles, from its three sides."""

    id = "geometry.triangle"
    name = N_("Triangle (three sides)")
    domain = DOMAIN.id
    summary = N_("Perimeter, area, and the three angles of a triangle, from its three sides.")
    params = (
        length("side_a", "a", "Side a", "3 in", "One side; angle A is opposite it."),
        length("side_b", "b", "Side b", "4 in", "Another side; angle B is opposite it."),
        length("side_c", "c", "Side c", "5 in", "The third side; angle C is opposite it."),
    )
    outputs = (
        Output("perimeter", "P", "Perimeter", LENGTH),
        Output("area", "S", "Area", AREA),
        Output("angle_a", "A", "Angle A (opposite a)", ANGLE),
        Output("angle_b", "B", "Angle B (opposite b)", ANGLE),
        Output("angle_c", "C", "Angle C (opposite c)", ANGLE),
    )
    methods = (
        method(
            "three_sides",
            "Three sides",
            "S by Heron, and each angle by its half-angle tangent, both in Kahan's arrangement",
            MH31_TRIANGLE,
            MH31_LAW_OF_COSINES,
            MH31_THREE_SIDES,
            DLMF_TRIANGLES,
            KAHAN_NEEDLE,
            POCKET_TRIANGLES,
            notes=TRIANGLE_NOTES,
        ),
    )

    @override
    def compute(self, ctx: Context) -> None:
        check_scale(ctx)
        shortest, middle, longest = sorted((ctx["side_a"], ctx["side_b"], ctx["side_c"]))
        # Sides typed as decimals are doubles, so a flat triangle's gap can come out a few
        # units in the last place over 0, as 0.1 + 0.2 - 0.3 does; within FLAT_GAP of the
        # longest side it's flat (ADR-0018, amendments).
        if (shortest + middle) - longest <= FLAT_GAP * longest:
            raise InputError(
                "These sides make no triangle: the longest side must be shorter than the "
                "other two together."
            )
        ctx.calc("P", "a + b + c", label="Perimeter", dimension=LENGTH, output="perimeter")
        ctx.calc("x", "max(a, b, c)", label="Longest side", dimension=LENGTH)
        ctx.calc("y", "max(min(a, b), min(max(a, b), c))", label="Middle side", dimension=LENGTH)
        ctx.calc("z", "min(a, b, c)", label="Shortest side", dimension=LENGTH)
        ctx.calc(
            "S",
            "sqrt((x + (y + z))*(z - (x - y))*(z + (x - y))*(x + (y - z)))/4",
            label="Area",
            dimension=AREA,
            output="area",
        )
        sides = {"a": ctx["side_a"], "b": ctx["side_b"], "c": ctx["side_c"]}
        for symbol, opposite, others in (("A", "a", "bc"), ("B", "b", "ca"), ("C", "c", "ab")):
            larger, smaller = sorted(others, key=lambda s: sides[s], reverse=True)
            ctx.calc(
                symbol,
                _kahan_angle(opposite, larger, smaller, sides[smaller] >= sides[opposite]),
                label=f"Angle {symbol}",
                dimension=ANGLE,
                output=f"angle_{opposite}",
            )


RIGHT_TRIANGLE_NOTE = (
    "Legs a and b meet at the right angle; c is the hypotenuse, and A and B are the acute "
    "angles opposite a and b. Two angles alone aren't a method, since they fix no size."
)


RIGHT_TRIANGLE_SOURCES = (MH31_RIGHT_TRIANGLES, DLMF_TRIANGLES, POCKET_TRIANGLES)


class RightTriangle(Calculator):
    """A right triangle's sides, angles, area, and perimeter, from two of its parts."""

    id = "geometry.right_triangle"
    name = N_("Right triangle")
    domain = DOMAIN.id
    summary = N_(
        "Legs, hypotenuse, acute angles, area, and perimeter of a right triangle, from "
        "any two of its sides, or a side and an acute angle."
    )
    params = (
        length(
            "leg_a",
            "a",
            "Leg a",
            "3 in",
            "A side at the right angle, opposite angle A.",
            "legs",
            "leg_hypotenuse",
            "leg_angle",
        ),
        length("leg_b", "b", "Leg b", "4 in", "The other side at the right angle.", "legs"),
        length(
            "hypotenuse",
            "c",
            "Hypotenuse c",
            "5 in",
            "The side opposite the right angle, longer than either leg.",
            "leg_hypotenuse",
            "hypotenuse_angle",
        ),
        Param(
            "angle_a",
            "A",
            "Angle A (opposite a)",
            ANGLE,
            default="30 deg",
            minimum=0.0,
            min_inclusive=False,
            maximum=90.0,
            max_inclusive=False,
            help="An acute angle, greater than 0° and less than 90°, opposite leg a.",
            methods=("leg_angle", "hypotenuse_angle"),
        ),
    )
    outputs = (
        Output("leg_a", "a", "Leg a", LENGTH),
        Output("leg_b", "b", "Leg b", LENGTH),
        Output("hypotenuse", "c", "Hypotenuse c", LENGTH),
        Output("angle_a", "A", "Angle A (opposite a)", ANGLE),
        Output("angle_b", "B", "Angle B (opposite b)", ANGLE),
        Output("area", "S", "Area", AREA),
        Output("perimeter", "P", "Perimeter", LENGTH),
    )
    methods = (
        method(
            "legs",
            "Two legs",
            "c = √(a² + b²), A = atan2(a, b)",
            *RIGHT_TRIANGLE_SOURCES,
            notes=(RIGHT_TRIANGLE_NOTE,),
        ),
        method(
            "leg_hypotenuse",
            "A leg and the hypotenuse",
            "b = √((c − a)·(c + a)), A = atan2(a, b)",
            *RIGHT_TRIANGLE_SOURCES,
            notes=(
                RIGHT_TRIANGLE_NOTE,
                "The other leg is √(c² − a²) written as √((c − a)·(c + a)), the same value, "
                "which keeps its digits when the leg is nearly as long as the hypotenuse.",
            ),
        ),
        method(
            "leg_angle",
            "A leg and its opposite angle",
            "b = a/tan(A), c = a/sin(A)",
            *RIGHT_TRIANGLE_SOURCES,
            notes=(RIGHT_TRIANGLE_NOTE,),
        ),
        method(
            "hypotenuse_angle",
            "The hypotenuse and an angle",
            "a = c·sin(A), b = c·cos(A)",
            *RIGHT_TRIANGLE_SOURCES,
            notes=(RIGHT_TRIANGLE_NOTE,),
        ),
    )

    @override
    def compute(self, ctx: Context) -> None:
        check_scale(ctx)
        if ctx.method in ("leg_angle", "hypotenuse_angle") and tan_is_undefined(ctx["angle_a"]):
            # So near 90° that tan(A) is undefined, A is 90° to the arithmetic, in either
            # angle method, and refused as the range refuses 90° itself.
            angle = next(p for p in self.params if p.key == "angle_a")
            raise InputError(
                f"{angle.named} is so near 90° that it counts as 90° to the arithmetic: "
                "give an angle further below 90°"
            )
        if ctx.method == "legs":
            ctx.given("a", output="leg_a")
            ctx.given("b", output="leg_b")
            ctx.calc(
                "c", "sqrt(a**2 + b**2)", label="Hypotenuse", dimension=LENGTH, output="hypotenuse"
            )
        elif ctx.method == "leg_hypotenuse":
            # Within FLAT_GAP of each other they're equal, as "39 in" and "990.6 mm" are:
            # each typed value is rounded on its way in (ADR-0018, amendments).
            if ctx["hypotenuse"] - ctx["leg_a"] <= FLAT_GAP * ctx["hypotenuse"]:
                raise InputError("The hypotenuse (c) must be longer than the leg (a).")
            ctx.given("a", output="leg_a")
            ctx.given("c", output="hypotenuse")
            ctx.calc("b", "sqrt((c - a)*(c + a))", label="Leg b", dimension=LENGTH, output="leg_b")
        elif ctx.method == "leg_angle":
            ctx.given("a", output="leg_a")
            ctx.given("A", output="angle_a")
            ctx.calc("b", "a/tand(A)", label="Leg b", dimension=LENGTH, output="leg_b")
            ctx.calc("c", "a/sind(A)", label="Hypotenuse", dimension=LENGTH, output="hypotenuse")
        else:
            ctx.given("c", output="hypotenuse")
            ctx.given("A", output="angle_a")
            ctx.calc("a", "c*sind(A)", label="Leg a", dimension=LENGTH, output="leg_a")
            ctx.calc("b", "c*cosd(A)", label="Leg b", dimension=LENGTH, output="leg_b")
        if ctx.method in ("legs", "leg_hypotenuse"):
            ctx.calc("A", "atan2d(a, b)", label="Angle A", dimension=ANGLE, output="angle_a")
            ctx.calc("B", "atan2d(b, a)", label="Angle B", dimension=ANGLE, output="angle_b")
        else:
            ctx.calc("B", "90 - A", label="Angle B", dimension=ANGLE, output="angle_b")
        ctx.calc("S", "a*b/2", label="Area", dimension=AREA, output="area")
        ctx.calc("P", "a + b + c", label="Perimeter", dimension=LENGTH, output="perimeter")
