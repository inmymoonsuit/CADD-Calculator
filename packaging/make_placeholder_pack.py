"""Write a placeholder branding pack, to exercise the branded build without real assets.

    uv run python packaging/make_placeholder_pack.py builds/placeholder-pack
    uv run python packaging/build.py --branding builds/placeholder-pack --smoke-test

The art is drawn here in code and is obviously a test pattern, so nobody mistakes a
placeholder build for a real branded edition. Real packs live in the git-ignored
``branding/`` folder (ADR-0008 item 4, ADR-0011); this script never writes there.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QImage, QPainter

from caddcalc.gui.welcome_style import style
from icons import ROOT, ensure_qt_app

TOML = """\
# Placeholder branding pack, written by packaging/make_placeholder_pack.py.
# For testing the branded build only. Not for distribution.
schema = 1
edition = "placeholder"
name = "CADD Calculator: Placeholder Edition"
icon = "icon.png"
about = "about.html"

[welcome]
art = "welcome-art.png"
art_focus = [0.4, 0.5]
logo = "logo-vertical.svg"
"""

LOGO_SVG = """\
<svg xmlns="http://www.w3.org/2000/svg" width="72" height="540" viewBox="0 0 72 540">
  <rect width="72" height="540" fill="#202020"/>
  <rect x="8" y="8" width="56" height="524" fill="none" stroke="#ff00ff" stroke-width="4"/>
  <text x="36" y="270" fill="#ff00ff" font-family="sans-serif" font-size="22"
        font-weight="bold" text-anchor="middle" dominant-baseline="middle"
        transform="rotate(-90 36 270)">TEST LOGO</text>
</svg>
"""

ABOUT = """\
<p><b>Placeholder branding pack.</b> This build exercises the branding hook with test
art. It is not a real branded edition and is not for distribution.</p>
"""


def _checker(image: QImage, cell: int, a: str, b: str) -> None:
    p = QPainter(image)
    for y in range(0, image.height(), cell):
        for x in range(0, image.width(), cell):
            p.fillRect(x, y, cell, cell, QColor(a if (x // cell + y // cell) % 2 else b))
    p.end()


def _label(image: QImage, text: str, point_size: int) -> None:
    p = QPainter(image)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    font = QFont()
    font.setPointSize(point_size)
    font.setBold(True)
    p.setFont(font)
    rect = QRectF(0, 0, image.width(), image.height())
    p.fillRect(rect.adjusted(0, rect.height() * 0.3, 0, -rect.height() * 0.3), QColor("black"))
    p.setPen(QColor("white"))
    p.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)
    p.end()


def write_pack(dest: Path) -> Path:
    """Write the pack into ``dest`` (created if needed) and return ``dest``."""
    dest = dest.resolve()
    if dest.is_relative_to(ROOT / "branding"):
        raise SystemExit(f"Refusing to write a placeholder pack inside {ROOT / 'branding'}")
    ensure_qt_app()
    dest.mkdir(parents=True, exist_ok=True)

    icon = QImage(256, 256, QImage.Format.Format_ARGB32)
    _checker(icon, 32, "#ff00ff", "#202020")
    _label(icon, "TEST", 40)
    icon.save(str(dest / "icon.png"))

    supplied = style().art.supplied
    art = QImage(int(supplied.width), int(supplied.height), QImage.Format.Format_ARGB32)
    _checker(art, 120, "#ff00ff", "#202020")
    _label(art, "PLACEHOLDER WELCOME ART\nnot for distribution", 64)
    art.save(str(dest / "welcome-art.png"))
    (dest / "logo-vertical.svg").write_text(LOGO_SVG, encoding="utf-8")

    (dest / "about.html").write_text(ABOUT, encoding="utf-8")
    (dest / "branding.toml").write_text(TOML, encoding="utf-8")
    return dest


def main(argv: list[str] | None = None) -> int:
    """Write the placeholder pack to the given folder and return the exit status."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("dest", type=Path, help="folder to write the pack into")
    args = parser.parse_args(argv)
    print(f"Wrote placeholder branding pack to {write_pack(args.dest)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
