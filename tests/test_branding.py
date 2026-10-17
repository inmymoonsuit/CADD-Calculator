"""The optional branding hook (ADR-0008 item 4, ADR-0009) and the build script's guards."""

from __future__ import annotations

import ast
import importlib
import json
import sys
from html import escape
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

from caddcalc.calculators import REFERENCE_TABLES
from caddcalc.gui import branding as branding_module
from caddcalc.gui.app import _split_smoke_test
from caddcalc.gui.branding import (
    ENV_VAR,
    GENERIC,
    GENERIC_ICON,
    PACK_DIR_NAME,
    BrandingError,
    active_branding,
    find_pack_dir,
    load_branding,
    packaged_app_dir,
)

ROOT = Path(__file__).resolve().parent.parent

PACK_TOML = """\
schema = 1
edition = "test-edition"
name = "CADD Calculator: Test Edition"
icon = "icon.png"
about = "about.html"

[welcome]
art = "welcome-art.png"
art_focus = [0.35, 0.5]
logo = "logo-vertical.svg"
"""


def make_pack(folder: Path, toml: str = PACK_TOML, *, images: bytes = b"not checked") -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "branding.toml").write_text(toml, encoding="utf-8")
    (folder / "icon.png").write_bytes(images)
    (folder / "welcome-art.png").write_bytes(images)
    (folder / "logo-vertical.svg").write_bytes(images)
    (folder / "about.html").write_text("<p>Made for <b>testing</b>.</p>\n", encoding="utf-8")
    return folder


# --- the generic default ----------------------------------------------------------------


def test_generic_branding_is_the_unbranded_public_build() -> None:
    assert GENERIC.is_generic
    assert GENERIC.name == "CADD Calculator"
    assert GENERIC.edition == "generic"
    assert (GENERIC.welcome_art, GENERIC.welcome_logo) == (None, None)
    assert GENERIC.welcome_focus == (0.5, 0.5)
    assert GENERIC.about_html is None
    assert GENERIC.icon == GENERIC_ICON
    assert GENERIC_ICON.is_file(), "the generic icon ships inside the package"


def test_branding_module_does_not_import_qt() -> None:
    """The build script and these tests load packs without a display."""
    tree = ast.parse(Path(branding_module.__file__).read_text(encoding="utf-8"))
    imported = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    } | {
        node.module.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    }
    assert "PySide6" not in imported


# --- loading a pack ---------------------------------------------------------------------


def test_load_branding_reads_a_complete_pack(tmp_path: Path) -> None:
    pack = make_pack(tmp_path / "pack")
    b = load_branding(pack)
    assert not b.is_generic
    assert b.source == pack
    assert b.name == "CADD Calculator: Test Edition"
    assert b.edition == "test-edition"
    assert b.icon == pack / "icon.png"
    assert b.welcome_art == pack / "welcome-art.png"
    assert b.welcome_focus == (0.35, 0.5)
    assert b.welcome_logo == pack / "logo-vertical.svg"
    assert set(b.files) >= {b.welcome_art, b.welcome_logo}, "the build stages them"
    assert b.about_html == "<p>Made for <b>testing</b>.</p>"


def test_optional_files_fall_back_to_generic(tmp_path: Path) -> None:
    pack = make_pack(tmp_path / "pack", 'edition = "minimal"\nname = "Minimal"\n')
    b = load_branding(pack)
    assert b.icon == GENERIC_ICON
    assert (b.welcome_art, b.welcome_focus, b.welcome_logo) == (None, (0.5, 0.5), None)
    assert b.about_html is None


def test_plain_text_about_is_escaped_into_paragraphs(tmp_path: Path) -> None:
    pack = make_pack(tmp_path / "pack", 'edition = "txt"\nname = "T"\nabout = "about.txt"\n')
    (pack / "about.txt").write_text("Tom & Jerry <3\n\nSecond paragraph.\n", encoding="utf-8")
    assert load_branding(pack).about_html == (
        "<p>Tom &amp; Jerry &lt;3</p><p>Second paragraph.</p>"
    )


@pytest.mark.parametrize(
    ("toml", "message"),
    [
        ('edition = "x"\nname = "X"\nsplsh = "s.png"\n', "unknown key"),
        ('schema = 2\nedition = "x"\nname = "X"\n', "schema 2"),
        ('edition = "x"\n', "'name' must be a non-empty string"),
        ('edition = "x"\nname = "   "\n', "'name' must be a non-empty string"),
        ('edition = "Example"\nname = "X"\n', "lowercase"),
        ('edition = "generic"\nname = "X"\n', "not 'generic'"),
        ('edition = "x"\nname = "X"\nicon = "missing.png"\n', "does not exist"),
        ('edition = "x"\nname = "X"\nicon = "icon.bmp"\n', "must be one of"),
        ('edition = "x"\nname = "X"\nicon = "../outside.png"\n', "inside the pack folder"),
        ('edition = "x"\nname = "X"\nicon = 3\n', "must be a file name"),
        ("edition = \n", "branding.toml"),
        ('edition = "x"\nname = "X"\nsplash = "s.png"\n', r"replaced by the \[welcome\] table"),
        ('edition = "x"\nname = "X"\nwelcome = "art.png"\n', "must be a table"),
        (
            'edition = "x"\nname = "X"\n[welcome]\nart_fokus = [0.5, 0.5]\n',
            r"unknown \[welcome\] key",
        ),
        (
            'edition = "x"\nname = "X"\n[welcome]\nart = "welcome-art.gif"\n',
            "must be one of .jpeg, .jpg, .png",
        ),
        ('edition = "x"\nname = "X"\n[welcome]\nlogo = "logo.jpg"\n', "must be one of .png, .svg"),
        ('edition = "x"\nname = "X"\n[welcome]\nart = "missing.png"\n', "does not exist"),
        (
            'edition = "x"\nname = "X"\n[welcome]\nart = "../outside.png"\n',
            "inside the pack folder",
        ),
        (
            'edition = "x"\nname = "X"\n[welcome]\nart_focus = [0.5, 1.5]\n',
            "two numbers from 0 to 1",
        ),
        ('edition = "x"\nname = "X"\n[welcome]\nart_focus = [0.5]\n', "two numbers from 0 to 1"),
        (
            'edition = "x"\nname = "X"\n[welcome]\nart_focus = [true, 0.5]\n',
            "two numbers from 0 to 1",
        ),
        ('edition = "x"\nname = "X"\n[welcome]\nart_focus = "centre"\n', "two numbers from 0 to 1"),
    ],
)
def test_invalid_packs_are_rejected_with_a_reason(tmp_path: Path, toml: str, message: str) -> None:
    pack = make_pack(tmp_path / "pack", toml)
    (tmp_path / "outside.png").write_bytes(b"x")
    (pack / "icon.bmp").write_bytes(b"x")
    with pytest.raises(BrandingError, match=message):
        load_branding(pack)


def test_welcome_files_over_the_byte_budget_are_refused(tmp_path: Path) -> None:
    from caddcalc.gui.welcome_layout import MAX_ART_BYTES

    pack = make_pack(tmp_path / "pack")
    with (pack / "welcome-art.png").open("r+b") as art:
        art.truncate(MAX_ART_BYTES + 1)
    with pytest.raises(BrandingError, match=r"welcome\.art 'welcome-art\.png' is larger than 8 MB"):
        load_branding(pack)


def test_a_folder_without_branding_toml_is_not_a_pack(tmp_path: Path) -> None:
    with pytest.raises(BrandingError, match="not a branding pack"):
        load_branding(tmp_path)


# --- finding the pack -------------------------------------------------------------------


def test_source_runs_are_not_packaged() -> None:
    assert packaged_app_dir() is None


def test_frozen_apps_look_next_to_the_executable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    assert packaged_app_dir() == Path(sys.executable).resolve().parent


def test_find_pack_dir_prefers_the_environment_variable(tmp_path: Path) -> None:
    app_dir = tmp_path / "app"
    make_pack(app_dir / PACK_DIR_NAME)
    other = make_pack(tmp_path / "other")
    assert find_pack_dir({ENV_VAR: str(other)}, app_dir) == other
    assert find_pack_dir({ENV_VAR: "  "}, app_dir) == app_dir / PACK_DIR_NAME
    assert find_pack_dir({}, app_dir) == app_dir / PACK_DIR_NAME
    assert find_pack_dir({}, tmp_path / "no-pack-here") is None
    assert find_pack_dir({}) is None  # tests run from source, so no app folder


def test_active_branding_falls_back_to_generic_with_a_warning(tmp_path: Path) -> None:
    pack = make_pack(tmp_path / "pack", 'edition = "x"\n')
    with pytest.warns(UserWarning, match="Ignoring branding pack"):
        assert active_branding({ENV_VAR: str(pack)}) is GENERIC
    assert active_branding({}) is GENERIC
    good = make_pack(tmp_path / "good")
    assert active_branding({ENV_VAR: str(good)}).edition == "test-edition"


def test_smoke_test_flag_is_removed_before_qt_sees_the_arguments(tmp_path: Path) -> None:
    assert _split_smoke_test(["-style", "fusion"]) == (["-style", "fusion"], False, None)
    assert _split_smoke_test(["--smoke-test"]) == ([], True, None)
    assert _split_smoke_test([f"--smoke-test={tmp_path}", "-x"]) == (["-x"], True, tmp_path)


# --- the build script's guards (packaging/build.py imports PySide6) ---------------------


@pytest.fixture
def build_script(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    # The qt fixture's full QApplication comes first: the packaging helpers would otherwise
    # create a bare QGuiApplication, and later widget tests can't run on that.
    request.getfixturevalue("qt")
    monkeypatch.syspath_prepend(str(ROOT / "packaging"))
    return importlib.import_module("build")


@pytest.mark.gui
def test_build_never_makes_a_branded_edition_in_ci(
    build_script: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pack = make_pack(tmp_path / "pack")
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    monkeypatch.setenv("CI", "true")
    with pytest.raises(build_script.BuildError, match="never built in CI"):
        build_script.choose_branding(str(pack))
    assert build_script.choose_branding(None) is GENERIC
    monkeypatch.delenv("CI")
    assert build_script.choose_branding(str(pack)).edition == "test-edition"


@pytest.mark.gui
def test_build_finds_named_packs_in_the_branding_folder(
    build_script: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    for var in ("CI", "GITHUB_ACTIONS"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setattr(build_script, "BRANDING_DIR", tmp_path / "branding")
    monkeypatch.chdir(tmp_path)
    make_pack(tmp_path / "branding" / "example")
    assert build_script.resolve_pack("example") == tmp_path / "branding" / "example"
    assert build_script.choose_branding("example").edition == "test-edition"
    with pytest.raises(build_script.BuildError, match="no branding pack at"):
        build_script.choose_branding("missing")
    with pytest.raises(build_script.BuildError, match="no branding pack at"):
        build_script.choose_branding(str(tmp_path))


@pytest.mark.gui
def test_build_stages_only_the_named_files_and_notices(
    build_script: ModuleType, tmp_path: Path
) -> None:
    pack = make_pack(tmp_path / "pack")
    (pack / "ART-NOTICE.md").write_text("Art notice", encoding="utf-8")
    (pack / "LICENSE.txt").write_text("License", encoding="utf-8")
    (pack / "README.md").write_text("Planning notes", encoding="utf-8")
    (pack / "source-render.blend").write_bytes(b"not for shipping")
    staged = tmp_path / "staged"
    build_script.stage_pack(load_branding(pack), staged)
    assert sorted(p.name for p in staged.iterdir()) == [
        "ART-NOTICE.md",
        "LICENSE.txt",
        "about.html",
        "branding.toml",
        "icon.png",
        "logo-vertical.svg",
        "welcome-art.png",
    ]


@pytest.mark.gui
def test_windows_version_resources_get_four_numbers(build_script: ModuleType) -> None:
    assert build_script.numeric_version("0.1.0.dev0") == "0.1.0.0"
    assert build_script.numeric_version("1.2") == "1.2.0.0"
    assert build_script.numeric_version("2.3.4.5.6") == "2.3.4.5"


@pytest.mark.gui
@pytest.mark.usefixtures("build_script")
def test_icon_helpers_write_a_multi_size_ico(tmp_path: Path) -> None:
    gui = pytest.importorskip("PySide6.QtGui")
    icons = importlib.import_module("icons")
    icons.ensure_qt_app()
    icon = tmp_path / "app.ico"
    icons.save_ico(icons.draw_generic_icon(256), icon)
    reader = gui.QImageReader(str(icon))
    assert reader.imageCount() == len(icons.ICO_SIZES)
    assert icons.png_bytes(icons.draw_generic_icon(16)).startswith(b"\x89PNG")


@pytest.mark.gui
@pytest.mark.usefixtures("build_script")
def test_placeholder_pack_is_a_valid_pack(tmp_path: Path) -> None:
    gui = pytest.importorskip("PySide6.QtGui")
    pack = importlib.import_module("make_placeholder_pack").write_pack(tmp_path / "pack")
    b = load_branding(pack)
    assert b.edition == "placeholder"
    art = gui.QImage(str(b.welcome_art))
    assert (art.width(), art.height()) == (1920, 1080), "supplied at 2x, per the art spec"
    svg = pytest.importorskip("PySide6.QtSvg")
    assert svg.QSvgRenderer(str(b.welcome_logo)).isValid()
    assert b.welcome_focus == (0.4, 0.5)
    assert b.icon is not None and not gui.QImage(str(b.icon)).isNull()
    assert "not for distribution" in (b.about_html or "")


# --- the GUI applies the branding -------------------------------------------------------


@pytest.mark.gui
@pytest.mark.usefixtures("build_script")
def test_the_welcome_template_marks_the_safe_areas() -> None:
    from caddcalc.gui.welcome_layout import ART_SCALE, NAME_PANEL, VERSION_LINE

    template = importlib.import_module("make_welcome_template")
    image = template.draw_template()
    assert (image.width(), image.height()) == (1920, 1080)
    background = image.pixelColor(5, 5).name()
    for area in (NAME_PANEL, VERSION_LINE):
        inside = image.pixelColor(int((area.x + 4) * ART_SCALE), int((area.y + 4) * ART_SCALE))
        assert inside.name() != background, "the safe area is marked"


@pytest.mark.gui
def test_window_shows_the_brand_and_keeps_the_disclaimer(qt: Any, tmp_path: Path) -> None:
    from caddcalc.core.formatting import DISCLAIMER
    from caddcalc.gui.window import GENERIC_ABOUT, MainWindow, about_html

    app = qt.QApplication.instance()
    b = load_branding(make_pack(tmp_path / "pack"))
    window = MainWindow(branding=b)
    assert window.windowTitle() == b.name
    html = about_html(b)
    assert b.name in html and "<b>testing</b>" in html and escape(DISCLAIMER) in html
    assert GENERIC_ABOUT not in html
    assert GENERIC_ABOUT in about_html(GENERIC)
    window.close()
    app.processEvents()


@pytest.mark.gui
def test_app_smoke_test_applies_a_pack_from_the_environment(
    qt: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    gui = pytest.importorskip("PySide6.QtGui")
    from caddcalc.gui.app import main

    app = qt.QApplication.instance()
    pack = make_pack(tmp_path / "pack")
    image = gui.QImage(32, 32, gui.QImage.Format.Format_ARGB32)
    image.fill(0xFF1F5F99)
    assert image.save(str(pack / "icon.png"), "PNG")
    assert image.save(str(pack / "welcome-art.png"), "PNG")
    monkeypatch.setenv(ENV_VAR, str(pack))
    report_dir = tmp_path / "report"
    try:
        assert main([f"--smoke-test={report_dir}"]) == 0
    finally:
        app.setApplicationDisplayName("")
    report = json.loads((report_dir / "smoke-test.json").read_text(encoding="utf-8"))
    assert report["name"] == "CADD Calculator: Test Edition"
    assert report["edition"] == "test-edition"
    assert report["window_title"] == report["name"]
    assert report["icon_loaded"] and report["about_custom"]
    assert "splash_shown" not in report, "the splash screen is gone (ADR-0015)"
    assert not report["packaged"]
    assert report["reference_tables"] == len(REFERENCE_TABLES) == 1, "the gauge table"
    assert (report_dir / "window.png").stat().st_size > 0


@pytest.mark.gui
def test_the_entry_point_reads_the_command_line(
    qt: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``caddcalc-gui`` calls ``main()`` with no arguments; it must still see --smoke-test."""
    from caddcalc.gui.app import main

    monkeypatch.delenv(ENV_VAR, raising=False)
    monkeypatch.setattr("sys.argv", ["caddcalc-gui", f"--smoke-test={tmp_path}"])
    try:
        assert main() == 0
    finally:
        qt.QApplication.instance().setApplicationDisplayName("")
    assert (tmp_path / "smoke-test.json").is_file()
