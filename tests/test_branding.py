"""The optional branding hook (ADR-0008 item 4, ADR-0009) and the build script's guards."""

from __future__ import annotations

import ast
import importlib
import json
import shutil
import sys
from html import escape
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

from caddcalc.calculators import REFERENCE_TABLES
from caddcalc.core.formatting import POINT
from caddcalc.gui import branding as branding_module
from caddcalc.gui.app import _split_smoke_test
from caddcalc.gui.branding import (
    ENV_VAR,
    GENERIC,
    GENERIC_ICON,
    PACK_DIR_NAME,
    PRODUCT_NAME,
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
    (folder / "logo-vertical.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="72" height="540"/>', encoding="utf-8"
    )
    (folder / "about.html").write_text("<p>Made for <b>testing</b>.</p>\n", encoding="utf-8")
    return folder


# --- the generic default ----------------------------------------------------------------


def test_generic_branding_is_the_unbranded_public_build() -> None:
    assert GENERIC.is_generic
    assert PRODUCT_NAME == "CADD Calculator"
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
    assert b.edition == "test-edition"
    assert b.icon == pack / "icon.png"
    assert b.welcome_art == pack / "welcome-art.png"
    assert b.welcome_focus == (0.35, 0.5)
    assert b.welcome_logo == pack / "logo-vertical.svg"
    assert set(b.files) >= {b.welcome_art, b.welcome_logo}, "the build stages them"
    assert b.about_html == "<p>Made for <b>testing</b>.</p>"


def test_a_pack_may_restyle_its_welcome_screen_within_the_whitelist(tmp_path: Path) -> None:
    from caddcalc.gui.welcome_style import style

    toml = (
        'edition = "styled"\n'
        "[welcome.style.logo]\n"
        'fill_role = "welcome_paper"\n'
        "margin_left = 24\n"
        "[welcome.style.panes]\n"
        "fill_opacity_min = 0.4\n"
    )
    tokens = load_branding(make_pack(tmp_path / "pack", toml)).welcome_tokens
    assert (tokens.logo.fill_role, tokens.logo.margin_left) == ("welcome_paper", 24)
    assert tokens.panes.fill_opacity_min == 0.4
    assert GENERIC.welcome_style is None and GENERIC.welcome_tokens is style()


def test_optional_files_fall_back_to_generic(tmp_path: Path) -> None:
    pack = make_pack(tmp_path / "pack", 'edition = "minimal"\n')
    b = load_branding(pack)
    assert b.icon == GENERIC_ICON
    assert (b.welcome_art, b.welcome_focus, b.welcome_logo) == (None, (0.5, 0.5), None)
    assert b.about_html is None


def test_plain_text_about_is_escaped_into_paragraphs(tmp_path: Path) -> None:
    pack = make_pack(tmp_path / "pack", 'edition = "txt"\nabout = "about.txt"\n')
    (pack / "about.txt").write_text("Tom & Jerry <3\n\nSecond paragraph.\n", encoding="utf-8")
    assert load_branding(pack).about_html == (
        "<p>Tom &amp; Jerry &lt;3</p><p>Second paragraph.</p>"
    )


@pytest.mark.parametrize(
    ("toml", "message"),
    [
        ('edition = "x"\nsplsh = "s.png"\n', "unknown key"),
        ('schema = 2\nedition = "x"\n', "schema 2"),
        ('name = "X"\n', "'name' was removed: every edition is called 'CADD Calculator'"),
        ('edition = "x"\nname = "   "\n', r"'name' was removed.*ADR-0016, S4"),
        ('icon = "icon.png"\n', "'edition' must be a non-empty string"),
        ('edition = "Example"\n', "lowercase"),
        ('edition = "generic"\n', "not 'generic'"),
        ('edition = "x"\nicon = "missing.png"\n', "does not exist"),
        ('edition = "x"\nicon = "icon.bmp"\n', "must be one of"),
        ('edition = "x"\nicon = "../outside.png"\n', "inside the pack folder"),
        ('edition = "x"\nicon = 3\n', "must be a file name"),
        ("edition = \n", "branding.toml"),
        ('edition = "x"\nsplash = "s.png"\n', r"replaced by the \[welcome\] table"),
        ('edition = "x"\nwelcome = "art.png"\n', "must be a table"),
        (
            'edition = "x"\n[welcome]\nart_fokus = [0.5, 0.5]\n',
            r"unknown \[welcome\] key",
        ),
        (
            'edition = "x"\n[welcome]\nart = "welcome-art.gif"\n',
            "must be one of .jpeg, .jpg, .png",
        ),
        ('edition = "x"\n[welcome]\nlogo = "logo.jpg"\n', "must be one of .png, .svg"),
        ('edition = "x"\n[welcome]\nart = "missing.png"\n', "does not exist"),
        (
            'edition = "x"\n[welcome]\nart = "../outside.png"\n',
            "inside the pack folder",
        ),
        (
            'edition = "x"\n[welcome]\nart_focus = [0.5, 1.5]\n',
            "two numbers from 0 to 1",
        ),
        ('edition = "x"\n[welcome]\nart_focus = [0.5]\n', "two numbers from 0 to 1"),
        (
            'edition = "x"\n[welcome]\nart_focus = [true, 0.5]\n',
            "two numbers from 0 to 1",
        ),
        ('edition = "x"\n[welcome]\nart_focus = "centre"\n', "two numbers from 0 to 1"),
        (
            'edition = "x"\n[welcome.style.card]\ncorner_radius = 0\n',
            r"welcome\.style: a pack may override only .*, not 'card'",
        ),
        ('edition = "x"\n[welcome]\nstyle = 3\n', r"must be a table, \[welcome\.style\]"),
        (
            'edition = "x"\n[welcome.style.panes]\nfill_roles = ["welcome_line", "welcome_line"]\n',
            "no pane text reaches",
        ),
    ],
)
def test_invalid_packs_are_rejected_with_a_reason(tmp_path: Path, toml: str, message: str) -> None:
    pack = make_pack(tmp_path / "pack", toml)
    (tmp_path / "outside.png").write_bytes(b"x")
    (pack / "icon.bmp").write_bytes(b"x")
    with pytest.raises(BrandingError, match=message):
        load_branding(pack)


def test_welcome_files_over_the_byte_budget_are_refused(tmp_path: Path) -> None:
    from caddcalc.gui.welcome_style import style

    pack = make_pack(tmp_path / "pack")
    with (pack / "welcome-art.png").open("r+b") as art:
        art.truncate(style().art.max_bytes + 1)
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
    pack = make_pack(tmp_path / "pack", 'edition = "x"\nname = "An Old Name"\n')
    with pytest.warns(UserWarning, match="Ignoring branding pack: .*'name' was removed"):
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
def test_build_checks_the_display_face_and_its_license_are_bundled(
    build_script: ModuleType, tmp_path: Path
) -> None:
    vendored = ROOT / "src" / "caddcalc" / "gui" / "assets" / "fonts" / "vt323"
    assert build_script.missing_fonts(tmp_path) == [
        "fonts/vt323/OFL.txt",
        "fonts/vt323/VT323-Regular.ttf",
    ]
    shipped = tmp_path / "caddcalc" / "gui" / "assets" / "fonts" / "vt323"
    shutil.copytree(vendored, shipped)
    assert build_script.missing_fonts(tmp_path) == []


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
    from caddcalc.gui.welcome_style import style

    scale = style().art.supplied_scale
    template = importlib.import_module("make_welcome_template")
    image = template.draw_template()
    assert (image.width(), image.height()) == (1920, 1080)
    background = image.pixelColor(1010, 610).name()  # clear of every area and line
    for area, _label in template.safe_areas():
        inside = image.pixelColor(int((area.x + 4) * scale), int((area.y + 4) * scale))
        assert inside.name() != background, "the safe area is marked"


@pytest.mark.gui
def test_window_shows_the_brand_and_keeps_the_disclaimer(qt: Any, tmp_path: Path) -> None:
    from caddcalc.core.formatting import DISCLAIMER
    from caddcalc.gui.actions import GENERIC_ABOUT, about_html
    from caddcalc.gui.window import MainWindow

    app = qt.QApplication.instance()
    b = load_branding(make_pack(tmp_path / "pack"))
    window = MainWindow(branding=b, symbols=POINT)
    assert window.windowTitle() == PRODUCT_NAME, "one name in every edition (ADR-0016, S4)"
    html = about_html(b)
    assert (
        f"<h3>{PRODUCT_NAME} " in html and "<b>testing</b>" in html and escape(DISCLAIMER) in html
    )
    assert GENERIC_ABOUT not in html
    assert GENERIC_ABOUT in about_html(GENERIC)
    assert "Licensed under the Apache License, Version 2.0" in html, "always shown"
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
    (pack / "logo-vertical.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="72" height="540"/>', encoding="utf-8"
    )
    monkeypatch.setenv(ENV_VAR, str(pack))
    report_dir = tmp_path / "report"
    try:
        assert main([f"--smoke-test={report_dir}"]) == 0
    finally:
        app.setApplicationDisplayName("")
    report = json.loads((report_dir / "smoke-test.json").read_text(encoding="utf-8"))
    assert report["name"] == PRODUCT_NAME
    assert report["edition"] == "test-edition"
    assert report["window_title"] == report["name"]
    assert report["icon_loaded"] and report["about_custom"]
    assert "splash_shown" not in report, "the welcome screen replaced it (ADR-0015)"
    assert (report["welcome_shown"], report["welcome_art"], report["welcome_logo"]) == (
        True,
        "pack",
        "pack",
    )
    assert not report["packaged"]
    assert report["reference_tables"] == len(REFERENCE_TABLES) == 2, "gauges and materials"
    assert (report_dir / "window.png").stat().st_size > 0
    from caddcalc.core import i18n

    assert report["catalogs"] == list(i18n.shipped_languages())
    assert report["qt_catalog"] is True, "Qt finds its own catalogs"


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


@pytest.mark.gui
def test_startup_shows_the_generic_welcome_screen_and_leaves_no_window(
    qt: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from PySide6.QtCore import QEvent

    from caddcalc.gui.app import main
    from caddcalc.gui.welcome import WelcomeScreen
    from caddcalc.gui.window import MainWindow

    monkeypatch.delenv(ENV_VAR, raising=False)
    app = qt.QApplication.instance()
    try:
        assert main([f"--smoke-test={tmp_path}"]) == 0
    finally:
        app.setApplicationDisplayName("")
    report = json.loads((tmp_path / "smoke-test.json").read_text(encoding="utf-8"))
    assert (report["welcome_shown"], report["welcome_art"], report["welcome_logo"]) == (
        True,
        "generic",
        "generic",
    )
    assert report["display_font"] == "VT323", "the vendored face loaded (ADR-0016 §2)"
    app.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    left = [w for w in app.topLevelWidgets() if isinstance(w, MainWindow | WelcomeScreen)]
    assert left == [], "main() disposes of its windows (KI-019)"
    assert app.quitOnLastWindowClosed(), "restored once the main window shows"


@pytest.mark.parametrize(
    "href",
    ['xlink:href="../outside.png"', 'href="file:///etc/passwd"', 'xlink:href="other.svg#logo"'],
)
def test_an_svg_logo_must_not_refer_to_other_files(tmp_path: Path, href: str) -> None:
    pack = make_pack(tmp_path / "pack")
    (pack / "logo-vertical.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink">'
        f'<image {href} width="72" height="72"/></svg>',
        encoding="utf-8",
    )
    with pytest.raises(BrandingError, match="must be self-contained"):
        load_branding(pack)


def test_an_svg_logo_may_embed_data_and_refer_within_itself(tmp_path: Path) -> None:
    pack = make_pack(tmp_path / "pack")
    (pack / "logo-vertical.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink">'
        '<defs><rect id="bar" width="72" height="8"/></defs>'
        '<image href="data:image/png;base64,iVBORw0KGgo=" width="72" height="72"/>'
        '<use xlink:href="#bar"/></svg>',
        encoding="utf-8",
    )
    assert load_branding(pack).welcome_logo == pack / "logo-vertical.svg"


def test_a_logo_that_isnt_xml_is_refused(tmp_path: Path) -> None:
    pack = make_pack(tmp_path / "pack")
    (pack / "logo-vertical.svg").write_text("<svg", encoding="utf-8")
    with pytest.raises(BrandingError, match="isn't valid SVG"):
        load_branding(pack)


def test_a_folder_named_like_the_art_is_not_a_file(tmp_path: Path) -> None:
    pack = make_pack(tmp_path / "pack")
    (pack / "welcome-art.png").unlink()
    (pack / "welcome-art.png").mkdir()
    with pytest.raises(BrandingError, match=r"'welcome-art\.png' is not a file"):
        load_branding(pack)


FAILING_STARTUP = """
import os
import sys
from PySide6.QtWidgets import QMessageBox
import caddcalc.gui.window as window
from caddcalc.gui.app import main

def broken(*args, **kwargs):
    raise RuntimeError("probe: the main window can't be built")

setattr(window.MainWindow, os.environ["PROBE_BREAKS"], broken)
QMessageBox.critical = lambda *args, **kwargs: print("critical shown", file=sys.stderr)
raise SystemExit(main(sys.argv[1:]))
"""


@pytest.mark.gui
@pytest.mark.parametrize("part", ["build", "__init__"], ids=["its build", "its shell"])
@pytest.mark.parametrize("args", [[], ["--smoke-test"]], ids=["running", "smoke test"])
def test_a_failed_startup_ends_the_app_with_status_1(
    tmp_path: Path, args: list[str], part: str
) -> None:
    """Run apart, under a timeout, so a regression can't hang the suite.

    The main window fails as it's built, or before, as its shell is made for the card
    to be owned by: either way the app says so, and ends with status 1.
    """
    import os
    import subprocess

    pytest.importorskip("PySide6.QtWidgets")
    script = tmp_path / "failing_startup.py"
    script.write_text(FAILING_STARTUP, encoding="utf-8")
    env = {**os.environ, "QT_QPA_PLATFORM": os.environ.get("QT_QPA_PLATFORM", "offscreen")}
    env.pop(ENV_VAR, None)
    env["PROBE_BREAKS"] = part
    done = subprocess.run(  # noqa: S603  # this interpreter, on a script the test wrote
        [sys.executable, str(script), *args],
        capture_output=True,
        text=True,
        timeout=60,
        env=env,
        check=False,
    )
    assert done.returncode == 1, done.stderr
    assert "probe: the main window can't be built" in done.stderr
    assert "couldn't start" in done.stderr or "critical shown" in done.stderr
    if not args:
        assert "critical shown" in done.stderr, "a running app shows the message"


@pytest.mark.gui
def test_build_checks_every_catalog_ours_and_qts_is_bundled(
    build_script: ModuleType, tmp_path: Path
) -> None:
    """ADR-0009's checklist: each language's .mo, and every qtbase_*.qm."""
    missing = build_script.missing_catalogs(tmp_path)
    assert "caddcalc/locale/en_001/LC_MESSAGES/caddcalc.mo" in missing
    assert "caddcalc/locale/en_CA/LC_MESSAGES/caddcalc.mo" in missing
    qt = build_script.qt_catalogs()
    assert qt, "this PySide6 has its qtbase catalogs"
    assert f"PySide6/translations/{qt[0].name}" in missing
    for name in missing:
        (tmp_path / name).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / name).write_bytes(b"")
    assert build_script.missing_catalogs(tmp_path) == []
    [include] = [a for a in build_script.nuitka_args(None) if a.startswith("--include-data-files")]
    assert include.endswith("qtbase_*.qm=PySide6/translations/"), include


@pytest.mark.gui
def test_the_build_fails_with_no_catalog_to_check(
    build_script: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """With no .po, there'd be no list of ours to check the build against."""
    monkeypatch.setattr(build_script, "CATALOGS", tmp_path / "locale")
    with pytest.raises(build_script.BuildError, match="no catalog to check"):
        build_script.missing_catalogs(tmp_path)


@pytest.mark.gui
def test_no_build_ships_the_catalogs_sources(build_script: ModuleType, tmp_path: Path) -> None:
    """The .po and .pot stay in the sdist; the app reads only the .mo."""
    import fnmatch

    args = build_script.nuitka_args(None)
    patterns = [a.partition("=")[2] for a in args if a.startswith("--noinclude-data-files=")]
    assert patterns == ["caddcalc/locale/*.po", "caddcalc/locale/*.pot"]
    files = {
        "caddcalc/locale/caddcalc.pot": False,
        "caddcalc/locale/en_CA/LC_MESSAGES/caddcalc.po": False,
        "caddcalc/locale/en_CA/LC_MESSAGES/caddcalc.mo": True,
    }
    for name, ships in files.items():  # as Nuitka matches them: where each would go
        assert any(fnmatch.fnmatch(name, p) for p in patterns) is not ships, name
    assert build_script.catalog_sources(tmp_path) == []
    for name in files:
        (tmp_path / name).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / name).write_bytes(b"")
    assert build_script.catalog_sources(tmp_path) == [
        "caddcalc/locale/caddcalc.pot",
        "caddcalc/locale/en_CA/LC_MESSAGES/caddcalc.po",
    ]
