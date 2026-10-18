"""Helpers for GUI tests: open a window and use it the way a person does.

Qt is imported inside each helper, so modules that import these still collect when
PySide6 isn't installed; their tests skip through the ``qt`` fixture.
"""

from __future__ import annotations

from typing import Any

from caddcalc.calculators import default_registry
from caddcalc.core import Registry


def open_window(registry: Registry | None = None) -> Any:
    """A main window over the built-ins (no plugins), or over ``registry``.

    It's placed on the primary screen. Shown unplaced, a window opens on the pointer's
    screen, and on a desktop of mixed scales, Windows resizes it for that screen's
    scale, so a native run's sizes would depend on where the pointer is.
    """
    from PySide6.QtGui import QGuiApplication

    from caddcalc.gui.window import MainWindow

    window = MainWindow(default_registry(load_plugins=False) if registry is None else registry)
    screen = QGuiApplication.primaryScreen()
    if screen is not None:
        window.setScreen(screen)
        window.move(screen.availableGeometry().topLeft())
    return window


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


def results_text(window: Any) -> str:
    """What a calculator page's results show: each result field's line, then the document.

    A field's line is its symbol, its label, and its value as shown, e.g.
    ``BA Bend allowance 0.3119 in``, or ``—`` while there's no value (ADR-0017).
    """
    lines = [
        f"{field.output.symbol} {field.output.label} "
        f"{'—' if field.parts is None else field.parts.with_unit}"
        for field in window.results.fields.values()
    ]
    return "\n".join([*lines, window.output.toPlainText()])


def settle(window: Any) -> None:
    """Run the event loop until the page's layout stops changing.

    Each layout pass can post the next, from the document up to the page area, and a
    few passes can go by with nothing to see, so it waits for several quiet passes.
    """
    from PySide6.QtWidgets import QApplication

    def state() -> tuple[int, int, int]:
        page = window.page_scroll
        bar = page.verticalScrollBar().maximum()
        return (bar, page.widget().height(), window.output.height())

    last, same = None, 0
    for _ in range(100):
        QApplication.processEvents()
        now = state()
        same = same + 1 if now == last else 0
        if same == 8:
            return
        last = now
    raise AssertionError("the page's layout never settled")
