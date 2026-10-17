"""Bend allowance, bend deduction, flat length of formed segments, and V-die opening."""

from __future__ import annotations

from dataclasses import replace
from typing import override

from caddcalc.calculators.sheet_metal.checks import BendCheck
from caddcalc.calculators.sheet_metal.common import (
    COURSE_METHOD,
    INSIDE_RADIUS,
    K_FACTOR,
    K_FACTOR_METHOD,
    LEGACY_LESSON_2,
    LEGACY_ROUGH_DRAFT,
    THICKNESS,
    bend_allowance_formula,
    bend_angle,
)
from caddcalc.calculators.sheet_metal.domain import DOMAIN, GAUGES, MATERIALS
from caddcalc.core import (
    Calculator,
    Context,
    Dimension,
    Method,
    NoteKind,
    Output,
    Param,
    Verification,
)

LENGTH = Dimension.LENGTH


def _check_bend(ctx: Context, *angle_keys: str) -> None:
    """Add engineering notes once per run, checking each named bend angle.

    The inside radius is checked after compute, against the material (``BendCheck``).
    """
    for key in angle_keys:
        if ctx[key] > 90:
            a = next(p.symbol for p in ctx.calculator.params if p.key == key)
            ctx.warn(
                f"{a} is past 90°. Its outside setback, tan({a}/2)·(R + T), is measured to the "
                "virtual sharp. Some drawings dimension these bends to the outside-arc tangent "
                "instead (KI-013), so confirm how the part is dimensioned.",
                subjects=(key,),
            )
    if ctx.method == "k_factor" and ctx["k_factor"] > 0.5:
        ctx.warn(
            "A K-factor above 0.5 puts the neutral axis past mid-thickness, which is unusual.",
            subjects=("k_factor",),
        )


class BendAllowance(Calculator):
    """Bend allowance, outside setback, and bend deduction for a single bend."""

    id = "sheet_metal.bend_allowance"
    name = "Bend allowance & deduction"
    domain = DOMAIN.id
    summary = (
        "Bend allowance (neutral-axis arc length), outside setback, and bend deduction "
        "for a single bend."
    )
    params = (THICKNESS, INSIDE_RADIUS, bend_angle(), K_FACTOR)
    checks = (BendCheck(MATERIALS, GAUGES, ("bend_angle",)),)
    outputs = (
        Output(
            "bend_allowance",
            "BA",
            "Bend allowance",
            LENGTH,
            "Length of the neutral axis through the bend.",
        ),
        Output(
            "outside_setback",
            "OSSB",
            "Outside setback",
            LENGTH,
            "From the tangent point to the outside mold line (virtual sharp).",
        ),
        Output(
            "bend_deduction",
            "BD",
            "Bend deduction",
            LENGTH,
            "Subtract from the sum of outside flange lengths to get the flat length.",
        ),
    )
    methods = (COURSE_METHOD, K_FACTOR_METHOD)

    @override
    def compute(self, ctx: Context) -> None:
        ctx.calc(
            "BA",
            bend_allowance_formula(ctx.method, "A"),
            label="Bend allowance",
            dimension=LENGTH,
            output="bend_allowance",
        )
        ctx.calc(
            "OSSB",
            "tand(A/2)*(R + T)",
            label="Outside setback",
            dimension=LENGTH,
            output="outside_setback",
        )
        ctx.calc(
            "BD", "2*OSSB - BA", label="Bend deduction", dimension=LENGTH, output="bend_deduction"
        )
        _check_bend(ctx, "bend_angle")


class FormedSegmentFlatLength(Calculator):
    """Generalizes the course "FPD with one / two 90° (or non-90°) bends" spreadsheets.

    A formed segment measured to the outside (FVD) loses one outside setback for each bent
    end and gains half that bend's allowance. Set A2 to 0° for a segment bent at one end only.
    """

    id = "sheet_metal.segment_flat_length"
    name = "Flat length of a formed segment"
    domain = DOMAIN.id
    summary = (
        "Flat-pattern length of one segment, dimensioned to the outside, with a bend at "
        "one or both ends."
    )
    params = (
        THICKNESS,
        INSIDE_RADIUS,
        Param(
            "formed_dimension",
            "FVD",
            "Formed view dimension",
            LENGTH,
            default="1.12 in",
            minimum=0.0,
            min_inclusive=False,
            help="Outside dimension of the segment as drawn in the formed view.",
        ),
        bend_angle("bend_angle_1", "A1", "Bend angle at end 1", "90 deg"),
        bend_angle("bend_angle_2", "A2", "Bend angle at end 2", "0 deg"),
        K_FACTOR,
    )
    checks = (BendCheck(MATERIALS, GAUGES, ("bend_angle_1", "bend_angle_2")),)
    outputs = (
        Output(
            "flat_length",
            "FPD",
            "Flat pattern dimension",
            LENGTH,
            "This segment's length in the flat pattern.",
        ),
        Output("bend_allowance_1", "BA1", "Bend allowance, end 1", LENGTH),
        Output("bend_allowance_2", "BA2", "Bend allowance, end 2", LENGTH),
    )
    methods = (COURSE_METHOD, K_FACTOR_METHOD)

    @override
    def compute(self, ctx: Context) -> None:
        ctx.calc(
            "BA1",
            bend_allowance_formula(ctx.method, "A1"),
            label="Bend allowance, end 1",
            dimension=LENGTH,
            output="bend_allowance_1",
        )
        ctx.calc(
            "BA2",
            bend_allowance_formula(ctx.method, "A2"),
            label="Bend allowance, end 2",
            dimension=LENGTH,
            output="bend_allowance_2",
        )
        ctx.calc("OSSB1", "tand(A1/2)*(R + T)", label="Outside setback, end 1", dimension=LENGTH)
        ctx.calc("OSSB2", "tand(A2/2)*(R + T)", label="Outside setback, end 2", dimension=LENGTH)
        fpd = ctx.calc(
            "FPD",
            "FVD - OSSB1 - OSSB2 + BA1/2 + BA2/2",
            label="Flat pattern dimension",
            dimension=LENGTH,
            output="flat_length",
        )
        _check_bend(ctx, "bend_angle_1", "bend_angle_2")
        if fpd <= 0:
            ctx.note(
                "The flat length is zero or negative: the segment is too short for these bends.",
                NoteKind.INFEASIBLE,
                subjects=("flat_length",),
            )


class VDieOpening(Calculator):
    """V-die opening for air bending, from the inside radius or the thickness."""

    id = "sheet_metal.v_die_opening"
    name = "V-die opening (air bending)"
    domain = DOMAIN.id
    summary = "Suggested female (V) die opening for air bending on a press brake."
    params = (
        replace(INSIDE_RADIUS, methods=("radius_ratio",)),
        Param(
            "radius_ratio",
            "P",
            "Radius-to-die-opening ratio",
            Dimension.RATIO,
            default="0.156",
            minimum=0.0,
            min_inclusive=False,
            maximum=1.0,
            help=(
                "In air bending the inside radius forms at roughly this fraction of the "
                "die opening. The course used 0.156 (mild steel). It varies by material."
            ),
            methods=("radius_ratio",),
        ),
        replace(THICKNESS, methods=("eight_t",)),
    )
    outputs = (Output("die_opening", "V", "Die opening", LENGTH),)
    methods = (
        Method(
            "radius_ratio",
            "Inside-radius percentage rule",
            "V = R / P: the die opening that naturally produces inside radius R.",
            Verification.UNVERIFIED,
            legacy=True,
            references=(LEGACY_LESSON_2, LEGACY_ROUGH_DRAFT),
            notes=("The course hard-coded P = 0.156. Here P is an input (KI-003).",),
        ),
        Method(
            "eight_t",
            "8 × thickness rule of thumb",
            "V = 8·T: a common starting point for mild steel.",
            Verification.UNVERIFIED,
            notes=("Citation needed (KI-004).",),
        ),
    )

    @override
    def compute(self, ctx: Context) -> None:
        if ctx.method == "radius_ratio":
            ctx.calc("V", "R/P", label="Die opening", dimension=LENGTH, output="die_opening")
        else:
            ctx.calc("V", "8*T", label="Die opening", dimension=LENGTH, output="die_opening")
