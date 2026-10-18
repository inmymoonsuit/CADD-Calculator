"""Vendored Tabler icons: pinned, verified, used, credited, and recolored (design/icons.md)."""

from __future__ import annotations

import hashlib
import re
import tomllib
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parent.parent
TABLER = ROOT / "src" / "caddcalc" / "gui" / "assets" / "icons" / "tabler"
MANIFEST = tomllib.loads((TABLER / "manifest.toml").read_text(encoding="utf-8"))
VENDORED = set(MANIFEST["icons"])
UI_TOKENS = tomllib.loads(
    (ROOT / "src" / "caddcalc" / "gui" / "assets" / "ui_style.toml").read_text(encoding="utf-8")
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_files_match_the_pinned_manifest() -> None:
    assert re.fullmatch(r"\d+\.\d+\.\d+", MANIFEST["version"])
    assert MANIFEST["license"] == "MIT"
    for name, digest in MANIFEST["icons"].items():
        assert sha256(TABLER / "outline" / f"{name}.svg") == digest, name
    assert sha256(TABLER / "LICENSE.txt") == MANIFEST["license_file"]["sha256"]
    on_disk = {p.stem for p in (TABLER / "outline").glob("*.svg")}
    assert on_disk == VENDORED, "every SVG on disk is listed, and vice versa"


def test_svgs_can_be_recolored() -> None:
    for name in VENDORED:
        assert "currentColor" in (TABLER / "outline" / f"{name}.svg").read_text(encoding="utf-8")


def test_only_the_icons_the_app_uses_are_vendored() -> None:
    """Every icon the GUI code asks for is vendored, and every vendored icon is used."""
    pattern = re.compile(r"""(?:\bicon|_img)\(\s*["']([a-z0-9-]+)["']""")
    used: set[str] = set()
    for path in (ROOT / "src" / "caddcalc" / "gui").glob("*.py"):
        used |= set(pattern.findall(path.read_text(encoding="utf-8")))
    # A component may name its icons by design tokens, such as result_field.copy_icon.
    for table in UI_TOKENS.values():
        if isinstance(table, dict):
            used |= {value for key, value in table.items() if key.endswith("_icon")}
    assert used == VENDORED


def test_notices_credit_the_pinned_version() -> None:
    notices = (ROOT / "THIRD_PARTY_NOTICES.md").read_text(encoding="utf-8")
    assert f"Tabler Icons {MANIFEST['version']}" in notices
    assert (TABLER / "LICENSE.txt").read_text(encoding="utf-8").strip() in notices


@pytest.mark.gui
def test_icons_render_in_the_palette_color(qt: Any) -> None:
    from caddcalc.gui import icons

    app = qt.QApplication.instance()
    assert app is not None
    crimson = icons.role_color("icon_error", "light")
    assert crimson == "#A3122F"
    assert b"currentColor" not in icons.svg_source("alert-circle", crimson)

    image = icons.render("alert-circle", crimson, 48)
    opaque = [
        image.pixelColor(x, y)
        for x in range(48)
        for y in range(48)
        if image.pixelColor(x, y).alpha() == 255
    ]
    assert opaque, "the icon drew something"
    assert all(c.name().upper() == crimson for c in opaque), "solid pixels use the palette color"

    for scheme in ("light", "dark"):
        for name in VENDORED:
            assert not icons.icon(name, scheme=scheme).isNull()
