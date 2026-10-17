"""Tabler icons, recolored from the UI palette (docs/dev/design/icons.md).

The vendored SVGs (assets/icons/tabler/, listed in its manifest.toml) draw in
``currentColor``, which Qt's SVG renderer doesn't resolve. So each icon is read as text,
``currentColor`` is replaced with the palette color for its role in the current light or
dark scheme, and the result is rendered with QtSvg.
"""

from __future__ import annotations

import tomllib
from functools import cache
from pathlib import Path
from typing import Any, Literal

from PySide6.QtCore import QByteArray, QRectF, Qt
from PySide6.QtGui import QGuiApplication, QIcon, QImage, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

ASSETS = Path(__file__).parent / "assets"
TABLER_DIR = ASSETS / "icons" / "tabler" / "outline"
SIZES = (16, 20, 24, 32, 48)
Scheme = Literal["light", "dark"]


@cache
def palette() -> dict[str, Any]:
    data: dict[str, Any] = tomllib.loads((ASSETS / "palette.toml").read_text(encoding="utf-8"))
    return data


def role_color(role: str, scheme: Scheme) -> str:
    """The hex color for a palette role, e.g. ``role_color("icon_error", "light")``."""
    theme = palette()[scheme]
    color: str = palette()["colors"][theme[role]]
    return color


def current_scheme() -> Scheme:
    """Light or dark, following the system setting when Qt knows it."""
    app = QGuiApplication.instance()
    if not isinstance(app, QGuiApplication):
        return "light"
    scheme = app.styleHints().colorScheme()
    if scheme == Qt.ColorScheme.Dark:
        return "dark"
    if scheme == Qt.ColorScheme.Light:
        return "light"
    return "dark" if app.palette().window().color().lightness() < 128 else "light"


def svg_source(name: str, color: str) -> bytes:
    """The icon's SVG with ``currentColor`` replaced by ``color``."""
    text = (TABLER_DIR / f"{name}.svg").read_text(encoding="utf-8")
    return text.replace("currentColor", color).encode("utf-8")


def render(name: str, color: str, size: int) -> QImage:
    """Render one icon as a transparent square image, ``size`` pixels wide."""
    renderer = QSvgRenderer(QByteArray(svg_source(name, color)))
    if not renderer.isValid():
        raise ValueError(f"cannot render icon {name!r}")
    image = QImage(size, size, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    renderer.render(painter, QRectF(0, 0, size, size))
    painter.end()
    return image


def icon(name: str, role: str = "icon", scheme: Scheme | None = None) -> QIcon:
    """A QIcon for a vendored Tabler icon, in the color of ``role`` for ``scheme``."""
    return _icon(name, role, scheme or current_scheme())


@cache
def _icon(name: str, role: str, scheme: Scheme) -> QIcon:
    color = role_color(role, scheme)
    result = QIcon()
    for size in SIZES:
        result.addPixmap(QPixmap.fromImage(render(name, color, size)))
    return result


def clear_cache() -> None:
    """Forget rendered icons, e.g. after the system switches between light and dark."""
    _icon.cache_clear()
