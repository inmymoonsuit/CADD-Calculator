"""Result fields: one boxed, copyable field per output, for every calculator (ADR-0017).

The Results panel holds one ``ResultField`` per output of the shown calculator, above the
document of notes, inputs, and work. It's always as tall as its fields: results are
never clipped or scrolled on their own, only with the page (ADR-0017 R3, as amended).
It's built when the calculator changes and its values update on every recompute, so
keyboard focus and hover survive typing. A field shows and copies its output through
``core.formatting.output_parts`` and ``copy_output``, the one place outputs are
presented, so it can't disagree with the document or the CLI.

Copying (ADR-0017 §4, §5): a field's button, Space, Enter, or Ctrl+C on it copies the
value as shown; its context menu offers the other forms; Copy all copies every output as
spreadsheet rows. Each copy shows a check in place for a moment, and is announced in the
status bar and to screen readers.

Every size, role, and state comes from the design tokens (``ui_style``); a test keeps
literals out of here. User-facing wording is whole sentences with named fields, so it can
be translated as written.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from typing import override

from PySide6.QtCore import QEvent, QObject, QRectF, QSize, Qt, QTimer, Signal
from PySide6.QtGui import (
    QAccessible,
    QAccessibleAnnouncementEvent,
    QColor,
    QContextMenuEvent,
    QEnterEvent,
    QFont,
    QFontMetricsF,
    QGuiApplication,
    QKeyEvent,
    QKeySequence,
    QPainter,
    QPaintEvent,
    QResizeEvent,
)
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMenu,
    QSizePolicy,
    QStyle,
    QStyleOptionToolButton,
    QStylePainter,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from caddcalc.core import Calculator, Output, Result
from caddcalc.core.formatting import (
    DISCLAIMER,
    CopyForm,
    DisplayPrefs,
    ValueParts,
    copy_output,
    decimal_separator,
    output_parts,
    results_tsv,
    spoken_value,
)
from caddcalc.gui.icons import current_scheme, icon, role_color
from caddcalc.gui.outlines import Outline, strongest
from caddcalc.gui.painting import frame_within, on_device_pixels, stroke
from caddcalc.gui.text_units import text_unit
from caddcalc.gui.ui_style import ResultFieldTokens, secondary_text, ui_style
from caddcalc.gui.window_layout import chars

NO_VALUE = "—"
"""What a field shows while its calculator's inputs have no result."""
NO_VALUE_TIP = "No value to copy"
NO_VALUE_SPOKEN = "no value"
"""What a screen reader says in place of a value while there's none."""
TITLE = "Results"
FIELD_NAME = "{label}, {symbol}: {value}"
"""A field's accessible name, e.g. "Bend allowance, BA: 0.3119 inches"."""
VALUE_SPOKEN = "{symbol}: {value}"
"""A copy button's accessible description, e.g. "BA: 0.3119 inches"."""
COPY = "Copy {label}"
"""The copy button's tooltip and accessible name, e.g. "Copy Bend allowance"."""
COPIED = "Copied {symbol} = {text} to the clipboard"
COPY_ALL = "Copy all"
COPY_ALL_NAME = "Copy all results"
COPY_ALL_TIP = "Copy all results as rows for a spreadsheet ({keys})"
COPIED_ALL = "Copied all results to the clipboard"
COPY_ALL_KEYS = QKeySequence("Ctrl+Shift+C")
"""Copy all, from anywhere in the window; Cmd+Shift+C on macOS."""
MENU = {
    CopyForm.VALUE: "Copy value",
    CopyForm.SHOWN: "Copy {number}",
    CopyForm.WITH_UNIT: "Copy with unit",
    CopyForm.FULL: "Copy full precision",
    CopyForm.FRACTION: "Copy fraction",
}
"""The context menu's copy forms (R6), in order. The fraction is there only when it's
shown, and the number as shown, e.g. "Copy 0,3119", only where the decimal mark isn't "."
(ADR-0020 §4): "Copy value" writes "." for CAD. Where it isn't, every item is named by
what it copies, such as "Copy 0.3119" and "Copy 0.3119 in"."""


def _announce(widget: QWidget, message: str) -> None:
    """Tell screen readers ``message``, politely, as the status bar shows it (R4)."""
    event = QAccessibleAnnouncementEvent(widget, message)
    event.setPoliteness(QAccessible.AnnouncementPoliteness.Polite)
    QAccessible.updateAccessibility(event)


class _ElidedLabel(QLabel):
    """A label that elides its text to its width, and offers the whole text as a tooltip."""

    def __init__(self, text: str, parent: QWidget) -> None:
        super().__init__(parent)
        self.full_text = text
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self._elide()

    def _elide(self) -> None:
        shown = self.fontMetrics().elidedText(
            self.full_text, Qt.TextElideMode.ElideRight, self.width()
        )
        self.setText(shown)
        self.setToolTip("" if shown == self.full_text else self.full_text)

    @override
    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self._elide()


class _CopyButton(QToolButton):
    """A copy button that Space, Enter, and the platform's Copy keys all press (§5).

    A tool button takes Space already; Enter and Copy (Ctrl+C, or Cmd+C on macOS) copy
    the focused field's value too, and nothing else, since the shortcut is the button's
    own key handling rather than a window-wide one.

    Args:
        parent: Its field, or the panel.
        ringed: Whether its field's focus ring shows its focus, so it draws none of its
            own; Copy all, which has no ring, keeps the style's.
    """

    def __init__(self, parent: QWidget, *, ringed: bool) -> None:
        super().__init__(parent)
        self.ringed = ringed

    @override
    def paintEvent(self, event: QPaintEvent) -> None:
        if not self.ringed:
            super().paintEvent(event)
            return
        # As QToolButton paints itself, less the focus state: one focus indicator, the
        # field's ring, rather than the style's inside it too.
        option = QStyleOptionToolButton()
        self.initStyleOption(option)
        option.state &= ~QStyle.StateFlag.State_HasFocus
        painter = QStylePainter(self)
        painter.drawComplexControl(QStyle.ComplexControl.CC_ToolButton, option)

    @override
    def keyPressEvent(self, event: QKeyEvent) -> None:
        enter = event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter)
        if (enter or event.matches(QKeySequence.StandardKey.Copy)) and self.isEnabled():
            self.click()
            event.accept()
            return
        super().keyPressEvent(event)


class _CopiedState:
    """Shows a button's check icon for ``copied_ms`` after a copy, then its copy icon."""

    def __init__(self, button: QToolButton, tokens: ResultFieldTokens) -> None:
        self.button = button
        self.tokens = tokens
        self.timer = QTimer(button)
        self.timer.setSingleShot(True)
        self.timer.setInterval(round(tokens.copied_ms))
        self.timer.timeout.connect(self.restyle)

    @property
    def showing(self) -> bool:
        """Whether the check shows now."""
        return self.timer.isActive()

    def start(self) -> None:
        """Show the check, for ``copied_ms`` from now; nothing else moves."""
        self.timer.start()
        self.restyle()

    def restyle(self) -> None:
        """Show the icon for the current state, in the current scheme."""
        name = self.tokens.copied_icon if self.showing else self.tokens.copy_icon
        self.button.setIcon(icon(name, "icon", current_scheme()))


class ResultField(QWidget):
    """One output, boxed: its symbol, label, value, unit, and a copy button (ADR-0017 §2).

    The frame is drawn inside a margin as wide as the focus ring and its gap, so the ring
    can sit outside the frame without being clipped.

    Attributes:
        copied: Emitted with the status message after the field copies.
    """

    copied = Signal(str)

    def __init__(self, output: Output, tokens: ResultFieldTokens, parent: QWidget) -> None:
        super().__init__(parent)
        self.output = output
        self.tokens = tokens
        self.parts: ValueParts | None = None
        """What the field shows; ``None`` while there's no value."""
        self.amount: float | None = None
        """The value it shows, in base units, which it copies from; ``None`` for none."""
        self.prefs = DisplayPrefs()
        """The display preferences it shows and copies its value in."""
        self.outline: Outline | None = None
        """The strongest outline of the notes that concern this output, if any."""
        self.hovered = False
        ring = tokens.focus_width + tokens.focus_gap
        vertical, horizontal = tokens.padding
        row = QHBoxLayout(self)
        row.setContentsMargins(
            round(ring + horizontal),
            round(ring + vertical),
            round(ring + horizontal),
            round(ring + vertical),
        )
        row.setSpacing(round(tokens.gap))
        self.symbol = QLabel(output.symbol, self)
        bold = QFont(self.symbol.font())
        bold.setBold(True)
        self.symbol.setFont(bold)
        self.label = _ElidedLabel(output.label, self)
        self.value = QLabel(NO_VALUE, self)
        self.value.setFont(self._value_font())
        self.value.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.value.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.unit = QLabel(self)
        self.fraction = QLabel(self)
        self.fraction.hide()
        self.copy_button = _CopyButton(self, ringed=True)
        self.copy_button.setAutoRaise(True)
        button = round(tokens.button_size)
        self.copy_button.setFixedSize(button, button)
        size = round(tokens.icon_size)
        self.copy_button.setIconSize(QSize(size, size))
        self.copy_button.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.copy_button.installEventFilter(self)
        self.copy_button.clicked.connect(self._on_clicked)
        self.copy_button.setAccessibleName(COPY.format(label=output.label))
        self.copied_state = _CopiedState(self.copy_button, tokens)
        for widget in (self.symbol, self.label, self.value, self.unit, self.fraction):
            row.addWidget(widget)
        row.setStretch(row.indexOf(self.label), 1)
        row.addWidget(self.copy_button)
        self.setMinimumHeight(round(tokens.min_height + 2 * ring))
        self.restyle()
        self.show_parts(None, None)

    def _value_font(self) -> QFont:
        font = QFont(self.font())
        bold = self.tokens.value_weight == "bold"
        font.setWeight(QFont.Weight.Bold if bold else QFont.Weight.Normal)
        if self.tokens.tabular_figures:
            font.setFeature(QFont.Tag("tnum"), 1)  # every digit one width, so columns align
        return font

    def set_value(self, amount: float | None, prefs: DisplayPrefs, outline: Outline | None) -> None:
        """Show ``amount``, in base units, in ``prefs``; ``None`` shows no value."""
        self.amount, self.prefs = amount, prefs
        parts = None if amount is None else output_parts(self.output, amount, prefs)
        self.show_parts(parts, outline)

    def show_parts(self, parts: ValueParts | None, outline: Outline | None) -> None:
        """Show ``parts``, or no value, outlined by ``outline`` when a note concerns it."""
        self.parts, self.outline = parts, outline
        if parts is None:
            self.amount = None
            self.value.setText(NO_VALUE)
            self.unit.setText("")
            self.fraction.hide()
            self.copy_button.setEnabled(False)
            self.copy_button.setToolTip(NO_VALUE_TIP)
        else:
            close_up = parts.unit_close_up  # "132.70°", as the document writes it
            self.value.setText(parts.with_unit if close_up else parts.number)
            self.unit.setText("" if close_up else parts.unit)
            self.fraction.setText("" if parts.fraction is None else f'(≈ {parts.fraction}")')
            self.fraction.setVisible(parts.fraction is not None)
            self.copy_button.setEnabled(True)
            self.copy_button.setToolTip(COPY.format(label=self.output.label))
        spoken = NO_VALUE_SPOKEN if parts is None else spoken_value(parts)
        symbol = self.output.symbol
        self.setAccessibleName(
            FIELD_NAME.format(label=self.output.label, symbol=symbol, value=spoken)
        )
        # Said after the button's name, "Copy Bend allowance", so not the label again.
        self.copy_button.setAccessibleDescription(VALUE_SPOKEN.format(symbol=symbol, value=spoken))
        self.update()

    def copy(self, form: CopyForm = CopyForm.VALUE) -> str | None:
        """Copy the value, in ``form``, and show and announce it; ``None`` with no value.

        It copies the value the field shows now, so an answer whose inputs changed is
        never copied (§4, "never stale").
        """
        if self.amount is None or self.parts is None:
            return None
        if form is CopyForm.FRACTION and self.parts.fraction is None:
            return None
        text = copy_output(self.output, self.amount, self.prefs, form)
        QGuiApplication.clipboard().setText(text)
        self.copied_state.start()
        self.copied.emit(COPIED.format(symbol=self.output.symbol, text=text))
        return text

    def _on_clicked(self) -> None:
        self.copy()

    def context_menu(self) -> QMenu:
        """Return the menu of copy forms (R6), as ``MENU`` lists them."""
        menu = QMenu(self)
        point = decimal_separator(self.prefs) == "."
        for form, text in MENU.items():
            if form is CopyForm.FRACTION and (self.parts is None or self.parts.fraction is None):
                continue
            if form is CopyForm.SHOWN and (point or self.parts is None):
                continue
            if point or self.amount is None:
                number = "" if self.parts is None else self.parts.number
                label = text.format(number=number)
            else:
                # Two decimal marks are on offer, so each item says what it copies,
                # "Copy 0.3119" beside "Copy 0,3119" (UI/UX's i4 review).
                copied = copy_output(self.output, self.amount, self.prefs, form)
                label = MENU[CopyForm.SHOWN].format(number=copied)
            action = menu.addAction(label)
            action.setEnabled(self.parts is not None)
            action.triggered.connect(_copier(self, form))
        return menu

    @override
    def contextMenuEvent(self, event: QContextMenuEvent) -> None:
        # Right-click, or the Menu key on the focused copy button, which passes it here.
        # A popup, not a nested event loop; the menu goes when it closes.
        menu = self.context_menu()
        menu.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        menu.popup(event.globalPos())
        event.accept()

    def restyle(self) -> None:
        """Take the current light or dark scheme's colours and icon."""
        scheme = current_scheme()
        color = role_color(self.tokens.text_role, scheme)
        for label in (self.symbol, self.label, self.value, self.unit, self.fraction):
            label.setStyleSheet(f"color: {color};")
        self.copied_state.restyle()
        self.update()

    @property
    def frame(self) -> QRectF:
        """The field's frame, inside the room kept for the focus ring, at 100% scaling.

        Painting places it in whole device pixels (``frame_within``).
        """
        ring = self.tokens.focus_width + self.tokens.focus_gap
        return QRectF(self.rect()).adjusted(ring, ring, -ring, -ring)

    @override
    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if watched is self.copy_button and event.type() in (
            QEvent.Type.FocusIn,
            QEvent.Type.FocusOut,
        ):
            self.update()  # the focus ring follows the button's focus
        return super().eventFilter(watched, event)

    @override
    def enterEvent(self, event: QEnterEvent) -> None:
        self.hovered = True
        self.update()
        super().enterEvent(event)

    @override
    def leaveEvent(self, event: QEvent) -> None:
        self.hovered = False
        self.update()
        super().leaveEvent(event)

    @override
    def paintEvent(self, event: QPaintEvent) -> None:
        tokens, scheme = self.tokens, current_scheme()
        p = QPainter(self)
        # The ring at the field's edge and the frame inside its room, in whole device
        # pixels, so the gap is even and the ring unclipped at any scaling.
        bounds = QRectF(self.rect())
        frame = frame_within(p, bounds, tokens.focus_gap, tokens.focus_width)
        surface = on_device_pixels(p, frame)
        p.fillRect(surface, QColor(role_color(tokens.fill_role, scheme)))
        if self.hovered:
            tint = QColor(role_color(tokens.hover_fill_role, scheme))
            tint.setAlphaF(tokens.hover_fill_opacity)
            p.fillRect(surface, tint)
        if self.outline is not None:
            color = QColor(role_color(self.outline.role, scheme))
            stroke(p, frame, color, self.outline.width, dashed=self.outline.style == "dashed")
        else:
            role = tokens.hover_border_role if self.hovered else tokens.border_role
            stroke(p, frame, QColor(role_color(role, scheme)), tokens.border_width)
        if self.copy_button.hasFocus():
            ring = on_device_pixels(p, bounds)
            stroke(p, ring, QColor(role_color(tokens.focus_role, scheme)), tokens.focus_width)
        p.end()


def _copier(field: ResultField, form: CopyForm) -> Callable[[], None]:
    """Return a slot that copies ``field``'s value in ``form``."""

    def copy() -> None:
        field.copy(form)

    return copy


class ResultsPanel(QWidget):
    """The shown calculator's results: its title and Copy all, its fields, and the disclaimer.

    The disclaimer is the panel's last line: safety text, so it's never cut off. It wraps
    at any width, in any language, and sits with the answers it qualifies (ADR-0021 §7).

    ``build`` makes the fields when the calculator changes; ``show_result`` updates
    their values, or blanks them all while the inputs have no result, so an old answer
    can't be read, or copied, after its inputs changed (ADR-0017 §1, §4).

    Attributes:
        announced: Emitted with each copy's status message, once screen readers have
            been told it.
    """

    announced = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.tokens = ui_style().result_field
        self.calculator: Calculator | None = None
        self.result: Result | None = None
        """The result the fields show, which Copy all copies; ``None`` for none."""
        self.prefs = DisplayPrefs()
        self.fields: dict[str, ResultField] = {}
        top, sides = self.tokens.panel_inset
        column = QVBoxLayout(self)
        column.setContentsMargins(round(sides), round(top), round(sides), 0)
        column.setSpacing(round(self.tokens.stack_gap))
        self.title = QLabel(TITLE, self)
        title_font = QFont(self.title.font())
        title_font.setBold(True)
        title_font.setPointSizeF(title_font.pointSizeF() * self.tokens.title_scale)
        self.title.setFont(title_font)
        self.copy_all_button = _CopyButton(self, ringed=False)
        self.copy_all_button.setText(COPY_ALL)
        self.copy_all_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.copy_all_button.setAutoRaise(True)
        size = round(self.tokens.icon_size)
        self.copy_all_button.setIconSize(QSize(size, size))
        self.copy_all_button.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.copy_all_button.setAccessibleName(COPY_ALL_NAME)
        keys = COPY_ALL_KEYS.toString(QKeySequence.SequenceFormat.NativeText)
        self.copy_all_button.setToolTip(COPY_ALL_TIP.format(keys=keys))
        self.copy_all_button.clicked.connect(self.copy_all)
        self.copy_all_state = _CopiedState(self.copy_all_button, self.tokens)
        # The title and Copy all sit in line with the fields' frames, inside the focus
        # ring's room.
        ring = round(self.tokens.focus_width + self.tokens.focus_gap)
        header = QHBoxLayout()
        header.setContentsMargins(ring, 0, ring, 0)
        header.addWidget(self.title, 1)
        header.addWidget(self.copy_all_button)
        column.addLayout(header)
        self._column = QVBoxLayout()
        self._column.setSpacing(round(self.tokens.stack_gap))
        column.addLayout(self._column)
        self.disclaimer = QLabel(DISCLAIMER, self)
        self.disclaimer.setWordWrap(True)
        notice = QHBoxLayout()
        notice.setContentsMargins(ring, 0, ring, 0)
        notice.addWidget(self.disclaimer)
        column.addLayout(notice)
        # Exactly the title's, the fields' and the disclaimer's height, never squeezed or
        # stretched; as wide as the page, up to its cap, centred beyond it (ADR-0021 §4).
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        cap = ui_style().layout.panel_max_chars
        self.setMaximumWidth(chars(cap, text_unit(self.font())))
        self.restyle()
        self._sync_copy_all()

    # Its height is its height at its width, as the disclaimer wraps; Qt's own hint takes
    # the disclaimer at a guessed width, which the page's fit would then wrongly trust.
    @override
    def sizeHint(self) -> QSize:
        hint = super().sizeHint()
        return QSize(hint.width(), self._height())

    @override
    def minimumSizeHint(self) -> QSize:
        hint = super().minimumSizeHint()
        return QSize(hint.width(), self._height())

    def _height(self) -> int:
        width = self.width() if self.width() > 0 else super().sizeHint().width()
        return self.heightForWidth(width)

    @override
    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        if event.size().width() != event.oldSize().width():
            self.updateGeometry()  # a new width: a new height

    def build(self, calc: Calculator) -> None:
        """Make one field per output of ``calc``; nothing changes for the same calculator."""
        if self.calculator is not None and self.calculator.id == calc.id:
            return
        for field in self.fields.values():
            field.hide()  # a deferred delete would show it until the event loop runs
            self._column.removeWidget(field)
            field.deleteLater()
        self.calculator = calc
        self.result = None
        self.fields = {o.key: ResultField(o, self.tokens, self) for o in calc.outputs}
        for field in self.fields.values():
            self._column.addWidget(field)
            field.copied.connect(self._announce)
        self._align()
        self._sync_copy_all()
        self.updateGeometry()

    def show_result(self, result: Result | None, prefs: DisplayPrefs) -> None:
        """Show ``result``'s outputs, outlined by its notes; ``None`` blanks every field."""
        calc = self.calculator
        if calc is None:
            return
        self.result, self.prefs = result, prefs
        if result is None:
            for field in self.fields.values():
                field.set_value(None, prefs, None)
        else:
            outlines = strongest(result.notes, self.fields)
            for output in calc.outputs:
                field = self.fields[output.key]
                field.set_value(result.outputs[output.key], prefs, outlines.get(output.key))
        self._align()
        self._sync_copy_all()

    def copy_all(self) -> str | None:
        """Copy every output as tab-separated rows (R2); ``None`` while there's no result."""
        if self.calculator is None or self.result is None:
            return None
        text = results_tsv(self.calculator, self.result, self.prefs)
        QGuiApplication.clipboard().setText(text)
        self.copy_all_state.start()
        self._announce(COPIED_ALL)
        return text

    def focus_chain(self) -> list[QWidget]:
        """The panel's stops for Tab, in order: each field's copy button, then Copy all."""
        return [*(f.copy_button for f in self.fields.values()), self.copy_all_button]

    def restyle(self) -> None:
        """Take the current light or dark scheme's colours and icons."""
        self.copy_all_state.restyle()
        self.disclaimer.setStyleSheet(f"color: {secondary_text(current_scheme(), self.tokens)};")
        for field in self.fields.values():
            field.restyle()

    def _announce(self, message: str) -> None:
        _announce(self, message)
        self.announced.emit(message)

    def _sync_copy_all(self) -> None:
        self.copy_all_button.setEnabled(self.result is not None)

    def _align(self) -> None:
        """Line the fields' columns up, and their values on the decimal point (ADR-0017 §2)."""
        fields = list(self.fields.values())
        if not fields:
            return
        symbol = max(f.symbol.sizeHint().width() for f in fields)
        unit = max(QFontMetricsF(f.unit.font()).horizontalAdvance(f.unit.text()) for f in fields)
        metrics = QFontMetricsF(fields[0].value.font())
        point = decimal_separator(self.prefs)
        tails = [_tail(f.parts, metrics, point) for f in fields]
        most = max(tails) if self.tokens.decimal_align else 0.0
        widths = []
        for field, tail in zip(fields, tails, strict=True):
            pad = most - tail if self.tokens.decimal_align else 0.0
            field.value.setContentsMargins(0, 0, round(pad), 0)
            widths.append(metrics.horizontalAdvance(field.value.text()) + round(pad))
        value = max(widths)
        # Up, not to the nearest: a column a fraction of a pixel narrower than its text
        # cuts off the text's last pixel.
        for field in fields:
            field.symbol.setFixedWidth(symbol)
            field.unit.setFixedWidth(math.ceil(unit))
            field.value.setFixedWidth(math.ceil(value))


def _tail(parts: ValueParts | None, metrics: QFontMetricsF, point: str) -> float:
    """Return how far a value reaches right of where its decimal point starts.

    That's the point and its decimals, and a unit written close up, such as "°". A whole
    number's point would start at its right edge, so only a close-up unit reaches past it.
    Padding every value out to the longest tail lines the points up.
    """
    if parts is None:
        return 0.0
    places = _decimals(parts.number, point)
    tail = metrics.horizontalAdvance(point + places) if places else 0.0
    return tail + (metrics.horizontalAdvance(parts.unit) if parts.unit_close_up else 0.0)


def _decimals(number: str, point: str) -> str:
    """Return what ``number`` shows after ``point``: its decimals, and any mark after them.

    A compound form, such as ``40°30′15.00″``, ends in a mark after its seconds' decimals.
    """
    _whole, found, places = number.partition(point)
    return places if found else ""
