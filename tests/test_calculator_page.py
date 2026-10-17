"""Calculator pages: inheriting and overriding family settings, and numeric intent.

ADR-0013 §8 and §9, decisions C and D. Skipped when PySide6 is not installed.
"""

from __future__ import annotations

from typing import Any

import pytest

from caddcalc.core import Dimension, TypedValue
from tests.qt_helpers import open_window, page_text, type_into

pytestmark = [pytest.mark.gui, pytest.mark.usefixtures("qt")]

BEND = "sheet_metal.bend_allowance"
CONE = "sheet_metal.truncated_cone_layout"


def set_family(window: Any, key: str, text: str) -> None:
    """Set a Sheet Metal value on its settings page, as a user does."""
    window.select_domain("sheet_metal")
    type_into(window.setting_fields[key][1], text)


def result(window: Any) -> str:
    text: str = window.output.toPlainText()
    return text


def test_an_inherited_value_reaches_the_result_with_its_source() -> None:
    window = open_window()
    set_family(window, "thickness", "0.25")
    window.select_calculator(BEND)
    window.method_box.setCurrentIndex(0)  # course: BA = (0.64·T + 1.57·R)·A/90

    assert window.fields["thickness"][1].text() == "0.25"
    box = window.inherit_boxes["thickness"]
    assert not box.isHidden() and box.isChecked()
    assert "0.4049 in" in result(window), "BA with T = 0.25 in, R = 0.156 in"
    assert "Material thickness\n0.2500 in\n(Sheet Metal settings)" in result(window)
    assert "Inside bend radius\n0.1560 in\n(default)" in result(window)
    window.close()


def test_typing_overrides_and_the_marker_follows_the_family_value() -> None:
    window = open_window()
    set_family(window, "thickness", "0.25")
    window.select_calculator(BEND)
    type_into(window.fields["thickness"][1], "0.1046", enter=False)  # forms recompute live

    assert not window.inherit_boxes["thickness"].isChecked()
    note = window.override_notes["thickness"]
    assert note.text() == "Sheet Metal value is 0.2500 in; this calculator uses 0.1046 in."
    assert "Material thickness\n0.1046 in\n(entered)" in result(window)

    set_family(window, "thickness", "0.3")
    window.select_calculator(BEND)
    note = window.override_notes["thickness"]
    assert note.text() == "Sheet Metal value is 0.3000 in; this calculator uses 0.1046 in."
    assert "(entered)" in result(window), "the override is sticky"

    set_family(window, "thickness", "")
    window.select_calculator(BEND)
    assert window.override_notes["thickness"].isHidden()
    assert window.inherit_boxes["thickness"].isHidden(), "nothing to inherit"
    assert "Material thickness\n0.1046 in\n(entered)" in result(window)

    set_family(window, "thickness", "0.3")
    window.select_calculator(BEND)
    window.inherit_boxes["thickness"].setChecked(True)
    assert window.fields["thickness"][1].text() == "0.3"
    assert window.override_notes["thickness"].isHidden()
    assert "Material thickness\n0.3000 in\n(Sheet Metal settings)" in result(window)
    window.close()


def test_the_settings_page_counts_the_calculators_that_override() -> None:
    window = open_window()
    set_family(window, "thickness", "0.25")
    window.select_calculator(BEND)
    type_into(window.fields["thickness"][1], "0.1046", enter=False)
    window.select_domain("sheet_metal")
    assert "Overridden in 1: Bend allowance & deduction" in page_text(window.settings_box)
    window.close()


def test_a_units_round_trip_never_changes_a_calculator_value() -> None:
    """KI-017: switching units used to re-read six-decimal display text as the value."""
    window = open_window()
    window.select_calculator(BEND)
    type_into(window.fields["thickness"][1], "1/3", enter=False)
    for unit, thickness, radius in (
        ("mm", "8.466667", "3.9624"),
        ("in", "1/3", "0.156"),
        ("mm", "8.466667", "3.9624"),
        ("in", "1/3", "0.156"),
    ):
        window.units_box.setCurrentText(unit)
        assert window.fields["thickness"][1].text() == thickness
        assert window.fields["inside_radius"][1].text() == radius
    typed = window.entries[BEND]["thickness"]
    assert typed == TypedValue.parse("1/3", Dimension.LENGTH, "in")
    assert typed.value == 1 / 3 * 25.4
    window.close()


def test_load_course_example_restores_the_lesson_inputs_over_family_values() -> None:
    """Decision D: with T set to Lesson 2's 0.1046 in, Lesson 4's cone gives 132.30°."""
    window = open_window()
    set_family(window, "thickness", "0.1046")
    window.select_calculator(CONE)
    assert "132.30°" in result(window)

    assert not window.example_button.isHidden()
    window.example_button.click()
    assert window.fields["thickness"][1].text() == "0.0747"
    assert not window.inherit_boxes["thickness"].isChecked()
    assert window.override_notes["thickness"].text() == (
        "Sheet Metal value is 0.1046 in; this calculator uses 0.0747 in."
    )
    assert "132.70°" in result(window)
    window.close()


def test_a_family_k_factor_reaches_only_the_methods_that_use_it() -> None:
    window = open_window()
    set_family(window, "k_factor", "0.44")
    window.select_calculator(BEND)
    window.method_box.setCurrentIndex(window.method_box.findData("course"))
    assert "k_factor" not in window.fields
    assert "0.3119 in" in result(window), "the course formula has its factor built in"

    window.method_box.setCurrentIndex(window.method_box.findData("k_factor"))
    assert window.fields["k_factor"][1].text() == "0.44"
    assert "K-factor\n0.4400\n(Sheet Metal settings)" in result(window)
    window.close()
