"""The welcome screen's geometry, computed from its design tokens (ADR-0015 §3, ADR-0016).

The sizes are tokens in ``assets/welcome_style.toml`` (``welcome_style``); this module
holds the rules that place things from them, so the widget, the tests,
``packaging/make_welcome_template.py``, and docs/dev/design/welcome-screen.md share one
source. Sizes are logical pixels unless they say otherwise. Standard library only.
"""

from __future__ import annotations

import math

from caddcalc.gui.welcome_style import Rect, Size, style

__all__ = [
    "Rect",
    "Size",
    "contain_fit",
    "cover_crop",
    "device_line",
    "display_pixels",
    "fit_scale",
    "logo_box",
    "pane_rect",
    "scaled",
]


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


def contain_fit(source: Size, area: Rect) -> Rect:
    """Return ``source`` scaled to fit inside ``area``, centred, keeping its shape."""
    if source.width <= 0 or source.height <= 0:
        return area
    scale = min(area.width / source.width, area.height / source.height)
    width, height = source.width * scale, source.height * scale
    return Rect(
        area.x + (area.width - width) / 2, area.y + (area.height - height) / 2, width, height
    )


def logo_box(
    source: Size, area: Rect, padding: float, min_short_side: float, max_long_side: float
) -> Rect:
    """Return the logo's box: the logo's shape plus its padding, as large as ``area`` allows.

    The box is centred in ``area``, so a tall banner, a square mark, and a wide wordmark
    all fit (ADR-0016 §3). Its long side is at most ``max_long_side``, so no logo becomes
    a full-height pillar. A box whose short side is under ``min_short_side`` then grows,
    keeping its shape, until it reaches it or meets those limits, so a wide logo never
    becomes a sliver. The logo stays contained, whole, in the box's padding.

    Args:
        source: The logo's size; only its shape matters.
        area: Where the box may sit.
        padding: The space inside the box, around the logo.
        min_short_side: The box's least short side.
        max_long_side: The box's greatest long side.
    """
    inner = Rect(
        area.x + padding, area.y + padding, area.width - 2 * padding, area.height - 2 * padding
    )
    fitted = contain_fit(source, inner)
    width, height = fitted.width + 2 * padding, fitted.height + 2 * padding
    shrink = min(1.0, max_long_side / max(width, height))
    width, height = width * shrink, height * shrink
    grow = max(1.0, min_short_side / min(width, height))
    width = min(width * grow, area.width, max_long_side)
    height = min(height * grow, area.height, max_long_side)
    return Rect(
        area.x + (area.width - width) / 2, area.y + (area.height - height) / 2, width, height
    )


_TIE = 1e-9
"""How near a half counts as one, so floating-point noise can't round a tie up."""


def display_pixels(size: float, scale: float, ratio: float, em_pixels: int) -> int:
    """Return how many device pixels draw one of a pixel face's design pixels.

    A pixel face, such as VT323, is drawn crisply only at whole multiples of its design
    grid, so its size snaps to the nearest one: ``n`` device pixels per design pixel, at
    least 1, for an em of ``em_pixels * n`` device pixels (ADR-0016, amendments). A tie
    rounds down, to keep the title inside its safe area: 62.5 device pixels at 125% is 2,
    and 87.5 at 175% is 3.

    Args:
        size: The wanted size, in logical pixels.
        scale: The card's scale on a small screen.
        ratio: The display's device pixels per logical pixel.
        em_pixels: The face's design pixels per em.
    """
    return max(1, math.floor(size * scale * ratio / em_pixels + 0.5 - _TIE))


def device_line(width: float, ratio: float) -> int:
    """Return a line's width in whole device pixels: at least 1, or 0 for no line.

    Args:
        width: The line's width, in logical pixels.
        ratio: The display's device pixels per logical pixel.
    """
    return max(1, round(width * ratio)) if width else 0


def scaled(rect: Rect, scale: float) -> Rect:
    """Return ``rect`` with its position and size multiplied by ``scale``."""
    return Rect(rect.x * scale, rect.y * scale, rect.width * scale, rect.height * scale)


def device_rect(rect: Rect, ratio: float) -> Rect:
    """Return the device pixels ``rect`` covers at device pixel ratio ``ratio``.

    It takes every device pixel the logical rectangle touches, so the art under a pane
    is measured at the display's resolution, partial pixels at its edges included.
    """
    left, top = math.floor(rect.x * ratio), math.floor(rect.y * ratio)
    right = math.ceil((rect.x + rect.width) * ratio)
    bottom = math.ceil((rect.y + rect.height) * ratio)
    return Rect(left, top, right - left, bottom - top)


def pane_rect(anchor: str, inset: float, size: Size, slot: Size) -> Rect:
    """Return where a pane of ``size`` sits, ``inset`` from the ``anchor`` corner of ``slot``."""
    x = inset if anchor.endswith("left") else slot.width - inset - size.width
    y = inset if anchor.startswith("top") else slot.height - inset - size.height
    return Rect(x, y, size.width, size.height)


def fit_scale(available: Size, window: Size | None = None) -> float:
    """Return how much to scale the whole screen so it fits ``available``, at most 1.

    The preferred size is the card's (``WelcomeStyle.window``); on a smaller screen the
    whole card shrinks, keeping the art slot at 16:9 (ADR-0015, amendments).
    """
    card = window or style().window
    return min(1.0, available.width / card.width, available.height / card.height)
