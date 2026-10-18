"""The main window's size and place, in text units (ADR-0021).

Widths are in ``ch``, the body font's average character width, and heights in its line
spacings, so the layout grows with the text and keeps its proportions. Display scaling
needs nothing: Qt lays out in logical pixels, and the font's points map to them.

Standard library only: the front end measures the font and the screen, and passes the
numbers in.
"""

from __future__ import annotations

import math
import sys
from typing import NamedTuple

from caddcalc.gui.style_tokens import Rect, Size
from caddcalc.gui.ui_style import LayoutTokens

CH_FALLBACK_EM = 0.45
"""``ch`` in ems, for a font that reports no average character width (ADR-0021 §1)."""
TEXT_SCALE_KEY = r"Software\Microsoft\Accessibility"
TEXT_SCALE_VALUE = "TextScaleFactor"
"""Where Windows keeps its "Text size" setting for the user, as a percentage: the value
behind ``UISettings.TextScaleFactor``, which Microsoft documents as 1 to 2.25."""
TEXT_SCALE_RANGE = (100, 225)


class Margins(NamedTuple):
    """A window frame's thickness on each side."""

    left: float
    top: float
    right: float
    bottom: float


def ch(average_char_width: float, em: float) -> float:
    """Return the text unit ``ch``: the font's average character width, or 0.45 em."""
    return average_char_width if average_char_width > 0 else CH_FALLBACK_EM * em


def chars(count: float, unit: float) -> int:
    """Return ``count`` characters of width ``unit``, in whole pixels, rounded up."""
    return math.ceil(count * unit)


def launch_size(
    tokens: LayoutTokens, unit: float, line: float, handle: float, pages: float = 0
) -> Size:
    """Return the window's preferred content size: the list, its handle, and a full page.

    Its height is ``launch_lines`` line spacings, or what the tallest calculator page
    needs, if that's more: the result fields' heights are in pixels, so with shorter
    lines than the design's the lines alone fall short (ADR-0021 §3, amendments).

    Args:
        tokens: The layout tokens.
        unit: ``ch``, in pixels.
        line: The body font's line spacing, in pixels.
        handle: The splitter handle's width, in pixels.
        pages: The window height the tallest calculator page needs at the launch width,
            its bars included, in pixels.
    """
    width = math.ceil(tokens.list_width_chars * unit + handle + tokens.page_max_chars * unit)
    return Size(width, max(math.ceil(tokens.launch_lines * line), math.ceil(pages)))


def fit_window(
    preferred: Size, least: Size, frame: Margins, available: Rect, margin: float
) -> Rect:
    """Return the window's content geometry: as preferred, fitted to the screen, centred.

    The content shrinks to fit the screen's work area less the frame and ``margin`` on
    each side, but never below ``least``. The frame is centred in the work area, so the
    window never opens under a taskbar (ADR-0021 §3).

    Args:
        preferred: The content size wanted.
        least: The window's least content size.
        frame: The window frame's thickness.
        available: The screen's work area.
        margin: The least room between the frame and the work area's edges.
    """
    room = Size(
        available.width - frame.left - frame.right - 2 * margin,
        available.height - frame.top - frame.bottom - 2 * margin,
    )
    width = max(least.width, min(preferred.width, room.width))
    height = max(least.height, min(preferred.height, room.height))
    outer = Size(width + frame.left + frame.right, height + frame.top + frame.bottom)
    x = available.x + math.floor((available.width - outer.width) / 2)
    y = available.y + math.floor((available.height - outer.height) / 2)
    return Rect(x + frame.left, y + frame.top, width, height)


def system_text_scale() -> float:
    """Return Windows' text size for the user, as a factor: 1.25 for 125%.

    It's 1 on other platforms, and when the setting is absent or out of its range
    (ADR-0021 §2). It's read once, at startup.
    """
    if sys.platform != "win32":
        return 1.0
    import winreg  # Windows only

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, TEXT_SCALE_KEY) as key:
            value, kind = winreg.QueryValueEx(key, TEXT_SCALE_VALUE)
    except OSError:
        return 1.0
    low, high = TEXT_SCALE_RANGE
    if kind != winreg.REG_DWORD or not low <= value <= high:
        return 1.0
    return float(value) / 100
