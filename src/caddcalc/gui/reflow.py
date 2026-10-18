"""Widgets side by side while they fit, and one above another when they don't (ADR-0021 §7).

A pair of choice boxes, or a method box and its status, would otherwise make a page as
wide as both together, so a narrow window would cut them off or scroll sideways.
"""

from __future__ import annotations

from typing import override

from PySide6.QtCore import QSize
from PySide6.QtGui import QResizeEvent
from PySide6.QtWidgets import QBoxLayout, QWidget


class Reflow(QWidget):
    """Lays out its widgets in a row while each gets its preferred width, else in a column.

    Its least width is its widest widget's least width, as a column, so it never makes its
    page wider than one of them. Its height follows its width.
    """

    def __init__(self, parent: QWidget | None = None, *, spacing: int = 6) -> None:
        super().__init__(parent)
        self._box = QBoxLayout(QBoxLayout.Direction.LeftToRight, self)
        self._box.setContentsMargins(0, 0, 0, 0)
        self._box.setSpacing(spacing)
        self._widgets: list[QWidget] = []

    def add(self, widget: QWidget, stretch: int = 0) -> None:
        """Add ``widget``; in a row, it takes ``stretch`` of the room beyond the widths."""
        self._box.addWidget(widget, stretch)
        self._widgets.append(widget)
        self._arrange(self.width())

    @property
    def stacked(self) -> bool:
        """Whether its widgets are one above another."""
        return self._box.direction() is QBoxLayout.Direction.TopToBottom

    def _shown(self) -> list[QWidget]:
        return [w for w in self._widgets if not w.isHidden()]

    def row_width(self) -> int:
        """The width its widgets need side by side, each at its preferred width."""
        shown = self._shown()
        spacing = self._box.spacing() * max(0, len(shown) - 1)
        return sum(w.sizeHint().width() for w in shown) + spacing

    def _arrange(self, width: int) -> None:
        wanted = (
            QBoxLayout.Direction.LeftToRight
            if width >= self.row_width()
            else QBoxLayout.Direction.TopToBottom
        )
        if self._box.direction() is not wanted:
            self._box.setDirection(wanted)
            self.updateGeometry()

    def _height(self, width: int, *, stacked: bool) -> int:
        shown = self._shown()
        if not shown:
            return 0
        heights = [
            w.heightForWidth(width) if stacked and w.hasHeightForWidth() else w.sizeHint().height()
            for w in shown
        ]
        if not stacked:
            return max(heights)
        return sum(heights) + self._box.spacing() * (len(shown) - 1)

    @override
    def sizeHint(self) -> QSize:
        width = self.row_width()
        return QSize(width, self._height(width, stacked=False))

    @override
    def minimumSizeHint(self) -> QSize:
        shown = self._shown()
        width = max((w.minimumSizeHint().width() for w in shown), default=0)
        return QSize(width, self._height(width, stacked=True))

    @override
    def hasHeightForWidth(self) -> bool:
        return True

    @override
    def heightForWidth(self, width: int) -> int:
        return self._height(width, stacked=width < self.row_width())

    @override
    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self._arrange(event.size().width())
