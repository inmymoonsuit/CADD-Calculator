"""Put the macOS .app in a .dmg, then mount it and start the app from it (slice d5).

    uv run python packaging/build.py --smoke-test
    uv run python packaging/macos/make_dmg.py builds/generic/<name>-macos-arm64.app --smoke-test

The image holds the app and a link to /Applications, so a user drags one onto the other.
It's made with ``hdiutil`` as a compressed, read-only image. With ``--smoke-test`` it
mounts the image read-only, checks the link is there, starts the app from the mounted
image with ``--smoke-test``, checks its report, and detaches. macOS only. The app isn't
signed or notarized yet (ADR-0022; docs/user/installing.md).
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

VOLUME_NAME = "CADD Calculator"
EXE_STEM = "CADDCalculator"


class DmgError(Exception):
    """A step failed: hdiutil, the image's contents, or the smoke test."""


def run(step: str, command: list[str], timeout: float = 600) -> None:
    """Run one step; raise if it doesn't exit 0."""
    result = subprocess.run(command, timeout=timeout, check=False)
    if result.returncode:
        raise DmgError(f"{step} exited with {result.returncode}")


def make_dmg(app: Path, out: Path) -> Path:
    """Make the .dmg ``out`` holding ``app`` and a link to /Applications; return it."""
    with tempfile.TemporaryDirectory(prefix="caddcalc-dmg-") as tmp:
        staging = Path(tmp) / VOLUME_NAME
        staging.mkdir()
        shutil.copytree(app, staging / app.name, symlinks=True)
        (staging / "Applications").symlink_to("/Applications")
        out.unlink(missing_ok=True)
        run(
            "hdiutil create",
            [
                "hdiutil",
                "create",
                "-volname",
                VOLUME_NAME,
                "-srcfolder",
                str(staging),
                "-fs",
                "HFS+",
                "-format",
                "UDZO",
                "-ov",
                str(out),
            ],
        )
    if not out.is_file():
        raise DmgError(f"hdiutil made no {out.name}")
    return out


def smoke_test(dmg: Path, app_name: str) -> dict[str, object]:
    """Mount ``dmg`` read-only, start the app from it with ``--smoke-test``, and detach."""
    report_dir = dmg.with_name(f"{dmg.name}.smoke-test")
    shutil.rmtree(report_dir, ignore_errors=True)
    with tempfile.TemporaryDirectory(prefix="caddcalc-mount-") as mount:
        run(
            "hdiutil attach",
            ["hdiutil", "attach", "-nobrowse", "-readonly", "-mountpoint", mount, str(dmg)],
        )
        try:
            link = Path(mount) / "Applications"
            if not link.is_symlink() or str(link.readlink()) != "/Applications":
                raise DmgError("the image has no link to /Applications")
            exe = Path(mount) / app_name / "Contents" / "MacOS" / EXE_STEM
            run("smoke test", [str(exe), f"--smoke-test={report_dir}"], timeout=180)
        finally:
            run("hdiutil detach", ["hdiutil", "detach", mount])
    report: dict[str, object] = json.loads(
        (report_dir / "smoke-test.json").read_text(encoding="utf-8")
    )
    if not report.get("packaged") or not report.get("qt_catalog"):
        raise DmgError(f"the app's smoke test from the image failed: {report}")
    return report


def main(argv: list[str] | None = None) -> int:
    """Run the command line; return the exit status."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("app", type=Path, help="the built .app")
    parser.add_argument("--smoke-test", action="store_true", help="mount it, start the app")
    args = parser.parse_args(argv)
    if sys.platform != "darwin":
        print("make_dmg: macOS only", file=sys.stderr)
        return 2
    app = args.app.resolve()
    out = app.with_suffix(".dmg")
    try:
        dmg = make_dmg(app, out)
        report = smoke_test(dmg, app.name) if args.smoke_test else None
    except (DmgError, subprocess.TimeoutExpired) as exc:
        print(f"make_dmg: error: {exc}", file=sys.stderr)
        if os.environ.get("GITHUB_ACTIONS") == "true":
            print(f"::error title=dmg::{exc}")
        return 1
    print(
        json.dumps(
            {"dmg": str(dmg), "size_mb": round(dmg.stat().st_size / 1e6, 1), "smoke_test": report}
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
