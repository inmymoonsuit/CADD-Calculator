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
from tests.qt_helpers import open_window, pick, results_text, settle, show_in, type_into
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
    shown = results_text(window)
    assert "Material thickness: '25 mm' names a unit" in shown
    assert "Units go in the picker" not in shown, "the fix's sentence shows once, by the field"
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


def test_typing_a_mixed_number_key_by_key_never_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    """Every keystroke to 1-3/16 passes "1-", which once raised IndexError mid-typing."""
    import sys

    from PySide6.QtTest import QTest

    raised: list[BaseException] = []
    monkeypatch.setattr(sys, "excepthook", lambda _t, exc, _tb: raised.append(exc))
    window = open_window()
    window.select_calculator(BEND)
    edit = field(window, "thickness")
    edit.selectAll()
    QTest.keyClicks(edit, "1-3/16")
    assert raised == []
    assert window.result.inputs["thickness"] == 1.1875 * INCH
    assert edit.echo.text == "= 1 3/16 in"
    window.close()


@pytest.mark.parametrize(
    ("choice", "text"),
    [("in", "2 × 1 3/16 - (1/4 + .5)"), ("ft_in", "-10'-2 3/16\""), ("in", "12-1/2")],
)
def test_every_prefix_typed_into_a_field_reads_or_is_refused(
    monkeypatch: pytest.MonkeyPatch, choice: str, text: str
) -> None:
    import sys

    from PySide6.QtTest import QTest

    raised: list[BaseException] = []
    monkeypatch.setattr(sys, "excepthook", lambda _t, exc, _tb: raised.append(exc))
    window = open_window()
    window.select_calculator(BEND)
    if choice != "in":
        pick(window, "thickness", choice)
    edit = field(window, "thickness")
    for end in range(1, len(text) + 1):
        edit.selectAll()
        QTest.keyClicks(edit, text[:end])
        assert raised == [], text[:end]
    window.close()


def test_a_field_the_user_typed_in_never_follows_a_pick() -> None:
    """Typed in inches, T and R stay in inches when FVD is picked in mm (§3 as amended)."""
    window = open_window()
    window.select_calculator("sheet_metal.segment_flat_length")
    type_into(field(window, "thickness"), "0.06")
    type_into(field(window, "inside_radius"), "0.09")
    pick(window, "formed_dimension", "mm")
    assert window.pickers["thickness"].choice == window.pickers["inside_radius"].choice == "in"
    assert window.result.inputs["thickness"] == pytest.approx(0.06 * INCH)
    assert window.result.inputs["inside_radius"] == pytest.approx(0.09 * INCH)
    message = window.statusBar().currentMessage()
    assert (
        message.startswith("Formed view dimension: shown in millimeters")
        and "Lengths" not in message
    )
    window.close()


def test_only_fields_showing_a_value_the_user_didnt_type_follow() -> None:
    window = open_window()
    window.select_calculator("sheet_metal.segment_flat_length")
    type_into(field(window, "thickness"), "0.06")
    pick(window, "formed_dimension", "mm")
    assert window.pickers["thickness"].choice == "in"
    assert window.pickers["inside_radius"].choice == "mm", "its default, converted"
    assert (
        window.statusBar()
        .currentMessage()
        .endswith("Lengths now in millimeters: inside bend radius")
    )
    window.close()


def test_arrow_keys_step_a_closed_picker_and_follow_once_it_settles(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """From in to mm the steps pass ft-in and ft: the others follow only the settled mm."""
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest

    import caddcalc.gui.window as window_module

    said: list[str] = []
    monkeypatch.setattr(window_module, "announce", lambda _w, message: said.append(message))
    window = open_window()
    window.show()
    window.select_calculator(BEND)
    type_into(field(window, "thickness"), "25")
    picker = window.pickers["thickness"]
    picker.setFocus()
    steps = []
    for _ in range(3):
        QTest.keyClick(picker, Qt.Key.Key_Down)
        steps.append((picker.choice, window.result.inputs["thickness"]))
    assert steps == [("ft_in", 25 * INCH), ("ft", 25 * 304.8), ("mm", 25.0)], "re-read each step"
    assert said == [] and window.pickers["inside_radius"].choice == "in", "nothing follows yet"
    QTest.keyClick(picker, Qt.Key.Key_Return)
    assert window.pickers["inside_radius"].choice == "mm"
    assert said == [
        "Material thickness: 25 now read as millimeters. "
        "Lengths now in millimeters: inside bend radius"
    ]
    window.close()


def test_focus_leaving_a_stepped_picker_settles_it() -> None:
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication

    window = open_window()
    window.show()
    window.activateWindow()
    QApplication.processEvents()
    window.select_calculator(BEND)
    picker = window.pickers["thickness"]
    picker.setFocus()
    QApplication.processEvents()
    QTest.keyClick(picker, Qt.Key.Key_Down)
    QTest.keyClick(picker, Qt.Key.Key_Up)
    QTest.keyClick(picker, Qt.Key.Key_Tab)
    assert window.statusBar().currentMessage() == "", "back where it began: nothing settled"
    picker.setFocus()
    QApplication.processEvents()
    assert picker.hasFocus()
    QTest.keyClick(picker, Qt.Key.Key_Down)
    QTest.keyClick(picker, Qt.Key.Key_Tab)
    assert not picker.hasFocus()
    assert window.pickers["inside_radius"].choice == "ft_in"
    assert window.statusBar().currentMessage().startswith("Material thickness: shown in")
    window.close()


@pytest.mark.parametrize("scheme", ["light", "dark"])
def test_the_echo_is_secondary_text_with_at_least_4_5_to_1(scheme: str) -> None:
    """It's information, not a placeholder's hint (WCAG 1.4.3)."""
    from caddcalc.gui.style_tokens import palette_color
    from caddcalc.gui.ui_style import secondary_text, ui_style
    from tests.test_palette import contrast

    color = secondary_text(scheme)
    assert contrast(color, palette_color(ui_style().result_field.fill_role, scheme)) >= 4.5
    window = open_window()
    window.select_calculator(BEND)
    label = field(window, "thickness").echo_label
    assert label.styleSheet() == f"color: {secondary_text('light')};"
    window.close()


def test_a_picker_is_as_wide_as_its_widest_symbol_with_no_icons_room() -> None:
    from PySide6.QtCore import QSize
    from PySide6.QtWidgets import QStyle, QStyleOptionComboBox

    window = open_window()
    window.select_calculator(BEND)
    picker = window.pickers["thickness"]
    option = QStyleOptionComboBox()
    picker.initStyleOption(option)
    least = picker.style().sizeFromContents(
        QStyle.ContentsType.CT_ComboBox,
        option,
        QSize(picker.text_width, picker.fontMetrics().height()),
        picker,
    )
    assert picker.sizeHint().width() == least.width()
    widest = max(
        picker.fontMetrics().horizontalAdvance(p.itemText(i))
        for p in window.pickers.values()
        for i in range(p.count())
    )
    assert widest <= picker.text_width <= widest + 1, "the widest symbol, measured"
    window.close()


def test_a_bend_angle_is_picked_in_degrees_dms_or_radians() -> None:
    window = open_window()
    window.select_calculator(BEND)
    assert window.pickers["bend_angle"].choices == ("deg", "dms", "rad")
    window.close()


@pytest.mark.parametrize(
    ("calc_id", "key", "pick_first", "typed", "kept", "base"),
    [
        (BEND, "thickness", "mm", "25 mm", "25", 25.0),
        (BEND, "thickness", None, '1-3/16"', "1-3/16", 1.1875 * INCH),
        (BEND, "bend_angle", None, "45°", "45", 45.0),
        ("sheet_metal.v_die_opening", "radius_ratio", None, "44 %", "0.44", 0.44),
    ],
)
def test_the_fix_applies_the_number_when_the_unit_is_already_picked(
    calc_id: str, key: str, pick_first: str | None, typed: str, kept: str, base: float
) -> None:
    """Pasting 25 mm into a field already in mm is the natural paste from an mm drawing."""
    window = open_window()
    window.select_calculator(calc_id)
    if pick_first is not None:
        pick(window, key, pick_first)
    type_into(field(window, key), typed)
    window.unit_fixes[key][2].click()
    assert field(window, key).text() == kept
    assert window.result.inputs[key] == pytest.approx(base, rel=1e-15)
    window.close()


def test_a_pick_after_an_unfinished_keystroke_keeps_picker_and_reading_in_step(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import sys

    from PySide6.QtTest import QTest

    raised: list[BaseException] = []
    monkeypatch.setattr(sys, "excepthook", lambda _t, exc, _tb: raised.append(exc))
    window = open_window()
    window.select_calculator(BEND)
    edit = field(window, "thickness")
    edit.selectAll()
    QTest.keyClicks(edit, "1-")
    pick(window, "thickness", "mm")
    edit = field(window, "thickness")
    edit.selectAll()
    QTest.keyClicks(edit, "2")
    assert raised == []
    assert window.pickers["thickness"].choice == "mm"
    assert window.result.inputs["thickness"] == 2.0
    window.close()


def test_the_echo_names_the_fields_unit_and_goes_with_unreadable_text() -> None:
    window = open_window()
    window.select_calculator(BEND)
    pick(window, "thickness", "mm")
    edit = field(window, "thickness")
    type_into(edit, "1/2")
    assert edit.echo.text == "= 1/2 mm"
    type_into(edit, "0.25")
    assert edit.echo is None, "a plain decimal has none, though it isn't the default"
    type_into(edit, "1-3/16")
    type_into(edit, "1-3/16x")
    assert edit.echo is None and window.result is None, "no echo of text that isn't read"
    window.close()


def test_an_announcement_says_unreadable_text_isnt_read_and_names_shown_fields_only() -> None:
    window = open_window()
    window.select_calculator(BEND)
    type_into(field(window, "thickness"), "abc")
    pick(window, "thickness", "mm")
    assert (
        window.statusBar()
        .currentMessage()
        .startswith("Material thickness: abc can't be read in millimeters")
    )
    window.select_calculator(RIGHT)
    window.method_box.setCurrentIndex(window.method_box.findData("legs"))
    pick(window, "leg_a", "mm")
    message = window.statusBar().currentMessage()
    assert message.endswith("Lengths now in millimeters: leg b"), message
    window.method_box.setCurrentIndex(window.method_box.findData("leg_hypotenuse"))
    assert window.pickers["hypotenuse"].choice == "mm", "hidden, it followed all the same"
    window.close()


def test_a_pick_keeps_the_undo_of_the_fields_it_didnt_change() -> None:
    window = open_window()
    window.select_calculator(BEND)
    type_into(field(window, "inside_radius"), "0.2")
    assert field(window, "inside_radius").isUndoAvailable()
    pick(window, "thickness", "mm")
    assert window.pickers["inside_radius"].choice == "in", "typed in, so set"
    assert field(window, "inside_radius").isUndoAvailable()
    window.close()


def test_the_inputs_are_shown_in_each_field_s_choice_not_the_results_units() -> None:
    """The Inputs block says each input as its field reads it (ADR-0024 E4)."""
    window = open_window()
    window.select_calculator(BEND)
    show_in(window, "mm")
    pick(window, "thickness", "in")  # the first pick leads the untouched fields
    pick(window, "bend_angle", "rad")
    text = window.output.toPlainText()
    inputs = text[text.index("Inputs") : text.index("Work")]
    assert "Material thickness\n0.1046\nin" in inputs
    assert "Bend angle\n1.5708\nrad" in inputs, "a radian to its own four places"
    assert "BA Bend allowance" in results_text(window) and "mm" in results_text(window)
    window.close()


def test_a_range_error_names_the_bound_in_the_field_s_choice() -> None:
    """The user types in the field's unit, so its bound is in that unit too."""
    window = open_window()
    window.select_calculator(BEND)
    show_in(window, "mm")
    pick(window, "bend_angle", "rad")
    type_into(field(window, "bend_angle"), "4")
    assert "must be less than 3.14159 rad" in window.output.toPlainText()
    pick(window, "bend_angle", "deg")
    type_into(field(window, "bend_angle"), "200")
    assert "must be less than 180°" in window.output.toPlainText()
    window.close()


def test_opening_a_stepped_picker_s_list_settles_nothing() -> None:
    """The list takes the focus before anything is chosen, so no step leads (M-B)."""
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication

    window = open_window()
    window.show()
    window.activateWindow()
    QApplication.processEvents()
    window.select_calculator(BEND)
    picker = window.pickers["thickness"]
    picker.setFocus()
    QApplication.processEvents()
    QTest.keyClick(picker, Qt.Key.Key_Down)  # in → ft-in, a step
    picker.showPopup()
    QApplication.processEvents()
    assert window.pickers["inside_radius"].choice == "in", "the step didn't lead"
    assert window.statusBar().currentMessage() == ""
    index = picker.choices.index("mm")
    picker.setCurrentIndex(index)
    picker.activated.emit(index)
    picker.hidePopup()
    QApplication.processEvents()
    assert window.pickers["inside_radius"].choice == "mm", "the choice made in the list leads"
    window.close()


@pytest.mark.parametrize("text", ["", "-", "+", "−", "40-", "40-30-", "40°-30′"])
def test_a_dms_field_refuses_text_with_no_number_or_a_stray_hyphen(text: str) -> None:
    """A bend angle left at "-" mustn't run at 0° (M-A)."""
    from caddcalc.core import InputError, TypedValue

    with pytest.raises(InputError):
        TypedValue.read(text, "dms", Dimension.ANGLE)


def test_a_bend_angle_left_at_a_sign_runs_nothing() -> None:
    window = open_window()
    window.select_calculator(BEND)
    pick(window, "bend_angle", "dms")
    type_into(field(window, "bend_angle"), "-", enter=False)
    assert window.result is None
    assert "ends before its last number" in window.output.toPlainText()
    window.close()
