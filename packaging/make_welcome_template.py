"""Write a guide image for whoever makes a welcome screen's art (ADR-0015 §3).

    uv run python packaging/make_welcome_template.py builds/welcome-template.png

The guide is the art's full size, 1920 × 1080, with the safe areas the logo box and the
panes cover shaded, and a grid in the slot's logical pixels. Draw the art on a layer above it, keep
detail out of the shaded areas, then hide the guide. The sizes are the welcome screen's
own design tokens (``caddcalc.gui.welcome_style``, ADR-0016).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QFontMetricsF, QImage, QPainter, QPen

from caddcalc.gui.welcome_style import Rect, style
from icons import ensure_qt_app

BACKGROUND = "#D9DDE0"
GRID = "#B8BFC4"
SAFE_AREA = QColor(163, 18, 47, 110)
"""Crimson at about 43% opacity: plainly marked, still see-through."""
INK = "#21251F"


def _scaled(rect: Rect) -> QRectF:
    scale = style().art.supplied_scale
    return QRectF(rect.x * scale, rect.y * scale, rect.width * scale, rect.height * scale)


def _label(p: QPainter, area: QRectF, text: str) -> None:
    """Write ``text`` in ``area``, wrapped, in the largest size up to the painter's that fits."""
    flags = Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap
    font = QFont(p.font())
    while font.pointSize() > 8:
        bounds = QFontMetricsF(font).boundingRect(area, int(flags.value), text)
        if area.contains(bounds):
            break
        font.setPointSize(font.pointSize() - 1)
    p.save()
    p.setFont(font)
    p.drawText(area, flags, text)
    p.restore()


def safe_areas() -> tuple[tuple[Rect, str], ...]:
    """Return each area the art keeps clear of detail, with its label."""
    tokens = style()
    return (
        (tokens.logo_region, "organization logo"),
        (tokens.safe_area(tokens.title_pane), "title logo"),
        (tokens.safe_area(tokens.version_pane), "version pane"),
    )


def draw_template() -> QImage:
    """Return the guide image, at the size the art is supplied at."""
    ensure_qt_app()
    tokens = style()
    slot, supplied = tokens.art.slot, tokens.art.supplied
    image = QImage(int(supplied.width), int(supplied.height), QImage.Format.Format_ARGB32)
    image.fill(QColor(BACKGROUND))
    p = QPainter(image)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(QPen(QColor(GRID), 1))
    step = tokens.art.grid * tokens.art.supplied_scale
    for x in range(0, int(supplied.width) + 1, step):
        p.drawLine(x, 0, x, int(supplied.height))
    for y in range(0, int(supplied.height) + 1, step):
        p.drawLine(0, y, int(supplied.width), y)
    font = QFont()
    font.setPointSize(26)
    p.setFont(font)
    for rect, text in safe_areas():
        area = _scaled(rect)
        p.fillRect(area, SAFE_AREA)
        p.setPen(QColor("white"))
        _label(p, area, f"{text}: keep clear of detail")
    centre = QRectF(supplied.width / 2 - 24, supplied.height / 2 - 24, 48, 48)
    p.setPen(QPen(QColor(INK), 3))
    p.drawEllipse(centre)
    left = tokens.logo_region.width * tokens.art.supplied_scale
    p.drawText(
        QRectF(left, supplied.height - 120, supplied.width / 2 - left, 100),
        Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap,
        f"{int(supplied.width)} × {int(supplied.height)} px, 16:9, shown at "
        f"{int(slot.width)} × {int(slot.height)}. The circle marks the default "
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
