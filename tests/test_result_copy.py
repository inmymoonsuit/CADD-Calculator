"""Copying results: the copy button, its keys and menu, Copy all, and what's said (ADR-0017)."""

from __future__ import annotations

from dataclasses import replace
from itertools import pairwise
from typing import Any, override

import pytest

from caddcalc.core.formatting import DisplayPrefs, results_tsv
from tests.qt_helpers import open_window, type_into

pytestmark = [pytest.mark.gui, pytest.mark.usefixtures("qt")]

BEND = "sheet_metal.bend_allowance"


def _clipboard() -> Any:
    from PySide6.QtGui import QGuiApplication

    return QGuiApplication.clipboard()


def _bend_window() -> Any:
    """Bend allowance with the course method: BA = 0.3119 in."""
    window = open_window()
    window.select_calculator(BEND)
    window.method_box.setCurrentIndex(window.method_box.findData("course"))
    _clipboard().clear()
    return window


def _icon_is(button: Any, name: str) -> bool:
    from caddcalc.gui.icons import icon

    return bool(button.icon().cacheKey() == icon(name, "icon").cacheKey())


def test_the_copy_button_copies_the_value_as_shown_and_shows_a_check() -> None:
    """R1 and R4: the number as shown, the check in place, and the status bar says so."""
    from caddcalc.gui.ui_style import ui_style

    tokens = ui_style().result_field
    window = _bend_window()
    field = window.results.fields["bend_allowance"]
    button = field.copy_button
    assert _icon_is(button, tokens.copy_icon)
    button.click()
    assert _clipboard().text() == "0.3119"
    assert field.copied_state.showing and _icon_is(button, tokens.copied_icon)
    assert window.statusBar().currentMessage() == "Copied BA = 0.3119 to the clipboard"
    timer = field.copied_state.timer
    assert timer.isSingleShot() and timer.interval() == tokens.copied_ms
    timer.stop()
    timer.timeout.emit()  # as it fires after copied_ms
    assert _icon_is(button, tokens.copy_icon), "the copy icon comes back"
    window.close()


@pytest.mark.parametrize(
    ("key", "modifiers"),
    [("Key_Space", "NoModifier"), ("Key_Return", "NoModifier"), ("Key_Enter", "KeypadModifier")],
)
def test_space_and_enter_copy_from_the_focused_button(key: str, modifiers: str) -> None:
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest

    window = _bend_window()
    button = window.results.fields["outside_setback"].copy_button
    QTest.keyClick(button, getattr(Qt.Key, key), getattr(Qt.KeyboardModifier, modifiers))
    assert _clipboard().text() == "0.2606"
    window.close()


def test_the_platforms_copy_keys_copy_the_focused_fields_value() -> None:
    from PySide6.QtGui import QKeySequence
    from PySide6.QtTest import QTest

    window = _bend_window()
    button = window.results.fields["bend_deduction"].copy_button
    (copy,) = QKeySequence.keyBindings(QKeySequence.StandardKey.Copy)[:1]
    QTest.keyClick(button, copy[0].key(), copy[0].keyboardModifiers())
    assert _clipboard().text() == "0.2093"
    window.close()


def test_the_context_menu_offers_each_form_and_the_fraction_only_when_shown() -> None:
    """R6: value, with unit, full precision, and the fraction as 5/16" when it's shown."""
    window = _bend_window()
    field = window.results.fields["bend_allowance"]
    menu = field.context_menu()
    texts = [a.text() for a in menu.actions()]
    assert texts == ["Copy value", "Copy with unit", "Copy full precision"]
    menu.actions()[1].trigger()
    assert _clipboard().text() == "0.3119 in"
    menu.actions()[2].trigger()
    assert _clipboard().text() == "0.311864", "the display unit, unrounded, 10 digits at most"
    window.prefs = replace(window.prefs, fraction_denominator=16)
    window.recompute()
    menu = field.context_menu()
    assert [a.text() for a in menu.actions()][-1] == "Copy fraction"
    menu.actions()[-1].trigger()
    assert _clipboard().text() == '5/16"', "with the inch mark, so it isn't read as a date"
    window.close()


def test_right_click_and_the_menu_key_open_the_menu() -> None:
    from PySide6.QtCore import QPoint
    from PySide6.QtGui import QContextMenuEvent
    from PySide6.QtWidgets import QApplication, QMenu

    window = _bend_window()
    window.show()
    field = window.results.fields["bend_allowance"]

    def shown() -> list[QMenu]:
        return [menu for menu in field.findChildren(QMenu) if menu.isVisible()]

    at = QPoint(4, 4)
    QApplication.sendEvent(
        field, QContextMenuEvent(QContextMenuEvent.Reason.Mouse, at, field.mapToGlobal(at))
    )
    (menu,) = shown()
    assert menu.actions()[0].text() == "Copy value"
    menu.close()
    QApplication.processEvents()
    assert shown() == []
    # The Menu key goes to the focused copy button, which passes it to its field.
    button = field.copy_button
    key = QContextMenuEvent(
        QContextMenuEvent.Reason.Keyboard, QPoint(0, 0), button.mapToGlobal(QPoint(0, 0))
    )
    QApplication.sendEvent(button, key)
    assert len(shown()) == 1
    window.close()


def test_copy_all_copies_spreadsheet_rows_from_its_button_and_the_window_keys() -> None:
    """R2: one tab-separated row per output; Ctrl+Shift+C from anywhere in the window."""
    from PySide6.QtCore import Qt

    from caddcalc.gui.result_fields import COPY_ALL_KEYS

    window = _bend_window()
    expected = results_tsv(window.calculator, window.result, window.prefs)
    window.results.copy_all_button.click()
    assert _clipboard().text() == expected
    assert window.statusBar().currentMessage() == "Copied all results to the clipboard"
    _clipboard().clear()
    action = window.copy_all_action
    assert action.shortcut() == COPY_ALL_KEYS and action in window.actions()
    assert action.shortcutContext() == Qt.ShortcutContext.WindowShortcut
    action.trigger()
    assert _clipboard().text() == expected
    window.select_domain("sheet_metal")
    _clipboard().clear()
    action.trigger()
    assert _clipboard().text() == "", "only while a calculator's results show"
    window.close()


def test_each_copy_is_announced_to_screen_readers(monkeypatch: pytest.MonkeyPatch) -> None:
    from PySide6.QtGui import QAccessible

    said: list[tuple[str, Any]] = []
    monkeypatch.setattr(
        QAccessible,
        "updateAccessibility",
        lambda event: said.append((event.message(), event.politeness())),
    )
    window = _bend_window()
    window.results.fields["bend_allowance"].copy_button.click()
    window.results.copy_all_button.click()
    polite = QAccessible.AnnouncementPoliteness.Polite
    assert said == [
        ("Copied BA = 0.3119 to the clipboard", polite),
        ("Copied all results to the clipboard", polite),
    ]
    window.close()


def test_fields_and_buttons_have_names_a_screen_reader_says_in_full() -> None:
    """§5, with the localization notes: whole messages, labels as written, units spoken."""
    window = _bend_window()
    field = window.results.fields["bend_allowance"]
    assert field.accessibleName() == "Bend allowance, BA: 0.3119 inches"
    assert field.copy_button.accessibleName() == "Copy Bend allowance"
    assert field.copy_button.toolTip() == "Copy Bend allowance", "the label as written"
    assert field.copy_button.accessibleDescription() == "BA: 0.3119 inches", "not the label twice"
    assert window.results.copy_all_button.accessibleName() == "Copy all results"
    window.select_calculator("sheet_metal.truncated_cone_layout")
    angle = window.results.fields["sweep_angle"]
    assert angle.accessibleName() == "Flat pattern angle, FPA: 132.70 degrees"
    window.close()


def _next_tab_stop(widget: Any) -> Any:
    """The next widget in the focus chain that Tab stops at, as Qt finds it."""
    from PySide6.QtCore import Qt

    window = widget.window()
    after = widget.nextInFocusChain()
    while after is not widget:
        takes_tab = bool(after.focusPolicy() & Qt.FocusPolicy.TabFocus)
        if takes_tab and after.isEnabled() and after.isVisibleTo(window):
            return after
        after = after.nextInFocusChain()
    return None


def test_tab_goes_down_the_page_from_the_inputs_to_the_document() -> None:
    """Inputs, each copy button, Copy all, then the document (UI/UX's k4 M3)."""
    from PySide6.QtCore import Qt

    window = _bend_window()
    stops = [edit for _p, edit in window.fields.values()]
    stops += [f.copy_button for f in window.results.fields.values()]
    stops += [window.results.copy_all_button, window.output]
    for before, after in pairwise(stops):
        assert _next_tab_stop(before) is after, (before, after)
    assert window.page_scroll.focusPolicy() == Qt.FocusPolicy.NoFocus, "no focus-less stop"
    window.close()


def test_a_focused_copy_button_draws_no_focus_of_its_own() -> None:
    """Its field's ring is the one focus indicator (UI/UX's k4 M2).

    Whether a style draws a tool button's focus varies by style and platform, so this
    checks what the button asks its style to draw: a field's button never asks for
    focus, and Copy all, which has no ring, still does. The next test checks the pixels.
    """
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication, QProxyStyle, QStyle

    class Recording(QProxyStyle):
        def __init__(self) -> None:
            super().__init__()
            self.focused: list[bool] = []

        @override
        def drawComplexControl(
            self, control: Any, option: Any, painter: Any, widget: Any = None
        ) -> None:
            if control == QStyle.ComplexControl.CC_ToolButton:
                self.focused.append(bool(option.state & QStyle.StateFlag.State_HasFocus))
            super().drawComplexControl(control, option, painter, widget)

    window = _bend_window()
    window.show()
    window.activateWindow()
    QApplication.processEvents()
    for button, asks in (
        (window.results.fields["bend_allowance"].copy_button, False),
        (window.results.copy_all_button, True),
    ):
        style = Recording()
        button.setStyle(style)
        button.setFocus(Qt.FocusReason.TabFocusReason)
        QApplication.processEvents()
        assert button.hasFocus()
        button.grab()
        assert style.focused and set(style.focused) == {asks}, button.accessibleName()
    window.close()


def _pixels_tab_changes(button: Any, before: Any) -> int:
    """How many of ``button``'s pixels change as Tab brings the focus to it from ``before``.

    A Tab key press, unlike ``setFocus()``, sets the window's keyboard-focus flag, which
    is what styles draw a tool button's focus for.
    """
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication

    before.setFocus(Qt.FocusReason.OtherFocusReason)
    QApplication.processEvents()
    plain = button.grab().toImage()
    QTest.keyClick(before, Qt.Key.Key_Tab)
    QApplication.processEvents()
    assert button.hasFocus(), button.accessibleName()
    focused = button.grab().toImage()
    size = range(plain.width()), range(plain.height())
    return sum(plain.pixel(x, y) != focused.pixel(x, y) for x in size[0] for y in size[1])


@pytest.mark.parametrize("style_name", ["Fusion", "windows11"])
def test_tabbing_to_a_copy_button_paints_no_focus_but_the_ring(style_name: str) -> None:
    """The painting itself (UI/UX's k6 L2): a field's button is unchanged; Copy all isn't."""
    from PySide6.QtWidgets import QApplication, QStyleFactory

    style = QStyleFactory.create(style_name)
    if style is None:
        pytest.skip(f"no {style_name} style on this platform")
    window = _bend_window()
    window.show()
    window.activateWindow()
    QApplication.processEvents()
    last_input = list(window.fields.values())[-1][1]
    fields = list(window.results.fields.values())
    for button in (fields[0].copy_button, window.results.copy_all_button):
        button.setStyle(style)
    assert _pixels_tab_changes(fields[0].copy_button, last_input) == 0
    copy_all = window.results.copy_all_button
    assert _pixels_tab_changes(copy_all, fields[-1].copy_button) > 0, "the style's own focus"
    window.close()


def test_the_copied_message_stays_long_enough_to_read(monkeypatch: pytest.MonkeyPatch) -> None:
    """The check shows for copied_ms; the status bar's words for longer (UI/UX's k4 L1)."""
    from caddcalc.gui.ui_style import ui_style

    tokens = ui_style().result_field
    window = _bend_window()
    shown: list[tuple[str, int]] = []
    # On the class, not the window's status bar: undoing a patch on a Qt object after the
    # window is deleted writes to a deleted object, which crashes on Linux.
    from PySide6.QtWidgets import QStatusBar

    def record(_bar: Any, text: str, ms: int = 0) -> None:
        shown.append((text, ms))

    monkeypatch.setattr(QStatusBar, "showMessage", record)
    window.results.fields["bend_allowance"].copy_button.click()
    assert shown == [("Copied BA = 0.3119 to the clipboard", tokens.copied_status_ms)]
    assert tokens.copied_status_ms > tokens.copied_ms
    window.close()


def test_nothing_stale_is_copied_while_the_inputs_have_no_result() -> None:
    """§4: every button is disabled, and copying does nothing, until a result is back."""
    window = _bend_window()
    _clipboard().setText("before")
    type_into(window.fields["thickness"][1], "abc", enter=False)
    field = window.results.fields["bend_allowance"]
    assert not field.copy_button.isEnabled() and not window.results.copy_all_button.isEnabled()
    assert field.copy() is None and window.results.copy_all() is None
    window.copy_all_action.trigger()
    assert _clipboard().text() == "before"
    assert field.accessibleName() == "Bend allowance, BA: no value"
    assert all(not a.isEnabled() for a in field.context_menu().actions())
    window.close()


def test_a_plugin_calculator_copies_with_no_code_of_its_own() -> None:
    from caddcalc.core import Registry
    from caddcalc.gui.window import MainWindow
    from tests.test_domains import ACME, _AcmeWidget

    registry = Registry()
    registry.register_domain(ACME)
    registry.register(_AcmeWidget)
    window = MainWindow(registry=registry)
    window.select_calculator("acme.widget")
    (field,) = window.results.fields.values()
    field.copy_button.click()
    assert _clipboard().text() == "1.0000"
    assert window.results.copy_all() == results_tsv(
        window.calculator, window.result, DisplayPrefs()
    )
    window.close()
