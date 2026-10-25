"""Check the AppImage against a stock Ubuntu 22.04 desktop (S&R's AppImage Medium).

    python3 packaging/linux/check_desktop.py manifest     # the baseline is on that desktop
    python3 packaging/linux/check_desktop.py ldd squashfs-root   # nothing it needs is missing

CI's appimage-x11 job runs both in a clean ubuntu:22.04 container that has only the
packages in ``desktop-baseline.txt`` (and Xvfb), then starts the AppImage on X11. ``manifest``
checks each baseline package against Ubuntu's own list of what its 22.04 desktop installs,
pinned by SHA-256. ``ldd`` runs ``ldd`` on every ELF file in the extracted AppImage and fails
on any library that neither the AppImage nor the host provides. Standard library only,
since the container's Python is the system's 3.10.
"""

from __future__ import annotations

import argparse
import hashlib
import subprocess
import sys
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASELINE = HERE / "desktop-baseline.txt"
MANIFEST_URL = "https://releases.ubuntu.com/22.04/ubuntu-22.04.5-desktop-amd64.manifest"
MANIFEST_SHA256 = "b0df520563aec46c6ae21f1504c1254e7872baab4ec9f8f306d92958ccd13689"


def baseline(path: Path = BASELINE) -> list[str]:
    """Return the baseline's package names, without comments or blank lines."""
    lines = path.read_text(encoding="utf-8").splitlines()
    return [line.strip() for line in lines if line.strip() and not line.startswith("#")]


def manifest_packages(text: str) -> set[str]:
    """Return the package names in an Ubuntu manifest: ``name[:arch]<tab>version`` lines."""
    return {line.split()[0].split(":")[0] for line in text.splitlines() if line.strip()}


def not_on_desktop(packages: list[str], manifest: set[str]) -> list[str]:
    """Return the packages a stock desktop doesn't install."""
    return [name for name in packages if name not in manifest]


def missing_libraries(ldd_output: str) -> list[str]:
    """Return the libraries ``ldd`` reports as ``not found``."""
    return [line.split("=>")[0].strip() for line in ldd_output.splitlines() if "not found" in line]


def is_elf(path: Path) -> bool:
    """Whether ``path`` is an ELF file."""
    with path.open("rb") as fh:
        return fh.read(4) == b"\x7fELF"


def check_ldd(root: Path) -> dict[str, list[str]]:
    """Return each ELF file under ``root`` that needs a library nothing provides."""
    problems = {}
    for path in sorted(root.rglob("*")):
        if path.is_file() and not path.is_symlink() and is_elf(path):
            result = subprocess.run(["ldd", str(path)], capture_output=True, text=True, check=False)
            missing = missing_libraries(result.stdout)
            if missing:
                problems[str(path.relative_to(root))] = missing
    return problems


def main(argv: list[str] | None = None) -> int:
    """Run the command line; return the exit status."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("manifest", help="check the baseline against Ubuntu's manifest")
    ldd = commands.add_parser("ldd", help="check the extracted AppImage's libraries")
    ldd.add_argument("root", type=Path)
    args = parser.parse_args(argv)
    if args.command == "manifest":
        with urllib.request.urlopen(MANIFEST_URL, timeout=60) as response:
            body: bytes = response.read()
        if hashlib.sha256(body).hexdigest() != MANIFEST_SHA256:
            print("::error title=Desktop baseline::Ubuntu's manifest doesn't match its pin")
            return 1
        extra = not_on_desktop(baseline(), manifest_packages(body.decode("utf-8")))
        if extra:
            print(f"::error title=Desktop baseline::not on a stock 22.04 desktop: {extra}")
            return 1
        print(f"{len(baseline())} baseline packages, all on a stock Ubuntu 22.04 desktop")
        return 0
    problems = check_ldd(args.root)
    if problems:
        # One annotation for them all: a step shows only its first ten.
        lines = [f"{path} needs {', '.join(missing)}" for path, missing in problems.items()]
        print("::error title=AppImage libraries::" + "%0A".join(lines))
    else:
        print("every library the AppImage needs is in it or on the desktop baseline")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
