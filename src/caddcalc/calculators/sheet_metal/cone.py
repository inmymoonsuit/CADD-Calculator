"""Flat-pattern (development) layout for a truncated right circular cone."""

from __future__ import annotations

from dataclasses import replace
from typing import override

from caddcalc.calculators.sheet_metal.common import EDD5_CONE, LEGACY_LESSON_4, THICKNESS
from caddcalc.calculators.sheet_metal.domain import DOMAIN
from caddcalc.core import (
    N_,
    Calculator,
    Context,
    Dimension,
    InputError,
    Method,
    Output,
    Param,
    Verification,
)

LENGTH = Dimension.LENGTH


class TruncatedConeLayout(Calculator):
    """Flat pattern (an annular sector) of a truncated right circular cone."""

    id = "sheet_metal.truncated_cone_layout"
    name = N_("Truncated cone flat pattern")
    domain = DOMAIN.id
    summary = N_(
        "Inside radius, outside radius, and sweep angle of the flat pattern for a cone frustum."
    )
    params = (
        Param(
            "top_diameter",
            "Dt",
            "Top diameter",
            LENGTH,
            default="6 in",
            minimum=0.0,
            help="Diameter of the small end. Use 0 for a full (pointed) cone.",
        ),
        Param(
            "bottom_diameter",
            "Db",
            "Bottom diameter",
            LENGTH,
            default="10 in",
            minimum=0.0,
            min_inclusive=False,
            help="Diameter of the large end.",
        ),
        Param(
            "height",
            "H",
            "Cone height",
            LENGTH,
            default="5 in",
            minimum=0.0,
            min_inclusive=False,
            help="Vertical height between the two ends.",
        ),
        replace(
            THICKNESS,
            default="0.0747 in",
            help=(
                "Sheet thickness. 0.0747 in is 14 ga (Manufacturers' Standard Gauge for "
                "steel sheet), the course example."
            ),
        ),
    )
    outputs = (
        Output("slant_height", "CH", "Slant height (cone hypotenuse)", LENGTH),
        Output("inside_radius", "FPIR", "Flat pattern inside radius", LENGTH),
        Output("outside_radius", "FPOR", "Flat pattern outside radius", LENGTH),
        Output("sweep_angle", "FPA", "Flat pattern angle", Dimension.ANGLE),
    )
    methods = (
        Method(
            "course",
            "Course spreadsheet",
            "Radii from the given diameters, and the angle from the bottom diameter less one "
            "thickness.",
            Verification.UNVERIFIED,
            legacy=True,
            references=(LEGACY_LESSON_4,),
            notes=(
                "The radii use the diameters as given, while the angle uses (Db − T). For the "
                "course example this gives {course} against {mean} for a mean-diameter "
                "layout. See KI-001.",
            ),
            quantities={"course": (132.70, Dimension.ANGLE), "mean": (133.70, Dimension.ANGLE)},
        ),
        Method(
            "mean_diameter",
            "Mean diameter (consistent)",
            "Treats the diameters as outside diameters and develops the mid-thickness surface "
            "(D − T) throughout.",
            Verification.UNVERIFIED,
            references=(EDD5_CONE,),
            notes=(
                "Ignores the small correction for wall slope: the horizontal wall thickness is "
                "T/cos(half-angle), not T. See KI-007.",
            ),
        ),
    )

    @override
    def compute(self, ctx: Context) -> None:
        if ctx["bottom_diameter"] <= ctx["top_diameter"]:
            raise InputError(
                "Bottom diameter must be larger than top diameter. Swap them, or use a "
                "cylinder layout if they are equal."
            )
        if ctx.method == "course":
            _require_bottom_above_thickness(ctx)
            ctx.calc(
                "CH",
                "sqrt(((Db - Dt)/2)**2 + H**2)",
                label="Slant height",
                dimension=LENGTH,
                output="slant_height",
            )
            ctx.calc(
                "FPIR",
                "CH*(Dt/2)/((Db - Dt)/2)",
                label="Flat pattern inside radius",
                dimension=LENGTH,
                output="inside_radius",
            )
            ctx.calc(
                "FPOR",
                "FPIR + CH",
                label="Flat pattern outside radius",
                dimension=LENGTH,
                output="outside_radius",
            )
            ctx.calc(
                "FPA",
                "180*(Db - T)/FPOR",
                label="Flat pattern angle",
                dimension=Dimension.ANGLE,
                output="sweep_angle",
            )
            return

        if ctx["top_diameter"] and ctx["top_diameter"] <= ctx["thickness"]:
            raise InputError("Top diameter must be larger than the thickness for this method.")
        _require_bottom_above_thickness(ctx)
        ctx.calc("Dtm", "max(Dt - T, 0)", label="Mean top diameter", dimension=LENGTH)
        ctx.calc("Dbm", "Db - T", label="Mean bottom diameter", dimension=LENGTH)
        ctx.calc(
            "CH",
            "sqrt(((Dbm - Dtm)/2)**2 + H**2)",
            label="Slant height",
            dimension=LENGTH,
            output="slant_height",
        )
        ctx.calc(
            "FPIR",
            "CH*(Dtm/2)/((Dbm - Dtm)/2)",
            label="Flat pattern inside radius",
            dimension=LENGTH,
            output="inside_radius",
        )
        ctx.calc(
            "FPOR",
            "FPIR + CH",
            label="Flat pattern outside radius",
            dimension=LENGTH,
            output="outside_radius",
        )
        ctx.calc(
            "FPA",
            "180*Dbm/FPOR",
            label="Flat pattern angle",
            dimension=Dimension.ANGLE,
            output="sweep_angle",
        )


def _require_bottom_above_thickness(ctx: Context) -> None:
    """Refuse a bottom diameter no larger than the thickness, in either method.

    Both sweep angles take ``Db - T``, which would then be zero or negative: no cone to lay
    out, only a zero or negative angle, or a division by zero. Refusing it is an input
    guard, not a change to a formula, and the course method takes it by the maintainer's
    approval (ADR-0010, amendments).
    """
    if ctx["bottom_diameter"] <= ctx["thickness"]:
        raise InputError("Bottom diameter must be larger than the thickness for this method.")
