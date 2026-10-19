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

from PySide6.QtCore import QEvent, QModelIndex, QObject, QPersistentModelIndex, QSize, Qt, Signal
from PySide6.QtGui import QFocusEvent, QFontMetricsF, QKeyEvent, QResizeEvent, QShowEvent
from PySide6.QtWidgets import (
    QComboBox,
    QLabel,
    QLineEdit,
    QStyle,
    QStyledItemDelegate,
    QStyleOptionComboBox,
    QStyleOptionFrame,
    QStyleOptionViewItem,
    QWidget,
)

from caddcalc.core.formatting import Echo
from caddcalc.core.i18n import _, npgettext_shown
from caddcalc.core.units import CompoundForm, Dimension, Unit, registry
from caddcalc.core.units.model import NAME_CONTEXT
from caddcalc.gui.icons import current_scheme
from caddcalc.gui.ui_style import secondary_text

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


class WheelGuard(QObject):
    """Ignores the mouse wheel on the widgets it watches, such as a choice's boxes.

    A wheel turned over a choice box would change the choice, and with it the values it
    derives or the units the results show in, without a click, even while another field
    has the focus (review M1). The boxes still change by click and by keyboard.
    """

    @override
    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        return event.type() == QEvent.Type.Wheel


class ChoiceItems(QStyledItemDelegate):
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

    A choice settles when it's made in the open list, when Enter is pressed, or when the
    picker loses focus; ↑, ↓ and the like on a closed picker only step through the
    choices (§3). Neither signal is emitted when the picker is set from code.

    Signals:
        stepped: Emitted with the choice's id at each step through a closed picker.
        picked: Emitted with the choice's id once a choice settles, if it differs from
            the one settled before.
    """

    stepped = Signal(str)
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
        self.setItemDelegate(ChoiceItems(self))
        for choice in choices:
            self.addItem(choice_symbol(choice, dimension))
            index = self.count() - 1
            name = choice_name(choice, dimension)
            self.setItemData(index, choice, CHOICE_ROLE)
            self.setItemData(index, name, NAME_ROLE)
            self.setItemData(index, name, Qt.ItemDataRole.ToolTipRole)
        self.setAccessibleName(f"{label} unit")
        self.text_width = 0
        """The width its closed face holds text in, shared by a page's pickers."""
        self._stepping = False
        self._listing = False
        """Whether its list is opening, which takes the focus without settling a step."""
        self._settled = ""
        self.currentIndexChanged.connect(self._named)
        self.activated.connect(self._activated)
        self._named()
        self._settled = self.choice

    @property
    def choice(self) -> str:
        """The id of the choice shown."""
        return str(self.currentData(CHOICE_ROLE) or "")

    @property
    def choices(self) -> tuple[str, ...]:
        """The ids it offers, in order."""
        return tuple(str(self.itemData(i, CHOICE_ROLE) or "") for i in range(self.count()))

    def set_choice(self, choice: str) -> None:
        """Show ``choice``, as code sets it: neither signal is emitted."""
        self.setCurrentIndex(self.choices.index(choice))
        self._settled = choice

    def set_text_width(self, width: int) -> None:
        """Hold ``width`` pixels of text, as wide as the page's widest symbol (§1, §8)."""
        self.text_width = width
        self.updateGeometry()

    @override
    def showEvent(self, event: QShowEvent) -> None:
        """Give the layout its size again, as measured now that it shows.

        A picker built on a hidden page is measured before it shows, and a style can
        measure a shown combo box wider; the layout keeps the first size unless told
        (engineering log, 2026-10-19).
        """
        super().showEvent(event)
        self.updateGeometry()

    @override
    def sizeHint(self) -> QSize:
        """The face that holds ``text_width`` of text, with the frame and arrow, no icon."""
        hint = super().sizeHint()
        if not self.text_width:
            return hint
        option = QStyleOptionComboBox()
        self.initStyleOption(option)
        contents = QSize(self.text_width, self.fontMetrics().height())
        size = self.style().sizeFromContents(
            QStyle.ContentsType.CT_ComboBox, option, contents, self
        )
        return QSize(size.width(), hint.height())

    @override
    def minimumSizeHint(self) -> QSize:
        """As ``sizeHint``: the picker column never narrows past its widest symbol."""
        return self.sizeHint() if self.text_width else super().minimumSizeHint()

    @override
    def keyPressEvent(self, event: QKeyEvent) -> None:
        """Step on ↑ and ↓ and the like while closed; settle on Enter."""
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and not self.view().isVisible():
            self._settle()
            event.accept()
            return
        self._stepping = not self.view().isVisible()
        try:
            super().keyPressEvent(event)
        finally:
            self._stepping = False

    @override
    def showPopup(self) -> None:
        """Open the list; the focus it takes isn't the picker losing it (§3).

        Only while it opens: after that the list's own visibility says so, since Escape
        or a click outside closes it without calling ``hidePopup`` (review M1).
        """
        self._listing = True
        try:
            super().showPopup()
        finally:
            self._listing = False

    @override
    def focusOutEvent(self, event: QFocusEvent) -> None:
        """Settle the choice stepped to, as the picker loses focus to another widget.

        Opening its own list takes the focus too, before anything is chosen, so that
        doesn't settle: the step would otherwise lead the follow (UI/UX's M-B).
        """
        if not self._listing and not self.view().isVisible():
            self._settle()
        super().focusOutEvent(event)

    def _activated(self, index: int) -> None:
        choice = str(self.itemData(index, CHOICE_ROLE) or "")
        if self._stepping:
            self.stepped.emit(choice)
        else:
            self._settle()

    def _settle(self) -> None:
        if self.choice != self._settled:
            self._settled = self.choice
            self.picked.emit(self.choice)

    def _named(self, *_args: object) -> None:
        """Say the choice by its name, and show it as the tooltip (Q3)."""
        name = str(self.currentData(NAME_ROLE) or "")
        self.setAccessibleDescription(name)
        self.setToolTip(name)


def picker_text_width(pickers: Iterable[UnitPicker]) -> int:
    """Return the text width every picker on a page shares: its widest symbol, measured.

    So the pickers stand in one column with no ragged edge, as narrow as their symbols
    allow (``picker_min_chars``, ADR-0024 §1, §8).
    """
    widest = 0.0
    for picker in pickers:
        metrics = QFontMetricsF(picker.font())
        for i in range(picker.count()):
            widest = max(widest, metrics.horizontalAdvance(picker.itemText(i)))
    return math.ceil(widest)


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
        self.echo_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self._color()
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

    def _color(self) -> None:
        """Give the echo secondary text's colour in the scheme shown (WCAG 1.4.3).

        It's information, not a placeholder's hint, so it takes the secondary text role.
        """
        self.echo_label.setStyleSheet(f"color: {secondary_text(current_scheme())};")

    @override
    def changeEvent(self, event: QEvent) -> None:
        """Recolour the echo when the palette or the colour scheme changes."""
        super().changeEvent(event)
        if event.type() in (QEvent.Type.PaletteChange, QEvent.Type.ApplicationPaletteChange):
            self._color()

    @override
    def minimumSizeHint(self) -> QSize:
        """As the field's with no echo, which hides when it doesn't fit.

        So showing it never widens the window's least size (UI/UX's Low at stop 2).
        """
        hint = super().minimumSizeHint()
        margins = self.textMargins()
        return QSize(max(0, hint.width() - margins.left() - margins.right()), hint.height())

    @override
    def resizeEvent(self, event: QResizeEvent) -> None:
        """Keep the echo at the right edge, or hide it, as the field's width changes."""
        super().resizeEvent(event)
        self._place()
