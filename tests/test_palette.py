"""The UI palette (gui/assets/palette.toml) must stay well formed and readable."""

from __future__ import annotations

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


def test_known_ratios() -> None:
    """Spot-check the contrast math against values computed by hand."""
    assert contrast("#21251F", "#FFFFFF") == pytest.approx(15.57, abs=0.01)
    assert contrast("#A3122F", "#FFFFFF") == pytest.approx(7.82, abs=0.01)
