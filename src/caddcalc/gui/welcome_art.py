"""The welcome screen's generated content: the public build's art.

It's drawn from the palette, as original line work that needs no notice, and stands in
until the roadmap's commissioned generic art exists. It's content, not layout, so its
proportions live here; the screen's layout comes from its tokens (ADR-0016). Without a
pack logo, the logo box holds the app icon.
"""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, QSize, Qt
from PySide6.QtGui import QColor, QImage, QLinearGradient, QPainter, QPen

from caddcalc.gui.icons import palette


def generic_art(size: QSize, device_pixel_ratio: float) -> QImage:
    """Return the public build's art, drawn at the screen's resolution.

    A flat pattern's bend lines over a slate field.
    """
    image = _canvas(size, device_pixel_ratio)
    p = QPainter(image)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    w, h = size.width(), size.height()
    gradient = QLinearGradient(QPointF(0, 0), QPointF(w, h))
    gradient.setColorAt(0, QColor(_color("ink")))
    gradient.setColorAt(1, QColor(_color("slate")))
    p.fillRect(QRectF(0, 0, w, h), gradient)
    unit = h / 9
    p.setPen(QPen(QColor(_color("amber")), max(1.0, unit / 30), Qt.PenStyle.DashLine))
    for i in range(1, 9):
        x = w * 0.08 + i * unit * 1.1
        p.drawLine(QPointF(x, h * 0.18), QPointF(x - unit * 1.6, h * 0.92))
    p.setPen(QPen(QColor(_color("crimson")), max(1.5, unit / 18)))
    p.drawArc(QRectF(w * 0.08, h * 0.30, unit * 7, unit * 7), 30 * 16, 120 * 16)
    p.end()
    return image


def _canvas(size: QSize, device_pixel_ratio: float) -> QImage:
    width = max(1, round(size.width() * device_pixel_ratio))
    height = max(1, round(size.height() * device_pixel_ratio))
    image = QImage(width, height, QImage.Format.Format_ARGB32_Premultiplied)
    image.setDevicePixelRatio(device_pixel_ratio)
    return image


def _color(name: str) -> str:
    """A palette colour by its name, such as ``"slate"``, for art that ignores the theme."""
    color: str = palette()["colors"][name]
    return color
