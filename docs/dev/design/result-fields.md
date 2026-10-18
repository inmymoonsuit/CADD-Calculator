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
* A copy button with the Tabler "copy" icon, which shows a "check" for a moment once
  it has copied.
* Lines follow the welcome screen's rule: whole device pixels, never under one.

## States

* **Hover:** the border takes the text colour, and the field a faint fill of it.
* **Keyboard focus:** a 2 px ring in `focus_ring`, `focus_blue`, outside the frame with
  a 1 px gap. Focus is never an outline colour, so it never looks like a warning; a test
  keeps it at least ΔE2000 15 from every outline and border role, and 3:1 against the
  background in both themes.
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
heavier than the border.

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
| `result_field.hover_border_role` | text | The border's role on hover |
| `result_field.hover_fill_role` | text | The hover fill's role |
| `result_field.hover_fill_opacity` | 0.04 | ... at this opacity, painted at paint time |
| `result_field.focus_role` | focus_ring | The keyboard focus ring's role |
| `result_field.focus_width` | 2 | Its width |
| `result_field.focus_gap` | 1 | Between the frame and the ring |
| `result_field.copied_ms` | 1500 | How long the copied check shows, in milliseconds |
| `result_field.value_weight` | bold | The value's weight |
| `result_field.tabular_figures` | true | Digits of one width, so columns line up |
| `result_field.decimal_align` | true | Align the values on their decimal points |
| `result_field.document_min_height` | 160 | The height the document under the panel always keeps |
| `result_field.copy_icon` | copy | The copy button's icon |
| `result_field.copied_icon` | check | Its icon once it has copied |
| `note_outline.width` | 2 | Every note outline's width, on input and result fields |
| `note_outline.limit_role` | outline_limit | A cited limit is exceeded |
| `note_outline.limit_style` | solid | Its line |
| `note_outline.note_role` | outline_note | A warning, or an impossibility |
| `note_outline.note_style` | solid | Its line |
| `note_outline.no_value_role` | outline_no_value | No reference value could check it |
| `note_outline.no_value_style` | dashed | Its line: dashed reads as "unchecked" |
| `note_outline.error_role` | outline_error | An input whose text can't be read |
| `note_outline.error_style` | solid | Its line |
