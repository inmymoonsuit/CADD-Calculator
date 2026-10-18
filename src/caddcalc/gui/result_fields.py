"""Result fields: one boxed, copyable field per output, for every calculator (ADR-0017).

The Results panel holds one ``ResultField`` per output of the shown calculator, above the
document of notes, inputs, and work. It's always as tall as its fields: results are
never clipped or scrolled on their own, only with the page (ADR-0017 R3, as amended).
It's built when the calculator changes and its values update on every recompute, so
keyboard focus and hover survive typing. A field shows its output through
``core.formatting.output_parts``, the one place outputs are presented, so it can't
disagree with the document or the CLI.

Every size, role, and state comes from the design tokens (``ui_style``); a test keeps
literals out of here.
"""

from __future__ import annotations

from typing import override

from PySide6.QtCore import QEvent, QObject, QRectF, QSize, Qt
from PySide6.QtGui import (
    QColor,
    QEnterEvent,
    QFont,
    QFontMetricsF,
    QPainter,
    QPaintEvent,
    QResizeEvent,
)
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from caddcalc.core import Calculator, Output, Result
from caddcalc.core.formatting import DisplayPrefs, ValueParts, output_parts
from caddcalc.gui.icons import current_scheme, icon, role_color
from caddcalc.gui.outlines import Outline, strongest
from caddcalc.gui.painting import on_device_pixels, stroke
from caddcalc.gui.ui_style import ResultFieldTokens, ui_style

NO_VALUE = "—"
"""What a field shows while its calculator's inputs have no result."""
NO_VALUE_TIP = "No value to copy"


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


class ResultField(QWidget):
    """One output, boxed: its symbol, label, value, unit, and a copy button (ADR-0017 §2).

    The frame is drawn inside a margin as wide as the focus ring and its gap, so the ring
    can sit outside the frame without being clipped.
    """

    def __init__(self, output: Output, tokens: ResultFieldTokens, parent: QWidget) -> None:
        super().__init__(parent)
        self.output = output
        self.tokens = tokens
        self.parts: ValueParts | None = None
        """What the field shows; ``None`` while there's no value."""
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
        self.copy_button = QToolButton(self)
        self.copy_button.setAutoRaise(True)
        button = round(tokens.button_size)
        self.copy_button.setFixedSize(button, button)
        size = round(tokens.icon_size)
        self.copy_button.setIconSize(QSize(size, size))
        self.copy_button.installEventFilter(self)
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

    def show_parts(self, parts: ValueParts | None, outline: Outline | None) -> None:
        """Show ``parts``, or no value, outlined by ``outline`` when a note concerns it."""
        self.parts, self.outline = parts, outline
        if parts is None:
            self.value.setText(NO_VALUE)
            self.unit.setText("")
            self.fraction.hide()
            self.copy_button.setEnabled(False)
            self.copy_button.setToolTip(NO_VALUE_TIP)
        else:
            self.value.setText(parts.number)
            self.unit.setText(parts.unit)
            self.fraction.setText("" if parts.fraction is None else f'(≈ {parts.fraction}")')
            self.fraction.setVisible(parts.fraction is not None)
            self.copy_button.setEnabled(True)
            self.copy_button.setToolTip(f"Copy {self.output.label.lower()}")
        self.update()

    def restyle(self) -> None:
        """Take the current light or dark scheme's colours and icon."""
        scheme = current_scheme()
        color = role_color(self.tokens.text_role, scheme)
        for label in (self.symbol, self.label, self.value, self.unit, self.fraction):
            label.setStyleSheet(f"color: {color};")
        self.copy_button.setIcon(icon(self.tokens.copy_icon, "icon", scheme))
        self.update()

    @property
    def frame(self) -> QRectF:
        """The field's frame, inside the room kept for the focus ring."""
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
        frame = self.frame
        p = QPainter(self)
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
            out = tokens.focus_gap + tokens.focus_width
            ring = frame.adjusted(-out, -out, out, out)
            stroke(p, ring, QColor(role_color(tokens.focus_role, scheme)), tokens.focus_width)
        p.end()


class ResultsPanel(QWidget):
    """The shown calculator's results: a title, then one field per output (ADR-0017 §1).

    ``build`` makes the fields when the calculator changes; ``show_result`` updates
    their values, or blanks them all while the inputs have no result, so an old answer
    can't be read, or copied, after its inputs changed.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.tokens = ui_style().result_field
        self.calculator: Calculator | None = None
        self.fields: dict[str, ResultField] = {}
        top, sides = self.tokens.panel_inset
        column = QVBoxLayout(self)
        column.setContentsMargins(round(sides), round(top), round(sides), 0)
        column.setSpacing(round(self.tokens.stack_gap))
        self.title = QLabel("Results", self)
        title_font = QFont(self.title.font())
        title_font.setBold(True)
        self.title.setFont(title_font)
        column.addWidget(self.title)
        self._column = column
        # Exactly the title's and the fields' height: never squeezed, never stretched.
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)

    def build(self, calc: Calculator) -> None:
        """Make one field per output of ``calc``; nothing changes for the same calculator."""
        if self.calculator is not None and self.calculator.id == calc.id:
            return
        for field in self.fields.values():
            field.hide()  # a deferred delete would show it until the event loop runs
            self._column.removeWidget(field)
            field.deleteLater()
        self.calculator = calc
        self.fields = {o.key: ResultField(o, self.tokens, self) for o in calc.outputs}
        for field in self.fields.values():
            self._column.addWidget(field)
        self._align()
        self.updateGeometry()

    def show_result(self, result: Result | None, prefs: DisplayPrefs) -> None:
        """Show ``result``'s outputs, outlined by its notes; ``None`` blanks every field."""
        calc = self.calculator
        if calc is None:
            return
        if result is None:
            for field in self.fields.values():
                field.show_parts(None, None)
        else:
            outlines = strongest(result.notes, self.fields)
            for output in calc.outputs:
                parts = output_parts(output, result.outputs[output.key], prefs)
                self.fields[output.key].show_parts(parts, outlines.get(output.key))
        self._align()

    def restyle(self) -> None:
        """Take the current light or dark scheme's colours and icons."""
        for field in self.fields.values():
            field.restyle()

    def _align(self) -> None:
        """Line the fields' columns up, and their values on the decimal point (ADR-0017 §2)."""
        fields = list(self.fields.values())
        if not fields:
            return
        symbol = max(f.symbol.sizeHint().width() for f in fields)
        unit = max(QFontMetricsF(f.unit.font()).horizontalAdvance(f.unit.text()) for f in fields)
        metrics = QFontMetricsF(fields[0].value.font())
        digit, point = metrics.horizontalAdvance("0"), metrics.horizontalAdvance(".")
        places = [_decimals(f.value.text()) for f in fields]
        most = max(places) if self.tokens.decimal_align else 0
        widths = []
        for field, decimals in zip(fields, places, strict=True):
            pad = 0.0
            if self.tokens.decimal_align and most:
                pad = (most - decimals) * digit + (point if decimals == 0 else 0)
            field.value.setContentsMargins(0, 0, round(pad), 0)
            widths.append(metrics.horizontalAdvance(field.value.text()) + round(pad))
        value = max(widths)
        for field in fields:
            field.symbol.setFixedWidth(symbol)
            field.unit.setFixedWidth(round(unit))
            field.value.setFixedWidth(round(value))


def _decimals(number: str) -> int:
    """Return how many decimal places ``number`` is shown with."""
    _whole, point, places = number.partition(".")
    return len(places) if point else 0
