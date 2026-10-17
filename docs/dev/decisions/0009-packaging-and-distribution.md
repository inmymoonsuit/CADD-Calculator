# ADR-0009: Packaging and distribution

* **Status:** **Proposed**. To be accepted after a packaging spike (roadmap milestone 0.3).
* **Date:** 2026-10-16

## Context

Users should install a normal desktop app with no Python knowledge, on Windows, macOS,
and Linux. The maintainer also asked for a *compiled* application.

## Proposed decision

* **Build:** `pyside6-deploy`, Qt's official tool, which drives **Nuitka**. Nuitka compiles
  Python to C and produces a standalone folder with Qt as replaceable shared libraries
  (LGPL-friendly, ADR-0008). Fallback: PyInstaller.
* **Installers per OS:**
  * Windows: an Inno Setup `.exe` installer, or MSI via WiX. Later, a `winget` manifest.
  * macOS: a `.app` in a `.dmg`, signed and notarized. Universal2, or separate arm64 and
    x86_64 builds.
  * Linux: AppImage first, then Flatpak (Flathub) and/or `.deb`.
* **CI:** GitHub Actions builds installers on each OS's runner when a version tag is
  pushed, and attaches them to a GitHub Release.
* **Branded editions (ADR-0008, item 4):** CI builds only the generic installers. A
  branded edition is built outside CI from the same tag, with a branding pack applied at
  build time. It is never attached to public releases.
* **PyPI:** also publish `cadd-calculator` for people who want the library or CLI
  (`pipx install cadd-calculator`).
* **Versioning:** SemVer. The single source is `caddcalc.__version__`.

## Open questions (decide in the spike)

* **Code signing costs.** Windows SmartScreen warns on unsigned apps; options are an OV/EV
  certificate, Azure Trusted Signing, or SignPath's free OSS program. macOS requires an Apple
  Developer account ($99/yr) or users must override Gatekeeper.
* **Antivirus false positives.** Nuitka and PyInstaller binaries are often flagged.
  Signing helps. Exclude `builds/` locally.
* **Auto-update:** probably not in 1.0. A "check for updates" link to GitHub Releases instead.
* **Telemetry:** **none.** The app makes no network calls (recorded here so it isn't added casually).

## Alternatives considered

* **Briefcase (BeeWare)**: produces native installers on every OS from one config, but its
  Qt support is less proven than pyside6-deploy. Worth comparing in the spike.
* **PyInstaller**: mature, but it bundles bytecode rather than compiling, and it is
  frequently flagged by antivirus software.
