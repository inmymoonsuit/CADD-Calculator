"""The app icon at every size, in each platform's icon file, and in About (brand.md)."""

from __future__ import annotations

import importlib
import json
import struct
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

from caddcalc.gui.branding import BRAND, ENV_VAR, GENERIC, GENERIC_ICON

ROOT = Path(__file__).parents[1]
CRIMSON = 0xFFA31D31

pytestmark = pytest.mark.gui


@pytest.fixture
def icons(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    """The packaging icon helpers, with the qt fixture's application running first."""
    request.getfixturevalue("qt")
    monkeypatch.syspath_prepend(str(ROOT / "packaging"))
    return importlib.import_module("icons")


@pytest.mark.usefixtures("qt")
def test_the_small_sizes_come_from_their_own_drawings() -> None:
    from caddcalc.gui.app_icon import SIZES, source

    assert {size: source(size).name for size in (16, 20, 24, 32, 40, 256)} == {
        16: "app-icon-16.svg",
        20: "app-icon-24.svg",
        24: "app-icon-24.svg",
        32: "app-icon-32.svg",
        40: "app-icon.svg",
        256: "app-icon.svg",
    }
    assert SIZES[0] == 16 and SIZES[-1] == 256
    assert GENERIC_ICON == BRAND / "app-icon.svg" and GENERIC.icon == GENERIC_ICON


@pytest.mark.usefixtures("qt")
def test_the_icon_loads_at_every_size() -> None:
    from caddcalc.gui.app_icon import SIZES, app_icon, image

    icon = app_icon()
    assert not icon.isNull()
    assert sorted({size.width() for size in icon.availableSizes()}) == list(SIZES)
    for size in SIZES:
        drawn = image(size)
        assert (drawn.width(), drawn.height()) == (size, size)
        assert drawn.pixel(size // 2, 1) == CRIMSON, "the tile's crimson, at its top edge"
        assert drawn.pixelColor(0, 0).alpha() < 255, "a rounded corner"


@pytest.mark.usefixtures("qt")
def test_a_packs_icon_is_its_own_file(tmp_path: Path) -> None:
    from PySide6.QtGui import QImage

    from caddcalc.gui.app_icon import window_icon

    png = tmp_path / "icon.png"
    picture = QImage(48, 48, QImage.Format.Format_ARGB32)
    picture.fill(0xFF1F5F99)
    assert picture.save(str(png), "PNG")
    assert [s.width() for s in window_icon(png).availableSizes()] == [48]
    assert len(window_icon(GENERIC_ICON).availableSizes()) > 1


def test_the_ico_holds_every_size_with_the_small_drawings(
    icons: ModuleType, tmp_path: Path
) -> None:
    from PySide6.QtGui import QImage, QImageReader

    from caddcalc.gui.app_icon import image

    ico = tmp_path / "app.ico"
    icons.save_ico(icons.images(GENERIC_ICON, icons.ICO_SIZES), ico)
    reader = QImageReader(str(ico))
    sizes = []
    for index in range(reader.imageCount()):
        assert reader.jumpToImage(index)
        sizes.append(reader.read().width())
    assert sorted(sizes) == sorted(icons.ICO_SIZES)
    assert 16 in sizes and 256 in sizes
    # The 16 px entry is the drawing made for 16 px, pixel for pixel, not the master shrunk.
    data = ico.read_bytes()
    count = struct.unpack_from("<H", data, 4)[0]
    for entry in range(count):
        side, _, _, _, _, _, length, offset = struct.unpack_from("<BBBBHHII", data, 6 + 16 * entry)
        if side == 16:
            stored = QImage.fromData(data[offset : offset + length])
            expected = image(16).convertToFormat(stored.format())
            assert stored == expected


def test_the_icns_holds_every_macos_size(icons: ModuleType, tmp_path: Path) -> None:
    from PySide6.QtGui import QImage

    icns = tmp_path / "app.icns"
    icons.save_icns(icons.images(GENERIC_ICON, tuple(sorted(set(icons.ICNS_TYPES.values())))), icns)
    data = icns.read_bytes()
    assert data[:4] == b"icns" and struct.unpack_from(">I", data, 4)[0] == len(data)
    found, at = {}, 8
    while at < len(data):
        kind, length = data[at : at + 4].decode("ascii"), struct.unpack_from(">I", data, at + 4)[0]
        png = QImage.fromData(data[at + 8 : at + length])
        found[kind] = png.width()
        at += length
    assert found == icons.ICNS_TYPES


@pytest.mark.usefixtures("qt")
def test_the_build_writes_the_platforms_icon_file(tmp_path: Path) -> None:
    import sys

    sys.path.insert(0, str(ROOT / "packaging"))
    try:
        build = importlib.import_module("build")
        out = build.exe_icon(GENERIC, tmp_path)
    finally:
        sys.path.remove(str(ROOT / "packaging"))
    assert out.is_file() and out.stat().st_size > 0
    if sys.platform == "win32":
        assert out.suffix == ".ico"
    elif sys.platform == "darwin":
        assert out.suffix == ".icns"


def test_about_shows_the_app_icon(qt: Any) -> None:
    from caddcalc.gui.actions import ABOUT_ICON, AppActions
    from caddcalc.gui.app_icon import app_icon

    app = qt.QApplication.instance()
    app.setWindowIcon(app_icon())
    box = AppActions(GENERIC).about_box(None)
    pixmap = box.iconPixmap()
    assert not pixmap.isNull()
    assert round(pixmap.width() / pixmap.devicePixelRatio()) == ABOUT_ICON
    assert pixmap.toImage().pixel(ABOUT_ICON // 2, 1) == CRIMSON
    box.deleteLater()


def test_the_smoke_report_shows_every_size_loaded(
    qt: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from caddcalc.gui.app import main
    from caddcalc.gui.app_icon import SIZES

    app = qt.QApplication.instance()
    monkeypatch.delenv(ENV_VAR, raising=False)
    report_dir = tmp_path / "report"
    try:
        assert main([f"--smoke-test={report_dir}"]) == 0
    finally:
        app.setApplicationDisplayName("")
    report = json.loads((report_dir / "smoke-test.json").read_text(encoding="utf-8"))
    assert report["edition"] == "generic" and report["icon_loaded"]
    assert report["icon_sizes"] == list(SIZES)


def test_linux_ships_the_svg_sources_by_size() -> None:
    manifest = (ROOT / "packaging/flatpak/io.github.inmymoonsuit.CADDCalculator.yml").read_text(
        encoding="utf-8"
    )
    for folder, name in (
        ("scalable", "app-icon.svg"),
        ("16x16", "app-icon-16.svg"),
        ("24x24", "app-icon-24.svg"),
        ("32x32", "app-icon-32.svg"),
    ):
        assert (
            f"assets/brand/{name} ${{FLATPAK_DEST}}/share/icons/hicolor/{folder}/apps/" in manifest
        )
    assert "app-icon.png" not in manifest


def test_the_installers_wizard_images_are_the_brands(icons: ModuleType, tmp_path: Path) -> None:
    """Inno Setup's left panel and header images, at every scale, as BMPs (brand.md)."""
    from PySide6.QtGui import QImage

    # Inno Setup 6.6's image areas at 100%, 125%, 150%, 175%, 200%, 225% and 250%: drawn at
    # those sizes, nothing is stretched.
    assert icons.WIZARD_SIZES == {
        "WizardImage": (
            (202, 386),
            (269, 515),
            (336, 643),
            (403, 772),
            (430, 824),
            (498, 953),
            (534, 1022),
        ),
        "WizardSmallImage": (
            (58, 58),
            (77, 77),
            (97, 97),
            (116, 116),
            (124, 124),
            (143, 143),
            (159, 159),
        ),
    }

    defines = icons.wizard_images(tmp_path)
    assert set(defines) == set(icons.WIZARD_SIZES)
    for kind, sizes in icons.WIZARD_SIZES.items():
        files = defines[kind].split(",")
        assert len(files) == len(sizes)
        for file, (width, height) in zip(files, sizes, strict=True):
            assert Path(file).read_bytes()[:2] == b"BM", "a bitmap, as Inno Setup 6 takes"
            drawn = QImage(file)
            assert (drawn.width(), drawn.height()) == (width, height)
    panel = QImage(defines["WizardImage"].split(",")[0])
    assert panel.pixel(0, 0) == CRIMSON
    assert panel.pixel(panel.width() // 2, round(panel.height() * 0.4)) in (CRIMSON, 0xFFFFFFFF)
    assert 0xFFFFFFFF in {panel.pixel(x, y) for x in range(panel.width()) for y in range(200)}
    header = QImage(defines["WizardSmallImage"].split(",")[0])
    assert header.pixel(0, 0) == 0xFFFFFFFF, "the page's white around the tile"
    assert header.pixel(header.width() // 2, 4) == CRIMSON, "the tile"


@pytest.mark.usefixtures("qt")
def test_a_pack_that_names_no_icon_inherits_the_app_icon(tmp_path: Path) -> None:
    """A pack with no icon gets every size of the brand's tile, not a single file."""
    from caddcalc.gui.app_icon import SIZES, window_icon
    from caddcalc.gui.branding import load_branding

    pack = tmp_path / "pack"
    pack.mkdir()
    (pack / "branding.toml").write_text('edition = "no-icon"\n', encoding="utf-8")
    branding = load_branding(pack)
    assert branding.icon == GENERIC_ICON
    assert sorted({s.width() for s in window_icon(branding.icon).availableSizes()}) == list(SIZES)


SIZES_PINNED = (16, 20, 24, 32, 40, 48, 64, 96, 128, 256)
"""Windows' icon sizes from 100% to 200% scaling, and the larger views' (brand.md)."""
ICNS_PINNED = {
    "icp4": 16,
    "icp5": 32,
    "ic11": 32,
    "icp6": 64,
    "ic12": 64,
    "ic07": 128,
    "ic08": 256,
    "ic13": 256,
    "ic09": 512,
    "ic14": 512,
    "ic10": 1024,
}
"""Each .icns type and its PNG's size, as macOS defines them (ic11–ic14 are 2x)."""


@pytest.mark.usefixtures("qt")
def test_the_icon_sizes_are_the_pinned_ones() -> None:
    from caddcalc.gui.app_icon import SIZES

    assert SIZES == SIZES_PINNED


def test_the_ico_directory_names_each_size_with_256_as_0(icons: ModuleType, tmp_path: Path) -> None:
    from PySide6.QtGui import QImage

    ico = tmp_path / "app.ico"
    icons.save_ico(icons.images(GENERIC_ICON, SIZES_PINNED), ico)
    data = ico.read_bytes()
    assert struct.unpack_from("<HHH", data, 0) == (0, 1, len(SIZES_PINNED))
    sides, decoded = [], []
    for entry in range(len(SIZES_PINNED)):
        width, height, _, _, planes, bits, length, offset = struct.unpack_from(
            "<BBBBHHII", data, 6 + 16 * entry
        )
        assert (width, planes, bits) == (height, 1, 32)
        sides.append(width)
        decoded.append(QImage.fromData(data[offset : offset + length]).width())
    assert sides == [*SIZES_PINNED[:-1], 0], "256 is written as 0"
    assert decoded == list(SIZES_PINNED)


def test_the_icns_types_have_the_pinned_png_sizes(icons: ModuleType, tmp_path: Path) -> None:
    from PySide6.QtGui import QImage

    assert icons.ICNS_TYPES == ICNS_PINNED
    icns = tmp_path / "app.icns"
    icons.save_icns(icons.images(GENERIC_ICON, tuple(sorted(set(ICNS_PINNED.values())))), icns)
    data, found, at = icns.read_bytes(), {}, 8
    while at < len(data):
        kind, length = data[at : at + 4].decode("ascii"), struct.unpack_from(">I", data, at + 4)[0]
        found[kind] = QImage.fromData(data[at + 8 : at + length]).width()
        at += length
    assert found == ICNS_PINNED


@pytest.mark.parametrize(
    ("sizes", "pack_icon", "missing"),
    [
        (list(SIZES_PINNED), False, None),
        ([s for s in SIZES_PINNED if s != 20], False, "[20]"),
        ([64], False, str([s for s in SIZES_PINNED if s != 64])),
        ([64], True, None),
    ],
    ids=["every size", "20 missing", "one file on the generic build", "a pack's own icon"],
)
@pytest.mark.usefixtures("qt")
def test_the_builds_smoke_check_reports_a_missing_icon_size(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    sizes: list[int],
    pack_icon: bool,
    missing: str | None,
) -> None:
    """The generic build's app must report every size; a pack's own icon is one file."""
    import subprocess
    from dataclasses import replace

    monkeypatch.syspath_prepend(str(ROOT / "packaging"))
    build = importlib.import_module("build")
    branding = replace(GENERIC, icon=tmp_path / "icon.png") if pack_icon else GENERIC

    def run(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        report = Path(command[1].split("=", 1)[1])
        report.mkdir(parents=True, exist_ok=True)
        summary = {
            "name": build.PRODUCT_NAME,
            "edition": branding.edition,
            "packaged": True,
            "icon_loaded": True,
            "icon_sizes": sizes,
        }
        (report / "smoke-test.json").write_text(json.dumps(summary), encoding="utf-8")
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(build.subprocess, "run", run)
    with pytest.raises(build.BuildError) as failed:  # the faked report lacks the other checks
        build.smoke_test(tmp_path / "app.exe", tmp_path / "dist", branding, 1)
    message = str(failed.value)
    if missing is None:
        assert "px drawings" not in message
    else:
        assert f"the app icon has no {missing} px drawings" in message


@pytest.mark.parametrize(
    ("product", "organization", "title", "strip", "problems"),
    [
        (False, False, "brand", "none", []),
        (False, False, "none", "none", ["the welcome title came from 'none', expected 'brand'"]),
        (False, False, "pack", "none", ["the welcome title came from 'pack', expected 'brand'"]),
        (True, False, "pack", "none", []),
        (True, False, "brand", "none", ["the welcome title came from 'brand', expected 'pack'"]),
        (True, False, "none", "none", ["the welcome title came from 'none', expected 'pack'"]),
        (False, True, "brand", "pack", []),
        (
            False,
            True,
            "brand",
            "none",
            ["the welcome organization logo came from 'none', expected 'pack'"],
        ),
        (
            False,
            False,
            "brand",
            "pack",
            ["the welcome organization logo came from 'pack', expected 'none'"],
        ),
    ],
    ids=[
        "official",
        "official, no title",
        "official, a pack's title",
        "fork",
        "fork, our title",
        "fork, no title",
        "branded",
        "branded, no strip",
        "official, a strip",
    ],
)
@pytest.mark.usefixtures("qt")
def test_the_builds_smoke_check_holds_the_title_and_the_strip_to_the_pack(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    product: bool,
    organization: bool,
    title: str,
    strip: str,
    problems: list[str],
) -> None:
    """The build-time guard for "never our logo on a fork" (S&R's L2, mutants B1 to B3).

    A pack's product logo means the report must say the pack's title was shown; none
    means ours. Likewise the organization logo, or none.
    """
    import subprocess
    from dataclasses import replace

    monkeypatch.syspath_prepend(str(ROOT / "packaging"))
    build = importlib.import_module("build")
    branding = replace(
        GENERIC,
        product_logo=tmp_path / "fork.svg" if product else None,
        organization_logo=tmp_path / "org.svg" if organization else None,
    )

    def run(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        report = Path(command[1].split("=", 1)[1])
        report.mkdir(parents=True, exist_ok=True)
        summary = {
            "name": build.PRODUCT_NAME,
            "edition": branding.edition,
            "packaged": True,
            "icon_loaded": True,
            "icon_sizes": list(SIZES_PINNED),
            "welcome_shown": True,
            "welcome_art": "generic",
            "welcome_title": title,
            "welcome_organization_logo": strip,
        }
        (report / "smoke-test.json").write_text(json.dumps(summary), encoding="utf-8")
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(build.subprocess, "run", run)
    with pytest.raises(build.BuildError) as failed:  # the faked report lacks the other checks
        build.smoke_test(tmp_path / "app.exe", tmp_path / "dist", branding, 1)
    found = [part for part in str(failed.value).split("; ") if "the welcome" in part]
    assert [part.removeprefix("smoke test failed: ") for part in found] == problems


@pytest.mark.parametrize(("art", "problem"), [("generic", None), ("none", "'none'")])
@pytest.mark.usefixtures("qt")
def test_the_builds_smoke_check_requires_the_built_in_art(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, art: str, problem: str | None
) -> None:
    """The official build must show its built-in art; without it the card is blank."""
    import subprocess

    monkeypatch.syspath_prepend(str(ROOT / "packaging"))
    build = importlib.import_module("build")

    def run(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        report = Path(command[1].split("=", 1)[1])
        report.mkdir(parents=True, exist_ok=True)
        summary = {
            "name": build.PRODUCT_NAME,
            "edition": GENERIC.edition,
            "packaged": True,
            "icon_loaded": True,
            "icon_sizes": list(SIZES_PINNED),
            "welcome_shown": True,
            "welcome_art": art,
            "welcome_title": "brand",
            "welcome_organization_logo": "none",
        }
        (report / "smoke-test.json").write_text(json.dumps(summary), encoding="utf-8")
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(build.subprocess, "run", run)
    with pytest.raises(build.BuildError) as failed:  # the faked report lacks the other checks
        build.smoke_test(tmp_path / "app.exe", tmp_path / "dist", GENERIC, 1)
    found = [part for part in str(failed.value).split("; ") if "the welcome art" in part]
    expected = (
        [] if problem is None else [f"the welcome art came from {problem}, expected 'generic'"]
    )
    assert [part.removeprefix("smoke test failed: ") for part in found] == expected
