# ADR-0017: Result fields, one boxed, copyable component for every calculator

* **Status:** **Accepted, and built** (slices k1–k6, 2026-10-17 and 18; see Amendments). On
  2026-10-17 the maintainer approved R1–R6 as recommended, and the optional findings
  F1–F3 as in scope, and later refined R3 (results are never obscured) and capped the
  panel's width. F4 is a follow-up, and F5 is KI-022, with ADR-0020's L4 (accepted) as
  its planned fix. Drafted by the UI/UX & Design session; the Engine checked it against
  the code and built it.
* **Date:** 2026-10-17
* **Builds on:** ADR-0016 (the style-token discipline), ADR-0004 (Result and provenance),
  ADR-0005 (units and display), ADR-0003 (layers), [design/palette.md](../design/palette.md)
* **Design references:** the mock-ups `results/mock-light.png` and `mock-dark.png`, and
  the current pane, `results/results-*-light|dark.png`. All are in the design session's
  scratchpad, local only.

## Context

The maintainer asked for each output under a calculator's Results to be in its own box,
with an inline Copy button, built as **one system and one style used by every calculator,
not a hand-rolled change to each**.

Today `result_html()` (gui/window.py) writes every section as a single rich-text document
in a `QTextBrowser`: Results, Notes, Inputs, Work, and Method. Results are table rows of
symbol, label, and `format_value()` text.

The likely use: someone reads a bend allowance or a flat length, then pastes it into a CAD
dimension box or a spreadsheet cell.

## Decision

### 1. A hybrid: native result fields above the document (option C)

| | A. Native widgets for everything | B. Keep one HTML document; copy as anchor links | **C. Hybrid: native result fields; the rest stays HTML** |
|---|---|---|---|
| Hover, focus, pressed, copied states | full | none (Qt rich text has no hover or focus styling) | full |
| Keyboard | full Tab order, Space or Enter, Ctrl+C | only link-by-link Tab within the browser | full |
| Screen readers | each field and button named | links read as "Copy" | each field and button named |
| Dark theme | palette roles | inline colours | palette roles |
| Selection of the value | a selectable label | document selection | a selectable label |
| Print and export (none today) | rebuild | already a document | the document form stays available (§6) |
| Effort and risk | large: Notes, Work, and Method would all be rebuilt | small, but it can't meet the states or accessibility | medium: one component, and the document keeps the rest |

**C is recommended.** Results are the part people act on, so they get real controls. The
reading sections (Notes, Inputs, Work, Method) stay as a document, which suits long
wrapped text, selection, and later export.

* The fields sit in a **Results panel pinned above the scrolling document** (R3). The
  answer stays in view while you read the Work, and short panels keep the pane compact.
* The document then starts at Notes.
* **Short windows (code-check decision 5).** The document always keeps at least
  `document_min_height`, 160 px.
  * The panel takes its content height, but never more than the pane height minus that
    minimum, and never less than one field plus its header.
  * When its fields don't fit, the panel scrolls on its own, vertically only; the
    document keeps its own scrollbar.
  * Example: at 1100 × 720, with five inputs, notes, and four fields, the panel shrinks
    to leave the document 160 px, and scrolls its fourth field into view.
  * **Refined by the maintainer:** results never scroll on their own; the page does (see
    Amendments, "Results are never obscured").

### 2. Anatomy

```
┌──────────────────────────────────────────────────────────────────┐
│ BA     Bend allowance                         0.3119  in   [⧉]  │
└──────────────────────────────────────────────────────────────────┘
  symbol  label (secondary)              value (tabular)  unit  copy
```

* **Frame:** a 1 px square border (no rounded corners, matching ADR-0016's square panes)
  in `field_border`, on `background`.
* **Symbol:** bold, in a fixed column sized from the widest symbol among this
  calculator's outputs, so labels line up.
* **Label:** the secondary text role, taking the remaining width, elided with a tooltip
  if it's too long.
* **Value:** bold, in **tabular figures** (`QFont.setFeature("tnum")`), and
  **aligned on the decimal point** (code-check decision 3).
  * Lengths show 4 decimals, angles 2, and stresses 1, so right alignment alone would
    misalign a mixed set such as the cone's.
  * Each value is right-aligned, then padded on its right by the width of the decimal
    places it lacks against the set's most: `(max_decimals − decimals) ×` the
    tabular-figure advance. A value with no decimal point is also padded by the point's
    width.
  * The value stays a single label, so selecting and copying it by mouse still gives
    the whole number.
* **Unit:** regular weight, in a fixed column sized to the widest unit text in this
  result set. When the inch-fraction preference is on, its "(≈ 5/16")" follows in the
  muted role and is never copied (R1).
* **Copy button:** a 28 × 28 px autoRaise tool button with a 16 px Tabler "copy" icon,
  and a "check" icon for the copied state. Both icons are vendored through the existing
  pinned, hash-checked fetch script.
* **Spacing,** all on ADR-0016's scale:
  * padding 6 px vertical and 12 px horizontal
  * gaps of 12 between columns and 6 between fields
  * the panel inset 16 at the sides and 12 at the top
* A field is at least 40 px tall, which keeps the 28 px button comfortable as a target.

### 3. States

| State | Look |
|---|---|
| default | `field_border` 1 px |
| hover (field or button) | border in the `text` role, plus a fill of the `text` role at `hover_fill_opacity` 0.04, painted at paint time (ADR-0016's role-plus-opacity pattern) |
| keyboard focus (button) | a 2 px `focus_ring`, drawn outside the frame with a 1 px gap, so it can sit beside a note outline without merging into it |
| pressed | the button's pressed fill (style default) |
| copied | the icon becomes a check for `copied_ms` (1500), with nothing else moving; the status bar shows "Copied BA = 0.3119 to the clipboard" |
| a note concerns it | the outline roles already used for inputs, by the same ranking: `outline_limit`, then `outline_note`, then `outline_no_value` (dashed). For example, INFEASIBLE flat length outlines its field. |
| no value | the value shows "—"; the button is disabled with the tooltip "No value to copy" |

* **Outline widths (code-check decision 4).** There's one width per role, shared by input
  and result fields:
  * The default border is 1 px, in `field_border`.
  * Every note outline is 2 px: `outline_limit` and `outline_note` solid,
    `outline_no_value` dashed.
  * The 2 px weight tells an outline from the default border even without colour (WCAG
    1.4.1, use of colour). Input fields change from 1 px to 2 px to match.
* **Focus must never look like a warning (code-check decision 1, option a).** In the
  light theme, ink, slate, and crimson are all outline roles, and amber fails 3:1 on
  white. So focus gets **one new palette colour, `focus_blue = #2E7BCF`**, used for
  `focus_ring` in both themes.
  * It's 4.33:1 on white and 3.60:1 on ink, so it passes non-text 3:1 in both themes.
  * Its colour distance (CIEDE2000) from every other palette colour is at least ΔE 17:
    17.1 from slate, 41.0 from ink, 45.6 from crimson, and 56.5 from amber. Blue against
    crimson stays distinct for red-green colour blindness.
  * Slate is the closest. A search of blues that pass 3:1 on both white and ink found
    none more than about ΔE 19.6 from slate, because slate is itself a mid-tone
    blue-grey.
  * The ring also differs from slate's uses in form: it's a solid 2 px ring outside the
    frame, while slate is the 1 px default border and the dashed no-value outline.
  * **Approved by the maintainer on 2026-10-17** ("I like that blue a lot, it fits
    well"). It joins the palette as `focus_blue`.
  * Option (b), the system accent from QPalette.highlight, was declined: it's untested,
    and it can fail contrast, for instance with a pale accent.
* **Tests:**
  * `focus_ring` meets 3:1 against `background` in both themes.
  * It differs from every `outline_*` and border role by CIEDE2000 ΔE ≥ 15. That's well
    above the roughly 10 at which colours read as clearly different, and the most a
    3:1-passing blue can reach against slate.
  * Every border role meets 3:1 (WCAG 1.4.11, non-text contrast).

### 4. Copy behaviour (R1, R2, R4, R6)

* **Copy (R1):** the number exactly as shown, without its unit. In the example that's
  `0.3119`: the displayed digits, ASCII "-" for negatives, and "." as the decimal point.
  * A bare number pastes cleanly into a spreadsheet cell, and into CAD dimension boxes
    that work in the drawing's units. A unit suffix breaks spreadsheet cells, and some
    CAD inputs refuse it.
  * Copying what's shown means the paste always matches the screen.
* **Copy all (R2):** a header button copies one tab-separated row per output, in this
  form: `BA⇥Bend allowance⇥0.3119⇥in`. Pasted into a spreadsheet, that lands as columns.
* **More formats (R6):** a context menu on a field, by right-click or the Menu key,
  offers:
  * "Copy value", the default
  * "Copy with unit" (`0.3119 in`)
  * "Copy full precision" (`0.311924…`, the display unit, unrounded, to 10 significant
    digits)
  * "Copy fraction", when shown. It copies `5/16"`, or `1-5/16"` for a mixed number,
    with the inch mark (code-check decision 6). A bare `5/16` is read as a date by
    spreadsheets; with the mark it's unambiguously a length, in the form CAD inch input
    takes. This stays dormant until a fraction preference exists.
* **Feedback (R4):** the check icon in place for 1.5 s, plus a status-bar message, which
  screen readers also announce. Nothing in the layout moves.
* **Never stale.** Copy reads the field's current `Result`. When the inputs become
  invalid, every field shows "—" at once and every button is disabled, so an old answer
  can't be copied after its inputs changed.

### 5. Keyboard and accessibility

* **Tab order:** the inputs, then each field's copy button in output order, then
  Copy all. Space or Enter copies. Ctrl+C copies the value of the focused field's
  button. Ctrl+Shift+C copies all.
* **Accessible names:**
  * the field: "Bend allowance, BA: 0.3119 inches", with the unit spoken
    (code-check decision 7). `core.units.Unit` gains a `spoken_plural`, e.g. "inches",
    "millimetres", "degrees", "kips per square inch". It's used for any value other
    than exactly 1, and the existing singular `name` for 1. A test checks that every
    unit has one. A unitless ratio speaks only its number.
  * the button: "Copy bend allowance"
  * Copy all: "Copy all results"

### 6. One generic data path, no per-calculator code

* `core.formatting` gains small pure functions, so the GUI never formats numbers itself:
  * `value_parts(value, dimension, prefs) -> (number, unit, fraction)`
  * `copy_text(value, dimension, prefs, form)`, where `form` is value, with_unit, full,
    or fraction
  * `results_tsv(calc, result, prefs)`

  They're tested in core, and the CLI is unchanged.
* `gui.result_fields.ResultsPanel` builds one `ResultField` per `calc.outputs` from
  `result.outputs`, every time results render. Every calculator, plugins included, gets
  it for free.
* `result_html()` gains `include_results: bool = True`. The GUI passes False, because the
  panel shows them. Export, print, and tests keep the complete document.

### 7. Tokens: an app-level extension of ADR-0016

* A new `gui/assets/ui_style.toml` (`schema = 1`), with a `[result_field]` section, read
  by `gui/ui_style.py`.
* It shares one loader core with `welcome_style.py`, factored into `gui/style_tokens.py`:
  * the spacing scale and its refusal
  * the role checks against both palette themes
  * the typed number and range checks
  * unknown-key refusal
  * a doc-quoting test
* Keeping the two files separate means no churn in the welcome tokens. Later components,
  such as notes or inputs, add sections to `ui_style.toml`.
* `[result_field]` tokens:
  * padding [6, 12]
  * gap 12
  * stack_gap 6
  * min_height 40
  * button_size 28
  * icon_size 16
  * border_width 1
  * border_role "field_border"
  * hover_border_role "text"
  * hover_fill_role "text"
  * hover_fill_opacity 0.04
  * focus_role "focus_ring"
  * focus_width 2
  * focus_gap 1
  * outline_width 2, which the input fields share
  * the outline roles as in §3
  * copied_ms 1500
  * value_weight "bold"
  * tabular_figures true
  * decimal_align true
  * document_min_height 160
* New palette entries:
  * the colour `focus_blue = "#2E7BCF"`, approved by the maintainer on 2026-10-17
  * the roles, in both themes:
    * `field_border`: slate, 3.85:1 on white and 4.05:1 on ink
    * `focus_ring`: focus_blue
* `field_surface_hover` is dropped: hover uses the `text` role at
  `hover_fill_opacity`.
* The literal ban extends to `result_fields.py`.

### 8. Tests

* core: `value_parts`, `copy_text` (every form; negatives; fractions excluded), and
  `results_tsv`.
* GUI, with QTest:
  * a panel per calculator that matches its outputs
  * the clipboard contents for each form
  * the check icon reverting after `copied_ms`
  * the disabled state on invalid inputs, with no stale copy
  * Tab order and Space, Enter, Ctrl+C, and Ctrl+Shift+C
  * accessible names
  * note outlines on a field a note concerns
  * dark theme
  * a plugin calculator in tests getting fields with no code of its own
* The palette tests: the new roles, the focus distinctness, and 3:1 non-text contrast.

## Decisions by the maintainer

Approved on 2026-10-17, each as recommended. The alternatives stay on record.

| | Question | Recommended | Alternatives |
|---|---|---|---|
| R1 | What Copy copies | **The number as shown, without its unit** (`0.3119`) | With its unit (`0.3119 in`); full precision (`0.311924…`) |
| R2 | Copy all | **Yes: tab-separated rows (symbol, label, value, unit), which paste into spreadsheet columns** | Plain lines ("BA = 0.3119 in"); no Copy all |
| R3 | Where the fields sit | **Pinned above the scrolling Notes, Inputs, and Work, so the answer stays in view** (refined: never scrolled on their own; see Amendments) | Scrolling with the rest of the document |
| R4 | Copied feedback | **A check icon in place for 1.5 s, plus a status-bar message** | A tooltip only; a toast |
| R5 | Field outlines from notes | **Yes, the same outline roles and ranking as the input fields** | No outlines on results |
| R6 | Other copy formats | **A context menu: with unit, full precision, fraction** | None |

## Consequences

* Every calculator's results, including plugins', get boxes, copy, states, and
  accessibility from one component and one token section.
* The style system grows from the welcome screen to the app, through one shared loader
  core.
* The document loses its Results table on screen but keeps it for export.
* Two new vendored icons (copy and check), and three new palette roles.

## Alternatives considered

* **B, anchor links in the HTML:** cheap, but it can't give hover, focus, or copied
  states, keyboard reach is weak, and screen readers hear only "Copy".
* **A, rebuilding the whole pane natively:** it isn't needed for this ask, and it puts
  the long Notes and Work text at risk.
* **Copying with the unit by default:** it fails in spreadsheets and in some CAD inputs.
  It stays available from the context menu.

---

## Findings for the same system

Seen in the current pane (`results/results-notes-light.png`).

**Scope, as approved on 2026-10-17:**
* **F1–F3 are in scope** for this ADR's build. F1's wording is drafted in
  `0017-note-wording.md`, beside this draft, for Support & Review to check against
  ADR-0014 §5.5 and the brief.
* **F4 is a follow-up.**
* **F5 is a follow-up,** recorded now as a KI.

* **F1. Notes bury the actionable number.** The 6061 limit note is about 700 characters.
  The required radius ("0.16 in at 0.063 in") sits mid-sentence, after the source
  names.
  * Lead with the decision, e.g. "Inside radius 0.050 in is below the recommended
    minimum 0.16 in (6061-T6, 0.063 in, aerospace practice)."
  * Follow it with a muted "Sources:" line.
  * Reword with Support & Review, since the content is theirs.
* **F2. Two markers on each note.** Every note has a list bullet as well as its kind
  icon. Drop the bullet and keep the icon.
* **F3. Results and Inputs don't share a grid.** Different tables, different column
  widths, and the Inputs' source is a fourth column in parentheses. With the fields in
  place, lay Inputs out on the same grid (symbol, label, value, unit), with the source
  as muted text.
* **F4. Method is long and always expanded.** Its notes and references run on for
  several lines. Move it to the end in a smaller size, or behind a "Method and
  references" disclosure once the reading sections go native.
* **F5. Decimal separator.** The app always writes ".", so a paste into a
  comma-decimal spreadsheet is misread. Record it as a KI, plus a future display
  preference. It isn't needed for this ADR.

## Amendments

### 2026-10-17: what k1, k2a, and k2b built

* **k1:** `core.formatting` gained `value_parts()`, `copy_text()` with the forms value,
  with unit, and full, and `results_tsv()`. `format_value()` is built on `value_parts()`,
  and a test holds it identical to before. The fraction form waits for the result fields.
* **k2a:** the loader core every token file shares moved into `gui/style_tokens.py`
  (ADR-0016, amendments).
* **k2b,** the style plumbing:
  * `gui/assets/ui_style.toml` and `gui/ui_style.py`, documented in
    `docs/dev/design/result-fields.md`, with a test that the page quotes every token.
  * The palette gains the colour `focus_blue` and the roles `field_border` and
    `focus_ring`. A test keeps focus at least CIEDE2000 ΔE 15 from every outline and
    border role, and every new role at 3:1 against the background.
  * The Tabler `copy` and `check` icons are vendored through the pinned fetch.
  * `gui/outlines.py` holds the note-outline ranking for input and result fields alike.
    Input fields' note outlines are now 2 px.
  * `core.units.Unit` gains `spoken_plural` and `spoken(amount)`.
* **Where k2b departs from §7's token list:**
  * The outline tokens are their own table, `[note_outline]`, not part of
    `[result_field]`, since input fields use them too (§7 lets later components add
    sections). It holds `width` (§7's `outline_width`), a role and a line style for each
    kind of note, and `error_role` and `error_style` for an input whose text can't be
    read.
  * `[result_field]` gains `panel_inset` (§2's 12 at the top and 16 at the sides), and
    `copy_icon` and `copied_icon`, which name the vendored icons, so `result_fields.py`
    writes no literals.
  * There's no `field_surface_hover` role, as §7 says: hover is the `text` role at
    `hover_fill_opacity`. So the palette gains one colour and two roles, not the three
    roles under Consequences.
* **§6, per the code check:** the panel is built when the calculator changes, and its
  values update on each recompute, rather than being rebuilt every time results render.
  That keeps keyboard focus and hover through typing (k3).

### 2026-10-17: the panel as built (k3)

* `gui/result_fields.py` holds `ResultField`, `ResultsPanel`, and `ResultsArea`, the
  scroll area. The panel is built per calculator and updated per recompute; both error
  paths blank every field and disable its copy button ("No value to copy").
* Fields present outputs through `core.formatting.output_parts()`, and the document and
  the CLI through `format_output()`, so ADR-0018's output presentation lands in one
  place. On screen, `result_html(..., include_results=False)` starts the document at
  Notes.
* Notes outline the result fields they name, through `gui/outlines.py`.
* Values align on the decimal point with tabular figures, as §2 describes.
* **Two tokens added:** `result_field.fill_role` (`background`) and
  `result_field.text_role` (`text`). §2's "secondary text role" for the label doesn't
  exist in the palette, and slate, the nearest, is 3.85:1 on white, under 4.5:1 for
  normal text (palette.md forbids slate for small text). So the label is the text role
  at regular weight, set apart from the bold symbol and value by weight. For the same
  reason, the dormant "(≈ 5/16\")" uses the text role, not the muted one.
* **The disclaimer** is a normal status-bar widget, not a permanent one: a passing
  message, such as "Copied", covers it for a moment and it comes back, rather than both
  sharing one line.
* **Shared painting:** the crisp-line helpers moved from `welcome.py` to
  `gui/painting.py`, with a dashed style for the no-value outline.
* The copy button is shown and enabled with a value, but copying, the copied state,
  the keyboard, and the accessible names come with k4.

### 2026-10-17: results are never obscured (refining R3)

* **The maintainer's decision,** on seeing bend allowance at 1100 × 720 show only BA,
  with OSSB and BD behind the panel's own scroll bar: "I feel that it's incorrect for us
  to ever obscure results, unless perhaps they are very long so they would cause the
  lower section to break the overall app border." The boxed fields themselves stay as
  built.
* **The panel never scrolls on its own.** It's always exactly as tall as its title and
  every field. `ResultsArea` is gone: the window holds the `ResultsPanel` itself.
* **The document takes the height that's left,** and keeps its own scroll bar.
  `document_min_height` drops from 160 to 96, so more layouts fit without scrolling. The
  document asks for no more than that least height, so a page that has to scroll gives
  its room to the results first.
* **A window too short for it all scrolls the page as a whole:** one vertical-only
  scroll area (`gui/pages.py`, `PageScrollArea`) around the title, summary, options,
  inputs, results, and document. Results scroll only with the page, never clipped on
  their own.
  * The area is never narrower than its page, since it doesn't scroll sideways.
  * The page stack takes its height from the shown page alone (`PageStack`), so a family
    page isn't made to scroll by the calculator page behind it. The family page keeps
    its own scroll area, unchanged.
* §1's short-window rule (the panel shrinking to leave the document 160 px, and
  scrolling its fields) and §7's `document_min_height 160` are replaced by the above.
* Tests: at 1100 × 720, bend allowance and the cone show every field in full, with no
  scroll bar on the panel; at 1100 × 420 the page scrolls, the document is at its least
  height, and every field can be scrolled into full view; the document still scrolls on
  its own; the page is never narrower than its content; and a family page isn't made to
  scroll by the hidden calculator page.

### 2026-10-17: layout refinements from the design review (k3c)

From UI/UX & Design's review of k3b:
* **Notes strongest first.** The document lists notes by the outlines' ranking
  (`gui/outlines.py`, `RANKS`, `strongest_first`): a cited limit, then a warning or an
  impossibility, then a check that couldn't be made, in the calculator's order within a
  rank. An impossibility ranks with a warning because it already shares a warning's
  outline, so the order and the outlines can't disagree. The CLI and JSON keep the
  calculator's order.
* **One scroll bar, never a scroll inside a scroll.** When the page scrolls, the
  document shows at its full height, with no scroll bar of its own, so the wheel over it
  scrolls the page. When the page fits, the document fills the height that's left and
  scrolls on its own, as before. `gui/pages.py`'s `PageScrollArea` decides: the document
  (`PageDocument`) shows in full exactly when the page couldn't fit with it at its least
  height.
* **The "Results" title** is indented by the focus ring's room, 3 px, in line with the
  frames. The design doc records the spacing as seen: a visible 12 px between frames and
  a visible 19 px side inset, both measured by a test.
* **A close-up unit joins its number.** The degree sign sat 27 px from its number in its
  own column; it now joins the value, as the document writes it, by the rule
  `ValueParts.unit_close_up` exposes, and counts in the decimal alignment.
* Tests: the switch from bend allowance to the cone and back shows every field in full
  each time; both document states, with the wheel in each; a page that grows tall again
  goes back to filling; the note order; the title and spacing; the degree sign.

### 2026-10-17: copying, the keyboard, screen readers, and the notes (k4)

* **Copy (R1)** goes through `core.formatting.copy_output()`, the output-level twin of
  `output_parts()`, so ADR-0018's output presentation applies to copies as well. The
  field copies the value it shows now, from its base value and the display preferences
  it was shown in; with no result, nothing copies (§4).
* **The context menu (R6)** opens as a popup rather than `QMenu.exec()`, so no nested
  event loop runs. `CopyForm.FRACTION` copies `5/16"` or `1-5/16"` (code-check decision
  6), only while a fraction shows; `copy_text` refuses it otherwise.
* **Copy all (R2)** has a header button and the window action Ctrl+Shift+C, which acts
  only while a calculator's results show. `results_tsv` keeps a text cell from being read
  as a formula: one starting with `=`, `+`, `-`, `@`, or their full-width forms, after
  any spaces, gets a leading apostrophe; the value cell never does. That follows OWASP's
  "CSV Injection" page, which lists those characters, the full-width forms that some
  locales' spreadsheets read, and tab, CR, and LF, which a cell here already turns into
  spaces (Support & Review's L5).
* **Feedback (R4):** the check shows for `copied_ms`, the status message lasts as long,
  and `QAccessibleAnnouncementEvent` tells screen readers, politely. That event is new
  in Qt 6.8, the `gui` extra's floor.
* **Keyboard (§5):** Space, Enter, and the platform's Copy keys press the focused copy
  button, through the button's own key handling, not a window-wide shortcut. Tab order
  is set explicitly: the inputs, each copy button, then Copy all.
* **Accessible names (§5),** as whole messages with named fields, keeping labels as
  written: the button is "Copy Bend allowance", not §5's "Copy bend allowance", since
  lower-casing a translated label would be wrong in, for example, German. The field's
  name is also the button's description, so it's said with the button.
* **Localization-ready, from ADR-0020's review (items A–E):**
  * A: `Note.quantities` is a mapping of named fields, e.g. `{"R": (value, LENGTH)}`
    filling `{R}`, and a mapping in JSON.
  * B: `Note.text` and `Note.detail` are templates; `Note.phrases` carries the data's
    words (material, practice, each source's stated value) as named fields too, so
    nothing is joined onto a sentence. A note with neither is plain text, so existing
    notes, plugins' included, read as before. A positional, unknown, or doubly given
    field is refused (`SpecError`).
  * C: `Unit.spoken()` takes the number as shown; only a shown "1" is singular.
  * D: the messages above.
  * E: decimal alignment counts the places after `decimal_separator(prefs)`, which is
    "." until a separator preference exists (ADR-0020 L4).
* **F1, the notes:** `describe_note(note, prefs)` returns a `NoteText` of heading, lead,
  detail, and sources. The bend check's wording follows UI/UX's draft with Support &
  Review's check:
  * M1: each source's value and where it applies, `{stated} at {column}` or `{stated}
    for sheet {column}`, verbatim, then `, from {label}` for a stand-in. Each source is
    its own sentence rather than one joined list. A test checks every covering source's
    stated value and column in each limit note's detail.
  * L1: the lead reads "below {minimum}, the recommended minimum this check uses, for
    …".
  * L2: the material is `name_in(temper)` and the practice comes from the rows.
  * L3: the scope words are always in the lead. With L1's longer phrase, the usual case,
    6061-T6 in inches, is 150 characters, not 140; 304's lead is 169, mild steel's 167,
    and inch fractions take one to 202. The budget test holds the template's own words
    to 85 characters and the 6061 case to 150, and never trims the scope.
  * L4: the K warning offers "a starting value given for this material" only when one
    is given.
* **F2:** notes are rows with their icon and no bullet. **F3:** Inputs use the fields'
  grid, symbol, label, value, unit, with the source after them.
* **"Muted" is smaller text,** for the Sources line and the inputs' sources: slate is
  3.85:1 on white, under 4.5:1 for text, and palette.md keeps it off words.
* **Not changed:** a domain's `Fact` (2b.7b) still fills positional `{}` fields; moving
  it to named fields belongs with ADR-0020's string sweep.

### 2026-10-17: review findings, and the docs (k5)

From UI/UX & Design's reviews of k2b and k3:
* **k2b M1, focus on an outlined input (WCAG 2.4.7).** An input's note or error outline
  is a style sheet border, which replaces the native frame and its focus indicator, and a
  `QLineEdit:focus` rule would hide the outline while focused. So one `FocusRing` per
  window (`gui/focus_ring.py`) follows the keyboard focus and draws the result fields'
  ring, `focus_ring`, 2 px, 1 px gap, outside an input marked `OUTLINED`, and ignores
  the mouse. The window owns it; while it rings an input it's a child of that input's
  parent, so it scrolls and clips with the input, and it goes back to the window when
  that parent goes (as amended in k6). One helper in `gui/window.py` sets every outline
  and its mark, and the ring refreshes after outlines change.
* **k2b L1, L3–L6:** the stale "focus rings" wording on amber is gone from palette.toml
  and palette.md; palette.md says `outline_error` equals `outline_limit` on purpose; the
  ΔE test adds the hover border role, read from `ui_style`; the doc-quote test runs both
  ways; and the design doc keeps the device-pixel rule to the painted fields, since a
  style sheet draws an input's outline.
* **k3 L1:** the "Results" title is `title_scale` (1.2) times the body text, the size Qt
  gives the document's `<h3>`; a test compares the two.
* **k3 L2:** the document's background is the fields' `fill_role` in both themes.
* **k3 L3:** a dashed line has flat caps, so its dashes are the pattern's 4 and 2 line
  widths, 8 and 4 px at 100%, not 10 and 2.
* **k3 L4:** the ring's gap and width are each whole device pixels. A result field now
  strokes its ring at its own edge and draws its frame inside the room
  (`painting.frame_within`), which also stops the ring losing a row at its top and left
  at 150%, where 2 px of ring and 1 px of gap need 5 device pixels, not the 4.5 the
  layout keeps.
* **The k3b check:** the window's least height is the least the page shows: the title
  and the method row, with room for one field. With the page scroll, it had fallen to
  112 px.
* **Docs:** the user guide's "Results and copying"; KI-022 for the decimal separator (F5);
  this ADR's status.
* Tests check each fix, and each was checked by removing it: the ring and the outline
  together, the ring following focus and outlines, the title against the document's
  heading, the document's surface in dark, the dashes, the ring at 150%, and the least
  height.

### 2026-10-18: the reviews of k3c–k5, and the width cap (k6)

From Support & Review's verification and UI/UX & Design's reviews of k3c, k4, and k5:
* **The focus ring's lifecycle (S&R k5 H1, M1).** A form rebuilt while the ring showed,
  for example by a change of units, left it holding a deleted input, so every later
  refresh raised and results stopped updating: a stale result on screen.
  * The ring now follows its input's `destroyed` signal, and checks that an input still
    exists before letting it go.
  * `recompute()` refreshes the ring only after the run is shown, in a `finally`, so
    nothing about the ring can stop a run.
  * The window owns the ring, which goes back to the window when an input's parent goes,
    so it's deleted with the window and never outlives it (KI-019's class).
  * Tests: a change of units while the ring shows, then live results; the ring deleted
    with its window, ringing or not; closing with the ring showing, then another window.
* **Notes and copying (S&R k4):**
  * A note's values are filled with their number and unit only, never the "(≈ 3/64")"
    fraction, which broke the sentence; the result fields show it. The budget test reads
    them the same way.
  * A note's fields are names alone: a format (`{R:.2f}`) or a conversion (`{R!r}`) is
    refused, since values are filled as text.
  * Copy all's formula guard looks past any whitespace, and also guards a leading `"`.
* **What people see (UI/UX k4):**
  * Sources are at the body's size, set apart by colour: the text role at
    `secondary_text_opacity` 0.70, #646662 on white (5.80:1) and #BCBEBC on ink
    (8.32:1). That also fixes their 2 px baseline lift, and corrects F1's "muted".
  * A field's copy button paints without the style's focus state, so the field's ring is
    the one focus indicator. Whether a style draws a tool button's focus varies, so the
    test checks the state the button hands its style.
  * Tab goes on from Copy all to the document, and the page's scroll area, which showed
    no focus, is no longer a Tab stop.
  * The status message has its own duration, `copied_status_ms` (4 s), long enough to
    read; the check stays at `copied_ms`.
  * A copy button's description is the value alone, "BA: 0.3119 inches", so the label
    isn't said twice.
* **The width cap,** approved by the maintainer on 2026-10-18 ("Approve all"): the
  panel's width is capped at `panel_max_width`, 800 px, about its width at the default
  1100 × 720 window, where it's 798 px, so nothing changes there. In a wider page it's
  centred. A test checks both.
* **Docs:** the user page takes UI/UX's edits; KI-020 lists the manual checks the tests
  can't make (the Menu key and Shift+F10 on a real Windows window, and a screen reader's
  speech); the k5 amendment above names what owns the ring, and no private name.
