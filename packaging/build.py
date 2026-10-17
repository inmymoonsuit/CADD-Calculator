"""Build the desktop app as a standalone folder with pyside6-deploy and Nuitka (ADR-0009).

    uv sync --extra gui --group build
    uv run python packaging/build.py                     # the public, unbranded edition
    uv run python packaging/build.py --branding NAME     # the pack in branding/NAME/
    uv run python packaging/build.py --branding DIR      # the pack in any folder

Add ``--smoke-test`` to start the built app and check it, and ``--archive`` to pack the
folder into a .zip (Windows), .tar.gz (Linux), or ditto .zip (macOS). Output goes to
``builds/<edition>/``, which is git-ignored, like ``branding/``.

Branded builds (ADR-0008 item 4, ADR-0011) copy only ``branding.toml``, the files it
names, and its notice and license files. They are refused when the ``CI`` or
``GITHUB_ACTIONS`` environment variable is set, so a public CI runner never makes one.
"""

from __future__ import annotations

import argparse
import configparser
import json
import os
import platform
import re
import shlex
import shutil
import subprocess
import sys
import time
from importlib.metadata import version as dist_version
from pathlib import Path

from PySide6.QtGui import QImage

from caddcalc import __version__
from caddcalc.calculators import REFERENCE_TABLES
from caddcalc.gui.branding import (
    GENERIC,
    PACK_DIR_NAME,
    PACK_FILE,
    Branding,
    BrandingError,
    load_branding,
)
from icons import ROOT, ensure_qt_app, save_icns, save_ico

BUILDS = ROOT / "builds"
BRANDING_DIR = ROOT / "branding"
"""Local branding packs live here, one folder per pack. The folder is git-ignored."""
LAUNCHER = Path(__file__).resolve().parent / "launcher.py"
EXE_STEM = "CADDCalculator"
NOTICE_WORDS = ("NOTICE", "LICENSE", "LICENCE", "COPYING")
"""Pack files whose names contain one of these ship with the app, e.g. ART-NOTICE.md."""
COMPANY = "CADD Calculator contributors"


class BuildError(Exception):
    """A build step failed; the message says which and why."""


def main(argv: list[str] | None = None) -> int:
    """Run the build from the command line and return the exit status."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--branding",
        metavar="PACK",
        help="a branding pack: a folder, or the name of one in branding/ (default: none)",
    )
    parser.add_argument("--mode", choices=["standalone", "onefile"], default="standalone")
    parser.add_argument("--smoke-test", action="store_true", help="start the built app, check it")
    parser.add_argument("--runs", type=int, default=3, help="smoke-test starts to time (default 3)")
    parser.add_argument("--archive", action="store_true", help="pack the output for distribution")
    parser.add_argument("--verbose", action="store_true", help="show pyside6-deploy's log")
    args = parser.parse_args(argv)
    try:
        branding = choose_branding(args.branding)
        report = build(branding, args.mode, verbose=args.verbose)
        output, exe = Path(str(report["output"])), Path(str(report["executable"]))
        if args.smoke_test:
            report["smoke_test"] = smoke_test(exe, output, branding, args.runs)
        if args.archive:
            archive = make_archive(output)
            report["archive"] = str(archive)
            report["archive_mb"] = round(archive.stat().st_size / 1e6, 1)
    except (BuildError, BrandingError) as exc:
        print(f"build.py: error: {exc}", file=sys.stderr)
        return 1
    report_path = output.with_name(f"{output.name}.build.json")
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


# --- choosing the edition ---------------------------------------------------------------


def running_in_ci() -> bool:
    """Whether a CI system runs this build (``CI`` or ``GITHUB_ACTIONS`` is set)."""
    return any(os.environ.get(v, "").lower() in {"1", "true"} for v in ("CI", "GITHUB_ACTIONS"))


def resolve_pack(pack: str) -> Path:
    """A folder path, or a bare name meaning ``branding/<name>/``."""
    path = Path(pack)
    if not path.is_dir() and len(path.parts) == 1:
        path = BRANDING_DIR / pack
    if not (path / PACK_FILE).is_file():
        raise BuildError(
            f"no branding pack at {path} (it needs a {PACK_FILE}). "
            f"Keep local packs in {BRANDING_DIR}, which is git-ignored."
        )
    return path


def choose_branding(pack: str | None) -> Branding:
    """GENERIC without a pack. A branded edition is never built in CI."""
    if pack is None:
        return GENERIC
    if running_in_ci():
        raise BuildError(
            "branded editions are never built in CI (ADR-0008 item 4). "
            "Build them outside CI from the release tag."
        )
    return load_branding(resolve_pack(pack))


# --- building ---------------------------------------------------------------------------


def platform_tag() -> str:
    """Return the platform part of output names, e.g. ``windows-x64``."""
    system = {"win32": "windows", "darwin": "macos"}.get(sys.platform, sys.platform)
    machine = platform.machine().lower()
    arch = {"amd64": "x64", "x86_64": "x64", "arm64": "arm64", "aarch64": "arm64"}.get(
        machine, machine
    )
    return f"{system}-{arch}"


def numeric_version(text: str) -> str:
    """Windows version resources take up to four numbers: 0.1.0.dev0 becomes 0.1.0.0."""
    match = re.match(r"\d+(?:\.\d+){0,3}", text)
    parts = (match.group(0) if match else "0").split(".")
    return ".".join(parts + ["0"] * (4 - len(parts)))


def stage_pack(branding: Branding, dest: Path) -> None:
    """Copy the files the pack uses, plus its notice and license files, into ``dest``.

    Anything else in the pack folder (source art, drafts) stays behind.
    """
    if branding.source is None:
        raise BuildError("the generic edition has no branding pack to stage")
    notices = [
        p
        for p in branding.source.iterdir()
        if p.is_file() and any(word in p.name.upper() for word in NOTICE_WORDS)
    ]
    for f in (*branding.files, *notices):
        target = dest / f.relative_to(branding.source)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(f, target)


def exe_icon(branding: Branding, work: Path) -> Path:
    """The icon file each platform's executable needs, converted from PNG if necessary."""
    source = branding.icon or GENERIC.icon
    if source is None:
        raise BuildError("no icon to convert for the executable")
    wanted = {"win32": ".ico", "darwin": ".icns"}.get(sys.platform, ".png")
    if source.suffix.lower() == wanted:
        return source
    ensure_qt_app()
    image = QImage(str(source))
    if image.isNull():
        raise BuildError(f"cannot read icon {source}")
    out = work / f"app{wanted}"
    if wanted == ".ico":
        save_ico(image, out)
    elif wanted == ".icns":
        save_icns(image, out)
    else:
        image.save(str(out))
    return out


def nuitka_args(branding: Branding, staged_pack: Path | None) -> list[str]:
    """Return the Nuitka options for an edition, passed through pyside6-deploy's spec."""
    args = [
        "--noinclude-qt-translations",
        "--assume-yes-for-downloads",  # Nuitka fetches its C compiler on first use
        "--include-package-data=caddcalc",  # the generic icon and the reference tables
        f"--company-name={COMPANY}",
        f"--product-name={branding.name}",
        f"--file-description={branding.name}",
        f"--file-version={numeric_version(__version__)}",
        f"--product-version={numeric_version(__version__)}",
        f"--copyright=Copyright {COMPANY}. Apache-2.0.",
        "--report=compilation-report.xml",
    ]
    if sys.platform == "win32":
        args.append("--windows-console-mode=disable")
    if sys.platform == "darwin":
        args += [f"--macos-app-name={branding.name}", f"--macos-app-version={__version__}"]
    if staged_pack is not None:
        args.append(f"--include-data-dir={staged_pack}={PACK_DIR_NAME}")
    return args


def write_spec(
    path: Path, *, title: str, icon: Path, exec_dir: Path, mode: str, extra: list[str]
) -> None:
    """Write the pyside6-deploy spec file for one build to ``path``."""
    spec = configparser.ConfigParser(interpolation=None)
    spec["app"] = {
        "title": title,
        "project_dir": ".",
        "input_file": f"{EXE_STEM}.py",
        "exec_directory": str(exec_dir),
        "project_file": "",
        "icon": str(icon),
    }
    spec["python"] = {"packages": "Nuitka"}
    spec["qt"] = {
        "qml_files": "",
        "excluded_qml_plugins": "",
        "modules": "Core,Gui,Widgets,Svg",  # Svg: the recolored Tabler icons
        "plugins": "",
    }
    # pyside6-deploy splits extra_args with shlex, so quote paths that contain spaces.
    spec["nuitka"] = {"macos.permissions": "", "mode": mode, "extra_args": shlex.join(extra)}
    with path.open("w", encoding="utf-8") as fh:
        spec.write(fh)


def build(branding: Branding, mode: str, *, verbose: bool = False) -> dict[str, object]:
    """Build one edition with pyside6-deploy and report what was built.

    Args:
        branding: The edition to build; ``GENERIC`` for the public build.
        mode: ``"standalone"`` for a folder, or ``"onefile"``.
        verbose: Print pyside6-deploy's log even when the build succeeds.

    Returns:
        Facts about the build (output paths, sizes, versions) for the JSON report.

    Raises:
        BuildError: pyside6-deploy failed, or the output is wrong for the edition.
    """
    edition_dir = BUILDS / branding.edition
    work = edition_dir / "work"
    name = f"{EXE_STEM}-{__version__}-{branding.edition}-{platform_tag()}"
    if mode == "onefile":
        name += "-onefile"
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True)
    # Replace this build's earlier output (and its archive and reports), nothing else.
    for old in [*edition_dir.glob(name), *edition_dir.glob(f"{name}.*")]:
        shutil.rmtree(old) if old.is_dir() else old.unlink()

    shutil.copy2(LAUNCHER, work / f"{EXE_STEM}.py")
    staged = None
    if not branding.is_generic:
        staged = work / "pack"
        stage_pack(branding, staged)
    write_spec(
        work / "pysidedeploy.spec",
        title=name,
        icon=exe_icon(branding, work),
        exec_dir=edition_dir,
        mode=mode,
        extra=nuitka_args(branding, staged),
    )

    deploy = shutil.which("pyside6-deploy", path=str(Path(sys.executable).parent))
    if deploy is None:
        raise BuildError("pyside6-deploy not found; run `uv sync --extra gui --group build`")
    command = [deploy, "-c", "pysidedeploy.spec", "--no-install", "--force", "--no-warn"]
    if verbose:
        command.append("--verbose")
    print(f"Building {branding.name} ({branding.edition}, {mode}) ...", flush=True)
    log = work / "deploy.log"
    started = time.perf_counter()
    with log.open("w", encoding="utf-8") as fh:
        result = subprocess.run(command, cwd=work, stdout=fh, stderr=subprocess.STDOUT, check=False)
    seconds = time.perf_counter() - started
    if verbose or result.returncode:
        print(log.read_text(encoding="utf-8", errors="replace"))
    if result.returncode:
        raise BuildError(f"pyside6-deploy failed (exit {result.returncode}); log: {log}")

    output, exe = locate_output(edition_dir, name, mode)
    if output.is_dir():
        for notice in ("LICENSE.md", "THIRD_PARTY_NOTICES.md"):
            shutil.copy2(ROOT / notice, output / notice)
        bundled_pack = exe.parent / PACK_DIR_NAME
        if branding.is_generic and bundled_pack.exists():
            raise BuildError(f"a generic build must not contain {bundled_pack}")
        if not branding.is_generic and not (bundled_pack / PACK_FILE).is_file():
            raise BuildError(f"the branding pack is missing from {bundled_pack}")
        if sys.platform != "darwin":  # the .app bundle's layout is unchecked (ADR-0009)
            for missing in missing_tables(exe.parent):
                raise BuildError(f"the reference table {missing} is missing from the build")

    files = [p for p in output.rglob("*") if p.is_file()] if output.is_dir() else [output]
    return {
        "edition": branding.edition,
        "name": branding.name,
        "version": __version__,
        "platform": platform_tag(),
        "mode": mode,
        "output": str(output),
        "executable": str(exe),
        "build_seconds": round(seconds),
        "size_mb": round(sum(p.stat().st_size for p in files) / 1e6, 1),
        "files": len(files),
        "exe_mb": round(exe.stat().st_size / 1e6, 1),
        "python": platform.python_version(),
        "pyside6": dist_version("PySide6-Essentials"),
        "nuitka": dist_version("Nuitka"),
        "reference_tables": [f"{s.package}/{s.filename}" for s in REFERENCE_TABLES],
    }


def missing_tables(app_dir: Path) -> list[str]:
    """Return the shipped reference tables that aren't in a standalone build's folder."""
    return [
        f"{spec.package}/{spec.filename}"
        for spec in REFERENCE_TABLES
        if not (app_dir.joinpath(*spec.package.split(".")) / spec.filename).is_file()
    ]


def locate_output(edition_dir: Path, name: str, mode: str) -> tuple[Path, Path]:
    """Return (the folder or file to ship, the executable to run)."""
    if sys.platform == "darwin":
        app = edition_dir / f"{name}.app"
        return app, app / "Contents" / "MacOS" / EXE_STEM
    suffix = ".exe" if sys.platform == "win32" else ".bin"
    if mode == "onefile":
        exe = edition_dir / f"{name}{suffix}"
        return exe, exe
    dist = edition_dir / f"{name}.dist"
    output = edition_dir / name
    dist.rename(output)
    return output, output / f"{EXE_STEM}{suffix}"


# --- checking and packing ---------------------------------------------------------------


def smoke_test(exe: Path, output: Path, branding: Branding, runs: int) -> dict[str, object]:
    """Start the built app ``runs`` times with --smoke-test and check what it reports."""
    report_dir = output.with_name(f"{output.name}.smoke-test")
    shutil.rmtree(report_dir, ignore_errors=True)
    env = {k: v for k, v in os.environ.items() if k != "CADDCALC_BRANDING"}
    times = []
    for _ in range(max(1, runs)):
        started = time.perf_counter()
        result = subprocess.run(
            [str(exe), f"--smoke-test={report_dir}"], env=env, timeout=180, check=False
        )
        times.append(round(time.perf_counter() - started, 2))
        if result.returncode:
            raise BuildError(f"{exe} --smoke-test exited with {result.returncode}")
    report = json.loads((report_dir / "smoke-test.json").read_text(encoding="utf-8"))
    problems = []
    if report["name"] != branding.name or report["edition"] != branding.edition:
        problems.append(f"shows {report['name']!r}, expected {branding.name!r}")
    if not report["packaged"]:
        problems.append("did not detect that it is packaged")
    if not report["icon_loaded"]:
        problems.append("window icon did not load")
    if report["splash_shown"] != (branding.splash is not None):
        problems.append("splash screen shown/not shown unexpectedly")
    if report.get("reference_tables") != len(REFERENCE_TABLES):
        problems.append(
            f"loaded {report.get('reference_tables')} reference tables, "
            f"expected {len(REFERENCE_TABLES)}"
        )
    if problems:
        raise BuildError(f"smoke test failed: {'; '.join(problems)}")
    return {"start_to_exit_s": times, "report_dir": str(report_dir), **report}


def make_archive(output: Path) -> Path:
    """Pack ``output`` for distribution and return the archive (a file is returned as is)."""
    if sys.platform == "darwin":
        archive = output.with_suffix(".zip")
        subprocess.run(["ditto", "-c", "-k", "--keepParent", str(output), str(archive)], check=True)
        return archive
    if output.is_file():
        return output
    fmt = "zip" if sys.platform == "win32" else "gztar"
    return Path(shutil.make_archive(str(output), fmt, root_dir=output.parent, base_dir=output.name))


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
