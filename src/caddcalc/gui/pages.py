"""Page containers: the scroll area a page scrolls in, and a stack sized to its shown page.

A calculator's page never clips its results on their own: when the window is too short for
the inputs, every result field, and the document's least height, the whole page scrolls
(ADR-0017 R3, as amended).
"""

from __future__ import annotations

from typing import override

from PySide6.QtCore import QEvent, QObject, QSize, Qt
from PySide6.QtWidgets import QFrame, QScrollArea, QStackedWidget, QWidget


class PageScrollArea(QScrollArea):
    """A frameless area that scrolls its page vertically, and is never narrower than it.

    With no horizontal scrolling, a narrower area would clip the page's right side, so the
    area asks for the page's least width plus room for the vertical scroll bar.
    """

    def __init__(self, page: QWidget, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWidget(page)
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

    @override
    def minimumSizeHint(self) -> QSize:
        hint = super().minimumSizeHint()
        page = self.widget()
        if page is None:
            return hint
        bar = self.verticalScrollBar().sizeHint().width()
        width = page.minimumSizeHint().width() + bar + 2 * self.frameWidth()
        return QSize(max(hint.width(), width), hint.height())

    @override
    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        # The page's least width can change (another calculator's form); pass it on.
        if watched is self.widget() and event.type() == QEvent.Type.LayoutRequest:
            self.updateGeometry()
        return super().eventFilter(watched, event)


class PageStack(QStackedWidget):
    """A stack of pages whose height follows the shown page alone.

    A plain stack asks for its tallest page's height, so in a page scroll area a short
    page would scroll for a long page that isn't shown. Width still takes every page, so
    the window's least width doesn't change as pages change.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.currentChanged.connect(self._on_current_changed)

    def _on_current_changed(self, _index: int) -> None:
        self.updateGeometry()

    @override
    def sizeHint(self) -> QSize:
        page = self.currentWidget()
        hint = super().sizeHint()
        return hint if page is None else QSize(hint.width(), page.sizeHint().height())

    @override
    def minimumSizeHint(self) -> QSize:
        page = self.currentWidget()
        hint = super().minimumSizeHint()
        return hint if page is None else QSize(hint.width(), page.minimumSizeHint().height())
