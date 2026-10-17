"""The welcome screen's geometry and art specification (ADR-0015 §3).

One source for the widget, the tests, ``packaging/make_welcome_template.py``, and
docs/dev/design/welcome-screen.md, so the specification can't drift from the code. Sizes
are logical pixels unless they say otherwise. Standard library only: the branding loader
uses the byte budget without importing Qt.
"""

from __future__ import annotations

from typing import NamedTuple


class Size(NamedTuple):
    """A width and a height."""

    width: float
    height: float


class Rect(NamedTuple):
    """A rectangle: its upper-left corner, then its size."""

    x: float
    y: float
    width: float
    height: float


ART_SIZE = Size(960, 540)
"""The art slot: exactly 16:9."""
ART_SCALE = 2
"""The art is supplied at twice the slot's size, so it stays sharp on high-DPI screens."""
ART_SUPPLIED = Size(ART_SIZE.width * ART_SCALE, ART_SIZE.height * ART_SCALE)
"""The size to supply art at: 1920 × 1080 device pixels."""
LOGO_STRIP = 72
"""The width of the vertical logo strip, left of the art slot."""
TOP_BAR = 32
"""The height of the bar across the top: menus, and the X."""
WINDOW = Size(LOGO_STRIP + ART_SIZE.width, TOP_BAR + ART_SIZE.height)
"""The whole screen at its preferred size, 1032 × 572. It scales down to fit a small screen."""

MARGIN = 24
"""The space between the art slot's edge and the text that sits over the art."""
NAME_PANEL = Rect(ART_SIZE.width - MARGIN - 376, MARGIN, 376, 88)
"""Where the name panel covers the art, in art-slot coordinates: keep it free of detail."""
VERSION_LINE = Rect(ART_SIZE.width - MARGIN - 376, ART_SIZE.height - 20 - 28, 376, 28)
"""Where the version line covers the art, in art-slot coordinates."""

ART_FORMATS = (".png", ".jpg", ".jpeg")
"""The art's file formats."""
LOGO_FORMATS = (".svg", ".png")
"""The logo's file formats: SVG scales to any screen, so it's preferred."""
MAX_ART_BYTES = 8_000_000
"""The largest art or logo file a pack may name, in bytes (8 MB). The loader checks it."""
MAX_ART_PX = 4096
"""The largest art width or height, in pixels. The screen checks it before decoding."""


def cover_crop(image: Size, slot: Size, focus: tuple[float, float] = (0.5, 0.5)) -> Rect:
    """Return the part of ``image`` to show in ``slot``, covering it without distortion.

    The image is scaled to cover the slot, and the overflow is cropped around ``focus``:
    the point, as fractions of the image's width and height, kept as near the slot's
    centre as the image's edges allow.

    Args:
        image: The image's size, in its own pixels.
        slot: The slot's size, in any unit; only its aspect ratio matters.
        focus: The point to keep in view, each from 0 to 1.

    Returns:
        The source rectangle, in the image's pixels.
    """
    scale = max(slot.width / image.width, slot.height / image.height)
    width, height = slot.width / scale, slot.height / scale
    x = min(max(focus[0] * image.width - width / 2, 0.0), image.width - width)
    y = min(max(focus[1] * image.height - height / 2, 0.0), image.height - height)
    return Rect(x, y, width, height)


def fit_scale(available: Size) -> float:
    """Return how much to scale the whole screen so it fits ``available``, at most 1.

    The preferred size is ``WINDOW``; on a smaller screen the whole card shrinks, keeping
    the art slot at 16:9 (ADR-0015, amendments).
    """
    return min(1.0, available.width / WINDOW.width, available.height / WINDOW.height)
