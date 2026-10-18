"""The vendored display face: pinned, verified, credited, and loaded (ADR-0016 §2)."""

from __future__ import annotations

import hashlib
import importlib
import re
import struct
import tomllib
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from caddcalc.gui.welcome_style import STYLE_FILE, style

ROOT = Path(__file__).resolve().parent.parent
ASSETS = STYLE_FILE.parent
FONT_DIR = ASSETS / "fonts" / "vt323"
MANIFEST = tomllib.loads((FONT_DIR / "manifest.toml").read_text(encoding="utf-8"))


def test_files_match_the_pinned_manifest() -> None:
    assert re.fullmatch(r"[0-9a-f]{40}", MANIFEST["commit"])
    assert MANIFEST["license"] == "OFL-1.1"
    for name, digest in MANIFEST["files"].items():
        assert hashlib.sha256((FONT_DIR / name).read_bytes()).hexdigest() == digest, name
    on_disk = {p.name for p in FONT_DIR.iterdir()} - {"manifest.toml"}
    assert on_disk == set(MANIFEST["files"]) == {"VT323-Regular.ttf", "OFL.txt"}
    assert "SIL OPEN FONT LICENSE Version 1.1" in (FONT_DIR / "OFL.txt").read_text("utf-8")


def test_the_fetch_scripts_offline_check_passes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.syspath_prepend(str(ROOT / "packaging"))
    fetch_fonts = importlib.import_module("fetch_fonts")
    assert fetch_fonts.check() == []
    assert fetch_fonts.main(["--check"]) == 0


def test_the_tokens_name_the_vendored_face_drawn_regular() -> None:
    typography = style().typography
    assert (ASSETS / typography.display_file).parent == FONT_DIR
    assert typography.display_family == MANIFEST["name"]
    assert typography.display_weight == "regular", "the maintainer's call (ADR-0016)"


def _table(font: bytes, tag: bytes) -> int:
    """Return the offset of a TrueType table, from the font's table directory."""
    (count,) = struct.unpack(">H", font[4:6])
    for entry in range(count):
        name, _checksum, offset, _length = struct.unpack(
            ">4sIII", font[12 + 16 * entry : 28 + 16 * entry]
        )
        if name == tag:
            return int(offset)
    raise AssertionError(f"no {tag!r} table")


def test_the_grid_tokens_match_the_font_file() -> None:
    """25 design pixels to the em and capitals 0.56 em tall, read from VT323 itself."""
    typography = style().typography
    font = (ASSETS / typography.display_file).read_bytes()
    head, os2, hhea, hmtx = (_table(font, t) for t in (b"head", b"OS/2", b"hhea", b"hmtx"))
    (units,) = struct.unpack(">H", font[head + 18 : head + 20])
    (cap,) = struct.unpack(">h", font[os2 + 88 : os2 + 90])
    assert cap / units == typography.display_cap_height
    pixel = units // typography.display_em_pixels
    assert pixel * typography.display_em_pixels == units
    (metrics,) = struct.unpack(">H", font[hhea + 34 : hhea + 36])
    advances = [
        struct.unpack(">H", font[hmtx + 4 * i : hmtx + 4 * i + 2])[0] for i in range(metrics)
    ]
    assert all(advance % pixel == 0 for advance in advances), "every glyph is whole pixels"


def test_notices_credit_the_pinned_face_with_its_license() -> None:
    notices = (ROOT / "THIRD_PARTY_NOTICES.md").read_text(encoding="utf-8")
    assert MANIFEST["commit"] in notices
    assert MANIFEST["copyright"] in notices
    assert (FONT_DIR / "OFL.txt").read_text(encoding="utf-8").strip() in notices


@pytest.mark.gui
@pytest.mark.usefixtures("qt")
def test_about_credits_the_face() -> None:
    from caddcalc.gui.actions import about_html
    from caddcalc.gui.branding import GENERIC

    html = about_html(GENERIC)
    assert "VT323" in html and "SIL Open Font License 1.1" in html


@pytest.fixture
def fresh_fonts(request: pytest.FixtureRequest) -> Iterator[Any]:
    """The fonts module with its once-only load forgotten, before and after the test."""
    request.getfixturevalue("qt")  # Qt's font database needs the application
    from caddcalc.gui import fonts

    fonts.display_family.cache_clear()
    yield fonts
    fonts.display_family.cache_clear()


@pytest.mark.gui
def test_the_display_face_loads_into_qt(fresh_fonts: Any) -> None:
    from PySide6.QtGui import QFontDatabase, QFontInfo

    from caddcalc.gui.welcome import display_font

    assert fresh_fonts.display_family() == "VT323"
    assert "VT323" in QFontDatabase.families()
    info = QFontInfo(display_font(50))
    assert (info.family(), info.bold()) == ("VT323", False)


@pytest.mark.gui
def test_the_fallbacks_are_named_only_for_a_face_that_didnt_load(
    fresh_fonts: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Named beside a loaded face, each fallback is resolved at the first measure.

    On a machine with many fonts, that held the welcome card's first paint for over a
    second (ADR-0016, amendments).
    """
    from caddcalc.gui.welcome import display_font

    typography = style().typography
    assert display_font(50).families() == [typography.display_family]
    fresh_fonts.display_family.cache_clear()
    monkeypatch.setattr(fresh_fonts, "ASSETS", tmp_path)
    with pytest.warns(UserWarning, match="using a fallback"):
        families = display_font(50).families()
    assert families == [typography.display_family, *typography.fallback_families]


@pytest.mark.gui
def test_a_face_that_cant_be_loaded_falls_back_with_a_warning(
    fresh_fonts: Any, tmp_path: Path
) -> None:
    not_a_font = tmp_path / "VT323-Regular.ttf"
    not_a_font.write_bytes(b"not a font")
    with pytest.warns(UserWarning, match="can't be read as a font"):
        assert fresh_fonts.add_font(not_a_font, "VT323") == fresh_fonts.FALLBACK
    with pytest.warns(UserWarning, match="can't be read as a font"):
        assert fresh_fonts.add_font(tmp_path / "missing.ttf", "VT323") == fresh_fonts.FALLBACK
    with pytest.warns(UserWarning, match="holds VT323"):
        wrong = fresh_fonts.add_font(FONT_DIR / "VT323-Regular.ttf", "Another Face")
    assert wrong == fresh_fonts.FALLBACK


@pytest.mark.gui
def test_the_welcome_screen_starts_without_its_face(
    fresh_fonts: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from caddcalc.gui.actions import AppActions
    from caddcalc.gui.branding import GENERIC
    from caddcalc.gui.welcome import WelcomeScreen

    monkeypatch.setattr(fresh_fonts, "ASSETS", tmp_path)
    with pytest.warns(UserWarning, match="using a fallback"):
        welcome = WelcomeScreen(GENERIC, AppActions(GENERIC))
    assert welcome.display_face == fresh_fonts.FALLBACK
    welcome.close()
