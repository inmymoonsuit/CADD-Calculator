# Engineering log: attempts, dead ends, and reversions

Newest first. This file records **what was tried and didn't work, or was undone**, so
nobody repeats it. Successful decisions belong in ADRs, and limitations belong in
known-issues. Keep entries short: what, why, outcome, and what to do instead.

Template:

```
## YYYY-MM-DD: Short title
**Tried:** …
**Outcome:** worked / failed / reverted (commit or PR link if any)
**Why:** …
**Instead / next time:** …
```

---

## 2026-10-25: Leaving out QtNetwork wasn't enough on Linux
**Tried:** dropping QtNetwork from packaged builds with `--nofollow-import-to` and the TLS
plugin family (run 40222824994).
**Outcome:** Windows and macOS passed; Linux failed the build's own check:
`libQt6Network.so.6` was still in the folder.
**Why:** on Linux the `platforms` family includes `libqvnc.so`, the VNC platform plugin,
which links QtNetwork. Reading DT_NEEDED across PySide6 6.12's Linux wheel, it was the
only plugin a build ships that does.
**Instead:** the build also leaves out `libqvnc.so`; the app uses xcb or Wayland. That
wasn't enough either (run 40224120571): Nuitka left the plugin out but still followed its
dependencies, so `libQt6Network.so.6` stayed, "Used by" the plugin it had skipped. The
build now leaves out the Qt6Network library by name as well (`--noinclude-dlls=*Qt6Network*`).

## 2026-10-25: Qt's catalogs in a Windows-only folder on Linux and macOS
**Tried:** the first CI builds of the generic edition on Linux and macOS (the release
workflow's dry run, run 40220148847).
**Outcome:** both built, and both failed the smoke test: "Qt couldn't load its own
catalog from the build". Windows passed.
**Why:** the build put the `qtbase_*.qm` catalogs in a fixed `PySide6/translations/`,
which is where PySide6's Windows wheel keeps them. Its Linux and macOS wheels keep them in
`PySide6/Qt/translations/`, and the frozen app's Qt looked there, so a German user's Qt
text wouldn't have translated on either.
**Instead:** `packaging/build.py`'s `qt_catalogs_dir()` puts them where the running
PySide6 keeps them, relative to the package. A test pins both layouts, so a Windows-only
unit-test run still checks the Linux and macOS rule, and the smoke report records the
folder Qt looked in (`qt_translations`).

## 2026-10-19: Two wrong causes for a settings picker clipped on Windows
**Tried:** at stop 3, both Windows jobs reported the Sheet Metal settings page's unit
pickers as clipped at the least window size, which no Linux run reproduced. First,
76d626e made the test settle before it sized the window, since it read the least size
before the new page's layout had run. Then bfef38a had a picker call `updateGeometry()`
when it shows, taking the layout for holding a stale size.
**Outcome:** neither was the cause, and the second was reverted. The test's new message
showed 52 px given of a 55 px least width, under Fusion, still clipped once the layout
was told to update.
**Why:** Qt's form decides a row fits beside its label without counting the gap between
them (KI-031), and Windows' Segoe UI put that row 3 px inside the gap.
**Instead:** `WrappingForm` keeps the gap in each label (KI-031). The test still
settles first, which it needs in any case. It names each clipped widget's style, font
and text width, and says whether the clip clears once the layout is told to update,
which is what told a stale size from a layout's own arithmetic.

## 2026-10-19: Knowing a picker's list is open by overriding hidePopup
**Tried:** for M-B at stop 2, the picker set `_listing` in `showPopup` and cleared it in
an overridden `hidePopup`, so the focus its list takes didn't settle a step.
**Outcome:** replaced after the cloud review of stop 2 (M1).
**Why:** Escape, and Qt closing the popup for a click outside it, close the list without
calling `hidePopup`, so `_listing` stayed set and the picker never settled again.
**Instead:** `_listing` is set only while `showPopup` runs, and after that the list's own
visibility says whether it's open (`unit_picker.UnitPicker`).

## 2026-10-19: The CLI corpus's outputs to 4 last places of the run
**Tried:** holding the corpus's outputs and steps to 4 units in the last place of a run's
largest value, from the most CI's macOS logs had shown (2).
**Outcome:** raised to 8 after S&R's native re-check of stop 2.
**Why:** S&R nudged every maths-library result: a 1-ulp difference, which is macOS's
against glibc, moves outputs by exactly 4.00 of the run's last places, so 4 had no
margin, and 2 ulps reach 6.
**Instead:** 8 (`tests/test_cli_corpus.py`, `ULPS`), which holds a 2-ulp library and
still allows at most 1.2 × 10⁻¹¹ relative; the inputs stay bit for bit.

## 2026-10-19: E-3's neutrality golden in full text, and from c7b1772
**Tried:** holding E-3 to every built-in calculator's text written with the length
preference, captured as ADR-0024's E8 says, from c7b1772, and in full: 912 runs, the
defaults, each input out of range, and each input scaled by 0.01 to 100.
**Outcome:** changed before E-3 was committed.
**Why:** c7b1772 is before F0, so F0's declared changes would count as differences E-3
didn't make. The full text was 1.45 MB, nearly all of it the 672 scaled runs, which
are there for the 60 runs whose notes the defaults never raise.
**Instead:** captured at 68e01ee, the head before E-3, with that commit's own API; the
240 default and out-of-range runs in full text, to read a difference by, and each
scaled run as the SHA-256 of its canonical JSON (`tests/data/e3_neutrality.json`,
310 KB).

## 2026-10-19: Following a pick with every untouched picker, at every step
**Tried:** in U1, the first change to a dimension's picker carried to the calculator's
other pickers of that dimension, each "moving under §2's rules", and a closed picker's
↑/↓ step was a change.
**Outcome:** replaced after UI/UX's native review of U1 (H2, M1).
**Why:** §2 re-reads a typed number in the new unit, so a field the user had typed
0.06 in became 0.06 mm when another field was picked in mm, silently, by a factor of
25.4. And the first arrow-key step, from in to ft-in, led the others there.
**Instead:** a field the user typed in never follows; only values the user didn't type
follow, converted. A step re-reads only its own field; the follow and the
announcement run when the choice settles (ADR-0024 §3, as amended).

## 2026-10-19: Recognizing a form before a unit in a field's text
**Tried:** for a field's text that names a unit (ADR-0024 Q5), reading it first by each
form's grammar with its marks optional, to offer ft-in for `5'9`, then by the unit
ending it.
**Outcome:** replaced before E-1 was committed.
**Why:** with the marks optional, feet and inches read `1-3/16"` as inches with their
mark, so the fix offered was "pick ft-in" where the text is plainly 1 3/16 in.
**Instead:** a form's marked grammar first (`1'-4"`), then a number and the unit ending
it (`1-3/16"` → pick in), and only then a form with its marks optional (`5'9`).

## 2026-10-19: Counting a tie's last places in millimeters
**Tried:** taking a count within `TIE_ULPS` = 2 units in the last place of a half as
the half, with the units counted in the base unit's last place, millimeters (ADR-0019's
amendment of fix round 4).
**Outcome:** replaced in PR #1's follow-ups (ADR-0019's amendment of the same date).
**Why:** a millimeter's last place is up to two of an inch's, so the window was up to
four units of the inch a value was typed in, and `-11.976562500000005 in`, three off a
half, was taken as the tie.
**Instead:** count them in the shown unit's last place, inches for an inch fraction. A
sweep of 520,115 typed ties in five units finds none missed either way. The window moved
rather than closed, though: values 3 or more of their own last places from a tie are
pulled to it on main when typed in in (268), cm (258) and ft (346), and here when typed
in ft (86), mm (108) and m (108), as `-254.99218750000009 mm` is (the cloud review of
PR #2; ADR-0019's amendment). Counting in the typed unit would close it, but a value
shown isn't always one typed.

## 2026-10-19: A launch height taken from the tallest built-in page
**Tried:** sizing the window at launch to the tallest built-in calculator page, with
each of its methods, at the launch width (ADR-0021 §3's tallest-page term, added for
KI-024 and widened to every method on UI/UX's M1), so no page scrolled at launch even
with a font of shorter lines than Windows'. The window laid out every built-in page
before it opened, behind an isolation boundary for a page that raised.
**Outcome:** reverted in PR #1 (`7623cb3`), on the maintainer's ruling (ADR-0021's
amendment of 2026-10-19).
**Why:** ADR-0018's Length converter, with twelve rows, made itself the tallest page,
so the window grew for everyone: offscreen at 9 pt from 765 to 996 px. A window sized to
its content grows with every long page a family adds, and laying out every page at
launch ran every calculator's code before it was chosen.
**Instead:** the launch height is `launch_lines` line spacings, 738 px at 9 pt, and a
longer page scrolls as a whole (rule C). ADR-0023's layout contract has a page declare
that it's long; until it's built, the layout test lists the long pages (KI-024).

## 2026-10-18: Converting a converter's rows in exact arithmetic
**Tried:** showing each fixed-unit row by converting the value's double to the row's unit
in exact arithmetic and rounding once (`float(Fraction(value) / unit.exact)`), as
ADR-0019 §2's "converters' exact path" suggested, so a row couldn't round twice.
**Outcome:** reverted before it was committed (ADR-0018, m2 amendment).
**Why:** the typed value is already a double, with the parser's rounding in it, so the
exact conversion of that double is no closer to what was typed: 3 ft shown in feet read
3.0000000000000004, where plain division gives 3.0. Either way the difference is past the
row's six figures and the full copy's ten, so no test could tell them apart.
**Instead:** rows use `from_base`, as every other value does; `core.units.convert` gives
the exact conversion of an exact amount, for checks. Converting what was typed exactly
would need the typed text's exact value carried to the calculator, which nothing does.

## 2026-10-18: Clearing a failed settings page at once
**Tried:** when a family's code failed on its settings page, removing the form's rows
(`QFormLayout.removeRow`) straight away, in the boundary that caught the error.
**Outcome:** failed on Linux, fixed before it was committed: the test segfaulted where
it picks a plate. Windows passed by chance.
**Why:** the failure came from the plate box's own `currentIndexChanged`. Removing the
row deleted the box while Qt was still emitting its signal, so control returned into a
deleted object.
**Instead:** hide the form at once, and clear it with `QTimer.singleShot(0, …)` once
control is back in the event loop, unless the page was built again since. Never delete
a widget from inside its own signal.

## 2026-10-18: Sampling the art under the welcome panes on a regular grid
**Tried:** in ADR-0016's slice i, each pane measured at least 4096 art pixels on a fixed
grid, each the nearest pixel, at one pixel per logical pixel.
**Outcome:** replaced by every device pixel under the pane (ADR-0016, 2026-10-18).
Support & Review first reported the name pane at 1.35:1 natively, at the card's full
size, with the card's size and scale as the cause; UI/UX diagnosed the grid.
**Why:** a regular grid aliases with periodic art. Over 1 px stripes every 17 px, it saw
1.1% of them where 5.7% are, so the percentile was taken over the wrong pixels.
**Instead:** measure every pixel, and make it cheap by tallying colours, not by sampling.

## 2026-10-18: Sorting every colour at each opacity the panes try
**Tried:** tallying the art's colours with their counts, then sorting the (value, count)
pairs at each opacity, and then selecting the 5% tails with `heapq`.
**Outcome:** both exact, but slow on art whose every pixel differs: about 1.1 s and
0.46 s for a 200% name pane of noise.
**Why:** a pane fill tries about 20 opacities, and sorting tuples, or a heap of a few
thousand, costs several passes over the colours each time.
**Instead:** a sample of the colours puts each tail's edge, and only the tail is sorted,
with a full sort where the sample misjudges: 0.27 s for the same pane.

## 2026-10-17: Reading pytest's summary line as the result
**Tried:** reporting the checks as passing from pytest's last line, e.g. "496 passed",
through every slice from phase 1 to 2a.5.
**Outcome:** missed KI-019. The interpreter crashed after that line, so the runs failed,
on CI every time; Project Management found it from the failing jobs.
**Why:** the summary is printed before interpreter exit, so a crash at exit can't change
it. Only the exit status shows it.
**Instead / next time:** confirm the exit status of every check, and repeat a GUI run
several times, since a crash at exit can be intermittent.

## 2026-10-17: Substituting a derived value's work in the display unit
**Tried:** a gauge's work showed its substituted line, then the value in the display
unit, e.g. "(70 + 0) / 16 / 41.82 = 2.6568 mm" (d03afe0).
**Outcome:** fixed in 5579818, after Support & Review's review of d03afe0 (M3).
**Why:** the expression yields inches, so the line was numerically false in mm: the
KI-005 hazard.
**Instead:** `Step.expression_unit`. The work shows the value in the expression's unit,
then in the display unit: "= 0.1046 in = 2.6568 mm".

## 2026-10-17: A per-exponent cap on exact powers
**Tried:** `evaluate_exact` refused a whole exponent above 1000 (d03afe0).
**Outcome:** replaced in 5579818, after Support & Review's review of d03afe0 (M1).
**Why:** nesting compounds exponents that each pass the cap, so
`((10 ** 1000) ** 1000) ** 1000` ran for over 20 s before it was killed.
**Instead:** bound the values, not the exponents: `MAX_EXACT_BITS` is checked after every
operation, and a whole power's size is estimated before it is computed.

## 2026-10-17: Step JSON keys only when used
**Tried:** `Result.to_dict` added a step's `substitution` only when it had one (d03afe0).
**Outcome:** changed in 5579818, after Support & Review's review of d03afe0 (L1).
**Why:** a consumer couldn't tell an old format from an ordinary step; `references` and
`subjects` are always present.
**Instead:** every step lists `substitution` and `expression_unit`, `null` when unused.

## 2026-10-17: Gauge formulas kept twice
**Tried:** each gauge formula as a display string beside a Python function that
evaluated it exactly, with a test holding the two to agree (c02bd36).
**Outcome:** replaced in d03afe0, by the proposal the maintainer approved in 2a.3.
**Why:** two copies of a formula can drift, which ADR-0004's one-string rule exists to
prevent.
**Instead:** `expr.evaluate_exact` evaluates the one expression the work shows; the float
agreement test now checks `evaluate_exact` against `evaluate`.

## 2026-10-17: Checking options at registration, and giving resolvers every selection
**Tried:** `Domain.validate_choices` computed every choice's options when the domain
registered (20e6ac8); then the resolver's `options()` got all current selections
(fe5e049).
**Outcome:** changed in fe5e049 and 22bd1e3, after Support & Review's reviews of
20e6ac8 (M2) and fe5e049 (M1).
**Why:** a dependent choice's options depend on selections that don't exist at
registration. And a resolver that read a parent it never declared lost its option
silently when that parent changed, unannounced.
**Instead:** registration checks only the static parts; options are checked when
computed; and a resolver sees only the selections of the choices it declares.

## 2026-10-17: Public domain by a source's kind
**Tried:** a statute or government document was public domain without a stated basis
(f31519c), and the host allowlist skipped a publication with no url (18f7db4).
**Outcome:** closed in 18f7db4 and 71b8e32, after Support & Review's re-probes of
f31519c (M1') and 18f7db4 (M1).
**Why:** a vendor chart declared a government document passed both, with and without a
url.
**Instead:** every public-domain publication states its basis, and the tests hold its url
to a host allowlist; one with no url must be named there on purpose.

## 2026-10-17: Sources that carried their own license and cap
**Tried:** each `[[source]]` declared its kind, license, terms, and cite-only cap
(f31519c).
**Outcome:** replaced in 18f7db4, after Support & Review's re-probe of f31519c (M2').
**Why:** one book split into five sources, each capped at 1, defined five values.
**Instead:** `[[publication]]` holds the kind, license, terms, and cap, and each
`[[source]]` cites a place in one. Two publications with the same loose title and
edition are refused, and a test counts each work's values across every shipped table
(71b8e32).

## 2026-10-17: A cite-only cap per table
**Tried:** one `cite_only_cap` in each table's header (ADR-0014's first phase 2a
amendment).
**Outcome:** replaced in f31519c, after Support & Review's review of 85082a8.
**Why:** §5.1 limits what any one cite-only source may supply, and a table-wide count
measures the table, not the source.
**Instead:** the cap is counted per defining publication, under a code-level ceiling,
`MAX_CITE_ONLY_PER_PUBLICATION`.

## 2026-10-17: Floats in nominal()
**Tried:** `nominal()` accepted a float at its exact binary value (85082a8).
**Outcome:** refused from f31519c, after Support & Review's review of 85082a8.
**Why:** some exact ties sit just below the tie as floats: US Standard 26 ga is exactly
0.01875 in, but the float rounds to 0.0187 at four decimals.
**Instead:** `nominal()` takes an exact `Fraction` or `Decimal` only.

## 2026-10-17: Suggesting the air-bend ratio P from a source we hadn't read
**Tried:** the first draft of ADR-0014's decision M3 leaned on a strength-scaling rule
and on strength figures known only from search summaries and vendor pages.
**Outcome:** reverted in Support & Review's review of the ADR-0014 draft.
**Why:** none of it had been read first-hand, and the publications' terms either
restrict reuse or couldn't be read, so nothing from them can ship (ADR-0014 §5.2).
**Instead / next time:** read a source first-hand, under terms that pass §5, before a
decision relies on it. Until then, record what was seen as a lead, not as a fact.

## 2026-10-17: Strength-scaled die ratio P
**Tried:** deriving P for each material by scaling a baseline with tensile strength, in
the first ADR-0014 draft.
**Outcome:** dropped after Support & Review's review of the draft (H1).
**Why:** published figures don't follow it for aluminum: an annealed temper is
published with a higher P than harder tempers. For steels the result depends on whether
a minimum or a typical strength is used.
**Instead:** ADR-0014 M3. P stays a user input, the course's 0.156 stays the default, and
the help asks for a test bend.

## 2026-10-17: Judging each keystroke for a no-op calculator edit
**Tried:** recording nothing when a calculator field's new value equaled the one in use,
checked on every keystroke (slice 6b).
**Outcome:** replaced in slice 6c, after Support & Review's review of 70cbdce (M1').
**Why:** the keystrokes of a retype are real changes on the way ("0", "0.1", "0.15" on
the way to "0.156"), so a retype or the typo "0.1x" still pinned an override.
**Instead:** note how the field stood at the first keystroke, apply keystrokes
provisionally, and judge the edit when it ends (ADR-0013 §8). Switching windows mid-edit
still ends an edit (KI-018).

## 2026-10-17: Typing in an inheriting field to override it
**Tried:** in slice 6, typing in a field that showed the family value made it override,
for the session.
**Outcome:** replaced in slice 6b, after Support & Review's review of a2f23d0 (M1).
**Why:** a no-op edit, such as typing a character and deleting it, pinned an override
that then ignored later family values, invisibly while the family value was unset.
**Instead:** a field inheriting a set family value is read-only, and only unticking "Use
Sheet Metal value" overrides, starting from an exact copy (ADR-0013 decision C, as the
CAD tools do).

## 2026-10-17: Applying settings-page fields on every keystroke
**Tried:** in slice 5, each keystroke in a Sheet Metal settings field set the value.
**Outcome:** replaced in slice 5b, after Support & Review's review of cf08012 (H1).
**Why:** a passing prefix was stored on the way: typing "15" for ".15" left K = 1 from
the "1". After a page or unit switch the refused "15" and its error vanished, so every
K-factor method would have used 1 with no sign of trouble.
**Instead:** a settings field applies on Enter or when focus leaves it, is checked as
the user types, and keeps refused text and its explanation until it is fixed.

## 2026-10-17: Nuitka 4.3 builds that crash when they open
**Tried:** building the app with pyside6-deploy and the newest Nuitka, 4.3, which uv
chose for `nuitka>=4.1.1`.
**Outcome:** failed. The app exited with an access violation while building the main
window ("Nuitka: A segmentation fault has occurred"). faulthandler pointed into
`caddcalc.core.expr.render_symbolic` during the first calculation, and gdb showed the fault
inside Nuitka-compiled code, reading a bad free-list pointer. It crashed the same way with
MinGW gcc 15.2 and with Zig 0.16, with uv's CPython 3.12 and python.org's CPython 3.14, and
with LTO off. The pre-branding `app.py` crashed too, so it wasn't the new code. Small
scripts running the same calculation inside a Qt signal didn't crash; creating
`MainWindow` right after `QApplication` did. Nuitka 4.1.1, the version pyside6-deploy
6.12's `default.spec` names, builds a working app from the same code.
**Instead:** pin `nuitka==4.1.1` in the `build` dependency group, and move the pin with
pyside6-deploy's `default.spec` when PySide6 is upgraded. Not reported upstream yet; the
smallest reproduction so far is "create a QApplication, then `MainWindow()`".

## 2026-10-17: A MinGW header "missing" when building inside the Claude desktop app
**Tried:** the first pyside6-deploy build, started from a Claude Code session in the
desktop app.
**Outcome:** failed with `propsys.h: fatal error: structuredquerycondition.h: No such file
or directory`, although the file was there.
**Why:** the desktop app is a packaged (MSIX) app, so `%LOCALAPPDATA%` was redirected to
`…\Packages\Claude_<id>\LocalCache\Local\`, and Nuitka's cache with it. gcc's
unnormalized include path (`…\bin\..\lib\gcc\…\..\..\..\..\x86_64-w64-mingw32\include\`)
plus that header's long name passed Windows' 260-character limit. Shorter header names
still fit, which made it look like a broken download.
**Instead:** set `NUITKA_CACHE_DIR` to a short folder, e.g. `C:\Users\<you>\.cache\nuitka`.
Builds from a normal terminal aren't affected.

## 2026-10-17: Smoke-test screenshots with boxes instead of text
**Tried:** checking the packaged build with `--smoke-test`, which saves a screenshot.
**Outcome:** fixed the same day. Every character in the screenshot was a box, and the
window had no DPI scaling.
**Why:** the build script's icon helper set `QT_QPA_PLATFORM=offscreen` in its own
environment to draw icons without a display, and the app under test inherited it. On
Windows, Qt's offscreen platform has no fonts. The packaged app itself was fine.
**Instead:** `packaging/icons.py` uses the offscreen platform only on Linux without a
display, and only while it creates its QGuiApplication.

## 2026-10-16: Wrong claim that the Handbook doesn't scale by A/90

**Tried:** documenting (KI-012 and the course method note) that scaling 0.64T + 1.57R by A/90
was the prototype's own extension, after checking only the Eq. (33) page.
**Outcome:** reverted the same day. The review session pointed to MH29 p. 1351 ("Angle of Bend
Other Than 90 Degrees"), and reading that page confirmed the rule. (It's p. 1421 in the 31st
edition.)
**Instead / next time:** search the whole section, not just the equation's page, before
writing that a source doesn't support something.

## 2026-10-16: Reading formulas out of the legacy `.xls` files

**Tried:** extracting cell formulas from `Lesson 2 …xls` and `Lesson 4 …xls` (Excel 97
BIFF format) with the Python library `xlrd`.
**Outcome:** failed for formulas. `xlrd` only returns cached *values* from BIFF files, not formula text.
**Instead:** opened the files through Excel's COM automation, **read-only with macros
force-disabled** (`AutomationSecurity = 3`), and read `Range.Formula`. The `.xlsm` rough
drafts are Open XML, so `openpyxl` reads their formulas directly. VBA modules were
read with `oletools`' `olevba`, which never runs macros. Results are in
[legacy-workbooks.md](legacy-workbooks.md).

## 2026-10-16: First reconstruction of formulas from values only

**Tried:** reverse-engineering the lesson formulas from the cached values before the real
formulas were available.
**Outcome:** superseded. The guesses (e.g. `BA = 1.57R + 0.64T`, `FPD = FVD − (R+T) + BA/2`)
turned out right, but guesses are not evidence.
**Instead:** always read the actual formula text. Treat value-matching as a check only.

## 2024 (prototype era): Excel/VBA "CADD Calculator Rough Draft" V1 and V2

**Tried:** building the app inside Excel. It had a VBA startup form, a dashboard sheet
with shape buttons, a basic arithmetic calculator form (adapted from a third-party
example), and an "Admin" reset table that restored input cells.
**Outcome:** abandoned for a standalone app (ADR-0002).
**Why:** Windows and Excel only. Formulas tied to cell addresses. No tests, no version
control, macro security prompts, and it can't be distributed as open source with
third-party assets inside.
**Kept:** the formulas (as `course` methods), the "reset to defaults" idea, and the
splash/about/dashboard UX ideas.
