"""The welcome screen's geometry, computed from its design tokens (ADR-0015 §3, ADR-0016).

The sizes are tokens in ``assets/welcome_style.toml`` (``welcome_style``); this module
holds the rules that place things from them, so the widget, the tests,
``packaging/make_welcome_template.py``, and docs/dev/design/welcome-screen.md share one
source. Sizes are logical pixels unless they say otherwise. Standard library only.
"""

from __future__ import annotations

from caddcalc.gui.welcome_style import Rect, Size, style

__all__ = ["Rect", "Size", "contain_fit", "cover_crop", "fit_scale", "pane_rect"]


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
