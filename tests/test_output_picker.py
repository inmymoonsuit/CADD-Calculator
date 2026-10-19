"""The results' output picker, "Show in:", in place of the Units box (ADR-0024 §5, U2)."""

from __future__ import annotations

from typing import Any

import pytest

from caddcalc.calculators import default_registry
from caddcalc.core import Calculator, Dimension, Method, Output, Param, Registry, Verification
from tests.qt_helpers import open_window, pick, settle, show_in, type_into

pytestmark = [pytest.mark.gui, pytest.mark.usefixtures("qt")]

BEND = "sheet_metal.bend_allowance"
RIGHT = "geometry.right_triangle"
L = Dimension.LENGTH


class _Mixed(Calculator):
    """A length doubled: in the set, in a fixed unit, and with its own picker."""

    id = "acme.mixed"
    name = "Mixed"
    domain = "acme"
    summary = "A length, three ways."
    params = (Param("length", "X", "Length", L, default="1 in"),)
    outputs = (
        Output("double", "Y", "Double", L),
        Output("fixed", "W", "Fixed", L, unit="mm"),
        Output("own", "Z", "Own", L, picks=("in", "cm")),
    )
    methods = (Method("only", "Only", "Y = 2 × X", Verification.UNVERIFIED),)

    def compute(self, ctx: Any) -> None:
        ctx.calc("Y", "2 * X", label="Double", dimension=L, output="double")
        ctx.calc("W", "2 * X", label="Fixed", dimension=L, output="fixed")
        ctx.calc("Z", "2 * X", label="Own", dimension=L, output="own")


class _Two(Calculator):
    """One length in one method, two in the other."""

    id = "acme.two"
    name = "Two"
    domain = "acme"
    summary = "One length or two."
    params = (
        Param("x", "X", "X", L, default="1 in"),
        Param("y", "Y", "Y", L, default="1 in", methods=("both",)),
    )
    outputs = (Output("total", "T", "Total", L),)
    methods = (
        Method("both", "Both", "T = X + Y", Verification.UNVERIFIED),
        Method("one", "One", "T = X", Verification.UNVERIFIED),
    )

    def compute(self, ctx: Any) -> None:
        if ctx.method == "both":
            ctx.calc("T", "X + Y", label="Total", dimension=L, output="total")
        else:
            ctx.calc("T", "X", label="Total", dimension=L, output="total")


def _acme_window(calc_id: str) -> Any:
    from tests.test_domains import ACME

    registry = Registry()
    registry.register_domain(ACME)
    registry.register(_Mixed)
    registry.register(_Two)
    window = open_window(registry)
    window.select_calculator(calc_id)
    return window


def _mixed_window() -> Any:
    return _acme_window(_Mixed.id)


def _shown(window: Any, key: str) -> str:
    field = window.results.fields[key]
    return f"{field.value.text()} {field.unit.text()}".strip()


def test_there_is_no_units_box() -> None:
    window = open_window()
    assert not hasattr(window, "units_box") and not hasattr(window, "_on_units_changed")
    assert not hasattr(window, "_name_pending_units")
    window.close()


def test_the_picker_is_named_results_units_and_labelled_show_in() -> None:
    window = open_window()
    window.select_calculator(BEND)
    picker = window.results.set_picker
    assert picker.accessibleName() == "Results units"
    assert window.results.show_in.text() == "Show in:" and window.results.show_in.buddy() is picker
    labels = [picker.itemText(i) for i in range(picker.count())]
    assert labels[:2] == ["in", "in 1/16"] and labels[-1] == "m", "one set per length choice"
    window.select_calculator(RIGHT)
    assert window.results.set_picker.itemText(0) == "in · ° · in²"
    window.close()


def test_a_set_changes_every_field_its_copy_its_speech_and_the_work_together() -> None:
    from PySide6.QtGui import QGuiApplication

    window = open_window()
    window.select_calculator(BEND)
    show_in(window, "mm")
    field = window.results.fields["bend_allowance"]
    assert (field.value.text(), field.unit.text()) == ("7.9213", "mm")
    assert "millimeters" in field.accessibleName()
    field.copy_button.click()
    assert QGuiApplication.clipboard().text() == "7.9213"
    tsv = window.results.copy_all()
    assert tsv is not None and tsv.splitlines()[0] == "BA\tBend allowance\t7.9213\tmm"
    text = window.output.toPlainText()
    work = text[text.index("Work") :]
    assert "mm" in work and " in\n" not in work, "the work is in the set's units"
    inputs = text[text.index("Inputs") : text.index("Work")]
    assert "0.1046\nin\n= 2.6568 mm" in inputs, "an input as typed, then in the set's units"

    show_in(window, "in_16")
    assert _shown(window, "bend_allowance") == '5/16"'
    show_in(window, "in")
    assert _shown(window, "bend_allowance") == "0.3119 in"
    assert "= 2.6568 mm" not in window.output.toPlainText(), "no second value in the same unit"
    window.close()


def _inputs(window: Any) -> str:
    text = window.output.toPlainText()
    return text[text.index("Inputs") : text.index("Work")]


@pytest.mark.parametrize("key", ["in_16", "in_64", "ft_in"])
def test_a_set_in_an_inch_form_gives_inch_fields_no_second_value(key: str) -> None:
    """``T 0.1046 in = 1/8"`` would be false: the form's unit is the field's (review M2)."""
    window = open_window()
    window.select_calculator(BEND)
    type_into(window.fields["inside_radius"][1], "0.03")
    show_in(window, key)
    assert "=" not in _inputs(window)
    window.close()


def test_a_form_never_stands_for_an_input_it_rounds() -> None:
    """In mm fields an ft-in set gives 0.1046 in, not ``= 0'-0 1/8"``; an exact 1/8" is one."""
    window = open_window()
    window.select_calculator(BEND)
    pick(window, "thickness", "mm")
    show_in(window, "ft_in")
    type_into(window.fields["inside_radius"][1], "3.175")
    inputs = _inputs(window)
    assert "2.6568\nmm\n= 0.1046 in" in inputs
    assert "3.1750\nmm\n= 0'-0 1/8\"" in inputs, "exactly 1/8 in"
    window.close()


def test_a_calculator_with_no_sets_gives_no_second_value() -> None:
    """Its inputs aren't in a set the user can see (review L1)."""
    window = open_window()
    for calc_id, choice in (("conversions.length", "cm"), ("conversions.stress", "MPa")):
        window.select_calculator(calc_id)
        pick(window, "value", choice)
        assert "=" not in _inputs(window), calc_id
    window.close()


def test_the_set_follows_the_length_fields_until_it_is_picked() -> None:
    window = open_window()
    window.select_calculator(BEND)
    assert window.results.set_key == "in"
    pick(window, "thickness", "mm")  # the first pick leads the untouched fields (§3)
    assert window.results.set_key == "mm"
    assert _shown(window, "bend_allowance") == "7.9213 mm"
    pick(window, "inside_radius", "cm")
    assert window.results.set_key == "mm", "two choices: the set it last followed"
    pick(window, "thickness", "cm")
    assert window.results.set_key == "cm"

    show_in(window, "ft_in")
    pick(window, "thickness", "in")
    pick(window, "inside_radius", "in")
    assert window.results.set_key == "ft_in", "once picked, it's the user's"
    window.select_calculator(RIGHT)
    window.select_calculator(BEND)
    assert window.results.set_key == "ft_in", "for the session"
    window.close()


def test_changing_the_method_never_moves_the_set() -> None:
    window = open_window()
    window.select_calculator(BEND)
    pick(window, "thickness", "cm")
    for index in range(window.method_box.count()):
        window.method_box.setCurrentIndex(index)
        assert window.results.set_key == "cm", window.method_key
    window.close()


def test_the_set_follows_the_method_s_length_fields_only() -> None:
    """Y, typed in mm but hidden by a method without it, doesn't hold the set in mm."""
    window = _acme_window(_Two.id)
    pick(window, "x", "mm")
    assert window.results.set_key == "mm", "Y followed X's first pick"
    pick(window, "x", "in")
    assert window.results.set_key == "mm", "two choices: the set it last followed"
    window.method_box.setCurrentIndex(window.method_box.findData("one"))
    assert window.method_key == "one" and "y" not in window.fields
    assert window.results.set_key == "in", "X alone is shown, in inches"
    window.method_box.setCurrentIndex(window.method_box.findData("both"))
    assert window.results.set_key == "in", "and disagreeing again keeps it"
    window.close()


def test_the_set_followed_last_is_kept_per_calculator() -> None:
    window = open_window()
    window.select_calculator(BEND)
    pick(window, "thickness", "cm")
    pick(window, "inside_radius", "mm")
    window.select_calculator(RIGHT)
    assert window.results.set_key == "in", "another calculator follows its own fields"
    window.select_calculator(BEND)
    assert window.results.set_key == "cm"
    window.close()


def test_a_fixed_unit_output_ignores_the_set_and_its_own_picker_sits_in_its_row() -> None:
    window = _mixed_window()
    own = window.results.fields["own"]
    assert own.picker is not None and own.unit.isHidden()
    assert own.picker.accessibleName() == "Own unit"
    assert own.picker.choices == ("in", "cm")
    assert (_shown(window, "double"), _shown(window, "fixed")) == ("2.0000 in", "50.8000 mm")
    assert own.value.text() == "2.0000"
    show_in(window, "m")
    assert (_shown(window, "double"), _shown(window, "fixed")) == ("0.0508 m", "50.8000 mm")
    assert own.value.text() == "2.0000", "its own picker, not the set"
    pick_own = own.picker
    pick_own.setCurrentIndex(1)
    pick_own.activated.emit(1)
    own = window.results.fields["own"]
    assert own.value.text() == "5.0800" and own.picker.choice == "cm"
    assert _shown(window, "double") == "0.0508 m", "only that output"
    tsv = window.results.copy_all()
    assert tsv is not None and tsv.splitlines()[2] == "Z\tOwn\t5.0800\tcm"
    window.select_calculator(_Two.id)
    window.select_calculator(_Mixed.id)
    own = window.results.fields["own"]
    assert own.picker is not None and own.picker.choice == "cm", "for the session"
    assert own.value.text() == "5.0800"
    window.close()


def test_the_picker_hides_for_a_calculator_with_no_sets() -> None:
    window = open_window()
    window.select_calculator("conversions.length")
    assert window.results.set_picker.isHidden() and window.results.show_in.isHidden()
    assert window.results.set_picker not in window.results.focus_chain()
    window.select_calculator(BEND)
    assert not window.results.set_picker.isHidden()
    assert window.results.focus_chain()[0] is window.results.set_picker
    window.close()


def test_at_the_least_width_the_picker_goes_under_the_title_and_nothing_clips() -> None:
    from tests.test_translated_gui import _clipped

    window = open_window()
    window.select_calculator(RIGHT)
    window.resize(1400, 900)
    window.show()
    settle(window)
    header = window.results.header
    assert not header.stacked, "beside the title at a wide window"
    window.resize(1, 1)
    settle(window)
    picker, title = window.results.set_picker, window.results.title
    assert header.stacked == (header.width() < header.row_width())
    if header.stacked:
        assert (
            picker.mapTo(window, picker.rect().topLeft()).y()
            > title.mapTo(window, title.rect().bottomLeft()).y()
        )
    assert [w for w in _clipped(window) if w in (picker, title, window.results.show_in)] == []
    window.close()


@pytest.mark.parametrize("calc_id", [c.id for c in default_registry(load_plugins=False)])
def test_the_header_keeps_its_height_without_the_picker(calc_id: str) -> None:
    """The picker fits the title's and Copy all's row, so no page grows (UI/UX's M1)."""
    window = open_window()
    window.select_calculator(calc_id)
    window.resize(1400, 900)
    window.show()
    settle(window)
    panel = window.results
    line = max(panel.title.sizeHint().height(), panel.copy_all_button.sizeHint().height())
    assert not panel.header.stacked
    assert panel.header.height() == line
    picker = panel.set_picker
    if picker.isHidden():
        return  # a calculator with no sets has no picker to fit, and lays none out
    assert picker.height() <= line
    assert picker.height() >= picker.fontMetrics().height(), "its text still fits"
    window.close()


def _wheel(widget: Any) -> None:
    from PySide6.QtCore import QPoint, QPointF, Qt
    from PySide6.QtGui import QWheelEvent
    from PySide6.QtWidgets import QApplication

    centre = QPointF(widget.rect().center())
    event = QWheelEvent(
        centre,
        QPointF(widget.mapToGlobal(centre.toPoint())),
        QPoint(0, 0),
        QPoint(0, -120),
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier,
        Qt.ScrollPhase.NoScrollPhase,
        False,
    )
    QApplication.sendEvent(widget, event)


def test_the_wheel_never_changes_the_results_units() -> None:
    """A wheel step over Show in once went from in to in 1/16 (UI/UX's M2)."""
    window = _mixed_window()
    window.show()
    settle(window)
    _wheel(window.results.set_picker)
    assert window.results.set_key == "in" and window.results.set_picker.currentIndex() == 0
    own = window.results.fields["own"].picker
    assert own is not None
    _wheel(own)
    assert own.choice == "in"
    assert window.results.fields["own"].value.text() == "2.0000"
    window.close()


def test_each_set_is_named_in_its_list_and_said_by_its_name() -> None:
    """As a field's picker is (Q3): "in 1/16 — inches, nearest 1/16; …"."""
    from caddcalc.gui.unit_picker import NAME_ROLE

    window = open_window()
    window.select_calculator(RIGHT)
    picker = window.results.set_picker
    index = picker.findData("in_16")
    assert picker.itemText(index) == "in 1/16 · ° · in²"
    assert picker.itemData(index, NAME_ROLE) == "inches, nearest 1/16; degrees; square inches"
    show_in(window, "in_16")
    assert picker.accessibleDescription() == "inches, nearest 1/16; degrees; square inches"
    assert picker.toolTip() == picker.accessibleDescription()
    window.select_calculator(BEND)
    assert window.results.set_picker.accessibleDescription() == "inches"
    window.close()


def test_show_in_and_its_name_are_translated(tmp_path: Any) -> None:
    from caddcalc.core import i18n
    from tests import pseudo_locale

    i18n.use([pseudo_locale.LANGUAGE], directories=[pseudo_locale.write(tmp_path)])
    try:
        window = open_window()
        window.select_calculator(BEND)
        assert window.results.show_in.text().startswith("⟦")
        assert window.results.set_picker.accessibleName().startswith("⟦")
        window.close()
    finally:
        i18n.use([])


def test_a_picker_taller_than_the_row_doesn_t_grow_the_header() -> None:
    """Natively a picker is 26 px, a field's height, and the row 24 (UI/UX's M1).

    Padding it here makes it taller than the row offscreen too, as it is natively.
    """
    window = open_window()
    window.select_calculator("sheet_metal.segment_flat_length")
    panel = window.results
    window.resize(1400, 900)
    window.show()
    settle(window)
    before = panel.header.height()
    panel.set_picker.setStyleSheet("QComboBox { padding: 6px; }")
    from PySide6.QtWidgets import QComboBox

    assert QComboBox.sizeHint(panel.set_picker).height() > before, "it is taller"
    settle(window)
    assert panel.header.height() == before
    window.close()


def test_the_picker_never_narrows_past_its_longest_label() -> None:
    """A squeezed picker clipped its label at the least window on Windows (CI at 6d859c6)."""
    window = open_window()
    window.select_calculator(RIGHT)
    picker = window.results.set_picker
    assert picker.minimumSizeHint().width() == picker.sizeHint().width()
    longest = max(
        picker.fontMetrics().horizontalAdvance(picker.itemText(i)) for i in range(picker.count())
    )
    assert picker.sizeHint().width() > longest
    window.close()


def test_the_user_s_set_is_for_that_calculator_only() -> None:
    window = open_window()
    window.select_calculator(BEND)
    show_in(window, "mm")
    window.select_calculator(RIGHT)
    assert window.results.set_key == "in"
    window.select_calculator(BEND)
    assert window.results.set_key == "mm"
    window.close()


def test_an_output_s_own_picker_steps_by_its_arrow_keys() -> None:
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest

    window = _mixed_window()
    picker = window.results.fields["own"].picker
    picker.setFocus()
    QTest.keyClick(picker, Qt.Key.Key_Down)
    own = window.results.fields["own"]
    assert own.picker.choice == "cm" and own.value.text() == "5.0800"
    window.close()


def test_a_failed_run_still_shows_the_set_followed() -> None:
    """The set follows a pick made while the run fails, and the picker shows it."""
    window = open_window()
    window.select_calculator(BEND)
    type_into(window.fields["thickness"][1], "abc")
    pick(window, "inside_radius", "mm")
    pick(window, "thickness", "mm")
    assert window.result is None
    assert window.results.set_key == "mm"
    assert window.results.set_picker.currentData() == "mm"
    window.close()
