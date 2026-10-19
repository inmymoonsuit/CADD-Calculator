# ADR-0023: The layout contract

* **Status:** **Accepted; not built.** On 2026-10-19 the maintainer was asked "Approve all
  eight as UI/UX recommends?" and replied "Approved". That covers C1–C8, as below.
  * One finding came after the approval, in C7's build detail: Selawik as published
    can't be used unchanged (§7.1). The maintainer approved the modified, renamed build
    on 2026-10-19: "Approve the font".
* **Asked for by the maintainer:** "we are setting ourselves up for a pattern of constantly
  trying to hack and patch our UI to accommodate outliers … We need to establish a target
  size and resolution, establish correct scrolling, text-wrapping, scaling, accessibility
  behavior, etc. and use a principled, formalized design approach to this."
* **Supersedes** parts of ADR-0021 and ADR-0017; see "What this supersedes", which lists
  each section with the note it gets.
* **Keeps:**
  * from ADR-0021: the text units (§1), following Windows' text size (§2), fitting to the
    screen and centring (§3 items 2–6), the page cap and placement (§4), the space beside
    the page (§5), the minimum window and rule C (§6), and the KI-023 rules (§7)
  * from ADR-0016: the spacing scale and the palette
  * from ADR-0017: the result fields, and "results are never obscured"
* **Measured at:** PR #1's head (8410aa8: main plus the Geometry and Conversions
  families).
  * Natively on Windows 11, Qt 6.12, Segoe UI 9 pt (ch = 5.5 px, one line = 16 px; Qt
    reports 15.94), on the primary 1920 × 1080 screen at 100%.
  * Every figure is measured unless it says "calculated".
  * The method is written out under "How the figures were measured", and its script
    is given there for the builder to commit.

## Context

The window's launch height was derived from its content. As pages were added, it went
720 → 736 → 738 → (PR #1) 1014 needed, capped at 969 by the screen. Each new tall page
reopened the rule.

The fix reverses the dependency: **the screens set the size, and pages are designed to that
size or declared long.**

## Decisions by the maintainer

| # | Decided (2026-10-19, "Approved") | Alternatives, kept for the record |
|---|---|---|
| C1 | **The target height is 46 lines** (`launch_lines`; 736 px at 9 pt). It fits R1 and R2 without fitting down. | T-B, 40 lines (640 px), fits R1–R3 (46.0% of desktops), but ten pages would be over budget. T-C, 37 lines (592 px), fits R1–R4 (50.7%), but seventeen would be over. |
| C2 | **The Length converter and the right triangle are declared long** (`Calculator.long_page`). **The segment's A1 and A2 share one input row.** | Length: split it into two calculators (about 702 px each, calculated; changes the CLI and JSON ids), or put each fraction with its error in one row (about 858, calculated; against ADR-0017's one value per field). Right triangle: two-column results (C3). Segment: declare it long for 2 px, or shrink every form's row gap from 6 to 5 px. |
| C3 | **No two-column results yet.** Keep them in reserve in case long pages multiply. | Two columns when the page is wide: Length about 702, right triangle about 630 (calculated). This costs the single decimal-aligned column, labels elide more, and reading order runs across columns. |
| C4 | **A long page doesn't auto-scroll on compute, and nothing is sticky.** | Scroll the first result into view once when the page opens (it is already in view at the target). A sticky results header with Copy all (Ctrl+Shift+C already copies everything). |
| C5 | **Field and button heights stay in pixels** (40 and 28), as named exceptions. | In text units, at Linux's 14 px line, the field would drop to 35 px and the button to about 24.5, and every platform's look would change. |
| C6 | **An AST check refuses pixel literals** in `gui/` size calls, with a named allowlist. | Review alone. |
| C7 | **Selawik is vendored as a test-only font,** so CI measures text as Windows does. See §7.1 for the build detail that needs confirming. | No test font: the budget would be checked natively only. |
| C8 | **No in-app text size yet.** It needs a settings store, which ADR-0013 doesn't have. | A Preferences item for text size. |

## Decision

### 1. Reference displays and the target size (C1)

**What people's desktops show:**
* **StatCounter, desktop, worldwide, September 2026:** 1920 × 1080 28.07%, 1536 × 864
  10.00%, 1366 × 768 7.95%, 1280 × 720 4.71%, 2560 × 1440 3.95%.
  * StatCounter measures what browsers report, which is the logical size. So 1536 × 864
    is a 1920 × 1080 screen at 125%, and 1280 × 720 is mostly 1080p at 150%.
* **Valve's Steam Hardware Survey, August 2026** (physical resolution, gamers' machines,
  so context only): 1920 × 1080 about 50.5%, 2560 × 1440 about 21.9%, 4K about 5%.
* **GNOME's HIG** names 1024 × 600 as the smallest desktop every app should support.

**The reference displays.** "Largest content" is the work area less the 48 px taskbar,
the window frame (31 + 8 px) and `screen_margin` (16) on each side, all measured.

| Ref | Logical screen | Typical hardware | Share (StatCounter) | Largest content |
|---|---|---|---|---|
| R1 | 1920 × 1080 | 1080p at 100% | 28.07% | 1872 × 961 |
| R2 | 1536 × 864 | 1080p at 125% (laptops) | 10.00% | 1488 × 745 |
| R3 | 1366 × 768 | 1366 × 768 at 100% | 7.95% | 1318 × 649 |
| R4 | 1280 × 720 | 1080p at 150%, or 720p | 4.71% | 1232 × 601 |
| R5 | 1024 × 600 | the GNOME floor | — | 976 × 481 |
| (larger) | 2560 × 1440 and up | — | 3.95% | fits everything below |

**The rule:**
* **The target size** is a fixed content size in text units:
  * width: `ceil(list_width_chars · ch + handle + page_max_chars · ch)`, which is 1100 at
    9 pt
  * height: `ceil(launch_lines · line spacing)`, which is 736 at 9 pt, menu and status
    bars included, as now
* **It is never derived from content.** The window opens at the target size, fitted down
  where the screen is smaller (ADR-0021 §3, items 2–6).
* **Decided: `launch_lines = 46`.** That fits R1 and R2 (38.1% of desktops, and every
  screen at or above 1080p at 125%), and it is the composition the maintainer approved.
  Smaller screens get the same composition fitted down, and the page scrolls (rule C).

### 2. The order of adaptation, as space shrinks

At any window size, text scale and language, in this order:

1. **Wrap:** prose wraps (descriptions, notes, the disclaimer, help).
2. **Reflow or stack:** paired controls stack (`ReflowLayout`, as the method row, the
   settings pairs and now paired input rows do); form labels go above their fields
   (`WrapLongRows`).
3. **Elide only what's non-essential, always with the whole text in a tooltip:** the
   calculator list's names, and a result field's label (ADR-0017).
4. **Scroll vertically,** with one scroll bar for the page (rule C) and the document shown
   in full.
5. **Never scroll horizontally.** Every page's least width is within the window's least
   width.

**Never clipped or elided** (the tests assert these whole):
* result values, units and symbols; the copy buttons
* input fields' contents and their labels (labels may wrap)
* errors and input messages; note leads (the first line of every note)
* the disclaimer
* method names and method status
* the page title and the Units box
* menu items, and dialog text and buttons
* focus indicators

### 3. The page budget, enforced in review, not in the window (C2, C3, C4)

* **The budget:** at the target size (1100 × 736 at 9 pt, 100% text, English), every
  built-in page that isn't declared long fits without scrolling, with each of its methods
  and its document at its least.
  * "Fits" means `pages.fit_height(page, width, document)` plus the window's bars is at
    most the target height, measured as `_tallest_calculator_page` does today (two layout
    passes, `pages.lay_out`).
  * It is checked for every built-in calculator and each of its methods.
* **Over budget, there are two choices, and review decides between them:**
  1. **Redesign** the page to fit.
  2. **Declare it long:** `Calculator.long_page: ClassVar[bool] = False`, set True with a
     one-line comment giving the reason. Setting it counts as a design change, and the
     review checklist names it.
* **Decided (C2):**
  * **Length converter:** long. It's a reference table, and scrolling one is natural. Its
    outputs are unchanged.
  * **Right triangle:** long. At the target size every row but the last shows.
  * **Segment:** A1 and A2 share one input row (slice 1). That saves one 32 px input row
    with each method: K-factor goes from 738 to about 706 (calculated), and Fixed K-factor
    from 706 to about 674 (calculated).
* **The budget test** (slice 2) lists every page's need in px and in lines. It fails:
  * for a page that is over budget and not declared long
  * for a page that is declared long but now fits, so the flag can't go stale (every
    method of a long page must be over)
  * for a calculator whose methods differ, with some fitting and some scrolling. A scroll
    bar that comes and goes narrows the page by 12 px and moves the Units box (the labels
    review's M1), so all of a calculator's methods must fit, or all must scroll.
* **What a long page does:**
  * It scrolls as a whole (rule C). The results panel stays directly under the inputs,
    so at the target size a long page shows its inputs and at least its first result.
    That's the long page's real budget, and the test asserts it.
  * **Decided (C4): no auto-scroll on compute.** Results update as the user types, and
    scrolling under someone who is typing takes away their focus context.
  * **Decided (C4): nothing sticky.**
  * Tab still scrolls each focused field into view (2.4.11).
* **Decided (C3): no two-column results** for now.

**The budget, measured.** Each figure is the least window height (client area, menu and
status bars included) at which the page fits, at 1100 px wide and 9 pt. Lines are the
content height (the window less 54 px of bars) ÷ 16.

| Page (method) | Outputs / inputs | Need | Lines | vs the 736 target | Contract |
|---|---|---|---|---|---|
| Length converter | 12 / 1 | 1014 | 60.0 | +278 | long |
| Right triangle (all four methods) | 7 / 2 | 786 | 45.75 | +50 | long |
| Segment (K-factor) | 3 / 6 | 738 | 42.75 | +2 | paired row: about 706, calculated |
| Cone (both methods) | 4 / 4 | 726 | 42.0 | −10 | fits |
| Triangle | 5 / 3 | 714 | 41.25 | −22 | fits |
| Segment (Fixed K-factor) | 3 / 5 | 706 | 40.75 | −30 | paired row: about 674, calculated |
| Regular polygon (all three) | 5 / 2 | 682 | 39.25 | −54 | fits |
| Bend allowance (K-factor) | 3 / 4 | 674 | 38.75 | −62 | fits |
| Area converter | 5 / 1 | 650 | 37.25 | −86 | fits |
| Bend allowance (Fixed K-factor) | 3 / 3 | 642 | 36.75 | −94 | fits |
| Arc and sector | 4 / 2 | 630 | 36.0 | −106 | fits |
| Circle (both), Stress converter | 4 / 1 | 598 | 34.0 | −138 | fits |
| Rectangle | 3 / 2 | 578 | 32.75 | −158 | fits |
| Angle converter | 3 / 1 | 546 | 30.75 | −190 | fits |
| V-die (both) | 1 / 1–2 | 474–506 | 26.25–28.25 | −230 or less | fits |

* **Row costs:** a result row is 52 px (a 46 px field plus the 6 px gap). An input row is
  32 px (a 26 px field plus the form's 6 px).
* **At the target size,** the Length converter shows its input and its first 9 rows (in
  through N32); E32, N64 and E64 scroll.
* **The cone is the tightest fit,** at 10 px under. Its margin is the first thing to
  watch when the cone page changes.

### 4. Scaling (C8)

* **Display scale, 100–200%:** Qt lays out in logical pixels, and points map to logical
  pixels, so every size is the same at every scale. Only the fit to the screen changes
  (§1). Lines are whole device pixels (ADR-0016).
* **Text scale, 100–200%, on Windows:** the app reads `TextScaleFactor` at startup
  (ADR-0021 §2).
  * Every text-unit size grows with it, the target size included: 1647 × 1104 px at 150%
    and 2198 × 1472 at 200% (measured), fitted to the screen.
  * **Every page needs fewer lines at 150% and 200% than at 100%,** because the pixel
    parts (field floors, gaps, borders) don't grow. Length needs 60.0, 41.9 and 34.5
    lines; the right triangle 45.8, 32.8 and 27.2. Every page fits 46 lines at 150% and
    200% (see Measurements).
  * So **100% text is the binding case,** and the budget is checked there only.
  * At larger text the screen is the limit. On R1 the window fits down to 961 px, so the
    Length converter scrolls at 150% (it needs 1068) and at 200% (1173). Vertical
    scrolling with the §2 invariants is allowed.
* **The pixel exceptions don't scale with text, on purpose (C5):** click targets (the
  28 px button and the 40 px field floor) and device-pixel lines. A field still grows
  with its text, because its height is the larger of its floor and its content.
* **macOS and Linux** have no text-scale setting to read. The app uses the platform's
  default UI font size, which already reflects the user's setting: macOS's text size
  options, and GNOME's text scaling factor, which changes the font DPI that Qt reads on
  X11. Wayland is to be confirmed by hand, in KI-020. Display scaling is Qt's.
* **Decided (C8): no in-app text size** for now.

### 5. Accessibility targets

| Criterion | Target, and how it's met |
|---|---|
| WCAG 1.4.4 Resize Text (AA) | Text to 200% (Windows text size, or a larger platform font) with no loss of content or function. Pages scroll vertically, and the §2 never-clip list holds. Tested at 200%. |
| 1.4.10 Reflow (AA) | Applied to desktop software as WCAG2ICT does: at the window's least width, and at 200% text, no content needs scrolling in two directions. Horizontal scrolling is never used (§2). |
| 1.4.3 Contrast (AA) and 1.4.11 Non-text Contrast (AA) | Already enforced by the palette tests: 4.5:1 for text and 3:1 for non-text, including the focus ring and secondary text (ADR-0016, 0017). |
| 1.4.12 Text Spacing (AA) | Not user-adjustable in a Qt desktop app, so a platform matter under WCAG2ICT. The layout is checked at the en_XA expansion instead (+40% length), which is a stricter test of the same failure, clipped text. |
| 2.1.1 Keyboard (A) | Every control can be reached and operated by keyboard (Tab, Space, Enter, the Menu key; ADR-0017 §5). |
| 2.4.3 Focus Order (A) | Down the page, as `_chain_tabs` does, and A1 before A2 in a paired row. The test walks it on every page. |
| 2.4.7 Focus Visible (AA) | The result fields' ring, the outlined inputs' ring, and native focus elsewhere. The copy button shows focus once (k4 M2). |
| 2.4.11 Focus Not Obscured (Minimum) (AA, new in 2.2) | Tab scrolls the page so the focused widget, ring included, is in view (k3b D). Tested at every matrix point. |
| 2.5.8 Target Size (Minimum) (AA, new in 2.2) | Every pointer target is at least 24 × 24 px. The copy button is 28; the token check refuses smaller. |
| 4.1.2 Name, Role, Value (A) | Every control has an accessible name: fields read "Bend allowance, BA: 0.3119 inches", and buttons "Copy Bend allowance" (ADR-0017 §5). A paired row's fields keep their own names ("Bend angle at end 1, A1"). The test asserts names on every page. |
| Windows contrast themes | Qt 6.12 exposes the setting: `QStyleHints.accessibility().contrastPreference()` (measured: available, `NoPreference` here). Under `HighContrast`, use the system palette for text, background, focus and outlines in place of our roles, and keep outline widths and dashes so they read without colour. Checked natively by hand, in KI-020. |
| Reduced motion | Qt 6.12 exposes `motionPreference()` (measured: available). Under `ReducedMotion`, turn off Qt's UI effects (tooltip and menu animation). The app's own "copied" check doesn't move, so it stays. |
| Platform guidance | Fluent: 40 × 40 epx standard and 32 × 32 compact targets, so our 28 px icon button inside a 40 px field matches the compact density. Apple's HIG gives no macOS minimum (44 pt is for touch). GNOME HIG: support 1024 × 600 desktops (R5), which our least window, about 570 × 175, does. |

### 6. Size tokens, in one table, and a check (C5, C6)

| Token | Value | Unit | Why |
|---|---|---|---|
| `list_width_chars` | 51 | ch | the list at launch (280 px at 9 pt) |
| `list_min_chars` | 24 | ch | the list never collapses (approved) |
| `page_max_chars` | 148 | ch | the page's cap, today's default width (814 px) |
| `panel_max_chars` | 148 | ch | the results panel fills the page |
| `launch_lines` | 46 | lines | the target height (C1); never raised by content |
| `document_min_lines` | 6 | lines | was `document_min_height = 96` px: the Notes heading and a note's lead |
| `choice_min_chars` | 24 | ch | was `CHOICE_CHARACTERS` in code |
| `method_min_chars` | measured | ch | the longest method name (ADR-0021 §7) |
| `Calculator.long_page` | per calculator | flag | §3, reviewed |
| **Pixel exceptions** (they don't scale with text, by design) | | | |
| `screen_margin` | 16 | px | distance from the screen's work area: screen geometry, not text |
| `result_field.min_height`, `button_size`, `icon_size` | 40, 28, 16 | px | click targets (2.5.8, Fluent) and icon art (C5) |
| `focus_width`, `focus_gap`, `border_width`, outline `width` | 2, 1, 1, 2 | px | whole device-pixel lines (ADR-0016) |
| `padding`, `gap`, `stack_gap`, `panel_inset` | ADR-0017's | px | ADR-0016's spacing scale (2–32) |
| `options_gap` | 16 | px | was `options.addSpacing(16)` in `window.py`; on the spacing scale |
| `document_icon_px` | 32 | px | was `ICON_PX`: the icon rendered into the document |

* **Decided (C5):** the result fields' heights stay in pixels.
* **Decided (C6), the check:** an AST test over `src/caddcalc/gui/*.py`.
  * It refuses an int or float literal other than 0 as an argument to
    `setFixedSize/Width/Height`, `setMinimumSize/Width/Height`,
    `setMaximumSize/Width/Height`, `resize`, `QSize`, `QSizeF`, `setContentsMargins`,
    `setSpacing`, `addSpacing`, `setMinimumContentsLength` and `setIconSize`.
  * It accepts names, attribute access (tokens) and expressions built from them.
  * It also accepts a literal that multiplies something that isn't a literal
    (`2 * ring`, `2 * view.frameWidth()`). That's a count, such as two sides, not a
    size.
  * Any other literal is allowed only through an allowlist in the test: each entry names
    a `(file, function, call)` and gives its reason.
  * Measured with a prototype of the check over every `gui/*.py` on 8410aa8, `welcome*.py`
    included:
    * It flags three calls: `options.addSpacing(16)` (`window.py:483`),
      `setMinimumHeight(round(tokens.min_height + 2 * ring))` (`result_fields.py:265`)
      and `setMinimumWidth(view.sizeHintForColumn(0) + 2 * view.frameWidth())`
      (`window.py:797`).
    * The last two are the multiplier case above, so with that rule only
      `addSpacing(16)` remains.
    * `ICON_PX` and `CHOICE_CHARACTERS` pass as names, and move to tokens in slice 3.

### 7. The test matrix (C7)

* **Points:** every built-in page, with each method, × window {least, target (fitted),
  large 1920 × 1032} × text {100, 150, 200%} × {en, en_XA}.
* **Invariants, at every point:**
  1. Nothing clips: the suite's `_clipped`, plus the §2 never-clip list.
  2. No horizontal scrolling.
  3. Every control can be reached by scrolling.
  4. Tabbing keeps focus visible and in view (2.4.7 and 2.4.11).
  5. Accessible names are present (4.1.2).
* **The budget (§3)** is checked once: target size, 100% text, English, built-ins.
* **What runs where:**
  * **Offscreen in CI (all three OSes):** every invariant at every point, with the test
    font (§7.1). The budget too, on the terms in "What the build must reproduce".
  * **Natively by hand, in KI-020:** contrast themes, reduced motion, real keyboard
    focus, the Menu key and Shift+F10, real screen readers, real monitors at
    125/150/200%, Wayland's text scaling, and the native figures in the Measurements
    tables.

#### 7.1 The test font: what Selawik is, and what it needs (C7)

* **Upstream:** https://github.com/microsoft/Selawik, at commit
  `89362e84731d1f5777fa078fd4d5ebbd339e4378` (2023-06-05, the last commit; the sources
  date from 2015-12-08).
  * Font version 1.001 (`versionMajor` 1, `versionMinor` 1 in the UFO).
  * License: SIL Open Font License 1.1 (`LICENSE.txt`), with the Reserved Font Name
    "Selawik".
  * The README calls it "an open source replacement for Segoe UI".
* **What it matches (checked 2026-10-19):** the advance widths. In the UFO, `a` is 1042,
  `n` 1159, `H` 1454 and `0` 1104 units per 2048, identical to Segoe UI's, read natively
  from `segoeui.ttf`.
* **Why it can't be used as published:**
  * **No font binaries.** The repo holds sources only: UFOs for Light, Regular and Bold,
    and a `.glyphs` file. It has no releases, and it isn't on npm.
  * **Different vertical metrics.** The UFO's ascender and descender are 1491 and −431,
    and it sets no hhea or OS/2 values. Segoe UI's are 2210 and 514, with no line gap
    (2724 units: 16 px per line at 9 pt). Compiled as published, Selawik's line spacing
    would be about 14.4 px at 9 pt, using a compiler's default 1.2 em. Every text-unit
    height would then differ from Windows'.
  * **Average width.** `ch` comes from OS/2 `xAvgCharWidth`, which Segoe UI sets to 940
    (5.5 px at 9 pt). A compiler computes its own value from Selawik's glyph set, so it
    must be set to match.
* **The build, which needs the maintainer's yes:**
  * Compile Regular and Bold from the pinned UFOs with fontmake.
  * Set hhea ascender/descender/lineGap to 2210/−514/0, OS/2 winAscent/winDescent to
    2210/514, typo ascender/descender/lineGap to 2210/−514/0 with USE_TYPO_METRICS on,
    and `xAvgCharWidth` to 940.
  * This is a Modified Version under the OFL. OFL §3 then forbids the Reserved Font
    Name, so it ships as **"CaddCalc Layout Test"**, with Selawik's copyright line,
    `OFL.txt`, and a name-table description that says it is modified from Selawik
    1.001.
  * It goes in `tests/data/fonts/`, never in the wheel. `THIRD_PARTY_NOTICES.md` gets an
    entry like VT323's.
  * **The alternative** is no test font: the budget is checked natively only, and the
    invariants run offscreen with each OS's fallback fonts.
* **Known limits of the test font:**
  * Selawik has no Semibold, so the 16 pt 600-weight page title is measured in Bold,
    which is slightly wider.
  * Its glyph coverage of ′ ″ ≈ ² − · ° has to be checked in slice 4; any missing glyph
    falls back to another font, on that row only.
  * The Work section's Consolas is replaced by the platform's monospace. The document is
    at its least height in the budget, so this doesn't change any need.
  * Kerning differs (an open upstream issue), which changes only how a string fits
    within a line, never the line height.

### 8. Audit: what each special case becomes

| Today | Where | Becomes |
|---|---|---|
| The launch height grows to the tallest built-in page (`_tallest_calculator_page`, `launch_pages`, `launch_size(..., pages)`), with its isolation boundaries and warnings | `window.py`, `window_layout.py` | **Removed** (slice 2). The launch height is `launch_lines` only. The page measure moves into the budget test's helper (§3), outside the app. |
| `test_the_launch_height_covers_the_tallest_calculator_page`, `test_no_calculator_page_scrolls_at_the_launch_size`, `test_each_calculator_page_is_measured_at_its_shown_height`, `test_a_page_that_fails_to_measure_leaves_the_window_working`, `test_a_method_that_fails_to_measure_leaves_out_its_own_page_only`, `test_the_measure_opens_each_further_method_once_directly` | `test_window_layout.py` | Replaced by the budget test (slice 2). `test_no_plugin_page_opens_until_it_is_chosen` stays: it's cheap, and still true. |
| PR #1's interim fixed 738 px and its test-local list of long pages | PR #1 | Replaced by `launch_lines` and `Calculator.long_page` (slice 2). |
| `test_the_segment_page_fits_1100_by_720`, and pixel window sizes in tests (1100 × 720, 1100 × 420, 1100 × 800, 2400 × 800) | `test_window_layout.py`, `test_result_fields.py`, `test_translated_gui.py` | Matrix points named by role (least, target, large), computed from the tokens (slice 5). |
| `launch_size(...)` arithmetic tests, `chars(148, 5.5) == 814`, `LEAST = Size(577, 175)`, the `fit_window` work-area cases | `test_window_layout.py` | Kept as unit tests of the arithmetic, with the values derived from the tokens rather than typed in. |
| `_least_page_height`: the title, the method row and one field | `window.py` | Kept, as the contract's "least page" (§2). |
| `CHOICE_CHARACTERS = 24` | `window.py` | Token `choice_min_chars` (slice 3). |
| `ICON_PX = 32` | `window.py` | Token `document_icon_px`, a named pixel exception (slice 3). |
| `options.addSpacing(16)` | `window.py` | Token `options_gap` (slice 3). |
| `document_min_height = 96` px | `ui_style.toml` `[result_field]` | `document_min_lines = 6` in `[layout]` (slice 3): 96 px at 9 pt, 84 at Linux's 14 px line. |
| `method_status.setFixedWidth(_widest_status)`, and the method box's `setMinimumContentsLength(_method_min_chars())` | `window.py` | Kept: measured from content, not typed in, which is the contract's preferred form. |
| `CH_FALLBACK_EM = 0.45` | `window_layout.py` | Kept, as a documented constant of `ch`. |
| ADR-0017's pixel tokens (fields, rings, gaps) | `ui_style.toml` | Kept, as the named pixel exceptions (§6). |
| `_flush` and the decimal alignment's pads | `result_fields.py` | Kept; they're measured from the font. |

## The build plan

**Start after PR #1 merges.** PR #1 keeps its interim fixed 738 px and its test-local list
of long pages (Length and the right triangle). Slice 2 replaces both.

**What that ordering needs:**
* **PR #1's window code must hold 738 itself, not just its tests.** If the test-local
  list only skips assertions, the window still measures Length and opens at 969. The
  same two pages must be left out of `_tallest_calculator_page` (or the height pinned),
  so that 738 is what users get.
* **PR #1's list names exactly `conversions.length` and `geometry.right_triangle`,** so
  that slice 2 moves it to `long_page` one for one.
* **Slice 1 lands before slice 2, or in the same PR.** At a fixed 736, the segment's
  K-factor page (738) would scroll by 2 px. Its scroll bar would narrow the page by 12 px
  and move the Units box between methods, bringing back the labels review's M1.
* **Slice 4 waits on the maintainer's yes to §7.1** (a modified, renamed Selawik).
  Slices 1–3 and 6 don't.

**Order:** 1 → 2 → {3, 4} → 5 → 6. Slices 3 and 4 are independent of each other. Slice
6 needs only slice 2. Each slice is one PR. Each one updates the CHANGELOG and adds an
"as built" amendment here with its measured figures.

### Slice 1: paired input rows, and the segment's A1 and A2

* **What it changes:**
  * `core/spec.py`: `Param` gets `row: str = ""`. Params with the same non-empty `row`
    share one form row, in declaration order. The row's label is a translatable string
    that the calculator declares: `Calculator.rows: ClassVar[Mapping[str, str]]`, for
    example `{"bend_angles": N_("Bend angles")}`. The data stays generic, with no
    per-calculator GUI code (ADR-0017 §6).
  * `window.py` `_build_form`: a row with two or more params becomes one form row,
    labelled with the row's label. Its field is a `ReflowLayout` of sub-fields, each with
    a short label ("End 1 (A1)"), its edit and its unit. Side by side while they fit,
    stacked when they don't (§2).
  * Each edit keeps its own accessible name and tooltip, from the `Param` as now.
    `_chain_tabs` orders A1 before A2.
  * The segment calculator's `bend_angle_1` and `bend_angle_2` get `row="bend_angles"`,
    in both methods.
  * The CLI, JSON, Copy all and the saved-file keys are unchanged: it's form layout only.
* **Tests:**
  * The segment page has one form row fewer with both methods, and its two angle edits
    share a row at the target width.
  * At the least width, and in en_XA, the pair stacks and nothing clips (`_clipped`).
  * Tab goes A1 → A2. Each edit's accessible name and tooltip are as before.
  * A `row` naming a key that isn't in `Calculator.rows` fails the calculator's
    validation, at the same point other declaration errors fail today.
* **The figures it must reproduce:**
  * **Native only:** segment K-factor about 706 and Fixed K-factor about 674 at 1100 px
    and 9 pt (calculated; each must be ≤ 736, and they're recorded as measured).
  * **Offscreen:** the row-count and stacking assertions above, which don't depend on
    the font.

### Slice 2: the fixed launch, `long_page`, and the budget test

* **What it changes:**
  * `window_layout.launch_size` drops its `pages` argument: the height is
    `ceil(launch_lines · line)`.
  * `MainWindow`: `_tallest_calculator_page`, `launch_pages` and their isolation
    boundaries go. Building the window no longer opens every built-in page, so the
    measure's startup cost goes too. ADR-0021's amendments timed the build at 777–814 ms
    with every method measured; slice 2 records the new time, natively.
  * `core/calculator.py`: `long_page: ClassVar[bool] = False`. Set True, with a one-line
    reason, on `conversions.length` ("a reference table of 12 rows") and
    `geometry.right_triangle` ("seven results").
  * The page measure moves to `tests/layout_budget.py`, a helper that both the test and
    the script use. It does what `_tallest_calculator_page` does (select, then for each
    further method set the index under a `QSignalBlocker` and call `_on_method_changed`;
    `lay_out`; `fit_height` + bars), returning one row per page and method.
  * `scripts/measure_page_needs.py` (the script under "How the figures were measured")
    is committed.
  * ADR-0021 and ADR-0017 get the notes listed under "What this supersedes". KI-024 is
    closed.
* **Tests:**
  * `test_the_launch_height_is_launch_lines_only`: at any font, the launch height is
    `ceil(46 · line)`, whatever the pages.
  * `test_every_page_is_within_the_budget_or_declared_long`: the §3 rules, all three of
    them.
  * `test_a_long_page_shows_its_inputs_and_first_result`: at the target size, every
    input and the first result field are wholly in the viewport, with no scrolling.
  * `test_changing_method_never_moves_the_units_box`: for every calculator at the target
    size, the Units box's x is the same with each method.
  * `test_no_plugin_page_opens_until_it_is_chosen` (kept).
* **The figures it must reproduce:**
  * **Native only, by UI/UX's review:**
    * the window launches at 1100 × 736 on R1 at 100%
    * every need in §3's table, within 2 px; any wider difference is reported, not
      absorbed
    * Length shows 9 rows at the target size
  * **Offscreen, the test passes on its own figures:**
    * Before slice 4 lands, CI's needs differ from Windows'. The fallback fonts differ
      (offscreen Windows measured 1524 px for a 661 px line) and so does the style
      (Fusion offscreen, windows11 natively).
    * So until then the budget test runs only where `QT_QPA_PLATFORM` is the native
      platform, and is skipped offscreen, with that reason given.
    * The other four tests run everywhere.

### Slice 3: the tokens, and the pixel-literal check

* **What it changes:**
  * `ui_style.toml` and `ui_style.py`:
    * `[layout]` gains `document_min_lines = 6` and `choice_min_chars = 24`, and drops
      `document_min_height` from `[result_field]`.
    * New pixel tokens `options_gap = 16` and `document_icon_px = 32`, in `[layout]`'s
      pixel section beside `screen_margin`.
  * `window.py`: `CHOICE_CHARACTERS`, `ICON_PX` and `addSpacing(16)` read the tokens. The
    document's least height is `ceil(document_min_lines · line)`.
  * `tests/test_no_pixel_literals.py`: the C6 check (§6), with its allowlist.
* **Tests:**
  * The check passes on the tree, and fails on a fixture source containing
    `w.setFixedWidth(120)`, `QSize(10, 10)`, `layout.addSpacing(16)` and
    `setMinimumHeight(tokens.x + 4)`.
  * It passes `setFixedWidth(tokens.x)`, `setContentsMargins(0, 0, 0, 0)`,
    `setMinimumHeight(tokens.x + 2 * ring)` and an allowlisted call.
  * `ui_style`'s schema test covers the new tokens and rejects the removed one.
* **The figures it must reproduce:**
  * **Offscreen:** the document's least height is 96 px at a 16 px line (asserted with a
    font whose line spacing is 16, or computed from the platform's line), and every
    existing GUI test still passes.
  * **Native only:** no page's need in §3 changes.

### Slice 4: the test font (C7, after the maintainer confirms §7.1)

* **What it changes:**
  * `scripts/build_test_font.py`:
    * fetches Selawik at the pinned commit (or reads a local checkout passed as an
      argument)
    * builds Regular and Bold with fontmake
    * sets the metrics in §7.1 with fontTools, renames the family to "CaddCalc Layout
      Test", and writes the TTFs and their SHA-256
    * fontmake and fontTools are dev-only, used for this script only, so they aren't
      runtime dependencies
  * `tests/data/fonts/caddcalc-layout-test/`: the two TTFs, `OFL.txt` and a `SOURCE.md`
    (upstream, commit, version, the modifications, the SHA-256 of each file).
  * `THIRD_PARTY_NOTICES.md` gets an entry.
  * `pyproject.toml` / `hatch_build.py`: confirm `tests/` stays out of the wheel and the
    sdist's payload as now. A test asserts the font isn't in the built wheel.
  * `tests/conftest.py`:
    * In offscreen runs, a session fixture adds the font with
      `QFontDatabase.addApplicationFont` and sets it as the application font at 9 pt.
    * The fixture is used by the layout tests (`test_window_layout.py`, the budget and
      the matrix) and nothing else, so other GUI tests keep their current fonts.
* **Tests:**
  * With the test font at 9 pt: `averageCharWidth` is within 5.45–5.55 and
    `lineSpacing` within 15.9–16.1.
  * Glyph coverage of ′ ″ ≈ ² − · °, recorded. Any missing glyph is listed in
    `SOURCE.md`, and nothing fails on it.
  * The font file isn't in the wheel.
* **The figures it must reproduce:**
  * **Offscreen with the test font, on all three CI OSes:**
    * ch 5.5 and line 16 at 9 pt
    * the launch at 1100 × 736 (arithmetic from ch and line)
    * 1647 × 1104 at 150% and 2198 × 1472 at 200% (within 2 px, from the same
      arithmetic)
  * **Offscreen, measured and recorded but not asserted against the native table:** each
    page's need. Field heights and form gaps still come from Fusion, not windows11.
    * The budget test now runs offscreen too. It asserts the §3 rules on CI's own
      figures.
    * If CI's figures put a page on the other side of the 736 line from Windows (the
      cone, 10 px under natively, is the likely one), that is reported to UI/UX with
      the figures, and no `long_page` is set on CI's figures alone.
    * On `windows-latest`, also try the windows11 style offscreen. If its needs match
      §3 within 2 px, the budget asserts the native table there.
  * **Native only:** Selawik's advance widths against Segoe UI's, for the ASCII range
    and the symbols above. UI/UX checks this in review, since Segoe UI isn't in CI and
    its data isn't copied into the repo.

### Slice 5: the test matrix

* **What it changes:**
  * `tests/test_layout_matrix.py`: the §7 points × the five invariants, parametrized.
  * Windows are named by role, computed from the tokens and the least window: least,
    target fitted to a 1920 × 1032 work area, and large 1920 × 1032.
  * Text scale is set as the app font at 9 pt × the scale, the path ADR-0021 §2 takes.
  * The pixel window sizes in `test_result_fields.py`, `test_window_layout.py` and
    `test_translated_gui.py` move to these roles.
* **Tests:** the matrix itself.
  * It has about 25 page-methods × 3 × 3 × 2 = 450 points.
  * If it runs over 60 s on a CI OS, the 150% and 200% points go under a `layout_slow`
    marker that runs on one OS per job, with that reason given.
* **The figures it must reproduce:**
  * **Offscreen with the test font:** the invariants at every point.
  * Also: every page fits 46 lines at 150% and 200% (§4). CI asserts that on its own
    figures, because it's a ratio property that doesn't depend on the style's exact
    pixels.
  * **Native only:** the Measurements table at 150% and 200%, within 2 px, by UI/UX's
    review.

### Slice 6: contrast themes and reduced motion

* **What it changes:**
  * `app.py` / `palette`: read `QStyleHints.accessibility()` at startup and on change.
    * Under `HighContrast`, the result fields, outlines and focus ring take their
      colours from the system palette (`QPalette` roles), not our roles, and keep their
      widths and dash styles.
    * Under `ReducedMotion`, call `QApplication.setEffectEnabled` with False for
      `UI_AnimateMenu`, `UI_FadeMenu`, `UI_AnimateCombo`, `UI_AnimateTooltip` and
      `UI_FadeTooltip`.
  * KI-020's checklist gains the native checks (§7).
* **Tests (offscreen):**
  * Patch the accessibility hints to `HighContrast`: the roles resolve to the system
    palette's colours, and outline widths are unchanged.
  * Patch to `ReducedMotion`: the effects are disabled.
  * A change signal re-applies both.
* **The figures it must reproduce:** none offscreen beyond the above. **Native only:**
  Windows' contrast themes (Aquatic, Desert, Dusk, Night sky) and "Animation effects" off,
  by hand. Measured here: `SPI_GETHIGHCONTRAST` reads off, and both Qt hints are
  `NoPreference`.

## What the build must reproduce: native and offscreen

| Figure | Where it's checked |
|---|---|
| ch 5.5 px and line 16 px at 9 pt | natively (measured); offscreen with the test font (slice 4) |
| The launch at 1100 × 736; 1647 × 1104 at 150%; 2198 × 1472 at 200% | natively; offscreen with the test font, as arithmetic |
| Each page's need (§3 and Measurements) | natively only, within 2 px. CI records its own and asserts the §3 rules on them. |
| The over/under split at 736 | natively. CI's split is compared against it and differences are reported (slice 4). |
| Length shows 9 result rows at the target size | natively; CI asserts "its inputs and at least its first result" |
| Every page fits 46 lines at 150% and 200% | natively; offscreen as a property |
| Frame 31 + 8 px, taskbar 48 px, R1–R5 content sizes | natively only; in CI they're typed test data for the `fit_window` arithmetic |
| The least window, about 570 × 175 | natively only (it depends on the style) |
| Contrast and motion hints | natively only; CI patches them |

## How the figures were measured

This is the method behind every "need" in the tables, so the builder can reproduce it
without UI/UX's scratchpad. Commit it as `scripts/measure_page_needs.py` in slice 2.

* **Native and hidden:** `WA_DontShowOnScreen`, on the primary screen, with no keyboard
  focus taken.
* **At each page's launch width** (`launch_size().width`).
* **Each built-in calculator and each of its methods.** For each probe, resize the window
  to 2400 px tall, let it settle, then resize to the trial height and let it settle (350
  ms; with 80 ms it gave false highs, such as Length at 1276). The page "fits" when
  `page_scroll.verticalScrollBar().maximum() == 0`.
* **Bisect** between 300 and 2400 for the least height that fits. It was confirmed by
  hand for Length: it fits at 1014 and scrolls at 1013, with no hysteresis.
* **Bars** are the window height less the central widget's: 54 px at 9 pt.
* **Lines** are (need − bars) ÷ line spacing.
* **Text scale** is set directly, as the app font at 9 pt × the scale. Windows' setting
  isn't used, so the result doesn't depend on the machine (this one's `TextScaleFactor`
  is 125).
* **It agrees with the deterministic measure:** where both were taken, `fit_height` +
  bars matched the bisection (segment K-factor 738, cone 726). So the budget test uses
  `fit_height`, with no timing, and the script is an independent cross-check by resizing.

```python
"""Each built-in page's least fitting window height, in px and lines, at one text scale.

Native and hidden: run it on a desktop session, not offscreen, to reproduce ADR-0023's
tables. Usage: python scripts/measure_page_needs.py SCALE OUT.json
"""

from __future__ import annotations

import json
import sys

from PySide6.QtCore import QEventLoop, Qt, QTimer
from PySide6.QtWidgets import QApplication

SETTLE_MS = 350  # shorter settles gave false highs (ADR-0023, "How the figures were measured")


def settle(ms: int = SETTLE_MS) -> None:
    loop = QEventLoop()
    QTimer.singleShot(ms, loop.quit)
    loop.exec()


def main(scale: float, out: str) -> int:
    app = QApplication([])
    if scale != 1:
        font = app.font()
        font.setPointSizeF(font.pointSizeF() * scale)
        app.setFont(font)
    from caddcalc.gui.text_units import line_spacing, text_unit
    from caddcalc.gui.window import MainWindow, builtin_ids

    window = MainWindow()
    window.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
    window.setScreen(app.primaryScreen())
    width = round(window.launch_size().width)
    line, ch = line_spacing(window.font()), text_unit(window.font())
    window.resize(width, 1500)
    window.show()
    settle()
    window.layout().activate()
    bars = window.height() - window.centralWidget().height()
    rows = []
    for calc in window.registry:
        if calc.id not in builtin_ids():
            continue
        window.select_calculator(calc.id)
        settle()
        for index in range(window.method_box.count()):
            window.resize(width, 1500)
            settle()
            window.method_box.setCurrentIndex(index)
            settle()
            low, high = 300, 2400
            while low < high:
                trial = (low + high) // 2
                window.resize(width, 2400)
                settle(150)
                window.resize(width, trial)
                settle()
                if window.page_scroll.verticalScrollBar().maximum() > 0:
                    low = trial + 1
                else:
                    high = trial
            rows.append(
                {
                    "calc": calc.id,
                    "method": window.method_box.currentText(),
                    "long_page": getattr(calc, "long_page", False),
                    "outputs": len(window.results.fields),
                    "inputs": len(window.fields),
                    "window_h": low,
                    "content_h": low - bars,
                    "lines": round((low - bars) / line, 2),
                }
            )
            print(rows[-1], flush=True)
    with open(out, "w", encoding="utf-8") as file:
        json.dump(
            {"scale": scale, "width": width, "line": line, "ch": ch, "bars": bars, "rows": rows},
            file,
            indent=1,
        )
    window.close()
    return 0


if __name__ == "__main__":
    sys.exit(main(float(sys.argv[1]), sys.argv[2]))
```

* **It takes minutes per scale natively,** because of the settles. It is a review
  tool, not a test, so it doesn't run in CI.

## Measurements

The 100% budget is in §3. These are the same pages at larger text: the least window
height, with content lines in brackets, at each page's launch width.

| Page | 100% (1100 wide, 16 px lines) | 150% (1647 wide, 24 px) | 200% (2198 wide, 32 px) |
|---|---|---|---|
| Length converter | 1014 (60.0) | 1068 (41.9) | 1173 (34.5) |
| Right triangle | 786 (45.8) | 848 (32.8) | 941 (27.2) |
| Segment (K-factor) | 738 (42.8) | 840 (32.4) | 957 (27.7) |
| Cone | 726 (42.0) | 812 (31.3) | 917 (26.5) |
| Triangle | 714 (41.3) | 784 (30.1) | 877 (25.2) |
| Segment (Fixed K-factor) | 706 (40.8) | 800 (30.8) | 909 (26.2) |
| Regular polygon | 682 (39.3) | 744 (28.4) | 829 (23.7) |
| Bend allowance (K-factor) | 674 (38.8) | 760 (29.1) | 861 (24.7) |
| Area converter | 650 (37.3) | 704 (26.8) | 781 (22.2) |
| Bend allowance (Fixed K-factor) | 642 (36.8) | 720 (27.4) | 813 (23.2) |
| Arc and sector | 630 (36.0) | 692 (26.3) | 773 (22.0) |
| Circle, Stress converter | 598 (34.0) | 652 (24.6) | 725 (20.5) |
| Rectangle | 578 (32.8) | 640 (24.1) | 717 (20.2) |
| Angle converter | 546 (30.8) | 600 (22.4) | 669 (18.7) |
| V-die | 474–506 (26.3–28.3) | 536–576 (19.8–21.4) | 605–653 (16.7–18.2) |

These are before slice 1. The segment's rows drop by one input row at each scale once A1
and A2 are paired.

**Other measurements:**
* **Frame and taskbar:** title bar 31 px, side and bottom borders 8 px, taskbar 48 px
  (`GetSystemMetricsForDpi`, and the primary work area 1920 × 1032).
* **The least window:** 570 × 175 at 9 pt.
* **The input form:** a 6 px row gap and 9 px margins (the platform style), and 26 px
  input fields.
* **Segoe UI** (`segoeui.ttf`, read with `QRawFont`): 2048 units per em, ascent 2210,
  descent 514, no leading, and an average character width of 940 units (5.5 px at 9 pt).
* **Accessibility hooks:** Qt 6.12's `QStyleHints.accessibility()` offers
  `contrastPreference()` and `motionPreference()`, both `NoPreference` here. Windows'
  `SPI_GETHIGHCONTRAST` reads off, and "Animation effects" is on.

## What this supersedes

Each superseded part gets the note below, added as a dated amendment line in its ADR.
The original text stays, as earlier amendments do.

| ADR and section | What's superseded | The note |
|---|---|---|
| ADR-0021 §3, item 1, the height | "or the height the tallest built-in calculator page needs at the launch width … if that's more (KI-024)" | "Superseded by ADR-0023 §1: the launch height is `launch_lines` line spacings only, never derived from content. Pages are held to it by the budget (ADR-0023 §3), not by the window." |
| ADR-0021 §8, the `launch_lines` row | "The launch content height's floor … the tallest calculator page can raise it" | "Now the target height (ADR-0023 C1, 46 lines). Nothing raises it." |
| ADR-0021, amendment "the launch height covers the tallest calculator page (KI-024)" | The rule, the startup measure, the isolation boundary, and their tests | "Superseded by ADR-0023. Kept: settings pages may scroll; field heights stay in pixels (now ADR-0023 C5); no plugin page opens before it's chosen. The measure moves to the budget test, outside the app." |
| ADR-0021, amendment "every method's page in the launch height" | Measuring every method at startup | "Superseded by ADR-0023 §3. The budget test measures every method, and requires all of a calculator's methods to fit, or all to scroll, so changing the method never moves the Units box." |
| ADR-0021 §9 | Nothing; the `prose_max_chars` idea stays for later | none |
| ADR-0017 §7, `document_min_height` (160, then 96 by the 2026-10-17 amendment) | The token in pixels | "Now `document_min_lines = 6` in `[layout]` (ADR-0023 §6): 96 px at 9 pt." |
| ADR-0017, amendment "results are never obscured (refining R3)", its tests | The fixed test sizes 1100 × 720 and 1100 × 420 | "The rule is kept. Its tests move to ADR-0023's matrix, at the target and least sizes. The maintainer's 'unless perhaps they are very long' is now `Calculator.long_page` (ADR-0023 §3)." |
| ADR-0017 §8, tests at fixed window sizes | Pixel window sizes in tests | "Matrix points named by role (ADR-0023 §7)." |

## Consequences

* The window's size no longer moves when calculators are added. A tall new page is a
  review decision (redesign it, or declare it long), not a change to the window.
* The default stays as approved: 1100 × 736 at 9 pt. Smaller screens get the same
  composition fitted down, with the page scrolling.
* Startup no longer opens every built-in page, so it no longer pays for measuring them.
* CI checks layout against a font that measures like Segoe UI, once §7.1 is confirmed.
* One pixel literal in layout code is fixed (`addSpacing(16)`), and the check keeps it
  that way.
* Review gets one new item: any `long_page = True`, with its reason.

## Amendments

### 2026-10-19: ADR-0024 (units on fields) is built first

* **Order:** ADR-0024's slices (E-1 to E-7, U1 to U4) come first. This ADR's slices 1–6
  follow, in their own order, starting after ADR-0024's U4.
* **Long pages:** the Length converter becomes one input and one output (444 px,
  measured in ADR-0024's mockup), so `long_page` names the right triangle only. Slice 2
  sets it on `geometry.right_triangle` alone, and replaces PR #1's interim list.
* **The Units box goes** (ADR-0024's U2), and with it `options.addSpacing(16)`. Slice 3
  drops `options_gap`, and the pixel-literal check has nothing left to flag there.
* **The Units-box invariant** (§3, slice 2's `test_changing_method_never_moves_the_units_box`)
  becomes the output picker's: `test_changing_method_never_moves_the_output_picker`.
* **Tokens (§6):** `picker_min_chars` joins, measured from the widest choice on a page.
* **Slice 1 (paired rows)** still holds. Each sub-field of a pair gets its own picker:
  `End 1 (A1) [90] [° ▾]   End 2 (A2) [0] [° ▾]`, stacking at the least width.
* **The budget:** the results header's output picker costs 0–2 px (segment 738 → 740,
  measured). The paired row still brings the segment under 736. The cone, 10 px under,
  is still the tightest fit.
* **The matrix (slice 5)** adds the pickers' accessible names, the Tab order field →
  picker, the echo's description, and no clipping of the picker column in en_XA.
