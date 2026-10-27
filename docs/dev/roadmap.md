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
- [x] Promote methods that now pass published worked examples to `verified`, with the
      maintainer's agreement (ADR-0010, amendments): the fixed K-factor (the course
      formula) in `bend_allowance` (MH31 Fig. 13), and the K-factor at 90° in `bend_allowance` and
      `segment_flat_length` (EDD5 Fig. 19.12). Each calculator has its own copy of the
      shared methods, verified only where the example runs through it.
- [ ] MH31 Eq. (32)/(33)/(34), p. 1421, as a material-class method (soft copper/brass; soft steel and aluminum; cold-rolled steel and hard copper)
- [ ] Dimension-origin input for bends past 90° (KI-013), with an ADR on the default
- [ ] Hems: 180° bends (KI-014)
- [ ] MH31 V-die bend deduction, 1.67·B·G (Table 13 method, p. 1422)
- [ ] K-factor from a test bend (the inverse calculation)
- [ ] Whole-part flat pattern: a chain of flanges (Σ outside dimensions − Σ BD)
- [ ] Dimensioning reference: outside, inside, or centerline (KI-006)
- [x] Gauge systems computed from their definitions, with sources (ADR-0014 phase 2a,
      built 2026-10-17): Manufacturers' Standard, galvanized, US Standard 1893, and AWG,
      chosen on the Sheet Metal page. Each gauge names its gauge system.
- [x] Material library with cited data (ADR-0014 phase 2b, built 2026-10-17): 5052-H32,
      6061-T6, mild cold-rolled, galvanized, HR P&O, and 304 annealed (2B), with their
      tempers, cited minimum radii, MIL-HDBK-5J strengths with their basis, and K-factor
      starting values applied on request. Its release record awaits sign-off.
- [x] Minimum inside bend radius checks per material and temper, as result notes that say
      so when no source covers the case (ADR-0014 phase 2b)
- [ ] **Next for materials:**
      - sign off the materials release record, and re-verify the gauge table's version 3
      - candidates from MH31's bending section, cite-only: minimum bend radius from the
        tensile reduction, Eq. (30), and maximum bend radius, Eq. (31), p. 1417;
        springback, Eq. (35), p. 1421; bending force, Eq. (36), p. 1422; and three-roll
        bending, p. 1423
      - more tempers and alloys, such as 6061-O and 5052-H34, as public-domain sources allow
      - a public-domain minimum radius for galvanized and HR P&O, which have none
      - press-brake tonnage, once an upper strength value passes ADR-0014 §5
      - user or shop-editable tables, which need their own decision, outside the
        session-only model
- [x] Feet-and-inches input (KI-009, ADR-0019 u3).
- [ ] Fraction display toggle in the GUI.
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
      `.github/workflows/release.yml` builds and smoke-tests the Windows installer, the
      macOS `.dmg`, the AppImage, and the Flatpak, writes `SHA256SUMS`, and on tags
      attests, drafts the release, and publishes to PyPI (ADR-0022, slices d1 to d6).
      Its dry runs pass on all three; it hasn't run on a tag yet.
- [ ] Move CI's Linux jobs to Ubuntu 26 once its package names are checked. They're pinned
      to `ubuntu-24.04` (`.github/workflows/ci.yml`), since the test job installs Qt's
      runtime libraries by name: libegl1, libgl1, libxkbcommon0, libfontconfig1 and
      libdbus-1-3.
- [x] Third-party license notices in the app folder (KI-016): full texts in `licenses/`, vendored by `packaging/fetch_notices.py`
- [ ] Light and dark Qt themes built from the UI palette (`gui/assets/palette.toml`,
      [design/palette.md](design/palette.md)), replacing the ad-hoc HTML colors in `gui/window.py`
- [x] Welcome screen at startup, replacing the splash screen (ADR-0015): composed from a
      pack's parts (art, focal point, vertical logo) with live name and version text,
      shared File and Help commands, and the public build's art, the item below.
- [x] Generic art for the public build. **The logo and app icon are done** (2026-10-26,
      [design/brand.md](design/brand.md)): the maintainer's artwork, in the `.ico`,
      `.icns`, Linux icons, About, the welcome screen's title and the installer. **The
      welcome art is done** (2026-10-26; the Viking with the abacus since 2026-10-27):
      the maintainer's, © inmymoonsuit, for this project only (ART-LICENSE.md), to the
      art specification
      ([ADR-0015, amendments](decisions/0015-welcome-screen.md);
      [design/welcome-screen.md](design/welcome-screen.md)). It replaces the art generated
      from the palette. Its source files aren't in the repo; whether to add them is the
      maintainer's call.
- [ ] One crimson: the UI palette's `#A3122F` (`palette.toml`) and the brand's `#A31D31`
      are two near values. Make them one, as a deliberate palette change with its own
      contrast tests ([design/brand.md](design/brand.md), "Palette").
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
| Default unit system (in vs mm) | ADR-0005, ADR-0024 §6 | **Decided by ADR-0024:** there's no unit system. Each calculator declares its fields' units and its output sets, inches for the course and US shops, and each picker is the user's for the session. Remembering the choices across sessions waits for saved preferences. |
| Default method when legacy and general both exist | ADR-0010 | Legacy first until a general method is `verified`. **Now due:** the K-factor is verified at 90° in both bend calculators (ADR-0010, amendments); the fixed K-factor, the course formula, is still first. |
| Python package and app name | pyproject.toml | Keep `cadd-calculator` / `caddcalc`. Renaming is cheap now and expensive later. |
| A converter's JSON rows in their own units | ADR-0018, the m2 amendment (the command line gives each row in base units) | Done in ADR-0024 E-4: JSON's schema 1 gives each row in `base` and as `shown`, in its own unit or form, with a form's `copied` text. (The cloud review of m2, Minor 4.) |
