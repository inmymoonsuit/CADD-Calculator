"""What an output set shows each value in (ADR-0024 E4, slice E-3)."""

from __future__ import annotations

from typing import Any

import pytest

from caddcalc.core import (
    Calculator,
    Dimension,
    Method,
    Output,
    Param,
    UnitSet,
    UsageError,
    Verification,
)
from caddcalc.core.formatting import (
    DisplayPrefs,
    ShownUnits,
    describe_error,
    format_input,
    format_output,
    output_unit,
    render_step,
    results_tsv,
    value_parts,
)

L, A, AREA, S = Dimension.LENGTH, Dimension.ANGLE, Dimension.AREA, Dimension.STRESS
PREFS = DisplayPrefs()


class _Part(Calculator):
    id = "demo.part"
    name = "Part"
    domain = "demo"
    summary = "A length doubled, its square, and an angle."
    params = (
        Param("length", "X", "Length", L, default="8.09375 in", minimum=0.0, maximum=254.0),
        Param("angle", "θ", "Angle", A, default="30.5"),
    )
    outputs = (
        Output("double", "Y", "Double", L),
        Output("square", "Q", "Square", AREA),
        Output("turn", "B", "Turn", A),
        Output("side", "Z", "Side", L, picks=("in", "mm")),
        Output("fixed", "W", "Fixed", L, unit="mm"),
    )
    methods = (Method("only", "Only", "Y = 2 × X", Verification.UNVERIFIED),)

    def compute(self, ctx: Any) -> None:
        ctx.calc("Y", "2 * X", label="Double", dimension=L, output="double")
        ctx.calc("Q", "X * X", label="Square", dimension=AREA, output="square")
        ctx.calc("B", "θ", label="Turn", dimension=A, output="turn")
        ctx.calc("Z", "X", label="Side", dimension=L, output="side")
        ctx.calc("W", "X", label="Fixed", dimension=L, output="fixed")


def _shown(units: ShownUnits) -> dict[str, str]:
    result = _Part().run()
    return {o.key: format_output(o, result.outputs[o.key], units, PREFS) for o in _Part.outputs}


def test_a_feet_and_inches_set_shows_lengths_in_the_form_and_area_in_square_inches() -> None:
    shown = _shown(ShownUnits.generated("ft_in"))
    assert shown["double"] == "1'-4 3/16\""
    assert shown["square"] == "65.5088 in²"
    assert shown["turn"] == "30.50°"


def test_an_inch_fraction_set_shows_the_fraction() -> None:
    assert _shown(ShownUnits.generated("in_16"))["double"] == '16 3/16"'


def test_a_set_can_show_angles_in_degrees_minutes_and_seconds() -> None:
    units = ShownUnits.of(UnitSet("in_dms", "Inches and DMS", {L: "in", A: "dms"}))
    shown = _shown(units)
    assert shown["turn"] == "30°30′0.00″" and shown["double"] == "16.1875 in"
    assert units.choice(Dimension.STRESS) == "ksi", "the rest come from the generated set"


@pytest.mark.parametrize("length", ["in", "ft_in", "in_16", "mm"])
def test_an_output_with_its_own_picks_never_follows_the_set(length: str) -> None:
    """Until it's picked, it shows in its first pick."""
    assert _shown(ShownUnits.generated(length))["side"] == "8.0938 in"


def test_an_output_with_its_own_picks_shows_its_pick() -> None:
    picked = ShownUnits.of(UnitSet("in", "in", {L: "in"}), picks={"side": "mm"})
    assert _shown(picked)["side"] == "205.5812 mm"
    assert _shown(picked)["double"] == "16.1875 in", "only that output"
    with pytest.raises(UsageError, match="offers in, mm, not 'ft_in'"):
        _shown(ShownUnits.of(UnitSet("in", "in", {L: "in"}), picks={"side": "ft_in"}))


@pytest.mark.parametrize("length", ["in", "ft_in", "in_16", "mm"])
def test_a_fixed_unit_output_ignores_the_set(length: str) -> None:
    assert _shown(ShownUnits.generated(length))["fixed"] == "205.581 mm"


def test_the_work_uses_the_form_s_full_unit() -> None:
    """A line reads ``2 · 8.0938``, never ``2 · 0'-8 1/8"``, and its value in inches."""
    units = ShownUnits.generated("ft_in")
    result = _Part().run()
    lines = [render_step(step, result, units, PREFS) for step in result.steps]
    assert lines[0] == ("2 · X", "2 · 8.0938", "16.1875 in")
    assert lines[1] == ("X · X", "8.0938 · 8.0938", "65.5088 in²")
    assert units.unit(L).symbol == "in" and output_unit(_Part.outputs[0], units).symbol == "in"


def test_an_input_is_shown_in_its_field_s_choice_else_the_set_s() -> None:
    result = _Part().run()
    units = ShownUnits.generated("mm").with_inputs({"length": "ft_in"})
    assert format_input("length", result.inputs["length"], L, units, PREFS) == "0'-8 1/8\""
    assert format_input("angle", result.inputs["angle"], A, units, PREFS) == "30.50°"
    plain = ShownUnits.generated("mm")
    assert format_input("length", result.inputs["length"], L, plain, PREFS) == "205.5812 mm"


def test_a_range_error_names_the_bound_in_the_input_s_choice() -> None:
    """The user types in the field's unit, so the bound is in it: a form's full unit."""
    from caddcalc.core import InputError

    with pytest.raises(InputError) as caught:
        _Part().run({"length": 300.0})
    mm = ShownUnits.generated("mm")
    assert "10 in" in describe_error(caught.value, mm.with_inputs({"length": "in"}), PREFS)
    assert "10 in" in describe_error(caught.value, mm.with_inputs({"length": "ft_in"}), PREFS)
    assert describe_error(caught.value, mm, PREFS) == "Length (X) must be at most 254 mm"


def test_the_tsv_writes_a_form_as_text() -> None:
    rows = results_tsv(_Part(), _Part().run(), ShownUnits.generated("ft_in"), PREFS)
    assert rows.splitlines()[0] == "Y\tDouble\t1'-4 3/16\"\t"


def test_shown_units_need_a_choice_for_every_dimension() -> None:
    with pytest.raises(UsageError, match="no choice for"):
        ShownUnits({L: "in"})
    with pytest.raises(UsageError, match="No output set for 'inch'"):
        ShownUnits.generated("inch")
    units = ShownUnits.generated("in")
    with pytest.raises(TypeError):
        units.choices[L] = "mm"  # type: ignore[index]


def test_a_value_in_a_form_is_in_parts_with_its_compound() -> None:
    parts = value_parts(411.1625, L, ShownUnits.generated("ft_in"), PREFS)
    assert parts.compound is not None and parts.number == "1'-4 3/16\"" and parts.unit == ""


def test_a_unit_too_coarse_for_its_dimension_s_places_shows_its_own() -> None:
    """0.01 rad is over half a degree, so a radian shows four places, as no other unit does."""
    from caddcalc.core.units import registry

    own = {u.symbol: u.decimals for u in registry().units if u.decimals}
    assert own == {"rad": 4}
    units = ShownUnits.of(UnitSet("in_rad", "Inches and radians", {L: "in", A: "rad"}))
    assert _shown(units)["turn"] == "0.5323 rad"
    shown = format_input(
        "angle", 0.5323254, A, ShownUnits.generated().with_inputs({"angle": "rad"}), PREFS
    )
    assert shown == "0.0093 rad"
