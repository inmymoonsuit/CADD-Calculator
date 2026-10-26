"""Wrap the standalone Linux build in an AppImage, and start it to check it (slice d4).

    uv run python packaging/build.py --smoke-test
    uv run python packaging/linux/make_appimage.py builds/generic/<name>-linux-x64 --smoke-test

It lays out an AppDir: the app folder in ``usr/lib/caddcalc``, a ``caddcalc-gui`` launcher,
the .desktop file, the icon, and the AppStream metainfo. Then it runs appimagetool, a pinned
release checked against its SHA-256, extracting it rather than mounting it, so no FUSE is
needed. With ``--smoke-test`` it starts the AppImage the same way
(``--appimage-extract-and-run``) and checks the app's report. Linux only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import stat
import subprocess
import sys
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
APP_ID = "io.github.inmymoonsuit.CADDCalculator"
DESKTOP = HERE / f"{APP_ID}.desktop"
METAINFO = HERE / f"{APP_ID}.metainfo.xml"
BRAND = ROOT / "src" / "caddcalc" / "gui" / "assets" / "brand"
ICONS = {
    "scalable": BRAND / "app-icon.svg",
    "16x16": BRAND / "app-icon-16.svg",
    "24x24": BRAND / "app-icon-24.svg",
    "32x32": BRAND / "app-icon-32.svg",
}
"""The app icon by hicolor folder: the master, and the drawings made for the small sizes
(docs/dev/design/brand.md)."""
APPIMAGETOOL_URL = (
    "https://github.com/AppImage/appimagetool/releases/download/1.9.1/appimagetool-x86_64.AppImage"
)
APPIMAGETOOL_SHA256 = "ed4ce84f0d9caff66f50bcca6ff6f35aae54ce8135408b3fa33abfc3cb384eb0"
"""appimagetool 1.9.1's x86_64 release, as its GitHub release lists it."""
RUNTIME_URL = "https://github.com/AppImage/type2-runtime/releases/download/20251108/runtime-x86_64"
RUNTIME_SHA256 = "2fca8b443c92510f1483a883f60061ad09b46b978b2631c807cd873a47ec260d"
"""The AppImage runtime, release 20251108, as its GitHub release lists it. appimagetool
would otherwise download the moving "continuous" runtime."""
TOOLS = ROOT / "builds" / "tools"

APP_RUN = """#!/bin/sh
# The AppImage's entry point: start the app from inside the image.
HERE="$(dirname "$(readlink -f "$0")")"
exec "$HERE/usr/bin/caddcalc-gui" "$@"
"""
LAUNCHER = """#!/bin/sh
# Start the packaged app, which lives in ../lib/caddcalc.
HERE="$(dirname "$(readlink -f "$0")")"
exec "$HERE/../lib/caddcalc/CADDCalculator.bin" "$@"
"""


class AppImageError(Exception):
    """A step failed: the tool's checksum, appimagetool, or the smoke test."""


def executable(path: Path, text: str) -> None:
    """Write a script to ``path`` and make it executable."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def make_appdir(app: Path, appdir: Path) -> Path:
    """Lay out the AppDir for the app folder ``app``; return it."""
    shutil.rmtree(appdir, ignore_errors=True)
    shutil.copytree(app, appdir / "usr" / "lib" / "caddcalc", symlinks=True)
    executable(appdir / "usr" / "bin" / "caddcalc-gui", LAUNCHER)
    executable(appdir / "AppRun", APP_RUN)
    for target in (appdir, appdir / "usr" / "share" / "applications"):
        target.mkdir(parents=True, exist_ok=True)
        shutil.copy2(DESKTOP, target / DESKTOP.name)
    for folder, icon in ICONS.items():
        apps = appdir / "usr" / "share" / "icons" / "hicolor" / folder / "apps"
        apps.mkdir(parents=True)
        shutil.copy2(icon, apps / f"{APP_ID}.svg")
    shutil.copy2(ICONS["scalable"], appdir / f"{APP_ID}.svg")
    metainfo = appdir / "usr" / "share" / "metainfo"
    metainfo.mkdir(parents=True)
    shutil.copy2(METAINFO, metainfo / METAINFO.name)
    return appdir


def pinned(url: str, sha256: str, name: str) -> Path:
    """Return a pinned download, fetching and checking it the first time.

    Raises:
        AppImageError: The download isn't the pinned file.
    """
    path = TOOLS / name
    if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != sha256:
        TOOLS.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(url, timeout=120) as response:  # noqa: S310 (fixed HTTPS)
            body: bytes = response.read()
        if hashlib.sha256(body).hexdigest() != sha256:
            raise AppImageError(f"{name}'s download doesn't match its pinned SHA-256")
        path.write_bytes(body)
        path.chmod(0o755)
    return path


def make_appimage(app: Path, out: Path) -> Path:
    """Build the AppImage for the app folder ``app`` as ``out``; return it."""
    appdir = make_appdir(app, out.with_suffix(".AppDir"))
    env = {**os.environ, "ARCH": "x86_64", "APPIMAGE_EXTRACT_AND_RUN": "1"}
    result = subprocess.run(
        [
            str(pinned(APPIMAGETOOL_URL, APPIMAGETOOL_SHA256, "appimagetool-1.9.1-x86_64")),
            "--runtime-file",
            str(pinned(RUNTIME_URL, RUNTIME_SHA256, "runtime-20251108-x86_64")),
            "--no-appstream",
            str(appdir),
            str(out),
        ],
        env=env,
        check=False,
    )
    if result.returncode or not out.is_file():
        raise AppImageError(f"appimagetool failed (exit {result.returncode})")
    shutil.rmtree(appdir)
    return out


def smoke_test(image: Path) -> dict[str, object]:
    """Start the AppImage with ``--smoke-test`` and check its report."""
    report_dir = image.with_name(f"{image.name}.smoke-test")
    shutil.rmtree(report_dir, ignore_errors=True)
    result = subprocess.run(
        [str(image), "--appimage-extract-and-run", f"--smoke-test={report_dir}"],
        timeout=180,
        check=False,
    )
    if result.returncode:
        raise AppImageError(f"the AppImage's smoke test exited with {result.returncode}")
    report: dict[str, object] = json.loads(
        (report_dir / "smoke-test.json").read_text(encoding="utf-8")
    )
    if not report.get("packaged") or not report.get("qt_catalog"):
        raise AppImageError(f"the AppImage's smoke test failed: {report}")
    return report


def main(argv: list[str] | None = None) -> int:
    """Run the command line; return the exit status."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("app", type=Path, help="the standalone Linux build's folder")
    parser.add_argument("--smoke-test", action="store_true", help="start it and check it")
    args = parser.parse_args(argv)
    if not sys.platform.startswith("linux"):
        print("make_appimage: Linux only", file=sys.stderr)
        return 2
    app = args.app.resolve()
    out = app.with_name(f"{app.name}.AppImage")
    try:
        image = make_appimage(app, out)
        report = smoke_test(image) if args.smoke_test else None
    except (AppImageError, subprocess.TimeoutExpired) as exc:
        print(f"make_appimage: error: {exc}", file=sys.stderr)
        if os.environ.get("GITHUB_ACTIONS") == "true":
            print(f"::error title=AppImage::{exc}")
        return 1
    size_mb = round(image.stat().st_size / 1e6, 1)
    print(json.dumps({"appimage": str(image), "size_mb": size_mb, "smoke_test": report}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
