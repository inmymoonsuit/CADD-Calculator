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

`0.64T + 1.57R` is *Machinery's Handbook* 31st ed., Eq. (33) (printed p. 1421; p. 1347 in
the 29th ed.): 90° bends in half-hard copper and brass, soft steel, and aluminum. The
Handbook uses 0.55T (Eq. 32) and 0.71T (Eq. 34) for other material classes. It is equivalent to K ≈ 0.408 with π/2 rounded
to 1.57. **Possible next step:** a "Handbook 90° empirical" method with a material-class
input, plus the Handbook's worked example as a `verified` test.

### KI-003: Die-opening ratio was hard-coded for mild steel (Medium)

The legacy `FDO = R/0.156` encodes the air-bending rule that the inside radius forms at
about 15.6% of the V-die opening, the course's mild-steel value. Other materials differ.
**Now:** `P` is an input (default 0.156). **Still missing:** a per-material table with
cited sources (roadmap). The rule is not in MH29, MH31's bending section (pp. 1417–1424),
or EDD5. The review session points to The Fabricator's "20 percent rule" articles (Steve
Benson). Their terms couldn't be read,
so their figures aren't reproduced here (ADR-0014 §5.2, M3), and they haven't been
re-checked.

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
**virtual sharp** (outside mold line), with setback `tan(A/2)·(R + T)`. That matches the
90° course sheets and the press-brake convention (the SOLIDWORKS help, linked in
ADR-0013's prior art, defines BD = 2·OSSB − BA). EDD5 Fig. 19.11b instead dimensions a
bend past 90° to the **outermost tangent of the outside arc**, which subtracts `R + T` at
any angle. At 135° the two setbacks are 2.414·(R + T) and 1.0·(R + T). The calculator
warns when A > 90°. **Options:** add an explicit dimension-origin input (virtual sharp /
outer-arc tangent / inside mold line), with an ADR choosing the default. The choice is
the maintainer's.

### KI-014: 180° hems are rejected (Low)

Bend angles must be below 180° because the outside setback, tan(A/2)·(R + T), is undefined
for a hem. BA itself is fine at 180° (MH31 Fig. 13 has one, MH29's Fig. 12), so the
published example's test has to double the 90° value in test code. **Possible fix:** let an `Output` be marked optional or
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
**Progress (2026-10-17):** `THIRD_PARTY_NOTICES.md` now exists. The build copies it into
the app folder, and it carries Tabler Icons' full MIT text, VT323's full SIL Open Font
License (ADR-0016), a table of the bundled runtime components, and the note on replacing
the Qt libraries. **Still needed before a public
release:** the full license texts for those runtime components (LGPL-3.0 and the GPL-3.0
it builds on, the PSF license, Apache-2.0, libffi's MIT text, and the MSVC runtime terms).

### KI-018: Switching to another window mid-edit ends a calculator edit (Low)

A calculator field's edit is judged when it ends, and Qt ends it when the field loses
focus, including to another application (Alt+Tab). A half-typed value is then judged
as final: if it differs from the value in use it is kept, and in a shared field it
overrides. Typing on and pressing Enter replaces it with the intended value, but a
retype interrupted this way can leave an override that a full retype wouldn't. The
field's override note and the settings page's "Overridden in N" count show it, and
ticking "Use … value" undoes it. Accepted for now; the code that judges an edit
points here (`MainWindow._finish_field_edit`).

### KI-020: Checks by hand on real windowing systems (Low)

The welcome screen (ADR-0015) is frameless and application-modal, and the result fields
(ADR-0017) depend on the platform's keys, style, and screen reader. CI runs Qt's
offscreen platform, which can't show how real windowing systems treat them, so these
need checking by hand before a release on each platform:

* **Wayland (Linux):** the compositor places windows, so the card may not open centred;
  dragging the top bar must still move it (`startSystemMove`). Stay-on-top hints are
  ignored, but the card still blocks the main window.
* **macOS:** About and Exit (Quit) must appear in the application menu for the main
  window, and the card must open as a window, not as a sheet attached to the main
  window. A calculator's work must be in a fixed-width face: where Consolas isn't
  installed, it's the system's fixed-width family, which on macOS may be a private one,
  named with a leading dot (ADR-0016, amendments).
* **The startup order (ADR-0015, amendments):** check that the main window appears once,
  behind the card, without taking its focus, and that the card stays above it until it's
  closed: it's a window the main window owns. Wayland ignores stacking requests, so check
  there especially, and on macOS.
* **Frameless windows everywhere:** check whether the system draws a shadow, and that the
  ⓘ, the X, Esc, and dragging work.
* **Rounded corners (ADR-0016 §4):** the card is a translucent window that paints its own
  rounded corners and border. Without a compositor, a translucent window's corners show
  black, and Qt's public API doesn't say whether an X11 desktop runs one. So the card
  rounds its corners only on Windows, macOS, and Wayland, which always composite
  (`COMPOSITING_PLATFORMS` in `gui/welcome.py`), and keeps them square on X11 and any
  other platform. Rounding on X11 would need asking the X server whether a compositor
  owns the `_NET_WM_CM_Sn` selection. On Windows 11, the system's own rounding doesn't
  apply to frameless windows, so the painted radius is what shows. Check that the
  corners are clean, with no dark or light fringe, at each display scale.
* **Keyboard focus:** Tab to the ⓘ and the X on each platform's real style and check
  that a focus ring shows; they are flat (auto-raise) buttons, which some styles draw
  without one.
* **Displays:** check 100%, 150%, and 200% scaling, and a small screen (e.g. 1366 × 768 at
  150%), where the card should shrink to fit.
* **The result fields' menu keys (ADR-0017):** on a real Windows window, check that the
  Menu key and Shift+F10 on a focused copy button open its menu of copy forms. Offscreen
  tests send the menu event itself, not the platform's key-to-menu step.
* **The result fields' focus (ADR-0017):** on a native Windows window, Tab to a copy
  button and check that only the focus ring shows, with no focus frame of the style's
  own inside it.
* **Screen readers (ADR-0017):** check that Narrator or NVDA reads a result field ("Bend
  allowance, BA: 0.3119 inches"), its copy button with its value, and the announcement
  after a copy. The tests check the names and the announcement calls, not the speech.

The art specification (docs/dev/design/welcome-screen.md) points here.

### KI-022: Values are always written with "." as the decimal point (Low)

The app writes every number with ".", on screen and when copying (ADR-0017 F5). A copied
value, or Copy all's rows, pasted into a spreadsheet set to a comma-decimal locale, such as
German or French, can be read as text or a date rather than a number. Typed input
accepts only "." too.

* **Workaround:** set the spreadsheet's import or paste to "." as the decimal separator,
  or paste into a cell formatted as text and convert it.
* **Planned fix:** ADR-0020 (accepted, its L4). Numbers the app formats show, and are
  typed, with the user's regional decimal separator; numbers quoted from a source stay
  as published. Copy and Ctrl+C keep ".", which CAD reads; Copy all uses the locale's
  separator, for a spreadsheet, and the menu gains a "Copy 0,3119" form. JSON keeps ".".
  Everything that reads a shown number's decimals already asks one helper,
  `core.formatting.decimal_separator()`.

### KI-023: Three things don't fit a window at its least size (Low)

The window's least size comes from the calculator page, which scrolls rather than
squeezes. At that size, three things are cut short:

* **The disclaimer** is one line across the status bar, so a window narrower than the
  sentence cuts off its end.
* **The method box** elides its method, e.g. "Course formula (0.64T + 1.57R) [unverif…".
  Its list shows each method in full.
* **The family settings page** is wider than the calculator page at its least, so it
  scrolls sideways there.

The pseudo-locale test (`tests/test_translated_gui.py`) allows only these three, so any
new clipping fails it.

* **Planned fix:** the window-layout work the maintainer approved on 2026-10-18 (a launch
  size fitted to the screen, and a cap on the whole page), whose rules UI/UX is
  writing. The test's allowance goes with each fix.

## Resolved

### KI-024: With shorter text lines, the tallest page could scroll at launch (resolved 2026-10-18)

The window's launch height was `launch_lines` line spacings, 736 px with 9 pt Segoe UI's
16 px lines, but the result fields' heights are in pixels (ADR-0017's tokens). With a UI
font whose lines are shorter, such as the offscreen platform's 14 px, the launch window
was shorter while the pages weren't, so the cone and segment pages scrolled as a whole at
launch (rule C) where on Windows they fit. The launch height now also covers the tallest
built-in calculator page at the launch width, within the screen, on UI/UX's ruling
(ADR-0021 §3, amendments). On Windows at 9 pt it's unchanged. `test_no_calculator_page_scrolls_at_the_launch_size`
runs everywhere, with lines under 16 px too.

### KI-021: The cone's course method took a bottom diameter no larger than the thickness (resolved 2026-10-17)

The course method's sweep angle is `FPA = 180·(Db − T)/FPOR`, so a bottom diameter equal to
the thickness gave 0°, and a smaller one a negative angle: a pointed cone with Db = 2 mm,
Dt = 0, H = 5 mm, and T = 3 mm gave −35.30°. The maintainer approved a guard: "Yes, add the same input guard
to the course cone method; it doesn't change the formula." Both methods now refuse such
input with "Bottom diameter must be larger than the thickness for this method." The
formula, the golden values, and the course example (132.70°, and 132.30° with Lesson 2's
thickness) are unchanged (ADR-0010, amendments).

### KI-019: The app and the tests could crash on exit (resolved 2026-10-17)

* **Symptom.** After the window closed, the interpreter could abort or crash on exit:
  "QObject: shared QObject was deleted directly", then exit status 134 or 139 on Linux and
  macOS, and 127 or 139 on Windows. In a Linux container, the app's own `--smoke-test`
  crashed on 13 of 15 runs, and a normal close after visiting pages on 14 of 15. The test
  suite crashed after "496 passed", which failed every CI job from the phase 1 push on.
* **Cause.** Slice 6 (a2f23d0) connected each field's signals to
  `functools.partial(self._handler, key)`. Qt holds a connected callable strongly, so the
  window's own child widgets held the window: a cycle through C++ that Python's collector
  can't see. The window outlived the code that made it and was torn down during
  interpreter exit, re-entrantly: deleting a child dropped the last slot holding the
  window, which deleted the window's widget tree from inside its own teardown.
* **Fix.** The window connects through `_slot`, which holds the window weakly, so a window
  is freed when its last reference goes
  (`test_a_window_is_freed_when_the_last_reference_goes`). `main()` closes and deletes the
  window while the application still runs. The `qt` test fixture closes and deletes each
  test's windows, then delivers the deferred deletes, as pytest-qt's `qtbot` does, and
  every GUI test uses it.
* **Also found.** The `caddcalc-gui` entry point called `main()` with no arguments, so it
  ignored the command line, `--smoke-test` included. `main()` now reads `sys.argv`.

### KI-017: Switching units in the GUI rounded the typed value (resolved 2026-10-17)

Changing the GUI between in and mm rewrote each field as six-decimal text and read it
back as the user's value: `1/3` in became `0.333333` in after one round trip, a loss of
8.5e-6 mm. Calculator fields now keep what the user typed as a `TypedValue`, and other
values (defaults, inherited family values, the course example) as base values. A unit
switch changes only the display, through `core.formatting.entry_text` (ADR-0013 §9).
Tested by `tests/test_calculator_page.py::test_a_units_round_trip_never_changes_a_calculator_value`.

### KI-011: K-factor method had no page citation (resolved 2026-10-16)

It now cites EDD5 Ch. 19, pp. 782–785 (K = 0.4 instructional). The Fig. 19.12 worked example
is a test (`tests/test_published_examples.py`).

### KI-012: Source for scaling the 90° formula by A/90 (resolved 2026-10-16)

MH29 "Angle of Bend Other Than 90 Degrees", printed p. 1351, gives this rule, and Fig. 12 is
tested. In the 31st edition the rule is on p. 1421 and the example is Fig. 13, the same
numbers; the test cites MH31 now. The first draft of this entry wrongly said the Handbook didn't cover it (see the engineering log).
