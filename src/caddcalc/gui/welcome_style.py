"""The welcome screen's design tokens, from ``assets/welcome_style.toml`` (ADR-0016).

Every size, colour role, and font the welcome screen uses is a token in that file, and
this module reads, types, range-checks, and documents each one, refusing unknown keys.
The screen reads tokens only, never literals, so restyling it means editing one checked
file. Sizes are logical pixels. Colours are palette roles (``palette.toml``), checked
to exist in both themes. The reading and the checks are the core every token file
shares, in ``style_tokens``; this module re-exports what it uses from there.

Standard library only: the branding loader and the build script use the art budget
without importing Qt.
"""

from __future__ import annotations

import math
import tomllib
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, replace
from functools import cache
from pathlib import Path
from typing import Any

from caddcalc.gui.style_tokens import (
    ASSETS,
    LEVELS,
    LINEAR,
    PALETTE_FILE,
    RGB,
    SCHEMES,
    SPACING,
    Check,
    Rect,
    Size,
    StyleError,
    check_choice,
    check_formats,
    check_number,
    check_role,
    check_roles,
    check_size,
    check_spacing,
    check_spacing_pair,
    check_text,
    check_texts,
    contrast,
    luminance,
    palette_color,
    parse_tables,
    rgb,
    rgb_luminance,
)

__all__ = [
    "ANCHORS",
    "ASSETS",
    "FONTS",
    "LARGE_TEXT_CONTRAST",
    "LARGE_TEXT_PX",
    "NORMAL_TEXT_CONTRAST",
    "PACK_OVERRIDES",
    "PALETTE_FILE",
    "RGB",
    "SCHEMA",
    "SCHEMES",
    "SPACING",
    "STYLE_FILE",
    "WEIGHTS",
    "ArtTokens",
    "CardTokens",
    "LogoTokens",
    "Pair",
    "PaneStyle",
    "PaneTokens",
    "Rect",
    "Size",
    "StyleError",
    "TopBarTokens",
    "TypographyTokens",
    "WelcomeStyle",
    "art_contrast",
    "background_spread",
    "contrast",
    "every_pixel",
    "load_style",
    "luminance",
    "opaque_fill",
    "pane_fill",
    "pane_pairs",
    "pane_reads",
    "parse_style",
    "rgb",
    "rgb_luminance",
    "short_of",
    "style",
    "with_overrides",
]

STYLE_FILE = ASSETS / "welcome_style.toml"
SCHEMA = 1
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
    max_background_spread: float
    """The most the background under a pane may vary: its luminance at the high
    percentile over its luminance at the low one, each plus 0.05, so busy art can't
    break the letters up even where their contrast holds."""


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
class StartupTokens:
    """How the card and the main window come up together (ADR-0015, amendments)."""

    hold_ms: int
    """How long the card is on screen alone, from its first paint, before the main window
    is revealed behind it; or less, if the card is closed first."""


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
    startup: StartupTokens

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

_WIDTH = check_number(0, 8)
_LENGTH = check_number(0, 1024)
_PANE: dict[str, Check] = {
    "anchor": check_choice(ANCHORS),
    "inset": check_spacing,
    "padding": check_spacing_pair,
    "font": check_choice(FONTS),
    "font_size": check_number(1, 256),
    "min_contrast": check_number(1, 21),
    "safe_area": check_size(0, 4096),
}
_TABLES: dict[str, tuple[type, dict[str, Check]]] = {
    "art": (
        ArtTokens,
        {
            "slot": check_size(1, 4096),
            "supplied_scale": check_number(1, 4, whole=True),
            "formats": check_formats,
            "max_bytes": check_number(1, 100_000_000, whole=True),
            "max_px": check_number(1, 16384, whole=True),
            "grid": check_number(1, 1024, whole=True),
        },
    ),
    "card": (
        CardTokens,
        {"corner_radius": check_number(0, 32), "border_width": _WIDTH, "border_role": check_role},
    ),
    "top_bar": (
        TopBarTokens,
        {
            "height": check_number(1, 256),
            "padding": check_spacing,
            "button_size": check_number(1, 256),
            "separator_width": _WIDTH,
            "separator_role": check_role,
        },
    ),
    "logo": (
        LogoTokens,
        {
            "formats": check_formats,
            "region_width": check_number(1, 1024),
            "margin_left": check_spacing,
            "margin_top": check_spacing,
            "margin_bottom": check_spacing,
            "padding": check_spacing,
            "min_short_side": check_number(1, 1024),
            "max_long_side": check_number(1, 4096),
            "border_width": _WIDTH,
            "border_role": check_role,
            "fill_role": check_role,
        },
    ),
    "panes": (
        PaneStyle,
        {
            "text_roles": check_roles,
            "fill_roles": check_roles,
            "fill_opacity_min": check_number(0, 1),
            "border_width": _WIDTH,
            "percentile": check_number(0, 50),
            "max_background_spread": check_number(1, 21),
        },
    ),
    "name_pane": (PaneTokens, _PANE),
    "version_pane": (PaneTokens, _PANE),
    "typography": (
        TypographyTokens,
        {
            "display_family": check_text,
            "display_file": check_text,
            "display_weight": check_choice(WEIGHTS),
            "display_em_pixels": check_number(1, 1000, whole=True),
            "display_cap_height": check_number(0.01, 1),
            "fallback_families": check_texts,
            "min_font_size": check_number(1, 64),
        },
    ),
    "startup": (StartupTokens, {"hold_ms": check_number(0, 10_000, whole=True)}),
}


def parse_style(data: Mapping[str, Any], origin: str = STYLE_FILE.name) -> WelcomeStyle:
    """Check parsed tokens and return them typed.

    Raises:
        StyleError: A table or token is unknown or missing, has the wrong type, or is out
            of range; or a role isn't in the palette.
    """
    return _checked(WelcomeStyle(**parse_tables(data, _TABLES, SCHEMA, origin)), origin)


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
        (rgb(palette_color(text, scheme)), rgb(palette_color(fill, scheme)))
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


Pair = tuple[RGB, RGB]
"""A pane's text colour, and its fill's colour."""


# --- the panes' contrast guarantee (ADR-0016 §5) -------------------------------------------


def every_pixel(rgbx: bytes, width: int, height: int) -> list[RGB]:
    """Return every pixel's colour, row by row: nothing sampled, nothing averaged.

    A regular grid of samples aliases with periodic art: over 1 px stripes it can see
    almost any share of them, and so take the percentile over the wrong pixels
    (ADR-0016, amendments). A pane is small, so every pixel under it is measured.

    Args:
        rgbx: Pixels as red, green, blue, and one unused byte each, row by row, as Qt's
            RGBX8888 images store them.
        width: The image's width, in pixels.
        height: The image's height, in pixels.
    """
    view = memoryview(rgbx)[: 4 * width * height]
    return list(zip(view[0::4], view[1::4], view[2::4], strict=True))


_WEIGHTS = (0.2126, 0.7152, 0.0722)
"""Each channel's share of relative luminance (WCAG 2)."""


def _blend_tables(fill: RGB, alpha: int) -> tuple[list[list[float]], list[list[float]]]:
    """Return, per channel, each art level's weighted linear light under ``fill`` at ``alpha``.

    The screen blends each 8-bit channel and lands on a whole level, so the blend is taken
    rounded down and rounded up: the darker and the lighter result.
    """
    darker, lighter = [], []
    for level, weight in zip(fill, _WEIGHTS, strict=True):
        blends = [level * alpha + art * (LEVELS - alpha) for art in range(LEVELS + 1)]
        darker.append([weight * LINEAR[blend // LEVELS] for blend in blends])
        lighter.append([weight * LINEAR[-(-blend // LEVELS)] for blend in blends])
    return darker, lighter


Art = Sequence[RGB] | Counter[RGB]
"""The art under a pane: every pixel's colour, or each distinct colour with its count."""


def tally(art: Art) -> Counter[RGB]:
    """Return each distinct colour in ``art`` with how many pixels have it.

    Every measure below depends only on how many pixels have each colour, so it's exact
    on the tally, and each colour is blended once however many pixels share it.
    """
    return art if isinstance(art, Counter) else Counter(art)


_SAMPLE = 512
"""How many colours a tail's edge is estimated from, before the tail is sorted."""


def _at_rank(values: list[float], counts: list[int], share: float) -> float:
    """Return the value at ``share`` percent of the pixels, by nearest rank.

    ``values`` is each colour's value and ``counts`` its pixels. Only the tail nearer
    the rank is sorted. A sample of the colours puts the tail's edge past the rank, at
    twice its share, well beyond the sample's error, and if the tail holds too few
    pixels after all, everything is sorted instead. So a tail of a few percent costs a
    pass over the values, not a sort of them, and the result is exact either way.
    """
    total = sum(counts)
    rank = max(math.ceil(share / 100 * total), 1) - 1  # the pixels below the value
    top = rank >= total - rank  # nearer the top, so counted down from there
    beyond = total - 1 - rank if top else rank  # the pixels past it, from that end
    pairs: Iterable[tuple[float, int]] = zip(values, counts, strict=True)
    if len(values) > 2 * _SAMPLE:
        step = len(values) // _SAMPLE
        sample = sorted(zip(values[::step], counts[::step], strict=True), reverse=top)
        wanted = 2 * (beyond + 1) / total * sum(counts[::step])
        seen, edge = 0, sample[-1][0]
        for value, count in sample:
            seen += count
            if seen >= wanted:
                edge = value
                break
        if top:
            tail = [(value, count) for value, count in pairs if value >= edge]
        else:
            tail = [(value, count) for value, count in pairs if value <= edge]
        if sum(count for _, count in tail) > beyond:
            pairs = tail
        else:  # the sample put the edge short of the rank
            pairs = zip(values, counts, strict=True)
    seen = 0
    for value, count in sorted(pairs, reverse=top):
        seen += count
        if seen > beyond:
            return value
    raise ValueError("no art under the pane")


def _blended(counted: Counter[RGB], fill: RGB, alpha: int) -> tuple[list[float], list[float]]:
    """Return each colour's luminance under ``fill`` at ``alpha``: rounded darker, lighter.

    Each colour is blended as the screen blends it, each 8-bit channel to a whole level,
    in the order ``counted`` lists them.
    """
    (dr, dg, db), (lr, lg, lb) = _blend_tables(fill, alpha)
    return (
        [dr[r] + dg[g] + db[b] for r, g, b in counted],
        [lr[r] + lg[g] + lb[b] for r, g, b in counted],
    )


def _short(
    darker: list[float], lighter: list[float], counts: list[int], text: RGB, needed: float
) -> int:
    """Return how many pixels leave ``text`` short of ``needed``, at either rounding."""
    luminance = rgb_luminance(text)
    light_enough = needed * (luminance + 0.05) - 0.05
    dark_enough = (luminance + 0.05) / needed - 0.05
    return sum(
        count
        for dark, light, count in zip(darker, lighter, counts, strict=True)
        if not (dark >= light_enough or light <= dark_enough)
    )


def _spread(
    darker: list[float], lighter: list[float], counts: list[int], percentile: float
) -> float:
    """Return the background's spread: see ``background_spread``."""
    return contrast(
        _at_rank(lighter, counts, 100 - percentile), _at_rank(darker, counts, percentile)
    )


def short_of(art: Art, text: RGB, fill: RGB, alpha: int, needed: float) -> int:
    """Return how many pixels of ``art`` leave ``text`` short of ``needed`` contrast.

    Each colour is blended under ``fill`` at ``alpha`` (0 to 255), as the screen blends it,
    and its luminance is compared with the text's. Either rounding of the blend must read.
    """
    counted = tally(art)
    return _short(*_blended(counted, fill, alpha), list(counted.values()), text, needed)


def art_contrast(art: Art, text: RGB, fill: RGB, alpha: int, percentile: float) -> float:
    """Return the text's contrast at ``percentile`` of the ``art``'s pixels, by nearest rank.

    Each colour is blended under ``fill`` at ``alpha``, and the worse rounding counts.
    """
    counted = tally(art)
    luminance = rgb_luminance(text)
    darker, lighter = _blended(counted, fill, alpha)
    values = [
        min(contrast(luminance, dark), contrast(luminance, light))
        for dark, light in zip(darker, lighter, strict=True)
    ]
    return _at_rank(values, list(counted.values()), percentile)


def background_spread(art: Art, fill: RGB, alpha: int, percentile: float) -> float:
    """Return how much the background under a pane varies, blended under ``fill``.

    It's the ratio of the blended art's luminance at ``100 - percentile`` percent, taken
    at its lighter rounding, to that at ``percentile`` percent, at its darker rounding,
    each plus 0.05, as a contrast is. 1 is a flat background.
    """
    counted = tally(art)
    return _spread(*_blended(counted, fill, alpha), list(counted.values()), percentile)


def pane_reads(art: Art, text: RGB, fill: RGB, alpha: int, panes: PaneStyle, needed: float) -> bool:
    """Return whether ``text`` reads on ``fill`` at ``alpha`` over the ``art`` beneath.

    It does when its contrast reaches ``needed`` over all but ``panes.percentile`` percent
    of the art, every colour blended as the screen blends it, and when the blended
    background is calm: its spread is at most ``panes.max_background_spread``, so busy
    art can't break the letters up (ADR-0016, amendments).
    """
    counted = tally(art)
    counts = list(counted.values())
    darker, lighter = _blended(counted, fill, alpha)  # once, for both tests
    allowed = max(math.ceil(panes.percentile / 100 * sum(counts)), 1) - 1
    return (
        _short(darker, lighter, counts, text, needed) <= allowed
        and _spread(darker, lighter, counts, panes.percentile) <= panes.max_background_spread
    )


def pane_fill(art: Art, pairs: Sequence[Pair], panes: PaneStyle, needed: float) -> tuple[int, int]:
    """Choose a pane's text and fill, and the fill's opacity over the art (ADR-0016 §5, S3).

    Each pair is a text colour and its own fill: dark text on a light fill, light text on
    a dark fill. A pair's fill starts at ``panes.fill_opacity_min`` and rises only as far
    as its text needs to read over the art beneath (``pane_reads``). Both the contrast
    and the calm are nearly monotone in opacity: the contrast for a fill on the far side
    of its text, and the calm because blending toward one colour narrows the spread, up
    to 8-bit rounding. So the least opacity is found by bisection, and bisection returns
    only an opacity it has checked; where the rise isn't strict, that may be a little
    above the least. The pair that needs the least opacity wins; at the same opacity,
    the one with more contrast, and then the first.

    Args:
        art: The art's colours under the pane, every pixel.
        pairs: Each text colour, with its fill's colour.
        panes: The panes' style: the floor, the percentile, and the most spread.
        needed: The contrast the text must reach.

    Returns:
        The index of the pair in ``pairs``, and the fill's alpha, 0 to 255. If no pair
        reads even opaque, the fill is opaque, in the pair that contrasts most.
    """
    counted = tally(art)  # once: the search below checks the art at every opacity it tries
    floor = math.ceil(panes.fill_opacity_min * LEVELS)
    candidates = []
    for index, (text, fill) in enumerate(pairs):

        def reads(alpha: int, text: RGB = text, fill: RGB = fill) -> bool:
            return pane_reads(counted, text, fill, alpha, panes, needed)

        if not reads(LEVELS):
            continue
        low, high = floor - 1, LEVELS  # low doesn't read (or is below the floor); high reads
        if reads(floor):
            high = floor
        else:
            low = floor
            while high - low > 1:
                middle = (low + high) // 2
                low, high = (low, middle) if reads(middle) else (middle, high)
        candidates.append((high, index))
    if not candidates:
        return opaque_fill(pairs)
    alpha = min(high for high, _index in candidates)
    tied = [index for high, index in candidates if high == alpha]

    def reached(index: int) -> float:
        text, fill = pairs[index]
        return art_contrast(counted, text, fill, alpha, panes.percentile)

    index = tied[0] if len(tied) == 1 else max(tied, key=reached)  # max keeps the first
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
    return index, LEVELS
