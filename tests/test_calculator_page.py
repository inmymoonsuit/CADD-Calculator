"""Calculator pages: inheriting and overriding family settings, and numeric intent.

ADR-0013 §8 and §9, decisions C and D. Skipped when PySide6 is not installed.
"""

from __future__ import annotations

from typing import Any

import pytest

from caddcalc.core import Dimension, TypedValue
from tests.qt_helpers import open_window, page_text, results_text, type_into

pytestmark = [pytest.mark.gui, pytest.mark.usefixtures("qt")]

BEND = "sheet_metal.bend_allowance"
CONE = "sheet_metal.truncated_cone_layout"
INCH = 25.4


def set_family(window: Any, key: str, text: str) -> None:
    """Set a Sheet Metal value on its settings page, as a user does."""
    window.select_domain("sheet_metal")
    type_into(window.setting_fields[key][1], text)


def result(window: Any) -> str:
    return results_text(window)


def source_of(window: Any, key: str) -> str:
    from caddcalc.core.formatting import describe_source

    return describe_source(window.result.source_of(key))


def field(window: Any, key: str) -> Any:
    return window.fields[key][1]


def test_an_inherited_value_reaches_the_result_and_is_read_only() -> None:
    window = open_window()
    set_family(window, "thickness", "0.25")
    window.select_calculator(BEND)
    window.method_box.setCurrentIndex(window.method_box.findData("course"))

    thickness = field(window, "thickness")
    assert thickness.text() == "0.25"
    assert thickness.isReadOnly(), "only unticking overrides (decision C)"
    box = window.inherit_boxes["thickness"]
    assert not box.isHidden() and box.isChecked()
    assert "0.4049 in" in result(window), "BA with T = 0.25 in, R = 0.156 in"
    assert "Material thickness\n0.2500\nin\nSheet Metal settings" in result(window)
    assert "Inside bend radius\n0.1560\nin\ndefault" in result(window)

    type_into(thickness, "9", enter=False)
    assert thickness.text() == "0.25"
    assert source_of(window, "thickness") == "Sheet Metal settings"
    window.close()


def overrides_radius(window: Any) -> bool:
    return "inside_radius" in window.overrides.get(BEND, set()) or (
        "inside_radius" in window.entries.get(BEND, {})
    )


def then_family_radius_flows_through(window: Any) -> None:
    set_family(window, "inside_radius", "0.3")
    window.select_calculator(BEND)
    assert source_of(window, "inside_radius") == "Sheet Metal settings"
    assert window.result.inputs["inside_radius"] == pytest.approx(0.3 * INCH)


@pytest.mark.parametrize("unit", ["in", "mm"])
def test_retyping_the_value_in_use_records_nothing(unit: str) -> None:
    """Retyping "0.156" passes "0", "0.1", "0.15"; only the end of the edit counts."""
    window = open_window()
    window.select_calculator(BEND)
    window.units_box.setCurrentText(unit)
    retyped = field(window, "inside_radius").text()
    type_into(field(window, "inside_radius"), retyped)  # ends with Enter
    assert not overrides_radius(window)
    assert source_of(window, "inside_radius") == "default"
    window.units_box.setCurrentText("in")
    then_family_radius_flows_through(window)
    window.close()


def test_an_edit_ending_on_a_typo_records_nothing() -> None:
    """A typo "0.1x" passes "0.1" on the way; ending refused, it applies nothing."""
    window = open_window()
    window.select_calculator(BEND)
    type_into(field(window, "inside_radius"), "0.1x", enter=False)
    window.select_domain("sheet_metal")  # leaving the page ends the edit
    assert not overrides_radius(window)
    window.select_calculator(BEND)
    assert field(window, "inside_radius").text() == "0.1x"

    then_family_radius_flows_through(window)
    note = window.override_notes["inside_radius"]
    assert note.text() == (
        "Your unapplied text '0.1x' for inside bend radius was discarded; it now uses the "
        "Sheet Metal value."
    )
    window.close()


def test_a_copied_family_value_is_credited_only_while_it_matches() -> None:
    window = open_window()
    set_family(window, "thickness", "0.25")
    window.select_calculator(BEND)
    window.inherit_boxes["thickness"].setChecked(False)
    assert source_of(window, "thickness") == "copied from Sheet Metal settings"

    set_family(window, "thickness", "0.0747")
    window.select_calculator(BEND)
    assert window.result.inputs["thickness"] == pytest.approx(0.25 * INCH)
    assert source_of(window, "thickness") == "copied earlier from Sheet Metal settings"
    window.close()


def test_a_cleared_field_shows_its_default_as_a_labelled_placeholder() -> None:
    window = open_window()
    window.select_calculator(BEND)
    thickness = field(window, "thickness")
    type_into(thickness, "")
    assert (thickness.text(), thickness.placeholderText()) == ("", "default 0.1046")
    window.units_box.setCurrentText("mm")
    assert field(window, "thickness").placeholderText() == "default 2.65684"
    window.close()


def test_unticking_copies_the_family_value_and_typing_then_overrides() -> None:
    window = open_window()
    set_family(window, "thickness", "0.25")
    window.select_calculator(BEND)
    before = window.result.outputs

    window.inherit_boxes["thickness"].setChecked(False)
    assert field(window, "thickness").text() == "0.25"
    assert not field(window, "thickness").isReadOnly()
    assert window.result.outputs == before, "unticking changes nothing by itself"
    assert source_of(window, "thickness") == "copied from Sheet Metal settings"

    type_into(field(window, "thickness"), "0.1046", enter=False)
    assert source_of(window, "thickness") == "entered"
    note = window.override_notes["thickness"]
    assert note.text() == "Sheet Metal value is 0.2500 in; this calculator uses 0.1046 in."
    window.close()


def test_the_override_note_follows_the_family_value() -> None:
    window = open_window()
    set_family(window, "thickness", "0.25")
    window.select_calculator(BEND)
    window.inherit_boxes["thickness"].setChecked(False)
    type_into(field(window, "thickness"), "0.1046", enter=False)

    set_family(window, "thickness", "0.3")
    window.select_calculator(BEND)
    assert window.override_notes["thickness"].text() == (
        "Sheet Metal value is 0.3000 in; this calculator uses 0.1046 in."
    )
    assert source_of(window, "thickness") == "entered", "the override is sticky"

    set_family(window, "thickness", "")
    window.select_calculator(BEND)
    assert window.override_notes["thickness"].isHidden()
    assert window.inherit_boxes["thickness"].isHidden(), "nothing to inherit"
    assert source_of(window, "thickness") == "entered"

    set_family(window, "thickness", "0.3")
    window.select_calculator(BEND)
    window.inherit_boxes["thickness"].setChecked(True)
    assert field(window, "thickness").text() == "0.3"
    assert window.override_notes["thickness"].isHidden()
    assert source_of(window, "thickness") == "Sheet Metal settings"
    window.close()


def test_the_settings_page_counts_the_calculators_that_override() -> None:
    window = open_window()
    set_family(window, "thickness", "0.25")
    window.select_calculator(BEND)
    window.inherit_boxes["thickness"].setChecked(False)
    window.select_domain("sheet_metal")
    assert "Overridden in 1: Bend allowance & deduction" in page_text(window.settings_box)
    window.close()


def test_unreadable_text_stays_with_its_error_and_applies_no_prefix() -> None:
    """Typing "0.1x" passes "0.1" on the way; after a rebuild it must not be in effect."""
    window = open_window()
    window.select_calculator(BEND)
    type_into(field(window, "thickness"), "0.1x", enter=False)
    assert "Material thickness: Unknown unit 'x'" in result(window)

    for leave_and_return in (
        lambda: (window.select_domain("sheet_metal"), window.select_calculator(BEND)),
        lambda: window.units_box.setCurrentText("mm"),
        lambda: window.units_box.setCurrentText("in"),
    ):
        leave_and_return()
        assert field(window, "thickness").text() == "0.1x"
        assert "border" in field(window, "thickness").styleSheet()
        assert window.result is None
        assert "Unknown unit 'x'" in result(window)

    type_into(field(window, "thickness"), "", enter=False)
    assert source_of(window, "thickness") == "default", "clearing drops the field's own value"
    type_into(field(window, "thickness"), "0.25", enter=False)
    assert window.result.inputs["thickness"] == pytest.approx(0.25 * INCH)
    window.close()


def test_a_units_round_trip_never_changes_a_calculator_value() -> None:
    """KI-017: switching units never re-reads six-decimal display text as the value."""
    window = open_window()
    window.select_calculator(BEND)
    type_into(field(window, "thickness"), "1/3", enter=False)
    for unit, thickness, radius in (
        ("mm", "8.466667", "3.9624"),
        ("in", "1/3", "0.156"),
        ("mm", "8.466667", "3.9624"),
        ("in", "1/3", "0.156"),
    ):
        window.units_box.setCurrentText(unit)
        assert field(window, "thickness").text() == thickness
        assert field(window, "inside_radius").text() == radius
    typed = window.entries[BEND]["thickness"].value
    assert typed == TypedValue.parse("1/3", Dimension.LENGTH, "in")
    assert window.result.inputs["thickness"] == 1 / 3 * INCH
    window.close()


def test_load_course_example_restores_the_lesson_over_family_values() -> None:
    """Decision D: with T set to Lesson 2's 0.1046 in, Lesson 4's cone gives 132.30°."""
    window = open_window()
    set_family(window, "thickness", "0.1046")
    window.select_calculator(CONE)
    assert "132.30°" in result(window)

    assert not window.example_button.isHidden()
    window.example_button.click()
    assert field(window, "thickness").text() == "0.0747"
    assert not window.inherit_boxes["thickness"].isChecked()
    assert window.override_notes["thickness"].text() == (
        "Sheet Metal value is 0.1046 in; this calculator uses 0.0747 in."
    )
    assert "132.70°" in result(window)
    assert source_of(window, "thickness") == "course example"
    assert "Material thickness\n0.0747\nin\ncourse example" in result(window)

    type_into(field(window, "thickness"), "0.08", enter=False)
    assert source_of(window, "thickness") == "entered"
    window.close()


def test_load_course_example_selects_the_course_method() -> None:
    """Lesson 2's bend allowance is 0.311864 in; the K-factor method would give 0.310766."""
    window = open_window()
    window.select_calculator(BEND)
    window.method_box.setCurrentIndex(window.method_box.findData("k_factor"))
    window.example_button.click()
    assert window.method_key == "course"
    bend_allowance = window.result.outputs["bend_allowance"] / INCH
    assert bend_allowance == pytest.approx(0.311864, abs=5e-7)

    window.method_box.setCurrentIndex(window.method_box.findData("k_factor"))
    assert source_of(window, "thickness") == "course example"
    assert source_of(window, "k_factor") == "default", "K isn't part of the course"
    window.close()


def test_loading_mid_edit_judges_the_edit_first() -> None:
    """A shortcut or script may load the example mid-edit; a no-op retype must not stick."""
    window = open_window()
    window.select_calculator(BEND)
    window.method_box.setCurrentIndex(window.method_box.findData("k_factor"))
    type_into(field(window, "k_factor"), "0.4", enter=False)  # K's default, retyped
    window.load_course_example()
    assert "k_factor" not in window.overrides.get(BEND, set())
    set_family(window, "k_factor", "0.33")
    window.select_calculator(BEND)
    window.method_box.setCurrentIndex(window.method_box.findData("k_factor"))
    assert source_of(window, "k_factor") == "Sheet Metal settings"
    window.close()


def test_loading_the_course_example_leaves_other_inputs_as_they_were() -> None:
    window = open_window()
    set_family(window, "k_factor", "0.33")
    window.select_calculator(BEND)
    window.method_box.setCurrentIndex(window.method_box.findData("k_factor"))
    window.inherit_boxes["k_factor"].setChecked(False)
    type_into(field(window, "k_factor"), "0.44")
    window.example_button.click()
    window.method_box.setCurrentIndex(window.method_box.findData("k_factor"))
    assert source_of(window, "k_factor") == "entered"
    assert window.result.inputs["k_factor"] == pytest.approx(0.44)
    assert source_of(window, "thickness") == "course example"
    window.close()


def test_fields_a_note_concerns_are_outlined() -> None:
    from caddcalc.gui.icons import role_color

    window = open_window()
    window.select_calculator(BEND)
    type_into(field(window, "inside_radius"), "0.05", enter=False)  # R < T
    outline = role_color("outline_note", "light")
    for key in ("inside_radius", "thickness"):
        assert outline in field(window, key).styleSheet(), key
    assert field(window, "bend_angle").styleSheet() == ""
    type_into(field(window, "inside_radius"), "0.156", enter=False)
    assert field(window, "thickness").styleSheet() == ""
    window.close()


def test_a_family_k_factor_reaches_only_the_methods_that_use_it() -> None:
    window = open_window()
    set_family(window, "k_factor", "0.44")
    window.select_calculator(BEND)
    window.method_box.setCurrentIndex(window.method_box.findData("course"))
    assert "k_factor" not in window.fields
    assert "0.3119 in" in result(window), "the course formula has its factor built in"

    window.method_box.setCurrentIndex(window.method_box.findData("k_factor"))
    assert field(window, "k_factor").text() == "0.44"
    assert "K-factor\n0.4400\n\nSheet Metal settings" in result(window)
    window.close()
