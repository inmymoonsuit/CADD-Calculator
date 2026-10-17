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
- Engineering guidelines (`docs/dev/engineering-guidelines.md`, ADR-0012), enforced in CI:
  Google-style docstrings and a best-practice ruff rule set, import-linter layer contracts
  (`uv run lint-imports`), and mypy strict. The codebase was brought into line.
- `scripts/launch_app.cmd` and `scripts/launch_app.sh` run the work-in-progress app from the
  checkout, with an optional `--branding FOLDER` (`docs/dev/launching.md`).
- Domains (ADR-0013): `caddcalc.core.Domain` declares a calculator family, and
  `Registry.register_domain()`, `domain()`, and `domains()` manage them. Plugins add
  domains through the `caddcalc.domains` entry-point group; every domain is registered
  before any calculator. A plugin can't redefine a built-in domain, and a plugin
  calculator with its own ID prefix may join any domain. A bad item in a plugin's list
  is recorded as `name[index]` and the rest still load. `Registry(entry_points=...)` and
  `default_registry(entry_points=...)` take the plugin source, so tests can pass a fake.
  `caddcalc list --json` reports `domain` and `domain_name`.
- Shared parameters and input provenance (ADR-0013): a `Param(shared=True)` inherits
  the domain setting with its key, checked at registration. `Calculator.run()` takes
  `settings=DomainValues(...)` and picks each input as explicit, then domain setting,
  then default. An out-of-range value raises `OutOfRangeError`, which carries the value,
  bound, parameter, and source; `core.formatting.describe_error()` words it in display
  units, and a domain setting's error says to override it in the calculator. Settings for
  another domain raise `UsageError`, the new error for API misuse. `Result.input_sources`
  records every input's `InputSource` (`core.provenance`), and `to_dict()` includes it,
  with a derived value's `reference` as a `Reference` or `null`. The CLI prints each
  input's source, e.g. `(entered)` or `(default)`.
- The Sheet Metal domain shares thickness, inside radius, and K-factor (ADR-0013, decision A).
  Its calculators build these parameters from the domain settings, keeping their own
  defaults: the cone keeps 0.0747 in, the V-die calculator shares R and T only in the
  method that uses each, and K is shared only by K-factor methods. The die ratio P stays
  per calculator.
- `DomainSettings`, the in-memory model of the domain settings a user sets during a session
  (ADR-0013 §7). It is immutable and starts empty; its setters are the only way to add a
  value, and they check the setting's key, dimension, and range. Every method takes the
  `Domain`. Each value is a `TypedValue`: the user's text, its exact base-unit parse, the
  unit applied, and whether the text named that unit (§9), from the new
  `parse_quantity_detailed()`. A `TypedValue` built directly must agree with its own
  text, or it raises `UsageError`. `for_domain()` returns the `DomainValues` that `run()`
  takes. Nothing is saved to disk. `Domain.values(thickness=...)` also builds checked `DomainValues`: an
  unknown key raises `UsageError` naming the domain's settings, and an out-of-range value
  raises `OutOfRangeError`. Their label always comes from `Domain.settings_label`, e.g.
  "Sheet Metal settings". Building `DomainValues` directly checks only that it has a label.

### Changed
- `Calculator.domain` holds a domain id (`"sheet_metal"`), not a display name. A
  calculator naming an unknown domain fails registration with a "did you mean" hint
  that matches domain IDs and names, and `Registry.by_domain()` is keyed by `Domain`.
- `UnknownCalculatorError` and `UnknownDomainError` print their message without the
  quotes `KeyError` adds, so the CLI shows `error: No calculator 'x'.`
- A calculator default that doesn't parse or is out of range fails registration with
  `SpecError`, as a definition bug, instead of an input error. `Registry()` and
  `DomainSettings()` start empty and are filled only through their checked methods.
- Parameter and domain-setting symbols must be usable in formulas: an identifier that
  isn't a Python keyword or an evaluator function or constant. Domain setting symbols
  must also be unique.
- A unit of the wrong kind now reads "'3 deg' is an angle, but a length is expected".
- Range errors name the unit and use the display unit, e.g. the CLI's
  "Material thickness (T) must be greater than 0 in".
- `default_registry()` moved from `caddcalc.core` to `caddcalc.calculators`, so core no
  longer depends on the calculators layer above it (ADR-0003, ADR-0006).
- The window title and Help > About come from the active branding. About always keeps
  the version, the disclaimer, and the link to the source code.
