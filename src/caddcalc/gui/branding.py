"""Optional branding packs for the desktop app (ADR-0008 item 4, ADR-0011).

The public build is unbranded and uses ``GENERIC``. A *branding pack* is a folder
with a ``branding.toml`` file and the files it names::

    schema = 1                                   # pack format version (optional)
    edition = "example"                          # short slug: build folder names
    name = "CADD Calculator: Example Edition"    # window title, About heading
    icon = "icon.png"                            # optional window icon (.png or .ico)
    splash = "splash.png"                        # optional, shown while the app starts
    about = "about.html"                         # optional About text (.html or .txt)

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
from collections.abc import Mapping
from dataclasses import dataclass
from html import escape
from pathlib import Path
from typing import Any

from caddcalc.core.errors import CaddCalcError

ENV_VAR = "CADDCALC_BRANDING"
PACK_FILE = "branding.toml"
PACK_DIR_NAME = "branding"
"""Name of the pack folder next to a packaged app's executable."""
SCHEMA = 1

ASSETS = Path(__file__).parent / "assets"
GENERIC_ICON = ASSETS / "app-icon.png"

ICON_SUFFIXES = frozenset({".png", ".ico"})
SPLASH_SUFFIXES = frozenset({".png", ".jpg", ".jpeg"})
ABOUT_SUFFIXES = frozenset({".html", ".htm", ".txt"})
_KEYS = frozenset({"schema", "edition", "name", "icon", "splash", "about"})
_EDITION_RE = re.compile(r"[a-z0-9][a-z0-9-]{0,31}")


class BrandingError(CaddCalcError):
    """A branding pack is missing, malformed, or names files it doesn't contain."""


@dataclass(frozen=True)
class Branding:
    """What the app shows as its identity. The defaults are the unbranded public build."""

    name: str = "CADD Calculator"
    edition: str = "generic"
    icon: Path | None = GENERIC_ICON
    splash: Path | None = None
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
    splash = _pack_file(data, "splash", root, SPLASH_SUFFIXES)
    about = _pack_file(data, "about", root, ABOUT_SUFFIXES)
    about_html = _read_about(about) if about is not None else None
    return Branding(
        name=name,
        edition=edition,
        icon=icon if icon is not None else GENERIC_ICON,
        splash=splash,
        about_html=about_html,
        source=root,
        files=(toml_path, *(f for f in (icon, splash, about) if f is not None)),
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


def _pack_file(
    data: Mapping[str, Any], key: str, root: Path, suffixes: frozenset[str]
) -> Path | None:
    value = data.get(key)
    if value is None:
        return None
    toml_path = root / PACK_FILE
    if not isinstance(value, str) or not value.strip():
        raise BrandingError(f"{toml_path}: {key!r} must be a file name")
    path = root / value
    # The build copies only the pack folder, so a file outside it would go missing.
    if not path.resolve().is_relative_to(root.resolve()):
        raise BrandingError(f"{toml_path}: {key} {value!r} must be inside the pack folder")
    if path.suffix.lower() not in suffixes:
        raise BrandingError(
            f"{toml_path}: {key} {value!r} must be one of {', '.join(sorted(suffixes))}"
        )
    if not path.is_file():
        raise BrandingError(f"{toml_path}: {key} file {value!r} does not exist")
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
