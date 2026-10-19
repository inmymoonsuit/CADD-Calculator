"""The GUI's domain settings page (ADR-0013 §8). Skipped when PySide6 is not installed."""

from __future__ import annotations

from typing import Any

import pytest

from caddcalc.calculators import default_registry
from caddcalc.calculators.sheet_metal import DOMAIN as SHEET_METAL
from caddcalc.core import Dimension, Domain, Param, TypedValue
from tests.qt_helpers import open_window, page_text, plain, show_in, type_into

pytestmark = [pytest.mark.gui, pytest.mark.usefixtures("qt")]

PLATE = Domain(
    "plate",
    "Plate Tools",
    "A plugin-style family whose length setting has a maximum.",
    settings=(
        Param("width", "W", "Width", Dimension.LENGTH, unit="in", minimum=0.0, maximum=10.0),
        Param("gap", "G", "Gap", Dimension.LENGTH, unit="in"),
    ),
)

ACME = Domain(
    "acme",
    "Acme Tools",
    "A plugin family whose calculators failed to load.",
    settings=(
        Param("gap", "G", "Gap", Dimension.LENGTH, unit="in", help="Clearance between parts."),
    ),
)


def pick_setting(window: Any, key: str, choice: str) -> None:
    """Pick a setting's unit in its picker, as a person does."""
    picker = window.setting_pickers[key]
    index = picker.choices.index(choice)
    picker.setCurrentIndex(index)
    picker.activated.emit(index)


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
    assert k_factor(window) == TypedValue.read("0.44", "", Dimension.RATIO)

    _setting, thickness = window.setting_fields["thickness"]
    type_into(thickness, "0.1046", enter=False)
    leave(thickness)
    assert window.domain_settings.get(SHEET_METAL, "thickness") == TypedValue.read(
        "0.1046", "in", Dimension.LENGTH
    )
    window.close()


def test_a_typo_never_applies_a_passing_prefix_and_stays_visible() -> None:
    """Typing "15" for ".15" must not leave K = 1 from the "1" that passed on the way."""
    window = open_window()
    window.select_domain("sheet_metal")
    type_into(window.setting_fields["k_factor"][1], "0.4")
    before = TypedValue.read("0.4", "", Dimension.RATIO)

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
        lambda: (
            window.select_calculator("sheet_metal.bend_allowance"),
            show_in(window, "mm"),
            window.select_domain("sheet_metal"),
        ),
    ):
        leave_and_return()
        _setting, field = window.setting_fields["k_factor"]
        assert field.text() == "15"
        assert "border" in field.styleSheet()
        assert "K-factor (K) must be at most 1" in plain(window.domain_note.text())
        assert k_factor(window) == before

    type_into(field, "0.15")
    assert k_factor(window) == TypedValue.read("0.15", "", Dimension.RATIO)
    assert window.domain_note.text() == ""
    assert field.styleSheet() == ""
    window.close()


def test_unreadable_text_is_explained_with_the_setting_name() -> None:
    window = open_window()
    window.select_domain("sheet_metal")
    type_into(window.setting_fields["k_factor"][1], "abc")
    assert "K-factor (K): 'abc' isn't a number or arithmetic" in plain(window.domain_note.text())
    assert k_factor(window) is None
    window.close()


def _length_labels(window: Any) -> set[str]:
    """The unit labels after the page's length fields."""
    from PySide6.QtWidgets import QLabel

    labels = window.settings_box.findChildren(QLabel)
    return {label.text() for label in labels if label.text() in ("in", "mm", "ft", "cm", "m")}


def test_a_setting_reads_in_its_picker_whatever_the_results_show() -> None:
    """Each setting has its own picker, as a calculator field has (ADR-0024 U2b)."""
    window = open_window()
    window.select_domain("sheet_metal")
    assert set(window.setting_pickers) == {"thickness", "inside_radius"}, "K has no unit"
    assert window.setting_pickers["thickness"].accessibleName() == "Material thickness unit"
    type_into(window.setting_fields["thickness"][1], "0.1046")
    typed = TypedValue.read("0.1046", "in", Dimension.LENGTH)
    assert window.domain_settings.get(SHEET_METAL, "thickness") == typed
    pick_setting(window, "inside_radius", "mm")
    type_into(window.setting_fields["inside_radius"][1], "3")
    assert window.domain_settings.for_domain(SHEET_METAL).values["inside_radius"] == 3.0

    window.select_calculator("sheet_metal.bend_allowance")
    show_in(window, "ft")
    window.select_domain("sheet_metal")
    assert window.setting_fields["thickness"][1].text() == "0.1046"
    assert window.setting_fields["inside_radius"][1].text() == "3"
    assert window.setting_pickers["inside_radius"].choice == "mm", "kept through a rebuild"
    assert window.domain_settings.get(SHEET_METAL, "thickness") == typed, "display never re-read"
    window.close()


def test_a_unit_typed_in_a_setting_is_refused_and_says_where_it_goes() -> None:
    window = open_window()
    window.select_domain("sheet_metal")
    type_into(window.setting_fields["inside_radius"][1], "3 mm")
    assert window.domain_settings.get(SHEET_METAL, "inside_radius") is None
    note = plain(window.domain_note.text())
    assert "Inside bend radius (R): Units go in the picker: '3 mm' names mm." in note
    assert "Use " not in note, "no button to offer it with"
    window.close()


def test_a_pick_re_reads_a_typed_setting_and_keeps_text_it_refuses() -> None:
    """As on a calculator field: 3 stays 3, now in mm (ADR-0024 §2)."""
    window = open_window()
    window.select_domain("sheet_metal")
    type_into(window.setting_fields["thickness"][1], "3")
    pick_setting(window, "thickness", "mm")
    assert window.setting_fields["thickness"][1].text() == "3"
    assert window.domain_settings.for_domain(SHEET_METAL).values["thickness"] == 3.0
    assert window.statusBar().currentMessage() == "Material thickness: in millimeters"
    pick_setting(window, "thickness", "ft_in")
    assert window.domain_settings.for_domain(SHEET_METAL).values["thickness"] == 3 * 25.4
    type_into(window.setting_fields["thickness"][1], "1'-4\"")
    pick_setting(window, "thickness", "mm")
    assert window.domain_settings.get(SHEET_METAL, "thickness") is None, "refused in mm"
    assert window.setting_fields["thickness"][1].text() == "1'-4\"", "kept to be fixed"
    window.close()


def test_a_setting_inherited_by_a_field_picked_in_another_unit_shows_converted() -> None:
    """ADR-0024 U2b: typed in mm on the page, shown in inches on the calculator, same value."""
    window = open_window()
    window.select_domain("sheet_metal")
    pick_setting(window, "thickness", "mm")
    type_into(window.setting_fields["thickness"][1], "2.54")
    window.select_calculator("sheet_metal.bend_allowance")
    assert window.pickers["thickness"].choice == "in"
    assert window.fields["thickness"][1].text() == "0.1"
    assert window.result.inputs["thickness"] == 2.54
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
    assert k_factor(window) == TypedValue.read("0.44", "", Dimension.RATIO)
    window.select_domain("sheet_metal")
    assert window.setting_fields["k_factor"][1].text() == "0.44"
    window.close()


def test_refused_text_stays_as_typed_and_unapplied() -> None:
    """A refused "5" stays refused, as typed, whatever the results are shown in."""
    registry = default_registry(load_plugins=False)
    registry.register_domain(PLATE)
    window = open_window(registry)
    window.select_domain("plate")
    type_into(window.setting_fields["width"][1], "5")
    type_into(window.setting_fields["gap"][1], "abc")
    assert "Width (W) must be at most" in plain(window.domain_note.text())

    for step in (
        lambda: (
            window.select_calculator("sheet_metal.bend_allowance"),
            show_in(window, "mm"),
            window.select_domain("plate"),
        ),
        lambda: (
            window.select_calculator("sheet_metal.bend_allowance"),
            window.select_domain("plate"),
        ),
    ):
        step()
        _setting, width = window.setting_fields["width"]
        assert width.text() == "5"
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


@pytest.mark.parametrize("language", ["", "en_XA"])
def test_the_settings_pickers_are_whole_at_the_least_window(tmp_path: Any, language: str) -> None:
    """ADR-0024 U2b: each picker shows its widest unit, in English and in en_XA.

    Group boxes are left out, as the launch-size test leaves the page out: the check
    measures a group box's least height at its least width (ADR-0024's U1 amendment).
    """
    from PySide6.QtWidgets import QGroupBox

    from tests.qt_helpers import settle
    from tests.test_translated_gui import _clipped, _in

    _in(language, tmp_path)
    window = open_window()
    window.select_domain("sheet_metal")
    window.show()
    window.resize(1, 1)
    settle(window)
    pickers = list(window.setting_pickers.values())
    assert pickers and all(p.isVisible() for p in pickers)
    clipped = [w for w in _clipped(window) if not isinstance(w, QGroupBox)]
    assert clipped == []
    widths = {p.width() for p in pickers}
    assert len(widths) == 1, "one column of pickers"
    window.close()
