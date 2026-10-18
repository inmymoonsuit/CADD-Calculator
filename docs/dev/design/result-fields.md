# Result fields: design tokens

A calculator's results show as **result fields**: one boxed, copyable field per output,
in a Results panel above the document of notes, inputs, and work (ADR-0017). Every
calculator, plugins included, gets them from one component and one style. Every size,
colour role, and state they use is a token in `src/caddcalc/gui/assets/ui_style.toml`,
read and checked by `caddcalc.gui.ui_style` on the core every token file shares
(`caddcalc.gui.style_tokens`, ADR-0016). A test checks that this page still quotes each
token, so the specification can't drift from the code.

## The field

```
┌──────────────────────────────────────────────────────────────────┐
│ BA     Bend allowance                         0.3119  in   [⧉]  │
└──────────────────────────────────────────────────────────────────┘
  symbol  label                                  value   unit  copy
```

* A square, 1 px border in `field_border` (slate), on the background.
* The symbol in bold, in a column as wide as the calculator's widest symbol; the label in
  the remaining width, elided with a tooltip when it's too long.
* The value in bold, tabular figures, aligned on the decimal point across the panel, and
  selectable by mouse; the unit beside it, in a column as wide as the widest unit.
* A unit written close up, the degree sign, joins its number, as the document writes it:
  `132.70°`, not `132.70  °`. Its width counts in the decimal alignment, so the points
  still line up.
* A copy button with the Tabler "copy" icon, which shows a "check" for a moment once
  it has copied.
* The field's painted lines (its border, its note outline, and its focus ring) follow the
  welcome screen's rule: whole device pixels, never under one, through `gui/painting.py`.
  An input field's note outline is a style sheet border, which Qt draws, so it isn't held
  to the rule and can look soft at 150%. The focus ring around an outlined input is
  painted, so it is.
* **Spacing as seen.** Each field keeps the focus ring's room, `focus_width` 2 plus
  `focus_gap` 1, inside its edges, so its frame sits 3 px in. Between two frames that
  makes a visible 12 px gap (`stack_gap` 6, plus 3 px on each side), and the frames sit
  a visible 19 px in from the panel's sides (`panel_inset` 16, plus 3). The "Results"
  title is indented the same 3 px, in line with the frames. A test measures both.

## The panel

* `gui/result_fields.py`: a `ResultsPanel` of `ResultField`s, between the inputs and the
  document. The panel is built when the calculator changes, and its values update on
  every recompute, so focus and hover survive typing. While the inputs have no result,
  every field shows "—" at once.
* A field shows its output through `core.formatting.output_parts()`, the one place
  outputs are presented; the CLI and the document use `format_output()` on it. An
  output's own presentation (ADR-0018) will apply there.
* **Results are never obscured.** The panel is always exactly as tall as its title,
  every field and the disclaimer, and has no scroll bar of its own.
* **The disclaimer is its last line** (ADR-0021 §7), aligned with the frames,
  word-wrapped, in the secondary text. It's safety text, so it's never cut off: it wraps
  at any width and in any language, and scrolls with the answers it qualifies. The status
  bar carries only passing messages, such as "Copied …".
* **Its width is capped** at `panel_max_chars`, the page's own cap, so it fills the page
  (ADR-0021 §4). The page sits left-aligned beside the list, up to `page_max_chars`, and a
  wider window adds plain background beyond it.
* The document under the panel starts at Notes, listed strongest first by the outlines'
  ranking: a cited limit, then a warning or an impossibility, then a check that
  couldn't be made. So a short document always opens with the note that matters most.
* **One scroll bar, never a scroll inside a scroll** (`gui/pages.py`):
  * While the page fits the window, the document takes the height that's left, never
    less than `document_min_height`, and scrolls on its own.
  * When the window is too short for the inputs, every field, and the document's least
    height, the page scrolls as a whole: title, options, inputs, results, and document,
    vertically only. The document then shows at its full height, with no scroll bar of
    its own, so the wheel over it scrolls the page.
  * The page is never narrower than its content, and a family page isn't made to
    scroll by the calculator page hidden behind it.
* The status bar's disclaimer is a widget, so a passing message covers it for a moment
  and it comes back.
* A test keeps layout numbers and colours out of `result_fields.py`, as out of
  `welcome.py`.

## Copying

* **Copy:** a field's button copies its value as shown, without its unit (`0.3119`),
  through `core.formatting.copy_output()`. So does Space, Enter, or the platform's
  Copy keys (Ctrl+C, Cmd+C on macOS) on the focused button. The value copied is the one
  the field shows now: with no result, every button is disabled and nothing copies.
* **The context menu,** by right-click or the Menu key: "Copy value", "Copy with unit"
  (`0.3119 in`), "Copy full precision" (the display unit, unrounded, at most 10
  significant digits), and "Copy fraction" (`5/16"`, or `1-5/16"`), only while a
  fraction shows. It opens as a popup, never a nested event loop.
* **Copy all,** the button beside the title, or Ctrl+Shift+C (Cmd+Shift+C) anywhere in
  the window while a calculator's results show: one tab-separated row per output,
  symbol, label, value, unit, for a spreadsheet. A text cell a spreadsheet would read
  as a formula (`=`, `+`, `-`, `@`, or their full-width forms, after any spaces) gets a
  leading apostrophe; the value never does, so a negative number stays a number
  (OWASP, "CSV Injection").
* **Feedback:** the button's icon becomes a check for `copied_ms`, and nothing else
  moves; the status bar says, for `copied_status_ms`, long enough to read, e.g. "Copied
  BA = 0.3119 to the clipboard"; and screen readers are told the same, politely
  (`QAccessibleAnnouncementEvent`).

## Keyboard and screen readers

* **Tab** goes down the page: the inputs, each field's copy button in output order,
  Copy all, then the document. The page's scroll area is no Tab stop: it would show no
  focus, and Tab scrolls each focused widget into view anyway.
* **One focus indicator:** a field's copy button paints without the style's focus state,
  so the field's ring alone shows its focus. Copy all, which has no ring, keeps the
  style's.
* **Accessible names** are whole sentences with named fields, so they can be translated
  as written, and keep each label as it's written:
  * a field: "Bend allowance, BA: 0.3119 inches", or "…: no value". The unit is said in
    full (`Unit.spoken`), singular only after a shown "1": "1.0000 in" is "1.0000
    inches". A ratio is only its number.
  * its button: "Copy Bend allowance", described by its value, "BA: 0.3119 inches", so
    a screen reader says the value with the button and the label only once
  * Copy all: "Copy all results"
* Every message is a module constant in `result_fields.py`.

## The document under the panel

* **Notes** (F1, F2), strongest first, each marked by its kind's icon with no bullet:
  * the heading and the **lead**: the verdict, with its numbers in the display units
  * the **detail**, if any: what each source gives, stand-in labels, how the check
    decided
  * the **sources**, set smaller
  * `core.formatting.describe_note()` gives these parts, and the CLI prints the same
    three lines, the detail and sources indented under the lead.
* **Inputs** (F3) on the fields' grid: symbol, label, value right-aligned, unit, with
  the source after them, set smaller.
* **Sources are lighter, not smaller:** the Inputs' source column and a note's
  "Sources:" line are at the body's size, in the text role at `secondary_text_opacity`
  over the fill: #646662 on white (5.80:1) and #BCBEBC on ink (8.32:1), both above
  4.5:1, and tested. The palette's muted role, slate, is under 4.5:1 for words, so it's
  never used for them.
* The document has the fields' surface, `fill_role`, in both themes, so in dark it
  matches the fields rather than Qt's lighter text-pane grey. The "Results" title is
  the size of the document's headings (`title_scale`).
* The window can't be shorter than the least the page shows: the title and the method
  row, with room for one field.

## States

* **Hover:** the border takes the text colour, and the field a faint fill of it.
* **Keyboard focus:** a 2 px ring in `focus_ring`, `focus_blue`, outside the frame with
  a 1 px gap. Focus is never an outline colour, so it never looks like a warning; a test
  keeps it at least ΔE2000 15 from every outline and border role, the hover border
  included, and 3:1 against the background in both themes.
  * The ring is at the field's edge and the frame inside its room, each in whole device
    pixels (`gui/painting.py`, `frame_within`), so at 150% the gap is the same on every
    side and the ring is never clipped.
  * **An input a note outlines** gets the same ring, outside its outline
    (`gui/focus_ring.py`): its style sheet border replaces the native focus indicator,
    and a `:focus` rule would hide the outline. Other inputs keep their native focus.
* **A dashed outline** has flat ends, so it reads 8 px on and 4 off at 100%, the
  pattern's four and two line widths.
* **A note concerns it:** the same outline an input field gets, by the same ranking
  (`gui/outlines.py`): a cited limit over a warning over a check that couldn't be made,
  whose outline is dashed. Every note outline is 2 px, heavier than the 1 px border, so
  it reads without its colour (WCAG 1.4.1), on input and result fields alike.
* **No value:** the value shows "—" and the copy button is disabled.

## Design tokens

To restyle the fields, edit `ui_style.toml`; the loader refuses an unknown key, a wrong
type, a value out of range, an inset or padding off the spacing scale (2, 4, 6, 8, 12,
16, 24, 32), a role missing from either theme, and an icon that isn't vendored. It also
refuses a field too short for its button, an icon too big for it, and a note outline no
heavier than the border. The `layout` tokens are in text units (ADR-0021 §1): `ch`, the
body font's average character width (5.5 px at 9 pt Segoe UI), or its line spacings; the
loader refuses a list whose least width is more than its launch width, and a panel wider
than the page.

| Token | Value | Meaning |
|---|---|---|
| `result_field.padding` | 6 × 12 | Inside a field: vertical × horizontal |
| `result_field.gap` | 12 | Between a field's columns |
| `result_field.stack_gap` | 6 | Between fields |
| `result_field.panel_inset` | 12 × 16 | Around the results panel: top × sides |
| `result_field.min_height` | 40 | A field's least height, for a comfortable button |
| `result_field.button_size` | 28 | The copy button's width and height |
| `result_field.icon_size` | 16 | Its icon's size |
| `result_field.border_width` | 1 | A field's border |
| `result_field.border_role` | field_border | Its colour role |
| `result_field.fill_role` | background | A field's surface |
| `result_field.text_role` | text | Its symbol, label, value, and unit; the label differs by weight, not colour |
| `result_field.hover_border_role` | text | The border's role on hover |
| `result_field.hover_fill_role` | text | The hover fill's role |
| `result_field.hover_fill_opacity` | 0.04 | ... at this opacity, painted at paint time |
| `result_field.focus_role` | focus_ring | The keyboard focus ring's role |
| `result_field.focus_width` | 2 | Its width |
| `result_field.focus_gap` | 1 | Between the frame and the ring |
| `result_field.copied_ms` | 1500 | How long the copied check shows, in milliseconds |
| `result_field.copied_status_ms` | 4000 | How long the status bar says what was copied, long enough to read |
| `result_field.value_weight` | bold | The value's weight |
| `result_field.tabular_figures` | true | Digits of one width, so columns line up |
| `result_field.decimal_align` | true | Align the values on their decimal points |
| `result_field.document_min_height` | 96 | The document's least height; below it, the page scrolls |
| `result_field.copy_icon` | copy | The copy button's icon |
| `result_field.copied_icon` | check | Its icon once it has copied |
| `result_field.title_scale` | 1.2 | The "Results" title's size against the body text: the document's headings', so it reads as one of them |
| `result_field.secondary_text_opacity` | 0.7 | Secondary text, such as a value's source, is the text role at this opacity over the fill: #646662 on white (5.80:1) and #BCBEBC on ink (8.32:1) |
| `note_outline.width` | 2 | Every note outline's width, on input and result fields |
| `note_outline.limit_role` | outline_limit | A cited limit is exceeded |
| `note_outline.limit_style` | solid | Its line |
| `note_outline.note_role` | outline_note | A warning, or an impossibility |
| `note_outline.note_style` | solid | Its line |
| `note_outline.no_value_role` | outline_no_value | No reference value could check it |
| `note_outline.no_value_style` | dashed | Its line: dashed reads as "unchecked" |
| `note_outline.error_role` | outline_error | An input whose text can't be read |
| `note_outline.error_style` | solid | Its line |
| `layout.list_width_chars` | 51 | The calculator list's launch width, in `ch` (280 px at 9 pt) |
| `layout.list_min_chars` | 24 | The list's least width (132 px); it never collapses |
| `layout.page_max_chars` | 148 | The page's widest, its scroll bar included (814 px at 9 pt) |
| `layout.panel_max_chars` | 148 | The results panel's widest: the page's, so the panel fills it |
| `layout.launch_lines` | 45 | The launch content height, in line spacings (720 px at 9 pt) |
| `layout.screen_margin` | 16 | Pixels between the window's frame and the screen's work area, at least |
| `layout.right_pane_min_chars` | 58 | A future right-hand pane's least width (ADR-0021 §5); unused until one exists |
| `layout.right_pane_default_chars` | 64 | That pane's width when it opens; unused until one exists |
