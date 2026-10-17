"""Vendor the welcome screen's display face, VT323, from one pinned google/fonts commit.

    uv run python packaging/fetch_fonts.py                   # re-download, verify all
    uv run python packaging/fetch_fonts.py --commit SHA      # move the pin, re-hash
    uv run python packaging/fetch_fonts.py --check           # offline: files match

The font and its license come from github.com/google/fonts at the exact commit in the
manifest, as raw files. The manifest records each file's SHA-256, so a download that
differs from what was reviewed is refused, and the license must still be the SIL Open
Font License 1.1. The font ships unmodified, as the OFL asks (ADR-0016 §2).
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
FONT_DIR = ROOT / "src" / "caddcalc" / "gui" / "assets" / "fonts" / "vt323"
MANIFEST = FONT_DIR / "manifest.toml"
SOURCE_PATH = "ofl/vt323"
FILES = ("VT323-Regular.ttf", "OFL.txt")
LICENSE_FILE = "OFL.txt"
BASE_URL = "https://raw.githubusercontent.com/google/fonts/{commit}/" + SOURCE_PATH
COMMIT_RE = re.compile(r"[0-9a-f]{40}")
OFL_TITLE = b"SIL OPEN FONT LICENSE Version 1.1"
FONT_MAGIC = (b"\x00\x01\x00\x00", b"true", b"OTTO")
"""The first four bytes of a TrueType or OpenType font."""


class FetchError(Exception):
    """A download was refused: changed license, not a font, or a file that differs."""


def sha256(data: bytes) -> str:
    """Return the hex SHA-256 digest of ``data``."""
    return hashlib.sha256(data).hexdigest()


def load_manifest() -> dict[str, Any]:
    """Return the parsed manifest, or an empty dict before the first fetch."""
    if not MANIFEST.is_file():
        return {}
    return tomllib.loads(MANIFEST.read_text(encoding="utf-8"))


def write_manifest(commit: str, digests: dict[str, str]) -> None:
    """Write the manifest for ``commit``, recording each file's SHA-256."""
    lines = [
        "# VT323, the welcome screen's display face, vendored unmodified (ADR-0016 §2).",
        "# Written by packaging/fetch_fonts.py.",
        'name = "VT323"',
        'designer = "Peter Hull"',
        'copyright = "Copyright 2011, The VT323 Project Authors (peter.hull@oikoi.com)"',
        'license = "OFL-1.1"',
        'repository = "https://github.com/google/fonts"',
        f'commit = "{commit}"',
        f'path = "{SOURCE_PATH}"',
        'upstream = "https://github.com/phoikoi/VT323"',
        "",
        "# file = SHA-256",
        "[files]",
        *(f'"{name}" = "{digest}"' for name, digest in sorted(digests.items())),
    ]
    MANIFEST.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def download(url: str) -> bytes:
    """Return the body of an HTTPS ``url``.

    Raises:
        FetchError: The URL is not HTTPS.
    """
    if not url.startswith("https://"):
        raise FetchError(f"refusing a non-HTTPS URL: {url}")
    # The scheme check above is what S310 asks for; ruff can't see it, hence the noqa.
    headers = {"User-Agent": "cadd-calculator-font-fetch"}
    request = urllib.request.Request(url, headers=headers)  # noqa: S310
    with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310
        data: bytes = response.read()
    return data


def check() -> list[str]:
    """Offline check that the vendored files match the manifest. Returns the problems."""
    manifest = load_manifest()
    if not manifest:
        return [f"{MANIFEST} is missing"]
    digests: dict[str, str] = manifest["files"]
    problems = []
    for name in FILES:
        path = FONT_DIR / name
        if not path.is_file():
            problems.append(f"{path} is missing")
        elif sha256(path.read_bytes()) != digests.get(name):
            problems.append(f"{name} does not match its manifest hash")
    extra = sorted(p.name for p in FONT_DIR.iterdir() if p.name not in {*FILES, MANIFEST.name})
    problems += [f"{name} is not listed in the manifest" for name in extra]
    return problems


def fetch(commit: str, known: dict[str, str]) -> None:
    """Download the font and its license at ``commit``, verify them, and vendor them.

    Args:
        commit: The google/fonts commit to pin, a full 40-character SHA.
        known: Hashes already recorded for this commit, to detect changed files.

    Raises:
        FetchError: The license isn't the OFL 1.1, the font isn't a font, or a file
            differs from the hash recorded for this commit.
    """
    base = BASE_URL.format(commit=commit)
    downloads = {name: download(f"{base}/{name}") for name in FILES}
    if OFL_TITLE not in downloads[LICENSE_FILE]:
        raise FetchError("VT323 is not under the SIL Open Font License 1.1 any more; review")
    for name, data in downloads.items():
        if name.endswith(".ttf") and not data.startswith(FONT_MAGIC):
            raise FetchError(f"{name} is not a TrueType or OpenType font")
        if known.get(name) and known[name] != sha256(data):
            raise FetchError(f"{name} at {commit} changed since it was recorded; review it")
    FONT_DIR.mkdir(parents=True, exist_ok=True)
    for name, data in downloads.items():
        (FONT_DIR / name).write_bytes(data)
    write_manifest(commit, {name: sha256(data) for name, data in downloads.items()})


def main(argv: list[str] | None = None) -> int:
    """Run the command line and return the exit status."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else None)
    parser.add_argument("--commit", help="move the pinned google/fonts commit (re-hashes)")
    parser.add_argument("--check", action="store_true", help="verify files offline and exit")
    args = parser.parse_args(argv)

    if args.check:
        problems = check()
        for problem in problems:
            print(f"fetch_fonts: {problem}", file=sys.stderr)
        return 1 if problems else 0

    manifest = load_manifest()
    commit = args.commit or manifest.get("commit")
    if not commit or not COMMIT_RE.fullmatch(commit):
        print("fetch_fonts: give --commit with a full 40-character SHA", file=sys.stderr)
        return 2
    known: dict[str, str] = manifest.get("files", {}) if commit == manifest.get("commit") else {}
    try:
        fetch(commit, known)
    except (FetchError, OSError) as exc:
        print(f"fetch_fonts: {exc}", file=sys.stderr)
        return 1
    where = FONT_DIR.relative_to(ROOT)
    print(f"VT323 at google/fonts {commit[:12]}: {', '.join(FILES)} in {where}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
