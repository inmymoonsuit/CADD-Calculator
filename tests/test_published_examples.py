"""Worked examples from published references, checked to the precision the source prints.

Cite edition, section, figure, and page in each docstring. Copy only the numbers needed for
the test; never copy text or tables (ADR-0008). These tests are what a method needs before
it can be promoted to Verification.VERIFIED (CONTRIBUTING.md).

MH31 = Machinery's Handbook, 31st ed., Industrial Press, 2020, "Bending Sheet Metal".
The same example is MH29's (29th ed.) Fig. 12, pp. 1347 and 1351, with the same numbers.
EDD5 = Madsen & Madsen, Engineering Drawing and Design, 5th ed., Cengage, 2012.
SP 811 = NIST Special Publication 811, 2008 Edition, Appendix B.8; it's public domain, and
only its factors are used here.
"""

from __future__ import annotations

import math

import pytest

from caddcalc.calculators import default_registry
from caddcalc.calculators.conversions import (
    AngleConverter,
    AreaConverter,
    DecimalToFraction,
    FractionToDecimal,
    LengthConverter,
    StressConverter,
)
from caddcalc.calculators.conversions.converters import SP811_B8
from caddcalc.calculators.sheet_metal import (
    BendAllowance,
    FormedSegmentFlatLength,
    TruncatedConeLayout,
)
from caddcalc.calculators.sheet_metal.common import EDD5_BEND_ALLOWANCE, MH31_FIG13
from caddcalc.core import Calculator, Dimension, Reference, Verification, parse_quantity
from caddcalc.core.formatting import (
    CopyForm,
    DisplayPrefs,
    ShownUnits,
    copy_output,
    format_output,
)
from tests.helpers import run_inches

UNITS = ShownUnits.generated()
"""The default set, for an output shown in its own fixed form."""


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
    segment's bend at either end.
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


def _full(calc: Calculator, typed: str, dimension: Dimension, pick: str) -> str:
    """A converter's value for ``typed``, picked in ``pick``, copied at full precision."""
    result = calc.run({"value": parse_quantity(typed, dimension)})
    units = ShownUnits(ShownUnits.generated().choices, {"value": pick}, {}, key="")
    return copy_output(
        calc.output("value"), result.outputs["value"], units, DisplayPrefs(), CopyForm.FULL
    )


def test_sp811_b8_inch_and_foot() -> None:
    """NIST SP 811 (2008), Appendix B.8, "Factors for Units Listed Alphabetically".

    The inch is 2.54 E-02 m and the foot 3.048 E-01 m, both printed as exact.
    """
    assert _full(LengthConverter(), "1 in", Dimension.LENGTH, "m") == "0.0254"
    assert _full(LengthConverter(), "1 ft", Dimension.LENGTH, "m") == "0.3048"
    assert _full(LengthConverter(), "0.0254 m", Dimension.LENGTH, "in") == "1"
    # Each converter its status names "for in and ft" runs both (S&R's PR #3 M2).
    assert _full(FractionToDecimal(), "1 in", Dimension.LENGTH, "m") == "0.0254"
    assert _full(FractionToDecimal(), "1 ft", Dimension.LENGTH, "m") == "0.3048"
    calc = DecimalToFraction()
    for typed, mm, shown in (("0.0254 m", 25.4, '1"'), ("0.3048 m", 304.8, '12"')):
        nearest = calc.run({"value": parse_quantity(typed, Dimension.LENGTH)})
        assert nearest.outputs["nearest"] == mm and nearest.outputs["error"] == 0.0
        value = nearest.outputs["nearest"]
        assert format_output(calc.output("nearest"), value, UNITS, DisplayPrefs()) == shown


def test_sp811_b8_square_inch_and_foot() -> None:
    """SP 811 Appendix B.8, the square inch and the square foot in square meters.

    They're 6.4516 E-04 m² and 9.290 304 E-02 m², both printed as exact.
    """
    assert _full(AreaConverter(), "1 in²", Dimension.AREA, "m²") == "0.00064516"
    assert _full(AreaConverter(), "1 ft²", Dimension.AREA, "m²") == "0.09290304"


def test_sp811_b8_psi_and_ksi() -> None:
    """SP 811 Appendix B.8, the pound-force and the kip per square inch in pascals.

    They're 6.894 757 E+03 Pa and 6.894 757 E+06 Pa, printed rounded to seven digits.
    """
    calc = StressConverter()
    assert float(_full(calc, "1 psi", Dimension.STRESS, "kPa")) == printed(6.894757, 6)
    assert float(_full(calc, "1 ksi", Dimension.STRESS, "MPa")) == printed(6.894757, 6)


def test_sp811_b8_degree() -> None:
    """SP 811 Appendix B.8: the degree is 1.745 329 E-02 rad, printed rounded."""
    assert float(_full(AngleConverter(), "1 deg", Dimension.ANGLE, "rad")) == printed(0.01745329, 8)


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
    ("conversions.length", "exact"): ("test_sp811_b8_inch_and_foot", SP811_B8, "for in and ft"),
    ("conversions.fraction_to_decimal", "exact"): (
        "test_sp811_b8_inch_and_foot",
        SP811_B8,
        "for in and ft",
    ),
    ("conversions.decimal_to_fraction", "exact"): (
        "test_sp811_b8_inch_and_foot",
        SP811_B8,
        "for in and ft",
    ),
    ("conversions.area", "exact"): (
        "test_sp811_b8_square_inch_and_foot",
        SP811_B8,
        "for in² and ft²",
    ),
    ("conversions.stress", "exact"): ("test_sp811_b8_psi_and_ksi", SP811_B8, "for psi and ksi"),
    ("conversions.angle", "exact"): ("test_sp811_b8_degree", SP811_B8, "for the degree"),
}
"""Each verified method, by calculator: the test of the published worked example that runs
through that calculator, the method's reference to its source, and the scope its status
writes, which is all the example covers (ADR-0010, amendments). No other method is
verified: the cones (KI-001, KI-007), the V-die rules (KI-003, KI-004), the fixed
K-factor's flat length of a segment, and the Geometry calculators have no such example."""

LOCATED = {
    MH31_FIG13: ("13", "Fig. 13,"),
    EDD5_BEND_ALLOWANCE: ("19.12", "Fig. 19.12,"),
    SP811_B8: ("B.8", "Appendix B.8,"),
}
"""Where each source's example is: in its citation, and as its method's note names it."""


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
    """The row's status carries the scope; its tooltip, the source (ADR-0010, amendments)."""
    registry = default_registry(load_plugins=False)
    statuses = {(c.id, m.key): m for c in registry for m in c.methods}
    for key, (_test, source, scope) in VERIFIED.items():
        method = statuses[key]
        assert method.scope == scope and len(scope) <= 20, key
        assert method.status.startswith(f"verified {scope}"), method.status
        cited, noted = LOCATED[source]  # where the example is, in the source and the note
        assert cited in source.detail and noted in method.verification_note, key
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
