"""Draw the repository's social preview, 1280 × 640 px, from the brand's logo.

    uv run python packaging/make_social_preview.py

It writes ``docs/dev/design/brand/social-preview.png`` for the maintainer to upload under
the repository's Settings → General → Social preview. The logo is outlined paths, so no
font is needed; the image is drawn offscreen and shows nothing.
"""

from __future__ import annotations

import sys

from PySide6.QtCore import QRectF
from PySide6.QtGui import QColor, QImage, QPainter
from PySide6.QtSvg import QSvgRenderer

from caddcalc.gui.branding import TITLE_LOGO
from icons import CRIMSON, ROOT, ensure_qt_app

OUT = ROOT / "docs" / "dev" / "design" / "brand" / "social-preview.png"
SIZE = (1280, 640)
"""GitHub's recommended social preview size."""
LOGO_WIDTH = 960
"""The logo's width, leaving GitHub's crop room on every side."""
BAND = 16
"""The crimson band along the bottom edge."""


def draw() -> QImage:
    """Return the preview: the logo on white, centred, over a crimson band."""
    width, height = SIZE
    image = QImage(width, height, QImage.Format.Format_RGB32)
    image.fill(QColor("#FFFFFF"))
    logo = QSvgRenderer(str(TITLE_LOGO))
    box = logo.viewBoxF()
    logo_height = LOGO_WIDTH * box.height() / box.width()
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    target = QRectF(
        (width - LOGO_WIDTH) / 2, (height - BAND - logo_height) / 2, LOGO_WIDTH, logo_height
    )
    logo.render(painter, target)
    painter.fillRect(0, height - BAND, width, BAND, QColor(CRIMSON))
    painter.end()
    return image


def main() -> int:
    """Write the preview and return the exit status."""
    ensure_qt_app()
    if not draw().save(str(OUT)):
        print(f"Could not write {OUT}", file=sys.stderr)
        return 1
    print(f"Wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
