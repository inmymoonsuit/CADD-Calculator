r"""Gather a release's files and write SHA256SUMS; and the release's tag checks (slice d6).

    python3 packaging/release_files.py collect downloads release --version 0.1.0a1 \
        --platforms Windows Linux [--signed signed --provider signpath]
    python3 packaging/release_files.py check-tag v0.1.0a1 0.1.0a1
    python3 packaging/release_files.py prerelease v0.1.0a1        # prints true or false

The release workflow runs these with the runner's own Python: they need only the standard
library. ``collect`` copies each chosen platform's files from the build artifacts, puts the
signed installer in place of the unsigned one when a signing provider ran, fails if a file
is missing or carries another version, and writes SHA256SUMS in ``sha256sum``'s format.
Which platforms a release carries is the workflow's ``RELEASE_PLATFORMS`` list
(docs/dev/packaging.md, "CI").
"""

from __future__ import annotations

import argparse
import hashlib
import re
import shutil
import sys
from pathlib import Path

PLATFORM_FILES = {
    "Windows": ("CADDCalculator-*-windows-*.zip", "CADDCalculator-*-windows-*-setup.exe"),
    "Linux": ("CADDCalculator-*-linux-*.tar.gz", "CADDCalculator-*-linux-*.AppImage"),
    "macOS": ("CADDCalculator-*-macos-*.zip", "CADDCalculator-*-macos-*.dmg"),
    "Python": ("cadd_calculator-*.whl", "cadd_calculator-*.tar.gz"),
}
"""Each platform a release can carry, and the files it must have, one of each pattern."""

INSTALLER = "CADDCalculator-*-setup.exe"
PRERELEASE = re.compile(r"v\d+(\.\d+)*(a|b|rc)\d+(\.post\d+)?(\.dev\d+)?|v\d+(\.\d+)*\.dev\d+")
"""A PEP 440 pre-release or development version, as a tag: v0.1.0a1, v1.0rc2, v0.2.dev3."""


class ReleaseError(Exception):
    """The release's files or tag are wrong: a file missing, or a version that differs."""


def sha256(path: Path) -> str:
    """Return a file's hex SHA-256 digest."""
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def collect(
    downloads: Path,
    release: Path,
    version: str,
    platforms: list[str],
    signed: Path | None = None,
    provider: str = "",
) -> list[Path]:
    """Copy the chosen platforms' files into ``release``, write SHA256SUMS; return them.

    Raises:
        ReleaseError: A platform is unknown, a file is missing or has another version, or a
            provider signed the installer and the signed file isn't there.
    """
    unknown = [p for p in platforms if p not in PLATFORM_FILES]
    if unknown or not platforms:
        raise ReleaseError(f"unknown platforms {unknown}; choose from {sorted(PLATFORM_FILES)}")
    release.mkdir(parents=True, exist_ok=False)
    for platform in platforms:
        for pattern in PLATFORM_FILES[platform]:
            matches = sorted(downloads.glob(pattern))
            if len(matches) != 1:
                raise ReleaseError(f"{platform}: expected one {pattern}, found {len(matches)}")
            [path] = matches
            if not re.search(rf"-{re.escape(version)}[-.]", path.name):
                raise ReleaseError(f"{path.name} isn't version {version}")
            shutil.copy2(path, release / path.name)
    if provider:
        # A provider signed the installer: the release must carry that file, never the
        # unsigned one it replaces (S&R's d6 M2).
        found = sorted(signed.glob(INSTALLER)) if signed else []
        unsigned = sorted(release.glob(INSTALLER))
        if len(found) != 1 or len(unsigned) != 1 or found[0].name != unsigned[0].name:
            raise ReleaseError(
                f"{provider} signed the installer, but the signed file isn't there to replace"
                f" the unsigned one (signed: {[p.name for p in found]})"
            )
        shutil.copy2(found[0], unsigned[0])
    files = sorted(release.iterdir())
    lines = [f"{sha256(path)}  {path.name}\n" for path in files]
    (release / "SHA256SUMS").write_text("".join(lines), encoding="utf-8", newline="\n")
    return files


def check_tag(tag: str, version: str) -> None:
    """Raise unless ``tag`` is ``v`` and the package's version, exactly.

    Raises:
        ReleaseError: They differ.
    """
    if tag != f"v{version}":
        raise ReleaseError(f"the tag {tag} doesn't match caddcalc.__version__ {version}")


def is_prerelease(tag: str) -> bool:
    """Whether ``tag`` names a pre-release or development version."""
    return PRERELEASE.fullmatch(tag) is not None


def main(argv: list[str] | None = None) -> int:
    """Run the command line; return the exit status."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    commands = parser.add_subparsers(dest="command", required=True)
    gather = commands.add_parser("collect", help="copy the files and write SHA256SUMS")
    gather.add_argument("downloads", type=Path)
    gather.add_argument("release", type=Path)
    gather.add_argument("--version", required=True)
    gather.add_argument("--platforms", nargs="+", required=True)
    gather.add_argument("--signed", type=Path)
    gather.add_argument("--provider", default="")
    tag = commands.add_parser("check-tag", help="the tag matches the version")
    tag.add_argument("tag")
    tag.add_argument("version")
    pre = commands.add_parser("prerelease", help="print true for a pre-release tag")
    pre.add_argument("tag")
    args = parser.parse_args(argv)
    try:
        if args.command == "collect":
            files = collect(
                args.downloads,
                args.release,
                args.version,
                args.platforms,
                args.signed,
                args.provider,
            )
            for path in files:
                print(f"{path.stat().st_size / 1e6:8.1f} MB  {path.name}")
        elif args.command == "check-tag":
            check_tag(args.tag, args.version)
        else:
            print("true" if is_prerelease(args.tag) else "false")
    except ReleaseError as exc:
        print(f"::error title=Release files::{exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
