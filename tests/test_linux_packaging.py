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
