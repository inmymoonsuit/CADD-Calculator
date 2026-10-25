# Changelog

All notable changes are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses
[Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- Release integrity: every release attaches `SHA256SUMS` over all its files, and on tags
  each file gets a GitHub artifact attestation (`gh attestation verify`). The wheel and the
  sdist are built and checked on every run, and a tag publishes them to TestPyPI, then
  PyPI, through Trusted Publishing, each upload after the maintainer approves it. No token
  is stored.
- macOS: a .dmg holding the app and a link to /Applications; CI mounts it and starts the
  app from it. A user guide, "Installing", says plainly that the downloads aren't signed
  yet, and gives Microsoft's and Apple's first-run steps ("Run anyway", "Open Anyway").
  Notarization is stubbed in the release workflow, switched off.
- Linux: an AppImage of the packaged build, with a .desktop file and AppStream metainfo,
  made with pinned, checksummed appimagetool and runtime releases; and a Flathub manifest
  that builds the app from source on the KDE runtime with the PySide BaseApp. CI validates
  the metadata and starts both, the Flatpak inside its sandbox.
- A Windows installer: `packaging/build.py --installer` wraps the app in an Inno Setup
  installer that installs per user with no admin rights (per-machine optional), with a
  Start-menu shortcut, an uninstaller, and a stable AppId. CI installs it, starts the
  installed app, and uninstalls it on every Windows dry run. Signing through SignPath
  Foundation or Microsoft Artifact Signing is wired in on tags, switched off until the
  maintainer configures one. winget manifest templates are validated against winget's
  schema (`docs/dev/packaging.md`).
- A code signing policy page (`docs/user/code-signing.md`), written to SignPath
  Foundation's conditions: who builds and signs, the review before a release, how to check
  a download, and the privacy statement. ADR-0022's research claims now have sources,
  checked on 2026-10-25 (`docs/dev/research/distribution.md`), with an amendment for the
  facts that changed.
- Packaged builds carry the full license texts of the runtime they bundle, in the app
  folder's `licenses/`: Qt's LGPL-3.0 and GPL-3.0, CPython and the software it
  includes, OpenSSL, libffi, zlib, bzip2, xz, Nuitka, the Microsoft C++ runtime, and
  Qt's own third-party notices (KI-016). They're vendored from upstream at pinned tags
  with checksums (`packaging/fetch_notices.py`), and the build fails if one is missing.
  THIRD_PARTY_NOTICES.md gives Qt 6.12 and PySide6 6.12 their copyright, source, and how
  to replace or rebuild them, and Help > About names them and their license.
- For calculator authors (ADR-0024 E1, E2): a field's text is read in the unit or form
  its picker chooses, by `TypedValue.read(text, choice, dimension)`. It takes numbers,
  fractions, mixed numbers and exact arithmetic (+ − × ÷ and parentheses), with
  AutoCAD's mixed-number rule: `1-3/16` is 1 3/16, `1 - 3/16` is 13/16. Feet and inches
  read as `10-2 3/16` or `10'-2 3/16"`, a bare number as inches, and degrees, minutes
  and seconds as `40 30 15`. A text that names a unit is refused with its fix
  (`UnitInTextError`). A parameter declares its picker's choices (`Param.unit`,
  `Param.units`; its default's unit otherwise), and a calculator its output sets
  (`UnitSet`, `Calculator.output_sets`, generated one per length choice by default); an
  output may have its own picker (`Output.picks`). A parameter whose picker has no
  default unit is refused at registration, a plugin's included.
- **The Conversions family (ADR-0018 §3, as ADR-0024 §7 splits it),** after Geometry:
  Length, Fraction to decimal, Decimal to fraction, Angle, Area, and Stress and pressure.
  Each takes one value and gives it in another unit, picked beside the result, to 6
  significant figures; Decimal to fraction gives the nearest 1/16, 1/32 or 1/64 inch and
  its error. The factors are the exact definitions (1 in = 25.4 mm, 1 ft² = 92 903.04
  mm²), and each converter is verified against NIST SP 811's Appendix B.8. See the user
  guide's [Conversions](docs/user/calculators/conversions.md).
- `core.units.convert` converts an exact amount between units from their exact
  definitions: 1 psi is 6.894757293168361 kPa, rounded once. An output with a fixed unit
  may give its own precision (`Output.precision`), as the converters' error rows do.
- **The Geometry family (ADR-0018 §2),** listed first: Circle, Rectangle, Triangle (three
  sides), Right triangle, Regular polygon, and Arc and sector. Each gives every property
  of its shape at once, cites *Machinery's Handbook* (31st ed.), and points students to
  the *Pocket Companion* (32nd ed.). Input that describes no shape is refused, such as a
  flat triangle or a hypotenuse no longer than its leg. Triangle angles all come from
  Kahan's arrangement of the law of cosines, a deliberate departure from the Handbook's
  three-sides procedure, and
  the formulas are arranged to keep their digits for needle-thin triangles and small
  arcs. See the user guide's [Geometry calculators](docs/user/calculators/geometry.md).
- `Context.given` reports an input as an output, unchanged, for a method that takes as
  input what another method gives, such as a circle's diameter.
- **Feet and inches (ADR-0019 U3; KI-009 resolved).** Type a length as `1'-4 3/16"`,
  `1'-4-3/16"`, `1'4-3/16"`, `1' 4 3/16"`, `1′ 4 3/16″` or `1 ft 4 3/16 in`. A result in
  feet and inches shows `1'-4 3/16"`, copies `1'4-3/16"`, and is read aloud as "1 foot 4
  and 3 sixteenths inches"; rounding carries, so 1'-11 63/64" shows as 2'-0".
- **Degrees, minutes and seconds.** Type an angle as `40°30′15″`, `40°30'15"` or
  `40d30'15.5"`. A result in this form shows `40°30′15.00″` and copies `40d30'15.00"`;
  29.99999999° reads 30°0′0.00″, and zero never reads -0°. In an angle, `′` and `″` (and
  `'` and `"`) are minutes and seconds, so `30′` is half a degree; elsewhere they're still
  feet and inches. An output can be shown in either form (`Output.form`).
- **Areas (ADR-0018 §3, ADR-0019).** A new kind of quantity, the area, in in², ft², mm²,
  cm² and m², each the exact square of its length unit, so 1 ft² is 92 903.04 mm²
  exactly. Type `3 in²`, `3 in^2`, `3 in2`, `3 sq in` or `3 square inches`; it's always
  written `in²`. Areas show in the square of your length unit, to 6 significant figures
  (`6451.60 mm²`, `10.0000 in²`), and JSON gives them in mm², with `"dimension":
  "area"`. Messages that list the base units now end in "mm²".
- **Results in a fixed unit.** A calculator's output may be shown in one unit always,
  whatever the unit system, to 6 significant figures (`Output.unit`), as the coming unit
  converters' rows are. Copying, Copy all, the document and the command line all show it
  so.
- **Numbers in your regional format (ADR-0020 §4).** The desktop app shows numbers with
  your regional format's decimal mark, such as `0,3119`, and takes it when you type, with
  "." always accepted too. Digits are never grouped, and a comma that isn't your mark is
  refused with a message saying why. Copy and Ctrl+C still write ".", which CAD reads;
  Copy all writes your mark, for a spreadsheet, and in comma locales the copy menu adds
  "Copy 0,3119". The work's formulas and values are written in your mark too. JSON and
  the command line's numbers keep ".". This resolves KI-022.
- **The language follows your system (ADR-0020 §3).** The desktop app reads the display
  language and the regional format when it starts, for its own text and for Qt's, such
  as dialog buttons; a change applies at the next start. The command line takes
  `--lang`, then `CADDCALC_LANG`, `LANGUAGE`, `LC_ALL`, `LC_MESSAGES` or `LANG`.
- **Groundwork for translation (ADR-0020).** `caddcalc.core.i18n` translates text where
  it's shown, through GNU gettext catalogs; text stays in US English, the source
  language, until a language is chosen and wherever a catalog lacks a string. It also
  gives the plural category of a number as shown ("1 inch", but "1.0000 inches").
  `scripts/i18n.py` extracts, updates, compiles, and checks the catalogs, with Babel as a
  development dependency, and CONTRIBUTING's "Translating" gives the rule for new text.
  Nothing is translated yet.
- **A British English catalog (ADR-0020 §2),** read by every English locale outside the
  US, following CLDR's parent locales, and by en_CA. The calculators' and families' names
  and summaries, and the welcome card's text, are marked for translation. The app
  doesn't choose a language from the system yet.
- The calculator list's tooltip gives a calculator's or family's whole name, above its
  summary, when the list is too narrow to show it.
- Units can be typed in British spelling too: `3 millimetre`, `1 metre`, `2 centimetre`,
  and `44 per cent` read as their units, in any case (ADR-0019 U5).
- A test pseudo-locale, en_XA, and tests that every page fits at the window's least size
  in it and in English, and that the welcome card's version line stays in its safe area.
- `scripts/i18n.py init LANG` starts a language's catalog, and `check` reports a fuzzy
  translation.
- ADR-0018 (Geometry and Conversions), ADR-0019 (a units registry), and ADR-0020
  (localization), all accepted, are in `docs/dev/decisions/`.
- **Copying results (ADR-0017).** Each result field's copy button copies its value as
  shown, without its unit, ready for a spreadsheet cell or a CAD dimension box; so do
  Space, Enter, and Ctrl+C (Cmd+C) on the focused button. Its menu (right-click or the
  Menu key) also copies with the unit, or at full precision. **Copy all**, beside the Results title or Ctrl+Shift+C (Cmd+Shift+C),
  copies every output as rows for a spreadsheet, with any text cell that a spreadsheet
  would read as a formula kept as text. A check shows on the button for a moment, and
  the status bar and screen readers say what was copied.
- Tab goes through the inputs, then each result's copy button, then Copy all. Screen
  readers hear each result in full, e.g. "Bend allowance, BA: 0.3119 inches".
- The user guide's [Results and copying](docs/user/results.md): the result fields,
  copying, the keyboard, and how a short window scrolls.
- Groundwork for result fields (ADR-0017): their design tokens in
  `gui/assets/ui_style.toml`, documented in `docs/dev/design/result-fields.md`; a new
  palette colour, focus blue, for keyboard focus, kept well apart from every warning
  outline; the Tabler copy and check icons; and spoken unit names ("inches") for
  screen readers.
- `core.formatting` shows a value in parts, for copying it (the coming result fields):
  `value_parts()` gives its number and its unit, and `format_value()`
  now joins them, unchanged. `copy_text()` gives the clipboard text: the number as shown,
  the number with its unit, or full precision (10 significant digits), always plain
  decimals with an ASCII minus and no negative zero. `results_tsv()` gives a result's
  outputs as tab-separated rows for a spreadsheet.
- Branding packs may restyle their welcome screen within a whitelist (ADR-0016, S5):
  `[welcome.style.logo]` sets the logo box's fill role, margins, and padding, and
  `[welcome.style.panes]` the panes' fill role and least opacity. Anything else is
  refused, as are values that would leave the logo no room or the panes unreadable.
- The welcome screen's display face, VT323 by Peter Hull, drawn bold (ADR-0016, S1). It
  ships unmodified under the SIL Open Font License 1.1 with its `OFL.txt`, pinned to a
  google/fonts commit and hashed by `packaging/fetch_fonts.py`. It's credited in About
  and THIRD_PARTY_NOTICES.md. If it can't be loaded, the name uses a fallback face, with a
  warning. The build checks that the face and its license are bundled, and the smoke
  report gains `display_font`.
- Design tokens for the welcome screen (ADR-0016): every size, colour role, and font it
  uses is a token in `gui/assets/welcome_style.toml`, read, typed, and range-checked by
  `gui/welcome_style.py`, which refuses unknown keys and checks each role against the
  palette. The art specification documents every token, and tests keep it quoting them
  and keep layout and colour literals out of `welcome.py`. New palette roles
  `welcome_line`, `welcome_ink`, and `welcome_paper`. The generated art and generic logo
  move to `gui/welcome_art.py`. The name and version now sit in panes that hug their
  text at their corners, and the logo region is 96 px wide.
- Phase 2b close-out (ADR-0014, amendments): the materials release record,
  `docs/dev/research/release-checklist-materials-v1.md`, with all seven items and the
  stand-ins disclosed, awaiting its sign-offs; the research notes' resolved items and
  phase 2b findings (§10, §11); and ADR-0014's status, phase 2b built. A packaged build
  bundles and loads both tables.
- **Materials on the Sheet Metal page (ADR-0014, amendments).** A **Facts** row shows the
  chosen material's minimum-radius rule with its sources and their scope, its bending
  practice, and its strengths with their basis, in ksi or MPa as the unit system sets.
  Buttons under the K-factor field apply its cited starting values (FAA's 0.445 for the
  aluminums, the textbook's 0.4 for four materials), which keep their citation and a
  test-bend note until you type over them. On calculator pages, a limit-exceeded note
  shows in red with red outlines on its fields, and a field no source could check gets a
  dashed outline (new palette roles `outline_limit`, `text_limit`, `outline_no_value`).
  A temper its material always selects offers no "None".
- What a domain tells about its selections (ADR-0014, amendments): `Domain.details`, a
  `SelectionDetails`, gives `facts()` to show (`Fact`: a heading, text with quantities in
  base units, and references) and `starting_values()` to offer (`StartingValue`: a
  setting, its stated value, and the `ValueOrigin` to apply it with). Both are checked
  against the domain's settings and tables.
- Short titles for citations (ADR-0014, amendments): a `[[publication]]` may give a
  `short_title`, e.g. "AC 43.13-1B (2024 ed. update)", which every shipped publication now
  has. `Reference.short` names a citation by it and its locator, and source labels and
  note texts use it: "Sheet Metal settings, starting value from FAA-H-8083-31B, p. 4-63".
  References, JSON (which gains `short_title`), and a note's list of sources keep the full
  citation, now with its locator before its detail. A source's `remark`, for reviewers,
  is never rendered. Without a short title, labels show the full citation as before.
  The gauge table, released at version 1, is now **"Gauge systems", version 2**:
  citation metadata only, values unchanged.
- **The minimum-radius check (ADR-0014, amendments).** With a material chosen, *Bend
  allowance & deduction* and *Flat length of a formed segment* check the inside radius
  against its cited minimum (`sheet_metal.checks.BendCheck`, a result check): the larger
  source governs, a range at its upper bound, with every source and its scope shown, and
  TO 1-1A-9's bending practice beside a limit. A thickness no source lists, a bend past 90°, a
  hem, and a material with no source each get a no-applicable-value note. A gauge
  thickness from a system the material isn't ordered by gets a warning. The materials
  table gains its `[practice]` entry.
- Material and temper choices on the Sheet Metal page (ADR-0014, amendments): a grouped
  **Material** row (aluminum, carbon steel, stainless) and a **Temper** row that depends
  on it, with a material's only temper selected for it. Tempers are keyed by their
  material, e.g. `temper:6061_t6`, and the carbon steels come "as supplied". A material
  derives no value (M2). `sheet_metal.domain.SheetMetalResolver` combines the gauge and
  material resolvers.
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
  never sees; a check that changes the run or repeats a note is a `SpecError`.
  `DomainSettings.set(origin=…)` takes a `ValueOrigin`, the table entry of a cited value
  the user applied rather than typed, with any note it carries; it must be an entry of
  one of the domain's tables (`Domain.tables`). Results name its source, e.g. "Sheet
  Metal settings, starting value from FAA-H-8083-31B, …", and carry the note while it's
  in use, also through a calculator's copy of it. Typing over the value drops both.
- Bands, conditions, and per-parent defaults for phase 2b (ADR-0014, amendments):
  `core.Band`, a range with included or excluded ends that a reference value applies
  across, never interpolated; `ReferenceValue.band`, `conditions`, `quantity`, `series`,
  and `key`; `TableSpec.quantities`, the quantities a table declares; and
  `ReferenceTable.check_values()` refuses overlapping bands within a series (one
  quantity, from one source, under one set of conditions, at one basis), a second value
  in a series without a band, a quantity the table doesn't declare, and values of one
  quantity that name different condition keys. `Option.default` lets a
  resolver mark the option a choice falls back to, so each material can default to its
  own temper.
- A stress dimension for phase 2b's material strengths (ADR-0005 and ADR-0014,
  amendments): `Dimension.STRESS`, in MPa, with kPa, GPa, psi, and ksi. Stresses show
  in ksi when lengths are in inches or feet and in MPa when they're metric, to
  `DisplayPrefs.stress_decimals` (1) places. `formatting.entry_unit()` gives the unit a
  bare number is read in.
- Welcome-screen docs: the art specification (docs/dev/design/welcome-screen.md), the
  `[welcome]` pack keys in packaging.md, the welcome screen in the user guide, and
  KI-020, the checks CI can't run on real windowing systems.
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
- **A family settings page clipped its facts and help at one window width,** the one
  where its form is exactly as wide as it prefers: the cited minimum inside radius and
  strengths lost their last line, and a setting's "Used by" list showed one calculator
  of four. Qt laid the rows out with heights from another width (KI-032); the form now
  lays itself out again when a wrapped row is short.
- **A family settings row is never squeezed beside its label** (KI-031): within a few
  pixels of fitting, a row stayed beside its label and its field lost those pixels,
  cutting into a choice box at some window widths and, on Windows, into the unit
  pickers at the least size. Such a row now goes below its label.
- **A decimal half shows to even in every unit** (KI-028): 49.92751 mm is `1.9656 in`, a
  0.5 mm circle's radius `0.0002 m`, and 1/32 in `0.7938 mm`, where each showed its
  double's rounding. A value within two of its last places of a half is taken as the
  half, as the inch fractions take one; the course's 0.66875 in bend allowance now shows
  `0.6688 in`.
- **A field's echo no longer widens the window's least size;** it hides when it doesn't
  fit, as it always did. A plugin's declared output set is shown by its translated label,
  in the results and in `caddcalc show`. A unit run on to a number with an exponent, as
  `1e3)mm`, is named as `mm`.
- **A converter's result near 10³⁰⁸ in feet and inches, an inch fraction or degrees,
  minutes and seconds printed hundreds of digits;** past what a double holds of the form's
  finest step, it's shown in inches or degrees to 6 significant figures. A number too
  small to hold six figures, near 10⁻³²⁴, shows only the figures it holds, and a copy
  menu no longer offers two items that copy the same text (PR #1's final review).
- **Escape, or a click outside, on a picker's open list left it unable to settle:** a
  step taken before, and every step after, never carried to the other fields. Closing
  the list chooses nothing, and the step settles when you leave the picker.
- **The Inputs list printed false equalities in inch-fraction and feet-and-inches sets,**
  such as `0.1046 in = 1/8"`. An input has no second value where the set's unit is its
  field's, a form gives way to its unit where it would round the input (`= 0.1046 in`),
  and a calculator with no Show in picker, such as a converter, gives none.
- **A calculator's own output set in a finer feet-and-inches form** (`ft_in_32`,
  `ft_in_64`) passed registration, then failed in the app and on the command line; it
  shows now, with its other units taken from the inch set.
- `30'`, `30"` and `30 arcmin` in a bend angle offered "Use 30′?" with no button; a unit
  its picker doesn't list is refused with no offer. A picker switch also clears its
  field's undo, which would otherwise read an earlier text in the new unit.
- Feet alone, `1'` in a feet-and-inches field, read a last place apart from the command
  line's `L=1'`; both read 304.8 mm now. A refused unit run on to its number, `3μm`, is
  named as `μm`; a refused form quotes a minus sign as typed; and `40d30m` in a DMS field
  is refused as not degrees, minutes and seconds rather than as a length.
- **The command line:** an unknown `--output-unit` name is named in its message, and a
  result is named in any case as an input is; `--unit` with an empty unit, or for an
  input the method doesn't use, is refused as such; a repeated `--output-set` is refused
  as the other repeated options are.
- **JSON gives `output_set: null` for a calculator with no output sets,** such as a
  converter, and an input's `shown.value` is the number as typed (`T=3` is 3), and
  always agrees with its `base`: `value=3 - 1/2"` gives 3.5, as the command line reads it.
- **An input read in feet and inches is listed as it ran:** `0'-0.1046"` is listed
  `0.1046 in`, not rounded to `0'-0 1/8"`; one the form shows exactly stays in the form.
- A result's label no longer draws a pixel past its edge where it elides, as on macOS.
- **The command line read no input given after an option on Python 3.12,** as in
  `run CALC --method course T=0.25`; it reads them wherever they're given now.
- **A degrees-minutes-seconds field left at a sign ran at 0°:** `-`, `+` or an empty
  text now isn't finished, as in any other field, and so are `40-` and `40-30-`; a
  hyphen after a mark, `40°-30′`, is refused.
- **Opening a unit picker's list after an arrow-key step moved the other fields** to the
  step's unit before anything was chosen. Only the choice made in the list leads now.
- **A Geometry length outside 10⁻⁷⁰ mm to 10⁷⁰ mm is refused, plainly** (KI-026). A 3-4-5
  triangle of 3·10⁻⁸² mm had an area of 0, and one of 3·10⁻¹⁶² mm angles 9 % off; at
  3·10⁻¹⁶⁵ mm it divided by zero, a circle that small had an area of 0, and a triangle of
  3·10⁷⁷ mm said its area "does not give a finite number".
- **A value three units in its last place off a half-way inch fraction rounds as itself:**
  `-11.976562500000005 in` is 11 63/64" to the 1/64, not the even 11 31/32". The two units
  in the last place that make a typed half-way value a tie are counted in inches, the
  unit it's shown in, not in millimeters, where they were up to four of an inch's.
- **A fraction or mixed number typed with its unit reads exactly, rounded once:**
  `3 78/100 mm` is 3.78 mm, not 3.7800000000000002, and `-0` reads as 0. Feet and
  inches, and degrees, minutes and seconds, read exactly too, so a value read on the
  command line is bit for bit the one a field reads.
- `tand(-0.0)` and `sind(-0.0)`, and their zeros at multiples of 180°, are signed as IEEE
  754's `tanPi` and `sinPi` sign them: `tand(-0.0)` is -0.0, not 0.0.
- A label that ends in parentheses takes its symbol inside them: "Across flats
  (inscribed circle, AF) must be greater than 0", not "(inscribed circle) (AF)".
- "1 and a half inches" and "4 and 3 sixteenths inches" are plural pairs for translators,
  their form following the whole value, as 1.5 and 4.1875, as a unit's name does.
- **A right triangle's hypotenuse equal to its leg is refused in any units:** `a=39 in`
  with `c=990.6 mm` gave a leg of 0 and an angle of 90°.
- **A half-way value typed in meters or as a fraction of a foot takes the even
  fraction:** `0.12779375 m` is 5" and `317/384 ft` 9 7/8" to the 1/16, and
  `1°35′3.405″` is `3.40″`.
- An angle within about 6e-11° of 90° is refused saying it counts as 90°, a count too
  large for the computer to hold exactly (2⁵³ and up) is refused, and `tand(180)` is
  exactly 0.
- **A triangle's small or nearly straight angle keeps its digits:** every angle is
  Kahan's half-angle formula, so sides 10, 10 and 1e-7 give C = 5.73e-7°, not 0, and
  Copy full precision and JSON give the true angle (ADR-0018, amendments).
- **A stress too large for its kPa or psi row is refused,** never shown as `inf`; a
  number too large to calculate with, such as `1e308 ft`, is refused as too large, not
  as "not a finite number".
- **The polygon's number of sides is at most 1 000 000,** refused plainly past that,
  where 1e300 failed with internal text.
- **A whole circle's chord is exactly 0,** not 2.4e-15 in: `sind` is exactly 0 at a
  whole multiple of 180°, and `cosd` at an odd multiple of 90° (ADR-0004, amendments).
- **A right triangle's angle within about 6e-11° of 90° is refused in both angle
  methods,** as 90° is; the hypotenuse-and-angle method gave a leg b of 8.7e-13 mm for
  c = 1 mm.
- **The Length converter's error is exactly 0** for a value that is the fraction, typed
  in millimeters too, such as `411.1625 mm`; Copy full precision gave -2.2e-15.
- The Geometry calculators' *Machinery's Handbook* locators name "Polygons" (pp. 81–82)
  and "Solution of Oblique Triangles" (p. 101), and the arc points students to the
  *Pocket Companion*'s "Segments of Circles" too.
- **A flat triangle typed in decimals is refused** (ADR-0018, amendments): sides 0.1,
  0.2 and 0.3 in made a "triangle", since 0.1 + 0.2 is a hair over 0.3 in the computer's
  arithmetic. A triangle within 4 machine epsilons of its longest side of flat is flat.
- **The polygon's number of sides is a count** (KI-025 resolved): it shows as `6`, not
  `6.0000`, everywhere, JSON included, where it's an integer and its dimension `count`;
  and `600 %` or `6 in` is refused, where `600 %` read as 6 sides.
- **A value half-way between two fractions takes the even one** (ADR-0019, amendments):
  3/32 in showed as 1/16" and 7/32 in as 3/16", since a typed 3/32 lands a hair under
  the half; they now show 1/8" and 1/4", in feet and inches and the nearest fractions.
- **The command line refuses a name that could be a result,** such as the right
  triangle's `B=30`, which it read as the side `b`; the message names both.
- A result's value or unit column could be a pixel narrower than its widest label asked
  for in some fonts, cutting the label's last pixel; on Linux with DejaVu Sans, the
  Angle converter's degrees, minutes and seconds lost one. Each column now takes its
  labels' own least widths into account (ADR-0017, amendments).
- A method whose calculation failed unexpectedly, such as a plugin's bug, left the
  previous method's results on screen under the new method's name. Now its result fields
  go blank and the error shows in the work, the command line exits with the error, and
  an error nothing else catches is shown in a message box rather than lost. The same
  holds for a plugin family's own code, in its calculators and on its settings page,
  which shows the error in place of its settings. The work says "The calculation
  failed:" for these, and keeps "Check the inputs:" for an input you can fix.
- **The welcome screen was slow to appear on a machine with many fonts:** about 2.7 s
  from launch, most of it resolving the display face's fallback fonts, which are for a
  face that didn't load. They're now used only then, and the card appears in about
  1.3 s, looking the same; the calculators load after it's painted.
- The work in a calculator's notes was meant to be fixed-width, but on Windows it was
  set in Tahoma, and finding a face for it held the main window for over a second. It's
  now set in Consolas on Windows, and in the platform's fixed-width face elsewhere.
- **The welcome screen flickered at startup.** The main window showed on top of it, then
  the card came back on top. Now the card shows once, and the main window is prepared
  hidden and appears behind it once, 1.5 s after the card shows, without taking its
  focus; closing the card gives the window the focus (ADR-0015, amendments).
- A result field's value or unit could lose its last pixel: their columns were sized to
  the nearest pixel of the text's width, and are now rounded up.
- Changing the units, or another calculator, while an outlined input had keyboard focus
  could leave the results unchanged after later edits. The focus ring around an outlined
  input now lets go of an input that's gone, and can never stop a calculation; it's also
  deleted with its window.
- An input outlined by a note showed no keyboard focus, since its outline replaced the
  native frame. It now gets the result fields' blue focus ring outside its outline
  (WCAG 2.4.7).
- At 150% scaling, a result field's focus ring had a 1 px gap on two sides and 2 px on
  the others, and lost a row at its top and left; it's now even and whole.
- A no-value result field's dashed outline read 10 px on and 2 off; it now reads 8 and 4.
- The window could shrink to a sliver; it now keeps at least a page's title, its method
  row, and one result field.
- **The bend check on a part with bends on both sides of 90°.** A bend past 90° made the
  whole part "no applicable value", so a bend up to 90° went unchecked: 6061-T6 at
  0.063 in with R = 0.15 in and bends of 90° and 120° showed no limit, though the 90° bend
  needs 0.16 in. Bends up to 90° are now checked, and those past 90° get their own note.
  The rule of thumb speaks only when no bend was checked against a source.
- **The welcome screen's panes could misjudge fine, regular art.** They sampled the
  art on a fixed grid, which aliases with periodic detail: over 1 px stripes it could
  see a fifth of their true share, so a fill could stop short. Each pane now measures
  every pixel under it, at the display's resolution, so detail finer than a logical
  pixel counts as the screen shows it. The `panes.min_samples` token is gone.
- **The welcome screen measured transparent art wrongly.** The image it measured the art
  in started uninitialized, so where a pack's PNG art was transparent the panes read
  arbitrary memory, and could pick a fill that left the text at about 1.55:1. The art is
  now measured over the card's own background, the same colour the card paints, and is
  measured again when the theme changes.
- **The mean-diameter cone with a bottom diameter no larger than the thickness.** It gave
  a negative sweep angle, or failed with a division by zero when they were equal. It now
  refuses the input, as it already did for the top diameter.
- **The course cone method with a bottom diameter no larger than the thickness.** It gave a
  sweep angle of 0° or less (−35.30° for Db = 2 mm, Dt = 0, H = 5 mm, T = 3 mm). With the maintainer's
  approval it now refuses the input as the mean-diameter method does; its formula and
  the course example are unchanged (KI-021, ADR-0010 amendments).
- **A window given an empty registry.** `MainWindow(registry=...)` replaced a registry with
  domains but no calculators by the built-in one, because an empty registry is falsy. It
  now keeps the registry it's given.
- The app, and the test suite, could crash on exit after the window closed (KI-019): the
  window's own widgets held it through their signal connections, so it was torn down
  during interpreter exit. Every CI job failed from it. The `caddcalc-gui` command also
  ignored its command-line arguments, `--smoke-test` included.
- KI-017: switching the GUI between in and mm no longer rounds the values in calculator
  fields. Typed text is kept and shown verbatim while its unit is the display unit, and
  other values are re-expressed from their base value; nothing is read back from the
  display.
- The K-factor's help said it "approaches 0.5 for large R/T", with no source. It now says
  what its source does: the neutral axis is often assumed to be at mid-thickness, 0.5
  (FAA-H-8083-31B, p. 4-59).

### Changed
- Packaged builds leave out QtNetwork, Qt's TLS backends, and the PDF, TIFF, WebP, TGA,
  WBMP, and ICNS image plugins, which the app never uses (`docs/dev/packaging.md`).
- Packaged builds on Linux and macOS put Qt's own catalogs where their Qt looks, so Qt's
  text (standard buttons, a field's context menu) follows the app's language there too.
- **The converters are one value in and one out** (ADR-0024 §7, E-6, U3): Length,
  **Fraction to decimal** and **Decimal to fraction**, new, Angle, Area, and Stress and
  pressure. Each takes a value in its input's picked unit and gives it in its result's
  own picker's unit, which is the other system's counterpart (in → mm, mm → in, ksi →
  MPa) until you pick it. Decimal to fraction takes its fineness, 1/16, 1/32 or 1/64, as
  a choice, and gives the nearest fraction and its error. The CLI and JSON give each
  converter's result as `value`, and `caddcalc show` lists a fineness's values and what
  a result follows. KI-029 is resolved. Its error is always a decimal, to 6 decimals in
  any unit, so its **Show in** offers decimal units only: in a fraction it read `0"` for an
  error of 1/32 inch. In every calculator, an input typed as a plain decimal is listed as
  typed, `0.09375 in`, not `0.0938 in`: in the Inputs list, the CLI's report and JSON's
  `shown.text`. For calculator authors: `Output.follows` and
  `Output.counterparts`, `Param.allowed`, `Output.precision` in any unit an output is
  shown in, and `Calculator.forms_in_sets`; a signed output in a form, fixed, picked or in
  a set, is refused at registration. The converters' help says to pick the unit, then type the
  number, and gives examples with no unit. On the command line, a fineness reads by its
  label, `F=1/16`, and `--unit` takes any of a unit's spellings, `--unit X=in2` or
  `"X=sq in"` for `in²`.
- **Each family setting with a unit has a picker** (ADR-0024 E-5, U2b), as a
  calculator's inputs do, and its number is read in the unit the picker shows; a unit
  typed in the field, as `3 mm`, is refused, and offered as a pick, "Use 3 mm?", as a
  calculator field offers it. Switching it re-reads the number you typed, and says so,
  "3 now read as millimeters", as a calculator field does; a calculator shows an
  inherited setting in its own field's unit. A material's facts are in the unit their source gives (Q13). KI-027 is
  resolved. For calculator and plugin authors: `DomainSettings.set_text` reads in the
  setting's picked choice (`field_choice`, `set_field_choice`) and no longer takes a
  default unit; a domain's setting must name its unit (`Param.unit`), checked at
  registration as a calculator's parameter is; `Fact.quantities` are the values as their
  source states them (`TypedValue`); and `core.formatting.entry_text` is removed, for
  `picked_text`.
- **The command line's units (ADR-0024 E-4):** a bare number reads in the input's default
  unit, which `caddcalc show` now lists with each input's units and the calculator's
  output sets: inches and degrees for every sheet-metal and geometry input. `--unit
  NAME=ID` reads an input as a field picked in that unit or form does (`--unit L=ft_in
  L=10-2`), refusing a unit in its text and a comma. `--output-set SET` (the first by
  default) and `--output-unit KEY=ID` choose the results' units, and each input is
  shown in the unit it was given in. **`--units` and `--fraction` are removed**, and
  with them the `(≈ 5/16")` hint, in the app too: `--output-set in_16` and the app's
  `in 1/16` replace them. A `--unit` without its input, twice for one input, or with a
  unit it doesn't offer is refused, as is an `--output-unit` for a result with no
  picker of its own.
- **JSON is schema 1:** every input, result and step gives its value in base units and
  as shown, a form adds its `copied` text, a given input adds `entered`, and the top
  level has `schema` and `output_set`. For calculator authors, `Result.to_dict` and
  `Note.to_dict` are replaced by `core.formatting.result_json`, and
  `DisplayPrefs.fraction_denominator`, `CopyForm.FRACTION`, `to_fraction` and
  `Unit.fractions` are removed.
- **The Units box is gone; the results have a Show in picker** (ADR-0024 U2), between
  their title and Copy all. It offers a set per length unit, `in`, `in 1/16`, `in 1/32`,
  `in 1/64`, `ft-in`, `ft`, `mm`, `cm` and `m`, labelled by what the calculator shows
  (`in · ° · in²` on the right triangle), and sets the fields, Copy, Copy all, speech
  and the work together. Until you choose one, it follows the method's length inputs
  while they share a unit, and stays on the set it last followed while they don't; once
  chosen, it's yours for the session. Its accessible name is "Results units", its list names each set ("in 1/16 —
  inches, nearest 1/16"), the mouse wheel doesn't change it, and it adds no height. The Inputs list adds each input's
  value in the set's units where its picker shows another: `0.1046 in = 2.6568 mm`. A
  result with its own picker (`Output.picks`) has it in its row.
- **The Inputs list and an input's range error are in the unit its picker shows**
  (ADR-0024 E4), not the Units box's: a bend angle picked in rad is listed as
  `1.5708 rad`, and refused as "must be less than 3.14159 rad". A value in radians shows
  4 decimals, where other angles show 2. Everything else shows as before, character for
  character, in inches and in millimetres. For calculator authors: `core.formatting`
  takes the units to show in as a `ShownUnits` (an output set, with each output's pick
  and each input's choice), and `DisplayPrefs.length_unit`, `display_unit` and
  `entry_unit` are removed; an output with its own picker shows in its first pick until
  it's picked.
- **Each calculator input with a unit has a unit picker after it** (ADR-0024 U1), and
  the number is read in the unit it shows. Fields take fractions, mixed numbers and
  exact arithmetic (`2 × 1 3/16`), with AutoCAD's rule that `1-3/16` is one and three
  sixteenths while `1 - 3/16` is thirteen sixteenths; feet and inches with their marks
  optional (`10-2 3/16`, a bare `10` being inches); and degrees, minutes and seconds as
  `40 30 15`. What the text reads as shows at the field's end, `= 1 3/16 in`, and is
  the field's accessible description. **A unit typed into a calculator field is
  refused**, with a button that moves it into the picker: `25 mm` offers "Use 25 mm".
  Switching a picker re-reads the number you typed and converts a value you didn't;
  your first switch carries to the calculator's other fields of that kind that show a
  value you didn't type, once the choice settles (Enter, leaving the picker, or a choice
  in its list). A bend angle is picked in °, ° ′ ″ or rad. Degrees, minutes and seconds
  take hyphens between their parts (`40-30-15`), and the minus sign `−` never joins a
  mixed number. For calculator authors, a default with no unit in its text is in the
  unit its picker starts in.
- **The command line suggests only names that can be given:** for the right
  triangle's `B=30` it says B is a result and asks "Did you mean b/leg_b?". With
  `--method leg_angle`, which takes no side b, it suggests none and names that method's
  inputs, a/leg_a and A/angle_a.
- A result's help reaches the keyboard: screen readers say it after the copy button's
  value. An error's work line shows its sign, `+0.0025 in`, as its row does.
- **Speech, in words a drafter says:** "1 foot and a quarter inch", "a half inch", "1
  foot and 3 sixteenths of an inch". Spoken parts are joined by CLDR's list patterns, so
  a translation can put its "and" before the last part only.
- **A comma in feet and inches or DMS says why it's refused,** quoting the whole value:
  `"90°30,5'" has a comma, which isn't a decimal mark here …`. `3 ft.` is "not a number"
  again, not "isn't feet and inches".
- "Copy full precision" on a feet-and-inches or DMS row says the unit it copies in:
  "Copy full precision, in inches".
- A label that names its symbol isn't followed by it again: "Side a", "Angle A (opposite
  a) must be less than 90°", not "Side a (a)".
- The command line's label column is as wide as its longest label.
- A value shown to significant figures takes an exponent outside 10⁻⁶ to 10¹⁶:
  `1.00000e+300`, not 301 digits.
- The odd polygon's note says how the caliper is held: from a flat to the opposite
  corner. The converters' note says how a row is converted: from the typed value,
  through each unit's factor.
- **The command line refuses an input it would lose:** one given twice, or one the
  chosen method doesn't use, such as `A=30` for the right triangle's two-legs method, is
  refused, exit 2, naming the method's inputs. They were silently overwritten or dropped.
  A sheet-metal command line that gave such an input is refused too: `K=0.44` for the
  bend allowance's default course method, which takes no K, needs `--method` naming a
  method that uses it. Every other sheet-metal command line runs as before.
- **Plugin families are listed after the built-ins, sorted by name,** whatever order the
  installed packages are found in.
- `get_unit` with a dimension that has neither unit raises `UsageError` for a mark the
  foot and the minute of arc share: `get_unit("'", Dimension.RATIO)` gave the foot before
  the minute and second of arc were added. With no dimension, `'` and `"` are still the
  foot and inch.
- For calculator authors: an output is given its value once (`Context.given`, `calc`
  and `record` raise `SpecError` for a second), and an output in a compound form can't
  give its own `precision`.
- **The Length converter's errors show their sign,** `+0.002500 in`, and the error
  row's tooltip says it's the fraction less the value (`Output.signed`; a field's
  label shows its output's help as a tooltip).
- **Screen readers hear every negative as "minus …"** and a shown plus sign as "plus
  …", and one part of an inch as "1 and a quarter inches" or "1 and a half inches".
- "Copy with unit" isn't offered for feet and inches or degrees, minutes and seconds,
  whose copy names its units already.
- **The disclaimer is one line for every family,** in the maintainer's words, marked for
  translation: "Verify results and test according to your organization's policies or
  industry best practice before manufacturing." It's shown under the results, after the
  command line's results, in About, and in the README (ADR-0020, amendments).
- **The window opens at one height whatever calculator it shows,** 738 px with
  Windows' 9 pt text and in proportion at other text sizes. A page taller than the
  window, such as the Length converter or the right triangle, scrolls as a whole; the
  window doesn't grow to fit it (ADR-0021, amendments).
- **Families are listed in their declared order,** general tools first: Geometry, then
  Conversions, then Sheet Metal, with a plugin's families after the built-ins, sorted by
  name. They were all sorted by name.
- **The command line reads an input's exact key or symbol first,** then in any case, so
  `a=3` is a side and `A=30` an angle in the same calculator. A name that matches two
  inputs only in different cases is refused, naming both.
- **The course formula is named for what it does: "Fixed K-factor (≈ 0.41)"**, the
  neutral-axis arc with K fixed at about 0.408 and π/2 rounded to 1.57 (ADR-0010,
  amendments). Its key is still `course`, so saved command lines and JSON keep working,
  and it still reproduces the course's answers exactly.
- **Two bend methods are verified against published worked examples** (ADR-0010,
  amendments). The fixed K-factor is verified for the bend allowance in Bend allowance &
  deduction, against *Machinery's Handbook* (31st ed.) Fig. 13, p. 1421, and reads
  "verified for BA · reproduces legacy". The K-factor is verified at 90°, in Bend
  allowance & deduction ("verified for BA at 90°") and in Flat length of a formed segment
  ("verified at 90°"), against *Engineering Drawing and Design* (5th ed.) Fig. 19.12,
  p. 785. The other methods stay unverified, the fixed K-factor's flat length of a
  segment among them.
- A method's status says what its verification covers, and its tooltip names the source,
  or says why the method isn't verified there. The status keeps one width, so changing
  the method no longer shifts the row.
- Citations of *Machinery's Handbook* move from the 29th edition to the 31st (2020): the
  course formula (p. 1421), the angle rule and its worked example (p. 1421, Fig. 13), and
  the 41.82 steel basis (Table 2, p. 2706), so the gauge table is version 3. The
  formulas and values are the same.
- **The window and page layout (ADR-0021).** The window opens centred on the welcome
  card's screen, sized to fit it, and in Windows follows the user's text size, read at
  startup: every size is in text units, so larger text makes the whole layout larger in
  proportion. The page is capped at a comfortable width, left-aligned beside the list,
  with plain background beyond it; the list can't be dragged shut.
- The disclaimer moves from the status bar to the last line under the results, wrapped,
  never cut off; the status bar keeps passing messages such as "Copied". The method box
  shows the method's name, with its status beside it, or under it when narrow; the open
  list shows both. The family settings page reflows to a narrow window instead of
  scrolling sideways.
- A typed number may use the minus sign `−`, and may no longer use `_` between digits,
  which was read as grouping: `1_000` was 1000.
- An elided calculator name shows in bold in its tooltip, above its summary.
- Units' names, which screen readers say, are US English, the source language
  ("millimeters"), and come in British spelling from the British catalog ("millimetres",
  "per cent"). Each is singular only after a number shown as a whole 1. So screen readers
  say "millimeters" in US English, and "millimetres" in English elsewhere.
- **One language for the whole window.** Qt's own words, such as a field's Undo and
  Copy, and its shortcut names, are in the language the app's words are in: the first of
  your display languages the app has words for, or US English. A window never mixes
  English words with another language's menus.
- Where the decimal mark isn't ".", the copy menu names each item by what it copies:
  "Copy 0.3119", "Copy 0,3119", "Copy 0.3119 in".
- A method's notes give their own numbers in your units and decimal mark, as the cone's
  course example does ("132,70°"); numbers quoted from a source stay as published.
- "per cent" reads however its two words are spaced, a no-break space included.
- Language tags keep a script that isn't the language's usual one, so Traditional
  Chinese or Latin Serbian would never fall back to Simplified Chinese or Cyrillic; `C`
  and `POSIX` mean the source language.
- `scripts/i18n.py check` refuses a marked text with a positional `{}`, a numbered
  `{0}`, unbalanced braces, or a printf placeholder of any kind, reads the fields nested
  in a format spec, such as `{width}` in `{value:{width}}`, and checks each plural form
  on its own.
- CI marks each failing test as an annotation on the line that failed, which anyone can
  read through GitHub's API without signing in.
- **The catalogs ship in every build.** The packaged app and the wheel carry the compiled
  catalogs, so an installed app has British spelling too. The packaged app also carries
  Qt's own `qtbase` catalogs, for Qt's words in each language the app gains, and
  `THIRD_PARTY_NOTICES.md` names them. The build checks that each is there, and its
  smoke test that the app finds them (ADR-0009's checklist); with no catalog to compile,
  the build and the wheel fail. The catalogs' sources stay in the sdist, and CI checks
  that the wheel has none.
- **Units come from one registry (ADR-0019).** `caddcalc.core.units` is now a package that
  declares every dimension and unit once, with its exact definition and its NIST SP 811
  citation, and reads typed units by asking that registry, rather than a list of
  characters. Every text that read before reads the same, and every error says the same.
  One factor changes: psi is now its exact definition rounded once, one unit in the last
  place from before; no shown value changes. Plugins can add units through the
  `caddcalc.units` entry-point group. A plugin unit can't take any built-in unit's name,
  in any dimension; one that tries is skipped, with an error naming both.
- `core.citations` holds the citation model, `Publication`, `Source`, `License`, and
  `PublicationKind`, which the units and the reference tables share; `TablePublication`
  and `TableSource` are still there, as its `Publication` and `Source`.
- **Result fields (ADR-0017).** A calculator's results now show as boxed fields, one per
  output, in a Results panel between the inputs and the notes: the symbol, the label, the
  value aligned on its decimal point, and the unit, with a copy button. A note about an
  output outlines its field as it would an input. While the inputs have no result, every
  field shows "—". Every field always shows in full: the notes, inputs, and work below
  take the height that's left, never less than 96 px, with their own scroll bar. In a
  window too short for all of it, the whole calculator page scrolls, results included,
  never the results alone, and the notes, inputs, and work show in full, so there's only
  one scroll bar. Notes are listed strongest first: a cited limit, then a warning or an
  impossibility, then a check that couldn't be made. An angle's degree sign sits against
  its number.
- An input field a note concerns is outlined 2 px, not 1 px, so the outline reads without
  its colour; result fields will share it (ADR-0017).
- In the dark theme, the notes, inputs, and work below the results have the result
  fields' background, rather than a lighter grey, and the "Results" title is the size of
  their headings.
- **Notes lead with the verdict (ADR-0017 F1).** A bend check's note now opens with the
  decision and its numbers, in your display units, e.g. "Limit exceeded: inside radius
  0.0500 in is below 0.1600 in, the recommended minimum this check uses, for 6061-T6
  aluminum at 0.0630 in, in aerospace bending practice." What each source gives follows,
  each value still as its source states it, and then the sources, in smaller text. The
  CLI prints the same three lines. Notes have no list bullets, only their icons, and the
  document's Inputs sit on the result fields' grid, with each value's source after it.
- In JSON, each note's `text` is now its lead alone, with its values in base units; its
  `detail` and `quantities` (each named value, in base units with its unit) are new. A
  script that wants the whole note joins `text` and `detail`, and reads numbers from
  `quantities`.
- Sources, in the Inputs list and on a note's last line, are now in lighter text at the
  body's size, rather than smaller. A note's values show without the nearest fraction,
  which the result fields show. The "Copied" status message stays for 4 seconds, long
  enough to read. A copy button's own focus box is gone; the blue ring around its field
  shows focus. Tab now goes on from Copy all to the notes, inputs, and work.
- In a wide window, the results stop growing at about their width in the default window,
  and stay centred.
- **Welcome screen refinements (ADR-0016, amendments).**
  * The name is VT323 at 50 px, snapped to the face's pixel grid at every display
    scale, drawn regular, and centred on its capitals. `typography.display_weight`
    may be set to `bold`, Qt's bold, which differs by platform.
  * Lines are whole device pixels on the pixel grid, so they stay crisp at 125% and
    150%. The card is clipped to one rounded outline, its border stroked along it.
  * Each pane text has its own fill, white under ink and ink under white. The name
    needs 3:1 contrast (large text) and the version 4.5:1.
  * The logo box keeps a least short side of 48 px instead of a least size, and a
    greatest long side of 320 px; its fill is white in both themes. Without a pack
    logo it holds the app icon alone, in an 80 px square.
  * Both panes' text is drawn as its outline, grey antialiased, so the name and the
    version match on every platform. The title's grid size rounds ties down.
  * The panes' contrast is exact: each pane measures every pixel of the art beneath,
    at the display's resolution, blends each under its fill, and holds 95% of them to
    the pane's contrast, which the loader keeps at or above WCAG 2's floor. Saturated art, such
    as pure blue, is now held to the contrast too. The background under a pane must
    also be calm (`panes.max_background_spread`, 1.5), so over busy art, such as a
    checker, the fill rises until the letters don't break up; calm art stays at 15%.
  * The corner radius is 5 px, and the card's border takes a new role, `card_border`,
    white in the dark theme.
  * Insets, margins, and paddings follow a spacing scale, and the loader refuses
    values off it. A pack's pane override is now `panes.fill_roles`.
- **The welcome screen's restyle (ADR-0016).**
  * The art spans the card, now 960 × 572.
  * The logo sits in a bordered box floating over the art's left edge. The box takes
    the logo's shape, with minimum margins and a minimum size. The art spec and
    template gain a left safe area for it.
  * The card has a 1 px border, a 1 px line under the top bar, and rounded outer
    corners where the windowing system composites. It is square elsewhere (KI-020).
  * The name and version panes share one quiet style: a fill at 15% opacity, raised
    only as far as their text needs to reach 4.5:1 contrast over the art beneath, with
    a thin border in the text's colour. The version sits close to the bottom-right
    corner.
- **One product name (ADR-0016, S4).** Every edition is called "CADD Calculator" in its
  window title, on its welcome screen, and in About, and is told apart by its icon,
  art, logo, and About text. A branding pack's `name` key is removed: a pack that still
  names it is refused, with a message saying to delete it, and the app falls back to the
  generic branding with a warning.
- The minimum-radius check states its scope: "The inside radius is below the recommended
  minimum for 6061-T6 aluminum in aerospace bending practice (AC 43.13-1B (2024 ed.
  update), Table 4-6, p. 4-17; …)". Where only one source lists the thickness, the note
  saying so is a warning, since the check still applies. The gauge-and-material warning
  goes by the thickness's source, so a typed thickness equal to the gauge's isn't
  warned about; a check sees each input's source (`Context.sources`). An applied K
  starting value given for other materials than the chosen one gets a warning. The
  bending-practice note cites TO 1-1A-9's current edition, p. 2-80.
- A note's sources read by their short citation and scope, e.g. "(AC 43.13-1B (2024 ed.
  update), Table 4-6, p. 4-17: …)"; the full citations stay in JSON. A calculator's copy
  of an applied K starting value keeps its citation, so it is checked against the chosen
  material like the family value.
- A calculator's copy of a gauge's thickness keeps the gauge warning when the material
  isn't ordered by that gauge system. The limit note names each source once in its text.
  Choice boxes are sized to 24 characters, so a long option, such as a gauge system's
  name, no longer widens the settings page; the open list still shows it whole.
- The family settings page scrolls when its contents outgrow the window.
- The "inside radius is smaller than the material thickness" warning is now part of the
  bend check: it is dropped wherever a cited minimum applies, and otherwise reads as
  before, after the calculator's other notes rather than before them.
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
