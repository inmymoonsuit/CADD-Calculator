"""The GUI's domain settings page (ADR-0013 §8). Skipped when PySide6 is not installed."""

from __future__ import annotations

import os
from collections.abc import Iterator
from typing import Any

import pytest

from caddcalc.calculators import default_registry
from caddcalc.calculators.sheet_metal import DOMAIN as SHEET_METAL
from caddcalc.core import Dimension, Domain, Param, Registry, TypedValue

pytestmark = pytest.mark.gui

ACME = Domain(
    "acme",
    "Acme Tools",
    "A plugin family whose calculators failed to load.",
    settings=(Param("gap", "G", "Gap", Dimension.LENGTH, help="Clearance between parts."),),
)


@pytest.fixture
def qt(monkeypatch: pytest.MonkeyPatch) -> Iterator[Any]:
    """The Qt widgets module, with an application running offscreen."""
    monkeypatch.setenv("QT_QPA_PLATFORM", os.environ.get("QT_QPA_PLATFORM", "offscreen"))
    widgets = pytest.importorskip("PySide6.QtWidgets")
    app = widgets.QApplication.instance() or widgets.QApplication([])
    yield widgets
    app.processEvents()


def open_window(registry: Registry | None = None) -> Any:
    from caddcalc.gui.window import MainWindow

    return MainWindow(registry or default_registry(load_plugins=False))


def type_into(edit: Any, text: str) -> None:
    """Replace a field's text the way a user does, so its edit signal fires."""
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest

    edit.selectAll()
    if text:
        QTest.keyClicks(edit, text)
    else:
        QTest.keyClick(edit, Qt.Key.Key_Backspace)


def plain(html: str) -> str:
    """The text a rich-text label shows."""
    from PySide6.QtGui import QTextDocument

    document = QTextDocument()
    document.setHtml(html)
    return document.toPlainText()


def page_text(widget: Any, qt: Any) -> str:
    return "\n".join(plain(label.text()) for label in widget.findChildren(qt.QLabel))


def test_a_family_row_opens_its_settings_page(qt: Any) -> None:
    window = open_window()
    assert window.calculator is not None, "a calculator is shown at first"
    family = window.tree.topLevelItem(0)
    assert family.text(0) == "Sheet Metal"
    window.tree.setCurrentItem(family)

    assert window.domain is SHEET_METAL
    assert window.calculator is None
    assert window.pages.currentWidget() is window.domain_page
    assert window.method_row.isHidden()
    assert list(window.setting_fields) == ["thickness", "inside_radius", "k_factor"]
    for _setting, edit in window.setting_fields.values():
        assert (edit.text(), edit.placeholderText()) == ("", "not set")

    text = page_text(window.settings_box, qt)
    assert "Gauge numbers mean different thicknesses" in text
    assert "V-die opening (air bending): 8 × thickness rule of thumb" in text
    assert "Bend allowance & deduction: K-factor (neutral axis)" in text

    window.select_calculator("sheet_metal.bend_allowance")
    assert window.pages.currentWidget() is window.calculator_page
    assert not window.method_row.isHidden()
    window.close()


@pytest.mark.usefixtures("qt")
def test_a_typed_setting_keeps_the_users_text_across_unit_switches() -> None:
    window = open_window()
    window.select_domain("sheet_metal")
    _setting, thickness = window.setting_fields["thickness"]
    type_into(thickness, "0.1046")
    typed = TypedValue.parse("0.1046", Dimension.LENGTH, "in")
    assert window.domain_settings.get(SHEET_METAL, "thickness") == typed

    _setting, radius = window.setting_fields["inside_radius"]
    type_into(radius, "3 mm")
    for unit, shown in (("mm", "2.65684"), ("in", "0.1046"), ("mm", "2.65684"), ("in", "0.1046")):
        window.units_box.setCurrentText(unit)
        assert window.setting_fields["thickness"][1].text() == shown
        assert window.setting_fields["inside_radius"][1].text() == "3 mm"
    assert window.domain_settings.get(SHEET_METAL, "thickness") == typed, "display never re-read"
    window.close()


@pytest.mark.usefixtures("qt")
def test_a_refused_setting_is_explained_and_keeps_its_last_value() -> None:
    window = open_window()
    window.select_domain("sheet_metal")
    _setting, k_factor = window.setting_fields["k_factor"]
    type_into(k_factor, "0.44")
    type_into(k_factor, "2")  # refused from its first keystroke
    assert "K-factor (K) must be at most 1" in plain(window.domain_note.text())
    assert "border" in k_factor.styleSheet()
    assert window.domain_settings.get(SHEET_METAL, "k_factor") == TypedValue.parse(
        "0.44", Dimension.RATIO
    )

    type_into(k_factor, "abc")
    assert "K-factor (K): Cannot read a value from 'abc'" in plain(window.domain_note.text())
    type_into(k_factor, "0.42")
    assert window.domain_note.text() == ""
    assert k_factor.styleSheet() == ""
    window.close()


@pytest.mark.usefixtures("qt")
def test_settings_can_be_unset_one_at_a_time_or_all_at_once() -> None:
    window = open_window()
    window.select_domain("sheet_metal")
    type_into(window.setting_fields["thickness"][1], "0.1046")
    type_into(window.setting_fields["k_factor"][1], "0.44")

    type_into(window.setting_fields["k_factor"][1], "")
    assert window.domain_settings.get(SHEET_METAL, "k_factor") is None
    assert window.domain_settings.get(SHEET_METAL, "thickness") is not None

    window.clear_settings_button.click()
    assert dict(window.domain_settings.values(SHEET_METAL)) == {}
    assert all(edit.text() == "" for _s, edit in window.setting_fields.values())
    window.close()


@pytest.mark.usefixtures("qt")
def test_settings_last_while_the_user_moves_between_pages() -> None:
    window = open_window()
    window.select_domain("sheet_metal")
    type_into(window.setting_fields["k_factor"][1], "0.44")
    window.select_calculator("sheet_metal.v_die_opening")
    window.select_domain("sheet_metal")
    assert window.setting_fields["k_factor"][1].text() == "0.44"
    window.close()


def test_a_family_with_no_calculators_is_listed_and_marked(qt: Any) -> None:
    from PySide6.QtCore import Qt

    registry = default_registry(load_plugins=False)
    registry.register_domain(ACME)
    window = open_window(registry)
    family = window.tree.topLevelItem(0)
    assert family.text(0) == "Acme Tools"
    placeholder = family.child(0)
    assert (family.childCount(), placeholder.text(0)) == (1, "No calculators loaded")
    assert placeholder.flags() == Qt.ItemFlag.NoItemFlags
    assert window.calculator is not None, "the first calculator is still shown first"

    window.tree.setCurrentItem(family)
    assert window.domain is ACME
    assert "No calculators loaded." in plain(window.domain_note.text())
    assert "Used by: no loaded calculator" in page_text(window.settings_box, qt)
    window.close()
