"""The Geometry family: six plane figures, each with every property at once (ADR-0018 §2).

The expected values are exact by geometry: a 3-4-5 triangle's area is 6, a hexagon of
side 1 is √3 across flats, and so on. Lengths are in inches, as ``run_inches`` gives them.
"""

from __future__ import annotations

import itertools
import math
from decimal import Decimal, getcontext
from typing import override

import pytest

from caddcalc.calculators import BUILTIN_DOMAINS, default_registry
from caddcalc.calculators.geometry import (
    CALCULATORS,
    ArcSector,
    Circle,
    Rectangle,
    RegularPolygon,
    RightTriangle,
    Triangle,
)
from caddcalc.calculators.geometry.common import (
    DLMF_TRIANGLES,
    KAHAN_NEEDLE,
    MH31,
    MH31_LAW_OF_COSINES,
    MH31_THREE_SIDES,
    POCKET_PLANE_FIGURES,
    POCKET_TRIANGLES,
)
from caddcalc.core import (
    Calculator,
    Context,
    Dimension,
    InputError,
    Method,
    OutOfRangeError,
    Output,
    Param,
    SpecError,
    Verification,
)
from caddcalc.core.formatting import DisplayPrefs, describe_note
from tests.helpers import run_inches

IN2 = 25.4**2
"""A square inch in square millimetres: ``run_inches`` gives areas in mm²."""


def test_geometry_is_listed_first_and_has_six_calculators() -> None:
    assert BUILTIN_DOMAINS[0].id == "geometry"
    registry = default_registry(load_plugins=False)
    ids = {c.id for c in registry if c.domain == "geometry"}
    assert ids == {
        "geometry.circle",
        "geometry.rectangle",
        "geometry.triangle",
        "geometry.right_triangle",
        "geometry.regular_polygon",
        "geometry.arc_sector",
    }
    assert registry.domain("geometry").settings == (), "no shared settings in this phase"


@pytest.mark.parametrize(
    ("method", "given"), [("diameter", {"diameter": 2}), ("radius", {"radius": 1})]
)
def test_a_circle_from_its_diameter_or_its_radius(method: str, given: dict[str, float]) -> None:
    out = run_inches(Circle(), method, **given)
    assert (out["diameter"], out["radius"]) == (pytest.approx(2), pytest.approx(1))
    assert out["circumference"] == pytest.approx(2 * math.pi, rel=1e-15)
    assert out["area"] / IN2 == pytest.approx(math.pi, rel=1e-15)


def test_an_input_given_as_an_output_adds_no_work() -> None:
    result = Circle().run(method="diameter")
    assert result.outputs["diameter"] == result.inputs["diameter"]
    assert [s.symbol for s in result.steps] == ["r", "C", "S"]


def test_a_rectangle_has_its_perimeter_area_and_diagonal() -> None:
    out = run_inches(Rectangle(), length=4, width=3)
    assert out["perimeter"] == pytest.approx(14)
    assert out["area"] / IN2 == pytest.approx(12)
    assert out["diagonal"] == pytest.approx(5, rel=1e-15)


def test_a_3_4_5_triangle_has_area_6_and_its_angles() -> None:
    out = run_inches(Triangle(), side_a=3, side_b=4, side_c=5)
    assert out["perimeter"] == pytest.approx(12)
    assert out["area"] / IN2 == pytest.approx(6, rel=1e-14)
    assert out["angle_a"] == pytest.approx(36.8699, abs=5e-5)
    assert out["angle_b"] == pytest.approx(53.1301, abs=5e-5)
    assert out["angle_c"] == pytest.approx(90, abs=1e-12)
    assert out["angle_a"] + out["angle_b"] + out["angle_c"] == pytest.approx(180, abs=1e-12)


def test_an_obtuse_angle_comes_from_the_law_of_cosines_not_the_law_of_sines() -> None:
    """Sides 3, 7, 5: B = 120°. The Handbook's law-of-sines step would give 60°."""
    out = run_inches(Triangle(), side_a=3, side_b=7, side_c=5)
    assert out["angle_b"] == pytest.approx(120, abs=1e-12)
    by_sines = math.degrees(math.asin(7 * math.sin(math.radians(out["angle_a"])) / 3))
    assert by_sines == pytest.approx(60, abs=1e-9), "why MH31 p. 101's second step isn't used"


NEEDLES = [
    (10.0, 10.0, 1e-7),
    (100000.0, 99999.99979, 0.00029),
    (99999.99996, 99999.99994, 0.00003),
    (100000.0, 99999.9999999, 3e-7),
    (100000.0, 100000.0, 1.00005),
]
"""Needle-thin triangles, some from Kahan's paper, where plain Heron loses digits."""


def _exact_area(a: float, b: float, c: float) -> float:
    getcontext().prec = 60
    x, y, z = (Decimal(v) for v in (a, b, c))
    s = (x + y + z) / 2
    return float((s * (s - x) * (s - y) * (s - z)).sqrt())


def test_a_needle_triangle_keeps_its_area() -> None:
    """Kahan's arrangement: sides 10, 10, 1e-7 have area 5e-7; plain Heron loses it."""
    result = Triangle().run({"side_a": 10.0, "side_b": 10.0, "side_c": 1e-7})
    assert result.outputs["area"] == pytest.approx(5e-7, rel=1e-15, abs=0)
    s = (10 + 10 + 1e-7) / 2
    plain = math.sqrt(s * (s - 10) * (s - 10) * (s - 1e-7))
    assert abs(plain - 5e-7) / 5e-7 > 1e-9, "the plain formula loses digits here"


@pytest.mark.parametrize("sides", NEEDLES)
def test_every_needle_keeps_its_area_in_any_order_of_its_sides(
    sides: tuple[float, float, float],
) -> None:
    exact = _exact_area(*sides)
    for order in itertools.permutations(sides):
        keys = dict(zip(("side_a", "side_b", "side_c"), order, strict=True))
        area = Triangle().run(keys).outputs["area"]
        assert area == pytest.approx(exact, rel=1e-14, abs=0), order


def test_each_cosine_is_clamped_so_a_rounding_past_one_is_still_an_angle() -> None:
    """These sides' cosine of A computes as 1.0000000000000002; acos would refuse it."""
    a, b, c = 0.07165433510563943, 4.478911887913045, 4.550566223018663
    cosine = (b**2 + c**2 - a**2) / (2 * b * c)
    assert cosine > 1, "the case the clamp is for"
    result = Triangle().run({"side_a": a, "side_b": b, "side_c": c})
    assert result.outputs["angle_a"] == 0.0
    assert 179 < result.outputs["angle_b"] + result.outputs["angle_c"] <= 180 + 1e-9


@pytest.mark.parametrize(
    "sides",
    [(1, 1, 2), (3, 4, 7), (3, 4, 8), (8, 3, 4), (4, 8, 3), (2, 1, 1)],
)
def test_a_flat_or_impossible_triangle_is_refused(sides: tuple[float, float, float]) -> None:
    """With the sides sorted a ≤ b ≤ c, c ≥ a + b is refused, a flat triangle included."""
    keys = dict(zip(("side_a", "side_b", "side_c"), sides, strict=True))
    with pytest.raises(InputError, match="These sides make no triangle"):
        Triangle().run(keys)


@pytest.mark.parametrize(
    ("method", "given"),
    [
        ("legs", {"leg_a": 3, "leg_b": 4}),
        ("leg_hypotenuse", {"leg_a": 3, "hypotenuse": 5}),
        ("leg_angle", {"leg_a": 3, "angle_a": math.degrees(math.atan2(3, 4))}),
        ("hypotenuse_angle", {"hypotenuse": 5, "angle_a": math.degrees(math.atan2(3, 4))}),
    ],
)
def test_a_right_triangle_from_any_two_of_its_parts(method: str, given: dict[str, float]) -> None:
    out = run_inches(RightTriangle(), method, **given)
    assert out["leg_a"] == pytest.approx(3, rel=1e-14)
    assert out["leg_b"] == pytest.approx(4, rel=1e-14)
    assert out["hypotenuse"] == pytest.approx(5, rel=1e-14)
    assert out["angle_a"] == pytest.approx(36.8699, abs=5e-5)
    assert out["angle_b"] == pytest.approx(53.1301, abs=5e-5)
    assert out["area"] / IN2 == pytest.approx(6, rel=1e-14)
    assert out["perimeter"] == pytest.approx(12, rel=1e-14)


def test_a_leg_from_the_hypotenuse_keeps_its_digits() -> None:
    """B = √((c − a)·(c + a)): with a leg nearly the hypotenuse, √(c² − a²) loses them."""
    a, c = 1.0, 1.0000000001
    out = RightTriangle().run({"leg_a": a, "hypotenuse": c}, "leg_hypotenuse").outputs
    getcontext().prec = 50
    exact = float((Decimal(c) ** 2 - Decimal(a) ** 2).sqrt())
    assert out["leg_b"] == pytest.approx(exact, rel=1e-15, abs=0)
    naive = math.sqrt(c * c - a * a)
    assert abs(naive - exact) / exact > 1e-12, "the plain form loses digits here"


@pytest.mark.parametrize(("leg", "hypotenuse"), [(5, 5), (5, 4), (5, 0.001)])
def test_a_hypotenuse_no_longer_than_its_leg_is_refused(leg: float, hypotenuse: float) -> None:
    with pytest.raises(InputError, match=r"hypotenuse \(c\) must be longer than the leg \(a\)"):
        run_inches(RightTriangle(), "leg_hypotenuse", leg_a=leg, hypotenuse=hypotenuse)


@pytest.mark.parametrize("angle", [0, 90, -10, 120])
def test_an_acute_angle_outside_0_to_90_is_refused(angle: float) -> None:
    with pytest.raises(OutOfRangeError, match="Angle A"):
        run_inches(RightTriangle(), "leg_angle", leg_a=3, angle_a=angle)


def test_two_angles_alone_are_never_a_method() -> None:
    """Two angles fix no size, so every method takes at least one length."""
    calc = RightTriangle()
    for m in calc.methods:
        assert any(p.dimension is Dimension.LENGTH for p in calc.params_for(m.key)), m.key
        assert len(calc.params_for(m.key)) == 2, m.key


def test_a_hexagon_of_side_one() -> None:
    """Across flats √3, across corners 2, area 3√3/2."""
    for method, given in (
        ("side", {"side": 1}),
        ("across_flats", {"across_flats": math.sqrt(3)}),
        ("across_corners", {"across_corners": 2}),
    ):
        out = run_inches(RegularPolygon(), method, sides=6, **given)
        assert out["side"] == pytest.approx(1, rel=1e-14), method
        assert out["across_flats"] == pytest.approx(math.sqrt(3), rel=1e-14), method
        assert out["across_corners"] == pytest.approx(2, rel=1e-14), method
        assert out["perimeter"] == pytest.approx(6, rel=1e-14), method
        assert out["area"] / IN2 == pytest.approx(3 * math.sqrt(3) / 2, rel=1e-14), method


def test_a_square_and_an_equilateral_triangle_as_polygons() -> None:
    square = run_inches(RegularPolygon(), "side", sides=4, side=2)
    assert square["across_flats"] == pytest.approx(2) and square["area"] / IN2 == pytest.approx(4)
    assert square["across_corners"] == pytest.approx(2 * math.sqrt(2))
    tri = run_inches(RegularPolygon(), "side", sides=3, side=2)
    assert tri["area"] / IN2 == pytest.approx(math.sqrt(3), rel=1e-14)


def test_an_odd_polygon_says_what_a_caliper_reads() -> None:
    """With no parallel flats, a caliper across it reads r + R."""
    result = RegularPolygon().run({"sides": 5, "side": 25.4}, "side")
    (note,) = result.notes
    reading = (result.outputs["across_flats"] + result.outputs["across_corners"]) / 2
    assert note.quantities["reading"] == (pytest.approx(reading), Dimension.LENGTH)
    assert note.subjects == ("sides", "across_flats", "across_corners")
    text = describe_note(note, DisplayPrefs()).lead
    assert "a caliper across the polygon reads 1.5388 in" in text and "r + R" in text
    assert RegularPolygon().run({"sides": 6}, "side").notes == (), "even: flats are parallel"


@pytest.mark.parametrize(("sides", "error"), [(2, OutOfRangeError), (2.999, OutOfRangeError)])
def test_fewer_than_three_sides_is_refused(sides: float, error: type[Exception]) -> None:
    with pytest.raises(error, match="Number of sides"):
        RegularPolygon().run({"sides": sides}, "side")


@pytest.mark.parametrize("sides", [6.5, 3.000001, 1e3 + 0.5])
def test_a_number_of_sides_that_isnt_whole_is_refused(sides: float) -> None:
    with pytest.raises(InputError, match=r"number of sides \(N\) must be a whole number"):
        RegularPolygon().run({"sides": sides}, "side")


def test_a_sector_of_radius_10_and_90_degrees() -> None:
    """Arc 5π, chord 10√2, sagitta 10 − 5√2, area 25π."""
    out = run_inches(ArcSector(), radius=10, angle=90)
    assert out["arc_length"] == pytest.approx(5 * math.pi, rel=1e-15)
    assert out["chord"] == pytest.approx(10 * math.sqrt(2), rel=1e-15)
    assert out["sagitta"] == pytest.approx(10 - 5 * math.sqrt(2), rel=1e-14)
    assert out["sector_area"] / IN2 == pytest.approx(25 * math.pi, rel=1e-15)


def test_a_major_arc_and_a_whole_circle() -> None:
    """Past 180° is a valid major arc; 360° is the whole circle."""
    major = run_inches(ArcSector(), radius=10, angle=270)
    assert major["chord"] == pytest.approx(10 * math.sqrt(2), rel=1e-14)
    assert major["sagitta"] == pytest.approx(10 + 5 * math.sqrt(2), rel=1e-14)
    whole = run_inches(ArcSector(), radius=10, angle=360)
    assert whole["arc_length"] == pytest.approx(20 * math.pi)
    assert whole["sagitta"] == pytest.approx(20) and whole["chord"] == pytest.approx(0, abs=1e-12)


def test_a_small_angles_sagitta_keeps_its_digits() -> None:
    """2·r·sin²(A/4) against r·(1 − cos(A/2)), which loses its digits as A shrinks."""
    r, angle = 1000.0, 1e-5
    out = ArcSector().run({"radius": r, "angle": angle}).outputs
    theta = math.radians(angle)
    series = r * (theta**2 / 8 - theta**4 / 384)
    assert out["sagitta"] == pytest.approx(series, rel=1e-12, abs=0)
    naive = r * (1 - math.cos(theta / 2))
    assert abs(naive - series) / series > 1e-6, "the Handbook's form, in floats, is off here"


@pytest.mark.parametrize("angle", [0, -1, 360.0001, 720])
def test_an_arc_angle_outside_0_to_360_is_refused(angle: float) -> None:
    with pytest.raises(OutOfRangeError, match="Included angle"):
        run_inches(ArcSector(), radius=1, angle=angle)


LENGTH_INPUTS = [
    (calc, m.key, p.key)
    for calc in CALCULATORS
    for m in calc.methods
    for p in calc.params_for(m.key)
    if p.dimension is Dimension.LENGTH
]


@pytest.mark.parametrize(("calc", "method", "key"), LENGTH_INPUTS)
@pytest.mark.parametrize("bad", [0.0, -1.0, math.inf, -math.inf, math.nan])
def test_every_length_is_finite_and_greater_than_zero(
    calc: type[Calculator], method: str, key: str, bad: float
) -> None:
    with pytest.raises(InputError):
        calc().run({key: bad}, method)


def test_every_method_cites_the_handbook_and_points_students_to_the_pocket_companion() -> None:
    for calc in CALCULATORS:
        for m in calc.methods:
            titles = [r.title for r in m.references]
            assert MH31 in titles, (calc.id, m.key)
            pocket = {POCKET_PLANE_FIGURES, POCKET_TRIANGLES} & set(m.references)
            assert len(pocket) == 1 and m.references[-1] in pocket, "last, as a see also"
            assert all(r.detail.startswith("see also") for r in pocket)
            assert m.verification is Verification.UNVERIFIED, "no published example tests it"
            assert m.verification_note, (calc.id, m.key)


def test_the_triangles_cite_the_dlmf_and_record_the_departure_from_the_handbook() -> None:
    (method,) = Triangle.methods
    assert {MH31_LAW_OF_COSINES, MH31_THREE_SIDES, DLMF_TRIANGLES, KAHAN_NEEDLE} <= set(
        method.references
    )
    assert any("departs from it there on purpose" in note for note in method.notes)
    assert all(DLMF_TRIANGLES in m.references for m in RightTriangle.methods)


def test_a_polygons_sizes_are_named_by_their_circles() -> None:
    labels = {o.key: o.label for o in RegularPolygon.outputs}
    assert labels["across_flats"] == "Across flats (inscribed circle)"
    assert labels["across_corners"] == "Across corners (circumscribed circle)"
    assert all("r + R" in m.notes[0] for m in RegularPolygon.methods)


def test_areas_are_shown_in_the_square_of_the_length_unit() -> None:
    from caddcalc.core.formatting import format_output

    calc = Rectangle()
    result = calc.run()
    area = calc.output("area")
    assert format_output(area, result.outputs["area"], DisplayPrefs()) == "12.0000 in²"
    prefs = DisplayPrefs(length_unit="mm")
    assert format_output(area, result.outputs["area"], prefs) == "7741.92 mm²"


def test_the_cli_and_json_need_no_code_of_their_own(capsys: pytest.CaptureFixture[str]) -> None:
    import json

    from caddcalc.cli import main

    assert main(["run", "geometry.triangle", "a=3", "b=7", "c=5"]) == 0
    out = capsys.readouterr().out
    assert "120.00°" in out and "acos(max(-1, min(1," in out and "in²" in out
    assert (
        main(
            ["run", "geometry.right_triangle", "a=3", "c=5", "--method", "leg_hypotenuse", "--json"]
        )
        == 0
    )
    data = json.loads(capsys.readouterr().out)
    assert data["outputs"]["area"] == {
        "value": pytest.approx(6 * IN2),
        "unit": "mm²",
        "dimension": "area",
    }
    assert data["outputs"]["hypotenuse"]["value"] == pytest.approx(127)
    assert main(["run", "geometry.right_triangle", "a=5", "C=4", "--method", "leg_hypotenuse"]) != 0
    assert "must be longer than the leg" in capsys.readouterr().err


class _Given(Calculator):
    id = "test.given"
    name = "Given"
    domain = "test"
    summary = "Gives an input as an output."
    params = (Param("length", "X", "Length", Dimension.LENGTH, default="1 in"),)
    outputs = (Output("same", "X", "Same", Dimension.LENGTH),)
    methods = (Method("only", "Only", "X", Verification.UNVERIFIED),)
    symbol, output = "X", "same"

    @override
    def compute(self, ctx: Context) -> None:
        ctx.given(self.symbol, output=self.output)


@pytest.mark.parametrize(
    ("symbol", "output", "problem"),
    [
        ("Y", "same", "'Y' isn't an input of this run"),
        ("X", "other", "'other' isn't an output"),
    ],
)
def test_given_names_an_input_and_an_output(symbol: str, output: str, problem: str) -> None:
    class Bad(_Given):
        pass

    Bad.symbol, Bad.output = symbol, output
    with pytest.raises(SpecError, match=problem):
        Bad().run()
    assert _Given().run().outputs["same"] == pytest.approx(25.4)


def test_given_refuses_an_output_of_another_dimension() -> None:
    class Angled(_Given):
        outputs = (Output("same", "X", "Same", Dimension.ANGLE),)

    with pytest.raises(SpecError, match="input 'X' isn't an angle"):
        Angled().run()
