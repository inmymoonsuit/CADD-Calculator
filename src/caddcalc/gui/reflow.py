"""Widgets side by side while they fit, and one above another when they don't (ADR-0021 §7).

A pair of choice boxes, or a method box and its status, would otherwise make a page as
wide as both together, so a narrow window would cut them off or scroll sideways.

It's a layout, not a widget that measures itself: Qt asks a widget's layout for its height
at a width, so only a layout's height-for-width reaches the layouts around it.
"""

from __future__ import annotations

from typing import override

from PySide6.QtCore import QRect, QSize, Qt
from PySide6.QtWidgets import QFormLayout, QLabel, QLayout, QLayoutItem, QWidget, QWidgetItem
from shiboken6 import isValid


class ReflowLayout(QLayout):
    """Its items in a row while each gets its preferred width, else in a column.

    In a row, the room beyond the items' preferred widths goes to them by their stretch.
    In a column, each takes the whole width. Its least width is its widest item's, so it
    never makes its page wider than one of them, and its height follows its width.
    """

    def __init__(self, parent: QWidget | None = None, *, spacing: int = 6) -> None:
        super().__init__(parent)
        self.setContentsMargins(0, 0, 0, 0)
        self.setSpacing(spacing)
        self._items: list[QLayoutItem] = []
        self._stretch: list[int] = []

    def add(self, widget: QWidget, stretch: int = 0) -> None:
        """Add ``widget``; in a row, it takes ``stretch`` of the room beyond the widths."""
        self.addChildWidget(widget)
        self._items.append(QWidgetItem(widget))
        self._stretch.append(stretch)
        self.invalidate()

    @override
    def addItem(self, item: QLayoutItem) -> None:
        self._items.append(item)
        self._stretch.append(0)

    @override
    def count(self) -> int:
        return len(self._items)

    @override
    def itemAt(self, index: int) -> QLayoutItem | None:
        return self._items[index] if 0 <= index < len(self._items) else None

    @override
    def takeAt(self, index: int) -> QLayoutItem | None:
        if not 0 <= index < len(self._items):
            return None
        self._stretch.pop(index)
        return self._items.pop(index)

    @override
    def expandingDirections(self) -> Qt.Orientation:
        return Qt.Orientation.Horizontal

    def _shown(self) -> list[tuple[QLayoutItem, int]]:
        return [(i, s) for i, s in zip(self._items, self._stretch, strict=True) if not i.isEmpty()]

    def row_width(self) -> int:
        """The width its items need side by side, each at its preferred width."""
        shown = self._shown()
        spacing = self.spacing() * max(0, len(shown) - 1)
        return sum(item.sizeHint().width() for item, _s in shown) + spacing

    def stacked_at(self, width: int) -> bool:
        """Whether its items are one above another at ``width``."""
        return width < self.row_width()

    @override
    def sizeHint(self) -> QSize:
        shown = self._shown()
        height = max((item.sizeHint().height() for item, _s in shown), default=0)
        return QSize(self.row_width(), height)

    @override
    def minimumSize(self) -> QSize:
        shown = self._shown()
        width = max((item.minimumSize().width() for item, _s in shown), default=0)
        return QSize(width, self._column_height(width))

    @override
    def hasHeightForWidth(self) -> bool:
        return True

    @override
    def heightForWidth(self, width: int) -> int:
        if self.stacked_at(width):
            return self._column_height(width)
        return self.sizeHint().height()

    def _item_height(self, item: QLayoutItem, width: int) -> int:
        if item.hasHeightForWidth():
            return item.heightForWidth(width)
        return item.sizeHint().height()

    def _column_height(self, width: int) -> int:
        shown = self._shown()
        heights = [self._item_height(item, width) for item, _s in shown]
        return sum(heights) + self.spacing() * max(0, len(shown) - 1)

    @override
    def setGeometry(self, rect: QRect) -> None:
        super().setGeometry(rect)
        shown = self._shown()
        if not shown:
            return
        if self.stacked_at(rect.width()):
            y = rect.y()
            for item, _stretch in shown:
                height = self._item_height(item, rect.width())
                item.setGeometry(QRect(rect.x(), y, rect.width(), height))
                y += height + self.spacing()
            return
        room = rect.width() - self.row_width()
        total = sum(s for _i, s in shown)
        x = rect.x()
        for index, (item, stretch) in enumerate(shown):
            extra = room * stretch // total if total else (room if index == 0 else 0)
            width = item.sizeHint().width() + extra
            item.setGeometry(QRect(x, rect.y(), width, rect.height()))
            x += width + self.spacing()


class Reflow(QWidget):
    """A widget holding a ``ReflowLayout``: its widgets in a row, or a column when narrow."""

    def __init__(self, parent: QWidget | None = None, *, spacing: int = 6) -> None:
        super().__init__(parent)
        self._layout = ReflowLayout(self, spacing=spacing)

    def add(self, widget: QWidget, stretch: int = 0) -> None:
        """Add ``widget``; in a row, it takes ``stretch`` of the room beyond the widths."""
        self._layout.add(widget, stretch)

    def row_width(self) -> int:
        """The width its widgets need side by side, each at its preferred width."""
        return self._layout.row_width()

    @property
    def stacked(self) -> bool:
        """Whether its widgets are one above another at its width."""
        return self._layout.stacked_at(self.width())


class WrappingForm(QFormLayout):
    """A form that puts each label above its field when the row doesn't fit beside it.

    Qt decides that a row fits side by side without counting the gap between its label and
    its field, then lays it out with the gap, so a row within the gap of fitting gets its
    field squeezed (KI-031). The gap goes in each label's right margin instead, which Qt
    counts, and the form's own horizontal spacing is none.

    Its rows are added with ``add_row``, and it never asks Qt for its layout items. PySide
    keeps the wrapper of each item Python gets from ``itemAt`` for as long as the form
    lives, and doesn't learn when ``removeRow`` deletes the item; a widget Qt makes later
    at the same address then comes back to Python as that item (KI-033). So it makes each
    row's label itself, and keeps each row's label and field.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
        self.gap = max(self.horizontalSpacing(), 0)
        """The style's space between a label and its field, kept in the label."""
        self.setHorizontalSpacing(0)
        self._repaired_at: QRect | None = None
        """The geometry this form was last laid out again at, so it's done once there."""
        self._parts: list[QWidget | QLayout] = []
        """Each row's label and field; a removed row's are deleted, and dropped when seen."""

    @override
    def setGeometry(self, rect: QRect) -> None:
        """Lay the rows out, and again from scratch if one's short of its wrapped height.

        At exactly the form's preferred width, Qt finds a height cached for that width and
        lays the rows out with heights it worked out for another width, so a wrapped label
        gets too few lines (KI-032). ``invalidate`` clears the cache and the form is laid
        out again at once. That's done once per geometry: ``invalidate`` asks the page to
        lay itself out again too, and that pass, at the same geometry, comes back here.
        """
        if rect != self._repaired_at:
            self._repaired_at = None
        super().setGeometry(rect)
        if self._repaired_at is not None or not self._short_rows():
            return
        self._repaired_at = rect
        self.invalidate()
        super().setGeometry(rect)

    def _short_rows(self) -> bool:
        """Whether a shown label or field that wraps is given less height than it needs.

        A widget is measured through an item of its own, which measures it as the form's
        item for it does; a layout is its own item.
        """
        self._parts = [part for part in self._parts if isValid(part)]
        for part in self._parts:
            item = QWidgetItem(part) if isinstance(part, QWidget) else part
            if item.isEmpty() or not item.hasHeightForWidth():
                continue
            box = item.geometry()
            if box.height() < item.heightForWidth(box.width()):
                return True
        return False

    def add_row(self, text: str, field: QWidget | QLayout) -> None:
        """Add a row of ``field`` after a label of ``text``."""
        label = QLabel(text)
        label.setContentsMargins(0, 0, self.gap, 0)
        if isinstance(field, QWidget):
            label.setBuddy(field)  # as the label Qt makes for a widget's row
        self.addRow(label, field)
        self._parts += [label, field]
