"""Consistency and behavior checks for the sheet-metal calculators, beyond the golden values."""

from __future__ import annotations

import math

import pytest

from caddcalc.calculators.sheet_metal import (
    BendAllowance,
    FormedSegmentFlatLength,
    TruncatedConeLayout,
    VDieOpening,
)
from caddcalc.core import InputError
from tests.helpers import run_inches


def test_course_formula_equals_k_factor_with_implied_k() -> None:
    """0.64T + 1.57R is the K-factor formula with K = 0.64/1.57 and π/2 rounded to 1.57."""
    t, r = 0.1046, 0.156
    course = run_inches(BendAllowance(), "course", thickness=t, inside_radius=r, bend_angle=90)
    k = run_inches(
        BendAllowance(),
        "k_factor",
        thickness=t,
        inside_radius=r,
        bend_angle=90,
        k_factor=0.64 / 1.57,
    )
    assert course["bend_allowance"] == pytest.approx(k["bend_allowance"] * 1.57 / (math.pi / 2))


@pytest.mark.parametrize("method", ["course", "k_factor"])
@pytest.mark.parametrize("angle", [15, 45, 90, 120, 170])
def test_bend_deduction_identity(method: str, angle: float) -> None:
    out = run_inches(BendAllowance(), method, bend_angle=angle)
    assert out["bend_deduction"] == pytest.approx(
        2 * out["outside_setback"] - out["bend_allowance"]
    )


@pytest.mark.parametrize("method", ["course", "k_factor"])
def test_bend_allowance_scales_linearly_with_angle(method: str) -> None:
    ba45 = run_inches(BendAllowance(), method, bend_angle=45)["bend_allowance"]
    ba90 = run_inches(BendAllowance(), method, bend_angle=90)["bend_allowance"]
    assert ba90 == pytest.approx(2 * ba45)


def test_zero_angle_end_contributes_nothing() -> None:
    out = run_inches(
        FormedSegmentFlatLength(), "k_factor", formed_dimension=2.0, bend_angle_1=0, bend_angle_2=0
    )
    assert out["flat_length"] == pytest.approx(2.0)


def test_warns_when_radius_below_thickness() -> None:
    calc = BendAllowance()
    result = calc.run({"thickness": 3.0, "inside_radius": 1.0}, method="k_factor")
    assert any("minimum bend radius" in w for w in result.warnings)


def test_flat_length_warns_when_segment_too_short() -> None:
    calc = FormedSegmentFlatLength()
    result = calc.run({"formed_dimension": 1.0, "bend_angle_2": 90.0}, method="course")
    assert result.outputs["flat_length"] < 0
    assert any("too short" in w for w in result.warnings)


def test_die_opening_eight_t_uses_only_thickness() -> None:
    out = run_inches(VDieOpening(), "eight_t", thickness=0.125)
    assert out["die_opening"] == pytest.approx(1.0)
    assert [p.key for p in VDieOpening.params_for("eight_t")] == ["thickness"]


def test_cone_mean_diameter_angle_is_independent_of_thickness() -> None:
    """With consistent mean diameters, the sweep angle is 180·(Db − Dt)/CH (KI-001)."""
    out = run_inches(
        TruncatedConeLayout(),
        "mean_diameter",
        top_diameter=6,
        bottom_diameter=10,
        height=5,
        thickness=0.0747,
    )
    assert out["sweep_angle"] == pytest.approx(180 * 4 / math.sqrt(29))
    assert out["outside_radius"] - out["inside_radius"] == pytest.approx(out["slant_height"])


def test_cone_full_cone_has_zero_inside_radius() -> None:
    for method in ("course", "mean_diameter"):
        out = run_inches(
            TruncatedConeLayout(),
            method,
            top_diameter=0,
            bottom_diameter=10,
            height=5,
            thickness=0.0747,
        )
        assert out["inside_radius"] == 0


def test_cone_rejects_inverted_diameters() -> None:
    with pytest.raises(InputError, match="larger than top"):
        run_inches(TruncatedConeLayout(), top_diameter=10, bottom_diameter=6, height=5)


def test_each_warning_appears_once_with_two_steep_bends() -> None:
    result = FormedSegmentFlatLength().run(
        {"thickness": 3.0, "inside_radius": 1.0, "bend_angle_1": 120.0, "bend_angle_2": 120.0},
        method="k_factor",
    )
    radius_warnings = [w for w in result.warnings if "minimum bend radius" in w]
    angle_warnings = [w for w in result.warnings if "past 90°" in w]
    assert len(radius_warnings) == 1
    assert [w[:2] for w in angle_warnings] == ["A1", "A2"]
