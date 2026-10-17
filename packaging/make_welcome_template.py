"""Write a guide image for whoever makes a welcome screen's art (ADR-0015 §3).

    uv run python packaging/make_welcome_template.py builds/welcome-template.png

The guide is the art's full size, 1920 × 1080, with the areas the name panel and the
version line cover shaded, and a grid in the slot's logical pixels. Draw the art on a
layer above it, keep detail out of the shaded areas, then hide the guide. The sizes come
from ``caddcalc.gui.welcome_layout``, the same module the welcome screen uses.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QImage, QPainter, QPen

from caddcalc.gui.welcome_layout import (
    ART_SCALE,
    ART_SIZE,
    ART_SUPPLIED,
    NAME_PANEL,
    VERSION_LINE,
    Rect,
)
from icons import ensure_qt_app

BACKGROUND = "#D9DDE0"
GRID = "#B8BFC4"
SAFE_AREA = QColor(163, 18, 47, 110)
"""Crimson at about 43% opacity: plainly marked, still see-through."""
INK = "#21251F"


def _scaled(rect: Rect) -> QRectF:
    return QRectF(
        rect.x * ART_SCALE, rect.y * ART_SCALE, rect.width * ART_SCALE, rect.height * ART_SCALE
    )


def draw_template() -> QImage:
    """Return the guide image, at the size the art is supplied at."""
    ensure_qt_app()
    image = QImage(int(ART_SUPPLIED.width), int(ART_SUPPLIED.height), QImage.Format.Format_ARGB32)
    image.fill(QColor(BACKGROUND))
    p = QPainter(image)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(QPen(QColor(GRID), 1))
    step = 60 * ART_SCALE  # a line every 60 logical pixels
    for x in range(0, int(ART_SUPPLIED.width) + 1, step):
        p.drawLine(x, 0, x, int(ART_SUPPLIED.height))
    for y in range(0, int(ART_SUPPLIED.height) + 1, step):
        p.drawLine(0, y, int(ART_SUPPLIED.width), y)
    font = QFont()
    font.setPointSize(26)
    p.setFont(font)
    for rect, text in ((NAME_PANEL, "name panel"), (VERSION_LINE, "version line")):
        area = _scaled(rect)
        p.fillRect(area, SAFE_AREA)
        p.setPen(QColor("white"))
        p.drawText(area, Qt.AlignmentFlag.AlignCenter, f"{text}: keep clear of detail")
    centre = QRectF(ART_SUPPLIED.width / 2 - 24, ART_SUPPLIED.height / 2 - 24, 48, 48)
    p.setPen(QPen(QColor(INK), 3))
    p.drawEllipse(centre)
    p.drawText(
        QRectF(0, ART_SUPPLIED.height - 120, ART_SUPPLIED.width / 2, 100),
        Qt.AlignmentFlag.AlignCenter,
        f"{int(ART_SUPPLIED.width)} × {int(ART_SUPPLIED.height)} px, 16:9, shown at "
        f"{int(ART_SIZE.width)} × {int(ART_SIZE.height)}. The circle marks the default "
        "focal point.",
    )
    p.end()
    return image


def main(argv: list[str] | None = None) -> int:
    """Write the guide image to the given path and return the exit status."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("dest", type=Path, help="the PNG file to write")
    args = parser.parse_args(argv)
    args.dest.parent.mkdir(parents=True, exist_ok=True)
    if not draw_template().save(str(args.dest)):
        print(f"Couldn't write {args.dest}", file=sys.stderr)
        return 1
    print(f"Wrote the welcome-art guide to {args.dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
