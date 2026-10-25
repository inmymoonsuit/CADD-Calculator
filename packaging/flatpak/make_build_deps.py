"""Write python3-build-deps.json: the wheel-build tools the Flatpak build installs offline.

    uv run python packaging/flatpak/make_build_deps.py

Flathub builds offline, so every download is listed with its SHA-256. The app needs only
its build backend at build time (hatchling and what it imports, tomlkit among them, and
Babel, which compiles
the catalogs, per pyproject.toml's ``[build-system]``); PySide6 comes from the
io.qt.PySide.BaseApp. These are all pure-Python wheels from PyPI, pinned below. The
module's ``cleanup`` drops them from the finished app.
"""

from __future__ import annotations

import json
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "python3-build-deps.json"
PINS = {
    "hatchling": "1.32.4",
    "packaging": "26.3",
    "pathspec": "1.1.1",
    "pluggy": "1.7.0",
    "trove-classifiers": "2026.9.21.13",
    "tomlkit": "0.15.2",
    "babel": "2.18.0",
}


def wheel(name: str, version: str) -> dict[str, str]:
    """Return the Flatpak file source for the pure-Python wheel of ``name`` at ``version``."""
    url = f"https://pypi.org/pypi/{name}/{version}/json"
    with urllib.request.urlopen(url, timeout=60) as response:
        release = json.load(response)
    for file in release["urls"]:
        if file["packagetype"] == "bdist_wheel" and file["filename"].endswith("-none-any.whl"):
            return {"type": "file", "url": file["url"], "sha256": file["digests"]["sha256"]}
    raise SystemExit(f"{name} {version} has no pure-Python wheel")


def main() -> int:
    """Write the module."""
    module = {
        "name": "python3-build-deps",
        "buildsystem": "simple",
        "build-commands": [
            'pip3 install --verbose --exists-action=i --no-index --find-links="file://${PWD}" '
            "--prefix=${FLATPAK_DEST} --no-build-isolation " + " ".join(PINS)
        ],
        "cleanup": ["*"],
        "sources": [wheel(name, version) for name, version in PINS.items()],
    }
    OUT.write_text(json.dumps(module, indent=4) + "\n", encoding="utf-8", newline="\n")
    print(f"Wrote {OUT.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
