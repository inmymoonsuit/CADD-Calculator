"""The GUI's domain settings page (ADR-0013 §8). Skipped when PySide6 is not installed."""

from __future__ import annotations

from typing import Any

import pytest

from caddcalc.calculators import default_registry
from caddcalc.calculators.sheet_metal import DOMAIN as SHEET_METAL
from caddcalc.core import Dimension, Domain, Param, TypedValue
from tests.qt_helpers import open_window, page_text, plain, type_into

pytestmark = [pytest.mark.gui, pytest.mark.usefixtures("qt")]

PLATE = Domain(
    "plate",
    "Plate Tools",
    "A plugin-style family whose length setting has a maximum.",
    settings=(
        Param("width", "W", "Width", Dimension.LENGTH, minimum=0.0, maximum=10.0),
        Param("gap", "G", "Gap", Dimension.LENGTH),
    ),
)

ACME = Domain(
    "acme",
    "Acme Tools",
    "A plugin family whose calculators failed to load.",
    settings=(Param("gap", "G", "Gap", Dimension.LENGTH, help="Clearance between parts."),),
)


def leave(edit: Any) -> None:
    """Take the focus away from a field, as clicking elsewhere does."""
    from PySide6.QtCore import QEvent, Qt
    from PySide6.QtGui import QFocusEvent
    from PySide6.QtWidgets import QApplication

    QApplication.sendEvent(edit, QFocusEvent(QEvent.Type.FocusOut, Qt.FocusReason.TabFocusReason))


def k_factor(window: Any) -> TypedValue | None:
    value: TypedValue | None = window.domain_settings.get(SHEET_METAL, "k_factor")
    return value


def test_a_family_row_opens_its_settings_page() -> None:
    window = open_window()
    assert window.calculator is not None, "a calculator is shown at first"
    families = [window.tree.topLevelItem(i) for i in range(window.tree.topLevelItemCount())]
    assert [f.text(0) for f in families] == ["Geometry", "Conversions", "Sheet Metal"]
    family = families[2]
    window.tree.setCurrentItem(family)

    assert window.domain is SHEET_METAL
    assert window.calculator is None
    assert window.pages.currentWidget() is window.domain_page
    assert window.method_row.isHidden()
    assert list(window.setting_fields) == ["thickness", "inside_radius", "k_factor"]
    for _setting, edit in window.setting_fields.values():
        assert (edit.text(), edit.placeholderText()) == ("", "not set")

    text = page_text(window.settings_box)
    assert "Gauge numbers mean different thicknesses" in text
    assert "V-die opening (air bending): 8 × thickness rule of thumb" in text
    assert "Bend allowance & deduction: K-factor (neutral axis)" in text

    window.select_calculator("sheet_metal.bend_allowance")
    assert window.pages.currentWidget() is window.calculator_page
    assert not window.method_row.isHidden()
    window.close()


def test_a_setting_applies_on_enter_or_when_the_field_is_left() -> None:
    window = open_window()
    window.select_domain("sheet_metal")
    _setting, field = window.setting_fields["k_factor"]
    type_into(field, "0.44", enter=False)
    assert k_factor(window) is None, "typing alone applies nothing"
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest

    QTest.keyClick(field, Qt.Key.Key_Return)
    assert k_factor(window) == TypedValue.parse("0.44", Dimension.RATIO)

    _setting, thickness = window.setting_fields["thickness"]
    type_into(thickness, "0.1046", enter=False)
    leave(thickness)
    assert window.domain_settings.get(SHEET_METAL, "thickness") == TypedValue.parse(
        "0.1046", Dimension.LENGTH, "in"
    )
    window.close()


def test_a_typo_never_applies_a_passing_prefix_and_stays_visible() -> None:
    """Typing "15" for ".15" must not leave K = 1 from the "1" that passed on the way."""
    window = open_window()
    window.select_domain("sheet_metal")
    type_into(window.setting_fields["k_factor"][1], "0.4")
    before = TypedValue.parse("0.4", Dimension.RATIO)

    _setting, field = window.setting_fields["k_factor"]
    type_into(field, "15", enter=False)
    assert "K-factor (K) must be at most 1" in plain(window.domain_note.text()), "checked live"
    assert k_factor(window) == before
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest

    QTest.keyClick(field, Qt.Key.Key_Return)
    assert k_factor(window) == before, "refused text applies nothing"

    for leave_and_return in (
        lambda: (
            window.select_calculator("sheet_metal.bend_allowance"),
            window.select_domain("sheet_metal"),
        ),
        lambda: window.units_box.setCurrentText("mm"),
        lambda: window.units_box.setCurrentText("in"),
    ):
        leave_and_return()
        _setting, field = window.setting_fields["k_factor"]
        assert field.text() == "15"
        assert "border" in field.styleSheet()
        assert "K-factor (K) must be at most 1" in plain(window.domain_note.text())
        assert k_factor(window) == before

    type_into(field, "0.15")
    assert k_factor(window) == TypedValue.parse("0.15", Dimension.RATIO)
    assert window.domain_note.text() == ""
    assert field.styleSheet() == ""
    window.close()


def test_unreadable_text_is_explained_with_the_setting_name() -> None:
    window = open_window()
    window.select_domain("sheet_metal")
    type_into(window.setting_fields["k_factor"][1], "abc")
    assert "K-factor (K): Cannot read a value from 'abc'" in plain(window.domain_note.text())
    assert k_factor(window) is None
    window.close()


def test_a_typed_setting_keeps_the_users_text_across_unit_switches() -> None:
    window = open_window()
    window.select_domain("sheet_metal")
    type_into(window.setting_fields["thickness"][1], "0.1046")
    typed = TypedValue.parse("0.1046", Dimension.LENGTH, "in")
    assert window.domain_settings.get(SHEET_METAL, "thickness") == typed

    type_into(window.setting_fields["inside_radius"][1], "3 mm")
    for unit, shown in (("mm", "2.65684"), ("in", "0.1046"), ("mm", "2.65684"), ("in", "0.1046")):
        window.units_box.setCurrentText(unit)
        assert window.setting_fields["thickness"][1].text() == shown
        assert window.setting_fields["inside_radius"][1].text() == "3 mm"
    assert window.domain_settings.get(SHEET_METAL, "thickness") == typed, "display never re-read"
    window.close()


def test_settings_can_be_unset_one_at_a_time_or_all_at_once() -> None:
    window = open_window()
    window.select_domain("sheet_metal")
    type_into(window.setting_fields["thickness"][1], "0.1046")
    type_into(window.setting_fields["k_factor"][1], "0.44")

    type_into(window.setting_fields["k_factor"][1], "")
    assert k_factor(window) is None
    assert window.domain_settings.get(SHEET_METAL, "thickness") is not None

    type_into(window.setting_fields["inside_radius"][1], "-1")
    window.clear_settings_button.click()
    assert dict(window.domain_settings.values(SHEET_METAL)) == {}
    assert all(edit.text() == "" for _s, edit in window.setting_fields.values())
    assert window.domain_note.text() == "", "clearing also drops refused text"
    window.close()


def test_leaving_the_page_applies_text_typed_without_enter() -> None:
    window = open_window()
    window.select_domain("sheet_metal")
    type_into(window.setting_fields["k_factor"][1], "0.44", enter=False)
    window.select_calculator("sheet_metal.v_die_opening")
    assert k_factor(window) == TypedValue.parse("0.44", Dimension.RATIO)
    window.select_domain("sheet_metal")
    assert window.setting_fields["k_factor"][1].text() == "0.44"
    window.close()


def test_refused_unitless_text_keeps_the_unit_it_was_typed_in() -> None:
    """A refused "5" in inches must not become an accepted 5 mm after a switch to mm."""
    registry = default_registry(load_plugins=False)
    registry.register_domain(PLATE)
    window = open_window(registry)
    window.select_domain("plate")
    type_into(window.setting_fields["width"][1], "5")
    type_into(window.setting_fields["gap"][1], "abc")
    assert "Width (W) must be at most" in plain(window.domain_note.text())

    for step in (
        lambda: window.units_box.setCurrentText("mm"),
        lambda: (
            window.select_calculator("sheet_metal.bend_allowance"),
            window.select_domain("plate"),
        ),
        lambda: window.units_box.setCurrentText("in"),
    ):
        step()
        _setting, width = window.setting_fields["width"]
        assert width.text() == "5 in"
        assert "border" in width.styleSheet()
        assert window.setting_fields["gap"][1].text() == "abc"
        assert window.domain_settings.get(PLATE, "width") is None, "never applied"
        assert window.domain_settings.get(PLATE, "gap") is None
    window.close()


def test_a_family_with_no_calculators_is_listed_and_marked() -> None:
    from PySide6.QtCore import Qt

    registry = default_registry(load_plugins=False)
    registry.register_domain(ACME)
    window = open_window(registry)
    family = window.tree.topLevelItem(window.tree.topLevelItemCount() - 1)
    assert family.text(0) == "Acme Tools", "a plugin's family follows the built-ins"
    placeholder = family.child(0)
    assert (family.childCount(), placeholder.text(0)) == (1, "No calculators loaded")
    assert placeholder.flags() == Qt.ItemFlag.NoItemFlags
    assert window.calculator is not None, "the first calculator is still shown first"

    window.tree.setCurrentItem(family)
    assert window.domain is ACME
    assert "No calculators loaded." in plain(window.domain_note.text())
    assert "Used by: no loaded calculator" in page_text(window.settings_box)
    window.close()
