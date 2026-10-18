"""Crisp lines at any display scaling, for the app's own painted components.

A line is a whole number of device pixels, at least one, centred on device-pixel centres,
so it stays sharp at 125% and 150% scaling (ADR-0016, amendments). The welcome card and
the result fields draw their borders and outlines through here.
"""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPen

from caddcalc.gui.welcome_layout import device_line


def on_device_pixels(p: QPainter, rect: QRectF, inset: float = 0) -> QRectF:
    """Return ``rect`` with its edges on whole device pixels, then ``inset`` device pixels in.

    The result is in the painter's own coordinates, so whatever is drawn on it lands on
    the display's pixel grid at any scaling.
    """
    to_device = p.deviceTransform()
    device = to_device.mapRect(rect)
    edges = QRectF(
        QPointF(round(device.left()), round(device.top())),
        QPointF(round(device.right()), round(device.bottom())),
    )
    to_logical, _invertible = to_device.inverted()
    return to_logical.mapRect(edges.adjusted(inset, inset, -inset, -inset))


def stroke(p: QPainter, rect: QRectF, color: QColor, width: float, *, dashed: bool = False) -> None:
    """Draw a line ``width`` logical pixels wide just inside ``rect``, crisply.

    The line is a whole number of device pixels, at least one, centred on device-pixel
    centres, so it stays sharp at 125% and 150% scaling. A dashed line reads as
    "unchecked" (ADR-0017 §3).
    """
    ratio = p.deviceTransform().m11()
    device = device_line(width, ratio)
    if not device:
        return
    pen = QPen(color, device / ratio)
    if dashed:
        pen.setStyle(Qt.PenStyle.DashLine)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawRect(on_device_pixels(p, rect, device / 2))
