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
import tomllib
from importlib.metadata import version as dist_version
from pathlib import Path

import PySide6
from PySide6.QtCore import QLibraryInfo, qVersion
from PySide6.QtGui import QImage

from caddcalc import __version__
from caddcalc.calculators import REFERENCE_TABLES
from caddcalc.core import i18n
from caddcalc.gui.branding import (
    GENERIC,
    PACK_DIR_NAME,
    PACK_FILE,
    PRODUCT_NAME,
    Branding,
    BrandingError,
    load_branding,
)
from caddcalc.gui.welcome_style import STYLE_FILE, style
from fetch_notices import NOTICES_DIR
from fetch_notices import check as check_notices
from fetch_notices import expected_files as notice_files
from icons import ROOT, ensure_qt_app, save_icns, save_ico

BUILDS = ROOT / "builds"
BRANDING_DIR = ROOT / "branding"
"""Local branding packs live here, one folder per pack. The folder is git-ignored."""
LAUNCHER = Path(__file__).resolve().parent / "launcher.py"
EXE_STEM = "CADDCalculator"
NOTICE_WORDS = ("NOTICE", "LICENSE", "LICENCE", "COPYING")
"""Pack files whose names contain one of these ship with the app, e.g. ART-NOTICE.md."""
COMPANY = "CADD Calculator contributors"
CATALOGS = ROOT / "src" / "caddcalc" / "locale"
"""The source catalogs: each language's .po, compiled to its .mo for the build."""
LOCALE_DIR = "caddcalc/locale"
"""Where a build keeps our compiled catalogs, as the package does."""
CATALOG_SOURCES = (".po", ".pot")
"""The catalogs' sources, which no build ships: the app reads only the compiled .mo."""
QT_CATALOG = "qtbase"
"""Qt's own text, such as standard buttons and a field's context menu, comes from its
``qtbase_<language>.qm`` catalogs, which ship beside it (ADR-0020 §1)."""


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
    parser.add_argument(
        "--installer",
        action="store_true",
        help="Windows: wrap the folder in an Inno Setup installer",
    )
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
        if args.installer:
            installer = make_installer(output, branding)
            report["installer"] = str(installer)
            report["installer_mb"] = round(installer.stat().st_size / 1e6, 1)
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


TRIMMED_QT_PLUGIN_FAMILIES = ("tls",)
"""Qt plugin families the build leaves out: TLS backends, for a network the app never uses."""
TRIMMED_IMAGE_FORMATS = ("qpdf", "qtiff", "qwebp", "qtga", "qwbmp", "qicns")
"""Qt image-format plugins the build leaves out. The app reads PNG and JPEG art, SVG and
ICO icons, and nothing else; ``.icns`` is made at build time, not read by the app."""
TRIMMED_PLATFORM_PLUGINS = ("qvnc",)
"""Qt platform plugins the build leaves out: VNC (Linux), which serves the window over a
network and would pull QtNetwork back in."""
TRIMMED_QT_MODULES = ("QtNetwork",)
"""Qt modules the build leaves out: nothing imports QtNetwork; only the TLS plugins and the
VNC platform plugin did."""


LICENSES_DIR = "licenses"
"""Where a build keeps the runtime's license texts, from packaging/notices/ (KI-016)."""


def copy_notices(output: Path) -> None:
    """Copy the project's license, the index, and the runtime's license texts into a build."""
    for notice in ("LICENSE.md", "THIRD_PARTY_NOTICES.md"):
        shutil.copy2(ROOT / notice, output / notice)
    folder = output / LICENSES_DIR
    folder.mkdir(exist_ok=True)
    for name in notice_files():
        shutil.copy2(NOTICES_DIR / name, folder / name)


def openssl_version(output: Path) -> str | None:
    """Return the OpenSSL release a build's libcrypto reports, or ``None`` if it has none."""
    for path in sorted(output.rglob("libcrypto*")):
        if path.is_file():
            match = re.search(rb"OpenSSL (\d+\.\d+\.\d+) ", path.read_bytes())
            if match:
                return match.group(1).decode()
    return None


def notice_version_problems(output: Path, index: str | None = None) -> list[str]:
    """Return what THIRD_PARTY_NOTICES.md gets wrong about the versions a build ships.

    It must name the Qt and PySide6 versions, and the libcrypto must be an OpenSSL 3
    release, since ``licenses/OpenSSL-LICENSE.txt`` is OpenSSL 3's license (M1, Low 1).
    """
    text = index if index is not None else (ROOT / "THIRD_PARTY_NOTICES.md").read_text("utf-8")
    problems = []
    qt, pyside = qVersion(), PySide6.__version__
    if f"### Qt {qt} and Qt for Python (PySide6, Shiboken6) {pyside}" not in text:
        problems.append(f"THIRD_PARTY_NOTICES.md doesn't name Qt {qt} and PySide6 {pyside}")
    ssl = openssl_version(output)
    if ssl is not None and not ssl.startswith("3."):
        problems.append(f"the build ships OpenSSL {ssl}, but the notice is OpenSSL 3's license")
    return problems


def missing_notices(output: Path) -> list[str]:
    """Return the notices a build lacks: our license, the index, or a runtime license text."""
    wanted = ["LICENSE.md", "THIRD_PARTY_NOTICES.md"]
    wanted += [f"{LICENSES_DIR}/{name}" for name in notice_files()]
    return [name for name in wanted if not (output / name).is_file()]


def trimmed_files(output: Path) -> list[str]:
    """Return the files in a build that the trim should have left out (docs/dev/packaging.md).

    Matches each platform's names: ``qpdf.dll``, ``libqpdf.so``, ``libqpdf.dylib``;
    ``QtNetwork.pyd``, ``Qt6Network.dll``, ``libQt6Network.so.6``, ``QtNetwork.framework``.
    """
    found = []
    for path in output.rglob("*"):
        name = path.name.lower()
        parts = [part.lower() for part in path.relative_to(output).parts]
        stem = name.removeprefix("lib").split(".")[0]
        if (
            ("imageformats" in parts and stem in TRIMMED_IMAGE_FORMATS)
            or ("platforms" in parts and stem in TRIMMED_PLATFORM_PLUGINS)
            or (any(family in parts for family in TRIMMED_QT_PLUGIN_FAMILIES) and path.is_file())
            or any(
                m.lower() in stem or m.lower().replace("qt", "qt6") in stem
                for m in TRIMMED_QT_MODULES
            )
        ):
            found.append(path)
    return sorted(str(p.relative_to(output)) for p in found)


def inclusion_reasons(report: Path) -> dict[str, str]:
    """Return why Nuitka included each library, by file name, from its compilation report.

    The reasons read like "Used by 'PySide6/qt-plugins/platforms/libqxcb.so'", so a file the
    trim should have left out names what pulled it in.
    """
    if not report.is_file():
        return {}
    import xml.etree.ElementTree as ET

    reasons = {}
    root = ET.parse(report).getroot()  # noqa: S314 (this build's own Nuitka report)
    for dll in root.iter("included_dll"):
        if dll.get("ignored") != "yes":
            reasons[dll.get("name", "").lower()] = dll.get("reason", "")
    return reasons


def qt_catalogs_dir(translations: Path | None = None, package: Path | None = None) -> str:
    """Return where a build keeps Qt's catalogs: where the running PySide6 keeps them.

    The folder is the one Qt reports for its translations, relative to the PySide6
    package, so the frozen app's Qt looks where the build put them. PySide6's wheels lay
    it out per platform: ``PySide6/translations`` on Windows, and
    ``PySide6/Qt/translations`` on Linux and macOS. A fixed Windows path broke the
    catalog check on both (engineering log, 2026-10-25).

    Args:
        translations: Qt's translations folder; the running PySide6's when ``None``.
        package: The PySide6 package folder; the running PySide6's when ``None``.
    """
    if translations is None:
        translations = Path(QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath))
    if package is None:
        package = Path(PySide6.__file__).parent
    inside = translations.resolve().relative_to(package.resolve())
    return (Path("PySide6") / inside).as_posix()


def qt_catalogs() -> list[Path]:
    """Return Qt's ``qtbase`` catalogs, from the PySide6 the build runs with."""
    folder = Path(QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath))
    return sorted(folder.glob(f"{QT_CATALOG}_*.qm"))


def compile_catalogs() -> list[str]:
    """Compile our catalogs into the source tree, where the build takes package data from.

    Returns:
        The languages compiled.

    Raises:
        BuildError: The catalog tool failed.
    """
    tool = ROOT / "scripts" / "i18n.py"
    result = subprocess.run(  # this interpreter, on the project's own script
        [sys.executable, str(tool), "compile"], capture_output=True, text=True, check=False
    )
    if result.returncode:
        raise BuildError(f"compiling the catalogs failed: {result.stdout}{result.stderr}")
    return list(i18n.shipped_languages(CATALOGS))


def nuitka_args(staged_pack: Path | None) -> list[str]:
    """Return the Nuitka options for an edition, passed through pyside6-deploy's spec.

    Of Qt's translations, only its ``qtbase`` catalogs ship: they're the text Qt shows
    in our window. The rest, for Qt modules we don't use, stay out. Of our catalogs, only
    the compiled ``.mo`` ship; their ``.po`` and ``.pot`` sources stay in the sdist, for
    translators (Nuitka matches them by where they'd go, ``*`` crossing folders).
    """
    qt_folder = Path(QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath))
    args = [
        "--noinclude-qt-translations",
        f"--include-data-files={qt_folder / f'{QT_CATALOG}_*.qm'}={qt_catalogs_dir()}/",
        *(f"--noinclude-data-files={LOCALE_DIR}/*{suffix}" for suffix in CATALOG_SOURCES),
        "--assume-yes-for-downloads",  # Nuitka fetches its C compiler on first use
        "--include-package-data=caddcalc",  # the generic icon and the reference tables
        f"--company-name={COMPANY}",
        f"--product-name={PRODUCT_NAME}",
        f"--file-description={PRODUCT_NAME}",
        f"--file-version={numeric_version(__version__)}",
        f"--product-version={numeric_version(__version__)}",
        f"--copyright=Copyright {COMPANY}. Apache-2.0.",
        "--report=compilation-report.xml",
        *(f"--noinclude-qt-plugins={family}" for family in TRIMMED_QT_PLUGIN_FAMILIES),
        *(f"--nofollow-import-to=PySide6.{module}" for module in TRIMMED_QT_MODULES),
        # The library too: Nuitka still follows the dependencies of a plugin it leaves out,
        # so libqvnc.so alone would bring libQt6Network back (engineering log, 2026-10-25).
        *(f"--noinclude-dlls=*{m.replace('Qt', 'Qt6', 1)}*" for m in TRIMMED_QT_MODULES),
        *(f"--noinclude-dlls=*imageformats*{plugin}*" for plugin in TRIMMED_IMAGE_FORMATS),
        *(f"--noinclude-dlls=*platforms*{plugin}*" for plugin in TRIMMED_PLATFORM_PLUGINS),
    ]
    if sys.platform == "win32":
        args.append("--windows-console-mode=disable")
    if sys.platform == "darwin":
        args += [f"--macos-app-name={PRODUCT_NAME}", f"--macos-app-version={__version__}"]
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
    for problem in check_notices():
        raise BuildError(f"packaging/notices: {problem}; run packaging/fetch_notices.py")
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
    languages = compile_catalogs()  # package data, so before the build reads it
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
        extra=nuitka_args(staged),
    )

    deploy = shutil.which("pyside6-deploy", path=str(Path(sys.executable).parent))
    if deploy is None:
        raise BuildError("pyside6-deploy not found; run `uv sync --extra gui --group build`")
    command = [deploy, "-c", "pysidedeploy.spec", "--no-install", "--force", "--no-warn"]
    if verbose:
        command.append("--verbose")
    print(f"Building {PRODUCT_NAME} ({branding.edition}, {mode}) ...", flush=True)
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
        copy_notices(output)
        for missing in missing_notices(output):
            raise BuildError(f"the notice {missing} is missing from the build (KI-016)")
        for problem in notice_version_problems(output):
            raise BuildError(problem)
        extras = trimmed_files(output)
        if extras:
            reasons = inclusion_reasons(work / "compilation-report.xml")
            listed = "; ".join(
                f"{extra} ({reasons.get(Path(extra).name.lower(), 'no reason recorded')})"
                for extra in extras
            )
            raise BuildError(f"the trim should have left these out: {listed}")
        bundled_pack = exe.parent / PACK_DIR_NAME
        if branding.is_generic and bundled_pack.exists():
            raise BuildError(f"a generic build must not contain {bundled_pack}")
        if not branding.is_generic and not (bundled_pack / PACK_FILE).is_file():
            raise BuildError(f"the branding pack is missing from {bundled_pack}")
        if sys.platform != "darwin":  # the .app bundle's layout is unchecked (ADR-0009)
            for missing in missing_tables(exe.parent):
                raise BuildError(f"the reference table {missing} is missing from the build")
            for missing in missing_fonts(exe.parent):
                raise BuildError(f"the display face's {missing} is missing from the build")
            for missing in missing_catalogs(exe.parent):
                raise BuildError(f"the catalog {missing} is missing from the build")
            for source in catalog_sources(exe.parent):
                raise BuildError(f"the catalog source {source} is in the build; only .mo ship")

    files = [p for p in output.rglob("*") if p.is_file()] if output.is_dir() else [output]
    return {
        "edition": branding.edition,
        "name": PRODUCT_NAME,
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
        "catalogs": languages,
        "qt_catalogs": len(qt_catalogs()),
        "openssl": openssl_version(output) if output.is_dir() else None,
    }


def missing_tables(app_dir: Path) -> list[str]:
    """Return the shipped reference tables that aren't in a standalone build's folder."""
    return [
        f"{spec.package}/{spec.filename}"
        for spec in REFERENCE_TABLES
        if not (app_dir.joinpath(*spec.package.split(".")) / spec.filename).is_file()
    ]


def missing_fonts(app_dir: Path) -> list[str]:
    """Return the display face's files that aren't in a standalone build's folder.

    Its manifest lists them: the font, and the license the OFL says ships with it.
    """
    assets = STYLE_FILE.parent
    font_dir = (assets / style().typography.display_file).parent
    manifest = tomllib.loads((font_dir / "manifest.toml").read_text(encoding="utf-8"))
    shipped = app_dir / font_dir.relative_to(ROOT / "src")
    return [
        f"{font_dir.relative_to(assets).as_posix()}/{name}"
        for name in manifest["files"]
        if not (shipped / name).is_file()
    ]


def missing_catalogs(app_dir: Path) -> list[str]:
    """Return the catalogs, ours and Qt's ``qtbase`` ones, missing from a build's folder.

    Ours are every language a .po exists for, compiled; Qt's are every ``qtbase`` catalog
    the build's PySide6 has (ADR-0009, the build's checklist).

    Raises:
        BuildError: There's no .po at all, so no list of ours to check the build against.
    """
    sources = sorted(CATALOGS.glob("*/LC_MESSAGES/caddcalc.po"))
    if not sources:
        raise BuildError(
            f"no catalog to check: no <language>/LC_MESSAGES/caddcalc.po in {CATALOGS}"
        )
    ours = [f"{LOCALE_DIR}/{path.parents[1].name}/LC_MESSAGES/caddcalc.mo" for path in sources]
    qt = [f"{qt_catalogs_dir()}/{path.name}" for path in qt_catalogs()]
    return [name for name in (*ours, *qt) if not (app_dir / name).is_file()]


def catalog_sources(app_dir: Path) -> list[str]:
    """Return the catalogs' sources, ``.po`` and ``.pot``, that a build's folder holds."""
    folder = app_dir / LOCALE_DIR
    found = [p for p in folder.rglob("*") if p.suffix in CATALOG_SOURCES] if folder.is_dir() else []
    return sorted(p.relative_to(app_dir).as_posix() for p in found)


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
    if report["name"] != PRODUCT_NAME or report["edition"] != branding.edition:
        problems.append(
            f"shows {report['name']!r} ({report['edition']}), "
            f"expected {PRODUCT_NAME!r} ({branding.edition})"
        )
    if not report["packaged"]:
        problems.append("did not detect that it is packaged")
    if not report["icon_loaded"]:
        problems.append("window icon did not load")
    if not report.get("welcome_shown"):
        problems.append("the welcome screen did not show")
    for part, path in (("art", branding.welcome_art), ("logo", branding.welcome_logo)):
        expected = "generic" if path is None else "pack"
        if report.get(f"welcome_{part}") != expected:
            problems.append(
                f"the welcome {part} came from {report.get(f'welcome_{part}')!r}, "
                f"expected {expected!r}"
            )
    family = style().typography.display_family
    if report.get("display_font") != family:
        problems.append(f"the display face is {report.get('display_font')!r}, expected {family!r}")
    if report.get("reference_tables") != len(REFERENCE_TABLES):
        problems.append(
            f"loaded {report.get('reference_tables')} reference tables, "
            f"expected {len(REFERENCE_TABLES)}"
        )
    languages = list(i18n.shipped_languages(CATALOGS))
    if report.get("catalogs") != languages:
        problems.append(f"found the catalogs {report.get('catalogs')}, expected {languages}")
    if not report.get("qt_catalog"):
        problems.append("Qt couldn't load its own catalog from the build")
    if problems:
        raise BuildError(f"smoke test failed: {'; '.join(problems)}")
    return {"start_to_exit_s": times, "report_dir": str(report_dir), **report}


INNO_SCRIPT = Path(__file__).resolve().parent / "windows" / "CADDCalculator.iss"
"""The Inno Setup script that wraps a standalone Windows build (ADR-0022, slice d3)."""


def find_iscc() -> Path:
    """Return Inno Setup 6's command-line compiler.

    Raises:
        BuildError: It isn't installed.
    """
    found = shutil.which("ISCC")
    candidates = [Path(found)] if found else []
    for base in ("ProgramFiles(x86)", "ProgramFiles", "LOCALAPPDATA"):
        root = os.environ.get(base)
        if root:
            candidates += [
                Path(root) / "Inno Setup 6" / "ISCC.exe",
                Path(root) / "Programs" / "Inno Setup 6" / "ISCC.exe",
            ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise BuildError("Inno Setup 6's ISCC.exe isn't installed (https://jrsoftware.org/isinfo.php)")


INSTALLER_LICENSE_NOTE = """

----------------------------------------------------------------------
Third-party components

CADD Calculator includes third-party components under their own licenses: Qt and
Qt for Python under the GNU LGPL v3, and others. Their notices and full license texts are
in THIRD_PARTY_NOTICES.md and the licenses folder, in the install folder.

On Windows it also includes Microsoft Visual C++ runtime files, which Microsoft lets
applications redistribute under its terms. By installing, you agree to the conditions
for those files in licenses\\Microsoft-Visual-C++-runtime.txt.
"""
"""What the installer's license page adds after LICENSE.md (Low 5)."""


def installer_license(output: Path, work: Path) -> Path:
    """Write the installer's license page: LICENSE.md, then the third-party note."""
    page = work / "installer-license.txt"
    text = (output / "LICENSE.md").read_text(encoding="utf-8").rstrip()
    page.write_text(text + INSTALLER_LICENSE_NOTE, encoding="utf-8", newline="\r\n")
    return page


def installer_defines(output: Path, icon: Path, license_page: Path) -> dict[str, str]:
    """Return the ISCC defines for wrapping ``output``: its folder, version, and names."""
    return {
        "SourceDir": str(output),
        "LicenseFile": str(license_page),
        "AppVersion": __version__,
        "NumericVersion": numeric_version(__version__),
        "IconFile": str(icon),
        "OutputDir": str(output.parent),
        "OutputBase": f"{output.name}-setup",
    }


def make_installer(output: Path, branding: Branding) -> Path:
    """Wrap a standalone Windows build in an Inno Setup installer; return its path.

    Raises:
        BuildError: Not a standalone Windows build, no Inno Setup, or ISCC failed.
    """
    if sys.platform != "win32" or not output.is_dir():
        raise BuildError("--installer needs a standalone Windows build")
    work = output.parent / "work"
    defines = installer_defines(output, exe_icon(branding, work), installer_license(output, work))
    command = [
        str(find_iscc()),
        "/Q",
        *(f"/D{k}={v}" for k, v in defines.items()),
        str(INNO_SCRIPT),
    ]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode:
        raise BuildError(f"ISCC failed (exit {result.returncode}): {result.stdout}{result.stderr}")
    installer = output.parent / f"{defines['OutputBase']}.exe"
    if not installer.is_file():
        raise BuildError(f"ISCC made no {installer.name}")
    return installer


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
