"""The welcome screen's design tokens (ADR-0016 §1): read, checked, documented, and used."""

from __future__ import annotations

import ast
import re
import tomllib
from dataclasses import fields
from pathlib import Path
from typing import Any

import pytest

from caddcalc.gui.welcome_style import (
    STYLE_FILE,
    Size,
    StyleError,
    WelcomeStyle,
    contrast,
    luminance,
    parse_style,
    style,
)

ROOT = Path(__file__).parents[1]
SPEC = ROOT / "docs" / "dev" / "design" / "welcome-screen.md"
WELCOME = ROOT / "src" / "caddcalc" / "gui" / "welcome.py"


def shipped() -> dict[str, Any]:
    data: dict[str, Any] = tomllib.loads(STYLE_FILE.read_text(encoding="utf-8"))
    return data


def test_the_shipped_tokens_load_and_add_up() -> None:
    tokens = style()
    assert tokens.art.slot.width / tokens.art.slot.height == 16 / 9
    assert Size(1920, 1080) == tokens.art.supplied
    assert tokens.window == Size(
        tokens.logo.region_width + tokens.art.slot.width,
        tokens.top_bar.height + tokens.art.slot.height,
    )
    assert tokens.panes.text_roles == ("welcome_ink", "welcome_paper")


@pytest.mark.parametrize("pane", ["name_pane", "version_pane"])
def test_each_panes_safe_area_lies_inside_the_art_slot(pane: str) -> None:
    tokens = style()
    area = tokens.safe_area(getattr(tokens, pane))
    assert area.x >= 0 and area.y >= 0
    assert area.x + area.width <= tokens.art.slot.width
    assert area.y + area.height <= tokens.art.slot.height


def edited(table: str, key: str, value: Any) -> dict[str, Any]:
    data = shipped()
    data[table] = {**data[table], key: value}
    return data


@pytest.mark.parametrize(
    ("data", "message"),
    [
        (edited("card", "shadow", 4), r"\[card\] has unknown \['shadow'\]"),
        ({**shipped(), "theme": {}}, "unknown table"),
        ({**shipped(), "schema": 2}, "schema must be 1"),
        (edited("card", "corner_radius", 0.5), "card.corner_radius must be a number from 0"),
        (edited("top_bar", "height", "32"), "top_bar.height must be a number"),
        (edited("art", "max_px", 4096.5), "art.max_px must be a whole number"),
        (edited("panes", "fill_opacity_min", True), "fill_opacity_min must be a number"),
        (edited("logo", "border_role", "ink"), "'ink' isn't a palette role in both themes"),
        (edited("name_pane", "anchor", "middle"), "name_pane.anchor must be one of"),
        (edited("panes", "percentiles", [95, 5]), "percentiles must rise"),
        (edited("logo", "formats", ["PNG"]), "lowercase file suffixes"),
    ],
)
def test_the_loader_refuses_a_bad_token(data: dict[str, Any], message: str) -> None:
    with pytest.raises(StyleError, match=message):
        parse_style(data)


def test_a_missing_token_is_refused() -> None:
    data = shipped()
    del data["logo"]["padding"]
    with pytest.raises(StyleError, match=r"\[logo\] has unknown \[\] and lacks \['padding'\]"):
        parse_style(data)


def _quote(value: Any) -> str:
    """How the spec writes a token's value: a pair as ``a × b``, a list joined by commas."""
    if (
        isinstance(value, list)
        and len(value) == 2
        and all(isinstance(v, int | float) for v in value)
    ):
        return f"{value[0]} × {value[1]}"
    if isinstance(value, list):
        return ", ".join(str(v) for v in value)
    if isinstance(value, int) and not isinstance(value, bool) and value >= 10_000:
        return f"{value:,}"
    return str(value)


def test_the_spec_quotes_every_token() -> None:
    """docs/dev/design/welcome-screen.md is written by hand; this keeps it in step."""
    spec = SPEC.read_text(encoding="utf-8")
    missing = [
        f"| `{table}.{key}` | {_quote(value)} |"
        for table, tokens in shipped().items()
        if isinstance(tokens, dict)
        for key, value in tokens.items()
        if f"| `{table}.{key}` | {_quote(value)} |" not in spec
    ]
    assert missing == [], missing


def test_the_spec_quotes_the_sizes_and_safe_areas_they_give() -> None:
    tokens = style()
    spec = SPEC.read_text(encoding="utf-8")
    slot, supplied, window = tokens.art.slot, tokens.art.supplied, tokens.window
    quoted = [
        f"**{int(slot.width)} × {int(slot.height)}**",
        f"**{int(supplied.width)} × {int(supplied.height)}**",
        f"({int(window.width)} × {int(window.height)})",
        f"**{tokens.art.max_bytes // 1_000_000} MB**",
        f"**{tokens.art.max_px} px**",
    ]
    for pane, name in ((tokens.name_pane, "Name pane"), (tokens.version_pane, "Version pane")):
        cells = " | ".join(str(int(v)) for v in tokens.safe_area(pane))
        quoted.append(f"| {name} | {cells} |")
    missing = [text for text in quoted if text not in spec]
    assert missing == [], missing


def test_every_token_table_has_its_typed_class() -> None:
    """Each table is typed in the loader, so the file and the classes can't drift."""
    assert {f.name for f in fields(WelcomeStyle)} == set(shipped()) - {"schema"}


_ALLOWED_NUMBERS = {0, 1, 2}
"""Numbers a layout may still write: zero, one, and halving."""
_LITERAL = re.compile(r"#[0-9A-Fa-f]{3,8}\b|\d\s*px\b|rgba?\(")


def test_the_widget_takes_every_size_and_colour_from_the_tokens() -> None:
    """ADR-0016 §1: no layout number or colour is written in welcome.py."""
    tree = ast.parse(WELCOME.read_text(encoding="utf-8"))
    found = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Constant):
            continue
        value = node.value
        if isinstance(value, int | float) and not isinstance(value, bool):
            if value not in _ALLOWED_NUMBERS:
                found.append(f"line {node.lineno}: {value!r}")
        elif isinstance(value, str) and _LITERAL.search(value):
            found.append(f"line {node.lineno}: {value!r}")
    assert found == [], found


def test_contrast_follows_wcag() -> None:
    assert contrast(luminance("#FFFFFF"), luminance("#000000")) == pytest.approx(21)
    assert contrast(luminance("#777777"), luminance("#777777")) == 1
