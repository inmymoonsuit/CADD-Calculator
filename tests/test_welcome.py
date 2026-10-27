"""The welcome screen (ADR-0015). Skipped when PySide6 is not installed.

Every image here is generated in the test; no pack art is used (ADR-0015 §3).
"""

from __future__ import annotations

import gc
import sys
import weakref
from pathlib import Path
from typing import Any

import pytest

from caddcalc import __version__
from caddcalc.gui.branding import GENERIC, PRODUCT_NAME, Branding, load_branding
from caddcalc.gui.welcome_layout import Rect, device_rect
from caddcalc.gui.welcome_style import style

ART_SIZE, MAX_ART_PX, WINDOW = style().art.slot, style().art.max_px, style().window

pytestmark = [pytest.mark.gui, pytest.mark.usefixtures("qt")]

LOGO_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="72" height="540" viewBox="0 0 72 540">'
    '<rect width="72" height="540" fill="#202020"/></svg>'
)


SQUARE_LOGO_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100" viewBox="0 0 100 100">'
    '<rect width="100" height="100" fill="#202020"/></svg>'
)
WIDE_LOGO_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="400" height="100" viewBox="0 0 400 100">'
    '<rect width="400" height="100" fill="#202020"/></svg>'
)


def generated_art(kind: str, size: tuple[int, int]) -> Any:
    """Art drawn here: flat blue, calm and light, dark, or a busy black-and-white check."""
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QColor, QImage, QPainter

    transparent = kind == "transparent"
    art = QImage(*size, QImage.Format.Format_ARGB32 if transparent else QImage.Format.Format_RGB32)
    art.fill(QColor({"blue": "#336699", "light": "#F4F1EA", "dark": "#101418"}.get(kind, "white")))
    if transparent:
        # Dark ink on the left, and nothing at all where the panes sit.
        art.fill(Qt.GlobalColor.transparent)
        p = QPainter(art)
        p.fillRect(0, 0, size[0] * 2 // 5, size[1], QColor("#101418"))
        p.end()
    if kind.startswith("saturated"):
        # A saturated colour between neutral extremes: grey and white stripes, 1 px in 17.
        saturated = {"blue": "#0000FF", "red": "#FF0000", "green": "#00FF00"}[kind.split("-")[1]]
        art.fill(QColor(saturated))
        p = QPainter(art)
        for x in range(0, size[0], 17 * 2):
            p.fillRect(x, 0, 2, size[1], QColor("#3C3C3C"))
            p.fillRect(x + 2, 0, 2, size[1], QColor("white"))
        p.end()
    if kind == "busy":
        p = QPainter(art)
        square = 24
        for x in range(0, size[0], square):
            for y in range(0, size[1], square):
                if (x // square + y // square) % 2:
                    p.fillRect(x, y, square, square, Qt.GlobalColor.black)
        p.end()
    return art


FORK_LOGO_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="300" height="100" viewBox="0 0 300 100">'
    '<rect width="300" height="100" fill="#2E7D32"/></svg>'
)
"""A modified build's own title logo: no crimson, so it can't be the project's."""


def pack(
    folder: Path,
    *,
    art_size: tuple[int, int] = (1920, 1080),
    logo: str | None = LOGO_SVG,
    art: str = "blue",
    product: str | None = None,
) -> Branding:
    """A pack with generated welcome art, an organization logo, and maybe a title logo."""
    folder.mkdir(parents=True, exist_ok=True)
    assert generated_art(art, art_size).save(str(folder / "welcome-art.png"))
    toml = 'edition = "test-edition"\n[welcome]\nart = "welcome-art.png"\nart_focus = [0.25, 0.5]\n'
    if logo is not None:
        (folder / "logo.svg").write_text(logo, encoding="utf-8")
        toml += 'organization_logo = "logo.svg"\n'
    if product is not None:
        (folder / "fork.svg").write_text(product, encoding="utf-8")
        toml += 'product_logo = "fork.svg"\n'
    (folder / "branding.toml").write_text(toml, encoding="utf-8")
    return load_branding(folder)


def screen(branding: Branding = GENERIC) -> Any:
    from caddcalc.gui.actions import AppActions
    from caddcalc.gui.welcome import WelcomeScreen

    return WelcomeScreen(branding, AppActions(branding))


def flush() -> None:
    from PySide6.QtCore import QEvent
    from PySide6.QtWidgets import QApplication

    QApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    gc.collect()


def test_the_generic_screen_shows_the_title_and_version_over_generated_art() -> None:
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QMenuBar

    welcome = screen()
    assert (welcome.art_source, welcome.title_source) == ("generic", "brand")
    assert welcome.organization_source == "none"
    assert welcome.title.accessibleName() == PRODUCT_NAME
    assert welcome.art.version_pane.text == f"Version {__version__}"
    assert welcome.windowModality() is Qt.WindowModality.ApplicationModal
    assert welcome.windowFlags() & Qt.WindowType.FramelessWindowHint
    assert welcome.findChildren(QMenuBar) == [], "the app's menus live in the main window"
    welcome.show()
    image = welcome.grab().toImage()
    assert not image.isNull()
    welcome.close()


def test_a_packs_art_and_organization_logo_are_used(tmp_path: Path) -> None:
    welcome = screen(pack(tmp_path / "pack"))
    assert (welcome.art_source, welcome.organization_source) == ("pack", "pack")
    assert welcome.title_source == "brand", "a branded edition keeps the project's title"
    assert welcome.art.version_pane.text == f"Version {__version__}", "no edition slug"
    welcome.show()
    assert welcome.logo.isVisible() and welcome.logo.accessibleName() == "Organization logo"
    assert not welcome.grab().toImage().isNull()
    welcome.close()


@pytest.mark.parametrize(
    "spoil",
    ["garbage", "oversized", "deleted"],
)
def test_art_that_cant_be_used_falls_back_to_the_built_in_art(tmp_path: Path, spoil: str) -> None:
    branding = pack(tmp_path / "pack")
    assert branding.welcome_art is not None
    if spoil == "garbage":
        branding.welcome_art.write_bytes(b"not an image")
    elif spoil == "oversized":
        branding = pack(tmp_path / "big", art_size=(MAX_ART_PX + 1, 4))
    else:
        branding.welcome_art.unlink()
    with pytest.warns(UserWarning, match="Ignoring the welcome art"):
        welcome = screen(branding)
    assert welcome.art_source == "generic"
    welcome.close()


def test_an_invalid_organization_logo_leaves_the_strip_empty(tmp_path: Path) -> None:
    """The loader refuses malformed XML; this covers XML that Qt still can't render."""
    branding = pack(tmp_path / "pack")
    assert branding.organization_logo is not None
    branding.organization_logo.write_text("<notsvg/>", encoding="utf-8")
    with pytest.warns(UserWarning, match="Ignoring the organization logo logo.svg: invalid SVG"):
        welcome = screen(branding)
    welcome.show()
    assert welcome.organization_source == "none" and not welcome.logo.isVisible()
    welcome.close()


def test_escape_and_the_x_close_it() -> None:
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest

    for close in ("escape", "x"):
        welcome = screen()
        welcome.show()
        if close == "escape":
            QTest.keyClick(welcome, Qt.Key.Key_Escape)
        else:
            QTest.mouseClick(welcome.close_button, Qt.MouseButton.LeftButton)
        assert not welcome.isVisible(), close


def test_dragging_the_top_bar_moves_the_card_through_the_system(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from PySide6.QtCore import QPoint, Qt
    from PySide6.QtGui import QWindow
    from PySide6.QtTest import QTest

    moves: list[bool] = []
    monkeypatch.setattr(QWindow, "startSystemMove", lambda _self: moves.append(True) or True)
    welcome = screen()
    welcome.show()
    QTest.mousePress(welcome.top_bar, Qt.MouseButton.LeftButton, pos=QPoint(400, 10))
    assert moves == [True]
    welcome.close()


def test_the_card_fits_its_screen_at_the_preferred_shape() -> None:
    welcome = screen()
    available = welcome.screen().availableGeometry()
    assert welcome.width() <= max(available.width(), WINDOW.width)
    assert welcome.width() / welcome.height() == pytest.approx(WINDOW.width / WINDOW.height, 0.01)
    assert welcome.art.width() / welcome.art.height() == pytest.approx(
        ART_SIZE.width / ART_SIZE.height, 0.01
    )
    welcome.close()


def test_the_built_in_art_is_the_maintainers_as_supplied() -> None:
    """The official build's art: a file in the package, 16:9 at 1920 x 1080, in budget.

    It's art, not a mark, so it isn't among the brand's files (TRADEMARKS.md).
    """
    from PySide6.QtGui import QImageReader

    from caddcalc.gui.branding import BRAND, GENERIC_ART

    tokens = style()
    reader = QImageReader(str(GENERIC_ART))
    assert (reader.size().width(), reader.size().height()) == (1920, 1080)
    assert reader.size().width() == tokens.art.supplied.width, "supplied at twice the slot"
    assert GENERIC_ART.suffix in tokens.art.formats
    assert GENERIC_ART.stat().st_size <= tokens.art.max_bytes
    assert not GENERIC_ART.is_relative_to(BRAND)
    data, markers, at = GENERIC_ART.read_bytes(), set(), 2
    while data[at] == 0xFF and data[at + 1] != 0xDA:  # every segment before the image data
        markers.add(data[at + 1])
        at += 2 + int.from_bytes(data[at + 2 : at + 4], "big")
    # JFIF's header, quantization, frame, and Huffman tables: no comment, EXIF, or XMP.
    assert markers <= {0xE0, 0xDB, 0xC0, 0xC2, 0xC4, 0xDD}, sorted(hex(m) for m in markers)
    welcome = screen()
    assert welcome.art_source == "generic"
    welcome.close()


def test_without_any_readable_art_the_cards_background_shows(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """If even the built-in art can't be read, startup goes on; the build's check fails."""
    from PySide6.QtGui import QImage

    from caddcalc.gui import welcome as module
    from caddcalc.gui.icons import current_scheme

    monkeypatch.setattr(module, "GENERIC_ART", tmp_path / "missing.jpg")
    with pytest.warns(UserWarning, match="Ignoring the built-in welcome art missing.jpg"):
        welcome = screen()
    welcome.show()
    assert welcome.art_source == "none"
    shown = welcome.art.shown_art().convertToFormat(QImage.Format.Format_RGB32)
    background = module.card_background(current_scheme()).rgb()
    assert {shown.pixel(x, y) for x in range(0, shown.width(), 37) for y in (0, 100)} == {
        background
    }
    welcome.close()


def test_a_closed_welcome_screen_is_freed() -> None:
    """KI-019: nothing may hold the screen once it's closed."""
    welcome = screen()
    welcome.show()
    alive = weakref.ref(welcome)
    welcome.close()
    del welcome
    flush()
    assert alive() is None


def test_help_reopens_it_over_the_main_window() -> None:
    from PySide6.QtCore import Qt

    from caddcalc.gui.welcome import WelcomeScreen
    from tests.qt_helpers import open_window

    window = open_window()
    window.show()
    window.app_actions.welcome.trigger()
    (welcome,) = window.findChildren(WelcomeScreen)
    assert welcome.isVisible() and welcome.parentWidget() is window
    assert welcome.windowModality() is Qt.WindowModality.ApplicationModal
    welcome.close()
    flush()
    assert window.findChildren(WelcomeScreen) == [], "deleted when closed"
    window.close()


def test_the_about_button_shows_the_version_and_the_license(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QMessageBox

    shown: list[tuple[str, str]] = []
    monkeypatch.setattr(
        QMessageBox, "exec", lambda box: shown.append((box.windowTitle(), box.text())) or 0
    )
    welcome = screen()
    welcome.show()
    assert welcome.about_button.accessibleName() == "About"
    QTest.mouseClick(welcome.about_button, Qt.MouseButton.LeftButton)
    ((title, text),) = shown
    # macOS ignores a message box's title, as its guidelines ask, so Qt reports none there.
    assert title == ("" if sys.platform == "darwin" else "About CADD Calculator")
    assert __version__ in text and "Apache License, Version 2.0" in text
    welcome.close()


# --- the restyle (ADR-0016 §3 to §5) -----------------------------------------------------


def measured(welcome: Any, pane: Any) -> tuple[float, float]:
    """The text's contrast, and the background's spread, over the art as Qt shows it.

    The card is grabbed with the pane hidden, as Qt renders it, so transparent art
    shows the card's background; the pane's fill is blended over it by Qt itself, and
    every pixel under the pane counts, at the style's percentile. The grab is in device
    pixels, so the pane's rectangle is taken in them too, at any display scale.
    """
    import math

    from PySide6.QtCore import QPoint, QRect
    from PySide6.QtGui import QColor, QImage, QPainter

    from caddcalc.gui.icons import current_scheme, role_color
    from caddcalc.gui.welcome_style import contrast, luminance, rgb_luminance

    panes, scheme = style().panes, current_scheme()
    text_role, fill_role, alpha = pane.fill(scheme)
    pane.hide()
    shown = welcome.grab().toImage().convertToFormat(QImage.Format.Format_RGBX8888)
    pane.show()
    ratio = shown.devicePixelRatio()
    shown.setDevicePixelRatio(1)  # painted and cropped in device pixels from here on
    corner = pane.mapTo(welcome, QPoint(0, 0))
    box = device_rect(Rect(corner.x(), corner.y(), pane.width(), pane.height()), ratio)
    area = QRect(round(box.x), round(box.y), round(box.width), round(box.height))
    fill = QColor(role_color(fill_role, scheme))
    fill.setAlpha(alpha)
    p = QPainter(shown)
    p.fillRect(area, fill)
    p.end()
    under = shown.copy(area)  # kept alive while its pixels are read
    data = bytes(under.constBits())
    levels = sorted(rgb_luminance(c) for c in zip(data[0::4], data[1::4], data[2::4], strict=True))
    text = luminance(role_color(text_role, scheme))

    def at(share: float) -> float:
        return levels[max(math.ceil(share / 100 * len(levels)), 1) - 1]

    low, high = at(panes.percentile), at(100 - panes.percentile)
    reading = min(contrast(text, low), contrast(text, high))  # the extremes read worst
    return reading, contrast(high, low)


@pytest.mark.parametrize(
    ("art", "raised"),
    [
        ("light", False),
        ("dark", False),
        ("busy", True),
        ("saturated-blue", True),
        ("saturated-red", True),
        ("saturated-green", True),
    ],
)
def test_the_panes_stay_quiet_and_readable_over_any_art(
    tmp_path: Path, art: str, raised: bool
) -> None:
    import math

    from caddcalc.gui.icons import current_scheme

    panes = style().panes
    floor = math.ceil(panes.fill_opacity_min * 255)
    welcome = screen(pack(tmp_path / "pack", art=art))
    welcome.show()
    for pane, needed in ((welcome.title, 3), (welcome.art.version_pane, 4.5)):
        name = pane.accessibleName()
        assert pane.tokens.min_contrast == needed, "the title's graphics 3:1, the version 4.5:1"
        text_role, fill_role, alpha = pane.fill(current_scheme())
        dark_text = text_role == panes.text_roles[0]
        assert fill_role == panes.fill_roles[0 if dark_text else 1], "each text has its fill"
        if not art.startswith("saturated"):  # how far those rise depends on the blend
            assert (alpha > floor) == raised, (name, alpha)
        assert alpha >= floor
        reading, spread = measured(welcome, pane)
        assert reading >= needed, name
        assert spread <= panes.max_background_spread, (name, spread)
    shown = welcome.title.shown_logo(current_scheme())
    if art in ("light", "dark"):
        assert shown == {"light": "normal", "dark": "reversed"}[art], "the logo that reads"
    welcome.close()


@pytest.mark.parametrize("art", ["saturated-blue", "saturated-red", "saturated-green"])
def test_the_panes_read_over_fine_stripes_at_the_cards_full_size(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, art: str
) -> None:
    """At its full size, the art's 1 px stripes fall where a regular grid missed them.

    A screen the card fits on shows it at full size, but the offscreen screen is
    smaller and shrinks it, so the card is held at its full size here.
    """
    from caddcalc.gui.icons import current_scheme
    from caddcalc.gui.welcome import WelcomeScreen

    monkeypatch.setattr(WelcomeScreen, "_fit_scale", lambda _self: 1.0)
    panes = style().panes
    welcome = screen(pack(tmp_path / "pack", art=art))
    welcome.show()
    assert (welcome.width(), welcome.height()) == (round(WINDOW.width), round(WINDOW.height))
    for pane, needed in ((welcome.title, 3), (welcome.art.version_pane, 4.5)):
        pane.fill(current_scheme())
        reading, spread = measured(welcome, pane)
        assert reading >= needed, (pane.accessibleName(), reading)
        assert spread <= panes.max_background_spread, (pane.accessibleName(), spread)
    welcome.close()


SCALED_PANES = """
import json
from PySide6.QtWidgets import QApplication
app = QApplication([])
from caddcalc.gui.actions import AppActions
from caddcalc.gui.branding import GENERIC
from caddcalc.gui.welcome import WelcomeScreen
from caddcalc.gui.welcome_layout import Rect, device_rect
welcome = WelcomeScreen(GENERIC, AppActions(GENERIC))
welcome.show()
app.processEvents()
found = []
for pane in (welcome.title, welcome.art.version_pane):
    ratio, box = pane.devicePixelRatioF(), pane.geometry()
    covered = device_rect(Rect(box.x(), box.y(), box.width(), box.height()), ratio)
    found.append([ratio, len(pane.art), round(covered.width * covered.height)])
welcome.close()
print(json.dumps(found))
"""


def test_a_pane_measures_every_device_pixel_at_twice_the_scale(tmp_path: Path) -> None:
    """At 200%, the art is drawn and measured in device pixels, four to a logical one.

    Qt's scale is set before the application starts, so it runs in its own process.
    """
    import json
    import os
    import subprocess
    import sys

    script = tmp_path / "scaled_panes.py"
    script.write_text(SCALED_PANES, encoding="utf-8")
    env = {**os.environ, "QT_QPA_PLATFORM": os.environ.get("QT_QPA_PLATFORM", "offscreen")}
    env["QT_SCALE_FACTOR"] = "2"
    done = subprocess.run(  # noqa: S603  # this interpreter, on a script the test wrote
        [sys.executable, str(script)],
        capture_output=True,
        text=True,
        timeout=60,
        env=env,
        check=False,
    )
    assert done.returncode == 0, done.stderr
    for ratio, measured_pixels, covered in json.loads(done.stdout.splitlines()[-1]):
        assert ratio == 2
        assert measured_pixels == covered, "every device pixel under the pane"


def test_the_fills_are_chosen_before_the_cards_first_paint() -> None:
    """Measuring the art chooses the panes' fills, so the first paint doesn't wait on it.

    ``show()`` lays the card out, and so measures its art; it paints only later.
    """
    from caddcalc.gui.icons import current_scheme

    welcome = screen()
    welcome.show()
    for pane in (welcome.title, welcome.art.version_pane):
        assert current_scheme() in pane._fills, pane.accessibleName()
    welcome.close()


def test_the_built_in_art_keeps_the_title_quiet() -> None:
    """The built-in art is light: both panes are ink on white, the title's at the floor.

    So the title shows the logo in black, the normal one. The version sits over the
    shield's rim, so its fill rises to read.
    """
    import math

    from caddcalc.gui.icons import current_scheme

    floor = math.ceil(style().panes.fill_opacity_min * 255)
    welcome = screen()
    welcome.show()
    for pane in (welcome.title, welcome.art.version_pane):
        text_role, fill_role, alpha = pane.fill(current_scheme())
        assert (text_role, fill_role) == ("welcome_ink", "welcome_paper")
        assert alpha >= floor, pane.accessibleName()
    assert welcome.title.fill(current_scheme())[2] == floor
    assert welcome.title.shown_logo(current_scheme()) == "normal"
    welcome.close()


VERSIONS = ["0.1.0.dev0", "0.1.0a1", "0.1.0", "0.1.0a10", "1.0.0", "10.12.3rc2"]
"""Versions whose lines differ in width: a near-tie under the text once tipped between
them (ADR-0016, amendments)."""


@pytest.mark.parametrize("version", VERSIONS)
def test_the_version_panes_look_doesnt_change_with_the_version(
    monkeypatch: pytest.MonkeyPatch, version: str
) -> None:
    """Its pair is chosen over its safe area, so every version looks alike, and reads."""
    from caddcalc.gui import welcome as module
    from caddcalc.gui.welcome_style import pane_pairs, pane_reads

    panes = style().panes
    monkeypatch.setattr(module, "__version__", VERSIONS[0])
    reference = screen()
    reference.show()
    expected = {s: reference.art.version_pane.fill(s) for s in ("light", "dark")}
    reference.close()
    monkeypatch.setattr(module, "__version__", version)
    welcome = screen()
    welcome.show()
    pane = welcome.art.version_pane
    assert pane.text == f"Version {version}"
    for scheme in ("light", "dark"):
        text_role, fill_role, alpha = pane.fill(scheme)
        assert (text_role, fill_role, alpha) == expected[scheme], scheme
        assert (text_role, fill_role) == ("welcome_ink", "welcome_paper"), scheme
        text, fill = pane_pairs(panes, scheme)[panes.text_roles.index(text_role)]
        needed = pane.tokens.min_contrast
        assert pane_reads(pane.art, text, fill, alpha, panes, needed), "the contrast rule holds"
    welcome.close()


@pytest.mark.parametrize(
    ("logo", "shape"), [(LOGO_SVG, "tall"), (SQUARE_LOGO_SVG, "square"), (WIDE_LOGO_SVG, "wide")]
)
def test_the_logo_box_floats_over_the_arts_left_edge(tmp_path: Path, logo: str, shape: str) -> None:
    from caddcalc.gui.welcome_layout import scaled

    tokens = style()
    welcome = screen(pack(tmp_path / "pack", logo=logo))
    welcome.show()  # placed once it has its size
    scale = welcome.art.width() / tokens.art.slot.width  # the card fits its screen
    box, area = welcome.logo.geometry(), scaled(tokens.logo_area, scale)
    least = tokens.logo.min_short_side * scale
    assert welcome.logo.parentWidget() is welcome.art, "over the art, not beside it"
    assert box.left() >= round(area.x) and box.right() < round(area.x + area.width)
    assert box.top() >= round(area.y) and box.bottom() < round(area.y + area.height)
    assert min(box.width(), box.height()) >= round(least)
    centre = area.y + area.height / 2
    assert abs(box.top() + box.height() / 2 - centre) <= 1, "centred vertically"
    if shape == "tall":
        assert box.height() == round(tokens.logo.max_long_side * scale), "capped"
    elif shape == "square":
        assert box.width() == box.height(), "a square mark keeps its shape"
    else:
        assert box.height() == round(least), "a wordmark gets the least short side"
    welcome.close()


def test_the_card_has_rounded_corners_a_border_and_a_separator() -> None:
    from PySide6.QtCore import Qt

    from caddcalc.gui.icons import current_scheme, role_color

    tokens, scheme = style(), current_scheme()
    welcome = screen()
    assert welcome.rounded, "the offscreen platform composites"
    assert welcome.testAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
    scale = welcome.width() / tokens.window.width
    assert welcome.radius == pytest.approx(tokens.card.corner_radius * scale, abs=0.01)
    welcome.show()
    image = welcome.grab().toImage()
    line = role_color(tokens.card.border_role, scheme)
    middle = welcome.width() // 2
    assert image.pixelColor(middle, 0).name().upper() == line
    assert image.pixelColor(middle, welcome.height() - 1).name().upper() == line
    separator = role_color(tokens.top_bar.separator_role, scheme)
    assert image.pixelColor(middle, welcome.top_bar.height() - 1).name().upper() == separator
    welcome.close()


def test_nothing_shows_outside_the_cards_rounded_outline(tmp_path: Path) -> None:
    """The top bar and busy art are clipped to the one outline; the corners stay clear."""
    welcome = screen(pack(tmp_path / "pack", art="busy"))
    welcome.show()
    image = welcome.grab().toImage()
    right, bottom = welcome.width() - 1, welcome.height() - 1
    for x, y in ((0, 0), (right, 0), (0, bottom), (right, bottom)):
        assert image.pixelColor(x, y).alpha() == 0, (x, y)
    welcome.close()


@pytest.mark.parametrize("ratio", [1, 1.25, 1.5, 2])
def test_lines_are_whole_device_pixels_on_the_pixel_grid(ratio: float) -> None:
    from PySide6.QtCore import QRectF, Qt
    from PySide6.QtGui import QColor, QImage, QPainter

    from caddcalc.gui.painting import stroke
    from caddcalc.gui.welcome_layout import device_line

    width, height = 50, 30
    image = QImage(
        round(width * ratio), round(height * ratio), QImage.Format.Format_ARGB32_Premultiplied
    )
    image.setDevicePixelRatio(ratio)
    image.fill(Qt.GlobalColor.transparent)
    p = QPainter(image)
    stroke(p, QRectF(0, 0, width, height), QColor("#21251F"), 1)
    p.end()
    device = device_line(1, ratio)
    alphas = {
        image.pixelColor(x, y).alpha() for x in range(image.width()) for y in range(image.height())
    }
    assert alphas == {0, 255}, "no part-covered pixels: crisp"
    middle = image.height() // 2
    assert [image.pixelColor(x, middle).alpha() for x in range(device + 1)] == [255] * device + [0]


def display_pane(tokens: Any, parent: Any) -> Any:
    """A pane in the display face, as the retired name pane was, placed at full size."""
    from dataclasses import replace

    from caddcalc.gui.welcome import _Pane
    from caddcalc.gui.welcome_layout import Size

    pane_tokens = replace(
        tokens.version_pane, font="display", font_size=50, padding=(8, 16), min_contrast=3
    )
    pane = _Pane("CADD Calculator", tokens, pane_tokens, parent)
    pane.place(Size(960, 540), 1.0)
    return pane


def test_a_display_pane_is_centred_on_its_capitals() -> None:
    """The padding is the space around the caps: "CADD" sits mid-pane (ADR-0016, amendments)."""
    from PySide6.QtGui import QFontMetricsF
    from PySide6.QtWidgets import QWidget

    parent = QWidget()
    pane = display_pane(style(), parent)
    pane._fills = dict.fromkeys(("light", "dark"), ("welcome_ink", "welcome_paper", 255))
    image = pane.grab().toImage()
    caps = QFontMetricsF(pane.text_font).horizontalAdvance("CADD") / pane.devicePixelRatioF()
    left = (pane.width() - QFontMetricsF(pane.text_font).horizontalAdvance(pane.text)) / 2
    rows = [
        y
        for y in range(1, pane.height() - 1)  # inside the border
        for x in range(round(left), round(left + caps))
        if image.pixelColor(x, y).lightness() < 128  # ink text on a light pane
    ]
    top, bottom = min(rows), pane.height() - 1 - max(rows)
    assert abs(top - bottom) <= 1, (top, bottom)
    band = style().typography.display_cap_height * pane.text_font.pixelSize()
    assert max(rows) - min(rows) + 1 == pytest.approx(band, abs=1), "the caps fill the band"
    parent.deleteLater()


def test_a_display_pane_is_regular_by_default_on_its_pixel_grid() -> None:
    from PySide6.QtGui import QFont
    from PySide6.QtWidgets import QWidget

    from caddcalc.gui.welcome_layout import display_pixels

    tokens = style()
    parent = QWidget()
    pane = display_pane(tokens, parent)
    assert tokens.typography.display_weight == "regular"
    assert pane.text_font.weight() == QFont.Weight.Normal
    grid = display_pixels(50, 1.0, pane.devicePixelRatioF(), 25)
    assert pane.text_font.pixelSize() == 25 * grid, "a whole multiple of the 25-pixel em"
    parent.deleteLater()


def test_a_bold_display_pane_sizes_itself_from_the_bold_run() -> None:
    """Bold widens each platform's run differently, so the pane measures the bold font."""
    from dataclasses import replace

    from PySide6.QtGui import QFont, QFontMetricsF
    from PySide6.QtWidgets import QWidget

    tokens = style()
    bold = replace(tokens, typography=replace(tokens.typography, display_weight="bold"))
    parent = QWidget()
    widths = {}
    for name, style_ in (("regular", tokens), ("bold", bold)):
        pane = display_pane(style_, parent)
        run = QFontMetricsF(pane.text_font).horizontalAdvance(pane.text)
        assert pane.width() >= run / pane.devicePixelRatioF() + 2 * pane.tokens.padding[1]
        widths[name] = (pane.width(), pane.text_font.weight())
    assert widths["bold"][1] == QFont.Weight.Bold and widths["regular"][1] == QFont.Weight.Normal
    assert widths["bold"][0] >= widths["regular"][0]
    parent.deleteLater()


def test_without_a_compositor_the_card_is_square(monkeypatch: pytest.MonkeyPatch) -> None:
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QGuiApplication

    from caddcalc.gui import welcome as module

    for platform, rounded in (
        ("xcb", False),
        ("eglfs", False),
        ("windows", True),
        ("wayland-egl", True),
    ):
        monkeypatch.setattr(QGuiApplication, "platformName", staticmethod(lambda p=platform: p))
        assert module.can_round_corners() is rounded, platform
    monkeypatch.setattr(QGuiApplication, "platformName", staticmethod(lambda: "xcb"))
    welcome = screen()
    assert not welcome.rounded and welcome.radius == 0
    assert not welcome.testAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
    welcome.show()
    assert welcome.grab().toImage().pixelColor(0, 0).alpha() == 255, "square, opaque"
    welcome.close()


def test_a_packs_style_overrides_reach_the_screen(tmp_path: Path) -> None:
    import math

    from caddcalc.gui.icons import current_scheme

    branding = pack(tmp_path / "pack", art="light")
    assert branding.source is not None
    toml = branding.source / "branding.toml"
    overrides = (
        "[welcome.style.logo]\nmargin_left = 32\n[welcome.style.panes]\nfill_opacity_min = 0.4\n"
    )
    toml.write_text(toml.read_text(encoding="utf-8") + overrides, encoding="utf-8")
    welcome = screen(load_branding(branding.source))
    welcome.show()
    scale = welcome.art.width() / style().art.slot.width
    assert welcome.logo.x() >= round(32 * scale), "the pack's margin"
    _text, _fill, alpha = welcome.title.fill(current_scheme())
    assert alpha == math.ceil(0.4 * 255), "calm art: the pack's floor, not the shipped one"
    welcome.close()


def _colour_near(image: Any, x: float, y: float) -> tuple[int, int, int]:
    colour = image.pixelColor(round(x), round(y))
    return colour.red(), colour.green(), colour.blue()


@pytest.mark.parametrize("scheme", ["light", "dark"])
@pytest.mark.parametrize("art", ["built-in", "dark"])
def test_the_title_is_the_projects_logo_upright_with_its_name(
    scheme: str, art: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The symbol and the wordmark, upright, at the top right, read as "CADD Calculator".

    The logo's file holds its clear space, so the pane is the logo, ``title_pane.height``
    tall, inside its safe area. Over the built-in art, which is light, it's the logo in
    black; over dark art, the reversed one, in white. Either way the C's upper arm is at
    the top of the symbol, and the crimson set-square at its lower left (ADR-0015,
    amendments).
    """
    import math

    from caddcalc.gui import welcome as module
    from caddcalc.gui.welcome_layout import scaled

    monkeypatch.setattr(module, "current_scheme", lambda: scheme)
    tokens = style()
    welcome = screen(GENERIC if art == "built-in" else pack(tmp_path / "pack", art=art, logo=None))
    welcome.show()
    title = welcome.title
    scale = welcome.art.width() / tokens.art.slot.width
    assert title.isVisible() and title.accessibleName() == PRODUCT_NAME
    assert title.parentWidget() is welcome.art, "over the art"
    height = round(tokens.title_pane.height * scale)
    logo = title.logo_size
    assert (title.width(), title.height()) == (math.ceil(height * logo.width / logo.height), height)
    assert logo.width > 4 * logo.height, "the horizontal logo, upright"
    area = scaled(tokens.safe_area(tokens.title_pane), scale)
    inset = round(tokens.title_pane.inset * scale)
    assert title.y() == inset and welcome.art.width() - title.x() - title.width() == inset
    assert title.x() >= math.floor(area.x) and title.height() <= math.ceil(area.height)
    assert title.width() <= math.ceil(area.width), "the logo fits its safe area's width"
    shown = title.shown_logo(scheme)
    assert shown == {"built-in": "normal", "dark": "reversed"}[art]
    image = title.grab().toImage()
    x, y = title.width() / logo.width, title.height() / logo.height  # logo units to pixels
    arm = _colour_near(image, 220 * x, 72 * y)
    square = _colour_near(image, 62 * x, 282 * y)
    if shown == "reversed":
        assert min(arm) >= 240, ("the C's upper arm is white, at the top", arm)
    else:
        assert max(arm) <= 40, ("the C's upper arm is black, at the top", arm)
    assert square[0] > 120 and max(square[1:]) < 80, ("the crimson set-square, lower left", square)
    welcome.close()


def test_the_titles_white_parts_are_the_panes_light_text() -> None:
    """The contrast the pane guarantees is for its text role, so the logo's white is it."""
    from caddcalc.gui.branding import TITLE_LOGO, TITLE_LOGO_REVERSED
    from caddcalc.gui.icons import role_color

    panes = style().panes
    reversed_ = TITLE_LOGO_REVERSED.read_text(encoding="utf-8")
    normal = TITLE_LOGO.read_text(encoding="utf-8")
    for scheme in ("light", "dark"):
        light, dark = (
            role_color(panes.text_roles[1], scheme),
            role_color(panes.text_roles[0], scheme),
        )
        assert light == "#FFFFFF" and f'fill="{light}"' in reversed_, scheme
        # The black C reads at least as well as the pane's dark text, which is lighter.
        assert 'fill="#000000"' in normal and dark != "#FFFFFF"


def test_without_an_organization_logo_the_strip_collapses() -> None:
    """No box and no white: the art shows where the strip would be (ADR-0015, amendments)."""
    from PySide6.QtGui import QImage

    tokens = style()
    welcome = screen()
    welcome.show()
    assert welcome.organization_source == "none" and not welcome.logo.isVisible()
    scale = welcome.art.width() / tokens.art.slot.width
    region = tokens.logo_region
    strip = (round(region.width * scale), welcome.art.height())
    shown = welcome.art.grab().toImage().convertToFormat(QImage.Format.Format_RGB32)
    art = welcome.art.shown_art().convertToFormat(QImage.Format.Format_RGB32)
    ratio = shown.devicePixelRatio()
    border = round(2 * ratio)  # the card's clipped outline
    differ = [
        (px, py)
        for px in range(border, round(strip[0] * ratio), 3)
        for py in range(border, round(strip[1] * ratio) - border, 3)
        if shown.pixel(px, py) != art.pixel(px, py)
    ]
    assert differ == [], "the art, uncovered"
    welcome.close()


def test_a_packs_product_logo_replaces_the_title(tmp_path: Path) -> None:
    """A modified build shows its own logo, boxed, never the project's (TRADEMARKS.md)."""
    from caddcalc.gui.icons import current_scheme, role_color

    tokens = style()
    welcome = screen(pack(tmp_path / "pack", logo=None, product=FORK_LOGO_SVG))
    welcome.show()
    title = welcome.title
    scale = welcome.art.width() / tokens.art.slot.width
    assert (welcome.title_source, welcome.organization_source) == ("pack", "none")
    assert title.isVisible() and title.accessibleName() == PRODUCT_NAME
    assert title.height() == round(tokens.title_pane.height * scale)
    assert title.width() <= round(tokens.title_pane.safe_area.width * scale)
    assert title.shown_logo(current_scheme()) == "pack"
    image = title.grab().toImage()
    colours = {
        image.pixelColor(x, y).name().upper()
        for x in range(title.width())
        for y in range(title.height())
    }
    assert "#2E7D32" in colours, "the pack's logo"
    assert role_color(tokens.logo.fill_role, current_scheme()) in colours, "in a logo box"
    assert "#A31D31" not in colours, "nothing of the project's logo"
    welcome.close()


def test_a_product_logo_that_cant_be_read_leaves_no_title(tmp_path: Path) -> None:
    """Rather than show the project's logo on a modified build."""
    branding = pack(tmp_path / "pack", logo=None, product=FORK_LOGO_SVG)
    assert branding.product_logo is not None
    branding.product_logo.write_text("<notsvg/>", encoding="utf-8")
    with pytest.warns(UserWarning, match="Ignoring the product logo fork.svg: invalid SVG"):
        welcome = screen(branding)
    welcome.show()
    assert welcome.title_source == "none" and not welcome.title.isVisible()
    image = welcome.title.grab().toImage()  # painted on demand, visible or not
    colours = {
        image.pixelColor(x, y).name().upper()
        for x in range(image.width())
        for y in range(image.height())
    }
    assert "#A31D31" not in colours, "never the project's logo on a modified build"
    welcome.close()


def test_transparent_art_is_measured_over_the_cards_background(tmp_path: Path) -> None:
    """Where the art is transparent the card's background shows, so that's what's measured."""
    from caddcalc.gui.icons import current_scheme, role_color
    from caddcalc.gui.welcome_style import rgb

    welcome = screen(pack(tmp_path / "pack", art="transparent"))
    welcome.show()
    background = rgb(role_color("background", current_scheme()))
    for pane, needed in ((welcome.title, 3), (welcome.art.version_pane, 4.5)):
        assert set(pane.art) == {background}, pane.accessibleName()
        reading, _spread = measured(welcome, pane)
        assert reading >= needed, pane.accessibleName()
    welcome.close()
