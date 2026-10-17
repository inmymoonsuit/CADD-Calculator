"""Helpers for GUI tests: open a window and use it the way a person does.

Qt is imported inside each helper, so modules that import these still collect when
PySide6 isn't installed; their tests skip through the ``qt`` fixture.
"""

from __future__ import annotations

from typing import Any

from caddcalc.calculators import default_registry
from caddcalc.core import Registry


def open_window(registry: Registry | None = None) -> Any:
    """A main window over the built-ins (no plugins), or over ``registry``."""
    from caddcalc.gui.window import MainWindow

    return MainWindow(registry or default_registry(load_plugins=False))


def type_into(edit: Any, text: str, *, enter: bool = True) -> None:
    """Replace a field's text by typing it, then press Enter unless told not to."""
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest

    edit.selectAll()
    if text:
        QTest.keyClicks(edit, text)
    else:
        QTest.keyClick(edit, Qt.Key.Key_Backspace)
    if enter:
        QTest.keyClick(edit, Qt.Key.Key_Return)


def plain(html: str) -> str:
    """The text a rich-text label shows."""
    from PySide6.QtGui import QTextDocument

    document = QTextDocument()
    document.setHtml(html)
    return document.toPlainText()


def page_text(widget: Any) -> str:
    """The text of every label inside ``widget``."""
    from PySide6.QtWidgets import QLabel

    return "\n".join(plain(label.text()) for label in widget.findChildren(QLabel))
