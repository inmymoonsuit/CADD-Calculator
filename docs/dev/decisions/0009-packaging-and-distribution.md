# ADR-0009: Packaging and distribution

* **Status:** **Accepted** for the build tool: pyside6-deploy driving Nuitka, standalone
  folder, Nuitka pinned to pyside6-deploy's version. Decided by the Windows spike on
  2026-10-17 (results below). The per-OS installers, the macOS and Linux builds, and code
  signing are still **proposed** until they have been built in CI.
* **Date:** 2026-10-16 (proposed); 2026-10-17 (spike, build tool accepted)

## Context

Users should install a normal desktop app with no Python knowledge, on Windows, macOS,
and Linux. The maintainer also asked for a *compiled* application.

## Decision

* **Build:** `pyside6-deploy`, Qt's official tool, which drives **Nuitka**. Nuitka compiles
  Python to C and produces a standalone folder with Qt as replaceable shared libraries
  (LGPL-friendly, ADR-0008). `packaging/build.py` writes the pyside6-deploy spec and runs
  it; see [packaging.md](../packaging.md).
  * **Standalone folder, not onefile.** Onefile works but unpacks itself to a temp folder on
    every start: 0.9 s slower in the spike, and a pattern antivirus software dislikes.
    Installers will wrap the folder.
  * **Pin Nuitka** to the version in pyside6-deploy's `default.spec` for the locked
    PySide6 (`nuitka==4.1.1` for PySide6 6.12, in the `build` dependency group). The newer
    Nuitka 4.3 built an app that crashed when it opened (engineering log, 2026-10-17).
  * Fallback if Nuitka is ever blocked: PyInstaller, then Briefcase. Neither was needed
    in the spike, so neither was tried.
* **Installers per OS (proposed):**
  * Windows: an Inno Setup `.exe` installer, or MSI via WiX. Later, a `winget` manifest.
  * macOS: a `.app` in a `.dmg`, signed and notarized. Universal2, or separate arm64 and
    x86_64 builds.
  * Linux: AppImage first, then Flatpak (Flathub) and/or `.deb`.
  * Until then, the build makes a portable archive per OS (`build.py --archive`).
* **CI (sketched):** GitHub Actions builds the generic edition on each OS's runner when a
  version tag is pushed, and attaches the archives to a **draft** GitHub Release
  (`.github/workflows/release.yml`). The maintainer publishes the draft by hand.
* **Branded editions (ADR-0008, item 4):** CI builds only the generic installers. A
  branded edition is built outside CI from the same tag, with a branding pack applied at
  build time (`build.py --branding PACK`, ADR-0011). It is never attached to public
  releases, and the build script refuses branded builds in CI.
* **PyPI:** also publish `cadd-calculator` for people who want the library or CLI
  (`pipx install cadd-calculator`).
* **Versioning:** SemVer. The single source is `caddcalc.__version__`. Windows version
  resources get its first four numbers (`0.1.0.dev0` becomes `0.1.0.0`).

## Spike results (2026-10-17)

Windows 11, 24 cores. CPython 3.12.14 (uv's python-build-standalone), PySide6-Essentials
6.12.0, Nuitka 4.1.1, and MinGW-w64 gcc 15.2, downloaded by Nuitka because Visual Studio
isn't installed.

| | Standalone folder | Onefile |
|---|---|---|
| Size | 74.6 MB in 55 files (6.9 MB exe); 28.0 MB zipped | 20.6 MB, one file |
| Build time | 21 to 42 s with a warm ccache. The first build adds a ~270 MB compiler download. | 71 s |
| Start to exit, `--smoke-test`, real desktop | 2.5 to 3.6 s warm; 5.7 s for the first start after a build | 3.2 to 3.5 s |
| Same, offscreen platform (no system fonts) | 0.22 to 0.27 s | not measured |

* **Startup.** On the maintainer's PC almost all of those seconds are Qt's text and font
  setup, not Python or Nuitka: a source run takes 2.4 to 2.9 s as well. This PC has 2,454
  font families. Profiling a source run, Qt's DirectWrite font handling took about 2 s
  (0.5 s to list the families, 1.5 s for the first `show()`, probably font fallback). With
  the GDI font engine the whole start took 1.3 s. Offscreen, the app is ready 0.13 s after
  `main()` starts. KI-015 tracks this; measure on a typical lab PC.
* **The branded path works.** A placeholder-branded build (standalone and onefile) showed
  the pack's name, icon, splash, and About text, and found the pack next to the executable.
  Its splash screen adds about 1 s before the main window appears (3.4 to 3.6 s ready).
* **Contents.** Qt Core, Gui, Widgets, and Svg; the `windows`, `offscreen`, `minimal`, and
  `direct2d` platform plugins; image format plugins; the Windows 11 style. The build
  also includes QtNetwork, the TLS plugins, and OpenSSL's `libcrypto` (about 10 MB), which
  the app doesn't use. Excluding them is an easy size win to try.
* **Antivirus.** Nothing was flagged. The output is inside the project folder, which the
  maintainer's antivirus excludes; Nuitka's cache was not excluded.
* **Problems found:** Nuitka 4.3's crash, MinGW include paths over MAX_PATH inside the
  Claude desktop app's sandbox, and an environment leak in the build script's smoke test.
  All three are in the engineering log. pyside6-deploy can't find `dumpbin` without Visual
  Studio, so the spec names the Qt modules itself.

## Open questions

* **Code signing costs.** Windows SmartScreen warns on unsigned apps; options are an OV/EV
  certificate, Azure Trusted Signing, or SignPath's free OSS program. macOS requires an Apple
  Developer account ($99/yr) or users must override Gatekeeper.
* **Antivirus false positives.** Nuitka and PyInstaller binaries are often flagged.
  Signing helps. Exclude `builds/` locally.
* **Third-party notices.** The app folder bundles Qt (LGPL-3.0), Python, OpenSSL, and the
  MSVC runtime. Their notices must ship before public release (KI-016).
* **Auto-update:** probably not in 1.0. A "check for updates" link to GitHub Releases instead.
* **Telemetry:** **none.** The app makes no network calls (recorded here so it isn't added casually).

## Alternatives considered

* **Briefcase (BeeWare)**: produces native installers on every OS from one config, but its
  Qt support is less proven than pyside6-deploy. Not tried: pyside6-deploy worked once
  Nuitka was pinned.
* **PyInstaller**: mature, but it bundles bytecode rather than compiling, and it is
  frequently flagged by antivirus software. Kept as the fallback.
* **Running Nuitka directly**: works the same (the spike's bisection builds did this), but
  pyside6-deploy knows which Qt plugins and options PySide6 needs, and Qt maintains it.

## Amendments

### 2026-10-18: the build's checklist (ADR-0020's i5)

What every build must carry, and how it's checked. `packaging/build.py` fails the build
for a missing file, and its `--smoke-test` fails when the built app can't use one.
The file checks skip macOS, whose `.app` layout is still unchecked.

| Item | Bundled by | Checked by |
|---|---|---|
| The reference tables | `--include-package-data=caddcalc` | `missing_tables`; the smoke report's `reference_tables` (each loaded and built) |
| The display face and its OFL license | the same | `missing_fonts`; the report's `display_font` |
| **Our catalogs**, each language's `.mo` | compiled from the committed `.po` by the build (`scripts/i18n.py compile`), before Nuitka reads the package data; their `.po` and `.pot` sources left out (`--noinclude-data-files`) | `missing_catalogs`, which fails with no `.po` to check against; `catalog_sources`, none bundled; the report's `catalogs`, the languages the built app finds |
| **Qt's `qtbase_*.qm` catalogs** | `--include-data-files` from the build's PySide6 into the same folder in the build (`PySide6/translations/` on Windows, `PySide6/Qt/translations/` on Linux and macOS), where its Qt looks; every other Qt translation stays out | `missing_catalogs`; the report's `qt_catalog`, that Qt loads its German catalog from the build |
| `LICENSE.md` and `THIRD_PARTY_NOTICES.md` | copied into the folder | (copied; what the notices still lack is KI-016) |
| The branding pack, or none | `--include-data-dir`, branded builds only | a generic build has no `branding/`, a branded one has its `branding.toml`; the report's name, edition, icon, and welcome art |

* **The wheel** takes our catalogs too: `hatch_build.py`, hatchling's build hook,
  compiles them into a staging folder and includes each in `caddcalc/locale`. So Babel is
  a build requirement, beside hatchling; an editable install reads the source tree, where
  `scripts/i18n.py compile` puts them. The hook fails with no `.po` to compile, and the
  wheel leaves out the `.po` and `.pot`, which the sdist keeps. CI builds the wheel and
  checks it holds each language's `.mo` and nothing else (`scripts/i18n.py
  check-wheel`).
* **Qt's catalogs for languages we don't have yet** ship anyway. The window loads one only
  with a catalog of ours for the same language (ADR-0020, amendments), so until then
  they cost space: 33 files, 5.8 MB, in PySide6 6.12. In return, a new language needs
  no packaging change.

### 2026-10-25: release integrity and PyPI, as built (ADR-0022's slice d6)

* **Checksums:** `release.yml`'s `release-files` job writes `SHA256SUMS` over every release
  file, including the wheel and the sdist, and attaches it to the draft release. It runs on
  dry runs too.
* **Attestations:** on tags, `actions/attest` (which replaced
  `actions/attest-build-provenance`) attests each file named in `SHA256SUMS`. Only that job
  has `id-token: write` and `attestations: write`.
* **PyPI**, decided above, is built: Trusted Publishing through
  `pypa/gh-action-pypi-publish`, on tags only, TestPyPI first, each upload behind an
  environment (`testpypi`, `pypi`) whose required reviewer is the maintainer. No token is
  stored. The maintainer's one-time setup is in [packaging.md](../packaging.md#pypi).
* Every action is pinned by commit SHA, and Dependabot proposes updates weekly.
