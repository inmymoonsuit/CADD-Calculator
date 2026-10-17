"""The app's shared commands, one ``QAction`` each (ADR-0015 §5).

The main window's menu bar and the welcome screen's top bar use the same objects, so a
command is defined, enabled, and tested once. Each carries its Qt menu role, so on macOS
Qt moves About, Preferences, and Quit to the application menu, as that platform expects.
"""

from __future__ import annotations

from PySide6.QtCore import QObject
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import QApplication, QMenuBar

from caddcalc.gui.branding import GENERIC, Branding


class AppActions(QObject):
    """The app-wide commands, shared by every window that shows them.

    Quit is handled here, because it concerns the whole app. The window that owns a
    command's dialog connects the others: the main window shows About. A command that
    doesn't exist yet, such as Preferences, is ``None`` and no menu lists it.
    """

    def __init__(self, branding: Branding = GENERIC, parent: QObject | None = None) -> None:
        """Create the commands for an app shown as ``branding``."""
        super().__init__(parent)
        self.about = QAction(f"&About {branding.name.replace('&', '&&')}", self)
        self.about.setMenuRole(QAction.MenuRole.AboutRole)
        self.quit = QAction("E&xit", self)
        self.quit.setMenuRole(QAction.MenuRole.QuitRole)
        self.quit.setShortcuts(QKeySequence.StandardKey.Quit)
        self.quit.triggered.connect(QApplication.closeAllWindows)
        self.preferences: QAction | None = None
        """Preferences…, once the app has preferences (ADR-0015 W3)."""
        self.welcome: QAction | None = None
        """Help > Welcome Screen, once the welcome screen exists."""

    def menus(self) -> tuple[tuple[str, tuple[QAction, ...]], ...]:
        """Return the menus in order, File then Help, each with the commands that exist."""
        file_menu = tuple(a for a in (self.preferences, self.quit) if a is not None)
        help_menu = tuple(a for a in (self.welcome, self.about) if a is not None)
        return (("&File", file_menu), ("&Help", help_menu))

    def fill(self, bar: QMenuBar) -> None:
        """Add the menus to ``bar``."""
        for title, actions in self.menus():
            menu = bar.addMenu(title)
            for action in actions:
                menu.addAction(action)
