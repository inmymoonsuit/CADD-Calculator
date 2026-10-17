"""Icon helpers for packaging (ADR-0009), and the generator for the generic app icon.

Run ``uv run python packaging/icons.py`` to redraw ``src/caddcalc/gui/assets/app-icon.png``.
The generic icon is original line art drawn here in code, so it is covered by the project's
Apache-2.0 license and needs no third-party notice. Its planned replacement is the roadmap
item "Generic art for the public build" (ADR-0008, item 4).

The build script uses ``save_ico`` and ``save_icns`` to turn a PNG into the
executable icon each platform needs, so a branding pack only has to supply one PNG.
"""

from __future__ import annotations

import os
import struct
import sys
from functools import cache
from pathlib import Path

from PySide6.QtCore import QBuffer, QByteArray, QIODevice, QPointF, QRectF, Qt
from PySide6.QtGui import (
    QColor,
    QGuiApplication,
    QImage,
    QImageWriter,
    QPainter,
    QPainterPath,
    QPen,
)

ROOT = Path(__file__).resolve().parent.parent
GENERIC_ICON = ROOT / "src" / "caddcalc" / "gui" / "assets" / "app-icon.png"
ICO_SIZES = (16, 24, 32, 48, 64, 128, 256)


def ensure_qt_app() -> QGuiApplication:
    """Return the running Qt application, creating one if needed. Nothing is shown.

    Image work and text drawing need a Qt application. On a Linux machine with no display,
    Qt's offscreen platform is used, but only while the application is created, so
    programs started later (the smoke test) still get the real platform. Elsewhere the
    native platform is kept: on Windows the offscreen platform has no fonts, so text would
    come out as boxes.
    """
    existing = QGuiApplication.instance()
    if isinstance(existing, QGuiApplication):
        return existing
    return _create_qt_app()


@cache
def _create_qt_app() -> QGuiApplication:
    """Create the application once; the cache also keeps it alive for the process."""
    headless = sys.platform.startswith("linux") and not (
        os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")
    )
    if not headless or "QT_QPA_PLATFORM" in os.environ:
        return QGuiApplication([sys.argv[0]])
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    try:
        return QGuiApplication([sys.argv[0]])
    finally:
        del os.environ["QT_QPA_PLATFORM"]


def draw_generic_icon(size: int = 256) -> QImage:
    """A blue tile with a white formed sheet-metal profile: a flange, a bend, a flange."""
    image = QImage(size, size, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.transparent)
    s = size / 256
    p = QPainter(image)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)

    tile = QPainterPath()
    tile.addRoundedRect(QRectF(8 * s, 8 * s, 240 * s, 240 * s), 44 * s, 44 * s)
    p.fillPath(tile, QColor("#1f5f99"))

    # The part: a vertical flange, a 90° bend with an inside radius, a horizontal flange.
    part = QPainterPath(QPointF(72 * s, 48 * s))
    part.lineTo(72 * s, 148 * s)
    part.arcTo(QRectF(72 * s, 108 * s, 80 * s, 80 * s), 180, 90)
    part.lineTo(212 * s, 188 * s)
    pen = QPen(QColor("white"), 26 * s)
    pen.setCapStyle(Qt.PenCapStyle.FlatCap)
    pen.setJoinStyle(Qt.PenJoinStyle.MiterJoin)
    p.strokePath(part, pen)

    # A dimension line across the bend, in a lighter blue, for "calculated".
    dim = QPen(QColor("#9cc8f0"), max(1.0, 8 * s))
    dim.setCapStyle(Qt.PenCapStyle.RoundCap)
    p.setPen(dim)
    p.drawLine(QPointF(118 * s, 64 * s), QPointF(204 * s, 64 * s))
    p.drawLine(QPointF(204 * s, 64 * s), QPointF(204 * s, 150 * s))
    p.end()
    return image


def png_bytes(image: QImage) -> bytes:
    """Return ``image`` encoded as PNG."""
    data = QByteArray()
    buffer = QBuffer(data)
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    # QImageWriter rather than QImage.save: PySide6 6.12's stubs and runtime disagree on
    # the type of save()'s format argument.
    writer = QImageWriter(buffer, QByteArray(b"png"))
    if not writer.write(image):
        raise RuntimeError(f"Qt could not encode a PNG: {writer.errorString()}")
    buffer.close()
    return bytes(data.data())


def scaled(image: QImage, size: int) -> QImage:
    """Return ``image`` resized to ``size`` by ``size`` pixels, smoothly filtered."""
    return image.scaled(
        size,
        size,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )


def save_ico(image: QImage, path: Path, sizes: tuple[int, ...] = ICO_SIZES) -> None:
    """Write a multi-size Windows .ico with PNG-compressed entries (Windows Vista and later).

    Qt's own ICO writer stores a single size, so the container is written here.
    """
    entries = [png_bytes(scaled(image, n)) for n in sizes]
    header = struct.pack("<HHH", 0, 1, len(entries))
    offset = 6 + 16 * len(entries)
    directory = b""
    for n, data in zip(sizes, entries, strict=True):
        side = 0 if n >= 256 else n  # 0 means 256 in the ICO format
        directory += struct.pack("<BBBBHHII", side, side, 0, 0, 1, 32, len(data), offset)
        offset += len(data)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(header + directory + b"".join(entries))


def save_icns(image: QImage, path: Path) -> None:
    """Write a macOS .icns with Qt's icns image plugin."""
    path.parent.mkdir(parents=True, exist_ok=True)
    writer = QImageWriter(str(path), QByteArray(b"icns"))
    if not writer.write(scaled(image, 512)):
        raise RuntimeError(f"Could not write {path}: {writer.errorString()}")


def main() -> int:
    """Redraw the generic app icon and return the exit status."""
    ensure_qt_app()
    GENERIC_ICON.parent.mkdir(parents=True, exist_ok=True)
    if not draw_generic_icon(256).save(str(GENERIC_ICON)):
        raise RuntimeError(f"Could not write {GENERIC_ICON}")
    print(f"Wrote {GENERIC_ICON.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
