"""The welcome screen's design tokens (ADR-0016 §1): read, checked, documented, and used."""

from __future__ import annotations

import ast
import math
import re
import tomllib
from dataclasses import fields
from pathlib import Path
from typing import Any

import pytest

from caddcalc.gui.welcome_style import (
    RGB,
    SPACING,
    STYLE_FILE,
    Size,
    StyleError,
    WelcomeStyle,
    art_contrast,
    background_spread,
    contrast,
    luminance,
    pane_fill,
    pane_reads,
    parse_style,
    rgb,
    sample_grid,
    style,
    with_overrides,
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
        tokens.art.slot.width, tokens.top_bar.height + tokens.art.slot.height
    ), "the art spans the card; the logo box floats over it (S2)"
    assert tokens.panes.text_roles == ("welcome_ink", "welcome_paper")
    assert tokens.panes.fill_roles == ("welcome_paper", "welcome_ink"), "dark on light"
    assert (tokens.name_pane.min_contrast, tokens.version_pane.min_contrast) == (3, 4.5)


@pytest.mark.parametrize("pane", ["name_pane", "version_pane"])
def test_each_panes_safe_area_lies_inside_the_art_slot(pane: str) -> None:
    tokens = style()
    area = tokens.safe_area(getattr(tokens, pane))
    assert area.x >= 0 and area.y >= 0
    assert area.x + area.width <= tokens.art.slot.width
    assert area.y + area.height <= tokens.art.slot.height


def test_the_logo_box_fits_its_region_beside_the_panes() -> None:
    tokens = style()
    region, area = tokens.logo_region, tokens.logo_area
    assert (region.x, region.y, region.height) == (0, 0, tokens.art.slot.height)
    assert min(area.width, area.height) >= tokens.logo.min_short_side
    for pane in (tokens.name_pane, tokens.version_pane):
        assert tokens.safe_area(pane).x >= region.x + region.width, "no overlap"


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
        (edited("card", "corner_radius", 40), "card.corner_radius must be a number from 0"),
        (edited("logo", "padding", 5), r"logo\.padding must be on the spacing scale, 2, 4"),
        (edited("name_pane", "inset", 20), r"name_pane\.inset must be on the spacing scale"),
        (edited("version_pane", "padding", [2, 3]), "on the spacing scale.*not 3"),
        (edited("typography", "display_weight", "heavy"), "must be one of bold, regular"),
        (edited("typography", "display_weight", 700), "must be one of bold, regular"),
        (edited("version_pane", "inset", 4), "version_pane.inset 4 is less than the card's"),
        (edited("logo", "region_width", 60), "less than its box's least short side, 48"),
        (edited("logo", "max_long_side", 40), "max_long_side 40 is less than"),
        (edited("top_bar", "height", "32"), "top_bar.height must be a number"),
        (edited("art", "max_px", 4096.5), "art.max_px must be a whole number"),
        (edited("panes", "fill_opacity_min", True), "fill_opacity_min must be a number"),
        (edited("logo", "border_role", "ink"), "'ink' isn't a palette role in both themes"),
        (edited("name_pane", "anchor", "middle"), "name_pane.anchor must be one of"),
        (edited("panes", "percentile", 60), "panes.percentile must be a number from 0 to 50"),
        (edited("panes", "max_background_spread", 0.9), "must be a number from 1 to 21"),
        (edited("name_pane", "min_contrast", 2.9), "below WCAG 2's 3:1 for large text"),
        (edited("version_pane", "min_contrast", 3), "below WCAG 2's 4.5:1 for normal text"),
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
    areas = (
        (tokens.logo_region, "Logo box"),
        (tokens.safe_area(tokens.name_pane), "Name pane"),
        (tokens.safe_area(tokens.version_pane), "Version pane"),
    )
    for area, name in areas:
        cells = " | ".join(str(int(v)) for v in area)
        quoted.append(f"| {name} | {cells} |")
    missing = [text for text in quoted if text not in spec]
    assert missing == [], missing


def test_the_spec_quotes_the_spacing_scale() -> None:
    scale = ", ".join(str(step) for step in SPACING)
    spec = " ".join(SPEC.read_text(encoding="utf-8").split())
    assert f"**{scale}** px" in spec


def test_every_token_table_has_its_typed_class() -> None:
    """Each table is typed in the loader, so the file and the classes can't drift."""
    assert {f.name for f in fields(WelcomeStyle)} == set(shipped()) - {"schema"}


_ALLOWED_NUMBERS = {0, 1, 2}
"""Numbers a layout may still write: zero, one, and halving."""
_LITERAL = re.compile(r"#[0-9A-Fa-f]{3,8}\b|\d\s*px\b|rgba?\(")


@pytest.mark.parametrize("module", ["welcome.py", "result_fields.py"])
def test_the_widget_takes_every_size_and_colour_from_the_tokens(module: str) -> None:
    """ADR-0016 §1, ADR-0017 §7: no layout number or colour is written in a widget."""
    tree = ast.parse((WELCOME.parent / module).read_text(encoding="utf-8"))
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


INK, WHITE = rgb("#21251F"), rgb("#FFFFFF")
BLACK: RGB = (0, 0, 0)
PAIRS = [(INK, WHITE), (WHITE, INK)]
"""Ink text on a white fill, white text on an ink fill: the shipped pairs."""


GREY: RGB = (60, 60, 60)


def mixed(*parts: tuple[RGB, float], count: int = 4096) -> list[RGB]:
    """Art samples: each colour in its share of ``count``."""
    return [colour for colour, share in parts for _ in range(round(share * count))]


def test_the_sample_grid_keeps_real_pixels_and_enough_of_them() -> None:
    small = bytes([10, 20, 30, 0] * 6)
    assert sample_grid(small, 3, 2, 4096) == [(10, 20, 30)] * 6, "every pixel when few"
    width, height = 400, 50
    pixels = bytearray()
    for y in range(height):
        for x in range(width):
            pixels += bytes([255 if (x + y) % 2 else 0] * 3 + [0])  # a one-pixel check
    samples = sample_grid(bytes(pixels), width, height, 4096)
    assert 4096 <= len(samples) < width * height
    assert set(samples) <= {BLACK, WHITE}, "nearest pixels: nothing is averaged to grey"


CALM = [(225 + 15 * i // 4095, 220 + 12 * i // 4095, 205 + 10 * i // 4095) for i in range(4096)]
"""Generated calm art: a soft, light gradient, as a quiet render is."""


@pytest.mark.parametrize("needed", [3, 4.5], ids=["title", "version"])
@pytest.mark.parametrize(
    ("art", "pair", "raised"),
    [
        (mixed(((244, 241, 234), 1.0)), 0, False),  # flat, light art: ink on white, the floor
        (CALM, 0, False),  # calm art: the floor
        (mixed((BLACK, 0.5), ((16, 20, 24), 0.5)), 1, False),  # dark art: white on ink
        (mixed((BLACK, 0.5), (WHITE, 0.5)), None, True),  # busy art: a fill rises
        (mixed((GREY, 0.06), ((0, 0, 255), 0.88), (WHITE, 0.06)), None, True),  # saturated
        (mixed((GREY, 0.06), ((255, 0, 0), 0.88), (WHITE, 0.06)), None, True),
        (mixed((GREY, 0.06), ((0, 255, 0), 0.88), (WHITE, 0.06)), None, True),
    ],
    ids=["light", "calm", "dark", "busy", "blue", "red", "green"],
)
def test_a_pane_stays_quiet_unless_the_art_would_hide_its_text(
    art: list[RGB], pair: int | None, raised: bool, needed: float
) -> None:
    panes = style().panes
    floor = math.ceil(panes.fill_opacity_min * 255)
    index, alpha = pane_fill(art, PAIRS, panes, needed)
    if pair is not None:
        assert index == pair
    text, fill = PAIRS[index]
    assert (alpha > floor) == raised and alpha >= floor
    assert art_contrast(art, text, fill, alpha, panes.percentile) >= needed
    assert background_spread(art, fill, alpha, panes.percentile) <= panes.max_background_spread
    if raised:
        assert not pane_reads(art, text, fill, alpha - 1, panes, needed), "the least opacity"


def test_busy_art_is_calmed_where_contrast_alone_would_stop() -> None:
    """Over a black-and-white check, contrast alone stops too low; the fill rises to calm.

    Ink reaches 3:1 at a low fill, but the letters would sit on a background still
    alternating strongly, which breaks them up.
    """
    panes, art = style().panes, mixed((BLACK, 0.5), (WHITE, 0.5))
    contrast_only = 0
    while art_contrast(art, INK, WHITE, contrast_only, panes.percentile) < 3:
        contrast_only += 1
    assert background_spread(art, WHITE, contrast_only, panes.percentile) > 5, "still busy"
    index, alpha = pane_fill(art, PAIRS, panes, 3)
    text, fill = PAIRS[index]
    assert alpha > contrast_only
    assert background_spread(art, fill, alpha, panes.percentile) <= panes.max_background_spread
    assert art_contrast(art, text, fill, alpha, panes.percentile) >= 3


def test_calm_art_stays_at_the_floor_with_room_to_spare() -> None:
    panes = style().panes
    floor = math.ceil(panes.fill_opacity_min * 255)
    assert background_spread(CALM, WHITE, floor, panes.percentile) < 1.2
    assert pane_fill(CALM, PAIRS, panes, 3) == (0, floor)


def test_saturated_art_is_held_to_the_contrast_where_two_percentiles_were_not() -> None:
    """Grey 6%, blue 88%, white 6%: every blue pixel, the bulk of the pane, must read."""
    blue = (0, 0, 255)
    art = mixed((GREY, 0.06), (blue, 0.88), (WHITE, 0.06))
    panes = style().panes
    for needed in (3, 4.5):
        index, alpha = pane_fill(art, PAIRS, panes, needed)
        text, fill = PAIRS[index]
        assert art_contrast([blue], text, fill, alpha, 0) >= needed


def test_the_title_needs_less_fill_than_the_version() -> None:
    """Large text needs 3:1, other text 4.5:1 (WCAG 2), so mid-tone art lifts it less."""
    panes, art = style().panes, mixed(((115, 115, 115), 0.5), ((140, 140, 140), 0.5))
    _pair, title = pane_fill(art, PAIRS, panes, 3)
    _pair, version = pane_fill(art, PAIRS, panes, 4.5)
    assert title < version


def test_an_unreadable_pair_becomes_opaque_in_the_pair_that_reads_best() -> None:
    mid = (119, 119, 119)
    pairs = [(INK, mid), (WHITE, mid)]
    art = mixed((BLACK, 0.5), (WHITE, 0.5))
    assert pane_fill(art, pairs, style().panes, 4.5) == (1, 255), "white on grey: 4.48"


def test_a_pack_may_override_its_whitelist() -> None:
    tokens = with_overrides(
        style(),
        {
            "logo": {"fill_role": "welcome_paper", "margin_left": 24, "padding": 6},
            "panes": {"fill_opacity_min": 0.3, "fill_roles": ["welcome_scrim", "welcome_ink"]},
        },
        "pack",
    )
    assert (tokens.logo.fill_role, tokens.logo.margin_left, tokens.logo.padding) == (
        "welcome_paper",
        24,
        6,
    )
    assert tokens.panes.fill_opacity_min == 0.3
    assert tokens.panes.fill_roles == ("welcome_scrim", "welcome_ink")
    assert tokens.logo_area.x == 24 and tokens.card == style().card, "the rest is shipped"


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"card": {"corner_radius": 0}}, "may override only .*, not 'card'"),
        ({"typography": {"display_weight": "bold"}}, "not 'typography'"),
        ({"logo": {"min_short_side": 10}}, r"not logo\.min_short_side"),
        ({"panes": {"text_roles": ["welcome_ink", "welcome_ink"]}}, r"not panes\.text_roles"),
        ({"panes": {"max_background_spread": 3}}, r"not panes\.max_background_spread"),
        ({"logo": 3}, r"logo must be a table, \[welcome\.style\.logo\]"),
        ("panes", r"must be a table, \[welcome\.style\]"),
        ({"panes": {"fill_opacity_min": 1.5}}, "fill_opacity_min must be a number from 0 to 1"),
        ({"logo": {"fill_role": "fuchsia"}}, "'fuchsia' isn't a palette role"),
        ({"logo": {"margin_left": 60}}, "margin_left must be on the spacing scale"),
        ({"logo": {"padding": 24}}, "logo.padding 24 leaves no room"),
        (
            {"panes": {"fill_roles": ["welcome_line", "welcome_line"]}},
            r"no pane text reaches 4\.5:1 on its own fill",
        ),
    ],
)
def test_a_pack_may_not_override_anything_else(overrides: Any, message: str) -> None:
    with pytest.raises(StyleError, match=message):
        with_overrides(style(), overrides, "pack")
