"""Golden tests: the app must reproduce the original course spreadsheets exactly.

The expected values are the spreadsheets' cached results, read from the original files
(see docs/dev/legacy-workbooks.md). They pin the *legacy* methods. They do not show those
methods are correct; that is what Verification.VERIFIED and cited worked examples are for.
"""

from __future__ import annotations

import pytest

from caddcalc.calculators.sheet_metal import (
    BendAllowance,
    FormedSegmentFlatLength,
    TruncatedConeLayout,
    VDieOpening,
)
from tests.helpers import run_inches

# Excel stores IEEE doubles; inch→mm→inch round trips cost ~1e-15 relative.
approx = lambda x: pytest.approx(x, rel=1e-12, abs=1e-12)  # noqa: E731

# Lesson 2 - 90 Degree Bend Calculation: MATL=0.1046, RADIUS=0.156, FVD=1.12
LESSON_2 = {"thickness": 0.1046, "inside_radius": 0.156}


def test_lesson2_bend_allowance() -> None:
    out = run_inches(BendAllowance(), "course", **LESSON_2, bend_angle=90)
    assert out["bend_allowance"] == approx(0.311864)


def test_lesson2_flat_length_one_90_bend() -> None:
    out = run_inches(
        FormedSegmentFlatLength(),
        "course",
        **LESSON_2,
        formed_dimension=1.12,
        bend_angle_1=90,
        bend_angle_2=0,
    )
    assert out["flat_length"] == approx(1.015332)


def test_lesson2_flat_length_two_90_bends() -> None:
    out = run_inches(
        FormedSegmentFlatLength(),
        "course",
        **LESSON_2,
        formed_dimension=1.12,
        bend_angle_1=90,
        bend_angle_2=90,
    )
    assert out["flat_length"] == approx(0.910664)


def test_lesson2_female_die_opening() -> None:
    out = run_inches(VDieOpening(), "radius_ratio", inside_radius=0.156, radius_ratio=0.156)
    assert out["die_opening"] == approx(1.0)


# Rough Draft V1/V2, sheet "Non-90 Degree Bend Calculations". It had no saved example, so
# these values come from evaluating its cell formulas by hand (see legacy-workbooks.md).
@pytest.mark.parametrize(
    ("a1", "a2", "expected"),
    [
        # B10 = FVD - tan(A1/2)(R+T) + BA1/2,  BA = (0.64T + 1.57R)A/90
        (45, 0, 1.12 - 0.4142135623730950 * 0.2606 + 0.311864 * 45 / 90 / 2),
        # B14 = FVD - tan(A1/2)(R+T) - tan(A2/2)(R+T) + BA1/2 + BA2/2
        (
            60,
            30,
            1.12
            - (0.5773502691896257 + 0.2679491924311227) * 0.2606
            + 0.311864 * (60 + 30) / 90 / 2,
        ),
    ],
)
def test_rough_draft_non_90_flat_length(a1: float, a2: float, expected: float) -> None:
    out = run_inches(
        FormedSegmentFlatLength(),
        "course",
        **LESSON_2,
        formed_dimension=1.12,
        bend_angle_1=a1,
        bend_angle_2=a2,
    )
    assert out["flat_length"] == approx(expected)


# Lesson 4 - Cone Spread Sheet: Top Dia=6, Bot Dia=10, Cone H=5, MT=0.0747
def test_lesson4_cone() -> None:
    out = run_inches(
        TruncatedConeLayout(),
        "course",
        top_diameter=6,
        bottom_diameter=10,
        height=5,
        thickness=0.0747,
    )
    assert out["slant_height"] == approx(5.385164807134504)
    assert out["inside_radius"] == approx(8.077747210701755)
    assert out["outside_radius"] == approx(13.46291201783626)
    assert out["sweep_angle"] == approx(132.70189968062587)
