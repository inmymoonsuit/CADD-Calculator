"""The welcome screen's generated content: the public build's art and its generic logo.

Both are drawn from the palette, as original line work that needs no notice, and stand
in until the roadmap's commissioned generic art exists. They are content, not layout,
so their proportions live here; the screen's layout comes from its tokens (ADR-0016).
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QPointF, QRectF, QSize, Qt
from PySide6.QtGui import QColor, QFont, QImage, QLinearGradient, QPainter, QPen

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


def generic_logo(
    size: QSize, device_pixel_ratio: float, icon: Path, name: str, color: str
) -> QImage:
    """Return the generic logo: the app icon above the name set upright, on transparency.

    Args:
        size: The logo's size, in logical pixels; it's drawn to fill it.
        device_pixel_ratio: The screen's ratio, so the logo is sharp on it.
        icon: The app icon's file.
        name: The product's name.
        color: The name's colour, ``#RRGGBB``.
    """
    image = _canvas(size, device_pixel_ratio)
    image.fill(Qt.GlobalColor.transparent)
    p = QPainter(image)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    w, h = size.width(), size.height()
    side = min(w, h) * 0.9
    p.drawImage(QRectF((w - side) / 2, 0, side, side), QImage(str(icon)))
    p.setPen(QColor(color))
    font = QFont()
    font.setPixelSize(max(8, round(w * 0.36)))
    font.setBold(True)
    p.setFont(font)
    p.translate(w / 2, side + (h - side) / 2)
    p.rotate(-90)
    room = h - side
    p.drawText(QRectF(-room / 2, -w / 2, room, w), Qt.AlignmentFlag.AlignCenter, name)
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
