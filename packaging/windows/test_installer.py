"""Install, start, and uninstall the Windows installer, checking every step (slice d3).

    uv run python packaging/windows/test_installer.py builds/generic/<name>-setup.exe

It installs for the current user, silently, into a fresh temporary folder, and checks:

* the install ran in Inno Setup's non-administrative mode, into the current user's
  registry, so it needs no admin rights (CI runners are admins, so this reads the log);
* the uninstall entry is registered under the installer's fixed AppId;
* the installed app starts and passes ``--smoke-test``;
* a silent uninstall removes the folder, the Start-menu shortcut, and the uninstall entry.

Every step's exit code is checked. CI runs it on windows-latest. It installs software, so
run it on a dev machine only on purpose.
"""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

APP_NAME = "CADD Calculator"
APP_EXE = "CADDCalculator.exe"
APP_ID = "{B2EF94B1-E799-438B-AEF3-A34EFB0048A2}"
"""The installer's AppId (packaging/windows/CADDCalculator.iss); it never changes."""
UNINSTALL_KEY = rf"Software\Microsoft\Windows\CurrentVersion\Uninstall\{APP_ID}_is1"
"""Where Inno Setup registers a per-user install's uninstall entry, under HKCU."""
UNINSTALLER = "unins000.exe"
SHORTCUT = (
    Path(os.environ.get("APPDATA", ""))
    / "Microsoft/Windows/Start Menu/Programs"
    / f"{APP_NAME}.lnk"
)
"""Where a per-user install puts its Start-menu shortcut ({autoprograms})."""
NON_ADMIN_LOG_LINES = (
    "Administrative install mode: No",
    "Install mode root key: HKEY_CURRENT_USER",
)
"""What Inno Setup's log says for a per-user install that needs no admin rights."""
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


def uninstall_entry() -> dict[str, str] | None:
    """Return the installer's per-user uninstall entry, or ``None`` if it isn't registered."""
    if sys.platform != "win32":  # also tells mypy, checking for Linux or macOS, to skip it
        return None
    import winreg

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, UNINSTALL_KEY) as key:
            names = ("DisplayName", "DisplayVersion", "InstallLocation", "UninstallString")
            entry = {}
            for name in names:
                with contextlib.suppress(OSError):  # a value Inno didn't write
                    entry[name] = str(winreg.QueryValueEx(key, name)[0])
            return entry
    except FileNotFoundError:
        return None


def test_installer(installer: Path, work: Path) -> dict[str, object]:
    """Run the whole cycle in ``work``; return what was checked."""
    target = work / "install"
    report_dir = work / "smoke-test"
    log = work / "install.log"
    if uninstall_entry() is not None:
        raise InstallerTestError(f"CADD Calculator is already installed (HKCU\\{UNINSTALL_KEY})")
    run(
        "install",
        [
            str(installer),
            "/VERYSILENT",
            "/SUPPRESSMSGBOXES",
            "/NORESTART",
            "/CURRENTUSER",
            f"/DIR={target}",
            f"/LOG={log}",
        ],
    )
    log_text = log.read_text(encoding="utf-8", errors="replace") if log.is_file() else ""
    for line in NON_ADMIN_LOG_LINES:
        if line not in log_text:
            raise InstallerTestError(
                f"the install log doesn't say {line!r}: not a per-user install"
            )
    exe = target / APP_EXE
    for path in (exe, target / UNINSTALLER, target / "LICENSE.md", target / "licenses"):
        if not path.exists():
            raise InstallerTestError(f"the install has no {path.name}")
    if not SHORTCUT.is_file():
        raise InstallerTestError(f"no Start-menu shortcut at {SHORTCUT}")
    entry = uninstall_entry()
    if entry is None:
        raise InstallerTestError(f"no uninstall entry under the AppId (HKCU\\{UNINSTALL_KEY})")
    if entry.get("DisplayName") != APP_NAME:
        raise InstallerTestError(f"the uninstall entry names {entry.get('DisplayName')!r}")

    run("smoke test", [str(exe), f"--smoke-test={report_dir}"], timeout=180)
    report = json.loads((report_dir / "smoke-test.json").read_text(encoding="utf-8"))
    if not report.get("packaged") or not report.get("qt_catalog"):
        raise InstallerTestError(f"the installed app's smoke test failed: {report}")

    # The uninstaller copies itself to a temporary folder and returns at once, so wait
    # for the install folder and the uninstall entry to go.
    run("uninstall", [str(target / UNINSTALLER), "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART"])
    deadline = time.monotonic() + UNINSTALL_WAIT_S
    while (target.exists() or uninstall_entry() is not None) and time.monotonic() < deadline:
        time.sleep(1)
    left = sorted(str(p.relative_to(target)) for p in target.rglob("*")) if target.exists() else []
    if target.exists():
        raise InstallerTestError(f"the uninstall left {target}: {left[:20]}")
    if SHORTCUT.exists():
        raise InstallerTestError(f"the uninstall left the shortcut {SHORTCUT}")
    if uninstall_entry() is not None:
        raise InstallerTestError(f"the uninstall left its entry, HKCU\\{UNINSTALL_KEY}")
    return {
        "installed_to": str(target),
        "uninstall_entry": entry,
        "non_admin": list(NON_ADMIN_LOG_LINES),
        "smoke_test": report,
        "left_behind": left,
    }


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
            if os.environ.get("GITHUB_ACTIONS") == "true":
                # Job logs need a signed-in reader; an annotation is public.
                message = str(exc).replace("%", "%25").replace("\n", "%0A")
                print(f"::error title=Installer test::{message}")
            return 1
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
