"""The UI palette (gui/assets/palette.toml) must stay well formed and readable."""

from __future__ import annotations

import math
import re
import tomllib
from importlib.resources import files
from typing import Any

import pytest

PALETTE: dict[str, Any] = tomllib.loads(
    files("caddcalc.gui").joinpath("assets/palette.toml").read_text(encoding="utf-8")
)
COLORS: dict[str, str] = PALETTE["colors"]

# (foreground role, background role, minimum WCAG contrast ratio)
# 4.5 is AA for normal text; 3.0 is AA for large text and for UI parts like borders and icons.
PAIRS = [
    ("text", "background", 4.5),
    ("on_primary", "primary", 4.5),
    ("on_accent", "accent", 4.5),
    ("on_error", "error", 4.5),
    ("on_warning", "warning", 4.5),
    ("muted", "background", 3.0),
    ("icon", "background", 3.0),
    ("icon_active", "background", 3.0),
    ("icon_error", "background", 3.0),
    ("icon_warning", "background", 3.0),
    ("text_error", "background", 4.5),
    ("text_warning", "background", 4.5),
    ("outline_error", "background", 3.0),
    ("outline_note", "background", 3.0),
    ("outline_limit", "background", 3.0),
    ("outline_no_value", "background", 3.0),
    ("text_limit", "background", 4.5),
    ("on_welcome_scrim", "welcome_scrim", 4.5),
    ("welcome_line", "background", 3.0),
    ("card_border", "background", 3.0),
    ("welcome_ink", "welcome_paper", 4.5),
    ("field_border", "background", 3.0),
    ("focus_ring", "background", 3.0),
]


def luminance(hex_color: str) -> float:
    channels = [int(hex_color[i : i + 2], 16) / 255 for i in (1, 3, 5)]
    r, g, b = (c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in channels)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a: str, b: str) -> float:
    hi, lo = sorted((luminance(a), luminance(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def test_colors_are_hex() -> None:
    for name, value in COLORS.items():
        assert re.fullmatch(r"#[0-9A-F]{6}", value), f"{name}: {value!r}"


@pytest.mark.parametrize("theme", ["light", "dark"])
def test_roles_name_defined_colors(theme: str) -> None:
    for role, name in PALETTE[theme].items():
        assert name in COLORS, f"{theme}.{role} names unknown color {name!r}"
    assert set(PALETTE["light"]) == set(PALETTE["dark"]), "both themes define the same roles"


@pytest.mark.parametrize("theme", ["light", "dark"])
@pytest.mark.parametrize(("fg", "bg", "minimum"), PAIRS)
def test_role_pairs_are_readable(theme: str, fg: str, bg: str, minimum: float) -> None:
    roles = PALETTE[theme]
    ratio = contrast(COLORS[roles[fg]], COLORS[roles[bg]])
    assert ratio >= minimum, f"{theme}: {fg} on {bg} is {ratio:.2f}:1, needs {minimum}:1"


def test_gui_code_takes_every_colour_from_the_palette() -> None:
    """Hex colours bypass the light and dark themes; only the palette loader reads them."""
    gui = files("caddcalc.gui")
    literal = re.compile(r"#[0-9A-Fa-f]{6}\b|#[0-9A-Fa-f]{3}\b")
    offenders = {
        path.name: literal.findall(path.read_text(encoding="utf-8"))
        for path in gui.iterdir()
        if path.name.endswith(".py") and path.name != "icons.py"
    }
    assert not {name: found for name, found in offenders.items() if found}


def test_known_ratios() -> None:
    """Spot-check the contrast math against values computed by hand."""
    assert contrast("#21251F", "#FFFFFF") == pytest.approx(15.57, abs=0.01)
    assert contrast("#A3122F", "#FFFFFF") == pytest.approx(7.82, abs=0.01)


def _lab(hex_color: str) -> tuple[float, float, float]:
    """CIE L*a*b* of an sRGB colour, under D65 (IEC 61966-2-1; CIE 15)."""
    rgb = [int(hex_color[i : i + 2], 16) / 255 for i in (1, 3, 5)]
    r, g, b = (c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in rgb)
    x = (0.4124564 * r + 0.3575761 * g + 0.1804375 * b) / 0.95047
    y = 0.2126729 * r + 0.7151522 * g + 0.0721750 * b
    z = (0.0193339 * r + 0.1191920 * g + 0.9503041 * b) / 1.08883

    def f(t: float) -> float:
        return t ** (1 / 3) if t > (6 / 29) ** 3 else t / (3 * (6 / 29) ** 2) + 4 / 29

    return 116 * f(y) - 16, 500 * (f(x) - f(y)), 200 * (f(y) - f(z))


def delta_e_2000(first: str, second: str) -> float:
    """CIEDE2000 colour difference of two sRGB colours."""
    return delta_e_lab(_lab(first), _lab(second))


Lab = tuple[float, float, float]


def delta_e_lab(first: Lab, second: Lab) -> float:
    """CIEDE2000 colour difference (Sharma, Wu, and Dalal, Color Res. Appl. 30, 2005)."""
    (l1, a1, b1), (l2, a2, b2) = first, second
    c_mean = (math.hypot(a1, b1) + math.hypot(a2, b2)) / 2
    g = 0.5 * (1 - math.sqrt(c_mean**7 / (c_mean**7 + 25**7)))
    a1p, a2p = (1 + g) * a1, (1 + g) * a2
    c1p, c2p = math.hypot(a1p, b1), math.hypot(a2p, b2)
    h1p = math.degrees(math.atan2(b1, a1p)) % 360 if c1p else 0.0
    h2p = math.degrees(math.atan2(b2, a2p)) % 360 if c2p else 0.0
    dl, dc = l2 - l1, c2p - c1p
    dh = 0.0
    if c1p * c2p:
        dh = h2p - h1p
        dh = dh - 360 if dh > 180 else dh + 360 if dh < -180 else dh
    dhp = 2 * math.sqrt(c1p * c2p) * math.sin(math.radians(dh / 2))
    lp, cp = (l1 + l2) / 2, (c1p + c2p) / 2
    hp = h1p + h2p
    if c1p * c2p:
        hp = (h1p + h2p) / 2 if abs(h1p - h2p) <= 180 else (h1p + h2p + 360) / 2 % 360
    t = (
        1
        - 0.17 * math.cos(math.radians(hp - 30))
        + 0.24 * math.cos(math.radians(2 * hp))
        + 0.32 * math.cos(math.radians(3 * hp + 6))
        - 0.20 * math.cos(math.radians(4 * hp - 63))
    )
    sl = 1 + 0.015 * (lp - 50) ** 2 / math.sqrt(20 + (lp - 50) ** 2)
    sc, sh = 1 + 0.045 * cp, 1 + 0.015 * cp * t
    rt = (
        -2
        * math.sqrt(cp**7 / (cp**7 + 25**7))
        * math.sin(math.radians(60 * math.exp(-(((hp - 275) / 25) ** 2))))
    )
    return math.sqrt(
        (dl / sl) ** 2 + (dc / sc) ** 2 + (dhp / sh) ** 2 + rt * (dc / sc) * (dhp / sh)
    )


def test_delta_e_2000_matches_the_published_test_data() -> None:
    """Pairs 1 and 17 of Sharma, Wu, and Dalal's table."""
    assert delta_e_lab((50.0, 2.6772, -79.7751), (50.0, 0.0, -82.7485)) == pytest.approx(
        2.0425, abs=1e-4
    )
    assert delta_e_lab((50.0, 2.5, 0.0), (73.0, 25.0, -18.0)) == pytest.approx(27.1492, abs=1e-4)


@pytest.mark.parametrize("theme", ["light", "dark"])
def test_focus_never_looks_like_an_outline_or_a_border(theme: str) -> None:
    """ADR-0017 §3: focus is ΔE2000 ≥ 15 from every outline and border role."""
    roles = PALETTE[theme]
    focus = COLORS[roles["focus_ring"]]
    others = [
        role
        for role in roles
        if role.startswith("outline_") or role in ("field_border", "card_border", "welcome_line")
    ]
    near = {role: round(delta_e_2000(focus, COLORS[roles[role]]), 1) for role in others}
    assert min(near.values()) >= 15, near
