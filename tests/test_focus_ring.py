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


def _raised(monkeypatch: pytest.MonkeyPatch) -> list[BaseException]:
    """Collect what a slot raises: Qt hands it to ``sys.excepthook`` rather than up."""
    import sys

    raised: list[BaseException] = []
    monkeypatch.setattr(sys, "excepthook", lambda _type, exc, _tb: raised.append(exc))
    return raised


def test_a_rebuild_while_the_ring_shows_leaves_results_live(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Units changed while an outlined input has focus rebuild the form."""
    raised = _raised(monkeypatch)
    window = _outlined_window()
    _focus(window.fields["thickness"][1])
    assert window.focus_ring.isVisible()
    window.units_box.setCurrentText("mm")  # rebuilds the form, deleting the ringed input
    assert window.focus_ring.target is None or window.focus_ring.target in [
        e for _p, e in window.fields.values()
    ]
    before = window.result.outputs["bend_allowance"]
    type_into(window.fields["inside_radius"][1], "8")  # R > T: a new run, a new result
    assert window.result.outputs["bend_allowance"] != pytest.approx(before)
    assert window.results.fields["bend_allowance"].parts is not None
    window.select_calculator("sheet_metal.segment_flat_length")  # another rebuild
    window.select_calculator("sheet_metal.bend_allowance")
    assert raised == []
    window.close()


@pytest.mark.parametrize("ringing", [False, True])
def test_the_ring_is_deleted_with_its_window(ringing: bool) -> None:
    """The window owns the ring, so it never outlives it (KI-019)."""
    from PySide6.QtCore import QEvent
    from PySide6.QtWidgets import QApplication
    from shiboken6 import isValid

    window = _outlined_window()
    if ringing:
        _focus(window.fields["thickness"][1])
        assert window.focus_ring.parentWidget() is window.fields["thickness"][1].parentWidget()
    ring = window.focus_ring
    window.close()
    window.deleteLater()
    QApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    assert not isValid(window) and not isValid(ring)


def test_closing_the_window_while_an_outlined_input_has_focus_is_clean(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The ring's lifecycle: close with the ring showing, then use another window."""
    from PySide6.QtCore import QEvent
    from PySide6.QtWidgets import QApplication

    raised = _raised(monkeypatch)
    first = _outlined_window()
    _focus(first.fields["thickness"][1])
    first.close()
    first.deleteLater()
    QApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    second = _outlined_window()
    _focus(second.fields["inside_radius"][1])
    _focus(second.fields["bend_angle"][1])
    assert raised == [] and not second.focus_ring.isVisible()
    second.close()
