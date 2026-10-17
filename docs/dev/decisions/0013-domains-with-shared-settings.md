# ADR-0013: Domains with shared settings that their calculators inherit

* **Status:** **Accepted** (maintainer, 2026-10-17): the design, and the recommended option
  of every decision below. Phase 1 is being built (§11). Phase 2 will be refined in its own
  ADR before it starts.
* **Date:** 2026-10-17
* **Reviewed by:** the Support & Review session (prior art, critique) and the Calculator
  Engine session (implementation), 2026-10-17

## Context

Calculators are grouped by a display string (`domain = "Sheet Metal"`). Users want to set
values once for a whole family by selecting the family's row in the calculator list.
Material and thickness are the examples for sheet metal. Every calculator in the family
then uses those values unless it is overridden.

The code already shares parameters informally. `THICKNESS`, `INSIDE_RADIUS`, and
`K_FACTOR` are Python constants that several calculators reuse with local changes:
* The cone gives thickness its own default.
* The V-die calculator uses thickness only in its `eight_t` method, and radius only in
  its `radius_ratio` method.

Nothing tells the engine, the GUI, or a plugin that these are the same quantity.

**Where values come from (maintainer, 2026-10-17).** A value is either built in or a
decision the user makes during the session:
* *Built in*: a calculator's own defaults, and later tables shipped with the app.
* *Decided by the user*: a value set in the GUI. It lasts for the session and is not
  saved.

The app creates no user files.

This design is the foundation for every future family (structural, tolerancing,
fasteners), so it is general rather than sheet-metal specific.

### Prior art (official documentation; paraphrased)

| Tool | Shared level | Per-feature override | Material link |
|---|---|---|---|
| SOLIDWORKS 2026 | Base flange / sheet-metal feature: thickness, bend radius, bend-allowance method (K, BA, BD, tables), relief, gauge table | "Use default radius" and "Use gauge table" on flanges and bends; thickness never per feature | Gauge table drives thickness, radii, and K. Custom materials can link K/BA by thickness range (opt-in) |
| Inventor 2026 | Sheet Metal Defaults → Rule (material, thickness, radius, relief, unfold rule: linear K, bend table, or equation) | Fields default to named rule parameters; typing a value overrides | Material is a field of the rule; no gauge object |
| Fusion | Sheet-metal rule (thickness, radius, linear K, relief, material label; values can be expressions of thickness) | "Override rules" checkbox per flange, fold, or hem | None; in effect one rule per material and gauge |
| Onshape | Sheet Metal Model (thickness, radius, K/BA/BD method; K defaults to 0.45) | "Use model bend radius" and "Use model K factor"; per-bend table overrides | None; gauge data kept as variables |

Sources:
* SOLIDWORKS: [base flange](https://help.solidworks.com/2026/English/SolidWorks/sldworks/r_base_flange_propertymanager.htm),
  [edge flange](https://help.solidworks.com/2026/English/SolidWorks/sldworks/HIDD_FEAT_SM_EDGE_FLANGE.htm),
  [gauge tables](https://help.solidworks.com/2026/English/SolidWorks/sldworks/c_Sheet_Metal_Gauge_Tables.htm),
  [linking materials](https://help.solidworks.com/2026/English/SolidWorks/sldworks/t_linking_materials_and_sheet_metal_parameters.htm),
  [different bend radius](https://help.solidworks.com/2026/English/SolidWorks/sldworks/t_different_bend_radius.htm)
* Inventor: [sheet-metal rules](https://help.autodesk.com/cloudhelp/2026/ENU/Inventor-Help/files/GUID-D1EBE010-86D3-49CC-88B3-522F9A0CCA3B.htm),
  [unfold rules](https://help.autodesk.com/cloudhelp/2026/ENU/Inventor-Help/files/GUID-7B2525E4-8191-46F2-8CC3-FF422114EAE5.htm),
  [style library](https://help.autodesk.com/cloudhelp/2026/ENU/Inventor-Help/files/GUID-D1523A53-F345-4350-8039-ABFE1A45912F.htm)
* Fusion: [sheet-metal rules](https://help.autodesk.com/cloudhelp/ENU/Fusion-Sheet-Metal/files/SM-RULES-REF.htm),
  [flange overrides](https://help.autodesk.com/cloudhelp/ENU/Fusion-Sheet-Metal/files/SM-REF-BASE-EDGE-CONTOUR-FLANGE.htm)
* Onshape: [sheet metal model](https://cad.onshape.com/help/Content/PartStudio/sheet_metal_model.htm),
  [sheet-metal table](https://cad.onshape.com/help/Content/sheetmetaltable.htm)

What the four tools agree on:
1. Thickness, the default bend radius, and the bend method or K-factor live at the
   shared level.
2. Every tool lets a feature override the radius. None lets a feature override the
   thickness.
3. An override is a visible "use default" toggle, and it stays in place until the user
   turns it back. No tool drops an override when the default changes.
4. Material drives values only through an opt-in link (SOLIDWORKS), or by being part of
   the rule itself (Inventor, Fusion).
5. The most-reported pitfall is an override that silently stops following the default
   when the default changes. No tool clearly flags it, and this design's markers do.

## Proposed design

### 1. `Domain` is a declared object

`caddcalc.core.domain.Domain` is a frozen dataclass with these fields:
* `id`, e.g. `"sheet_metal"`
* `name`, e.g. `"Sheet Metal"`
* `summary`
* `settings`: a tuple of `Param`
* `references`

Rules for settings:
* A setting has **no default** (`default=None`), so "unset" is unambiguous and never
  competes with a calculator's own default.
* A setting isn't limited to particular methods.

Each domain package declares its domain, e.g. `calculators/sheet_metal/domain.py`, and
exports `DOMAIN` next to `CALCULATORS`.

### 2. A calculator names its domain explicitly

`Calculator.domain` holds a **domain id**, not a display name.
* Built-in calculator IDs start with their domain id (`sheet_metal.…`). A test checks
  this convention.
* Plugins may use their own prefix, e.g. `acme.sheet_metal.press_brake`, so they can't
  collide with future built-ins.
* An unknown domain fails registration with a "did you mean" hint (decision G).
* The display name comes from the `Domain`.
* `Registry.by_domain()` returns `Domain` → calculators, sorted by name.

### 3. Shared parameters are opt-in and validated

A calculator `Param` with `shared=True` must use the key of a setting in its domain, with
the same `Dimension`. Registration enforces this.

The calculator may still:
* keep its own default (the cone)
* narrow the allowed range
* limit the parameter to some methods (the V-die calculator, and K for the `k_factor`
  method only)
* use a different symbol

A plugin can't add settings to another package's domain.

### 4. One precedence rule, with a slot reserved for materials

For each input the selected method uses, the first of these that exists wins:

1. **Explicit**: a value given for this run (a form field set to override, a CLI
   argument, the API)
2. **Domain**: the session's domain setting, if the user has set it
3. **Derived** *(phase 2)*: computed at run time from a built-in material or gauge
   table
4. **Default**: the calculator parameter's own built-in default
5. Otherwise an `InputError`

A value that is out of range for this calculator **fails**, naming where it came from,
e.g. "Sheet Metal setting T = … is outside this calculator's range; override it here".
It never silently falls back to a default.

### 5. Provenance on every input

`Result.input_sources` maps each input key to an `InputSource`, which has:
* `kind`: explicit, domain, derived, or default
* `label`: e.g. "Sheet Metal settings"
* `reference`: an optional table name and version, used in phase 2

`Result.to_dict()` includes the source of every input. `core.formatting` writes the
wording, so the GUI and the CLI print the same text, e.g.
"T = 0.1046 in (Sheet Metal settings)".

### 6. Engine API

`Calculator.run(inputs=None, method=None, *, settings=None)`, where `settings` holds the
values the user has set for this calculator's domain, in base units. The Python API stays
pure: with `settings=None`, results are exactly what they are today.

### 7. Settings last for the session (decision B)

* `caddcalc.core.settings.DomainSettings` is a pure, in-memory model of the values the
  user has set, per domain. It validates them against each domain's settings. Following
  the numeric-intent rules below, each value keeps its base-unit number and the text the
  user typed.
* The GUI holds one `DomainSettings` for the life of the app window. Closing the app
  discards it; the next session starts with every setting unset. There is **no settings
  file**, no store, and no new dependency.
* **The CLI needs no settings feature.** Each run of `caddcalc run` is its own session
  for one calculator, so an explicit argument (`T=3mm`) already does what a domain
  setting would. The CLI's only change is the input sources in its text and `--json`
  output.
* If the roadmap's saved sessions ever arrive, they can serialize this same model. That
  is a separate decision.

### 8. GUI

* **Domain rows become pages.** Selecting "Sheet Metal" shows a form generated from
  `Domain.settings`:
  * an empty field means unset
  * each field lists the calculators and methods that use it, e.g. "V-die opening (8×T
    method)"
  * a count shows how many calculators override it
  * a "Clear all" button
* **Inherit or override, per shared field.**
  * An explicit "Use Sheet Metal value" toggle controls the field. Only overridden
    fields are passed to `run` as inputs. Today every field is passed, which made shared
    values unreachable.
  * Overrides are sticky for the session (decision C).
  * A non-modal note appears when the shared value changes while a field overrides it.
* **"Load course example"** fills a calculator's course-example values as explicit
  inputs (decision D).

### 9. Numeric intent (amends ADR-0005; decision J)

Parametric CADD's units and numeric-values standards come from hard experience. Its
lessons that fit a calculator app:

1. **Three tiers.**
   * *Intent* is what the user typed, kept as the text and its exact parse in base units.
   * *Computation* uses doubles.
   * *Presentation* is rounded display text.
2. **Display text is never read back as intent.** A unit switch, an inherited value, and
   "Load course example" keep the base value. Only the user's own typing creates new
   intent. Today the GUI breaks this rule (KI-017), and phase 1 fixes it.
3. **Typed text is kept beside the value** for anything the user enters, form fields and
   domain settings alike. A field shows the user's own spelling while its unit is
   unchanged, and a converted value otherwise.
4. **Doubles stay** (ADR-0005). Parametric CADD needs `Decimal` because Blender caches
   values as float32. This app has no float32 tier, and its formulas are transcendental.
5. **Rules recorded now, for features that don't exist yet:**
   * If an input ever accepts expressions, each term carries its own unit (Parametric
     CADD I-0035: `1 + 1in` must be 2 in, not 26.4 mm).
   * Adding a length to an angle is refused.
   * Numeric thresholds, such as where `tan` is undefined, are named constants in one
     place.
   * Drawing conventions (ASME or ISO zero suppression, fraction carry, feet-and-inches)
     are display preferences only.

### 10. Plugins

* Domains register through a `caddcalc.domains` entry-point group.
* All domains are registered before any calculators.

### 11. Phasing

**Phase 1**, with sheet-metal settings for thickness, inside radius, and K-factor
(decision A). It is built in slices, each passing ruff, mypy, lint-imports, and pytest:
1. domains
2. shared parameters, precedence, and provenance (including CLI output)
3. the sheet-metal settings
4. the in-memory settings model
5. the GUI domain page
6. GUI inherit and override, the numeric-intent rules for form fields (fixes KI-017),
   and "Load course example"
7. close-out: this ADR accepted, and amendments to ADR-0003, ADR-0005, ADR-0006, and the
   guidelines

**Phase 2** is materials:
* built-in reference tables with provenance and license fields (ADR-0004, ADR-0008)
* a categorical parameter kind, used for material, gauge, and a domain-level default
  bend method (related to the ADR-0010 default-method question)
* one active gauge table per domain
* derived values: a suggested K, the die ratio P, and minimum-radius checks, live while
  linked (decision E)

User- or shop-editable tables would need files, which is outside the session-only model.
They are left for a later decision.

## Decisions (all decided 2026-10-17)

The maintainer accepted the recommended option for each.

| | Question | Decision | Alternatives not taken |
|---|---|---|---|
| A | Shared in phase 1 | Thickness, inside radius, K-factor. The die ratio P moves to phase 2, derived from material. | All four; or thickness and K only |
| B | Where settings live | For the session only, not saved. | A per-user settings file |
| C | Overrides | Explicit toggle, sticky for the session. A marker, an "overridden in N" count, and a note when the shared value changes. | Overrides dropped when the shared value changes (no CAD tool does this, and it loses work) |
| D | Shared values vs course-example defaults | A set domain value wins, and "Load course example" restores the exact lesson inputs. | The domain value wins, with no course-example action; or course methods ignore domain values (an inconsistency nobody can see) |
| E | Material-derived values (phase 2) | Live while linked to the material; typing a value breaks that field's link. | Suggestions the user accepts; or always live |
| G | Plugin calculator naming an unknown domain | Fail registration with a "did you mean" hint. | Create an empty domain automatically |
| J | Adopt the numeric-intent rules (§9), amending ADR-0005 | Yes, and fix KI-017 in phase 1. | Keep ADR-0005 as is, and fix KI-017 alone |

**What D means in numbers:** with Lesson 4's cone and thickness set to Lesson 2's
0.1046 in, the course method's sweep angle becomes 132.30° instead of 132.70°.

**What E means in numbers:** at T = 0.1046 in, R = 0.156 in, and a 90° bend, the bend
allowance is:
* 0.3108 in with K = 0.40
* 0.3120 in with the course formula
* 0.3173 in with K = 0.44

That is about 2% per bend.

## Consequences

* Shared quantities become explicit and validated, not constants that happen to be
  reused.
* Every input of every result carries its source, which also prepares printed
  calculation sheets.
* There is no persistence and no new dependency, and the architecture layers stay as
  they are.
* Public-API changes before 0.1:
  * `Calculator.domain` becomes an id
  * `run()` gains `settings`
  * `Result` gains `input_sources`
  * there is a new entry-point group

  Each needs a CHANGELOG entry. None needs a deprecation shim yet.

## Alternatives considered

* **Global "preferences" without domains:** this doesn't scale to several families with
  different quantities.
* **Sharing parameters implicitly when their keys match:** this couples calculators by
  accident, and a plugin could inherit a value it never expected.
* **Settings handled in the GUI only:** this puts engineering behavior in a front end,
  against ADR-0003.
* **Deriving each calculator's domain from its ID prefix:** this is simpler, but forces
  plugins to use built-in prefixes, which risks collisions. Built-ins keep the prefix as
  a tested convention instead.
* **A per-user settings file** (in an earlier draft of this ADR, using `tomli-w` and
  `platformdirs` in a new services layer): it was dropped when the maintainer chose
  session-only settings.
