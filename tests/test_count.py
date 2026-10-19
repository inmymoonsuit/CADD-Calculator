"""A count, such as a polygon's number of sides, is a whole number everywhere (KI-025)."""

from __future__ import annotations

import json
import re

import pytest

from caddcalc.calculators.geometry import RegularPolygon
from caddcalc.core import Dimension, InputError
from caddcalc.core.formatting import (
    CopyForm,
    DisplayPrefs,
    copy_text,
    field_text,
    format_value,
    spoken_value,
    value_parts,
)
from caddcalc.core.units import parse_quantity
from tests.qt_helpers import open_window, type_into

COUNT = Dimension.COUNT


def test_a_count_shows_and_copies_without_decimals() -> None:
    prefs = DisplayPrefs()
    assert format_value(6.0, COUNT, prefs) == "6"
    assert field_text(6.0, COUNT, prefs) == "6"
    forms = (CopyForm.VALUE, CopyForm.SHOWN, CopyForm.WITH_UNIT, CopyForm.FULL)
    assert {copy_text(6.0, COUNT, prefs, form) for form in forms} == {"6"}
    assert spoken_value(value_parts(6.0, COUNT, prefs)) == "6"


@pytest.mark.parametrize(
    ("typed", "why"),
    [
        ("600 %", "is a ratio, but a count is expected"),
        ("6 in", "is a length, but a count is expected"),
        ("6 deg", "is an angle, but a count is expected"),
        ("6.5", "isn't a whole number"),
        ("6 1/2", "isn't a whole number"),
    ],
)
def test_a_unit_a_percent_or_a_fraction_on_a_count_is_refused(typed: str, why: str) -> None:
    """A percent is a unit of the ratio, so ``600 %`` is never 6 sides (KI-025)."""
    with pytest.raises(InputError, match=re.escape(why)):
        parse_quantity(typed, COUNT)
    assert parse_quantity("6", COUNT) == 6.0 and parse_quantity("6.0", COUNT) == 6.0


def test_the_cli_and_json_show_a_count_whole(capsys: pytest.CaptureFixture[str]) -> None:
    from caddcalc.cli import main

    assert main(["run", "geometry.regular_polygon", "N=6", "a=1in"]) == 0
    out = capsys.readouterr().out
    assert re.search(r"N +Number of sides +6  \(entered\)", out), out
    assert "= 6·1.0000\n" in out and "6.0000·" not in out, "the work shows it whole"
    assert main(["run", "geometry.regular_polygon", "N=6", "a=1in", "--json"]) == 0
    sides = json.loads(capsys.readouterr().out)["inputs"]["sides"]
    assert sides == {**sides, "value": 6, "unit": "", "dimension": "count"}
    assert isinstance(sides["value"], int)
    assert main(["run", "geometry.regular_polygon", "N=600 %", "a=1in"]) != 0
    assert "is a ratio, but a count is expected" in capsys.readouterr().err


def test_a_count_runs_as_the_whole_number_it_is() -> None:
    result = RegularPolygon().run({"sides": parse_quantity("6", COUNT), "side": 1.0}, "side")
    assert result.to_dict()["inputs"]["sides"]["value"] == 6
    with pytest.raises(InputError, match=r"Number of sides \(N\) must be a whole number"):
        RegularPolygon().run({"sides": 6.5, "side": 1.0}, "side")


@pytest.mark.gui
@pytest.mark.usefixtures("qt")
def test_the_window_shows_a_count_whole_and_refuses_a_percent() -> None:
    window = open_window()
    window.select_calculator("geometry.regular_polygon")
    _param, sides = window.fields["sides"]
    assert sides.text() == "6"
    document = window.output.toPlainText()
    assert "6·" in document and "6.0" not in document.replace("6.0000 in", "")
    type_into(sides, "600 %")
    assert window._field_problem(_param, "600 %") == (
        "Number of sides: '600 %' is a ratio, but a count is expected"
    )
    assert window.result is None
    window.close()


@pytest.mark.parametrize("typed", ["9007199254740993", "9007199254740992", "-9007199254740993"])
def test_a_count_a_double_cant_hold_exactly_is_refused(typed: str) -> None:
    """2⁵³ + 1 reads as 2⁵³, so from 2⁵³ on a count can't be told from its neighbour."""
    with pytest.raises(InputError, match="too large a count to hold exactly"):
        parse_quantity(typed, COUNT)
    assert parse_quantity("9007199254740991", COUNT) == 2**53 - 1
    from caddcalc.core import Param

    param = Param("n", "N", "Number", COUNT, default="1")
    with pytest.raises(InputError, match=r"Number \(N\) must be under 2\^53"):
        param.check(float(2**53))
    param.check(float(2**53 - 1))
