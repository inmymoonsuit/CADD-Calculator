"""The welcome screen's design tokens, from ``assets/welcome_style.toml`` (ADR-0016).

Every size, colour role, and font the welcome screen uses is a token in that file, and
this module reads, types, range-checks, and documents each one, refusing unknown keys.
The screen reads tokens only, never literals, so restyling it means editing one checked
file. Sizes are logical pixels. Colours are palette roles (``palette.toml``), checked
here to exist in both themes.

Standard library only: the branding loader and the build script use the art budget
without importing Qt.
"""

from __future__ import annotations

import tomllib
from collections.abc import Callable, Mapping
from dataclasses import dataclass, fields
from functools import cache
from pathlib import Path
from typing import Any, NamedTuple

from caddcalc.core.errors import CaddCalcError

ASSETS = Path(__file__).parent / "assets"
STYLE_FILE = ASSETS / "welcome_style.toml"
PALETTE_FILE = ASSETS / "palette.toml"
SCHEMA = 1


class StyleError(CaddCalcError):
    """The welcome style is malformed: an unknown key, a wrong type, or a value out of range."""


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


ANCHORS = frozenset({"top_left", "top_right", "bottom_left", "bottom_right"})
FONTS = frozenset({"display", "body"})


@dataclass(frozen=True)
class ArtTokens:
    """The art slot and what a pack's art may be."""

    slot: Size
    """The art's area, 16:9, in logical pixels."""
    supplied_scale: int
    """Art is supplied at this multiple of the slot's size, so it stays sharp."""
    formats: tuple[str, ...]
    max_bytes: int
    """The largest art or logo file a pack may name."""
    max_px: int
    """The largest art width or height, checked before the art is decoded."""
    grid: int
    """The art template's grid, in logical pixels."""

    @property
    def supplied(self) -> Size:
        """The size to supply art at, in device pixels."""
        return Size(self.slot.width * self.supplied_scale, self.slot.height * self.supplied_scale)


@dataclass(frozen=True)
class CardTokens:
    """The card's frame."""

    corner_radius: float
    """The outer corners' radius as a fraction of the card's height, so they keep their
    proportion when the card shrinks to fit a small screen."""
    border_width: float
    border_role: str


@dataclass(frozen=True)
class TopBarTokens:
    """The bar across the top, with the About button and the X."""

    height: float
    padding: float
    """The space beside its buttons."""
    separator_width: float
    separator_role: str


@dataclass(frozen=True)
class LogoTokens:
    """The logo's region, its bordered box, and what a pack's logo may be."""

    formats: tuple[str, ...]
    region_width: float
    margin_left: float
    margin_top: float
    margin_bottom: float
    padding: float
    """The space inside the box, around the logo."""
    min_size: Size
    """The box's least width and height."""
    border_width: float
    border_role: str
    fill_role: str


@dataclass(frozen=True)
class PaneStyle:
    """The style the name and version panes share: quiet, and readable (ADR-0016 §5)."""

    fill_role: str
    fill_opacity_min: float
    """The fill's least opacity; it rises only as far as the text's contrast needs."""
    border_width: float
    """The border's width; it takes the text's role."""
    text_roles: tuple[str, str]
    """The two text roles to choose between, dark and light; the one that reads wins."""
    min_contrast: float
    """The least contrast ratio of the text against the fill over the art."""
    percentiles: tuple[float, float]
    """The art's luminance under a pane is measured at these two percentiles."""


@dataclass(frozen=True)
class PaneTokens:
    """Where one pane sits, and its text."""

    anchor: str
    """The corner of the art the pane hugs, e.g. ``"top_right"``."""
    inset: float
    """Its distance from that corner's two edges."""
    padding: tuple[float, float]
    """The space around its text: vertical, then horizontal."""
    font: str
    """``"display"`` for the display face, ``"body"`` for the system's UI font."""
    font_size: float
    safe_area: Size
    """The area at its corner that art keeps clear of detail."""


@dataclass(frozen=True)
class TypographyTokens:
    """The display face and its fallbacks; the body text uses the system's UI font."""

    display_family: str
    display_file: str
    """The vendored font file, relative to the assets folder."""
    display_weight: int
    """The weight it's drawn at, from 100 to 900; 700 is bold."""
    fallback_families: tuple[str, ...]
    """Families tried, in order, when the display face can't be loaded."""
    min_font_size: float
    """The least size any text shrinks to when the card shrinks to fit a small screen."""


@dataclass(frozen=True)
class WelcomeStyle:
    """Every token of the welcome screen, checked."""

    art: ArtTokens
    card: CardTokens
    top_bar: TopBarTokens
    logo: LogoTokens
    panes: PaneStyle
    name_pane: PaneTokens
    version_pane: PaneTokens
    typography: TypographyTokens

    @property
    def window(self) -> Size:
        """The card's preferred size: the logo region beside the art, under the top bar."""
        return Size(
            self.logo.region_width + self.art.slot.width,
            self.top_bar.height + self.art.slot.height,
        )

    def safe_area(self, pane: PaneTokens) -> Rect:
        """Where ``pane`` may cover the art, in the art slot's coordinates."""
        slot, area, inset = self.art.slot, pane.safe_area, pane.inset
        x = inset if pane.anchor.endswith("left") else slot.width - inset - area.width
        y = inset if pane.anchor.startswith("top") else slot.height - inset - area.height
        return Rect(x, y, area.width, area.height)


# --- reading --------------------------------------------------------------------------------

Check = Callable[[str, Any], Any]


def _number(low: float, high: float, *, whole: bool = False) -> Check:
    def check(where: str, value: Any) -> float:
        kind = int if whole else int | float
        if not isinstance(value, kind) or isinstance(value, bool) or not low <= value <= high:
            noun = "a whole number" if whole else "a number"
            raise StyleError(f"{where} must be {noun} from {low:g} to {high:g}, not {value!r}")
        return value

    return check


def _pair(low: float, high: float) -> Check:
    item = _number(low, high)

    def check(where: str, value: Any) -> tuple[float, float]:
        if not isinstance(value, list) or len(value) != 2:
            raise StyleError(f"{where} must be two numbers, e.g. [10, 16]")
        return item(where, value[0]), item(where, value[1])

    return check


def _size(low: float, high: float) -> Check:
    pair = _pair(low, high)
    return lambda where, value: Size(*pair(where, value))


def _choice(allowed: frozenset[str]) -> Check:
    def check(where: str, value: Any) -> str:
        if value not in allowed:
            raise StyleError(f"{where} must be one of {', '.join(sorted(allowed))}, not {value!r}")
        return str(value)

    return check


def _text(where: str, value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise StyleError(f"{where} must be non-empty text")
    return value


def _texts(where: str, value: Any) -> tuple[str, ...]:
    if not isinstance(value, list) or not value:
        raise StyleError(f"{where} must be a non-empty list of text")
    return tuple(_text(where, item) for item in value)


def _formats(where: str, value: Any) -> tuple[str, ...]:
    formats = _texts(where, value)
    if not all(f.startswith(".") and f == f.lower() for f in formats):
        raise StyleError(f'{where} must be lowercase file suffixes, e.g. ".png"')
    return formats


def _role(where: str, value: Any) -> str:
    role = _text(where, value)
    palette = _palette()
    if not all(role in palette[scheme] for scheme in ("light", "dark")):
        raise StyleError(f"{where}: {role!r} isn't a palette role in both themes")
    return role


def _roles(where: str, value: Any) -> tuple[str, str]:
    if not isinstance(value, list) or len(value) != 2:
        raise StyleError(f"{where} must be two palette roles, dark text then light")
    return _role(where, value[0]), _role(where, value[1])


def _percentiles(where: str, value: Any) -> tuple[float, float]:
    low, high = _pair(0, 100)(where, value)
    if low >= high:
        raise StyleError(f"{where} must rise, e.g. [5, 95]")
    return low, high


_WIDTH = _number(0, 8)
_LENGTH = _number(0, 1024)
_PANE: dict[str, Check] = {
    "anchor": _choice(ANCHORS),
    "inset": _LENGTH,
    "padding": _pair(0, 64),
    "font": _choice(FONTS),
    "font_size": _number(1, 256),
    "safe_area": _size(0, 4096),
}
_TABLES: dict[str, tuple[type, dict[str, Check]]] = {
    "art": (
        ArtTokens,
        {
            "slot": _size(1, 4096),
            "supplied_scale": _number(1, 4, whole=True),
            "formats": _formats,
            "max_bytes": _number(1, 100_000_000, whole=True),
            "max_px": _number(1, 16384, whole=True),
            "grid": _number(1, 1024, whole=True),
        },
    ),
    "card": (
        CardTokens,
        {"corner_radius": _number(0, 0.1), "border_width": _WIDTH, "border_role": _role},
    ),
    "top_bar": (
        TopBarTokens,
        {
            "height": _number(1, 256),
            "padding": _LENGTH,
            "separator_width": _WIDTH,
            "separator_role": _role,
        },
    ),
    "logo": (
        LogoTokens,
        {
            "formats": _formats,
            "region_width": _number(1, 1024),
            "margin_left": _LENGTH,
            "margin_top": _LENGTH,
            "margin_bottom": _LENGTH,
            "padding": _LENGTH,
            "min_size": _size(1, 1024),
            "border_width": _WIDTH,
            "border_role": _role,
            "fill_role": _role,
        },
    ),
    "panes": (
        PaneStyle,
        {
            "fill_role": _role,
            "fill_opacity_min": _number(0, 1),
            "border_width": _WIDTH,
            "text_roles": _roles,
            "min_contrast": _number(1, 21),
            "percentiles": _percentiles,
        },
    ),
    "name_pane": (PaneTokens, _PANE),
    "version_pane": (PaneTokens, _PANE),
    "typography": (
        TypographyTokens,
        {
            "display_family": _text,
            "display_file": _text,
            "display_weight": _number(100, 900, whole=True),
            "fallback_families": _texts,
            "min_font_size": _number(1, 64),
        },
    ),
}


def parse_style(data: Mapping[str, Any], origin: str = STYLE_FILE.name) -> WelcomeStyle:
    """Check parsed tokens and return them typed.

    Raises:
        StyleError: A table or token is unknown or missing, has the wrong type, or is out
            of range; or a role isn't in the palette.
    """
    unknown = sorted(set(data) - set(_TABLES) - {"schema"})
    if unknown:
        raise StyleError(f"{origin}: unknown table(s) {', '.join(unknown)}")
    if data.get("schema") != SCHEMA:
        raise StyleError(f"{origin}: schema must be {SCHEMA}, not {data.get('schema')!r}")
    tables: dict[str, Any] = {}
    for name, (kind, checks) in _TABLES.items():
        table = data.get(name)
        if not isinstance(table, Mapping):
            raise StyleError(f"{origin}: [{name}] is missing")
        extra = sorted(set(table) - set(checks))
        missing = sorted(set(checks) - set(table))
        if extra or missing:
            raise StyleError(f"{origin}: [{name}] has unknown {extra} and lacks {missing}")
        values = {
            key: check(f"{origin}: {name}.{key}", table[key]) for key, check in checks.items()
        }
        tables[name] = kind(**{f.name: values[f.name] for f in fields(kind)})
    return WelcomeStyle(**tables)


def load_style(path: Path = STYLE_FILE) -> WelcomeStyle:
    """Read and check the tokens in ``path``.

    Raises:
        StyleError: The file can't be read, isn't TOML, or its tokens don't check.
    """
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
        raise StyleError(f"{path}: {exc}") from exc
    return parse_style(data, path.name)


@cache
def style() -> WelcomeStyle:
    """Return the shipped tokens, read and checked once."""
    return load_style()


@cache
def _palette() -> dict[str, Any]:
    data: dict[str, Any] = tomllib.loads(PALETTE_FILE.read_text(encoding="utf-8"))
    return data


# --- contrast (WCAG 2) ----------------------------------------------------------------------


def luminance(color: str) -> float:
    """Return the relative luminance of a ``#RRGGBB`` colour, from 0 (black) to 1."""
    channels = [int(color[i : i + 2], 16) / 255 for i in (1, 3, 5)]
    r, g, b = (c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in channels)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(first: float, second: float) -> float:
    """Return the contrast ratio of two relative luminances, from 1 to 21."""
    high, low = max(first, second), min(first, second)
    return (high + 0.05) / (low + 0.05)
