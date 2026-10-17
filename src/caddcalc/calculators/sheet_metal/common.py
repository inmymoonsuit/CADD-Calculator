"""Parameters, methods, and references shared by the sheet-metal calculators.

Conventions (see docs/user/glossary.md):

* **Bend angle (A)** is the angle the flange is bent *through*, measured from flat:
  0° means no bend and 90° is a square bend. It is *not* the included angle between flanges.
* **Formed dimensions** are to the *outside* of the material (outside mold line), as in
  the original course spreadsheets.
"""

from __future__ import annotations

from dataclasses import replace

from caddcalc.calculators.sheet_metal.domain import (
    INSIDE_RADIUS_SETTING,
    K_FACTOR_SETTING,
    THICKNESS_SETTING,
)
from caddcalc.core import Dimension, Method, Param, Reference, Verification

LEGACY_LESSON_2 = Reference(
    "Original CADD course spreadsheets, 'Lesson 2 - 90 Degree Bend Calculation'",
    "legacy spreadsheet; formulas transcribed in docs/dev/legacy-workbooks.md",
)
LEGACY_LESSON_4 = Reference(
    "Original CADD course spreadsheets, 'Lesson 4 - Cone Spread Sheet'",
    "legacy spreadsheet; formulas transcribed in docs/dev/legacy-workbooks.md",
)
LEGACY_ROUGH_DRAFT = Reference(
    "CADD Calculator Rough Draft V1/V2 (Excel/VBA prototype, 2024)",
    "sheet 'Non-90 Degree Bend Calculations'; see docs/dev/legacy-workbooks.md",
)
MH29_EQ33 = Reference(
    "Machinery's Handbook, 29th ed.",
    "Bending Sheet Metal: Allowances for Bending Sheet Metal, Eq. (33), printed p. 1347",
)
MH29_ANGLE_RULE = Reference(
    "Machinery's Handbook, 29th ed.",
    "Bending Sheet Metal: Angle of Bend Other Than 90 Degrees, printed p. 1351",
)
EDD5_BEND_ALLOWANCE = Reference(
    "Madsen & Madsen, Engineering Drawing and Design, 5th ed.",
    "Ch. 19, Calculating Bend Allowance, Figs. 19.11-19.12, printed pp. 782-785",
)
EDD5_CONE = Reference(
    "Madsen & Madsen, Engineering Drawing and Design, 5th ed.",
    "Ch. 23, Developing a Cone, step 3, printed p. 1051",
)

# Shared parameters (ADR-0013): each is its domain setting plus this calculator family's
# default and help, so key, dimension, and range always match the setting.
THICKNESS = replace(
    THICKNESS_SETTING,
    shared=True,
    default="0.1046 in",
    help="Sheet thickness. 0.1046 in is 12 ga (Manufacturers' Standard Gauge for steel sheet), "
    "the course example.",
)
INSIDE_RADIUS = replace(
    INSIDE_RADIUS_SETTING,
    shared=True,
    default="0.156 in",
    help="Radius on the inside surface of the bend.",
)
K_FACTOR = replace(
    K_FACTOR_SETTING,
    shared=True,
    default="0.4",
    help=(
        "Neutral-axis position as a fraction of thickness, measured from the inside surface. "
        "Cited starting values are about 0.35 to 0.45 (FAA, Machinery's Handbook), approaching "
        "0.5 for large R/T. The default, 0.4, is the instructional value in Engineering "
        "Drawing and Design (5th ed., Ch. 19). Use your shop's test-bend value for production."
    ),
    methods=("k_factor",),
)


def bend_angle(
    key: str = "bend_angle", symbol: str = "A", label: str = "Bend angle", default: str = "90 deg"
) -> Param:
    """Return a bend-angle parameter, measured from flat and below 180°.

    Args:
        key: The parameter key, e.g. ``"bend_angle_1"``.
        symbol: The formula symbol, e.g. ``"A1"``.
        label: The label shown to users.
        default: The default as text with units, e.g. ``"90 deg"``.
    """
    return Param(
        key,
        symbol,
        label,
        Dimension.ANGLE,
        default=default,
        minimum=0.0,
        maximum=180.0,
        max_inclusive=False,
        help="Angle bent through, measured from flat (0° = no bend, 90° = square bend).",
    )


K_FACTOR_METHOD = Method(
    "k_factor",
    "K-factor (neutral axis)",
    "BA = (π/180)·A·(R + K·T): arc length of the neutral axis.",
    Verification.UNVERIFIED,
    references=(EDD5_BEND_ALLOWANCE,),
    notes=("EDD5 uses K = 0.4 as an instructional value.",),
)
COURSE_METHOD = Method(
    "course",
    "Course formula (0.64T + 1.57R)",
    "BA = (0.64·T + 1.57·R)·A/90: the formula taught in the original coursework.",
    Verification.UNVERIFIED,
    legacy=True,
    references=(
        LEGACY_LESSON_2,
        LEGACY_ROUGH_DRAFT,
        MH29_EQ33,
        MH29_ANGLE_RULE,
    ),
    notes=(
        "Machinery's Handbook gives 0.64T + 1.57R for 90° bends in half-hard copper and brass, "
        "soft steel, and aluminum. It gives 0.55T for soft brass and copper, and 0.71T for "
        "bronze, hard copper, cold-rolled steel, and spring steel.",
        "For other angles the Handbook multiplies the 90° value by A/90, where A is the angle "
        "actually bent through.",
        "Equivalent to the K-factor method with K ≈ 0.64/1.57 ≈ 0.408 and π/2 rounded to 1.57.",
    ),
)

COURSE_BA = "(0.64*T + 1.57*R)*{A}/90"
K_FACTOR_BA = "pi/180*{A}*(R + K*T)"


def bend_allowance_formula(method_key: str, angle_symbol: str) -> str:
    """Return the bend-allowance expression for ``method_key``, using ``angle_symbol``."""
    template = COURSE_BA if method_key == "course" else K_FACTOR_BA
    return template.format(A=angle_symbol)
