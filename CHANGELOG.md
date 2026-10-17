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
