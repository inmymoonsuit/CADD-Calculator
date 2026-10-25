"""Vendor the license texts of the runtime that packaged builds bundle (KI-016).

    uv run python packaging/fetch_notices.py             # re-download, verify every hash
    uv run python packaging/fetch_notices.py --update    # after moving a pin: re-hash
    uv run python packaging/fetch_notices.py --check     # offline: the files match

Each text comes from its project's repository at a pinned tag, as a raw file, and the
manifest records its SHA-256, so a download that differs from what was reviewed is
refused. Qt's own third-party notices are collected from every ``qt_attribution.json``
in qtbase at its tag, for the Qt modules and plugins a build ships. The build copies the
folder into the app's ``licenses/`` and fails if a text is missing; THIRD_PARTY_NOTICES.md
is the index (docs/dev/packaging.md, "Notices").
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tomllib
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
NOTICES_DIR = ROOT / "packaging" / "notices"
MANIFEST = NOTICES_DIR / "manifest.toml"
RAW = "https://raw.githubusercontent.com"
API = "https://api.github.com/repos"

QT_TAG = "v6.12.0"
"""qtbase's tag, matching the locked PySide6-Essentials."""
CPYTHON_TAG = "v3.12.14"
"""The CPython release the build's Python reports."""
QT_THIRD_PARTY = "Qt-third-party.txt"
QT_MODULES = frozenset({"qtcore", "qtgui", "qtdbus", "qtsvg", "qtwaylandcompositor"})
"""Qt modules whose third-party code ships: Core, Gui (with its platform plugins, the
Wayland ones on Linux), DBus (Linux), and Svg. Network, Sql, and Test stay out."""
QT_SKIPPED_PATHS = (
    "tests/",
    "util/",
    "cmake/",
    "src/testlib/",
    "src/testinternal/",
    "src/3rdparty/android/",
    "src/3rdparty/wasm/",
    "src/3rdparty/gradle/",
)
"""Attribution files for platforms, tools, and tests no build ships."""


@dataclass(frozen=True)
class Text:
    """One license text: the file it's saved as, what it covers, and where it comes from.

    A text with no URL is the project's own, written for the app (the Microsoft runtime's
    notice); it's committed, not downloaded, and its hash is checked all the same.
    """

    file: str
    covers: str
    url: str | None


TEXTS = (
    Text(
        "LGPL-3.0.txt",
        "Qt 6, PySide6, Shiboken6",
        f"{RAW}/qt/qtbase/{QT_TAG}/LICENSES/LGPL-3.0-only.txt",
    ),
    Text(
        "GPL-3.0.txt",
        "the GPL-3.0 that LGPL-3.0 builds on",
        f"{RAW}/qt/qtbase/{QT_TAG}/LICENSES/GPL-3.0-only.txt",
    ),
    Text(
        "Python-LICENSE.txt",
        "CPython (PSF License 2.0, and its history)",
        f"{RAW}/python/cpython/{CPYTHON_TAG}/LICENSE",
    ),
    Text(
        "Python-incorporated-software.rst",
        "software CPython includes: OpenSSL, expat, libffi, zlib, libmpdec, and more",
        f"{RAW}/python/cpython/{CPYTHON_TAG}/Doc/license.rst",
    ),
    Text(
        "Microsoft-Visual-C++-runtime.txt",
        "the Microsoft Visual C++ runtime DLLs (Windows builds): the app's own notice",
        None,
    ),
    Text(
        "expat-COPYING.txt",
        "expat (pyexpat), at the release python-build-standalone 3.12.14 carries",
        f"{RAW}/libexpat/libexpat/R_2_8_3/expat/COPYING",
    ),
    Text(
        "OpenSSL-LICENSE.txt",
        "OpenSSL's libcrypto (Apache-2.0), at the release the Windows build ships",
        f"{RAW}/openssl/openssl/openssl-3.5.7/LICENSE.txt",
    ),
    Text(
        "libffi-LICENSE.txt",
        "libffi (_ctypes)",
        f"{RAW}/python/cpython-source-deps/libffi-3.4.4/LICENSE",
    ),
    Text(
        "zlib-LICENSE.txt",
        "zlib, at the release python-build-standalone 3.12.14 carries",
        f"{RAW}/madler/zlib/v1.3.2/LICENSE",
    ),
    Text(
        "bzip2-LICENSE.txt", "bzip2 (_bz2)", f"{RAW}/python/cpython-source-deps/bzip2-1.0.8/LICENSE"
    ),
    Text(
        "xz-5.2-COPYING.txt",
        "xz's liblzma before 5.4 (_lzma)",
        f"{RAW}/python/cpython-source-deps/xz-5.2.5/COPYING",
    ),
    Text(
        "xz-COPYING.0BSD.txt",
        "xz's liblzma from 5.4 on (_lzma)",
        f"{RAW}/tukaani-project/xz/v5.8.1/COPYING.0BSD",
    ),
    Text(
        "libuuid-COPYING.txt",
        "util-linux's libuuid (_uuid), linked into libpython on Linux: the app's own copy of"
        " its source's notice, since its COPYING has no copyright line",
        None,
    ),
    Text(
        "libedit-LICENSE.txt",
        "libedit (readline), linked into libpython on Linux: the app's own copy of its"
        " BSD-3-Clause notice, since libedit has no license file to fetch",
        None,
    ),
    Text(
        "ncurses-COPYING.txt",
        "ncurses (curses, readline), linked into libpython on Linux",
        f"{RAW}/ThomasDickey/ncurses-snapshots/v6_5_20240427/COPYING",
    ),
    Text(
        "ICU-LICENSE.txt",
        "ICU 73, which PySide6's Linux wheel bundles for Qt Core (Unicode-3.0 and its notices)",
        f"{RAW}/unicode-org/icu/release-73-2/icu4c/LICENSE",
    ),
    Text(
        "Nuitka-LICENSE.txt",
        "Nuitka's runtime, compiled into the executable (Apache-2.0)",
        f"{RAW}/Nuitka/Nuitka/4.1.1/LICENSE.txt",
    ),
)


class FetchError(Exception):
    """A download was refused: not HTTPS, or a file that differs from the manifest."""


def sha256(data: bytes) -> str:
    """Return the hex SHA-256 digest of ``data``."""
    return hashlib.sha256(data).hexdigest()


def download(url: str) -> bytes:
    """Return the body of an HTTPS ``url``.

    Raises:
        FetchError: The URL is not HTTPS.
    """
    if not url.startswith("https://"):
        raise FetchError(f"refusing a non-HTTPS URL: {url}")
    with urllib.request.urlopen(url, timeout=60) as response:  # noqa: S310 (HTTPS only)
        body: bytes = response.read()
    return body


def qt_attributions() -> list[tuple[str, dict[str, Any]]]:
    """Return (attribution file, entry) for each third-party entry a build ships."""
    listing = json.loads(download(f"{API}/qt/qtbase/git/trees/{QT_TAG}?recursive=1"))
    if listing.get("truncated"):
        raise FetchError("qtbase's file listing came back truncated")
    paths = sorted(
        item["path"]
        for item in listing["tree"]
        if item["path"].endswith("qt_attribution.json")
        and not item["path"].startswith(QT_SKIPPED_PATHS)
    )
    entries = []
    for path in paths:
        parsed = json.loads(download(f"{RAW}/qt/qtbase/{QT_TAG}/{path}"), strict=False)
        for entry in parsed if isinstance(parsed, list) else [parsed]:
            parts = entry.get("QtParts", ["libs"])
            if entry.get("QDocModule") in QT_MODULES and "libs" in parts:
                entries.append((path, entry))
    return entries


def qt_third_party_text() -> bytes:
    """Assemble Qt's third-party notices: each entry's name, copyright, and license text."""
    lines = [
        f"Third-party code in Qt {QT_TAG.lstrip('v')} (qtbase), as it ships in CADD Calculator's",
        "packaged builds. Collected by packaging/fetch_notices.py from each",
        f"qt_attribution.json at https://github.com/qt/qtbase/tree/{QT_TAG}.",
        "",
    ]
    license_cache: dict[str, str] = {}
    for path, entry in qt_attributions():
        folder = path.rsplit("/", 1)[0]
        copyright_ = entry.get("Copyright", "")
        if isinstance(copyright_, list):
            copyright_ = "\n".join(copyright_)
        lines += [
            "=" * 78,
            f"{entry['Name']}{' ' + entry['Version'] if entry.get('Version') else ''}",
            f"Used: {entry.get('QtUsage', '')}",
            f"License: {entry.get('License', '')} ({entry.get('LicenseId', '')})",
        ]
        if copyright_:
            lines += ["", copyright_]
        files = entry.get("LicenseFiles") or (
            [entry["LicenseFile"]] if entry.get("LicenseFile") else []
        )
        for name in files:
            url = f"{RAW}/qt/qtbase/{QT_TAG}/{folder}/{name}"
            if url not in license_cache:
                license_cache[url] = download(url).decode("utf-8", errors="replace")
            lines += ["", license_cache[url].rstrip()]
        lines.append("")
    return ("\n".join(lines) + "\n").encode("utf-8")


def load_manifest() -> dict[str, str]:
    """Return the recorded digests, file name to SHA-256; empty before the first fetch."""
    if not MANIFEST.is_file():
        return {}
    data = tomllib.loads(MANIFEST.read_text(encoding="utf-8"))
    files: dict[str, str] = data.get("files", {})
    return files


def write_manifest(digests: dict[str, str]) -> None:
    """Write the manifest: the pins, and each file's SHA-256."""
    lines = [
        "# License texts that packaged builds ship in licenses/ (KI-016).",
        "# Written by packaging/fetch_notices.py; THIRD_PARTY_NOTICES.md is the index.",
        f'qt_tag = "{QT_TAG}"',
        f'cpython_tag = "{CPYTHON_TAG}"',
        "",
        "# file = SHA-256",
        "[files]",
        *(f'"{name}" = "{digest}"' for name, digest in sorted(digests.items())),
    ]
    MANIFEST.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def expected_files() -> list[str]:
    """Return every file the notices folder must hold, the manifest aside."""
    return sorted([text.file for text in TEXTS] + [QT_THIRD_PARTY])


def check(folder: Path = NOTICES_DIR) -> list[str]:
    """Return problems with the vendored texts in ``folder``: missing or changed files."""
    recorded = load_manifest()
    problems = []
    for name in expected_files():
        path = folder / name
        if name not in recorded:
            problems.append(f"{name} is not in the manifest")
        elif not path.is_file():
            problems.append(f"{name} is missing")
        elif sha256(path.read_bytes()) != recorded[name]:
            problems.append(f"{name} differs from the manifest")
    return problems


def fetch(update: bool) -> int:
    """Download every text; with ``update``, re-hash, otherwise refuse a changed one."""
    recorded = load_manifest()
    NOTICES_DIR.mkdir(parents=True, exist_ok=True)
    bodies = {
        text.file: download(text.url) if text.url else (NOTICES_DIR / text.file).read_bytes()
        for text in TEXTS
    }
    bodies[QT_THIRD_PARTY] = qt_third_party_text()
    digests = {name: sha256(body) for name, body in bodies.items()}
    if not update:
        changed = [n for n, d in digests.items() if recorded.get(n) != d]
        if changed:
            raise FetchError(f"differs from the manifest: {', '.join(sorted(changed))}")
    for name, body in bodies.items():
        (NOTICES_DIR / name).write_bytes(body)
    if update:
        write_manifest(digests)
    print(f"{len(bodies)} license texts in {NOTICES_DIR.relative_to(ROOT)}")
    return 0


def main(argv: list[str] | None = None) -> int:
    """Run the command line; return the exit status."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--update", action="store_true", help="re-download and re-hash")
    mode.add_argument("--check", action="store_true", help="offline: verify the files")
    args = parser.parse_args(argv)
    if args.check:
        problems = check()
        for problem in problems:
            print(f"fetch_notices: {problem}", file=sys.stderr)
        return 1 if problems else 0
    try:
        return fetch(update=args.update)
    except FetchError as exc:
        print(f"fetch_notices: error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
