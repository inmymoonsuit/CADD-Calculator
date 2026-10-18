"""The welcome screen (ADR-0015). Skipped when PySide6 is not installed.

Every image here is generated in the test; no pack art is used (ADR-0015 §3).
"""

from __future__ import annotations

import gc
import weakref
from pathlib import Path
from typing import Any

import pytest

from caddcalc import __version__
from caddcalc.gui.branding import GENERIC, Branding, load_branding
from caddcalc.gui.welcome_layout import Rect
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


def pack(
    folder: Path,
    *,
    art_size: tuple[int, int] = (1920, 1080),
    logo: str = LOGO_SVG,
    art: str = "blue",
) -> Branding:
    """A pack with generated welcome art and logo."""
    folder.mkdir(parents=True, exist_ok=True)
    assert generated_art(art, art_size).save(str(folder / "welcome-art.png"))
    (folder / "logo.svg").write_text(logo, encoding="utf-8")
    (folder / "branding.toml").write_text(
        'edition = "test-edition"\n'
        '[welcome]\nart = "welcome-art.png"\nart_focus = [0.25, 0.5]\nlogo = "logo.svg"\n',
        encoding="utf-8",
    )
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


def test_the_generic_screen_shows_live_name_and_version_over_generated_art() -> None:
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QMenuBar

    welcome = screen()
    assert (welcome.art_source, welcome.logo_source) == ("generic", "generic")
    assert welcome.art.name_pane.text == "CADD Calculator"
    assert welcome.art.version_pane.text == f"Version {__version__}"
    assert welcome.windowModality() is Qt.WindowModality.ApplicationModal
    assert welcome.windowFlags() & Qt.WindowType.FramelessWindowHint
    assert welcome.findChildren(QMenuBar) == [], "the app's menus live in the main window"
    welcome.show()
    image = welcome.grab().toImage()
    assert not image.isNull()
    welcome.close()


def test_a_packs_art_and_logo_are_used(tmp_path: Path) -> None:
    welcome = screen(pack(tmp_path / "pack"))
    assert (welcome.art_source, welcome.logo_source) == ("pack", "pack")
    assert welcome.art.version_pane.text == f"Version {__version__}", "no edition slug"
    welcome.show()
    assert not welcome.grab().toImage().isNull()
    welcome.close()


@pytest.mark.parametrize(
    "spoil",
    ["garbage", "oversized", "deleted"],
)
def test_art_that_cant_be_used_falls_back_to_the_generic_art(tmp_path: Path, spoil: str) -> None:
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


def test_an_invalid_logo_falls_back_to_the_app_icon(tmp_path: Path) -> None:
    """The loader refuses malformed XML; this covers XML that Qt still can't render."""
    from dataclasses import replace

    branding = pack(tmp_path / "pack")
    assert branding.welcome_logo is not None
    branding.welcome_logo.write_text("<notsvg/>", encoding="utf-8")
    with pytest.warns(UserWarning, match="invalid SVG"):
        welcome = screen(replace(branding))
    assert welcome.logo_source == "generic"
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


def test_the_generic_art_is_drawn_at_the_screens_resolution() -> None:
    from PySide6.QtCore import QSize

    from caddcalc.gui.welcome import generic_art

    image = generic_art(QSize(480, 270), 1.5)
    assert (image.width(), image.height(), image.devicePixelRatio()) == (720, 405, 1.5)


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
        QMessageBox, "about", lambda _parent, title, text: shown.append((title, text))
    )
    welcome = screen()
    welcome.show()
    assert welcome.about_button.accessibleName() == "About"
    QTest.mouseClick(welcome.about_button, Qt.MouseButton.LeftButton)
    ((title, text),) = shown
    assert title == "About CADD Calculator"
    assert __version__ in text and "Apache License, Version 2.0" in text
    welcome.close()


# --- the restyle (ADR-0016 §3 to §5) -----------------------------------------------------


def measured(welcome: Any, pane: Any) -> tuple[float, float]:
    """The text's contrast, and the background's spread, over the art as Qt shows it.

    The card is grabbed with the pane hidden, as Qt renders it, so transparent art
    shows the card's background; the pane's fill is blended over it by Qt itself, and
    every pixel under the pane counts, at the style's percentile.
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
    area = QRect(pane.mapTo(welcome, QPoint(0, 0)), pane.size())
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
    for pane, needed in ((welcome.art.name_pane, 3), (welcome.art.version_pane, 4.5)):
        assert pane.tokens.min_contrast == needed, "large text 3:1, the version 4.5:1"
        text_role, fill_role, alpha = pane.fill(current_scheme())
        dark_text = text_role == panes.text_roles[0]
        assert fill_role == panes.fill_roles[0 if dark_text else 1], "each text has its fill"
        if not art.startswith("saturated"):  # how far those rise depends on the blend
            assert (alpha > floor) == raised, (pane.text, alpha)
        assert alpha >= floor
        reading, spread = measured(welcome, pane)
        assert reading >= needed, pane.text
        assert spread <= panes.max_background_spread, (pane.text, spread)
    welcome.close()


def test_the_generic_look_is_unchanged_by_the_calm_rule() -> None:
    """The generic gradient is calm: both panes stay at the floor, white on ink."""
    import math

    from caddcalc.gui.icons import current_scheme

    panes = style().panes
    welcome = screen()
    welcome.show()
    for pane in (welcome.art.name_pane, welcome.art.version_pane):
        text_role, fill_role, alpha = pane.fill(current_scheme())
        assert (text_role, fill_role) == ("welcome_paper", "welcome_ink")
        assert alpha == math.ceil(panes.fill_opacity_min * 255), pane.text
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

    from caddcalc.gui.welcome import stroke
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


def test_the_title_is_centred_on_its_capitals(tmp_path: Path) -> None:
    """The padding is the space around the caps: "CADD" sits mid-pane (ADR-0016, amendments)."""
    from PySide6.QtGui import QFontMetricsF

    welcome = screen(pack(tmp_path / "pack", art="light"))
    welcome.show()
    pane = welcome.art.name_pane
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
    welcome.close()


def test_the_title_is_regular_by_default_on_its_pixel_grid() -> None:
    from PySide6.QtGui import QFont

    from caddcalc.gui.welcome_layout import display_pixels

    tokens = style()
    welcome = screen()
    welcome.show()
    pane = welcome.art.name_pane
    assert tokens.typography.display_weight == "regular"
    assert pane.text_font.weight() == QFont.Weight.Normal
    scale = welcome.art.width() / tokens.art.slot.width
    grid = display_pixels(50, scale, pane.devicePixelRatioF(), 25)
    assert pane.text_font.pixelSize() == 25 * grid, "a whole multiple of the 25-pixel em"
    welcome.close()


def test_a_bold_title_sizes_its_pane_from_the_bold_run() -> None:
    """Bold widens each platform's run differently, so the pane measures the bold font."""
    from dataclasses import replace

    from PySide6.QtGui import QFont, QFontMetricsF
    from PySide6.QtWidgets import QWidget

    from caddcalc.gui.welcome import _Pane
    from caddcalc.gui.welcome_layout import Size

    tokens = style()
    bold = replace(tokens, typography=replace(tokens.typography, display_weight="bold"))
    parent = QWidget()
    widths = {}
    for name, style_ in (("regular", tokens), ("bold", bold)):
        pane = _Pane("CADD Calculator", style_, style_.name_pane, parent)
        pane.place(Size(960, 540), 1.0)
        run = QFontMetricsF(pane.text_font).horizontalAdvance(pane.text)
        assert pane.width() >= run / pane.devicePixelRatioF() + 2 * style_.name_pane.padding[1]
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
    _text, _fill, alpha = welcome.art.name_pane.fill(current_scheme())
    assert alpha == math.ceil(0.4 * 255), "calm art: the pack's floor, not the shipped one"
    welcome.close()


@pytest.mark.parametrize("scheme", ["light", "dark"])
def test_the_generic_mark_is_the_app_icon_alone_in_a_square_box(
    scheme: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No name beside the icon, so nothing can vanish in the dark theme (ADR-0016, h)."""
    from caddcalc.gui import welcome as module
    from caddcalc.gui.icons import role_color
    from caddcalc.gui.welcome_layout import contain_fit

    monkeypatch.setattr(module, "current_scheme", lambda: scheme)
    tokens = style()
    welcome = screen()
    welcome.show()
    box = welcome.logo
    scale = welcome.art.width() / tokens.art.slot.width
    side = round((tokens.logo.region_width - tokens.logo.margin_left) * scale)
    assert welcome.logo_source == "generic"
    assert box.width() == box.height() == side, "80 px at full size: 64 px icon and padding"
    image = box.grab().toImage()
    fill = role_color(tokens.logo.fill_role, scheme)
    inner = tokens.logo.padding * scale
    icon = contain_fit(
        box.logo_size, Rect(inner, inner, box.width() - 2 * inner, box.height() - 2 * inner)
    )
    border = 2
    outside_icon = [
        image.pixelColor(x, y).name().upper()
        for x in range(border, box.width() - border)
        for y in range(border, box.height() - border)
        if not (icon.x - 1 <= x <= icon.x + icon.width and icon.y - 1 <= y <= icon.y + icon.height)
    ]
    assert outside_icon and set(outside_icon) == {fill}, "only the fill around the icon"
    welcome.close()


def test_transparent_art_is_measured_over_the_cards_background(tmp_path: Path) -> None:
    """Where the art is transparent the card's background shows, so that's what's measured."""
    from caddcalc.gui.icons import current_scheme, role_color
    from caddcalc.gui.welcome_style import rgb

    welcome = screen(pack(tmp_path / "pack", art="transparent"))
    welcome.show()
    background = rgb(role_color("background", current_scheme()))
    for pane, needed in ((welcome.art.name_pane, 3), (welcome.art.version_pane, 4.5)):
        assert set(pane.art) == {background}, pane.text
        reading, _spread = measured(welcome, pane)
        assert reading >= needed, pane.text
    welcome.close()
