# Scope and roadmap

## Vision

A trustworthy, open-source calculator suite for drafters, designers, students, and
instructors. Every number shows its work, names its method and source, and says how far it
has been checked. The suite starts with sheet metal and grows by domain.

## Non-goals (for 1.0)

* A CAD program or a geometry or drawing engine. We compute numbers, not models.
  DXF export of flat patterns is a possible later extra.
* Replacing a shop's own bend tables. We make it easy to *enter* them.
* Cloud features, accounts, or telemetry.

## Milestones

### 0.1: Skeleton (this commit)
- [x] Layered package: core, calculators, CLI, GUI (ADR-0003)
- [x] Declarative calculators, the expression evaluator, show-work, verification status (ADR-0004)
- [x] Units and drafting-fraction parsing (ADR-0005)
- [x] Sheet metal: bend allowance/deduction, segment flat length, V-die opening, cone layout
- [x] Golden tests reproducing the legacy spreadsheets
- [x] CI on Windows, macOS, and Linux (lint, types, tests)
- [x] Developer and user documentation structure

### 0.2: Trustworthy sheet metal
- [ ] Verify formulas against cited sources and promote methods to `verified` (KI-001, KI-004)
- [ ] Promote methods that now pass published worked examples to `verified`, after the
      maintainer agrees (course BA: MH29 Fig. 12; K-factor: EDD5 Fig. 19.12, at 90° only, see
      KI-013). `COURSE_METHOD` and `K_FACTOR_METHOD` are shared by two calculators, so give
      each calculator its own copy (`dataclasses.replace`) before promoting one.
- [ ] MH29 Eq. (32)/(33)/(34) as a material-class method (soft copper/brass; soft steel and aluminum; cold-rolled steel and hard copper)
- [ ] Dimension-origin input for bends past 90° (KI-013), with an ADR on the default
- [ ] Hems: 180° bends (KI-014)
- [ ] MH29 V-die bend deduction, 1.67·B·G (Table 13 method, pp. 1351–1352)
- [ ] K-factor from a test bend (the inverse calculation)
- [ ] Whole-part flat pattern: a chain of flanges (Σ outside dimensions − Σ BD)
- [ ] Dimensioning reference: outside, inside, or centerline (KI-006)
- [ ] Gauge systems computed from their definitions, with sources (ADR-0014 phase 2a):
      Manufacturers' Standard, galvanized, US Standard 1893, and AWG.
      **Each gauge must name its gauge system.** MH29 Table 13 lists 12 ga as 0.1093, not 0.1046.
- [ ] Material library with cited data (ADR-0014 phase 2b). User or shop-editable tables
      need a separate decision, outside the session-only model.
- [ ] Minimum inside bend radius checks per material and temper, as result notes that say
      so when no source covers the case (ADR-0014 phase 2b)
- [ ] Feet-and-inches input (KI-009). Fraction display toggle in the GUI.
- [ ] 1:1 printable SVG templates for cone layouts (annular sector) and flat blanks, to
      cut a paper template and check a first part (see KI-001). Use the conventions of the
      maintainer's parametric_CADD SVG writer: the user unit is the paper millimetre
      (`width`/`height` in mm with a matching `viewBox`), Y is flipped because model Y
      points up and SVG Y points down, and numbers have fixed precision. Any code reused
      from that GPL project is contributed by its author under Apache-2.0; say so in the
      commit. Include a printed scale check (e.g. a 100 mm / 4 in bar) on every sheet.

### 0.3: Installable
- [x] Packaging spike, then accept ADR-0009: pyside6-deploy + Nuitka (pinned to 4.1.1),
      standalone folder, built by `packaging/build.py`. Windows only so far (ADR-0009).
- [ ] Installers for Windows, macOS, and Linux, built in CI on tags. GitHub Releases.
      A workflow that builds generic archives on tags and drafts a release is sketched in
      `.github/workflows/release.yml`. It hasn't run on GitHub, and macOS and Linux are untested.
- [ ] Third-party license notices in the app folder (KI-016)
- [ ] Light and dark Qt themes built from the UI palette (`gui/assets/palette.toml`,
      [design/palette.md](design/palette.md)), replacing the ad-hoc HTML colors in `gui/window.py`
- [ ] Generic art for the public build: logo/app icon (Windows `.ico`, macOS `.icns`,
      Linux PNG sizes) and splash. Use original work, released permissively (see
      ADR-0008, item 4), with the source files (SVG or `.blend`) committed so others can
      edit them. Build it only from assets whose licenses allow that: your own models,
      CC0 assets, or OFL fonts. Not purchased stock assets whose licenses forbid relicensing.
      Until then, an interim icon drawn in code (`packaging/icons.py`) is in
      `src/caddcalc/gui/assets/`.
- [x] Branding hook: load name, icon, splash, and About text from an optional branding pack
      at build or run time, with a `--branding <pack>` build option (ADR-0008 item 4,
      ADR-0011, `docs/dev/packaging.md`)
- [x] Choose the license: Apache-2.0 (ADR-0008)
- [ ] Docs site generator (ADR-0007) published to GitHub Pages

### 0.4+: New domains (each gets its own ADR if it needs new dimensions or dependencies)
- **Drafting geometry:** bolt-circle coordinates, chord/arc/segment, right-triangle and
  oblique-triangle solvers, decimal to fraction conversion
- **Tolerancing:** worst-case and RSS stack-ups, ISO 286 limits and fits, GD&T
  position-tolerance conversions (cite ASME Y14.5 by section; no copied tables)
- **Fasteners:** tap drill and clearance hole sizes, thread pitch/major/minor diameters
- **Structural drafting:** beam and section properties, weld size helpers. Steel shape
  databases need a redistributable source.
- **Piping and ducting:** rolling offsets, miter cuts, transitions (more developments)
- **Press brake:** tonnage, minimum flange length

### Later ideas
- Saved sessions and printable or PDF "calculation sheets" for the shop or a grader
- DXF flat-pattern export
- Plugin folder for the packaged app (ADR-0006)
- Translations (strings are already centralized in calculator metadata)
- Web version (the pure-Python core via Pyodide)

## Open decisions (need the maintainer)

| Decision | Where | Recommendation |
|---|---|---|
| Code license | ADR-0008 | **Decided: Apache-2.0** |
| Code signing budget | ADR-0009 | Start unsigned. Apply to SignPath's free OSS program. |
| Default unit system (in vs mm) | ADR-0005 | `in` (the course and US shops). Remember the user's choice. |
| Default method when legacy and general both exist | ADR-0010 | Legacy first until a general method is `verified` |
| Python package and app name | pyproject.toml | Keep `cadd-calculator` / `caddcalc`. Renaming is cheap now and expensive later. |
