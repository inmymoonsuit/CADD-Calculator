"""The CLI's units and JSON's schema 1 (ADR-0024 E5, slice E-4)."""

from __future__ import annotations

import json
from typing import Any

import pytest

from caddcalc.calculators import default_registry
from caddcalc.cli import main
from caddcalc.core import Dimension, TypedValue
from caddcalc.core.formatting import DisplayPrefs, ShownUnits, choice_unit, result_json
from caddcalc.core.units import BASE_UNITS, from_base, get_unit

INCH = 25.4
BEND = "sheet_metal.bend_allowance"


def _run(capsys: pytest.CaptureFixture[str], *argv: str) -> tuple[int, str, str]:
    status = main(list(argv))
    out, err = capsys.readouterr()
    return status, out, err


def _json(capsys: pytest.CaptureFixture[str], *argv: str) -> dict[str, Any]:
    status, out, err = _run(capsys, *argv, "--json")
    assert status == 0, err
    data: dict[str, Any] = json.loads(out)
    return data


def test_a_bare_number_is_in_the_input_s_default_choice(capsys: pytest.CaptureFixture[str]) -> None:
    """Inches for every sheet-metal and geometry length, and degrees for every angle."""
    data = _json(capsys, "run", BEND, "T=0.25", "R=4mm")
    assert data["inputs"]["thickness"]["base"]["value"] == pytest.approx(0.25 * INCH)
    assert data["inputs"]["thickness"]["entered"] == {
        "text": "0.25",
        "unit": "in",
        "unit_in_text": False,
    }
    assert data["inputs"]["inside_radius"]["entered"]["unit_in_text"] is True
    assert data["inputs"]["inside_radius"]["shown"]["text"] == "4.0000 mm", "as it was read"
    assert "entered" not in data["inputs"]["bend_angle"], "a default wasn't given"
    assert data["inputs"]["bend_angle"]["base"]["value"] == 90.0


def test_unit_reads_an_input_as_a_picked_field_does(capsys: pytest.CaptureFixture[str]) -> None:
    data = _json(capsys, "run", "geometry.circle", "--unit", "d=ft_in", "d=10-2")
    diameter = data["inputs"]["diameter"]
    assert diameter["base"]["value"] == pytest.approx(122 * INCH)
    assert diameter["entered"] == {
        "text": "10-2",
        "unit": "in",
        "form": "ft_in",
        "unit_in_text": False,
    }
    assert diameter["shown"]["text"] == "10'-2\"" and diameter["shown"]["copied"] == "10'2\""
    marked = _json(capsys, "run", "geometry.circle", "--unit", "d=ft_in", "d=10'-2\"")
    assert marked["inputs"]["diameter"]["base"] == diameter["base"], "a form's marks are its own"
    angle = _json(capsys, "run", BEND, "--unit", "A=dms", "A=40 30 15")
    assert angle["inputs"]["bend_angle"]["base"]["value"] == pytest.approx(40 + 30 / 60 + 15 / 3600)
    sums = _json(capsys, "run", BEND, "--unit", "T=in", "T=2*3/32")
    assert (
        sums["inputs"]["thickness"]["base"]["value"]
        == TypedValue.read("3/16", "in", Dimension.LENGTH).value
    )


@pytest.mark.parametrize(
    ("argv", "why"),
    [
        (["--unit", "T=in", "T=3mm"], "names a unit, mm, but --unit T=in reads it in in"),
        (["--unit", "T=in", 'T=3"'], "names a unit"),
        (["--unit", "T=mm", "T=2,5"], "comma"),
        (["T=2,5"], "comma"),
        (["--unit", "T=mm"], "which isn't given; give it as T=VALUE"),
        (["--unit", "T=mm", "--unit", "T=in", "T=3"], "names T/thickness twice"),
        (["--unit", "T=deg", "T=3"], "'deg' isn't a unit for T/thickness"),
        (["--unit", "T", "T=3"], "Expected --unit NAME=ID"),
        (["--output-set", "inch"], "--output-set 'inch' isn't one of"),
        (["--output-unit", "BA=mm"], "has no unit of its own to pick"),
        (["--output-unit", "XX=mm"], "has no output 'XX'; the outputs with their own unit"),
        (["--output-unit", "ba=mm"], "BA/bend_allowance has no unit of its own"),
        (["--output-unit", "=mm"], "Expected --output-unit KEY=ID"),
        (["--unit", "T=", "T=3"], "give the unit or form to read thickness in"),
        (["--output-set", "mm", "--output-set", "in"], "--output-set is given 2 times"),
    ],
)
def test_mistakes_are_refused(
    capsys: pytest.CaptureFixture[str], argv: list[str], why: str
) -> None:
    status, out, err = _run(capsys, "run", BEND, *argv)
    assert status == 2 and out == ""
    assert why in err


@pytest.mark.parametrize("removed", [["--units", "mm"], ["--fraction", "64"]])
def test_units_and_fraction_are_gone(
    capsys: pytest.CaptureFixture[str], removed: list[str]
) -> None:
    with pytest.raises(SystemExit) as exited:
        main(["run", BEND, *removed])
    assert exited.value.code == 2
    assert "unrecognized arguments" in capsys.readouterr().err


def test_the_output_set_and_an_output_s_own_pick(capsys: pytest.CaptureFixture[str]) -> None:
    status, out, _err = _run(capsys, "run", BEND, "--output-set", "in_16", "--no-work")
    assert status == 0 and 'Bend allowance                   5/16"' in out
    assert '")' not in out, 'no (≈ 5/16") hint'
    data = _json(capsys, "run", BEND, "--output-set", "mm")
    assert data["output_set"] == "mm"
    assert data["outputs"]["bend_allowance"]["shown"]["unit"] == "mm"
    assert data["inputs"]["thickness"]["shown"]["unit"] == "in", "an input in its own choice"
    assert data["steps"][0]["shown"]["unit"] == "mm", "a step in the set's unit"


def test_show_lists_each_input_s_choices_and_the_output_sets(
    capsys: pytest.CaptureFixture[str],
) -> None:
    status, out, _err = _run(capsys, "show", BEND)
    assert status == 0
    assert "Units (--unit): in (default), ft_in, ft, mm, cm, m" in out
    assert "Units (--unit): deg (default), dms, rad" in out
    assert "Output sets (--output-set)" in out and "in_16      in 1/16" in out
    status, out, _err = _run(capsys, "show", "conversions.length")
    assert "Output sets" not in out
    assert "Units (--output-unit): in, ft_in, ft, mm, cm, m" in out
    assert "Until picked, it follows value: in → mm, ft_in → mm, ft → m, mm → in" in out
    status, out, _err = _run(capsys, "show", "conversions.decimal_to_fraction")
    assert "Values: 16 (1/16), 32 (1/32), 64 (1/64)" in out and "Always in in_64" in out


def _calls() -> list[tuple[str, str]]:
    return [(c.id, m.key) for c in default_registry(load_plugins=False) for m in c.methods]


@pytest.mark.parametrize(("calc_id", "method"), _calls())
def test_every_key_of_schema_1_is_there_with_its_type(calc_id: str, method: str) -> None:
    """Every built-in and method, on its defaults, with its first input given as text."""
    calc = default_registry(load_plugins=False).get(calc_id)
    first = calc.params_for(method)[0]
    unit = choice_unit(first.default_choice or "", first.dimension).symbol
    entry = TypedValue.parse(first.default or "1", first.dimension, unit)
    result = calc.run({first.key: entry.value}, method)
    from caddcalc.cli import _output_units

    units = _output_units(calc, None, [], {first.key: entry})
    data = result_json(calc, result, units, DisplayPrefs(), {first.key: entry})
    json.dumps(data)  # it serialises
    assert data["schema"] == 1 and data["calculator"] == calc_id and data["method"] == method
    sets = calc.unit_sets()
    assert data["output_set"] == (sets[0].key if sets else None), "null with no sets"
    values = [
        *(("input", k, v) for k, v in data["inputs"].items()),
        *(("output", k, v) for k, v in data["outputs"].items()),
        *(("step", s["symbol"], s) for s in data["steps"]),
    ]
    for kind, key, value in values:
        dimension = Dimension(value["dimension"])
        base, shown = value["base"], value["shown"]
        assert base["unit"] == BASE_UNITS[dimension], (kind, key)
        whole = dimension is Dimension.COUNT
        assert isinstance(base["value"], int if whole else float), (kind, key)
        assert {"unit", "value", "text"} <= shown.keys(), (kind, key)
        unit = get_unit(shown["unit"], dimension)
        assert shown["value"] == pytest.approx(from_base(base["value"], unit)), "unrounded"
        assert ("form" in shown) == ("copied" in shown), (kind, key)
    for key, value in data["inputs"].items():
        assert ("entered" in value) == (key == first.key), key
        assert set(value) >= {"dimension", "base", "shown", "source"}
    if "entered" in data["inputs"][first.key]:
        entered = data["inputs"][first.key]["entered"]
        assert {"text", "unit", "unit_in_text"} <= entered.keys()
    for note in data["notes"]:
        assert set(note) == {"kind", "text", "detail", "quantities", "references", "subjects"}
        for quantity in note["quantities"].values():
            assert set(quantity) == {"dimension", "base", "shown"}


def test_a_published_example_in_schema_1(capsys: pytest.CaptureFixture[str]) -> None:
    """MH31 Fig. 13, printed p. 1421: BA at 90° is half the printed 1.338 for 180°.

    MH31 = Machinery's Handbook, 31st ed., "Bending Sheet Metal" (tests/test_published_examples).
    """
    args = ("run", BEND, "--method", "course", "T=0.125", "R=0.375", "A=90")
    data = _json(capsys, *args)
    ba = data["outputs"]["bend_allowance"]
    assert ba["base"]["unit"] == "mm" and ba["shown"]["unit"] == "in"
    assert ba["shown"]["value"] == pytest.approx(1.338 / 2, abs=0.0005 + 1e-9)
    assert ba["base"]["value"] == pytest.approx(ba["shown"]["value"] * INCH, rel=1e-15)
    assert ba["shown"]["text"] == f"{ba['shown']['value']:.4f} in"
    sixteenths = _json(capsys, *args, "--output-set", "in_16")["outputs"]["bend_allowance"]
    assert sixteenths["base"] == ba["base"], "the set changes only how it's shown"
    assert sixteenths["shown"] == {
        "unit": "in",
        "value": ba["shown"]["value"],
        "form": "in_16",
        "text": '11/16"',
        "copied": '11/16"',
    }


def test_a_signed_step_shows_its_plus_in_json() -> None:
    """A fraction's error shows ``+0.0025 in`` in its work, so its JSON does too."""
    from caddcalc.calculators.conversions import DecimalToFraction

    calc = DecimalToFraction()
    result = calc.run({"value": 7.9223})
    data = result_json(calc, result, ShownUnits.generated(), DisplayPrefs())
    signed = [s for s, step in zip(data["steps"], result.steps, strict=True) if step.signed]
    assert signed, "the converter has signed steps"
    for step in signed:
        sign = "+" if step["base"]["value"] > 0 else "-"
        assert step["shown"]["text"].startswith(sign), step


def test_a_unit_for_an_input_the_method_doesn_t_use_is_refused_as_such(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """It's never advised as ``give it as c=VALUE``, which would then be refused."""
    status, _out, err = _run(capsys, "run", "geometry.right_triangle", "--unit", "c=mm")
    assert status == 2
    assert "c/hypotenuse isn't an input of this method; its inputs are a/leg_a, b/leg_b" in err


def test_an_output_with_its_own_picker_is_named_in_any_case(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    from caddcalc import cli
    from tests.test_output_picker import _Mixed

    monkeypatch.setattr(cli, "default_registry", _mixed_registry)
    for name in ("Z", "z", "own", "OWN"):
        data = _json(capsys, "run", _Mixed.id, "--output-unit", f"{name}=cm")
        assert data["outputs"]["own"]["shown"]["text"] == "5.0800 cm", name


def _mixed_registry() -> Any:
    from caddcalc.core import Registry
    from tests.test_domains import ACME
    from tests.test_output_picker import _Mixed

    registry = Registry()
    registry.register_domain(ACME)
    registry.register(_Mixed)
    return registry


def test_a_unit_between_inputs_is_read(capsys: pytest.CaptureFixture[str]) -> None:
    data = _json(capsys, "run", BEND, "T=0.1", "--unit", "R=mm", "R=3")
    assert data["inputs"]["inside_radius"]["base"]["value"] == 3.0
    assert data["inputs"]["thickness"]["base"]["value"] == 0.1 * 25.4


def test_inputs_after_options_are_read(capsys: pytest.CaptureFixture[str]) -> None:
    """Before Python 3.13, argparse took a run's inputs only before its first option."""
    data = _json(capsys, "run", BEND, "--method", "course", "T=0.25", "--output-set", "mm", "R=4mm")
    assert data["method"] == "course" and data["output_set"] == "mm"
    assert data["inputs"]["thickness"]["entered"]["text"] == "0.25"
    assert data["inputs"]["inside_radius"]["entered"]["text"] == "4mm"
    status, _out, err = _run(capsys, "run", BEND, "--method", "course", "T=0.25", "stray")
    assert status == 2 and "Expected NAME=VALUE, got 'stray'" in err, "in every version"


@pytest.mark.parametrize(
    ("argv", "unit", "value"),
    [
        (["T=3"], "in", 3.0),
        (["T=0.3cm"], "cm", 0.3),
        (["--unit", "T=cm", "T=0.3"], "cm", 0.3),
        (["--unit", "T=ft_in", "T=10-2"], "in", 122.0),
    ],
)
def test_an_input_s_shown_value_is_the_number_typed(
    capsys: pytest.CaptureFixture[str], argv: list[str], unit: str, value: float
) -> None:
    """Not base ÷ factor, which makes T=3 2.9999999999999996 (S&R's L2 at stop 2)."""
    thickness = _json(capsys, "run", BEND, *argv)["inputs"]["thickness"]
    assert (thickness["shown"]["unit"], thickness["shown"]["value"]) == (unit, value)
    assert thickness["base"]["value"] == TypedValue.read(str(value), unit, Dimension.LENGTH).value


@pytest.mark.parametrize(
    ("text", "unit", "value"),
    [
        ('value=3 - 1/2"', "in", 3.5),
        ("value=3- 3/16", "in", 3.1875),
        ("value=12 - 1/2 mm", "mm", 12.5),
    ],
)
def test_a_shown_value_agrees_with_its_base_however_the_text_was_read(
    capsys: pytest.CaptureFixture[str], text: str, unit: str, value: float
) -> None:
    """Without ``--unit``, ``3 - 1/2"`` is a mixed number, so its shown value is 3.5, not 2.5.

    The CLI reads it as ``parse_quantity`` does; the field's reader would subtract. An
    amount that doesn't give the base the run used isn't the one typed (the cloud
    review's final Medium).
    """
    data = _json(capsys, "run", "conversions.length", text)["inputs"]["value"]
    assert (data["shown"]["unit"], data["shown"]["value"]) == (unit, value)
    assert data["base"]["value"] == pytest.approx(value * (25.4 if unit == "in" else 1.0))


def test_an_input_in_a_form_is_listed_as_nearly_as_it_ran(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """0.1046 in picked in ft-in isn't 0'-0 1/8": it's listed in inches (S&R's L3)."""
    inexact = _json(capsys, "run", BEND, "--unit", "T=ft_in", "T=0'-0.1046\"")
    shown = inexact["inputs"]["thickness"]["shown"]
    assert shown["text"] == "0.1046 in" and "form" not in shown
    status, out, _err = _run(capsys, "run", BEND, "--unit", "T=ft_in", "T=0'-0.1046\"")
    assert status == 0 and "Material thickness               0.1046 in" in out
    exact = _json(capsys, "run", BEND, "--unit", "T=ft_in", "T=10-2 3/16")
    assert exact["inputs"]["thickness"]["shown"]["text"] == "10'-2 3/16\""
    seconds = _json(capsys, "run", BEND, "--unit", "A=dms", "A=40 30 15.123")
    assert seconds["inputs"]["bend_angle"]["shown"]["text"] == "40°30′15.12″", "nearer than 40.50°"


def test_an_input_written_in_a_form_s_marks_is_shown_in_that_form(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """``d=10'-2"`` with no ``--unit`` is listed as ``10'-2"``, not 122 in."""
    data = _json(capsys, "run", "geometry.circle", "d=10'-2\"")
    assert data["inputs"]["diameter"]["shown"]["text"] == "10'-2\""


def test_an_input_is_entered_as_typed_spaces_and_all(capsys: pytest.CaptureFixture[str]) -> None:
    """``1 1/2`` replays as 1 1/2; ``11/2`` would be 5 1/2."""
    data = _json(capsys, "run", BEND, "T=1 1/2")
    assert data["inputs"]["thickness"]["entered"]["text"] == "1 1/2"


def test_a_calculator_with_no_sets_shows_each_input_as_read(
    capsys: pytest.CaptureFixture[str],
) -> None:
    data = _json(capsys, "run", "conversions.length", "value=3cm")
    assert data["output_set"] is None
    assert data["inputs"]["value"]["shown"]["text"] == "3.0000 cm"


def test_the_inputs_are_listed_in_their_own_choice_not_the_set_s(
    capsys: pytest.CaptureFixture[str],
) -> None:
    status, out, _err = _run(capsys, "run", BEND, "T=0.1", "--output-set", "mm", "--no-work")
    assert status == 0
    (line,) = [line for line in out.splitlines() if "Material thickness" in line]
    assert "0.1000 in" in line
