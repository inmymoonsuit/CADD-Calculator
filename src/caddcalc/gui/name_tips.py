"""Tooltips for list rows whose names don't fit, such as the calculator list's (ADR-0020 §6).

A row's tooltip is its summary. A name too long for its row is elided ("Bend allowance &
ded…"), and a translation makes that likelier, so such a row's tooltip starts with the
whole name.
"""

from __future__ import annotations

from html import escape
from typing import override

from PySide6.QtCore import QEvent, QModelIndex, QPersistentModelIndex, Qt
from PySide6.QtGui import QHelpEvent
from PySide6.QtWidgets import (
    QAbstractItemView,
    QStyle,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QToolTip,
)


def tip_text(name: str, summary: str) -> str:
    """Return the tooltip of a row whose ``name`` is elided: the name in bold, then its summary.

    It's rich text, so both are escaped: a name such as "Bend allowance & deduction" shows
    its "&".
    """
    bold = f"<b>{escape(name)}</b>"
    return f"{bold}<br>{escape(summary)}" if summary else bold


class NameTips(QStyledItemDelegate):
    """Draws rows as usual; a row too narrow for its name shows the whole name in its tip."""

    def elided(
        self,
        view: QAbstractItemView,
        option: QStyleOptionViewItem,
        index: QModelIndex | QPersistentModelIndex,
    ) -> bool:
        """Return whether the row at ``index``, drawn with ``option``, elides its name."""
        item = QStyleOptionViewItem(option)
        self.initStyleOption(item, index)
        style = view.style()
        room = style.subElementRect(QStyle.SubElement.SE_ItemViewItemText, item, view)
        # The item's text is drawn this far inside its rectangle on each side, as
        # QCommonStyle lays it out.
        margin = style.pixelMetric(QStyle.PixelMetric.PM_FocusFrameHMargin, None, view) + 1
        return item.fontMetrics.horizontalAdvance(item.text) > room.width() - 2 * margin

    def tip(
        self,
        view: QAbstractItemView,
        option: QStyleOptionViewItem,
        index: QModelIndex | QPersistentModelIndex,
    ) -> str:
        """Return the row's tooltip: its summary, after its whole name when that's elided."""
        summary = str(index.data(Qt.ItemDataRole.ToolTipRole) or "")
        if not self.elided(view, option, index):
            return summary
        return tip_text(str(index.data(Qt.ItemDataRole.DisplayRole) or ""), summary)

    @override
    def helpEvent(
        self,
        event: QHelpEvent,
        view: QAbstractItemView,
        option: QStyleOptionViewItem,
        index: QModelIndex | QPersistentModelIndex,
    ) -> bool:
        if event.type() != QEvent.Type.ToolTip or not index.isValid():
            return super().helpEvent(event, view, option, index)
        text = self.tip(view, option, index)
        if text:
            QToolTip.showText(event.globalPos(), text, view)
        else:
            QToolTip.hideText()
        return True
