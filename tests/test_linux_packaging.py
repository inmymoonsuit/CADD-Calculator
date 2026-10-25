"""The AppImage and Flathub packaging's files agree with each other (slice d4).

CI validates the .desktop file and the metainfo with desktop-file-validate and
appstreamcli, builds and starts the AppImage, and builds and starts the Flatpak; these
check what doesn't need Linux: one app ID everywhere, the metainfo's required fields,
the build dependencies matching their pins, and the pinned downloads.
"""

from __future__ import annotations

import configparser
import importlib.util
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).parents[1]
LINUX = ROOT / "packaging" / "linux"
FLATPAK = ROOT / "packaging" / "flatpak"
APP_ID = "io.github.inmymoonsuit.CADDCalculator"


def _load(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module  # a dataclass resolves its annotations through it
    spec.loader.exec_module(module)
    return module


def test_the_desktop_file_launches_the_installed_command() -> None:
    entry = configparser.ConfigParser(interpolation=None)
    entry.optionxform = str  # type: ignore[assignment,method-assign]
    entry.read(LINUX / f"{APP_ID}.desktop", encoding="utf-8")
    desktop = entry["Desktop Entry"]
    assert desktop["Type"] == "Application"
    assert desktop["Name"] == "CADD Calculator"
    assert desktop["Exec"] == "caddcalc-gui", "the gui-scripts entry point in pyproject.toml"
    assert desktop["Icon"] == APP_ID
    assert "caddcalc-gui = " in (ROOT / "pyproject.toml").read_text(encoding="utf-8")


def test_the_metainfo_names_the_app_and_its_licenses() -> None:
    root = ET.parse(LINUX / f"{APP_ID}.metainfo.xml").getroot()  # noqa: S314 (our file)
    assert root.get("type") == "desktop-application"
    assert root.findtext("id") == APP_ID
    assert root.findtext("metadata_license") == "CC0-1.0"
    assert root.findtext("project_license") == "Apache-2.0"
    assert root.findtext("launchable") == f"{APP_ID}.desktop"
    assert root.find("content_rating") is not None
    assert root.find("developer/name") is not None
    assert root.find("releases/release") is not None


def test_the_flathub_manifest_builds_this_app_from_source() -> None:
    manifest = (FLATPAK / f"{APP_ID}.yml").read_text(encoding="utf-8")
    assert f"id: {APP_ID}" in manifest
    assert "base: io.qt.PySide.BaseApp" in manifest
    assert re.search(r"runtime-version: '(\d+\.\d+)'", manifest)
    runtime = re.search(r"runtime-version: '([\d.]+)'", manifest)
    base = re.search(r"base-version: '([\d.]+)'", manifest)
    assert runtime and base and runtime.group(1) == base.group(1), "Flathub: they must match"
    assert "command: caddcalc-gui" in manifest
    assert "--share=network" not in manifest.replace("no --share=network", ""), "no network"
    assert "pip3 install" in manifest and "--no-index" in manifest, "offline, from source"
    assert "python3-build-deps.json" in manifest


def test_the_build_dependencies_match_their_pins() -> None:
    pins = _load("make_build_deps", FLATPAK / "make_build_deps.py").PINS
    module = json.loads((FLATPAK / "python3-build-deps.json").read_text(encoding="utf-8"))
    sources = module["sources"]
    assert len(sources) == len(pins)
    for (name, version), source in zip(pins.items(), sources, strict=True):
        wheel = source["url"].rsplit("/", 1)[1].lower()
        assert wheel.startswith(f"{name.replace('-', '_')}-{version}-"), (name, wheel)
        assert re.fullmatch(r"[0-9a-f]{64}", source["sha256"])
    assert module["cleanup"] == ["*"], "build tools don't ship"
    assert "babel" in pins and "hatchling" in pins, "pyproject.toml's [build-system]"
    # hatchling's own requirements (Python 3.11+): a missing one fails the offline build.
    assert {"packaging", "pathspec", "pluggy", "tomlkit", "trove-classifiers"} <= set(pins)


def test_the_appimage_tools_are_pinned_and_checked() -> None:
    maker = _load("make_appimage", LINUX / "make_appimage.py")
    for url, digest in (
        (maker.APPIMAGETOOL_URL, maker.APPIMAGETOOL_SHA256),
        (maker.RUNTIME_URL, maker.RUNTIME_SHA256),
    ):
        assert "/continuous/" not in url, "a tagged release, not a moving one"
        assert url.startswith("https://github.com/AppImage/")
        assert re.fullmatch(r"[0-9a-f]{64}", digest)
    assert maker.DESKTOP.is_file() and maker.METAINFO.is_file() and maker.ICON.is_file()


def test_only_listed_binaries_pass_the_notice_check() -> None:
    """S&R's mutant L2 and Low 2: only listed binaries pass the notice check.

    An unknown library, or a third-party C extension, has no component, so the build fails
    on it; the interpreter's own extension modules pass.
    """
    notices = _load("library_notices", ROOT / "packaging" / "library_notices.py")
    for unknown in (
        "libfoo.so",
        "libfoo.so.1",
        "foo.dll",
        "foo.pyd",
        "_cffi_backend.cpython-312-x86_64-linux-gnu.so",
        "numpy/_core/_multiarray_umath.cpython-312-x86_64-linux-gnu.so",
        "numpy/_core/_multiarray_umath.pyd",
        "libstdc++.so.6",
        "libgcc_s.so.1",
    ):
        assert notices.component_of(unknown) is None, unknown
    # Whichever Python runs the tests: some build every module into libpython, and list none.
    own = sorted(notices.stdlib_extensions())
    if sys.platform == "win32":
        assert own, "Windows interpreters keep their extension modules in DLLs"
    for module in own[:3]:
        for name in (f"{module}.pyd", f"{module}.cpython-312-x86_64-linux-gnu.so"):
            assert notices.component_of(name).name.startswith("Python"), name
    assert notices.component_of("PySide6/Qt/lib/libxcb-cursor.so.0").name.startswith("xcb")


def test_the_appimage_brings_what_a_stock_desktop_lacks() -> None:
    """S&R's AppImage Medium: the AppImage brings what a stock desktop lacks.

    libxcb-cursor is bundled, since Ubuntu 22.04's desktop doesn't install it; everything
    else comes from that desktop's own packages.
    """
    desktop = _load("check_desktop", LINUX / "check_desktop.py")
    baseline = desktop.baseline()
    assert "libxcb-cursor0" not in baseline
    assert {"libxkbcommon-x11-0", "libxcb-icccm4", "libgl1", "libfontconfig1"} <= set(baseline)
    assert re.fullmatch(r"[0-9a-f]{64}", desktop.MANIFEST_SHA256)
    assert desktop.MANIFEST_URL.startswith("https://releases.ubuntu.com/22.04/")
    manifest = desktop.manifest_packages("libxcb1:amd64\t1.14-3ubuntu3\nlibgl1\t1.4.0-1\n")
    assert manifest == {"libxcb1", "libgl1"}
    assert desktop.not_on_desktop(["libgl1", "libxcb-cursor0"], manifest) == ["libxcb-cursor0"]
    ldd = (
        "\tlibxcb-cursor.so.0 => not found\n"
        "\tlibxcb.so.1 => /lib/x86_64-linux-gnu/libxcb.so.1 (0x00007f)\n"
    )
    assert desktop.missing_libraries(ldd) == ["libxcb-cursor.so.0"]
    build = (ROOT / "packaging" / "build.py").read_text(encoding="utf-8")
    assert 'HOST_LIBRARIES = ("libxcb-cursor.so.0",)' in build
    workflow = (ROOT / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")
    job = workflow[workflow.index("  appimage-x11:") : workflow.index("  linux-metadata:")]
    assert "container: ubuntu:22.04" in job
    assert "QT_QPA_PLATFORM: xcb" in job and "xvfb-run" in job
    assert "r['qt_platform'] == 'xcb'" in job
    assert "check_desktop.py manifest" in job and "check_desktop.py ldd squashfs-root" in job
