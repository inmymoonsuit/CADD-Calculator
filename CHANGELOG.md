# Changelog

All notable changes are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses
[Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- Project skeleton: a layered `caddcalc` package (core, calculators, CLI, PySide6 GUI).
- Core framework: units and drafting-fraction parsing, a safe formula evaluator with
  show-work rendering, declarative calculators with references and verification status,
  and a registry with entry-point plugins.
- Sheet-metal calculators: bend allowance & deduction, flat length of a formed segment,
  V-die opening, and truncated cone flat pattern. Each has the legacy course method and a
  general method.
- Golden tests reproducing the original course spreadsheets.
- Developer docs (architecture, ADRs 0001 to 0010, known issues, engineering log, roadmap,
  legacy transcription) and user docs.
- CI on Windows, macOS, and Linux.
- Licensed under Apache-2.0.
- Packaging: `packaging/build.py` builds the desktop app as a standalone folder with
  pyside6-deploy and Nuitka (pinned to 4.1.1), with an optional smoke test and archive
  (ADR-0009, `docs/dev/packaging.md`).
- Branding hook: an optional branding pack (`branding.toml` with a name, icon, splash, and
  About text) is applied at build time with `build.py --branding PACK`, or at run time with
  the `CADDCALC_BRANDING` environment variable (ADR-0011). The public build stays unbranded.
- An interim generic app icon, drawn in code.
- `caddcalc-gui --smoke-test[=DIR]` opens the window, optionally writes a report and a
  screenshot to DIR, and exits. It is used to check packaged builds.
- UI color palette (crimson, slate, amber, ink) with light and dark role mappings in
  `gui/assets/palette.toml`, documented in `docs/dev/design/palette.md`. A test keeps every
  text/background pair at or above WCAG AA contrast.
- Tabler Icons 3.49.0 (MIT), vendored with only the icons the app uses, pinned by SHA-256
  in a manifest, refreshed with `packaging/fetch_tabler_icons.py`, and recolored from the
  palette for light and dark schemes (`docs/dev/design/icons.md`). Icons appear in the
  calculator list, Help > About, and the results' warnings and input errors.
- `THIRD_PARTY_NOTICES.md`, shipped in packaged builds and in the wheel's license files,
  and credited in Help > About.
- A sketch of a release workflow that builds the generic edition when a version tag is
  pushed and drafts a GitHub release.

### Changed
- The window title and Help > About come from the active branding. About always keeps
  the version, the disclaimer, and the link to the source code.
