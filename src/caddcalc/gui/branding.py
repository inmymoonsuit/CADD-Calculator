"""Optional branding packs for the desktop app (ADR-0008 item 4, ADR-0011).

The public build is unbranded and uses ``GENERIC``. A *branding pack* is a folder
with a ``branding.toml`` file and the files it names::

    schema = 1                                   # pack format version (optional)
    edition = "example"                          # short slug: build folder names
    name = "CADD Calculator: Example Edition"    # window title, About heading
    icon = "icon.png"                            # optional window icon (.png or .ico)
    about = "about.html"                         # optional About text (.html or .txt)

    [welcome]                                    # optional welcome-screen parts (ADR-0015)
    art = "welcome-art.png"                      # 16:9, supplied at 1920 x 1080
    art_focus = [0.35, 0.5]                      # the point kept in view when cropping
    logo = "logo-vertical.svg"                   # the vertical logo strip (.svg or .png)

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
from caddcalc.gui.welcome_layout import ART_FORMATS, LOGO_FORMATS, MAX_ART_BYTES

ENV_VAR = "CADDCALC_BRANDING"
PACK_FILE = "branding.toml"
PACK_DIR_NAME = "branding"
"""Name of the pack folder next to a packaged app's executable."""
SCHEMA = 1

ASSETS = Path(__file__).parent / "assets"
GENERIC_ICON = ASSETS / "app-icon.png"

ICON_SUFFIXES = frozenset({".png", ".ico"})
ABOUT_SUFFIXES = frozenset({".html", ".htm", ".txt"})
_KEYS = frozenset({"schema", "edition", "name", "icon", "about", "welcome"})
_WELCOME_KEYS = frozenset({"art", "art_focus", "logo"})
_EDITION_RE = re.compile(r"[a-z0-9][a-z0-9-]{0,31}")


class BrandingError(CaddCalcError):
    """A branding pack is missing, malformed, or names files it doesn't contain."""


@dataclass(frozen=True)
class Branding:
    """What the app shows as its identity. The defaults are the unbranded public build."""

    name: str = "CADD Calculator"
    edition: str = "generic"
    icon: Path | None = GENERIC_ICON
    welcome_art: Path | None = None
    """The welcome screen's art; ``None`` means the generic art (ADR-0015)."""
    welcome_focus: tuple[float, float] = (0.5, 0.5)
    """The point of the art kept in view when it is cropped, as fractions of its size."""
    welcome_logo: Path | None = None
    """The welcome screen's vertical logo; ``None`` means the app icon and name."""
    about_html: str | None = None
    """Rich-text fragment for Help > About. ``None`` means the generic description."""
    source: Path | None = None
    """The pack folder this came from, or ``None`` for the built-in generic branding."""
    files: tuple[Path, ...] = ()
    """Every file the pack uses, ``branding.toml`` included: what a build must bundle."""

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
            "logo); see ADR-0015"
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

    name = _required_text(data, "name", toml_path)
    edition = _required_text(data, "edition", toml_path)
    if not _EDITION_RE.fullmatch(edition) or edition == GENERIC.edition:
        raise BrandingError(
            f"{toml_path}: edition {edition!r} must be 1 to 32 lowercase letters, digits, "
            f"or hyphens, and not {GENERIC.edition!r}"
        )

    icon = _pack_file(data, "icon", root, ICON_SUFFIXES)
    about = _pack_file(data, "about", root, ABOUT_SUFFIXES)
    about_html = _read_about(about) if about is not None else None
    art, focus, logo = _welcome(data.get("welcome", {}), root)
    return Branding(
        name=name,
        edition=edition,
        icon=icon if icon is not None else GENERIC_ICON,
        welcome_art=art,
        welcome_focus=focus,
        welcome_logo=logo,
        about_html=about_html,
        source=root,
        files=(toml_path, *(f for f in (icon, about, art, logo) if f is not None)),
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


def _welcome(table: Any, root: Path) -> tuple[Path | None, tuple[float, float], Path | None]:
    """Read the ``[welcome]`` table: the art, its focal point, and the logo.

    Only the suffix, the path, and the size in bytes are checked here, without Qt. The
    welcome screen checks the art's pixel size before decoding it (ADR-0015, amendments).
    """
    toml_path = root / PACK_FILE
    if not isinstance(table, Mapping):
        raise BrandingError(f"{toml_path}: 'welcome' must be a table, [welcome]")
    unknown = sorted(set(table) - _WELCOME_KEYS)
    if unknown:
        raise BrandingError(
            f"{toml_path}: unknown [welcome] key(s) {', '.join(unknown)}; "
            f"expected some of {', '.join(sorted(_WELCOME_KEYS))}"
        )
    art = _pack_file(table, "art", root, frozenset(ART_FORMATS), label="welcome.art")
    logo = _pack_file(table, "logo", root, frozenset(LOGO_FORMATS), label="welcome.logo")
    for path, label in ((art, "welcome.art"), (logo, "welcome.logo")):
        if path is not None and path.stat().st_size > MAX_ART_BYTES:
            raise BrandingError(
                f"{toml_path}: {label} {path.name!r} is larger than {MAX_ART_BYTES // 1_000_000} MB"
            )
    if logo is not None and logo.suffix.lower() == ".svg":
        _check_self_contained(logo, toml_path)
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
    return art, (float(focus[0]), float(focus[1])), logo


_XLINK_HREF = "{http://www.w3.org/1999/xlink}href"


def _check_self_contained(svg: Path, toml_path: Path) -> None:
    """Refuse an SVG that refers to other files: they would escape the pack folder.

    An ``<image>`` or ``<use>`` may embed its data (``data:``) or point within the file
    (``#…``), nothing else (ADR-0015, amendments). The byte budget is checked first, and
    Python's expat limits entity expansion.
    """
    try:
        root = ElementTree.parse(svg).getroot()  # noqa: S314  # see the docstring
    except ElementTree.ParseError as exc:
        raise BrandingError(
            f"{toml_path}: welcome.logo {svg.name!r} isn't valid SVG: {exc}"
        ) from exc
    for element in root.iter():
        if element.tag.rsplit("}", 1)[-1] not in ("image", "use"):
            continue
        for key in (_XLINK_HREF, "href"):
            href = (element.get(key) or "").strip()
            if href and not href.startswith(("data:", "#")):
                raise BrandingError(
                    f"{toml_path}: welcome.logo {svg.name!r} refers to {href!r}; a logo must be "
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
