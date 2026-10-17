"""Consistency and behavior checks for the sheet-metal calculators, beyond the golden values."""

from __future__ import annotations

import math

import pytest

from caddcalc.calculators.sheet_metal import (
    CALCULATORS,
    BendAllowance,
    FormedSegmentFlatLength,
    TruncatedConeLayout,
    VDieOpening,
)
from caddcalc.calculators.sheet_metal import DOMAIN as SHEET_METAL
from caddcalc.core import DomainValues, InputError, NoteKind, SourceKind
from caddcalc.core.units import from_base, to_base
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
    notes = [n for n in result.warnings if "minimum bend radius" in n.text]
    assert [n.kind for n in notes] == [NoteKind.LIMIT_EXCEEDED]


def test_flat_length_warns_when_segment_too_short() -> None:
    calc = FormedSegmentFlatLength()
    result = calc.run({"formed_dimension": 1.0, "bend_angle_2": 90.0}, method="course")
    assert result.outputs["flat_length"] < 0
    notes = [n for n in result.warnings if "too short" in n.text]
    assert [n.kind for n in notes] == [NoteKind.LIMIT_EXCEEDED]


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
    radius_warnings = [n for n in result.warnings if "minimum bend radius" in n.text]
    angle_warnings = [n for n in result.warnings if "past 90°" in n.text]
    assert len(radius_warnings) == 1
    assert [n.text[:2] for n in angle_warnings] == ["A1", "A2"]
    assert {n.kind for n in angle_warnings} == {NoteKind.WARNING}


# --- shared sheet-metal settings (ADR-0013, decision A) -----------------------------------


def sheet_metal_settings(**inches: float) -> DomainValues:
    """Sheet Metal settings with lengths given in inches (ratios as plain numbers)."""
    values = {
        key: to_base(value, "in") if key != "k_factor" else value for key, value in inches.items()
    }
    return SHEET_METAL.values(**values)


def test_sheet_metal_shares_thickness_inside_radius_and_k_factor() -> None:
    assert [s.key for s in SHEET_METAL.settings] == ["thickness", "inside_radius", "k_factor"]
    shared = {p.key for calc in CALCULATORS for p in calc.params if p.shared}
    assert shared == {"thickness", "inside_radius", "k_factor"}
    assert not any(p.shared for p in VDieOpening.params if p.key == "radius_ratio")


def test_every_parameter_with_a_setting_key_is_shared() -> None:
    keys = {s.key for s in SHEET_METAL.settings}
    for calc in CALCULATORS:
        for p in calc.params:
            if p.key in keys:
                assert p.shared, f"{calc.id}: {p.key} should inherit the Sheet Metal setting"


def test_the_cone_keeps_its_own_thickness_until_the_setting_is_set() -> None:
    cone = TruncatedConeLayout()
    plain = cone.run(method="course")
    assert from_base(plain.inputs["thickness"], "in") == pytest.approx(0.0747)
    assert plain.source_of("thickness").kind is SourceKind.DEFAULT

    shared = cone.run(method="course", settings=sheet_metal_settings(thickness=0.1046))
    assert shared.source_of("thickness").kind is SourceKind.DOMAIN
    # ADR-0013 decision D: Lesson 4's cone at Lesson 2's thickness.
    assert shared.outputs["sweep_angle"] == pytest.approx(132.30, abs=0.005)


def test_v_die_methods_read_only_their_own_shared_setting() -> None:
    settings = sheet_metal_settings(thickness=0.25, inside_radius=0.3)
    eight_t = VDieOpening().run(method="eight_t", settings=settings)
    assert from_base(eight_t.outputs["die_opening"], "in") == pytest.approx(2.0)
    assert "inside_radius" not in eight_t.inputs

    ratio = VDieOpening().run(method="radius_ratio", settings=settings)
    assert from_base(ratio.outputs["die_opening"], "in") == pytest.approx(0.3 / 0.156)
    assert "thickness" not in ratio.inputs
    assert ratio.source_of("radius_ratio").kind is SourceKind.DEFAULT


def test_only_k_factor_methods_read_the_shared_k_factor() -> None:
    settings = sheet_metal_settings(k_factor=0.44)
    course = BendAllowance().run(method="course", settings=settings)
    assert "k_factor" not in course.inputs
    k = BendAllowance().run(method="k_factor", settings=settings)
    assert k.inputs["k_factor"] == pytest.approx(0.44)
    assert k.source_of("k_factor").kind is SourceKind.DOMAIN


def test_an_entered_value_still_beats_the_shared_setting() -> None:
    settings = sheet_metal_settings(thickness=0.25)
    out = FormedSegmentFlatLength().run(
        {"thickness": to_base(0.1046, "in")}, method="course", settings=settings
    )
    assert out.source_of("thickness").kind is SourceKind.EXPLICIT
    assert from_base(out.outputs["flat_length"], "in") == pytest.approx(1.015332, rel=1e-9)
