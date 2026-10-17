"""The app's shared commands (ADR-0015 §5). Skipped when PySide6 is not installed."""

from __future__ import annotations

from typing import Any

import pytest

from caddcalc.gui.branding import Branding
from tests.qt_helpers import open_window

pytestmark = [pytest.mark.gui, pytest.mark.usefixtures("qt")]


def menu_layout(window: Any) -> list[tuple[str, list[str]]]:
    bar = window.menuBar()
    return [
        (action.text(), [item.text() for item in action.menu().actions()])
        for action in bar.actions()
    ]


def test_each_command_carries_its_macos_menu_role() -> None:
    from PySide6.QtGui import QAction, QKeySequence

    from caddcalc.gui.actions import AppActions

    actions = AppActions(Branding(name="Shop & Co"))
    assert actions.about.text() == "&About Shop && Co"
    assert actions.about.menuRole() is QAction.MenuRole.AboutRole
    assert actions.quit.menuRole() is QAction.MenuRole.QuitRole
    assert actions.quit.shortcuts() == QKeySequence.keyBindings(QKeySequence.StandardKey.Quit)
    assert actions.welcome.menuRole() is QAction.MenuRole.NoRole
    assert actions.preferences is None, "there are no preferences yet"


def test_menus_list_only_the_commands_that_exist() -> None:
    from caddcalc.gui.actions import AppActions

    actions = AppActions()
    assert [(t, [a.text() for a in items]) for t, items in actions.menus()] == [
        ("&File", ["E&xit"]),
        ("&Help", ["&Welcome Screen", "&About CADD Calculator"]),
    ]


def test_the_main_window_shows_the_shared_commands() -> None:
    from caddcalc.gui.actions import AppActions

    window = open_window()
    assert menu_layout(window) == [
        ("&File", ["E&xit"]),
        ("&Help", ["&Welcome Screen", "&About CADD Calculator"]),
    ]
    shared = AppActions(window.branding)
    other = type(window)(window.registry, actions=shared)
    assert other.app_actions is shared
    assert other.menuBar().actions()[1].menu().actions() == [shared.welcome, shared.about]
    other.close()
    window.close()


def test_exit_closes_every_window(monkeypatch: pytest.MonkeyPatch) -> None:
    window = open_window()
    window.show()
    closed: list[bool] = []
    monkeypatch.setattr(type(window), "closeEvent", lambda _self, _event: closed.append(True))
    window.app_actions.quit.trigger()
    assert closed == [True]
    window.close()


def test_about_shows_over_the_active_window(monkeypatch: pytest.MonkeyPatch) -> None:
    from PySide6.QtWidgets import QMessageBox

    window = open_window()
    shown: list[tuple[Any, str]] = []
    monkeypatch.setattr(
        QMessageBox, "about", lambda parent, title, _text: shown.append((parent, title))
    )
    window.app_actions.about.trigger()
    assert shown == [(window, "About CADD Calculator")]
    window.close()
