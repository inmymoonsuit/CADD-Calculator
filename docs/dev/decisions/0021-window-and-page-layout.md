# ADR-0021: Window and page layout

* **Status:** **Accepted**; built (see Amendments). The maintainer approved the plan on 2026-10-18
  ("Approve all four: fit the launch size to the screen, cap the whole page left-aligned
  in text units, no right-hand handle for now, and have UI/UX measure and write the layout
  rules first"). After UI/UX & Design's measurements, the maintainer also approved, on
  2026-10-18, "follow Windows' text size at startup, and keep the list at least about 24
  characters wide", and §7's visible changes: "Yes, move the disclaimer under the results,
  and approve the method status and settings page changes too."
* **Builds on:** ADR-0013 (no settings file), ADR-0016 (style tokens), ADR-0017 (result
  fields; the width cap it replaces; the one-scroll-bar rule C)

## Context

* The main window always opens at 1100 × 720 and leaves its position to the system. With
  the Windows frame (about 1116 × 759 in all), it doesn't fit 1366 × 768 at 100% (39 px
  too tall) or 1920 × 1080 at 150% (87 px too tall), and only just fits 1080p at 125%.
  The status bar's disclaimer then sits under the taskbar.
* ADR-0017's width cap (`panel_max_width` = 800) caps only the results panel. On a wide
  window the inputs and notes still stretch, and the results float in the middle.
* Every size is in pixels, so nothing grows when the user's text size grows. With
  Windows' text size at 125% (as on the maintainer's machine), the app's font stays 9 pt.
  So does Windows' own Win32 message font, so reading the system font wouldn't help; only
  the text scale factor does.
* The calculator list's handle can drag the list to nothing.
* The app saves no settings file (ADR-0013), so it can't remember a window size,
  position or list width.

## Decision

### 1. Text units

* Widths are in `ch`, the body font's average character width
  (`QFontMetricsF(font).averageCharWidth()`, 5.5 px at 9 pt). Heights are in line
  spacings. Measured, `ch` tracks how much real prose fits (0.96–0.97 of it at 9, 11.25
  and 13.5 pt), where the width of "0" and the em drift.
* If a font reports `ch ≤ 0`, use 0.45 em.
* Display scaling (100–200%) needs nothing: Qt lays out in logical pixels, and points map
  to logical pixels, so every text-unit size is the same logical width at every scale.

### 2. Follow the system's text size (Windows)

* At startup, read Windows' text scale factor (the per-user `TextScaleFactor` value behind
  `UISettings.TextScaleFactor`, through the standard library's `winreg`), and scale the
  app's base font by it. Every text-unit rule then follows.
* It applies at the next start; a change isn't followed live.
* Other platforms keep their current font behaviour for now.

### 3. The launch size

1. The preferred content size, in text units:
   * width: `ceil(list_width_chars · ch + handle + page_max_chars · ch)` (1100 at 9 pt:
     280.5 + 5 + 814 = 1099.5, rounded up)
   * height: `launch_lines · line spacing` (736 at 9 pt; 720 as first approved, see Amendments),
     or the height the tallest built-in calculator page needs at the launch width, with
     any of its methods and the window's bars, if that's more (KI-024, see Amendments).
     Plugin pages aren't
     measured, so no plugin code runs before it's chosen; settings pages don't count,
     having no results to keep in view, so they may scroll.
2. Fit it to the available geometry of the screen the welcome card is on (or the primary
   screen), less the platform frame (from the native window, before it's shown) and
   `screen_margin` on each side. The welcome card is to be checked to be centred on that
   screen too, so the two stay together.
3. Centre the frame in that screen's available geometry. The position is never left to the
   system.
4. Never below the minimum window (§6).
5. Windowed, never maximized: the app is used beside a CAD window.
6. Nothing is remembered between runs (ADR-0013). If a settings file is ever allowed, it
   would store `saveGeometry()` and check it against the current screens before use.

### 4. The page cap and placement

* The splitter keeps two children, [list | page slot]. The page slot holds [page scroll
  area, capped at `page_max_chars · ch` | empty stretch], so the page sits left-aligned
  beside the list, with its scroll bar at its own right edge.
* Not inside the scroll area (the bar would sit at the window's edge, and rule C measures
  the viewport), and not as a capped splitter child (the splitter would give the extra
  width to the list).
* **The results panel** stays centred in the page. `panel_max_width` (800 px) becomes
  `panel_max_chars` = `page_max_chars`, so the panel always fills the page, inset
  included.
* **The list's handle** always moves the page's left edge. The page keeps its cap while
  the space allows, and shrinks only when it doesn't. On a window resize the list keeps
  its width and the page grows to its cap.
* **The list can't collapse:** `setChildrenCollapsible(False)` and `list_min_chars`.
* At the default window and font the page is 814 px against today's 815, so the default
  looks the same.

### 5. The space beside the page

* It's plain background: no handle, divider or placeholder.
* It's where a future right-hand pane goes (a history, a part diagram, reference). When one
  exists:
  * It docks beside a capped page when the window's content width (without the frame) is
    at least list + handle + page cap + handle + `right_pane_min_chars · ch` (1423 px at
    9 pt, about 1778 at 125% text), as the page slot's third
    part, with its own handle, opening at `right_pane_default_chars`. Its handle takes from
    the empty area first.
  * On narrower windows, a header button swaps the document area ("Notes and work") for the
    pane, like tabs, under the results. It never floats over the content, because results
    are never obscured (ADR-0017). Focus moves into the pane and back (WCAG 2.4.3).

### 6. The minimum window, and rule C

* The minimum height is unchanged: the least the page shows (ADR-0017 k5).
* The minimum width is the list's least width, plus the handle, plus the page's least
  width.
* Rule C is unaffected, because the cap is on the scroll area itself, so its viewport is
  the page's width.

### 7. The minimum-size shortfalls (KI-023)

Every page fits the window's least width, and nothing essential is cut off. KI-023's
offscreen Windows figures come from a much wider fallback font; natively the disclaimer is
661 px, the least window 365 and the settings form 615, and those are the figures to design
to.

* **The disclaimer moves under the results, out of the status bar.**
  * It becomes the results panel's last line: aligned with the frames, word-wrapped, in
    the secondary text style (4.5:1 or better).
  * It's safety text, so it's never cut off. It wraps at any width and in any language,
    sits with the answers it qualifies, and scrolls with them. It costs one or two lines
    of page height, after the first field, so the minimum-height rule is unchanged.
  * The status bar keeps only passing messages, such as "Copied …". The About dialog and
    the CLI keep their copies.
  * Eliding it was rejected (an ellipsis hides the part that says to verify), and so was
    a wrapping status bar (a status bar is one line by convention, and growing it takes
    height where it's scarcest).
* **The method box shows the method's name; its status goes beside it.**
  * The status ("unverified · reproduces legacy") is secondary text beside the box, and on
    a line of its own under the row when narrow. The dropdown list keeps the status, so
    methods can still be compared.
  * The box's least width is its longest name (`method_min_chars`, measured from the
    registry, through `setMinimumContentsLength`), so names are never cut. The page's
    least width includes it.
* **The family settings page reflows instead of scrolling sideways.**
  * Paired choice boxes stack when there isn't room for both side by side.
  * The form wraps labels above their fields when narrow (`QFormLayout.WrapLongRows`).
  * Its horizontal scroll bar is off, and its least width drops to about 260 px.
* **Test:** the en_XA clipping test runs every page at the least size, with no exceptions
  left; KI-023 closes.

### 8. Tokens (`[layout]` in `ui_style.toml`)

| Token | Value | Meaning |
|---|---|---|
| `list_width_chars` | 51 | The list's launch width (280 px at 9 pt) |
| `list_min_chars` | 24 | The list's least width (132 px at 9 pt) |
| `page_max_chars` | 148 | The page's widest, scroll bar included (814 px at 9 pt) |
| `panel_max_chars` | 148 | Replaces `panel_max_width`: the results panel's widest |
| `launch_lines` | 46 | The launch content height's floor, in line spacings (736 px at 9 pt; 45 as first approved, see Amendments); the tallest calculator page can raise it |
| `screen_margin` | 16 | The least space between the frame and the screen's work area |
| `method_min_chars` | measured | The method box's least width: the longest method name, computed from the registry when the window is built, not typed in |
| `right_pane_min_chars` | 58 | Future: a docked right pane's least width |
| `right_pane_default_chars` | 64 | Future: its width when it opens |

### 9. Later, not part of this decision

* A separate measure for the notes' prose (`prose_max_chars` about 100). At the cap the
  notes wrap at 136–142 characters per line.

## Consequences

* The window always fits the screen it opens on.
* The disclaimer sits under the results, always whole, in every language.
* The default window looks as it does today; wide windows keep the same composition, with
  empty space to the right.
* Larger Windows text makes the whole layout larger in proportion, not just the letters.
* A right-hand pane can be added later without re-laying out the page.

## Amendments

### 2026-10-18: as built

* **Modules.** `gui/window_layout.py` holds the arithmetic, with no Qt: `ch`, `chars`, the
  launch size, `fit_window`, and Windows' text size. `gui/text_units.py` measures a font,
  and `gui/reflow.py` lays widgets out in a row while they fit at their preferred widths,
  else in a column. The import contract keeps `window_layout` free of Qt.
* **Line spacing** is the font's in whole pixels (`QFontMetrics.lineSpacing()`), as text
  lines are laid out: 16 at 9 pt Segoe UI, so 45 lines are 720. The fractional spacing,
  15.94, would give 718.
* **Windows' text size** is read with `winreg` from `HKCU\Software\Microsoft\Accessibility`,
  `TextScaleFactor`, a percentage from 100 to 225 (`UISettings.TextScaleFactor`'s 1 to
  2.25). Any other value, a missing one, or another platform gives 1. `main()` scales the
  app's font before the first widget, and puts it back on the way out.
* **The launch.** `MainWindow.fit_to_screen()` measures the frame from the native window
  before it shows, then fits and centres the window on the welcome card's screen. The
  welcome card now centres itself on its screen's work area; before, its place was the
  system's. A window built without `fit_to_screen`, as in tests, opens at its launch size.
* **`method_min_chars`** is measured when the window is built: the longest method name in
  the registry, plugins included, in the widths of "X" that a combo box's least contents
  length counts. A test checks every method's name fits its box at the window's least
  size. The box's open list shows each method with its status, through an item delegate.
* **The settings page** scrolls in a `PageScrollArea`, as the calculator page does, so its
  least width is its content's and it never scrolls sideways. Paired choice boxes are a
  `Reflow`.
* **The results panel's height** is its height for its width, since the disclaimer wraps;
  its size hints say so, so the page's one-scroll-bar fit reads the true height.
* **What the disclaimer costs at the default size.** Natively, at 1100 × 720 and 9 pt, it
  adds 22 px to the results (one line and a gap). The cone's page had 16 px to spare, so
  at 720 it scrolls as a whole by 6 px (rule C). So `launch_lines` is 46, 736 px at 9 pt,
  on UI/UX's recommendation: every page fits the launch size, the default view is as it
  was, and it fits every screen 45 did.
* **Offscreen fonts.** On Windows the offscreen platform has no font database, so every
  character, the average included, is 12 px, and `ch` is 12 rather than 5.5. Tests of the
  results pin the list at 280 px, so they test the results, not the platform's font; the
  layout's own tests check the text-unit rules against whatever font there is.
* **The `math.ceil` fix** in `ResultsPanel._align` is here: a column a fraction of a pixel
  narrower than its text lost the text's last pixel on Linux.
* **KI-023,** the least-size shortfalls, is on the localization branch with its clipping
  test, which narrows its allowance once this is rebased under it.

### 2026-10-18: the layout review's fixes (UI/UX)

* **A reflowing row is a layout** (`ReflowLayout`), not a widget that measures itself.
  Qt asks a widget's layout for its height at a width, never the widget, so the first
  build's heights didn't reach the form: the settings page's choice boxes were 0 px tall
  (H1), and the method row didn't grow when its status went under the box (M1).
* **A page's least height is its height at its width** (`PageWidget`). Its layout's
  least height takes each part at its narrowest, where a stacked row or wrapped text is
  tallest, and a scroll area sizes its page by it, so a page scrolled by 22 px it didn't
  need. The page's fit (`_needed_height`) uses its height for its width alone (M2).
* **A limitation, KI-024:** the launch height is in lines, but the fields' heights are in
  pixels. With a UI font whose lines are shorter than 9 pt Segoe UI's 16 px, the launch
  window is shorter than the pages need, and the tallest page scrolls at launch.
* **Tests** check that every part of every page is as tall as it needs, at the launch
  size and the least; that the method row grows and shrinks; that the segment page fits
  1100 × 720; and that no page scrolls at the launch size, where the lines are 16 px.
* **The tests' clipboard is in memory.** A native run shared the system's clipboard with
  every other program, so copying tests failed by turns, and overwrote the user's copy.

### 2026-10-18: Support & Review's Lows

* **The font is put back however `main()` ends** (L3), in a `finally`, so a failed
  start or teardown can't leave the app's font scaled.
* **Tests for what had none** (L2): a column whose text ends a fraction past a whole
  pixel, in an unhinted face, is rounded up; a text size that isn't a DWORD gives 1;
  each of the three `[layout]` cross-checks refuses; and `main()`, at 125%, builds the
  window in scaled fonts, fits it to the welcome card's screen, and restores the font,
  even when its teardown fails.

### 2026-10-18: the launch height covers the tallest calculator page (KI-024)

UI/UX ruled on KI-024 (its layout-fixes review): the launch shows every calculator page
without scrolling, whatever the font, as 1100 × 736 does on Windows at 9 pt.

* **The rule.** The launch height is `max(launch_lines · line spacing, the tallest
  built-in calculator page's height at the launch width)`, capped by the screen's fit
  as before.
  A page's height is the height it fits in with its document at its least (rule C),
  plus the window's menu and status bars. `launch_lines` is now the floor.
* **Calculator pages only.** A family's settings page has no results; it's a form with
  long help text, and scrolling it is normal. Counting it would let its help text set
  the window's height. Its rules stay: never sideways, and nothing clipped at the
  least size (§7).
* **Not field heights in text units.** ADR-0017's field sizes are pixels on purpose:
  the 28 px copy button and the 40 px field are click targets, which text units would
  shrink toward WCAG 2.5.8's 24 px minimum, and the focus ring and borders are whole
  device pixels by rule.
* **How it's measured.** When the window is built, each calculator's page is laid out
  hidden at the page's cap and measured, with each of its methods (below). A hidden page is laid out only when shown, and
  the results panel's height follows its own width, so the page is laid out twice
  (`pages.lay_out`); the second pass gives exactly the heights the shown page has,
  where one pass overstates the first page measured. The fit test and the page scroll
  area share one measure (`pages.fit_height`).
* **Built-in calculators only.** Measuring opens each page before the user chooses
  it, and a plugin's page runs the plugin's code, so only built-in pages are measured:
  no plugin code runs before its calculator is chosen, and the cost stays fixed as
  plugins are added. A plugin page taller than the launch height scrolls as a whole
  when opened (rule C). The window opens on the first built-in calculator, though a
  plugin's family sorts first, so a broken plugin's page isn't the first one shown
  (Support & Review).
* **A failing page is left out.** As a safety net, a page whose code raises any error
  while it's measured is left out of the launch size, with a warning, as an isolation
  boundary: it mustn't stop the window or the other calculators (Support & Review's
  M1; ADR-0019).
* **What it does.** On Windows at 9 pt nothing changes: the tallest page, the cone's,
  needs 672 px plus 54 px of bars, 726, under 736. With the offscreen platform's 14 px
  lines, 644 px of lines became 672, and no page scrolls where the cone and segment
  did. Measuring the four built-in pages takes about 25 ms, while the welcome screen
  shows.
* **Tests.** No calculator page scrolls at the launch size, with the platform's font
  and with one whose lines are under 16 px, everywhere; a mutation back to lines alone
  fails both. Each page's measured height is its shown height, which one layout pass
  fails. Building the window opens no plugin page, and opens on a built-in one, though
  the plugin's family sorts first; and a built-in page that raises while measured is
  left out, the window and the others working.

### 2026-10-18: every method's page in the launch height (UI/UX's labels review, M1)

* **What UI/UX found.** The launch measure took each built-in calculator with its first
  method only. The segment calculator's K-factor method adds the K field, and its page
  then needed 618 px with its document at its least, so at the launch size it scrolled.
  The scroll bar narrowed the page, from 814 to 802 px, so choosing that method moved the
  Units box, from x 1024 to 1012.
* **The rule now.** The tallest page is measured over every built-in calculator and each
  of its methods, within the same isolation boundary, now one per method, and the same
  screen cap. So no built-in calculator's page scrolls at the launch size with any of its
  methods, and changing the method never moves the row's controls.
* **Each method is opened directly,** with the method box's signal blocked, not through
  the signal: an error raised in a Qt slot goes to `sys.excepthook`, past the isolation
  boundary, so a failing method's broken page would have been measured, unwarned.
  Support & Review's test of one failing method found it: only the V-die's 8 × thickness
  page fails to show, one warning names it, and the percentage rule is still measured. A
  compute's own error no longer reaches the measure: the page shows it, and is measured
  so (ADR-0006 and ADR-0017, amendments).
* **What it costs.** On Windows at 9 pt the launch height is 738 px, the segment
  calculator's K-factor page with the window's bars, two more than `launch_lines`' 736.
  The window's build lays out twice as many pages, and took 777–814 ms against 740–769 ms
  before, over six launches each, natively; it runs hidden, after the card's first paint.
