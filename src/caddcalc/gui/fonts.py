"""The welcome screen's display face, vendored and loaded into Qt (ADR-0016 §2).

The face ships unmodified under the SIL Open Font License 1.1, in ``assets/fonts/``
beside its ``OFL.txt`` and the manifest that pins and hashes it
(``packaging/fetch_fonts.py``). The tokens name its file and family
(``typography.display_file``, ``typography.display_family``). If it can't be loaded, text
falls back to the token's fallback families, with a warning; the screen never fails to
start for want of a font.
"""

from __future__ import annotations

import warnings
from functools import cache
from pathlib import Path

from PySide6.QtGui import QFontDatabase

from caddcalc.gui.welcome_style import STYLE_FILE, style

ASSETS = STYLE_FILE.parent
FALLBACK = "fallback"
"""What :func:`display_family` returns when the display face couldn't be loaded."""


@cache
def display_family() -> str:
    """Load the display face into Qt's font database, once, and return its family.

    Returns:
        The tokens' display family, e.g. ``"VT323"``, or :data:`FALLBACK`, with a
        warning, if the face couldn't be loaded.
    """
    typography = style().typography
    return add_font(ASSETS / typography.display_file, typography.display_family)


def add_font(path: Path, family: str) -> str:
    """Add the font file at ``path`` to the application's fonts and return ``family``.

    Returns:
        ``family``; or :data:`FALLBACK`, with a warning, if the file is missing, isn't a
        font Qt can read, or doesn't hold ``family``. A font without ``family`` isn't
        kept.
    """
    font_id = QFontDatabase.addApplicationFont(str(path))
    if font_id == -1:  # Qt's sign that the file is missing or not a font
        return _fallback(f"{path.name} can't be read as a font", family)
    found = QFontDatabase.applicationFontFamilies(font_id)
    if family not in found:
        QFontDatabase.removeApplicationFont(font_id)
        return _fallback(f"{path.name} holds {', '.join(found) or 'no family'}", family)
    return family


def _fallback(reason: str, family: str) -> str:
    # warnings, not print: a windowed app may have no stderr at all.
    warnings.warn(
        f"The display face {family} isn't available ({reason}); using a fallback",
        stacklevel=3,
    )
    return FALLBACK
