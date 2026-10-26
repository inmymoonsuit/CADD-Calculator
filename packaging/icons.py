"""Icon helpers for packaging (ADR-0009): the app icon as each platform's icon file.

The generic edition's icon is the brand's tile (docs/dev/design/brand.md), drawn at each
size by ``caddcalc.gui.app_icon``: from the drawings made for 16, 24 and 32 px, and the
master above them. A branding pack's icon is one PNG, scaled to each size. The Windows
``.ico`` and the macOS ``.icns`` hold every size, each entry a PNG; Linux takes the SVG
sources themselves (``packaging/linux/make_appimage.py``, the Flatpak manifest).
"""

from __future__ import annotations

import os
import struct
import sys
from collections.abc import Mapping
from functools import cache
from pathlib import Path

from PySide6.QtCore import QBuffer, QByteArray, QIODevice, QRectF, Qt
from PySide6.QtGui import QColor, QGuiApplication, QImage, QImageWriter, QPainter
from PySide6.QtSvg import QSvgRenderer

from caddcalc.gui import app_icon
from caddcalc.gui.branding import BRAND, GENERIC_ICON

ROOT = Path(__file__).resolve().parent.parent
ICO_SIZES = app_icon.SIZES
"""Every size in the Windows ``.ico``: Windows' icon sizes from 100% to 200% scaling."""
ICNS_TYPES = {
    "icp4": 16,
    "icp5": 32,
    "ic11": 32,
    "icp6": 64,
    "ic12": 64,
    "ic07": 128,
    "ic08": 256,
    "ic13": 256,
    "ic09": 512,
    "ic14": 512,
    "ic10": 1024,
}
"""The ``.icns`` entries, each a PNG, by type and size: the 1x and 2x sizes macOS asks for
(ic11 to ic14 are the 2x ones of the size before them)."""
WIZARD_SIZES = {
    "WizardImage": (
        (202, 386),
        (269, 515),
        (336, 643),
        (403, 772),
        (430, 824),
        (498, 953),
        (534, 1022),
    ),
    "WizardSmallImage": (
        (58, 58),
        (77, 77),
        (97, 97),
        (116, 116),
        (124, 124),
        (143, 143),
        (159, 159),
    ),
}
"""Inno Setup's wizard images: the welcome and finish pages' left panel, and the inner
pages' header, each at the exact size of its image area at 100%, 125%, 150%, 175%, 200%,
225% and 250% display scale, from Inno Setup 6.6's help for WizardImageFile and
WizardSmallImageFile (the modern style's defaults; CI's windows-latest has 6.7). Inno picks
the one that fits, so none is stretched. The older 164x314 and 55x55 sizes were stretched
to 202x386 and 58x58 at 100%, measured in the wizard on 2026-10-26."""
CRIMSON, WHITE = "#A31D31", "#FFFFFF"
"""The brand's crimson, and the white its marks take on it (docs/dev/design/brand.md)."""


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


def images(icon: Path, sizes: tuple[int, ...]) -> dict[int, QImage]:
    """Return the icon at each of ``sizes``: drawn for the app's own, scaled for a pack's PNG.

    Raises:
        RuntimeError: A pack's icon can't be read.
    """
    if icon == GENERIC_ICON:
        return {size: app_icon.image(size) for size in sizes}
    source = QImage(str(icon))
    if source.isNull():
        raise RuntimeError(f"Cannot read the icon {icon}")
    return {size: scaled(source, size) for size in sizes}


def save_ico(entries: Mapping[int, QImage], path: Path) -> None:
    """Write a multi-size Windows .ico, one PNG-compressed entry per size (Vista and later).

    Qt's own ICO writer stores a single size, so the container is written here.
    """
    sizes = sorted(entries)
    data = [png_bytes(entries[n]) for n in sizes]
    header = struct.pack("<HHH", 0, 1, len(data))
    offset = 6 + 16 * len(data)
    directory = b""
    for n, png in zip(sizes, data, strict=True):
        side = 0 if n >= 256 else n  # 0 means 256 in the ICO format
        directory += struct.pack("<BBBBHHII", side, side, 0, 0, 1, 32, len(png), offset)
        offset += len(png)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(header + directory + b"".join(data))


def save_icns(entries: Mapping[int, QImage], path: Path) -> None:
    """Write a macOS .icns with a PNG for every type in ``ICNS_TYPES``.

    ``entries`` holds the icon at each size ``ICNS_TYPES`` names. Qt's icns writer stores
    one size, so the container is written here: the "icns" magic and its length, then each
    entry's type, its length with its 8-byte header, and its PNG.
    """
    body = b""
    for kind, size in ICNS_TYPES.items():
        png = png_bytes(entries[size])
        body += kind.encode("ascii") + struct.pack(">I", 8 + len(png)) + png
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"icns" + struct.pack(">I", 8 + len(body)) + body)


def wizard_image(kind: str, width: int, height: int) -> QImage:
    """Draw one of Inno Setup's wizard images, with no alpha, as a BMP needs.

    The left panel is the brand's crimson with the symbol in white, a little above the
    middle; the header's is the app icon on the page's white.
    """
    image = QImage(width, height, QImage.Format.Format_RGB32)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    if kind == "WizardImage":
        image.fill(QColor(CRIMSON))
        side = width * 0.6
        target = QRectF((width - side) / 2, height * 0.4 - side / 2, side, side)
        QSvgRenderer(str(BRAND / "symbol-monochrome-reversed.svg")).render(painter, target)
    else:
        image.fill(QColor(WHITE))
        icon = app_icon.image(round(min(width, height) * 0.9))
        painter.drawImage((width - icon.width()) // 2, (height - icon.height()) // 2, icon)
    painter.end()
    return image


def wizard_images(work: Path) -> dict[str, str]:
    """Write Inno Setup's wizard images to ``work`` as BMPs; return the script's defines.

    Each define lists the image's sizes, comma-separated, as Inno takes them.

    Raises:
        RuntimeError: Qt can't write a BMP.
    """
    defines = {}
    for kind, sizes in WIZARD_SIZES.items():
        paths = []
        for width, height in sizes:
            path = work / f"{kind}-{width}x{height}.bmp"
            path.parent.mkdir(parents=True, exist_ok=True)
            writer = QImageWriter(str(path), QByteArray(b"bmp"))
            if not writer.write(wizard_image(kind, width, height)):
                raise RuntimeError(f"Could not write {path}: {writer.errorString()}")
            paths.append(str(path))
        defines[kind] = ",".join(paths)
    return defines
