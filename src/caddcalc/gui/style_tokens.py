"""The core every design-token file shares: reading, checking, and the palette (ADR-0016).

A token file is TOML with a ``schema`` and one table per part. Each table is typed by a
dataclass, and each token by a check here that types it, range-checks it, and refuses a
wrong value with a message naming it; a table with an unknown or a missing key is
refused. Colours are palette roles, checked to exist in both themes, and every inset,
margin, and padding comes from one spacing scale. ``welcome_style`` is built on it.

Standard library only: the branding loader and the build script read tokens without
importing Qt.
"""

from __future__ import annotations

import tomllib
from collections.abc import Callable, Mapping, Sequence
from dataclasses import fields
from functools import cache
from pathlib import Path
from typing import Any, NamedTuple

from caddcalc.core.errors import CaddCalcError

ASSETS = Path(__file__).parent / "assets"
PALETTE_FILE = ASSETS / "palette.toml"


class StyleError(CaddCalcError):
    """A token file is malformed: an unknown key, a wrong type, or a value out of range."""


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


# --- checking ---------------------------------------------------------------------------

Check = Callable[[str, Any], Any]
"""A token's check: given where the token is and its value, the typed value, or a
``StyleError``."""


def check_number(low: float, high: float, *, whole: bool = False) -> Check:
    """Return a check for a number from ``low`` to ``high``, whole if ``whole``."""

    def check(where: str, value: Any) -> float:
        kind = int if whole else int | float
        if not isinstance(value, kind) or isinstance(value, bool) or not low <= value <= high:
            noun = "a whole number" if whole else "a number"
            raise StyleError(f"{where} must be {noun} from {low:g} to {high:g}, not {value!r}")
        return value

    return check


def check_pair(low: float, high: float) -> Check:
    """Return a check for two numbers, each from ``low`` to ``high``."""
    item = check_number(low, high)

    def check(where: str, value: Any) -> tuple[float, float]:
        if not isinstance(value, list) or len(value) != 2:
            raise StyleError(f"{where} must be two numbers, e.g. [10, 16]")
        return item(where, value[0]), item(where, value[1])

    return check


def check_size(low: float, high: float) -> Check:
    """Return a check for a width and a height, each from ``low`` to ``high``."""
    pair = check_pair(low, high)
    return lambda where, value: Size(*pair(where, value))


def check_choice(allowed: frozenset[str]) -> Check:
    """Return a check for one of ``allowed``."""

    def check(where: str, value: Any) -> str:
        if value not in allowed:
            raise StyleError(f"{where} must be one of {', '.join(sorted(allowed))}, not {value!r}")
        return str(value)

    return check


def check_bool(where: str, value: Any) -> bool:
    """Check ``true`` or ``false``."""
    if not isinstance(value, bool):
        raise StyleError(f"{where} must be true or false, not {value!r}")
    return value


def check_text(where: str, value: Any) -> str:
    """Check non-empty text."""
    if not isinstance(value, str) or not value.strip():
        raise StyleError(f"{where} must be non-empty text")
    return value


def check_texts(where: str, value: Any) -> tuple[str, ...]:
    """Check a non-empty list of non-empty text."""
    if not isinstance(value, list) or not value:
        raise StyleError(f"{where} must be a non-empty list of text")
    return tuple(check_text(where, item) for item in value)


def check_formats(where: str, value: Any) -> tuple[str, ...]:
    """Check a list of lowercase file suffixes, such as ``".png"``."""
    formats = check_texts(where, value)
    if not all(f.startswith(".") and f == f.lower() for f in formats):
        raise StyleError(f'{where} must be lowercase file suffixes, e.g. ".png"')
    return formats


def check_role(where: str, value: Any) -> str:
    """Check a palette role that both themes define."""
    role = check_text(where, value)
    palette = load_palette()
    if not all(role in palette[scheme] for scheme in SCHEMES):
        raise StyleError(f"{where}: {role!r} isn't a palette role in both themes")
    return role


def check_roles(where: str, value: Any) -> tuple[str, str]:
    """Check two palette roles."""
    if not isinstance(value, list) or len(value) != 2:
        raise StyleError(f"{where} must be two palette roles")
    return check_role(where, value[0]), check_role(where, value[1])


def check_spacing(where: str, value: Any) -> float:
    """Check a step of the spacing scale."""
    if isinstance(value, bool) or value not in SPACING:
        scale = ", ".join(str(step) for step in SPACING)
        raise StyleError(f"{where} must be on the spacing scale, {scale}; not {value!r}")
    return float(value)


def check_spacing_pair(where: str, value: Any) -> tuple[float, float]:
    """Check two steps of the spacing scale, such as a vertical and a horizontal padding."""
    if not isinstance(value, list) or len(value) != 2:
        raise StyleError(f"{where} must be two numbers, e.g. [8, 16]")
    return check_spacing(where, value[0]), check_spacing(where, value[1])


def parse_tables(
    data: Mapping[str, Any],
    tables: Mapping[str, tuple[type, Mapping[str, Check]]],
    schema: int,
    origin: str,
) -> dict[str, Any]:
    """Check a token file's parsed tables, and return each typed by its class.

    Args:
        data: The parsed TOML.
        tables: Each table's name, its class, and each token's check, in order.
        schema: The ``schema`` the file must give.
        origin: Where the tokens came from, for messages.

    Raises:
        StyleError: A table or token is unknown or missing, has the wrong type, or is out
            of range; or a role isn't in the palette.
    """
    unknown = sorted(set(data) - set(tables) - {"schema"})
    if unknown:
        raise StyleError(f"{origin}: unknown table(s) {', '.join(unknown)}")
    if data.get("schema") != schema:
        raise StyleError(f"{origin}: schema must be {schema}, not {data.get('schema')!r}")
    typed: dict[str, Any] = {}
    for name, (kind, checks) in tables.items():
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
        typed[name] = kind(**{f.name: values[f.name] for f in fields(kind)})
    return typed


# --- the palette ------------------------------------------------------------------------


@cache
def load_palette() -> dict[str, Any]:
    """Return the parsed ``palette.toml``, read once."""
    data: dict[str, Any] = tomllib.loads(PALETTE_FILE.read_text(encoding="utf-8"))
    return data


def palette_color(role: str, scheme: str) -> str:
    """Return a palette role's ``#RRGGBB`` colour in ``scheme``."""
    palette = load_palette()
    color: str = palette["colors"][palette[scheme][role]]
    return color


# --- contrast (WCAG 2) ----------------------------------------------------------------------

RGB = tuple[int, int, int]
"""A colour's red, green, and blue, each from 0 to 255, as sRGB stores them."""
LEVELS = 255
"""The highest level of an 8-bit channel."""
LINEAR = tuple(
    c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    for c in (level / LEVELS for level in range(LEVELS + 1))
)
"""Each 8-bit sRGB level's linear light, for relative luminance (WCAG 2)."""


def rgb(color: str) -> RGB:
    """Return a ``#RRGGBB`` colour's channels."""
    return int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)


def rgb_luminance(color: Sequence[int]) -> float:
    """Return the relative luminance of 8-bit sRGB channels, from 0 (black) to 1."""
    r, g, b = LINEAR[color[0]], LINEAR[color[1]], LINEAR[color[2]]
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def luminance(color: str) -> float:
    """Return the relative luminance of a ``#RRGGBB`` colour, from 0 (black) to 1."""
    return rgb_luminance(rgb(color))


def contrast(first: float, second: float) -> float:
    """Return the contrast ratio of two relative luminances, from 1 to 21."""
    high, low = max(first, second), min(first, second)
    return (high + 0.05) / (low + 0.05)


def blend(top: str, bottom: str, opacity: float) -> str:
    """Return ``top`` at ``opacity`` over ``bottom``, as ``#RRGGBB``, as Qt paints it."""
    channels = (
        round(t * opacity + b * (1 - opacity)) for t, b in zip(rgb(top), rgb(bottom), strict=True)
    )
    return "#" + "".join(f"{c:02X}" for c in channels)
