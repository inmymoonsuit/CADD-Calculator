"""The app icon, drawn from the brand's SVG sources at each size (docs/dev/design/brand.md).

The master tile blurs its gap and hole shut below about 32 px, so the smallest sizes use
drawings made for their own pixel grid: 16, 24 and 32 px. 20 px, Windows' small icon at
125%, uses the 24 px drawing, which keeps its gap open; from 40 px up, the master. Every
platform's icon is made here: the window and taskbar icon, the About box, and through
``packaging/icons.py`` the Windows ``.ico``, the macOS ``.icns`` and the Linux icons.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QIcon, QImage, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

from caddcalc.gui.branding import BRAND, GENERIC_ICON

SMALL = {
    16: BRAND / "app-icon-16.svg",
    24: BRAND / "app-icon-24.svg",
    32: BRAND / "app-icon-32.svg",
}
"""The drawings made for their own pixel grid, by size."""
SIZES = (16, 20, 24, 32, 40, 48, 64, 96, 128, 256)
"""The sizes the icon is drawn at: Windows' icon sizes at 100–200%, and the larger views'."""
LARGEST = SIZES[-1]


def source(size: int) -> Path:
    """Return the SVG the icon is drawn from at ``size`` pixels.

    That's the drawing made for that size, or the next one up within the small sizes,
    else the master.
    """
    for drawn in sorted(SMALL):
        if size <= drawn and size < 40:
            return SMALL[drawn]
    return GENERIC_ICON


def image(size: int) -> QImage:
    """Return the icon drawn at ``size`` by ``size`` pixels, with an alpha channel.

    Raises:
        RuntimeError: The source can't be read, which the brand tests rule out.
    """
    renderer = QSvgRenderer(str(source(size)))
    if not renderer.isValid():
        raise RuntimeError(f"Cannot draw the app icon from {source(size).name}")
    drawn = QImage(size, size, QImage.Format.Format_ARGB32_Premultiplied)
    drawn.fill(Qt.GlobalColor.transparent)
    painter = QPainter(drawn)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    renderer.render(painter, QRectF(0, 0, size, size))
    painter.end()
    return drawn


def app_icon() -> QIcon:
    """Return the app icon with every size in ``SIZES``, so Qt picks the drawn one."""
    icon = QIcon()
    for size in SIZES:
        icon.addPixmap(QPixmap.fromImage(image(size)))
    return icon


def window_icon(icon: Path | None) -> QIcon:
    """Return the window icon for a branding's ``icon``: the app's own, or a pack's file."""
    if icon is None or icon == GENERIC_ICON:
        return app_icon()
    return QIcon(str(icon))
