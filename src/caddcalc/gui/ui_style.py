"""The app's design tokens beyond the welcome screen, from ``assets/ui_style.toml``.

Every size, colour role, and state the app's own components use is a token in that file
(ADR-0017 §7), read, typed, and range-checked here on the core every token file shares
(``style_tokens``), so a component reads tokens only, never literals. The result fields
take ``result_field``; input and result fields alike take ``note_outline``.

Standard library only.
"""

from __future__ import annotations

import tomllib
from collections.abc import Mapping
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from typing import Any

from caddcalc.gui.style_tokens import (
    ASSETS,
    Check,
    StyleError,
    check_bool,
    check_choice,
    check_number,
    check_role,
    check_spacing,
    check_spacing_pair,
    check_text,
    parse_tables,
)

STYLE_FILE = ASSETS / "ui_style.toml"
SCHEMA = 1
ICON_DIR = ASSETS / "icons" / "tabler" / "outline"
LINE_STYLES = frozenset({"solid", "dashed"})
WEIGHTS = frozenset({"regular", "bold"})


@dataclass(frozen=True)
class ResultFieldTokens:
    """One boxed, copyable result, and the panel of them (ADR-0017 §2 and §3)."""

    padding: tuple[float, float]
    """Inside a field: vertical, then horizontal."""
    gap: float
    """Between a field's columns."""
    stack_gap: float
    """Between fields."""
    panel_inset: tuple[float, float]
    """Around the results panel: its top, then its sides."""
    min_height: float
    button_size: float
    icon_size: float
    border_width: float
    border_role: str
    hover_border_role: str
    hover_fill_role: str
    hover_fill_opacity: float
    """The hover fill is ``hover_fill_role`` at this opacity, painted at paint time."""
    focus_role: str
    focus_width: float
    focus_gap: float
    """Between the frame and the focus ring, so the ring never merges with an outline."""
    copied_ms: int
    """How long the copied check shows, in milliseconds."""
    value_weight: str
    tabular_figures: bool
    decimal_align: bool
    """Align the values on their decimal points, not only on their right edges."""
    document_min_height: float
    """The height the document under the panel always keeps; the panel scrolls past it."""
    copy_icon: str
    copied_icon: str


@dataclass(frozen=True)
class NoteOutlineTokens:
    """How a field a note concerns is outlined, input or result alike (ADR-0017 §3)."""

    width: float
    """Every note outline's width, heavier than a field's border."""
    limit_role: str
    limit_style: str
    note_role: str
    note_style: str
    no_value_role: str
    no_value_style: str
    error_role: str
    """An input whose text can't be read."""
    error_style: str


@dataclass(frozen=True)
class UiStyle:
    """Every token of the app's own components, checked."""

    result_field: ResultFieldTokens
    note_outline: NoteOutlineTokens


def check_icon(where: str, value: Any) -> str:
    """Check the name of a vendored Tabler icon."""
    name = check_text(where, value)
    if not (ICON_DIR / f"{name}.svg").is_file():
        raise StyleError(f"{where}: {name!r} isn't a vendored icon")
    return name


_WIDTH = check_number(0, 8)
_SIZE = check_number(1, 1024)
_LINE = check_choice(LINE_STYLES)
_TABLES: dict[str, tuple[type, dict[str, Check]]] = {
    "result_field": (
        ResultFieldTokens,
        {
            "padding": check_spacing_pair,
            "gap": check_spacing,
            "stack_gap": check_spacing,
            "panel_inset": check_spacing_pair,
            "min_height": _SIZE,
            "button_size": _SIZE,
            "icon_size": _SIZE,
            "border_width": _WIDTH,
            "border_role": check_role,
            "hover_border_role": check_role,
            "hover_fill_role": check_role,
            "hover_fill_opacity": check_number(0, 1),
            "focus_role": check_role,
            "focus_width": _WIDTH,
            "focus_gap": _WIDTH,
            "copied_ms": check_number(100, 10_000, whole=True),
            "value_weight": check_choice(WEIGHTS),
            "tabular_figures": check_bool,
            "decimal_align": check_bool,
            "document_min_height": _SIZE,
            "copy_icon": check_icon,
            "copied_icon": check_icon,
        },
    ),
    "note_outline": (
        NoteOutlineTokens,
        {
            "width": _WIDTH,
            "limit_role": check_role,
            "limit_style": _LINE,
            "note_role": check_role,
            "note_style": _LINE,
            "no_value_role": check_role,
            "no_value_style": _LINE,
            "error_role": check_role,
            "error_style": _LINE,
        },
    ),
}


def parse_ui_style(data: Mapping[str, Any], origin: str = STYLE_FILE.name) -> UiStyle:
    """Check parsed tokens and return them typed.

    Raises:
        StyleError: A table or token is unknown or missing, has the wrong type, or is out
            of range; a role isn't in the palette; an icon isn't vendored; or the tokens
            don't fit together.
    """
    return _checked(UiStyle(**parse_tables(data, _TABLES, SCHEMA, origin)), origin)


def _checked(tokens: UiStyle, origin: str) -> UiStyle:
    """Check what no single token can: that the tokens fit together.

    A field must be tall enough for its button, the icon must fit the button, and a note
    outline must be heavier than a field's border, so it reads without its colour (WCAG
    1.4.1).
    """
    field, outline = tokens.result_field, tokens.note_outline
    if field.min_height < field.button_size:
        raise StyleError(
            f"{origin}: result_field.min_height {field.min_height:g} is less than its "
            f"button_size {field.button_size:g}"
        )
    if field.icon_size > field.button_size:
        raise StyleError(
            f"{origin}: result_field.icon_size {field.icon_size:g} is larger than its "
            f"button_size {field.button_size:g}"
        )
    if outline.width <= field.border_width:
        raise StyleError(
            f"{origin}: note_outline.width {outline.width:g} must be heavier than "
            f"result_field.border_width {field.border_width:g}"
        )
    return tokens


def load_ui_style(path: Path = STYLE_FILE) -> UiStyle:
    """Read and check the tokens in ``path``.

    Raises:
        StyleError: The file can't be read, isn't TOML, or its tokens don't check.
    """
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
        raise StyleError(f"{path}: {exc}") from exc
    return parse_ui_style(data, path.name)


@cache
def ui_style() -> UiStyle:
    """Return the shipped tokens, read and checked once."""
    return load_ui_style()
