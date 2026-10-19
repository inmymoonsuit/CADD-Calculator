"""Each input's unit picker, and the echo of what its text reads as (ADR-0024 U1).

The picker is the field's one unit author: a number is read in it, a unit typed into the
text is refused with its fix, and the field shows what arithmetic or a form read as.
"""

from __future__ import annotations

from itertools import pairwise
from pathlib import Path
from typing import Any

import pytest

from caddcalc.calculators import default_registry
from caddcalc.core import Dimension, i18n
from tests import pseudo_locale
from tests.qt_helpers import open_window, pick, results_text, settle, type_into
from tests.test_translated_gui import _clipped, _rows

pytestmark = [pytest.mark.gui, pytest.mark.usefixtures("qt")]

BEND = "sheet_metal.bend_allowance"
RIGHT = "geometry.right_triangle"
INCH = 25.4


def field(window: Any, key: str) -> Any:
    return window.fields[key][1]


def pages() -> list[tuple[str, str]]:
    """Every built-in calculator and method."""
    return [(c.id, m.key) for c in default_registry(load_plugins=False) for m in c.methods]


@pytest.mark.parametrize(("calc_id", "method"), pages())
def test_every_input_with_a_unit_has_a_picker_and_a_unitless_one_none(
    calc_id: str, method: str
) -> None:
    """Its choices are its parameter's, in a picker's order, starting at its default."""
    window = open_window()
    window.select_calculator(calc_id)
    window.method_box.setCurrentIndex(window.method_box.findData(method))
    for key, (p, _edit) in window.fields.items():
        picker = window.pickers.get(key)
        if p.dimension in (Dimension.RATIO, Dimension.COUNT):
            assert picker is None, key
            continue
        assert picker is not None, key
        assert picker.choices == p.choices and picker.choice == p.default_choice
        assert picker.accessibleName() == f"{p.label} unit"
    window.close()


def test_the_pickers_on_a_page_share_one_width_that_holds_the_widest_choice() -> None:
    """The bend's lengths and its angle stand in one column (ADR-0024 §1)."""
    from PySide6.QtGui import QFontMetricsF

    window = open_window()
    window.show()
    window.select_calculator(BEND)
    settle(window)
    pickers = list(window.pickers.values())
    widths = {picker.width() for picker in pickers}
    assert len(pickers) == 3 and len(widths) == 1, widths
    metrics = QFontMetricsF(pickers[0].font())
    widest = max(
        metrics.horizontalAdvance(p.itemText(i)) for p in pickers for i in range(p.count())
    )
    assert widest < widths.pop()
    window.method_box.setCurrentIndex(window.method_box.findData("k_factor"))
    settle(window)
    ends = {
        field(window, key).mapTo(window, field(window, key).rect().topRight()).x()
        for key in window.fields
    }
    assert len(ends) == 1, "a unitless K field ends where a picker would begin"
    window.close()


def test_a_pickers_list_shows_the_symbol_and_name_and_it_says_the_name() -> None:
    from PySide6.QtWidgets import QStyleOptionViewItem

    window = open_window()
    window.select_calculator(BEND)
    picker = window.pickers["thickness"]
    assert [picker.itemText(i) for i in range(picker.count())] == [
        "in",
        "ft-in",
        "ft",
        "mm",
        "cm",
        "m",
    ]
    option = QStyleOptionViewItem()
    picker.itemDelegate().initStyleOption(option, picker.model().index(3, 0))
    assert option.text == "mm — millimeters"
    assert picker.accessibleDescription() == "inches"
    pick(window, "thickness", "mm")
    assert window.pickers["thickness"].accessibleDescription() == "millimeters"
    assert window.pickers["bend_angle"].itemText(0) == "°"
    window.close()


def test_tab_goes_from_each_field_to_its_picker() -> None:
    window = open_window()
    window.select_calculator(BEND)
    stops = [s for k, (_p, e) in window.fields.items() for s in (e, window.pickers[k])]
    for before, after in pairwise(stops):
        assert before.nextInFocusChain() is after or _skips_to(before, after)
    window.close()


def _skips_to(before: Any, after: Any) -> bool:
    """Whether Tab from ``before`` reaches ``after`` next, past widgets that take no Tab."""
    from PySide6.QtCore import Qt

    widget = before.nextInFocusChain()
    while widget is not after and widget is not before:
        takes = bool(widget.focusPolicy() & Qt.FocusPolicy.TabFocus) and widget.isVisibleTo(
            before.window()
        )
        if takes:
            return False
        widget = widget.nextInFocusChain()
    return widget is after


def test_a_family_value_and_a_course_example_are_converted_by_a_pick() -> None:
    """Neither was typed in the field, so each keeps its quantity (ADR-0013 §9 rule 2)."""
    window = open_window()
    window.select_domain("sheet_metal")
    type_into(window.setting_fields["thickness"][1], "0.25")
    window.select_calculator(BEND)
    pick(window, "thickness", "mm")
    assert field(window, "thickness").text() == "6.35"
    assert window.result.inputs["thickness"] == pytest.approx(0.25 * INCH)
    assert (
        window.statusBar()
        .currentMessage()
        .startswith("Material thickness: shown in millimeters, 6.35")
    )
    window.method_box.setCurrentIndex(window.method_box.findData("k_factor"))
    window.load_course_example()
    assert field(window, "thickness").text() == "2.65684", "the course's 0.1046 in"
    assert window.result.inputs["thickness"] == pytest.approx(0.1046 * INCH)
    pick(window, "thickness", "in")
    assert field(window, "thickness").text() == "0.1046"
    window.close()


def test_each_pick_is_announced_to_screen_readers(monkeypatch: pytest.MonkeyPatch) -> None:
    import caddcalc.gui.window as window_module

    said: list[str] = []
    monkeypatch.setattr(window_module, "announce", lambda _widget, message: said.append(message))
    window = open_window()
    window.select_calculator(BEND)
    type_into(field(window, "thickness"), "25")
    pick(window, "thickness", "mm")
    assert said == [
        "Material thickness: 25 now read as millimeters. "
        "Lengths now in millimeters: inside bend radius"
    ]
    assert said[-1] == window.statusBar().currentMessage()
    window.close()


def test_follow_until_set_carries_the_first_pick_to_untouched_pickers_only() -> None:
    """A segment drawn in mm takes one change, not three (ADR-0024 Q6)."""
    window = open_window()
    window.select_calculator("sheet_metal.segment_flat_length")
    lengths = [k for k, (p, _e) in window.fields.items() if p.dimension is Dimension.LENGTH]
    assert len(lengths) >= 3
    first, second, *rest = lengths
    pick(window, second, "cm")  # the user's own: the first pick; the others follow it
    assert {window.pickers[k].choice for k in [first, *rest]} == {"cm"}
    pick(window, first, "mm")  # after the first, each picker is the user's
    assert window.pickers[first].choice == "mm"
    assert {window.pickers[k].choice for k in [second, *rest]} == {"cm"}
    assert window.pickers["bend_angle_1"].choice == "deg", "another dimension's own"
    window.close()


def test_after_the_first_pick_no_picker_follows_another() -> None:
    """One that already showed the first pick's unit didn't move, and stays the user's."""
    from caddcalc.core import Calculator, Method, Output, Param, Registry, Verification
    from tests.test_domains import ACME

    class Three(Calculator):
        id = "acme.three"
        name = "Three"
        domain = "acme"
        summary = "Three lengths."
        params = tuple(
            Param(key, key.upper(), key.title(), Dimension.LENGTH, default=default)
            for key, default in (("a", "1 in"), ("b", "1 in"), ("c", "25 mm"))
        )
        outputs = (Output("total", "T", "Total", Dimension.LENGTH),)
        methods = (Method("only", "Only", "T = A + B + C", Verification.UNVERIFIED),)

        def compute(self, ctx: Any) -> None:
            ctx.calc("T", "A + B + C", label="Total", dimension=Dimension.LENGTH, output="total")

    registry = Registry()
    registry.register_domain(ACME)
    registry.register(Three)
    window = open_window(registry)
    window.select_calculator("acme.three")
    pick(window, "a", "mm")
    assert [window.pickers[k].choice for k in "abc"] == ["mm", "mm", "mm"]
    pick(window, "b", "cm")
    assert [window.pickers[k].choice for k in "abc"] == ["mm", "cm", "mm"]
    window.close()


def test_a_unit_in_the_text_is_refused_and_its_fix_offered() -> None:
    """Nothing is misread as 25 in; the user's click moves the unit to the picker (Q5)."""
    window = open_window()
    window.select_calculator(BEND)
    type_into(field(window, "thickness"), "25 mm")
    assert window.result is None
    assert "Material thickness: Units go in the picker. Use 25 mm?" in results_text(window)
    row, note, button = window.unit_fixes["thickness"]
    assert not row.isHidden() and button.text() == "Use 25 mm"
    assert note.text() == "Units go in the picker. Use 25 mm?"
    button.click()
    assert (field(window, "thickness").text(), window.pickers["thickness"].choice) == ("25", "mm")
    assert window.result.inputs["thickness"] == 25.0
    assert window.unit_fixes["thickness"][0].isHidden()
    window.close()


def test_a_unit_of_another_dimension_is_refused_with_no_offer() -> None:
    window = open_window()
    window.select_calculator(BEND)
    type_into(field(window, "thickness"), "25 MPa")
    assert "'25 MPa' is a stress, but a length is expected" in results_text(window)
    assert window.unit_fixes["thickness"][0].isHidden()
    window.close()


def test_feet_and_inches_read_with_their_marks_in_an_ft_in_field() -> None:
    window = open_window()
    window.select_calculator(BEND)
    pick(window, "thickness", "ft_in")
    type_into(field(window, "thickness"), "1'-4 3/16\"")
    assert window.result.inputs["thickness"] == 16.1875 * INCH
    assert field(window, "thickness").echo is None, "the form as shown needs no echo"
    window.close()


@pytest.mark.parametrize(
    ("choice", "text", "shown", "spoken"),
    [
        ("in", "1-3/16", "= 1 3/16 in", "reads as 1 and 3 sixteenths inches"),
        ("in", "1 - 3/16", "= 0.8125 in", "reads as 0.8125 inches"),
        ("in", "2 × 1 3/16", "= 2.375 in", "reads as 2.375 inches"),
        ("ft_in", "10", "= 0'-10\"", "reads as 10 inches"),
        ("ft_in", "10-2", "= 10'-2\"", "reads as 10 feet 2 inches"),
        ("in", "0.1046", None, ""),
    ],
)
def test_the_echo_says_what_the_text_reads_as(
    choice: str, text: str, shown: str | None, spoken: str
) -> None:
    """D7's hyphen is where the echo matters: 1-3/16 and 1 - 3/16 differ by a space (D8)."""
    window = open_window()
    window.show()
    window.select_calculator(BEND)
    settle(window)
    if choice != "in":
        pick(window, "thickness", choice)
    edit = field(window, "thickness")
    type_into(edit, text)
    if shown is None:
        assert edit.echo is None and not edit.echo_shown
        assert edit.accessibleDescription() == ""
    else:
        assert edit.echo.text == shown and edit.echo_shown
        assert edit.echo_label.text() == shown
        assert edit.accessibleDescription() == spoken
        assert edit.toolTip().endswith(f"\n{shown}")
    window.close()


def test_the_echo_hides_when_there_is_no_room_and_stays_in_the_tooltip() -> None:
    window = open_window()
    window.show()
    window.select_calculator(BEND)
    settle(window)
    edit = field(window, "thickness")
    type_into(edit, "1-3/16")
    assert edit.echo_shown
    edit.setFixedWidth(edit.fontMetrics().horizontalAdvance("1-3/16 = 1 3/16") // 2)
    settle(window)
    assert not edit.echo_shown and edit.echo_label.isHidden()
    assert "= 1 3/16 in" in edit.toolTip()
    assert edit.accessibleDescription() == "reads as 1 and 3 sixteenths inches"
    window.close()


def test_an_angle_field_picks_degrees_minutes_and_seconds() -> None:
    window = open_window()
    window.select_calculator(RIGHT)
    window.method_box.setCurrentIndex(window.method_box.findData("leg_angle"))
    pick(window, "angle_a", "dms")
    type_into(field(window, "angle_a"), "30 30")
    assert window.result.inputs["angle_a"] == 30.5
    assert field(window, "angle_a").echo.text == "= 30°30′0.00″"
    window.close()


def _in(language: str, folder: Path) -> None:
    i18n.use([language] if language else [], directories=[pseudo_locale.write(folder)])


@pytest.mark.parametrize("language", ["", pseudo_locale.LANGUAGE])
def test_nothing_clips_at_the_launch_size(tmp_path: Path, language: str) -> None:
    """Every calculator page as the window opens; the least size is the translated GUI's.

    A settings page is left out: the check measures a group box's least height at its
    least width, where its labels wrap most, so at the launch width it reports one that
    fits (ADR-0024's U1 amendment).
    """
    from caddcalc.gui.window import ID_ROLE

    _in(language, tmp_path)
    window = open_window()
    window.show()
    for row in _rows(window):
        if not row.flags() or row.data(0, ID_ROLE) is None:
            continue
        window.tree.setCurrentItem(row)
        launch = window.launch_size()
        window.resize(round(launch.width), round(launch.height))
        settle(window)
        assert _clipped(window) == [], row.text(0)
    window.close()
