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

import math
import tomllib
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, fields, replace
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


SCHEMES = ("light", "dark")
SPACING = (2, 4, 6, 8, 12, 16, 24, 32)
"""The spacing scale: every inset, margin, and padding is one of these (ADR-0016,
amendments). Sizes, such as the logo region's width, are free."""
WEIGHTS = frozenset({"regular", "bold"})
LARGE_TEXT_PX = 24
"""WCAG 2's large text: 18 points, 24 px at 96 dpi, or more."""
LARGE_TEXT_CONTRAST = 3.0
"""WCAG 2's least contrast for large text (success criterion 1.4.3, AA)."""
NORMAL_TEXT_CONTRAST = 4.5
"""WCAG 2's least contrast for other text (success criterion 1.4.3, AA)."""
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
    """The outer corners' radius; it shrinks with the card on a small screen."""
    border_width: float
    border_role: str


@dataclass(frozen=True)
class TopBarTokens:
    """The bar across the top, with the About button and the X."""

    height: float
    padding: float
    """The space beside its buttons."""
    button_size: float
    """The About button's and the X's width and height."""
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
    min_short_side: float
    """The box's least short side; the box keeps the logo's shape up to it."""
    max_long_side: float
    """The box's greatest long side, so no logo becomes a full-height pillar."""
    border_width: float
    border_role: str
    fill_role: str


@dataclass(frozen=True)
class PaneStyle:
    """The style the name and version panes share: quiet, and readable (ADR-0016 §5)."""

    text_roles: tuple[str, str]
    """The two text roles to choose between: dark, then light."""
    fill_roles: tuple[str, str]
    """Each text role's own fill: a light fill under the dark text, a dark fill under
    the light text. The pair that needs the least opacity wins."""
    fill_opacity_min: float
    """The fill's least opacity; it rises only as far as the text's contrast needs."""
    border_width: float
    """The border's width; it takes the text's role."""
    percentile: float
    """The share of the art under a pane, in percent, that may fall short of the
    contrast: the contrast is held at this percentile of the pixels."""
    min_samples: int
    """The least number of art pixels sampled under a pane, on a fixed grid."""


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
    """Its text's pixel size; the display face's snaps to its pixel grid."""
    min_contrast: float
    """The least contrast of its text against its fill over the art: 3:1 for large text,
    4.5:1 otherwise (WCAG 2)."""
    safe_area: Size
    """The area at its corner that art keeps clear of detail."""


@dataclass(frozen=True)
class TypographyTokens:
    """The display face and its fallbacks; the body text uses the system's UI font."""

    display_family: str
    display_file: str
    """The vendored font file, relative to the assets folder."""
    display_weight: str
    """``"regular"``, which keeps the face on its pixel grid, or ``"bold"``, Qt's bold,
    which each platform's text engine draws differently."""
    display_em_pixels: int
    """The face's design pixels per em; its size snaps to whole multiples of these."""
    display_cap_height: float
    """Its capitals' height as a fraction of the em, for centring on the cap band."""
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
        """The card's preferred size: the art, at the card's full width, under the top bar.

        The logo box floats over the art's left edge (S2), so it adds no width.
        """
        return Size(self.art.slot.width, self.top_bar.height + self.art.slot.height)

    @property
    def logo_region(self) -> Rect:
        """The art's left edge, where the logo box floats, in the slot's coordinates.

        The art keeps it clear of detail, like the panes' safe areas.
        """
        return Rect(0, 0, self.logo.region_width, self.art.slot.height)

    @property
    def logo_area(self) -> Rect:
        """Where the logo box may sit: the logo region less its minimum margins."""
        logo, height = self.logo, self.art.slot.height
        return Rect(
            logo.margin_left,
            logo.margin_top,
            logo.region_width - logo.margin_left,
            height - logo.margin_top - logo.margin_bottom,
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
    if not all(role in palette[scheme] for scheme in SCHEMES):
        raise StyleError(f"{where}: {role!r} isn't a palette role in both themes")
    return role


def _roles(where: str, value: Any) -> tuple[str, str]:
    if not isinstance(value, list) or len(value) != 2:
        raise StyleError(f"{where} must be two palette roles")
    return _role(where, value[0]), _role(where, value[1])


def _spacing(where: str, value: Any) -> float:
    if isinstance(value, bool) or value not in SPACING:
        scale = ", ".join(str(step) for step in SPACING)
        raise StyleError(f"{where} must be on the spacing scale, {scale}; not {value!r}")
    return float(value)


def _spacing_pair(where: str, value: Any) -> tuple[float, float]:
    if not isinstance(value, list) or len(value) != 2:
        raise StyleError(f"{where} must be two numbers, e.g. [8, 16]")
    return _spacing(where, value[0]), _spacing(where, value[1])


_WIDTH = _number(0, 8)
_LENGTH = _number(0, 1024)
_PANE: dict[str, Check] = {
    "anchor": _choice(ANCHORS),
    "inset": _spacing,
    "padding": _spacing_pair,
    "font": _choice(FONTS),
    "font_size": _number(1, 256),
    "min_contrast": _number(1, 21),
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
        {"corner_radius": _number(0, 32), "border_width": _WIDTH, "border_role": _role},
    ),
    "top_bar": (
        TopBarTokens,
        {
            "height": _number(1, 256),
            "padding": _spacing,
            "button_size": _number(1, 256),
            "separator_width": _WIDTH,
            "separator_role": _role,
        },
    ),
    "logo": (
        LogoTokens,
        {
            "formats": _formats,
            "region_width": _number(1, 1024),
            "margin_left": _spacing,
            "margin_top": _spacing,
            "margin_bottom": _spacing,
            "padding": _spacing,
            "min_short_side": _number(1, 1024),
            "max_long_side": _number(1, 4096),
            "border_width": _WIDTH,
            "border_role": _role,
            "fill_role": _role,
        },
    ),
    "panes": (
        PaneStyle,
        {
            "text_roles": _roles,
            "fill_roles": _roles,
            "fill_opacity_min": _number(0, 1),
            "border_width": _WIDTH,
            "percentile": _number(0, 50),
            "min_samples": _number(1, 1_000_000, whole=True),
        },
    ),
    "name_pane": (PaneTokens, _PANE),
    "version_pane": (PaneTokens, _PANE),
    "typography": (
        TypographyTokens,
        {
            "display_family": _text,
            "display_file": _text,
            "display_weight": _choice(WEIGHTS),
            "display_em_pixels": _number(1, 1000, whole=True),
            "display_cap_height": _number(0.01, 1),
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
    return _checked(WelcomeStyle(**tables), origin)


PACK_OVERRIDES: Mapping[str, frozenset[str]] = {
    "logo": frozenset({"fill_role", "margin_left", "margin_top", "margin_bottom", "padding"}),
    "panes": frozenset({"fill_roles", "fill_opacity_min"}),
}
"""The tokens a branding pack may override in ``[welcome.style]`` (ADR-0016 §7, S5).

The fonts, the frame, and the sizes stay the same in every edition.
"""


def with_overrides(base: WelcomeStyle, overrides: Any, origin: str) -> WelcomeStyle:
    """Return ``base`` with a pack's overrides, each checked as the token file's are.

    Args:
        base: The tokens to start from, normally the shipped ones.
        overrides: The pack's ``[welcome.style]`` table: a ``logo`` table, a ``panes``
            table, or both, holding only the tokens in ``PACK_OVERRIDES``.
        origin: Where the overrides came from, for messages.

    Raises:
        StyleError: A table or token isn't one a pack may override, a value doesn't
            check, or together they'd break the layout or the panes' contrast.
    """
    allowed = ", ".join(
        f"{name}.{key}" for name, keys in PACK_OVERRIDES.items() for key in sorted(keys)
    )
    if not isinstance(overrides, Mapping):
        raise StyleError(f"{origin} must be a table, [welcome.style]")
    changed: dict[str, Any] = {}
    for name, table in overrides.items():
        if name not in PACK_OVERRIDES:
            raise StyleError(f"{origin}: a pack may override only {allowed}, not {name!r}")
        if not isinstance(table, Mapping):
            raise StyleError(f"{origin}: {name} must be a table, [welcome.style.{name}]")
        refused = sorted(set(table) - PACK_OVERRIDES[name])
        if refused:
            raise StyleError(
                f"{origin}: a pack may override only {allowed}, not {name}.{refused[0]}"
            )
        checks = _TABLES[name][1]
        values = {key: checks[key](f"{origin}: {name}.{key}", v) for key, v in table.items()}
        changed[name] = replace(getattr(base, name), **values)
    return _checked(replace(base, **changed), origin)


def _checked(tokens: WelcomeStyle, origin: str) -> WelcomeStyle:
    """Check what no single token can: that the tokens fit together.

    The logo area must hold the logo box's least short side, with room for the logo
    inside its padding. A pane anchored at a corner must clear the card's rounded corner
    and its border. And some pane text must reach each pane's contrast on its opaque
    fill in both themes, so the contrast guarantee can always be met (ADR-0016 §5).
    """
    area, logo = tokens.logo_area, tokens.logo
    if min(area.width, area.height) < logo.min_short_side:
        raise StyleError(
            f"{origin}: the logo's margins leave {area.width:g} × {area.height:g} px, less "
            f"than its box's least short side, {logo.min_short_side:g}"
        )
    if logo.max_long_side < logo.min_short_side:
        raise StyleError(
            f"{origin}: logo.max_long_side {logo.max_long_side:g} is less than "
            f"logo.min_short_side {logo.min_short_side:g}"
        )
    if 2 * logo.padding >= logo.min_short_side:
        raise StyleError(
            f"{origin}: logo.padding {logo.padding:g} leaves no room for the logo in a box "
            f"{logo.min_short_side:g} px across"
        )
    for name in ("name_pane", "version_pane"):
        pane = getattr(tokens, name)
        large = pane.font_size >= LARGE_TEXT_PX
        floor = LARGE_TEXT_CONTRAST if large else NORMAL_TEXT_CONTRAST
        if pane.min_contrast < floor:
            raise StyleError(
                f"{origin}: {name}.min_contrast {pane.min_contrast:g} is below WCAG 2's "
                f"{floor:g}:1 for {'large' if large else 'normal'} text"
            )
    corner = tokens.card.corner_radius + tokens.card.border_width
    for name in ("name_pane", "version_pane"):
        inset = getattr(tokens, name).inset
        if inset < corner:
            raise StyleError(
                f"{origin}: {name}.inset {inset:g} is less than the card's corner radius "
                f"plus its border, {corner:g}"
            )
    panes = tokens.panes
    needed = max(tokens.name_pane.min_contrast, tokens.version_pane.min_contrast)
    for scheme in SCHEMES:
        pairs = pane_pairs(panes, scheme)
        index, _alpha = opaque_fill(pairs)
        best = contrast(rgb_luminance(pairs[index][0]), rgb_luminance(pairs[index][1]))
        if best < needed:
            raise StyleError(
                f"{origin}: no pane text reaches {needed:g}:1 on its own fill, "
                f"panes.fill_roles {list(panes.fill_roles)}, in the {scheme} theme "
                f"({best:.2f}:1)"
            )
    return tokens


def pane_pairs(panes: PaneStyle, scheme: str) -> list[Pair]:
    """Return each pane text colour with its own fill's colour, in ``scheme``."""
    return [
        (rgb(_role_color(text, scheme)), rgb(_role_color(fill, scheme)))
        for text, fill in zip(panes.text_roles, panes.fill_roles, strict=True)
    ]


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


def _role_color(role: str, scheme: str) -> str:
    """Return a palette role's ``#RRGGBB`` colour in ``scheme``."""
    palette = _palette()
    color: str = palette["colors"][palette[scheme][role]]
    return color


# --- contrast (WCAG 2) ----------------------------------------------------------------------

RGB = tuple[int, int, int]
"""A colour's red, green, and blue, each from 0 to 255, as sRGB stores them."""
Pair = tuple[RGB, RGB]
"""A pane's text colour, and its fill's colour."""
_LEVELS = 255
_LINEAR = tuple(
    c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    for c in (level / _LEVELS for level in range(_LEVELS + 1))
)
"""Each 8-bit sRGB level's linear light, for relative luminance (WCAG 2)."""


def rgb(color: str) -> RGB:
    """Return a ``#RRGGBB`` colour's channels."""
    return int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)


def rgb_luminance(color: Sequence[int]) -> float:
    """Return the relative luminance of 8-bit sRGB channels, from 0 (black) to 1."""
    r, g, b = _LINEAR[color[0]], _LINEAR[color[1]], _LINEAR[color[2]]
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def luminance(color: str) -> float:
    """Return the relative luminance of a ``#RRGGBB`` colour, from 0 (black) to 1."""
    return rgb_luminance(rgb(color))


def contrast(first: float, second: float) -> float:
    """Return the contrast ratio of two relative luminances, from 1 to 21."""
    high, low = max(first, second), min(first, second)
    return (high + 0.05) / (low + 0.05)


# --- the panes' contrast guarantee (ADR-0016 §5) -------------------------------------------


def sample_grid(rgbx: bytes, width: int, height: int, minimum: int) -> list[RGB]:
    """Return the pixels on a fixed grid of at least ``minimum`` points, or every pixel.

    Each point takes its nearest pixel, and nothing is averaged, so the art's extremes
    survive the sampling.

    Args:
        rgbx: Pixels as red, green, blue, and one unused byte each, row by row, as Qt's
            RGBX8888 images store them.
        width: The image's width, in pixels.
        height: The image's height, in pixels.
        minimum: The least number of samples.
    """
    if width * height <= minimum:
        xs, ys = list(range(width)), list(range(height))
    else:
        columns = min(width, math.ceil(math.sqrt(minimum * width / height)))
        rows = min(height, math.ceil(minimum / columns))
        xs = [int((i + 0.5) * width / columns) for i in range(columns)]
        ys = [int((j + 0.5) * height / rows) for j in range(rows)]
    stride = 4 * width
    return [
        (rgbx[y * stride + 4 * x], rgbx[y * stride + 4 * x + 1], rgbx[y * stride + 4 * x + 2])
        for y in ys
        for x in xs
    ]


_WEIGHTS = (0.2126, 0.7152, 0.0722)
"""Each channel's share of relative luminance (WCAG 2)."""


def _blend_tables(fill: RGB, alpha: int) -> tuple[list[list[float]], list[list[float]]]:
    """Return, per channel, each art level's weighted linear light under ``fill`` at ``alpha``.

    The screen blends each 8-bit channel and lands on a whole level, so the blend is taken
    rounded down and rounded up: the darker and the lighter result.
    """
    darker, lighter = [], []
    for level, weight in zip(fill, _WEIGHTS, strict=True):
        blends = [level * alpha + art * (_LEVELS - alpha) for art in range(_LEVELS + 1)]
        darker.append([weight * _LINEAR[blend // _LEVELS] for blend in blends])
        lighter.append([weight * _LINEAR[-(-blend // _LEVELS)] for blend in blends])
    return darker, lighter


def short_of(art: Sequence[RGB], text: RGB, fill: RGB, alpha: int, needed: float) -> int:
    """Return how many ``art`` colours leave ``text`` short of ``needed`` contrast.

    Each colour is blended under ``fill`` at ``alpha`` (0 to 255), as the screen blends it,
    and its luminance is compared with the text's. Either rounding of the blend must read.
    """
    luminance = rgb_luminance(text)
    light_enough = needed * (luminance + 0.05) - 0.05
    dark_enough = (luminance + 0.05) / needed - 0.05
    (dr, dg, db), (lr, lg, lb) = _blend_tables(fill, alpha)
    return sum(
        1
        for r, g, b in art
        if not (dr[r] + dg[g] + db[b] >= light_enough or lr[r] + lg[g] + lb[b] <= dark_enough)
    )


def art_contrast(art: Sequence[RGB], text: RGB, fill: RGB, alpha: int, percentile: float) -> float:
    """Return the text's contrast at ``percentile`` of the ``art`` colours, by nearest rank.

    Each colour is blended under ``fill`` at ``alpha``, and the worse rounding counts.
    """
    luminance = rgb_luminance(text)
    (dr, dg, db), (lr, lg, lb) = _blend_tables(fill, alpha)
    values = sorted(
        min(
            contrast(luminance, dr[r] + dg[g] + db[b]),
            contrast(luminance, lr[r] + lg[g] + lb[b]),
        )
        for r, g, b in art
    )
    return values[max(math.ceil(percentile / 100 * len(values)), 1) - 1]


def pane_fill(
    art: Sequence[RGB],
    pairs: Sequence[Pair],
    floor_opacity: float,
    needed: float,
    percentile: float,
) -> tuple[int, int]:
    """Choose a pane's text and fill, and the fill's opacity over the art (ADR-0016 §5, S3).

    Each pair is a text colour and its own fill: dark text on a light fill, light text on
    a dark fill. A pair's fill starts at ``floor_opacity`` and rises only as far as the
    text needs to reach ``needed`` contrast over all but ``percentile`` percent of the art
    beneath, every art colour blended as the screen blends it (ADR-0016, amendments).
    Contrast rises with opacity for a fill on the far side of its text, so the least
    opacity is found by bisection; any opacity returned has been checked. The pair that
    needs the least opacity wins; at the same opacity, the one with more contrast.

    Args:
        art: The art's colours under the pane, sampled.
        pairs: Each text colour, with its fill's colour.
        floor_opacity: The fill's least opacity, from 0 to 1.
        needed: The contrast the text must reach.
        percentile: The share of the art, in percent, that may fall short.

    Returns:
        The index of the pair in ``pairs``, and the fill's alpha, 0 to 255. If no pair
        reaches the contrast even opaque, the fill is opaque, in the pair that contrasts
        most.
    """
    allowed = max(math.ceil(percentile / 100 * len(art)), 1) - 1
    floor = math.ceil(floor_opacity * _LEVELS)
    candidates = []
    for index, (text, fill) in enumerate(pairs):

        def reads(alpha: int, text: RGB = text, fill: RGB = fill) -> bool:
            return short_of(art, text, fill, alpha, needed) <= allowed

        if not reads(_LEVELS):
            continue
        low, high = floor - 1, _LEVELS  # low is too faint (or below the floor); high reads
        if reads(floor):
            high = floor
        else:
            low = floor
            while high - low > 1:
                middle = (low + high) // 2
                low, high = (low, middle) if reads(middle) else (middle, high)
        reached = art_contrast(art, text, fill, high, percentile)
        candidates.append((high, -reached, index))
    if not candidates:
        return opaque_fill(pairs)
    alpha, _contrast, index = min(candidates)
    return index, alpha


def opaque_fill(pairs: Sequence[Pair]) -> tuple[int, int]:
    """Return the pair whose text contrasts most with its fill, and an opaque alpha.

    Returns:
        The index of the pair in ``pairs``, and 255.
    """
    index = max(
        range(len(pairs)),
        key=lambda i: contrast(rgb_luminance(pairs[i][0]), rgb_luminance(pairs[i][1])),
    )
    return index, _LEVELS
