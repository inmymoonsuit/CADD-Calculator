"""A font's text units: ``ch`` for widths and its line spacing for heights (ADR-0021 §1)."""

from __future__ import annotations

from PySide6.QtGui import QFont, QFontInfo, QFontMetrics, QFontMetricsF

from caddcalc.gui.window_layout import ch


def text_unit(font: QFont) -> float:
    """Return ``font``'s ``ch``: its average character width, or 0.45 em without one."""
    return ch(QFontMetricsF(font).averageCharWidth(), QFontInfo(font).pixelSize())


def line_spacing(font: QFont) -> float:
    """Return ``font``'s line spacing, the text unit for heights, in whole pixels.

    Text lines are laid out in whole pixels: 16 at 9 pt Segoe UI, so 45 lines are 720.
    """
    return QFontMetrics(font).lineSpacing()


def scaled_font(font: QFont, scale: float) -> QFont:
    """Return ``font`` at ``scale`` times its size, such as the user's text size."""
    scaled = QFont(font)
    if scale != 1 and font.pointSizeF() > 0:
        scaled.setPointSizeF(font.pointSizeF() * scale)
    elif scale != 1 and font.pixelSize() > 0:
        scaled.setPixelSize(round(font.pixelSize() * scale))
    return scaled
