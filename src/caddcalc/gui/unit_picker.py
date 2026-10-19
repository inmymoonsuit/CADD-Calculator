"""A field's unit picker, and the field that shows what its text reads as (ADR-0024 §1, D8).

The picker is the field's one unit author: the text never names a unit. Closed, it
shows the choice's symbol, which isn't translated, so the picker column keeps its width
in every language; its list shows the symbol and the name, and the name is what it's
spoken as (Q3). The field shows, after its text, what the text reads as, while there's
room, and always in its tooltip and accessible description.
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Sequence
from typing import override

from PySide6.QtCore import QModelIndex, QPersistentModelIndex, Qt, Signal
from PySide6.QtGui import QFontMetricsF, QPalette, QResizeEvent
from PySide6.QtWidgets import (
    QComboBox,
    QLabel,
    QLineEdit,
    QStyle,
    QStyledItemDelegate,
    QStyleOptionFrame,
    QStyleOptionViewItem,
    QWidget,
)

from caddcalc.core.formatting import Echo
from caddcalc.core.i18n import _, npgettext_shown
from caddcalc.core.units import CompoundForm, Dimension, Unit, registry
from caddcalc.core.units.model import NAME_CONTEXT

NAME_ROLE = int(Qt.ItemDataRole.UserRole) + 10
"""Picker item data holding the choice's name, as its list shows and it's spoken."""
CHOICE_ROLE = int(Qt.ItemDataRole.UserRole) + 11
"""Picker item data holding the choice's id: a unit's key symbol or a form's key."""


def choice_symbol(choice: str, dimension: Dimension) -> str:
    """Return what a closed picker shows for a choice: ``in``, ``°``, ``ft-in``."""
    picked = registry().choice(choice, dimension)
    return picked.written if isinstance(picked, Unit) else picked.symbol


def choice_name(choice: str, dimension: Dimension) -> str:
    """Return a choice's name, as its picker's list shows it and it's spoken: "millimeters"."""
    picked = registry().choice(choice, dimension)
    if isinstance(picked, CompoundForm):
        return _(picked.name)
    # The plural, since a picker names the unit any amount is in.
    return npgettext_shown(NAME_CONTEXT, picked.name, picked.spoken_plural, "2")


class _ChoiceItems(QStyledItemDelegate):
    """Draws a picker's open list as "symbol — name", "mm — millimeters"."""

    @override
    def initStyleOption(
        self, option: QStyleOptionViewItem, index: QModelIndex | QPersistentModelIndex
    ) -> None:
        super().initStyleOption(option, index)
        name = index.data(NAME_ROLE)
        if name:
            option.text = f"{option.text} — {name}"


class UnitPicker(QComboBox):
    """A field's unit picker: its parameter's choices, in a picker's order (ADR-0024 §1).

    Signals:
        picked: Emitted with the choice's id when the user picks one, never when the
            picker is set from code.
    """

    picked = Signal(str)

    def __init__(
        self,
        label: str,
        choices: Sequence[str],
        dimension: Dimension,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.dimension = dimension
        self.setItemDelegate(_ChoiceItems(self))
        for choice in choices:
            self.addItem(choice_symbol(choice, dimension))
            index = self.count() - 1
            name = choice_name(choice, dimension)
            self.setItemData(index, choice, CHOICE_ROLE)
            self.setItemData(index, name, NAME_ROLE)
            self.setItemData(index, name, Qt.ItemDataRole.ToolTipRole)
        self.setAccessibleName(f"{label} unit")
        self.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.currentIndexChanged.connect(self._named)
        self.activated.connect(lambda index: self.picked.emit(self.itemData(index, CHOICE_ROLE)))
        self._named()

    @property
    def choice(self) -> str:
        """The id of the choice shown."""
        return str(self.currentData(CHOICE_ROLE) or "")

    @property
    def choices(self) -> tuple[str, ...]:
        """The ids it offers, in order."""
        return tuple(str(self.itemData(i, CHOICE_ROLE) or "") for i in range(self.count()))

    def set_choice(self, choice: str) -> None:
        """Show ``choice``, as code sets it: ``picked`` isn't emitted."""
        self.setCurrentIndex(self.choices.index(choice))

    def _named(self, *_args: object) -> None:
        """Say the choice by its name, and show it as the tooltip (Q3)."""
        name = str(self.currentData(NAME_ROLE) or "")
        self.setAccessibleDescription(name)
        self.setToolTip(name)


def picker_min_chars(pickers: Iterable[UnitPicker]) -> int:
    """Return the least width every picker on a page shares: its widest symbol, measured.

    It's counted in the widths of "X" that a combo box's least contents length counts,
    so the pickers stand in one column with no ragged edge (``picker_min_chars``,
    ADR-0024 §1, §8).
    """
    widest = 0
    for picker in pickers:
        metrics = QFontMetricsF(picker.font())
        x = metrics.horizontalAdvance("X")
        longest = max(
            (metrics.horizontalAdvance(picker.itemText(i)) for i in range(picker.count())),
            default=0.0,
        )
        if x > 0:
            widest = max(widest, math.ceil(longest / x))
    return widest


class EchoField(QLineEdit):
    """A field that shows, after its text, what the text reads as (ADR-0024 D8).

    The echo is a label inside the field's right edge, in the secondary text colour. It
    shows only while the text and it both fit; it's always in the tooltip, after the
    field's help, and it's the field's accessible description.
    """

    GAP_CHARS = 1
    """The space between the text and the echo, in widths of "X"."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.help = ""
        self.echo: Echo | None = None
        self.echo_label = QLabel(self)
        self.echo_label.setForegroundRole(QPalette.ColorRole.PlaceholderText)
        self.echo_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.echo_label.hide()
        self.textChanged.connect(self._place)

    def set_help(self, text: str) -> None:
        """Give the field its help, the first part of its tooltip."""
        self.help = text
        self._describe()

    def set_echo(self, echo: Echo | None) -> None:
        """Show what the text reads as, or nothing for a plain decimal."""
        self.echo = echo
        self.echo_label.setText("" if echo is None else echo.text)
        self._describe()
        self._place()

    @property
    def echo_shown(self) -> bool:
        """Whether the echo shows inside the field, rather than only in its tooltip."""
        return self.echo is not None and not self.echo_label.isHidden()

    def _describe(self) -> None:
        tip = [self.help] if self.help else []
        if self.echo is not None:
            tip.append(self.echo.text)
        self.setToolTip("\n".join(tip))
        self.setAccessibleDescription("" if self.echo is None else self.echo.spoken)

    def _place(self, *_args: object) -> None:
        """Show the echo at the right edge if it and the text both fit, else hide it."""
        if self.echo is None:
            self.echo_label.hide()
            self.setTextMargins(0, 0, 0, 0)
            return
        metrics = QFontMetricsF(self.font())
        echo = math.ceil(metrics.horizontalAdvance(self.echo.text))
        gap = math.ceil(metrics.horizontalAdvance("X") * self.GAP_CHARS)
        option = QStyleOptionFrame()
        self.initStyleOption(option)
        inner = self.style().subElementRect(QStyle.SubElement.SE_LineEditContents, option, self)
        text = math.ceil(metrics.horizontalAdvance(self.text()))
        if text + gap + echo > inner.width():
            self.echo_label.hide()
            self.setTextMargins(0, 0, 0, 0)
            return
        self.setTextMargins(0, 0, echo + gap, 0)
        self.echo_label.setGeometry(inner.right() - echo + 1, inner.top(), echo, inner.height())
        self.echo_label.show()

    @override
    def resizeEvent(self, event: QResizeEvent) -> None:
        """Keep the echo at the right edge, or hide it, as the field's width changes."""
        super().resizeEvent(event)
        self._place()
