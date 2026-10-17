"""Vendor the Tabler Icons the app uses, from one pinned official release.

    uv run python packaging/fetch_tabler_icons.py                  # re-download, verify all
    uv run python packaging/fetch_tabler_icons.py --add copy       # add icons by name
    uv run python packaging/fetch_tabler_icons.py --version 3.50.0 # move the pin, re-hash
    uv run python packaging/fetch_tabler_icons.py --check          # offline: files match

Icons come from the npm package ``@tabler/icons`` (MIT, github.com/tabler/tabler-icons)
through the jsDelivr CDN, at the exact version in the manifest. The manifest records each
file's SHA-256, so a download that differs from what was reviewed is refused. Only icons
listed in the manifest are vendored. See docs/dev/design/icons.md.
"""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
import tomllib
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
TABLER = ROOT / "src" / "caddcalc" / "gui" / "assets" / "icons" / "tabler"
MANIFEST = TABLER / "manifest.toml"
LICENSE = TABLER / "LICENSE.txt"
SVG_DIR = TABLER / "outline"
BASE_URL = "https://cdn.jsdelivr.net/npm/@tabler/icons@{version}"
NAME_RE = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
VERSION_RE = re.compile(r"\d+\.\d+\.\d+")


class FetchError(Exception):
    pass


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_manifest() -> dict[str, Any]:
    if not MANIFEST.is_file():
        return {}
    return tomllib.loads(MANIFEST.read_text(encoding="utf-8"))


def write_manifest(version: str, icons: dict[str, str], license_sha: str) -> None:
    lines = [
        "# Tabler Icons vendored into CADD Calculator: only the icons the app uses.",
        "# Written by packaging/fetch_tabler_icons.py; see docs/dev/design/icons.md.",
        'name = "Tabler Icons"',
        'repository = "https://github.com/tabler/tabler-icons"',
        'package = "@tabler/icons"',
        f'version = "{version}"',
        'license = "MIT"',
        'style = "outline"',
        f'source = "{BASE_URL}"',
        "",
        "[license_file]",
        'path = "LICENSE.txt"',
        f'sha256 = "{license_sha}"',
        "",
        "# icon name = SHA-256 of its SVG file",
        "[icons]",
        *(f'{name} = "{digest}"' for name, digest in sorted(icons.items())),
    ]
    MANIFEST.write_text("\n".join(lines) + "\n", encoding="utf-8")


def download(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "cadd-calculator-icon-fetch"})
    with urllib.request.urlopen(request, timeout=30) as response:
        data: bytes = response.read()
    return data


def check() -> list[str]:
    """Offline check that the vendored files match the manifest. Returns the problems."""
    manifest = load_manifest()
    if not manifest:
        return [f"{MANIFEST} is missing"]
    icons: dict[str, str] = manifest["icons"]
    problems = []
    for name, digest in sorted(icons.items()):
        path = SVG_DIR / f"{name}.svg"
        if not path.is_file():
            problems.append(f"{path} is missing")
        elif sha256(path.read_bytes()) != digest:
            problems.append(f"{name}.svg does not match its manifest hash")
    if not LICENSE.is_file() or sha256(LICENSE.read_bytes()) != manifest["license_file"]["sha256"]:
        problems.append(f"{LICENSE.name} is missing or does not match its manifest hash")
    extra = sorted({p.stem for p in SVG_DIR.glob("*.svg")} - set(icons))
    problems += [f"{name}.svg is not listed in the manifest" for name in extra]
    return problems


def fetch(version: str, names: set[str], known: dict[str, str], known_license: str | None) -> None:
    base = BASE_URL.format(version=version)
    license_text = download(f"{base}/LICENSE")
    if b"MIT License" not in license_text:
        raise FetchError(f"Tabler {version} is not MIT-licensed any more; stop and review")
    license_sha = sha256(license_text)
    if known_license and known_license != license_sha:
        raise FetchError(f"LICENSE for {version} changed since it was recorded; review it")

    downloads: dict[str, bytes] = {}
    for name in sorted(names):
        if not NAME_RE.fullmatch(name):
            raise FetchError(f"{name!r} is not a Tabler icon name")
        data = download(f"{base}/icons/outline/{name}.svg")
        if b"currentColor" not in data:
            raise FetchError(f"{name}.svg does not use currentColor, so it can't be recolored")
        if known.get(name) and known[name] != sha256(data):
            raise FetchError(f"{name}.svg for {version} changed since it was recorded; review it")
        downloads[name] = data

    SVG_DIR.mkdir(parents=True, exist_ok=True)
    for stale in SVG_DIR.glob("*.svg"):
        if stale.stem not in downloads:
            stale.unlink()
    for name, data in downloads.items():
        (SVG_DIR / f"{name}.svg").write_bytes(data)
    LICENSE.write_bytes(license_text)
    write_manifest(version, {n: sha256(d) for n, d in downloads.items()}, license_sha)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else None)
    parser.add_argument("--add", nargs="+", default=[], metavar="NAME", help="icons to add")
    parser.add_argument("--remove", nargs="+", default=[], metavar="NAME", help="icons to drop")
    parser.add_argument("--version", help="move the pinned Tabler version (re-hashes all)")
    parser.add_argument("--check", action="store_true", help="verify files offline and exit")
    args = parser.parse_args(argv)

    if args.check:
        problems = check()
        for problem in problems:
            print(f"fetch_tabler_icons: {problem}", file=sys.stderr)
        return 1 if problems else 0

    manifest = load_manifest()
    version = args.version or manifest.get("version")
    if not version or not VERSION_RE.fullmatch(version):
        print("fetch_tabler_icons: give --version X.Y.Z for the first fetch", file=sys.stderr)
        return 2
    same_pin = version == manifest.get("version")
    known: dict[str, str] = manifest.get("icons", {}) if same_pin else {}
    known_license = manifest.get("license_file", {}).get("sha256") if same_pin else None
    names = (set(manifest.get("icons", {})) | set(args.add)) - set(args.remove)
    if not names:
        print("fetch_tabler_icons: no icons to fetch; use --add NAME", file=sys.stderr)
        return 2
    try:
        fetch(version, names, known, known_license)
    except (FetchError, OSError) as exc:
        print(f"fetch_tabler_icons: {exc}", file=sys.stderr)
        return 1
    print(f"Tabler Icons {version}: {len(names)} icons in {SVG_DIR.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
