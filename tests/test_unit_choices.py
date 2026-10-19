"""What a field's picker and a calculator's output picker offer (ADR-0024 E1).

Each choice is a unit's key symbol or a form's key. A calculator declares its default
input units through its parameters' defaults, and its output sets, or gets the generated
ones, which show what the length preference showed (ADR-0019 §2).
"""

from __future__ import annotations

from typing import Any

import pytest

from caddcalc.calculators import default_registry
from caddcalc.calculators.geometry import RightTriangle
from caddcalc.calculators.sheet_metal import BendAllowance
from caddcalc.core import (
    Calculator,
    Dimension,
    Method,
    Output,
    Param,
    SpecError,
    UnitSet,
    UsageError,
    Verification,
)
from caddcalc.core.formatting import DisplayPrefs, display_unit
from caddcalc.core.units import registry

L, A, R, S, AREA, C = (
    Dimension.LENGTH,
    Dimension.ANGLE,
    Dimension.RATIO,
    Dimension.STRESS,
    Dimension.AREA,
    Dimension.COUNT,
)


def test_a_picker_lists_inch_pound_first_then_si_each_form_after_its_unit() -> None:
    units = registry()
    assert units.entry_choices(L) == ("in", "ft_in", "ft", "mm", "cm", "m")
    assert units.entry_choices(A) == ("deg", "dms", "arcmin", "arcsec", "rad")
    assert units.entry_choices(S) == ("psi", "ksi", "MPa", "kPa", "GPa")
    assert units.entry_choices(AREA) == ("in²", "ft²", "mm²", "cm²", "m²")
    assert units.entry_choices(R) == units.entry_choices(C) == ("",), "no picker"
    assert units.output_choices(L) == (
        "in",
        "in_16",
        "in_32",
        "in_64",
        "ft_in",
        "ft_in_32",
        "ft_in_64",
        "ft",
        "mm",
        "cm",
        "m",
    )
    assert units.output_choices(R) == ("", "%")


def test_only_feet_and_inches_and_dms_read() -> None:
    """A field reads any fraction, so the finer feet and inches are for output only."""
    units = registry()
    reading = {f.key for d in Dimension for f in units.compounds_for(d) if f.reads}
    assert reading == {"ft_in", "dms"}
    for key in ("in_16", "in_64", "ft_in_32", "ft_in_64"):
        with pytest.raises(UsageError, match="is shown only"):
            units.compound(key).read("3/16")
    shown = {f.key: f.symbol for d in Dimension for f in units.compounds_for(d)}
    assert shown["ft_in"] == "ft-in" and shown["dms"] == "° ′ ″"


def test_a_choice_names_its_unit_or_form_for_its_dimension_only() -> None:
    units = registry()
    assert units.choice("mm", L).symbol == "mm"
    assert units.choice("ft_in", L).key == "ft_in"  # type: ignore[union-attr]
    for choice, dimension in (("deg", L), ("dms", L), ("ft_in", A), ("inch", L), ("xx", L)):
        with pytest.raises(UsageError, match="isn't a choice for"):
            units.choice(choice, dimension)


def test_the_generated_sets_are_one_per_length_choice() -> None:
    keys = [key for key, _choices in registry().generated_sets()]
    assert keys == ["in", "in_16", "in_32", "in_64", "ft_in", "ft", "mm", "cm", "m"]


@pytest.mark.parametrize("length", ["in", "mm", "ft", "cm", "m"])
def test_a_generated_set_shows_what_the_length_preference_showed(length: str) -> None:
    """E-3's neutrality rests on it: the in and mm sets are today's display units."""
    choices = dict(registry().generated_sets())[length]
    prefs = DisplayPrefs(length_unit=length)
    assert {d: choices[d] for d in Dimension} == {
        d: display_unit(d, prefs).symbol for d in Dimension
    }


@pytest.mark.parametrize("form", ["in_16", "in_32", "in_64", "ft_in"])
def test_area_is_square_inches_in_every_inch_form(form: str) -> None:
    choices = dict(registry().generated_sets())[form]
    assert (choices[L], choices[AREA], choices[S], choices[A]) == (form, "in²", "ksi", "deg")


def test_a_generated_set_is_labelled_by_what_the_calculator_shows() -> None:
    triangle = {s.key: s.label for s in RightTriangle.unit_sets()}
    assert triangle["in"] == "in · ° · in²" and triangle["mm"] == "mm · ° · mm²"
    assert triangle["ft_in"] == "ft-in · ° · in²"
    assert {s.key: s.label for s in BendAllowance.unit_sets()}["in_16"] == "in 1/16"


def test_every_built_in_input_starts_its_picker_in_a_unit_it_offers() -> None:
    """Every sheet-metal and geometry length starts in inches and every angle in degrees."""
    starts: dict[Dimension, set[str]] = {}
    for calc in default_registry(load_plugins=False):
        for p in calc.params:
            assert p.default_choice in p.choices, (calc.id, p.key)
            if not calc.id.startswith("conversions."):
                starts.setdefault(p.dimension, set()).add(p.default_choice or "")
    assert starts[L] == {"in"} and starts[A] == {"deg"}


class _Demo(Calculator):
    id = "demo.choices"
    name = "Choices"
    domain = "demo"
    summary = "A length."
    params = (Param("length", "X", "Length", L, default="1 in"),)
    outputs = (Output("same", "Y", "Same", L),)
    methods = (Method("only", "Only", "Y = X", Verification.UNVERIFIED),)

    def compute(self, ctx: Any) -> None:
        ctx.calc("Y", "X", label="Same", dimension=L, output="same")


def _with(**attrs: Any) -> type[Calculator]:
    return type("Variant", (_Demo,), attrs)


@pytest.mark.parametrize(
    ("param", "why"),
    [
        (Param("length", "X", "Length", L, default="1"), "has no default unit for its picker"),
        (Param("length", "X", "Length", L), "has no default unit for its picker"),
        (
            Param("length", "X", "Length", L, default="1 in", units=("mm", "m")),
            "starts its picker in 'in', which it doesn't offer",
        ),
        (
            Param("length", "X", "Length", L, default="1 in", unit="dms"),
            "starts its picker in 'dms', which it doesn't offer",
        ),
        (
            Param("length", "X", "Length", L, default="1 in", units=("in", "in_16")),
            "names 'in_16', which isn't a choice for a length",
        ),
        (
            Param("length", "X", "Length", L, default="1 in", units=("in", "in")),
            "duplicate choice",
        ),
    ],
)
def test_a_parameter_needs_a_default_choice_it_offers(param: Param, why: str) -> None:
    with pytest.raises(SpecError, match=why):
        _with(params=(param,)).validate_spec()


def test_a_parameter_resolves_its_default_choice() -> None:
    assert Param("t", "T", "T", L, default="3 mm").default_choice == "mm"
    assert Param("t", "T", "T", L, default="1", unit="ft_in").default_choice == "ft_in"
    assert Param("t", "T", "T", L, default="1'-4\"").default_choice == "ft_in"
    assert Param("k", "K", "K", R, default="0.44").default_choice == ""
    assert Param("n", "N", "N", C, default="6").default_choice == ""
    assert Param("t", "T", "T", L, units=("mm", "m")).choices == ("mm", "m")
    _with(params=(Param("length", "X", "Length", L, default="1", unit="mm"),)).validate_spec()


@pytest.mark.parametrize(
    ("attrs", "why"),
    [
        (
            {"output_sets": (UnitSet("in", "in", {A: "deg"}),)},
            "output set 'in' has no choice for length",
        ),
        (
            {"output_sets": (UnitSet("in", "in", {L: "deg"}),)},
            "output set 'in' names 'deg', which isn't a choice for a length",
        ),
        (
            {"output_sets": (UnitSet("in", "in", {L: "in"}), UnitSet("in", "x", {L: "mm"}))},
            "duplicate output set key 'in'",
        ),
        (
            {"outputs": (Output("same", "Y", "Same", L, unit="mm", picks=("in", "mm")),)},
            "gives picks and a fixed unit or form",
        ),
        (
            {"outputs": (Output("same", "Y", "Same", L, picks=("in", "deg")),)},
            "names 'deg', which isn't a choice for a length",
        ),
    ],
)
def test_output_sets_and_picks_are_checked(attrs: dict[str, Any], why: str) -> None:
    with pytest.raises(SpecError, match=why):
        _with(**attrs).validate_spec()


def test_a_declared_set_covers_only_what_follows_a_set() -> None:
    """An output with its own picks or a fixed unit needs no choice in a set."""
    _with(
        outputs=(
            Output("same", "Y", "Same", L),
            Output("angle", "B", "Angle", A, picks=("deg", "dms")),
        ),
        output_sets=(UnitSet("in_dms", "Inches", {L: "in"}),),
    ).validate_spec()
    sets = _with(output_sets=(UnitSet("in_dms", "Inches and DMS", {L: "in", A: "dms"}),))
    assert [s.key for s in sets.unit_sets()] == ["in_dms"]


def test_a_bare_default_is_in_the_unit_its_picker_starts_in() -> None:
    """0.1046 with unit "in" is 0.1046 in, never 0.1046 mm."""
    assert Param("t", "T", "T", L, default="0.1046", unit="in").default_value() == 0.1046 * 25.4
    assert Param("t", "T", "T", L, default="1", units=("in",)).default_value() == 25.4
    assert Param("t", "T", "T", L, default="10", unit="ft_in").default_value() == 10 * 25.4
    assert Param("t", "T", "T", L, default="3 mm", unit="in").default_value() == 3.0


def test_a_calculator_whose_outputs_all_have_their_own_units_has_no_sets() -> None:
    from caddcalc.calculators.conversions import LengthConverter

    assert LengthConverter.unit_sets() == ()


@pytest.mark.parametrize(("key", "label"), [("", "in"), ("in", ""), (" ", "x")])
def test_an_output_set_needs_a_key_and_a_label(key: str, label: str) -> None:
    with pytest.raises(SpecError, match="needs a key and a label"):
        _with(output_sets=(UnitSet(key, label, {L: "in"}),)).validate_spec()
