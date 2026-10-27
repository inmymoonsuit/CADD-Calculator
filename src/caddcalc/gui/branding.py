"""Optional branding packs for the desktop app (ADR-0008 item 4, ADR-0011).

The public build is unbranded and uses ``GENERIC``. A *branding pack* is a folder
with a ``branding.toml`` file and the files it names::

    schema = 1                                   # pack format version (optional)
    edition = "example"                          # short slug: build folder names
    icon = "icon.png"                            # optional window icon (.png or .ico)
    about = "about.html"                         # optional About text (.html or .txt)

    [welcome]                                    # optional welcome-screen parts (ADR-0015)
    art = "welcome-art.png"                      # 16:9, supplied at 1920 x 1080
    art_focus = [0.35, 0.5]                      # the point kept in view when cropping
    organization_logo = "logo-vertical.svg"      # the strip's logo, in its box (.svg, .png)
    product_logo = "my-fork.svg"                 # a modified build's own title logo

    [welcome.style.logo]                         # optional overrides (ADR-0016, S5)
    fill_role = "welcome_paper"                  # also margin_left, margin_top,
                                                 #   margin_bottom, padding
    [welcome.style.panes]
    fill_opacity_min = 0.25                      # also fill_roles

Every edition is called ``PRODUCT_NAME``, and is told apart by its icon, art,
organization logo, and About text (ADR-0016, S4). The title shows the project's logo; a
modified build's pack replaces it with ``product_logo`` (TRADEMARKS.md). Official builds
and branded editions don't set it.

Where the app looks for a pack (first match wins):

1. the folder named by the ``CADDCALC_BRANDING`` environment variable, to try a pack
   from a source checkout;
2. a ``branding`` folder next to the executable of a packaged app, where
   ``packaging/build.py`` puts it.

This module does not import Qt, so the build script and the tests can use it without a
display. Branding packs, and the marks and art in them, never go in this repository
(ADR-0008 item 4, ADR-0011).
"""

from __future__ import annotations

import os
import re
import sys
import tomllib
import warnings
import xml.etree.ElementTree as ElementTree
from collections.abc import Mapping
from dataclasses import dataclass
from html import escape
from pathlib import Path
from typing import Any

from caddcalc.core.errors import CaddCalcError
from caddcalc.gui.welcome_style import StyleError, WelcomeStyle, style, with_overrides

PRODUCT_NAME = "CADD Calculator"
"""The name every edition shows: window title, welcome screen, and About (ADR-0016, S4)."""
ENV_VAR = "CADDCALC_BRANDING"
PACK_FILE = "branding.toml"
PACK_DIR_NAME = "branding"
"""Name of the pack folder next to a packaged app's executable."""
SCHEMA = 1

ASSETS = Path(__file__).parent / "assets"
BRAND = ASSETS / "brand"
"""The brand artwork's sources (docs/dev/design/brand.md)."""
GENERIC_ICON = BRAND / "app-icon.svg"
"""The app icon's master; ``app_icon`` draws every size from it and its small drawings."""
GENERIC_ART = ASSETS / "welcome" / "welcome-art.jpg"
"""The official build's welcome art, © the maintainer, for this project only
(ART-LICENSE.md). It's art, not a mark, so it isn't in ``BRAND``."""
TITLE_LOGO = BRAND / "logo-outlined.svg"
"""The welcome screen's title: the symbol and the wordmark, for a light fill (ADR-0015)."""
TITLE_LOGO_REVERSED = BRAND / "logo-outlined-reversed.svg"
"""The same, with the C and "Calculator" in white, for a dark fill."""

ICON_SUFFIXES = frozenset({".png", ".ico"})
ABOUT_SUFFIXES = frozenset({".html", ".htm", ".txt"})
_KEYS = frozenset({"schema", "edition", "icon", "about", "welcome"})
_WELCOME_KEYS = frozenset({"art", "art_focus", "organization_logo", "product_logo", "style"})
_EDITION_RE = re.compile(r"[a-z0-9][a-z0-9-]{0,31}")


class BrandingError(CaddCalcError):
    """A branding pack is missing, malformed, or names files it doesn't contain."""


@dataclass(frozen=True)
class Branding:
    """What sets an edition apart. The defaults are the unbranded public build.

    The name isn't part of it: every edition is ``PRODUCT_NAME``.
    """

    edition: str = "generic"
    icon: Path | None = GENERIC_ICON
    welcome_art: Path | None = None
    """The welcome screen's art; ``None`` means the built-in art, ``GENERIC_ART``."""
    welcome_focus: tuple[float, float] = (0.5, 0.5)
    """The point of the art kept in view when it is cropped, as fractions of its size."""
    organization_logo: Path | None = None
    """The welcome screen's strip logo, an organization's; ``None`` leaves no strip."""
    product_logo: Path | None = None
    """A modified build's own title logo; ``None`` means the project's (TRADEMARKS.md)."""
    welcome_style: WelcomeStyle | None = None
    """The welcome screen's tokens with the pack's overrides; ``None`` for the shipped ones."""
    about_html: str | None = None
    """Rich-text fragment for Help > About. ``None`` means the generic description."""
    source: Path | None = None
    """The pack folder this came from, or ``None`` for the built-in generic branding."""
    files: tuple[Path, ...] = ()
    """Every file the pack uses, ``branding.toml`` included: what a build must bundle."""

    @property
    def welcome_tokens(self) -> WelcomeStyle:
        """The welcome screen's design tokens for this edition (ADR-0016)."""
        return style() if self.welcome_style is None else self.welcome_style

    @property
    def is_generic(self) -> bool:
        """Whether this is the built-in, unbranded identity."""
        return self.source is None


GENERIC = Branding()


def load_branding(pack_dir: Path | str) -> Branding:
    """Read and check the branding pack in ``pack_dir``.

    Raises:
        BrandingError: The pack is missing, malformed, or names files it doesn't contain.
    """
    root = Path(pack_dir)
    toml_path = root / PACK_FILE
    if not toml_path.is_file():
        raise BrandingError(f"{root} is not a branding pack: it has no {PACK_FILE}")
    try:
        data = tomllib.loads(toml_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
        raise BrandingError(f"{toml_path}: {exc}") from exc

    if "splash" in data:
        raise BrandingError(
            f"{toml_path}: 'splash' was replaced by the [welcome] table (art, art_focus, "
            "organization_logo); see ADR-0015"
        )
    if "name" in data:
        raise BrandingError(
            f"{toml_path}: 'name' was removed: every edition is called {PRODUCT_NAME!r}, "
            "told apart by its icon, art, logo, and About text; delete the key "
            "(ADR-0016, S4)"
        )
    unknown = sorted(set(data) - _KEYS)
    if unknown:
        raise BrandingError(
            f"{toml_path}: unknown key(s) {', '.join(unknown)}; "
            f"expected some of {', '.join(sorted(_KEYS))}"
        )
    schema = data.get("schema", SCHEMA)
    if schema != SCHEMA:
        raise BrandingError(f"{toml_path}: schema {schema!r} is not supported (expected {SCHEMA})")

    edition = _required_text(data, "edition", toml_path)
    if not _EDITION_RE.fullmatch(edition) or edition == GENERIC.edition:
        raise BrandingError(
            f"{toml_path}: edition {edition!r} must be 1 to 32 lowercase letters, digits, "
            f"or hyphens, and not {GENERIC.edition!r}"
        )

    icon = _pack_file(data, "icon", root, ICON_SUFFIXES)
    about = _pack_file(data, "about", root, ABOUT_SUFFIXES)
    about_html = _read_about(about) if about is not None else None
    art, focus, organization, product, tokens = _welcome(data.get("welcome", {}), root)
    return Branding(
        edition=edition,
        icon=icon if icon is not None else GENERIC_ICON,
        welcome_art=art,
        welcome_focus=focus,
        organization_logo=organization,
        product_logo=product,
        welcome_style=tokens,
        about_html=about_html,
        source=root,
        files=(
            toml_path,
            *(f for f in (icon, about, art, organization, product) if f is not None),
        ),
    )


def packaged_app_dir() -> Path | None:
    """The folder holding a packaged app's executable, or ``None`` when run from Python."""
    # Nuitka defines __compiled__ in compiled modules; PyInstaller and others set sys.frozen.
    if "__compiled__" in globals() or getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return None


def find_pack_dir(
    environ: Mapping[str, str] | None = None, app_dir: Path | None = None
) -> Path | None:
    """Locate the pack to use (see the module docstring), or ``None`` for the generic build.

    ``app_dir`` defaults to ``packaged_app_dir()``.
    """
    env = os.environ if environ is None else environ
    if value := env.get(ENV_VAR, "").strip():
        return Path(value)
    folder = app_dir if app_dir is not None else packaged_app_dir()
    if folder is not None and (folder / PACK_DIR_NAME / PACK_FILE).is_file():
        return folder / PACK_DIR_NAME
    return None


def active_branding(
    environ: Mapping[str, str] | None = None, app_dir: Path | None = None
) -> Branding:
    """The branding the app should show. A broken pack warns and falls back to generic."""
    pack = find_pack_dir(environ, app_dir)
    if pack is None:
        return GENERIC
    try:
        return load_branding(pack)
    except BrandingError as exc:
        # warnings, not print: a windowed app may have no stderr at all.
        warnings.warn(f"Ignoring branding pack: {exc}", stacklevel=2)
        return GENERIC


def _required_text(data: Mapping[str, Any], key: str, toml_path: Path) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise BrandingError(f"{toml_path}: {key!r} must be a non-empty string")
    return value.strip()


def _welcome(
    table: Any, root: Path
) -> tuple[Path | None, tuple[float, float], Path | None, Path | None, WelcomeStyle | None]:
    """Read the ``[welcome]`` table: the art, its focal point, the logos, and the style.

    Only the suffix, the path, and the size in bytes are checked here, without Qt. The
    welcome screen checks the art's pixel size before decoding it (ADR-0015, amendments).
    The style's overrides are checked by ``welcome_style.with_overrides`` (ADR-0016, S5).
    """
    toml_path = root / PACK_FILE
    if not isinstance(table, Mapping):
        raise BrandingError(f"{toml_path}: 'welcome' must be a table, [welcome]")
    if "logo" in table:
        raise BrandingError(
            f"{toml_path}: welcome.logo was renamed welcome.organization_logo: the strip "
            "now holds an organization's logo, and the title the project's (ADR-0015, "
            "amendments)"
        )
    unknown = sorted(set(table) - _WELCOME_KEYS)
    if unknown:
        raise BrandingError(
            f"{toml_path}: unknown [welcome] key(s) {', '.join(unknown)}; "
            f"expected some of {', '.join(sorted(_WELCOME_KEYS))}"
        )
    tokens = style()
    art = _pack_file(table, "art", root, frozenset(tokens.art.formats), label="welcome.art")
    logos = frozenset(tokens.logo.formats)
    organization, product = (
        _pack_file(table, key, root, logos, label=f"welcome.{key}")
        for key in ("organization_logo", "product_logo")
    )
    budget = tokens.art.max_bytes
    for path, label in (
        (art, "welcome.art"),
        (organization, "welcome.organization_logo"),
        (product, "welcome.product_logo"),
    ):
        if path is not None and path.stat().st_size > budget:
            raise BrandingError(
                f"{toml_path}: {label} {path.name!r} is larger than {budget // 1_000_000} MB"
            )
        if path is not None and path is not art and path.suffix.lower() == ".svg":
            _check_self_contained(path, toml_path, label)
    focus = table.get("art_focus", [0.5, 0.5])
    if (
        not isinstance(focus, list)
        or len(focus) != 2
        or not all(isinstance(v, int | float) and not isinstance(v, bool) for v in focus)
        or not all(0 <= v <= 1 for v in focus)
    ):
        raise BrandingError(
            f"{toml_path}: welcome.art_focus must be two numbers from 0 to 1, e.g. [0.35, 0.5]"
        )
    overridden: WelcomeStyle | None = None
    if "style" in table:
        try:
            overridden = with_overrides(tokens, table["style"], f"{toml_path}: welcome.style")
        except StyleError as exc:
            raise BrandingError(str(exc)) from exc
    return art, (float(focus[0]), float(focus[1])), organization, product, overridden


_XLINK_HREF = "{http://www.w3.org/1999/xlink}href"


def _check_self_contained(svg: Path, toml_path: Path, label: str) -> None:
    """Refuse an SVG that refers to other files: they would escape the pack folder.

    An ``<image>`` or ``<use>`` may embed its data (``data:``) or point within the file
    (``#…``), nothing else (ADR-0015, amendments). The byte budget is checked first, and
    Python's expat limits entity expansion.
    """
    try:
        root = ElementTree.parse(svg).getroot()  # noqa: S314  # see the docstring
    except ElementTree.ParseError as exc:
        raise BrandingError(f"{toml_path}: {label} {svg.name!r} isn't valid SVG: {exc}") from exc
    for element in root.iter():
        if element.tag.rsplit("}", 1)[-1] not in ("image", "use"):
            continue
        for key in (_XLINK_HREF, "href"):
            href = (element.get(key) or "").strip()
            if href and not href.startswith(("data:", "#")):
                raise BrandingError(
                    f"{toml_path}: {label} {svg.name!r} refers to {href!r}; a logo must be "
                    "self-contained (embed images as data: URIs)"
                )


def _pack_file(
    data: Mapping[str, Any],
    key: str,
    root: Path,
    suffixes: frozenset[str],
    *,
    label: str | None = None,
) -> Path | None:
    value = data.get(key)
    if value is None:
        return None
    toml_path = root / PACK_FILE
    label = label or key
    if not isinstance(value, str) or not value.strip():
        raise BrandingError(f"{toml_path}: {label!r} must be a file name")
    path = root / value
    # The build copies only the pack folder, so a file outside it would go missing.
    if not path.resolve().is_relative_to(root.resolve()):
        raise BrandingError(f"{toml_path}: {label} {value!r} must be inside the pack folder")
    if path.suffix.lower() not in suffixes:
        raise BrandingError(
            f"{toml_path}: {label} {value!r} must be one of {', '.join(sorted(suffixes))}"
        )
    if path.exists() and not path.is_file():
        raise BrandingError(f"{toml_path}: {label} {value!r} is not a file")
    if not path.is_file():
        raise BrandingError(f"{toml_path}: {label} file {value!r} does not exist")
    return path


def _read_about(path: Path) -> str:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise BrandingError(f"{path}: {exc}") from exc
    if path.suffix.lower() in {".html", ".htm"}:
        return text.strip()
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    return "".join(f"<p>{escape(p)}</p>" for p in paragraphs)
