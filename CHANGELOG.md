# Changelog

All notable changes are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses
[Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- **Phase 2b: the materials table (ADR-0014, amendments).**
  `sheet_metal/data/materials.toml` (version 1) defines the starter materials, keyed
  `al:5052`, `al:6061`, `cs:a1008`, `cs:a653`, `cs:a1011`, and `ss:304`, with their
  tempers. It gives cited minimum inside radii (AC 43.13-1B Table 4-6, and TO 1-1A-9
  Tables 2-15, 2-16, and A-31/A-32), MIL-HDBK-5J strengths with their basis, and two
  K-factor starting values (FAA-H-8083-31B's 0.445 and the textbook's 0.4), every value as
  its source states it. `sheet_metal.materials` loads and checks it, and
  `listed_bands()` reads a sheet within 2% of a listed thickness at that listing, else at
  the next one up. `Basis.RECOMMENDED_MINIMUM` is new, for a minimum bend radius. The
  table is the second in `REFERENCE_TABLES`, so the smoke report counts 2.
- Result checks, selections, and applied values for phase 2b (ADR-0014, amendments):
  `Calculator.checks` declares `ResultCheck`s that run after compute and add notes, never
  work, seeing the domain's choice selections (`DomainValues.selections`), which compute
  never sees. `DomainSettings.set()` takes an `origin` and a `note` for a cited value the
  user applied rather than typed (`ValueOrigin`): results name it, e.g. "Sheet Metal
  settings, starting value from FAA-H-8083-31B, p. 4-63", and carry the note while it's
  in use. Typing over the value drops both.
- Bands, conditions, and per-parent defaults for phase 2b (ADR-0014, amendments):
  `core.Band`, a range with included or excluded ends that a reference value applies
  across, never interpolated; `ReferenceValue.band`, `conditions`, and `quantity`; and
  `ReferenceTable.check_values()` refuses overlapping bands within a series (one
  quantity, from one source, under one set of conditions). `Option.default` lets a
  resolver mark the option a choice falls back to, so each material can default to its
  own temper.
- A stress dimension for phase 2b's material strengths (ADR-0005 and ADR-0014,
  amendments): `Dimension.STRESS`, in MPa, with kPa, GPa, psi, and ksi. Stresses show
  in ksi when lengths are in inches or feet and in MPa when they're metric, to
  `DisplayPrefs.stress_decimals` (1) places. `formatting.entry_unit()` gives the unit a
  bare number is read in.
- Welcome-screen docs: the art specification (docs/dev/design/welcome-screen.md), the
  `[welcome]` pack keys in packaging.md, the welcome screen in the user guide, and
  KI-020, the platform checks CI can't run on Wayland and macOS.
- `caddcalc.gui.welcome.WelcomeScreen` (ADR-0015): a frameless, application-modal card
  with an About button (ⓘ) and an X, a vertical logo strip, and 16:9 art with
  the name and version as live text on theme-coloured scrims (new palette roles
  `welcome_scrim` and `on_welcome_scrim`). Pack art and logos that can't be used,
  including art over 4096 px, fall back to generated art with a warning. Esc or the X
  closes it, dragging the top bar moves it, and it shrinks to fit a small screen.
  It shows at every start, before the main window is built, and blocks the main window
  until it's closed; Help > Welcome Screen reopens it. The smoke report gains
  `welcome_shown`, `welcome_art`, and `welcome_logo`, which the build checks.
- **Phase 2a: gauge systems (ADR-0014).** The Sheet Metal page offers a gauge: a
  system (Manufacturers' Standard, galvanized, US Standard 1893, or AWG) and a number,
  which derives the thickness every calculator shares, at the system's published
  precision. Results carry a nominal-thickness caution that points to the system's
  tolerance standard, and show how the thickness was computed. The data ships as a
  cited, versioned table, computed exactly from public-domain definitions and one
  cited fact, and checked against ADR-0014's release checklist
  (`docs/dev/research/release-checklist-gauges-v1.md`). The entries below give the
  details.
- Domain choices and derived values (ADR-0014 §2, phase 2a): a `Domain` can offer
  `choices`, whose `options` come from its `resolver`; option keys such as `"msg:12"` are
  public. A choice can depend on others (`Choice.depends_on`, e.g. a temper on a
  material), and its resolver sees only their selections. `DomainSettings.set_choice()`,
  `clear_choice()`, and `choice()` keep the user's selections; changing one clears any
  dependent selection it no longer offers, keeps the rest, and `cleared_choices()` names
  the ones cleared and whether each fell back to its default (`ClearedChoice`). Clear
  all (`clear_domain()`) returns each choice to its default.
  `for_domain()` fills `DomainValues.derived` with the `DerivedValue`s the selections
  give, each naming its table and its domain. A calculator takes a derived value after a
  typed or explicit one and before its default, names it as a derived source, and adds
  the value's note, such as a nominal caution, once whenever the value is used, naming
  the inputs that took it; only `run()` names them. An explicit input can carry such a
  note too (`run(explicit_notes=...)`), as a copy of a derived value does.
- Gauge systems for sheet metal (ADR-0014 §2, phase 2a): the Sheet Metal domain offers a
  `gauge` choice whose options name the system and the size, e.g. `"msg:12"` for 12 ga
  Manufacturers' Standard, `"galv:"`, `"uss:"`, and `"awg:"` for galvanized, US Standard
  1893 (as commonly used for stainless), and AWG. Choosing one derives the thickness at
  the system's published precision, e.g. 0.1046 in for `"msg:12"`, and results that use
  it carry a nominal-thickness caution pointing to the system's tolerance standard. The
  definitions ship as a cited, versioned table, `data/gauges.toml`; every thickness is
  computed from them exactly, and a result that uses one shows its work ahead of the
  calculator's (`DerivedValue.work`). No gauge is selected by default.
- The Sheet Metal page's gauge picker: a system, then a number; changing the system
  clears the number. The derived thickness shows as the field's placeholder, with its
  source, caution, and work under it, and a typed thickness takes precedence. On
  calculator pages a gauge's thickness inherits, reads only, and copies like a set
  value; a copy is named after the gauge and keeps the caution. Work shows each derived
  step's note, such as the value before rounding, in the app and the CLI.
- The packaged app's smoke report counts the reference tables it loaded, and the build
  checks that each one is bundled.
- A path for reporting a wrong or rights-encumbered reference value: a section in
  CONTRIBUTING.md and the *Reference value* issue template, linked from the README and
  the sheet-metal user guide (ADR-0014 §5.7).
- `core.expr.evaluate_exact()`: evaluates a formula with exact rational arithmetic, for
  values a standard defines, from the same expression its work shows. A non-integer
  power alone is computed to a stated number of digits; a float input, a function, and
  `pi` are refused, and so is any value over `MAX_EXACT_BITS`. `Step` moves to
  `core.steps`, still exported from `caddcalc.core`, and gains `substitution`, the text
  shown for symbols that aren't the calculator's, and `expression_unit`, the unit a
  formula yields when it isn't the base unit. Work in such a unit is shown in it, then in
  the display unit, e.g. `0.1046 in = 2.6568 mm`, and a step's `stated` value, such as
  US Standard 12 ga's `0.109375 in`, is shown as stated, never rounded for display. JSON
  output lists all three for every step, `null` when unused. `evaluate_exact` takes at
  most `MAX_EXACT_DIGITS` digits, and holds its inputs to the size bound too.
- Reference-data machinery for phase 2 (ADR-0014 §1), in `caddcalc.core.refdata`:
  `load_table()` reads a cited TOML table shipped in a package and checks it: a known
  schema version, only the content keys its domain module declares, each publication
  declared once (`TablePublication`, compared by title and by edition number) with a
  kind, license, edition, public-domain basis, and (for online ones) recorded terms of
  use that agree with ADR-0014 §5, and sources (`TableSource`) that each cite a place in
  one. `ReferenceTable.check_values()` checks that each value's defining source is
  declared and that no cite-only publication defines more values than its cap, itself
  bounded by a code-level ceiling; each `TableSpec` says how its values are built, so
  tests hold the ceiling across every shipped table. `ReferenceValue`, `TableSpec`, the
  `License`, `PublicationKind` (including `own_measurement`), `Basis`, and `TrustLevel`
  enums, and `nominal()`, the one place a standard's stated precision is applied,
  rounding exact `Fraction` or `Decimal` input only.
- Project skeleton: a layered `caddcalc` package (core, calculators, CLI, PySide6 GUI).
- Core framework: units and drafting-fraction parsing, a safe formula evaluator with
  show-work rendering, declarative calculators with references and verification status,
  and a registry with entry-point plugins.
- Sheet-metal calculators: bend allowance & deduction, flat length of a formed segment,
  V-die opening, and truncated cone flat pattern. Each has the legacy course method and a
  general method.
- Golden tests reproducing the original course spreadsheets.
- ADR-0013 accepted, with phase 1 as built, and ADR-0014 (materials and reference data
  for phase 2, accepted), with its research notes in
  `docs/dev/research/materials-data-sources.md`. ADR-0003, ADR-0005, ADR-0006, and the
  engineering guidelines are amended for domains, numeric intent, and the
  `caddcalc.domains` entry-point group.
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
  input's source, e.g. `(entered)` or `(default)`. `run(explicit_sources=...)` labels
  explicit inputs, e.g. "course example", without changing precedence; it accepts only
  explicit sources for keys in `inputs` and raises `UsageError` otherwise.
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
- The GUI's family rows open a settings page (ADR-0013 §8), generated from the domain's
  settings. An empty field means unset. Under each field are the setting's help and the
  calculators and methods that use it. **Clear all** unsets the family. A field applies
  on Enter or when focus leaves it, and is checked as you type. Refused text applies
  nothing, so the setting keeps its previous value, and it stays outlined in red and
  explained across page and unit switches until it is fixed. On a unit switch, such text
  typed without a unit gains the unit it was typed in ("5" becomes "5 in"). A family
  with no loaded calculator is still listed, marked "No calculators loaded". Values set
  here are kept for the session.
- Calculators inherit family settings (ADR-0013 §8, decisions C and D). Once a family
  value is set, each field that shares it shows the value, read-only, with a ticked
  "Use Sheet Metal value" box. Unticking overrides it for the session with an exact
  copy of the family value, labelled "copied from Sheet Metal settings" until edited,
  or "copied earlier from Sheet Metal settings" once the family value changes. Results
  follow each keystroke, but an edit is judged when it ends (Enter, leaving the field,
  or leaving the page or switching units): one that ends on the value in use, or on
  unreadable text, records nothing, so retyping a value never pins an override.
  Only overridden or edited values are passed to `run()` as inputs. A note under an
  overriding field shows both values, recomputed on every render, and the settings
  page shows "Overridden in N" with the calculators' names. Unreadable text stays
  outlined and explained across page and unit switches and applies nothing, and a note
  says when it is discarded because the field started inheriting. Clearing a field
  returns it to its default, shown as "default 0.1046". "Load course example" fills
  the course method's inputs with the course example, labelled "course example",
  overrides family values, and selects the course method, for calculators with a
  legacy method; other inputs are left as they were. Results in the GUI list each
  input with its source, as the CLI does.
- `core.formatting.entry_text()` is the one display rule for typed values (ADR-0013
  §9.3): a field shows the user's own text while it names its unit or its unit is the
  display unit, and otherwise the value converted, without re-reading any display text.
  `field_text()`, `display_unit()`, `describe_setting_uses()`, and
  `Registry.setting_uses()` support the settings page.

### Fixed
- The app, and the test suite, could crash on exit after the window closed (KI-019): the
  window's own widgets held it through their signal connections, so it was torn down
  during interpreter exit. Every CI job failed from it. The `caddcalc-gui` command also
  ignored its command-line arguments, `--smoke-test` included.
- KI-017: switching the GUI between in and mm no longer rounds the values in calculator
  fields. Typed text is kept and shown verbatim while its unit is the display unit, and
  other values are re-expressed from their base value; nothing is read back from the
  display.

### Changed
- The K-factor help names its cited starting values: 0.445 for aircraft aluminum (FAA),
  about 0.408 and 0.452 from *Machinery's Handbook* by material, and the textbook's 0.4.
- About names the license (Apache-2.0), and opens over whichever window is active.
- If the main window can't be built, the app says so and exits with status 1 instead of
  running on with no window. A pack's SVG logo must be self-contained, and the welcome
  screen's version line shows just the version.
- The main window gains a File menu with Exit, beside Help > About. Both come from
  `caddcalc.gui.actions.AppActions`, the app's shared commands, which carry Qt's menu
  roles so macOS puts About and Quit in the application menu (ADR-0015 §5).
- Branding packs: a `[welcome]` table (`art`, `art_focus`, `logo`) replaces the `splash`
  key (ADR-0015), and the splash screen and the smoke report's `splash_shown` are gone
  until the welcome screen replaces them. A pack that still names `splash` is refused
  with a message naming `[welcome]`. `packaging/make_welcome_template.py` draws a guide
  for the art, and the placeholder pack gains welcome parts.
- CI and release workflows use action versions that run on Node.js 24: checkout v7,
  setup-uv v10.3.0 (pinned by commit, as setup-uv no longer publishes major tags),
  cache v6, upload-artifact v7, and download-artifact v8.
- `Reference` gains optional `edition`, `locator`, `accessed`, and `scope` fields
  (ADR-0014). Its text adds the edition and locator when given, and `to_dict()` (so the
  JSON of each note's references) gains the four keys. A note shows each source's scope
  after it, e.g. "(AC 43.13-1B, Table 4-6: aerospace bench practice)".
- The GUI's coloured text and field outlines (errors, the Notes heading, fields a note
  concerns) come from new palette roles, so they follow the light and dark themes; a
  test keeps hex colours out of the GUI code.
- `Result.warnings` becomes `Result.notes`, a tuple of `Note`s instead of strings. A
  note has a `NoteKind` (`warning`, `limit_exceeded`, `no_applicable_value`, or
  `infeasible`), its text, its `references`, and its `subjects`, the parameter or output
  keys it concerns. A `limit_exceeded` note must cite a reference. `ctx.note(text, kind,
  references=..., subjects=...)` makes notes and checks the subjects; `ctx.warn(text)`
  is short for a warning. In `to_dict()` and `--json`, `notes` is a list of objects
  with `kind`, `text`, `references`, and `subjects`. The CLI and GUI head the section
  "Notes" and prefix each kind but a warning, e.g. "Not makeable: …"; the GUI marks
  each kind with its own icon and outlines the fields a note concerns. A radius below
  the thickness is a warning (a rule of thumb, not a cited limit), and a segment too
  short for its bends is infeasible. Nothing has been released yet, so this changes the
  shape outright, with no deprecation path.
- `Calculator.domain` holds a domain id (`"sheet_metal"`), not a display name. A
  calculator naming an unknown domain fails registration with a "did you mean" hint
  that matches domain IDs and names, and `Registry.by_domain()` is keyed by `Domain`.
- `UnknownCalculatorError` and `UnknownDomainError` print their message without the
  quotes `KeyError` adds, so the CLI shows `error: No calculator 'x'.`
- A calculator default that doesn't parse or is out of range fails registration with
  `SpecError`, as a definition bug, instead of an input error. The message quotes the
  default as written, gives its value and the bound in named base units, e.g. "bad default
  '5 in' (= 127 mm), which must be at most 10 mm". `Registry()` and
  `DomainSettings()` start empty and are filled only through their checked methods.
- Parameter and domain-setting symbols must be usable in formulas: an identifier that
  isn't a Python keyword or an evaluator function or constant. Domain setting symbols
  must also be unique.
- The Sheet Metal thickness setting's help warns that gauge numbers mean different
  thicknesses in different gauge systems, and the K-factor setting's help gives the
  cited range of starting values (about 0.35 to 0.45, approaching 0.5 for large R/T) and
  the test-bend advice. The user guide and glossary give the same cited range.
- A unit of the wrong kind now reads "'3 deg' is an angle, but a length is expected".
- Range errors name the unit and use the display unit, e.g. the CLI's
  "Material thickness (T) must be greater than 0 in".
- `default_registry()` moved from `caddcalc.core` to `caddcalc.calculators`, so core no
  longer depends on the calculators layer above it (ADR-0003, ADR-0006).
- The window title and Help > About come from the active branding. About always keeps
  the version, the disclaimer, and the link to the source code.
