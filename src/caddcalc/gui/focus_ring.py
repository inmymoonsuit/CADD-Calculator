"""The keyboard focus ring for an input a note outlines (ADR-0017, amendments; WCAG 2.4.7).

A note's outline on an input is a style sheet border, and a style sheet replaces the
native frame, focus indicator and all. So a focused, outlined input showed no focus, on
exactly the fields a note sends the user to. A ``:focus`` style rule can't fix that
without hiding the outline while the field has focus.

Instead, focus is added outside the outline, as on a result field: a ``focus_ring`` ring
``focus_width`` wide, ``focus_gap`` outside the field, in whole device pixels. One
``FocusRing`` per window follows the keyboard focus, and shows only around an input
marked ``OUTLINED``; other inputs keep their native focus indicator.

The window owns the ring. While it rings an input, the ring is a child of the input's
parent, so it scrolls and clips with the input; when that parent goes, the ring goes back
to the window, so it's deleted with the window and never outlives it (KI-019).
"""

from __future__ import annotations

from typing import override

from PySide6.QtCore import QEvent, QObject, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPaintEvent
from PySide6.QtWidgets import QApplication, QWidget
from shiboken6 import isValid

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

    Args:
        owner: The window it belongs to, which deletes it.
        tokens: The result fields' tokens, whose focus ring it draws.
    """

    def __init__(self, owner: QWidget, tokens: ResultFieldTokens | None = None) -> None:
        super().__init__(owner)
        self.owner = owner
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
        """Ring ``widget`` if it's an outlined input of this window, or hide."""
        self._let_go()
        if widget is None or not isValid(widget) or not widget.property(OUTLINED):
            self.hide()
            return
        parent = widget.parentWidget()
        if parent is None or widget.window() is not self.owner:
            self.hide()
            return
        self.target = widget
        widget.installEventFilter(self)
        widget.destroyed.connect(self._on_target_destroyed)
        if self.parentWidget() is not parent:
            self.setParent(parent)
            # Back to the window before the parent goes, which would take the ring with it.
            parent.destroyed.connect(self._on_parent_destroyed)
        self._place()
        self.show()
        self.raise_()

    def _let_go(self) -> None:
        """Stop following the input it rings, if that input still exists."""
        target, self.target = self.target, None
        if target is not None and isValid(target):
            target.removeEventFilter(self)
            target.destroyed.disconnect(self._on_target_destroyed)

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

    def _on_target_destroyed(self) -> None:
        # A rebuilt form deletes its inputs, but keeps their parent and so the ring.
        self.target = None
        self.hide()

    def _on_parent_destroyed(self) -> None:
        self.target = None
        self.hide()
        if isValid(self.owner):
            self.setParent(self.owner)

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
