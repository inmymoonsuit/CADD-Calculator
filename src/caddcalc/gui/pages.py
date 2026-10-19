"""Page containers: the scroll area a page scrolls in, its document, and the page stack.

A calculator's page never clips its results on their own, and never puts a scroll inside a
scroll (ADR-0017 R3, as amended):
* While the page fits the window, its document takes the height that's left, at least its
  least height, and scrolls on its own.
* When the window is too short for the inputs, every result field, and the document's
  least height, the whole page scrolls, and the document shows in full, with no scroll
  bar of its own.
"""

from __future__ import annotations

import math
from typing import override

from PySide6.QtCore import QEvent, QObject, QSize, QSizeF, Qt
from PySide6.QtGui import QResizeEvent
from PySide6.QtWidgets import QFrame, QScrollArea, QStackedWidget, QTextBrowser, QWidget


class PageDocument(QTextBrowser):
    """A page's document: it fills the height the page leaves, or shows in full.

    Its page's ``PageScrollArea`` decides which. Filling, it asks for only ``least``, so a
    page that's laid out at its preferred height gives its room to everything else first.
    In full, it asks for its whole content's height and has no scroll bar.
    """

    def __init__(self, least: int, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.least = least
        """The least height it fills; below that, its page scrolls."""
        self.full = False
        """Whether it shows in full, because its page scrolls."""
        layout = self.document().documentLayout()
        layout.documentSizeChanged.connect(self._on_content_resized)

    def set_full(self, full: bool) -> None:
        """Show in full, with no scroll bar of its own, or fill the height that's left."""
        if full is self.full:
            return
        self.full = full
        bars = Qt.ScrollBarPolicy
        self.setVerticalScrollBarPolicy(bars.ScrollBarAlwaysOff if full else bars.ScrollBarAsNeeded)
        self.updateGeometry()

    def _on_content_resized(self, _size: QSizeF) -> None:
        if self.full:
            self.updateGeometry()  # new content, or a new width: a new full height

    def _height(self) -> int:
        if not self.full:
            return self.least
        return math.ceil(self.document().size().height()) + 2 * self.frameWidth()

    @override
    def sizeHint(self) -> QSize:
        return QSize(super().sizeHint().width(), self._height())

    @override
    def minimumSizeHint(self) -> QSize:
        return QSize(super().minimumSizeHint().width(), self._height())


class PageWidget(QWidget):
    """A page whose least height is its height at its width.

    Its layout's least height takes each part at its narrowest, where wrapped text and a
    stacked row are tallest. A scroll area sizes its page by that least height, so the page
    would scroll for room it doesn't need (ADR-0021 §7).
    """

    @override
    def minimumSizeHint(self) -> QSize:
        hint = super().minimumSizeHint()
        layout = self.layout()
        if layout is None or not layout.hasHeightForWidth() or self.width() <= 0:
            return hint
        return QSize(hint.width(), self.heightForWidth(self.width()))

    @override
    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        if event.size().width() != event.oldSize().width():
            self.updateGeometry()  # a new width: a new least height


def fit_height(page: QWidget, width: int, document: PageDocument | None = None) -> int:
    """Return the height ``page`` fits in at ``width``, with its document at its least.

    It's the least height at which the page doesn't scroll (rule C, ADR-0021 §6).
    """
    needed = _needed_height(page, width)
    if document is None or not document.isVisibleTo(page):
        return needed
    return needed - document.sizeHint().height() + document.least


def _needed_height(page: QWidget, width: int) -> int:
    """The height ``page`` needs at ``width``.

    A page whose height follows its width needs its height at that width, and no more: its
    least height is its height at its narrowest, where wrapped text, such as the disclaimer,
    takes the most lines, so it overstates the need at any other width (ADR-0021 §7).
    """
    layout = page.layout()
    if layout is not None and layout.hasHeightForWidth():
        return page.heightForWidth(width)
    return page.minimumSizeHint().height()


class PageScrollArea(QScrollArea):
    """A frameless area that scrolls its page vertically, and is never narrower than it.

    With no horizontal scrolling, a narrower area would clip the page's right side, so the
    area asks for the page's least width plus room for the vertical scroll bar. It also
    decides whether the page's document fills or shows in full (``PageDocument``).
    """

    def __init__(
        self, page: QWidget, document: PageDocument | None = None, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self.document = document
        self.setWidget(page)
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        # No Tab stop of its own: it would show no focus (WCAG 2.4.7), and Tab already
        # scrolls each focused widget into view.
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

    def _fit(self) -> None:
        """Show the document in full exactly when the page can't fit with it filling."""
        document, page = self.document, self.widget()
        if document is None or page is None or not document.isVisibleTo(page):
            return
        view = self.viewport()
        document.set_full(fit_height(page, view.width(), document) > view.height())

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
    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self._fit()

    @override
    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if watched is self.widget() and event.type() == QEvent.Type.LayoutRequest:
            # The page's sizes changed (another calculator, new results, a document's
            # new full height): pass its least width on, and fit its document again.
            self.updateGeometry()
            self._fit()
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
