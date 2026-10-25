"""Install, start, and uninstall the Windows installer, checking every step (slice d3).

    uv run python packaging/windows/test_installer.py builds/generic/<name>-setup.exe

It installs for the current user, silently, into a fresh temporary folder; starts the
installed app with ``--smoke-test``; uninstalls silently; and checks the install folder
and the Start-menu shortcut are gone. Every step's exit code is checked. CI runs it on
windows-latest. It installs software, so run it on a dev machine only on purpose.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

APP_NAME = "CADD Calculator"
APP_EXE = "CADDCalculator.exe"
UNINSTALLER = "unins000.exe"
SHORTCUT = (
    Path(os.environ.get("APPDATA", ""))
    / "Microsoft/Windows/Start Menu/Programs"
    / f"{APP_NAME}.lnk"
)
"""Where a per-user install puts its Start-menu shortcut ({autoprograms})."""
UNINSTALL_WAIT_S = 120


class InstallerTestError(Exception):
    """A step failed: its exit code, or what it left behind."""


def run(step: str, command: list[str], timeout: float = 300) -> None:
    """Run one step; raise if it doesn't exit 0."""
    print(f"{step}: {' '.join(command)}", flush=True)
    result = subprocess.run(command, timeout=timeout, check=False)
    print(f"{step}: exit {result.returncode}", flush=True)
    if result.returncode:
        raise InstallerTestError(f"{step} exited with {result.returncode}")


def test_installer(installer: Path, work: Path) -> dict[str, object]:
    """Run the whole cycle in ``work``; return what was checked."""
    target = work / "install"
    report_dir = work / "smoke-test"
    run(
        "install",
        [
            str(installer),
            "/VERYSILENT",
            "/SUPPRESSMSGBOXES",
            "/NORESTART",
            "/CURRENTUSER",
            f"/DIR={target}",
            f"/LOG={work / 'install.log'}",
        ],
    )
    exe = target / APP_EXE
    for path in (exe, target / UNINSTALLER, target / "LICENSE.md", target / "licenses"):
        if not path.exists():
            raise InstallerTestError(f"the install has no {path.name}")
    if not SHORTCUT.is_file():
        raise InstallerTestError(f"no Start-menu shortcut at {SHORTCUT}")

    run("smoke test", [str(exe), f"--smoke-test={report_dir}"], timeout=180)
    report = json.loads((report_dir / "smoke-test.json").read_text(encoding="utf-8"))
    if not report.get("packaged") or not report.get("qt_catalog"):
        raise InstallerTestError(f"the installed app's smoke test failed: {report}")

    # The uninstaller copies itself to a temporary folder and returns at once, so wait
    # for the install folder to go.
    run("uninstall", [str(target / UNINSTALLER), "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART"])
    deadline = time.monotonic() + UNINSTALL_WAIT_S
    while target.exists() and time.monotonic() < deadline:
        time.sleep(1)
    left = sorted(str(p.relative_to(target)) for p in target.rglob("*")) if target.exists() else []
    if target.exists():
        raise InstallerTestError(f"the uninstall left {target}: {left[:20]}")
    if SHORTCUT.exists():
        raise InstallerTestError(f"the uninstall left the shortcut {SHORTCUT}")
    return {"installed_to": str(target), "smoke_test": report, "left_behind": left}


def main(argv: list[str] | None = None) -> int:
    """Run the command line; return the exit status."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("installer", type=Path, help="the -setup.exe to test")
    args = parser.parse_args(argv)
    if sys.platform != "win32":
        print("test_installer: Windows only", file=sys.stderr)
        return 2
    with tempfile.TemporaryDirectory(prefix="caddcalc-installer-") as tmp:
        try:
            result = test_installer(args.installer.resolve(), Path(tmp))
        except (InstallerTestError, subprocess.TimeoutExpired) as exc:
            print(f"test_installer: error: {exc}", file=sys.stderr)
            return 1
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
