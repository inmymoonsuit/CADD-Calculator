r"""Render the winget manifests for a release, and validate them against winget's schema.

    uv run python packaging/windows/winget.py render --version 0.3.0 \\
        --url <the installer's release download URL> \\
        --sha256 <the installer's SHA-256> --out builds/winget
    uv run --no-project --with jsonschema==4.26.0 --with pyyaml==6.0.3 \\
        python packaging/windows/winget.py validate builds/winget

The templates in ``winget/`` use manifest schema 1.10.0. ``validate`` checks each
rendered file against that schema, downloaded from winget-cli at a pinned tag and checked
against its SHA-256. Submitting to winget-pkgs is the maintainer's job, after the first
signed release (docs/dev/packaging.md, "winget").
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import urllib.request
from pathlib import Path
from typing import Any

TEMPLATES = Path(__file__).resolve().parent / "winget"
SCHEMA_VERSION = "1.10.0"
SCHEMA_URL = (
    "https://raw.githubusercontent.com/microsoft/winget-cli/v1.29.380/schemas/JSON/"
    "manifests/v{v}/manifest.{kind}.{v}.json"
)
SCHEMA_SHA256 = {
    "installer": "cca7bea1fbdaa18a3d5231de7f9f896b1dd41283c33a03a0565771861d393b31",
    "version": "330a3ece4ed602afb0c4f35290d14dec1e188e7b3c2fb330893ac3daac82b547",
    "defaultLocale": "77e406d25b35f908f70fb893335155e9e8a83aa59a6f3e9f959692e995e51e3c",
}
VERSION_RE = re.compile(r"\d+(\.\d+){1,3}([-+.][0-9A-Za-z.]+)?")
SHA256_RE = re.compile(r"[0-9A-Fa-f]{64}")


class WingetError(Exception):
    """A value, a template, or a rendered manifest is wrong."""


def render(version: str, url: str, sha256: str, out: Path) -> list[Path]:
    """Fill the templates into ``out``; return the manifests written."""
    if not VERSION_RE.fullmatch(version):
        raise WingetError(f"not a version: {version!r}")
    if not url.startswith("https://") or not url.endswith(".exe"):
        raise WingetError(f"the installer URL must be an HTTPS .exe: {url!r}")
    if not SHA256_RE.fullmatch(sha256):
        raise WingetError(f"not a SHA-256: {sha256!r}")
    values = {"VERSION": version, "INSTALLER_URL": url, "INSTALLER_SHA256": sha256.upper()}
    out.mkdir(parents=True, exist_ok=True)
    written = []
    for template in sorted(TEMPLATES.glob("*.yaml.in")):
        text = template.read_text(encoding="utf-8")
        for key, value in values.items():
            text = text.replace("{{" + key + "}}", value)
        if "{{" in text:
            raise WingetError(f"{template.name} has a placeholder render doesn't fill")
        target = out / template.name.removesuffix(".in")
        target.write_text(text, encoding="utf-8", newline="\n")
        written.append(target)
    return written


def schema(kind: str) -> dict[str, Any]:
    """Return winget's manifest schema for ``kind``, checked against its pinned SHA-256."""
    url = SCHEMA_URL.format(v=SCHEMA_VERSION, kind=kind)
    with urllib.request.urlopen(url, timeout=60) as response:  # noqa: S310 (fixed HTTPS)
        body: bytes = response.read()
    if hashlib.sha256(body).hexdigest() != SCHEMA_SHA256[kind]:
        raise WingetError(f"winget's {kind} schema differs from the pinned one")
    parsed: dict[str, Any] = json.loads(body)
    return parsed


def validate(folder: Path) -> list[str]:
    """Return the problems in the rendered manifests in ``folder``; empty when valid."""
    import jsonschema  # type: ignore[import-untyped]  # only for validate, via uv --with
    import yaml  # type: ignore[import-untyped]

    problems = []
    manifests = sorted(folder.glob("*.yaml"))
    kinds = set()
    for path in manifests:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        kind = data.get("ManifestType")
        kinds.add(kind)
        if kind not in SCHEMA_SHA256:
            problems.append(f"{path.name}: unknown ManifestType {kind!r}")
            continue
        validator = jsonschema.Draft7Validator(schema(kind))
        problems += [f"{path.name}: {error.message}" for error in validator.iter_errors(data)]
    for kind in sorted(set(SCHEMA_SHA256) - kinds):
        problems.append(f"no {kind} manifest in {folder}")
    return problems


def main(argv: list[str] | None = None) -> int:
    """Run the command line; return the exit status."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    commands = parser.add_subparsers(dest="command", required=True)
    make = commands.add_parser("render", help="fill the templates for a release")
    make.add_argument("--version", required=True)
    make.add_argument("--url", required=True, help="the installer's release download URL")
    make.add_argument("--sha256", required=True, help="the installer's SHA-256")
    make.add_argument("--out", type=Path, required=True)
    check = commands.add_parser("validate", help="check rendered manifests against the schema")
    check.add_argument("folder", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "render":
            for path in render(args.version, args.url, args.sha256, args.out):
                print(path)
            return 0
        problems = validate(args.folder)
    except WingetError as exc:
        print(f"winget: error: {exc}", file=sys.stderr)
        return 1
    for problem in problems:
        print(f"winget: {problem}", file=sys.stderr)
    if not problems:
        print(f"winget: {args.folder} is valid against manifest schema {SCHEMA_VERSION}")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
