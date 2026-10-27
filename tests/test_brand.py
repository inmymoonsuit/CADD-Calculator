"""The brand artwork (docs/dev/design/brand.md): clean SVG sources, its palette and contrast."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from caddcalc.gui.style_tokens import contrast, luminance

ROOT = Path(__file__).parents[1]
APP_BRAND = ROOT / "src" / "caddcalc" / "gui" / "assets" / "brand"
DOC_BRAND = ROOT / "docs" / "dev" / "design" / "brand"
SOURCES = sorted([*APP_BRAND.glob("*.svg"), *DOC_BRAND.glob("*.svg")])
SVG = "{http://www.w3.org/2000/svg}"

CRIMSON, BLACK, WHITE = "#A31D31", "#000000", "#FFFFFF"
PALETTE = {CRIMSON, BLACK, WHITE}
SHAPES = {"path", "rect"}
"""The only elements a brand source holds, besides the ``<svg>`` itself."""
LIGHT_BACKGROUNDS = ["#FFFFFF"]
DARK_BACKGROUNDS = ["#21251F", "#202020", "#2D2D2D", "#0D1117"]
"""The app's dark background (ink), Windows' dark title bar and taskbar, and GitHub's
dark page: where the reversed files are shown."""
SMALL = (16, 24, 32)


def parse(path: Path) -> ET.Element:
    """Parse one of the repo's own brand files: trusted input, not data from outside."""
    return ET.parse(path).getroot()  # noqa: S314


def fills(path: Path) -> set[str]:
    return {el.get("fill", "") for el in parse(path).iter() if el.tag[len(SVG) :] in SHAPES}


def test_every_expected_source_is_there() -> None:
    names = {path.name for path in SOURCES}
    assert {
        "app-icon.svg",
        *(f"app-icon-{size}.svg" for size in SMALL),
        "symbol.svg",
        "symbol-reversed.svg",
        "symbol-monochrome.svg",
        "symbol-monochrome-reversed.svg",
        "logo-outlined.svg",
        "logo-outlined-reversed.svg",
    } <= names
    masters = {path.name for path in (DOC_BRAND / "masters").glob("*.ai")}
    assert {
        f"cadd-calculator-{name}.ai"
        for name in ("app-icon", "symbol", "symbol-monochrome", "logo-outlined")
    } <= masters


@pytest.mark.parametrize("path", sorted((DOC_BRAND / "masters").glob("*.ai")), ids=str)
def test_a_master_names_its_owner_only_by_handle(path: Path) -> None:
    """Illustrator writes the user's name into ``%%For:``; the masters carry the handle.

    The compressed copy of the header in Illustrator's private data can't be read
    without zstd, so only the plain header is checked here.
    """
    owners = re.findall(rb"%%For: \(([^)]*)\)", path.read_bytes())
    assert set(owners) <= {b"inmymoonsuit"}, owners


@pytest.mark.parametrize("path", SOURCES, ids=lambda p: p.name)
def test_a_source_is_plain_flat_vector(path: Path) -> None:
    """Paths and rectangles only: no hidden layers, styles, text, images or references."""
    text = path.read_text(encoding="utf-8")
    assert "<!--" not in text, "no comments"
    assert "display" not in text and "visibility" not in text, "no hidden layers"
    assert "href" not in text and "url(" not in text, "no external references"
    assert "_" not in path.name, "hyphens in file names"
    root = parse(path)
    assert root.tag == f"{SVG}svg"
    for el in root.iter():
        if el is root:
            continue
        tag = el.tag[len(SVG) :] if el.tag.startswith(SVG) else el.tag
        assert tag in SHAPES, f"<{tag}> isn't allowed in a brand source"
        assert "class" not in el.attrib and "style" not in el.attrib, "fills, not styles"
        assert re.fullmatch(r"[a-z]+(-[a-zA-Z]+)+", el.get("id", "")), el.get("id")


@pytest.mark.parametrize("path", SOURCES, ids=lambda p: p.name)
def test_a_source_uses_only_the_palettes_three_colours(path: Path) -> None:
    used = fills(path)
    assert used <= PALETTE, used - PALETTE


def test_crimson_reaches_3_to_1_on_light_backgrounds() -> None:
    for background in LIGHT_BACKGROUNDS:
        assert contrast(luminance(CRIMSON), luminance(background)) >= 3, background


@pytest.mark.parametrize(
    "path",
    [p for p in SOURCES if "reversed" in p.name and "monochrome" not in p.name],
    ids=lambda p: p.name,
)
def test_a_reversed_mark_reads_by_its_white_parts_on_dark(path: Path) -> None:
    """The C and "Calculator" are white, at least 4.5:1 on every dark background.

    The crimson parts stay crimson on dark, by the maintainer's decision: a logo is exempt
    from SC 1.4.3, and isn't content under SC 1.4.11 (brand.md, "Palette").
    """
    shapes = {el.get("id"): el.get("fill") for el in parse(path).iter() if el.get("id")}
    for part in ("symbol-C-upper", "symbol-C-lower", "word-Calculator"):
        if part in shapes:
            assert shapes[part] == WHITE, part
    for background in DARK_BACKGROUNDS:
        assert contrast(luminance(WHITE), luminance(background)) >= 4.5, background


def test_the_app_icons_mark_reads_on_its_tile() -> None:
    root = parse(APP_BRAND / "app-icon.svg")
    tile = next(el for el in root if el.get("id") == "icon-background")
    marks = {el.get("fill") for el in root if el is not tile}
    assert tile.get("fill") == CRIMSON and marks == {"#FFFFFF"}
    assert contrast(luminance(CRIMSON), luminance("#FFFFFF")) >= 4.5


@pytest.mark.gui
@pytest.mark.usefixtures("qt")
@pytest.mark.parametrize(("size", "band"), [(16, 3), (24, 4), (32, 5)])
def test_a_small_drawing_keeps_its_diagonal_gap_open(size: int, band: int) -> None:
    """At its own size, every pixel on the gap's centre diagonal is the tile's crimson.

    The master's gap is under a pixel at these sizes, so it blurs shut (brand.md).
    """
    from PySide6.QtCore import QRectF, Qt
    from PySide6.QtGui import QColor, QImage, QPainter
    from PySide6.QtSvg import QSvgRenderer

    renderer = QSvgRenderer(str(APP_BRAND / f"app-icon-{size}.svg"))
    assert renderer.isValid() and renderer.viewBox().width() == size
    image = QImage(size, size, QImage.Format.Format_ARGB32)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    renderer.render(painter, QRectF(0, 0, size, size))
    painter.end()
    crimson = QColor(CRIMSON)
    gap = [(x, x + band) for x in range(size) if 0 <= x + band < size]
    inside = [(x, y) for x, y in gap if size * 0.2 < x < size * 0.6]  # along the mark only
    assert inside
    for x, y in inside:
        assert image.pixelColor(x, y).rgb() == crimson.rgb(), (x, y)


@pytest.mark.parametrize("size", SMALL[:2])
def test_the_smallest_drawings_drop_the_squares_hole(size: int) -> None:
    root = parse(APP_BRAND / f"app-icon-{size}.svg")
    square = next(el for el in root if el.get("id") == "symbol-drafting-square")
    assert square.get("d", "").upper().count("M") == 1, "one outline, no hole"


def test_the_trademark_policy_names_the_marks_and_is_linked() -> None:
    """The brand files are under Apache-2.0; TRADEMARKS.md governs their use as marks."""
    policy = (ROOT / "TRADEMARKS.md").read_text(encoding="utf-8")
    for folder in ("src/caddcalc/gui/assets/brand/", "docs/dev/design/brand/"):
        assert f"`{folder}`" in policy, folder
    assert '"CADD Calculator"' in policy
    assert "The files themselves are under Apache-2.0" in policy
    assert "aren't licensed" not in policy, "one licence for the whole repo"
    assert "(TRADEMARKS.md)" in (ROOT / "README.md").read_text(encoding="utf-8")
    assert "TRADEMARKS.md" in (ROOT / "docs/dev/design/brand.md").read_text(encoding="utf-8")


def test_the_welcome_art_names_its_rights_holder_and_licence() -> None:
    """The maintainer's art, for this project only and credited; art, not a mark."""
    rights = "Welcome art © inmymoonsuit (the maintainer), not under Apache-2.0"
    for doc in ("THIRD_PARTY_NOTICES.md", "docs/dev/design/brand.md"):
        text = " ".join((ROOT / doc).read_text(encoding="utf-8").split())
        assert rights in text, doc
        assert "ART-LICENSE.md" in text, doc
    terms = (ROOT / "ART-LICENSE.md").read_text(encoding="utf-8")
    assert "`src/caddcalc/gui/assets/welcome/welcome-art.jpg`" in terms
    assert "> Welcome art © inmymoonsuit" in terms, "the credit"
    assert "**Use it in any other project,**" in terms
    assert "(ART-LICENSE.md)" in (ROOT / "README.md").read_text(encoding="utf-8")
    assert "welcome art" not in (ROOT / "TRADEMARKS.md").read_text(encoding="utf-8").lower()
