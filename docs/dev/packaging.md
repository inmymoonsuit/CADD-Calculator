# Packaging the desktop app

How to build the standalone app, and how branded editions work. The decisions behind it
are [ADR-0009](decisions/0009-packaging-and-distribution.md) (build tool, spike results),
[ADR-0011](decisions/0011-branding-packs.md) (branding packs), and
[ADR-0008](decisions/0008-licensing-and-third-party-assets.md) item 4 (branding policy).

## Quick start

```bash
uv sync --extra gui --group build
uv run python packaging/build.py --smoke-test --archive
```

The output goes to `builds/generic/` (git-ignored):

| Path | What it is |
|---|---|
| `CADDCalculator-<version>-generic-windows-x64/` | the app folder. Run `CADDCalculator.exe`. |
| `…-windows-x64.zip` | the same folder zipped, for handing out (`--archive`) |
| `…-windows-x64.smoke-test/` | `smoke-test.json` and a `window.png` screenshot (`--smoke-test`) |
| `…-windows-x64.build.json` | size, build time, tool versions, startup times |
| `work/` | pyside6-deploy's spec, the log, and Nuitka's compilation report |

The first build downloads Nuitka's C compiler (MinGW-w64 gcc, about 270 MB) and Dependency
Walker into Nuitka's cache. Later builds take 20 to 45 seconds because ccache keeps the
compiled C.

## Editions

| Command | Edition | Branding |
|---|---|---|
| `build.py` | `generic`, the public build | none: the built-in name and icon |
| `build.py --branding NAME` | the pack's `edition` | the pack in `branding/NAME/` |
| `build.py --branding DIR` | the pack's `edition` | the pack in `DIR`, e.g. a private repository |

Branded editions are built outside this repository's CI and never attached to public
releases (ADR-0008 item 4). `branding/` is git-ignored, so local packs aren't committed by accident.
Whoever builds a branded edition is responsible for permission to use the marks and art
in its pack.

The script refuses every branded build when the `CI` or `GITHUB_ACTIONS` environment
variable is set, so the public CI can't make one even by mistake.

### Testing the branded path without a real pack

```bash
uv run python packaging/make_placeholder_pack.py builds/placeholder-pack
uv run python packaging/build.py --branding builds/placeholder-pack --smoke-test
```

The placeholder pack is a magenta test pattern that says "not for distribution", with
the edition `placeholder`. To try any pack from a source checkout without building, set
`CADDCALC_BRANDING`:

```bash
CADDCALC_BRANDING=builds/placeholder-pack uv run caddcalc-gui
```

## Branding packs

A pack is a folder with a `branding.toml`:

```toml
schema = 1                                    # pack format version (optional)
edition = "example"                           # slug for folder names: a-z, 0-9, -
name = "CADD Calculator: Example Edition"     # window title and About heading
icon = "icon.png"                             # optional; .png (256 px or more) or .ico
splash = "splash.png"                         # optional; .png or .jpg
about = "about.html"                          # optional; .html fragment or .txt
```

* Paths are relative to the pack folder and must stay inside it.
* `icon` sets the window icon, and also the `.exe` icon. A PNG is converted to a
  multi-size `.ico` (Windows) or `.icns` (macOS) at build time.
* `about` replaces the one-line description in Help > About. The version, the
  disclaimer, and the link to the source code are always shown.
* The build copies only `branding.toml`, the files it names, and any file at the top of
  the pack whose name contains `NOTICE`, `LICENSE`, `LICENCE`, or `COPYING` (such as
  `ART-NOTICE.md` for the pack's art). Source art, drafts, and planning notes in the pack
  folder stay behind.
* The packaged app finds the pack in a `branding/` folder next to its executable. The
  window title changes, but the application name used for settings stays
  "CADD Calculator" in every edition.
* A broken pack at run time gives a warning and the generic branding. The build script
  checks the pack first and stops with the reason, so a broken pack can't ship.

The loader is `caddcalc.gui.branding`. It doesn't import Qt.

## Notices

The build copies `LICENSE.md` and `THIRD_PARTY_NOTICES.md` into the app folder. Third-party
assets inside the package, such as the Tabler icons and their `LICENSE.txt`, ride along
with the package data. See KI-016 for what the notices still lack.

## What the build does

1. Copies `packaging/launcher.py` into `work/` as `CADDCalculator.py`. pyside6-deploy
   compiles a script, not an entry point. The launcher calls `caddcalc.gui.app:main`.
2. Writes `work/pysidedeploy.spec`: the Qt modules (`Core,Gui,Widgets`), the icon, and
   the Nuitka options. Those include Windows version info, `--include-package-data=caddcalc`
   for the generic icon, and, for a branded build, `--include-data-dir=<staged pack>=branding`.
3. Runs `pyside6-deploy -c pysidedeploy.spec --no-install`, which runs Nuitka in standalone
   mode. Nuitka must already be installed by uv (the `build` dependency group).
4. Renames the `.dist` folder, copies `LICENSE.md` into it, and checks that a generic build
   has no `branding/` folder and a branded build has one, and that every reference table
   in `caddcalc.calculators.REFERENCE_TABLES`, such as `sheet_metal/data/gauges.toml`, is
   bundled (`--include-package-data=caddcalc` carries them).
5. With `--smoke-test`, starts the app with `--smoke-test=DIR` a few times (`--runs`). Each
   run opens the window, loads every reference table, writes the report, and exits. The
   script checks the reported name, edition, icon, splash, the number of reference
   tables loaded, and that the app knew it was packaged.

`--mode onefile` builds a single self-extracting executable instead. It works, branded too,
but starts about 0.9 s slower and unpacks to a temp folder on every start, which
antivirus software tends to dislike (ADR-0009).

## Troubleshooting

* **Use the pinned Nuitka.** `pyproject.toml` pins the version that pyside6-deploy's
  `default.spec` names (4.1.1 for PySide6 6.12). Nuitka 4.3 builds an app that crashes
  when it opens (engineering log, 2026-10-17). When PySide6 is upgraded, read the new
  `default.spec` and move the pin with it.
* **`structuredquerycondition.h: No such file or directory`** (or another missing MinGW
  header) means the compiler's include paths are longer than Windows' 260-character limit.
  This happened when the build ran inside the Claude desktop app, whose sandbox moves
  `%LOCALAPPDATA%` to a much longer path. Point Nuitka's cache at a short folder:
  `NUITKA_CACHE_DIR=C:\Users\<you>\.cache\nuitka`.
* **"Unable to find dumpbin"** from pyside6-deploy is harmless. It needs Visual Studio's
  `dumpbin` to find Qt module dependencies, so the spec lists the modules itself.
* **Antivirus.** No detections happened during the spike, but Nuitka builds are sometimes
  flagged. The build output stays under `builds/` in the project folder. If a file is
  quarantined, note its exact name before changing any exclusions.
* **Slow start on machines with many fonts.** See KI-015.

## CI

[`.github/workflows/release.yml`](../../.github/workflows/release.yml) builds the generic
edition on Windows, macOS, and Linux when a `v*` tag is pushed, and attaches the archives
to a **draft** GitHub release for the maintainer to publish. It never builds a branded
edition.

Status:
* It is a sketch from the 0.3 packaging spike. The Windows build and smoke test have run
  locally with the same commands, but the workflow hasn't run on GitHub yet, and the macOS
  and Linux jobs are untested.
* The output is a portable archive per OS. Real installers (Inno Setup, .dmg, AppImage)
  come later (roadmap 0.3).
* Nothing is signed yet (ADR-0009, open questions).
