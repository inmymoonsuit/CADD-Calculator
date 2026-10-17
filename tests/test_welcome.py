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
from caddcalc.gui.welcome_layout import ART_SIZE, MAX_ART_PX, WINDOW

pytestmark = [pytest.mark.gui, pytest.mark.usefixtures("qt")]

LOGO_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="72" height="540" viewBox="0 0 72 540">'
    '<rect width="72" height="540" fill="#202020"/></svg>'
)


def pack(
    folder: Path, *, art_size: tuple[int, int] = (1920, 1080), logo: str = LOGO_SVG
) -> Branding:
    """A pack with generated welcome art and logo."""
    from PySide6.QtGui import QImage

    folder.mkdir(parents=True, exist_ok=True)
    art = QImage(*art_size, QImage.Format.Format_RGB32)
    art.fill(0xFF336699)
    assert art.save(str(folder / "welcome-art.png"))
    (folder / "logo.svg").write_text(logo, encoding="utf-8")
    (folder / "branding.toml").write_text(
        'edition = "test-edition"\nname = "Test Edition"\n'
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
    assert welcome.art.name_label.text() == "CADD Calculator"
    assert welcome.art.version_label.text() == f"Version {__version__}"
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
    assert welcome.art.version_label.text() == f"Version {__version__}", "no edition slug"
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


def test_an_invalid_logo_falls_back_to_the_icon_and_name(tmp_path: Path) -> None:
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
