"""Focus on an outlined input: the outline stays and the ring adds to it (WCAG 2.4.7)."""

from __future__ import annotations

from typing import Any

import pytest

from tests.qt_helpers import open_window, type_into

pytestmark = [pytest.mark.gui, pytest.mark.usefixtures("qt")]


def _outlined_window() -> Any:
    """Bend allowance with R < T, so a note outlines thickness and inside radius."""
    from PySide6.QtWidgets import QApplication

    window = open_window()
    window.select_calculator("sheet_metal.bend_allowance")
    type_into(window.fields["thickness"][1], "0.25")
    type_into(window.fields["inside_radius"][1], "0.1")
    window.show()
    window.activateWindow()
    QApplication.processEvents()
    return window


def _focus(edit: Any) -> None:
    from PySide6.QtWidgets import QApplication

    edit.setFocus()
    QApplication.processEvents()
    assert edit.hasFocus()


def test_a_focused_outlined_input_keeps_its_outline_and_gains_the_focus_ring() -> None:
    from caddcalc.gui.focus_ring import OUTLINED
    from caddcalc.gui.icons import current_scheme, role_color
    from caddcalc.gui.ui_style import ui_style

    tokens = ui_style().result_field
    window = _outlined_window()
    edit = window.fields["thickness"][1]
    assert edit.property(OUTLINED) and ":focus" not in edit.styleSheet(), "no :focus rule"
    _focus(edit)
    ring = window.focus_ring
    assert ring.isVisible() and ring.target is edit and ring.parentWidget() is edit.parentWidget()
    image = edit.parentWidget().grab().toImage()
    box = edit.geometry()
    x = box.center().x()
    scheme = current_scheme()
    outline = role_color("outline_note", scheme)
    focus = role_color(tokens.focus_role, scheme)
    assert image.pixelColor(x, box.top()).name().upper() == outline, "the note's outline stays"
    gap, width = round(tokens.focus_gap), round(tokens.focus_width)
    assert image.pixelColor(x, box.top() - gap).name().upper() != focus, "the gap"
    for row in range(gap + 1, gap + width + 1):
        assert image.pixelColor(x, box.top() - row).name().upper() == focus, row
        assert image.pixelColor(box.left() - row, box.center().y()).name().upper() == focus
    window.close()


def test_the_ring_follows_focus_and_outlines() -> None:
    window = _outlined_window()
    ring = window.focus_ring
    _focus(window.fields["thickness"][1])
    assert ring.isVisible()
    _focus(window.fields["bend_angle"][1])
    assert not ring.isVisible(), "an input without an outline keeps its native focus"
    radius = window.fields["inside_radius"][1]
    _focus(radius)
    assert ring.isVisible() and ring.target is radius
    type_into(radius, "0.3")  # R > T: the note, and so the outline, goes
    assert not ring.isVisible()
    type_into(radius, "abc", enter=False)  # an error outline comes
    assert ring.isVisible() and ring.target is radius
    window.close()


def test_a_settings_field_with_an_error_gets_the_ring_too() -> None:
    from PySide6.QtWidgets import QApplication

    window = open_window()
    window.select_domain("sheet_metal")
    window.show()
    window.activateWindow()
    QApplication.processEvents()
    edit = window.setting_fields["thickness"][1]
    _focus(edit)
    type_into(edit, "abc", enter=False)
    assert window.focus_ring.isVisible() and window.focus_ring.target is edit
    window.close()
