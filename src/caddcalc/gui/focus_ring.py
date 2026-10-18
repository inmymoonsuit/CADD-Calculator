"""The keyboard focus ring for an input a note outlines (ADR-0017, amendments; WCAG 2.4.7).

A note's outline on an input is a style sheet border, and a style sheet replaces the
native frame, focus indicator and all. So a focused, outlined input showed no focus, on
exactly the fields a note sends the user to. A ``:focus`` style rule can't fix that
without hiding the outline while the field has focus.

Instead, focus is added outside the outline, as on a result field: a ``focus_ring`` ring
``focus_width`` wide, ``focus_gap`` outside the field, in whole device pixels. One
``FocusRing`` per window follows the keyboard focus, and shows only around an input
marked ``OUTLINED``; other inputs keep their native focus indicator.
"""

from __future__ import annotations

from typing import override

from PySide6.QtCore import QEvent, QObject, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPaintEvent
from PySide6.QtWidgets import QApplication, QWidget

from caddcalc.gui.icons import current_scheme, role_color
from caddcalc.gui.painting import ring_around, stroke
from caddcalc.gui.ui_style import ResultFieldTokens, ui_style

OUTLINED = "noteOutline"
"""The property that marks an input whose style sheet draws a note's or an error's
outline, so the focus ring knows to draw around it."""

_PLACE = (QEvent.Type.Move, QEvent.Type.Resize, QEvent.Type.Show)
"""Changes to the focused input that move its ring with it."""


class FocusRing(QWidget):
    """A focus ring around whichever outlined input has the keyboard focus.

    It's a child of the input's parent, just around the input, so it scrolls and clips
    with it, and it ignores the mouse.
    """

    def __init__(self, tokens: ResultFieldTokens | None = None) -> None:
        super().__init__()
        self.tokens = ui_style().result_field if tokens is None else tokens
        self.target: QWidget | None = None
        """The outlined input it rings now, if any."""
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.hide()
        app = QApplication.instance()
        if isinstance(app, QApplication):
            app.focusChanged.connect(self._on_focus_changed)

    def refresh(self) -> None:
        """Ring the focused input if it's outlined now; call after outlines change."""
        self.follow(QApplication.focusWidget())

    def follow(self, widget: QWidget | None) -> None:
        """Ring ``widget`` if it's an outlined input, or hide."""
        if self.target is not None:
            self.target.removeEventFilter(self)
        parent = None if widget is None else widget.parentWidget()
        outlined = widget is not None and bool(widget.property(OUTLINED))
        self.target = widget if outlined and parent is not None else None
        if self.target is None or parent is None:
            self.hide()
            return
        self.target.installEventFilter(self)
        if self.parentWidget() is not parent:
            self.setParent(parent)
            # Let go before the parent goes, which would take the ring with it.
            parent.destroyed.connect(self._on_parent_destroyed)
        self._place()
        self.show()
        self.raise_()

    @property
    def _room(self) -> int:
        """How far the ring may reach outside its input, rounding included.

        That's the ring, its gap, and a pixel for rounding them to device pixels.
        """
        return round(self.tokens.focus_gap + self.tokens.focus_width) + 1

    def _place(self) -> None:
        if self.target is not None:
            room = self._room
            self.setGeometry(self.target.geometry().adjusted(-room, -room, room, room))

    def _on_focus_changed(self, _old: QWidget | None, new: QWidget | None) -> None:
        self.follow(new)

    def _on_parent_destroyed(self) -> None:
        self.target = None
        self.setParent(None)

    @override
    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if watched is self.target:
            if event.type() in _PLACE:
                self._place()
            elif event.type() == QEvent.Type.Hide:
                self.hide()
        return super().eventFilter(watched, event)

    @override
    def paintEvent(self, event: QPaintEvent) -> None:
        tokens = self.tokens
        room = self._room
        field = QRectF(self.rect()).adjusted(room, room, -room, -room)
        p = QPainter(self)
        ring = ring_around(p, field, tokens.focus_gap, tokens.focus_width)
        color = QColor(role_color(tokens.focus_role, current_scheme()))
        stroke(p, ring, color, tokens.focus_width)
        p.end()
