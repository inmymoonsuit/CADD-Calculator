"""The app's shared commands, one ``QAction`` each (ADR-0015 §5).

The main window's menu bar and the welcome screen's top bar use the same objects, so a
command is defined, enabled, and tested once. Each carries its Qt menu role, so on macOS
Qt moves About, Preferences, and Quit to the application menu, as that platform expects.
"""

from __future__ import annotations

from html import escape

import PySide6
from PySide6.QtCore import QObject, qVersion
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import QApplication, QMenuBar, QMessageBox

from caddcalc import __version__
from caddcalc.core.formatting import DISCLAIMER
from caddcalc.core.i18n import _
from caddcalc.gui.branding import GENERIC, PRODUCT_NAME, Branding

GENERIC_ABOUT = "<p>Open-source calculators for computer-aided drafting and design.</p>"
"""The public build's description in About; a branding pack may replace it."""


def about_html(branding: Branding) -> str:
    """Return the About text: the name and version, the description, and the terms.

    A branding pack replaces the description. The version, the license, the disclaimer,
    the link to the source code, and the third-party credits are always shown.
    """
    return (
        f"<h3>{escape(PRODUCT_NAME)} {escape(__version__)}</h3>"
        + (branding.about_html if branding.about_html is not None else GENERIC_ABOUT)
        + "<p>Licensed under the Apache License, Version 2.0. See LICENSE.md.</p>"
        f"<p>{escape(_(DISCLAIMER))}</p>"
        '<p><a href="https://github.com/inmymoonsuit/CADD-Calculator">'
        "github.com/inmymoonsuit/CADD-Calculator</a></p>"
        '<p>Icons: <a href="https://tabler.io/icons">Tabler Icons</a>, MIT License. '
        'Display typeface: <a href="https://github.com/phoikoi/VT323">VT323</a> by Peter '
        "Hull, SIL Open Font License 1.1. "
        "Third-party notices are in THIRD_PARTY_NOTICES.md.</p>" + qt_credit()
    )


def qt_credit() -> str:
    """Return About's line for Qt and PySide6, at the versions the app runs on.

    LGPL-3.0 §4(c): an app that shows copyright notices while it runs shows the library's,
    with where its license is (THIRD_PARTY_NOTICES.md, "Qt and Qt for Python").
    """
    return (
        f"<p>Built with Qt {escape(qVersion())} and Qt for Python (PySide6) "
        f"{escape(PySide6.__version__)}, © The Qt Company Ltd. and other "
        "contributors, under the GNU LGPL v3. The license texts are in the licenses folder, "
        "and how to replace or rebuild them is in THIRD_PARTY_NOTICES.md.</p>"
    )


class AppActions(QObject):
    """The app-wide commands, shared by every window that shows them.

    About and Quit are handled here, because they concern the whole app; About opens
    over whichever window is active. The main window connects Welcome Screen, which it
    owns. A command that doesn't exist yet, such as Preferences, is ``None`` and no menu
    lists it.
    """

    def __init__(self, branding: Branding = GENERIC, parent: QObject | None = None) -> None:
        """Create the commands for an app shown as ``branding``."""
        super().__init__(parent)
        self.branding = branding
        self.about = QAction(f"&About {PRODUCT_NAME}", self)
        self.about.setMenuRole(QAction.MenuRole.AboutRole)
        self.about.triggered.connect(self.show_about)
        self.quit = QAction("E&xit", self)
        self.quit.setMenuRole(QAction.MenuRole.QuitRole)
        self.quit.setShortcuts(QKeySequence.StandardKey.Quit)
        self.quit.triggered.connect(QApplication.closeAllWindows)
        self.welcome = QAction("&Welcome Screen", self)
        self.welcome.setMenuRole(QAction.MenuRole.NoRole)
        self.preferences: QAction | None = None
        """Preferences…, once the app has preferences (ADR-0015 W3)."""

    def menus(self) -> tuple[tuple[str, tuple[QAction, ...]], ...]:
        """Return the menus in order, File then Help, each with the commands that exist."""
        file_menu = tuple(a for a in (self.preferences, self.quit) if a is not None)
        help_menu = (self.welcome, self.about)
        return (("&File", file_menu), ("&Help", help_menu))

    def fill(self, bar: QMenuBar) -> None:
        """Add the menus to ``bar``."""
        for title, actions in self.menus():
            menu = bar.addMenu(title)
            for action in actions:
                menu.addAction(action)

    def show_about(self) -> None:
        """Show About over the active window: the version, the license, and the terms."""
        QMessageBox.about(
            QApplication.activeWindow(), f"About {PRODUCT_NAME}", about_html(self.branding)
        )
