# Known issues and open formula questions

Stable IDs (`KI-NNN`) are referenced from code, method notes, and tests. Never reuse an ID.
When an issue is resolved, move it to **Resolved** with the date and the PR or ADR that
resolved it. Actionable work also gets a GitHub Issue that links back here.

Severity: **High** means it can produce a wrong part. **Medium** means a misleading result
or missing safeguard. **Low** means a limitation or cosmetic problem.

## Open

### KI-001: Legacy cone sheet uses two diameter bases (High until resolved)

*Lesson 4 - Cone Spread Sheet* computes the radii from the diameters as given, but the
sweep angle from `(Db − T)`: `FPA = 180·(Db − T)/FPOR`. For the course example (Dt 6, Db 10, H 5, T 0.0747):

* The bottom arc `FPOR·FPA` = 31.181 in = π·(Db − T). It matches the **mean** circumference.
* The top arc `FPIR·FPA` = 18.709 in, which rolls to a 5.955 in diameter. That is neither
  6.000 (outside) nor 5.925 (mean).
* A consistent mean-diameter development gives FPA = 133.70°, not 132.70°. That is 0.235 in
  of arc at the outside radius.

*Engineering Drawing and Design* (Ch. 23) states the sector angle as (base radius / slant
height)·360 and doesn't say which surface to use. The legacy sheet fits that rule with a mean
radius over an outside slant height.

**Options:**
1. Keep `course` as the default for coursework.
2. Default to `mean_diameter`.
3. Add an input for which surface the diameters describe (outside, inside, or mean).
   This changes only the radii. The sweep angle is 360·sin(half-angle) =
   360·((Db − Dt)/2)/CH on every parallel surface (EDD5 Ch. 23, p. 1051; EDD6 p. 883),
   so 132.70° can't come from any single surface.

**Status:** both methods ship, and the legacy method is pinned (ADR-0010). Which one is the
default is the maintainer's call.

### KI-002: Course bend-allowance formula is for one material class (Low)

`0.64T + 1.57R` is *Machinery's Handbook* 29th ed., Eq. (33) (printed p. 1347): 90° bends in
half-hard copper and brass, soft steel, and aluminum. The Handbook uses 0.55T (Eq. 32) and
0.71T (Eq. 34) for other material classes. It is equivalent to K ≈ 0.408 with π/2 rounded
to 1.57. **Possible next step:** a "Handbook 90° empirical" method with a material-class
input, plus the Handbook's worked example as a `verified` test.

### KI-003: Die-opening ratio was hard-coded for mild steel (Medium)

The legacy `FDO = R/0.156` encodes the air-bending rule that the inside radius forms at
about 15.6% of the V-die opening, which is roughly right for mild cold-rolled steel. Other
materials differ. **Now:** `P` is an input (default 0.156). **Still missing:** a per-material
table with cited sources (roadmap). The rule is not in MH29 or EDD5. The review
session points to The Fabricator's "20 percent rule" articles (Steve Benson): about 15–17%
for cold-rolled mild steel and 20–22% for 304 stainless. Those articles haven't been
re-checked here yet.

### KI-004: The "8 × T" die-opening rule has no citation (Medium)

The `eight_t` method is a common rule of thumb, implemented without a reference. It stays
`unverified` until it is cited.

### KI-005: "Show work" substitution assumes homogeneous formulas (Low)

The numeric line substitutes values in *display* units (e.g. inches). That is valid for
every current formula because they are dimensionally homogeneous. A future formula with a
unit-specific empirical constant must convert explicitly, and its display will need care (ADR-0005).

### KI-006: Only outside (mold-line) dimensioning is supported (Medium)

Flat-length calculators assume formed dimensions are to the outside of the material, as
the course did. The main alternative convention, for bends past 90°, is EDD5 Fig. 19.11b
(p. 784); see KI-013. Inside dimensions, centerline dimensions, and dimensions to the tangent
point are not supported yet. The glossary states the convention.

### KI-007: Mean-diameter cone ignores the wall-slope correction (Low)

On a sloped wall, the horizontal offset of the mid-surface is (T/2)/cos(β), where β is the
wall's angle from vertical, not T/2. The effect is small for steep cones and larger for flat
ones. It is documented in the method notes.

### KI-008: Legacy label mistake on the non-90° sheet (Low, historical)

In the Rough Draft workbooks, cell D14 on "Non-90 Degree Bend Calculations" says "with 2
90 Degree Bends", but the formula is for two arbitrary angles. Recorded for history only;
the app doesn't reuse the labels.

### KI-009: No feet-and-inches input (Low)

`parse_quantity` accepts `2'` and `1-1/2"` but not the combined `3'-4 1/2"`.

### KI-010: GUI is a skeleton (Low)

No saved sessions, printing or export, fraction display toggle, dark-mode polish,
accessibility review, or translations yet. See the roadmap. **When adding the fraction
toggle:** `expr.render_numeric` substitutes text as given, so fractions in the work lines
must be parenthesized ("1/8/1/16" is ambiguous), or the work lines should stay decimal.

### KI-013: Where outside dimensions are measured on bends past 90° (High)

`segment_flat_length`, and the OSSB and BD outputs of `bend_allowance`, measure to the
**virtual sharp** (outside mold line), with setback
`tan(A/2)·(R + T)`. That matches the 90° course sheets and the press-brake convention
(The Fabricator; SOLIDWORKS defines BD = 2·OSSB − BA). EDD5 Fig. 19.11b instead dimensions
a bend past 90° to the **outermost tangent of the outside arc**, which subtracts `R + T`
at any angle. At 135° the two setbacks are 2.414·(R + T) and 1.0·(R + T). The calculator
warns when A > 90°. **Options:** add an explicit dimension-origin input (virtual sharp /
outer-arc tangent / inside mold line), with an ADR choosing the default. The choice is the maintainer's.

### KI-014: 180° hems are rejected (Low)

Bend angles must be below 180° because the outside setback, tan(A/2)·(R + T), is undefined
for a hem. BA itself is fine at 180° (MH29 Fig. 12 has one), so the MH29 test has to double
the 90° value in test code. **Possible fix:** let an `Output` be marked optional or
not-applicable, so `bend_allowance` accepts A = 180° and reports BA with OSSB and BD shown
as "n/a (hem)". That needs a small change in `Calculator.run`, which today raises SpecError
when any output is missing.

### KI-015: Slow start on machines with many fonts (Low)

On the maintainer's PC, which has 2,454 font families, the app takes 2.5 to 3.5 s to open,
packaged or run from source. Profiling a source run: about 0.5 s for Qt's DirectWrite
font database to list the families, and 1.5 s for the first `show()` (probably font
fallback for π, ·, and ° in the results). The app's own work takes 0.13 s. With
`QT_QPA_PLATFORM=windows:fontengine=gdi` the start takes 1.3 s. **Next:** measure on a
typical lab PC. If it's still slow, try naming font families for the results pane, or
show a splash screen. Switching the font engine changes how text looks, so check that
before choosing it.

### KI-016: Packaged builds lack third-party license notices (Medium)

The app folder bundles at least Qt 6 and PySide6/Shiboken (LGPL-3.0), CPython (PSF
License), OpenSSL's libcrypto (Apache-2.0), libffi (MIT), Nuitka's runtime (Apache-2.0),
and the Microsoft C++ runtime (redistributable). `packaging/build.py` copies only the
project's `LICENSE.md`, and the PySide6 wheels carry no LGPL text to copy.
**Needed before a public release:** `THIRD_PARTY_NOTICES.md` (ADR-0008, Remaining) with
the LGPL texts and a note on replacing the Qt libraries, copied into the app folder by
the build.

## Resolved

### KI-011: K-factor method had no page citation (resolved 2026-10-16)

It now cites EDD5 Ch. 19, pp. 782–785 (K = 0.4 instructional). The Fig. 19.12 worked example
is a test (`tests/test_published_examples.py`).

### KI-012: Source for scaling the 90° formula by A/90 (resolved 2026-10-16)

MH29 "Angle of Bend Other Than 90 Degrees", printed p. 1351, gives this rule, and Fig. 12 is
tested. The first draft of this entry wrongly said the Handbook didn't cover it (see the engineering log).
