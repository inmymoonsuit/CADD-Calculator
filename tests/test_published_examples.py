"""Worked examples from published references, checked to the precision the source prints.

Cite edition, section, figure, and page in each docstring. Copy only the numbers needed for
the test; never copy text or tables (ADR-0008). These tests are what a method needs before
it can be promoted to Verification.VERIFIED (CONTRIBUTING.md).

MH31 = Machinery's Handbook, 31st ed., Industrial Press, 2020, "Bending Sheet Metal".
The same example is MH29's (29th ed.) Fig. 12, pp. 1347 and 1351, with the same numbers.
EDD5 = Madsen & Madsen, Engineering Drawing and Design, 5th ed., Cengage, 2012.
"""

from __future__ import annotations

import math

import pytest

from caddcalc.calculators import default_registry
from caddcalc.calculators.sheet_metal import (
    BendAllowance,
    FormedSegmentFlatLength,
    TruncatedConeLayout,
)
from caddcalc.calculators.sheet_metal.common import EDD5_BEND_ALLOWANCE, MH31_FIG13
from caddcalc.core import Reference, Verification
from tests.helpers import run_inches


def printed(value: float, decimals: int = 3) -> object:
    """Match a value printed to ``decimals`` places (half a unit in the last place, plus eps).

    Keep the inclusive half-unit tolerance. Some exact values sit right on the rounding
    boundary: MH31 prints 1.338 for 1.3375 and 0.707 for 0.7075.
    """
    return pytest.approx(value, abs=0.5 * 10**-decimals + 1e-9)


def test_mh31_fig13_soft_steel_part() -> None:
    """MH31 "Example, Showing Application of Formulas 32–34", Fig. 13, printed p. 1421.

    Soft steel (Eq. 33), T = 0.125. Bends: 180° at R = 0.375 and 60° at R = 0.625, with
    straight lengths totaling 3.5. Scaling by bend angle / 90 is MH31 "Angle of Bend Other
    Than 90 Degrees", p. 1421. The calculator rejects A = 180° because the outside setback
    is undefined for a hem (KI-014), so the 180° bend applies that rule to the 90° value.
    """
    calc = BendAllowance()
    ba_90 = run_inches(calc, "course", thickness=0.125, inside_radius=0.375, bend_angle=90)
    ba_180 = ba_90["bend_allowance"] * 180 / 90
    ba_60 = run_inches(calc, "course", thickness=0.125, inside_radius=0.625, bend_angle=60)
    assert ba_180 == printed(1.338)
    assert ba_60["bend_allowance"] == printed(0.707)
    assert 3.5 + ba_180 + ba_60["bend_allowance"] == printed(5.545)


def test_edd5_fig19_12_single_bend_k_factor() -> None:
    """EDD5 Ch. 19 "Example Bend Allowance Calculation", Fig. 19.12, printed p. 785.

    B = 12.250, A = 4.875, R = C = 0.125, K = 0.4, one 90° bend, dimensioned to the outside.
    The book rounds π to 3.14 (Z = .275, flat = 16.900). With exact π, flat = 16.899889.
    Each leg is bent at its first end, then at its second, so "verified at 90°" covers a
    segment's bend at either end (S&R's note).
    """
    common = {"thickness": 0.125, "inside_radius": 0.125, "k_factor": 0.4}
    z = run_inches(BendAllowance(), "k_factor", **common, bend_angle=90)["bend_allowance"]
    assert z == printed(0.275)

    seg = FormedSegmentFlatLength()
    leg_b = run_inches(seg, "k_factor", **common, formed_dimension=12.250, bend_angle_1=90)
    leg_a = run_inches(seg, "k_factor", **common, formed_dimension=4.875, bend_angle_1=90)
    flat = leg_b["flat_length"] + leg_a["flat_length"]
    assert flat == printed(16.900)
    assert flat == pytest.approx(16.625 + 0.0875 * math.pi, rel=1e-12)

    end_2 = {**common, "bend_angle_1": 0, "bend_angle_2": 90}
    leg_a_2 = run_inches(seg, "k_factor", **end_2, formed_dimension=4.875)["flat_length"]
    leg_b_2 = run_inches(seg, "k_factor", **end_2, formed_dimension=12.250)["flat_length"]
    assert leg_a_2 == printed(4.762445, 6)
    assert leg_b_2 + leg_a_2 == printed(16.899889, 6)
    assert leg_b_2 + leg_a_2 == printed(16.900)


def test_edd5_cone_sector_rule_on_one_surface() -> None:
    """EDD5 Ch. 23 "Developing a Cone", step 3, p. 1051: angle = (base radius / slant)·360.

    Developed on a single surface, the sweep angle of the course frustum is
    360·((Db − Dt)/2)/CH whatever thickness offset is used. The mean-diameter method matches.
    The course method differs; see KI-001.
    """
    out = run_inches(
        TruncatedConeLayout(),
        "mean_diameter",
        top_diameter=6,
        bottom_diameter=10,
        height=5,
        thickness=0.0747,
    )
    slant = math.hypot(2, 5)
    assert out["sweep_angle"] == pytest.approx(360 * 2 / slant, rel=1e-12)
    assert out["sweep_angle"] == printed(133.7006, 4)
    assert out["inside_radius"] == printed(7.977179, 6)
    assert out["outside_radius"] == printed(13.362344, 6)


VERIFIED: dict[tuple[str, str], tuple[str, Reference, str]] = {
    ("sheet_metal.bend_allowance", "course"): (
        "test_mh31_fig13_soft_steel_part",
        MH31_FIG13,
        "for BA",
    ),
    ("sheet_metal.bend_allowance", "k_factor"): (
        "test_edd5_fig19_12_single_bend_k_factor",
        EDD5_BEND_ALLOWANCE,
        "for BA at 90°",
    ),
    ("sheet_metal.segment_flat_length", "k_factor"): (
        "test_edd5_fig19_12_single_bend_k_factor",
        EDD5_BEND_ALLOWANCE,
        "at 90°",
    ),
}
"""Each verified method, by calculator: the test of the published worked example that runs
through that calculator, the method's reference to its source, and the scope its status
writes, which is all the example covers (ADR-0010, amendments). No other method is
verified: the cones (KI-001, KI-007), the V-die rules (KI-003, KI-004), and the fixed
K-factor's flat length of a segment have no such example."""


def test_only_methods_a_published_example_runs_through_are_verified() -> None:
    """A method is verified in a calculator only with its worked example here (CONTRIBUTING)."""
    registry = default_registry(load_plugins=False)
    verified = {
        (calc.id, method.key): method
        for calc in registry
        for method in calc.methods
        if method.verification is Verification.VERIFIED
    }
    assert verified.keys() == VERIFIED.keys()
    for key, (test, source, _scope) in VERIFIED.items():
        assert callable(globals()[test]), test
        assert source in verified[key].references, key


def test_each_status_says_what_its_example_covers() -> None:
    """UI/UX's promotion review: the row's status carries the scope; its tooltip, the source."""
    registry = default_registry(load_plugins=False)
    statuses = {(c.id, m.key): m for c in registry for m in c.methods}
    for key, (_test, source, scope) in VERIFIED.items():
        method = statuses[key]
        assert method.scope == scope and len(scope) <= 20, key
        assert method.status.startswith(f"verified {scope}"), method.status
        figure = "13" if source is MH31_FIG13 else "19.12"  # the example's figure, cited
        assert figure in source.detail and f"Fig. {figure}," in method.verification_note, key
    assert statuses["sheet_metal.bend_allowance", "course"].status == (
        "verified for BA · reproduces legacy"
    )
    assert statuses["sheet_metal.bend_allowance", "k_factor"].status == "verified for BA at 90°"
    assert statuses["sheet_metal.segment_flat_length", "k_factor"].status == "verified at 90°"
    segment_course = statuses["sheet_metal.segment_flat_length", "course"]
    assert segment_course.status == "unverified · reproduces legacy"
    assert segment_course.verification_note.startswith("Not verified in this calculator")
    for key in ("sheet_metal.bend_allowance", "sheet_metal.segment_flat_length"):
        assert statuses[key, "course"].label == "Fixed K-factor (≈ 0.41)"
