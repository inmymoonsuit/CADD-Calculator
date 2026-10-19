# ADR-0024: Units on fields

* **Status:** **Accepted; not built.** UI/UX & Design wrote it, with Calculator
  Engine's sections, on 2026-10-19. Support & Review checked the final CLI and JSON (E5) for correctness: one Medium and three Lows, all folded in.
  * **D1–D6** are the maintainer's design decisions.
  * **D7, arithmetic,** is the maintainer's own decision (2026-10-19): "Let's go with the
    AutoCAD or industry standard meaning then."
  * **D8, the in-field "reads as" echo,** is the maintainer's own decision too
    (2026-10-19): "I like the evaluation echo. That is helpful for a user to see what the
    arithmetic evaluated to."
  * **Q2–Q14 were delegated** (2026-10-19), and are decided on the lanes'
    recommendation: "I'm not sure I am qualified to rule on some of these. Likely you
    and the lanes, with research and based on best practice and industry standards, can
    arrive at sounder decisions than my arbitrary ones."
  * **No backward compatibility in pre-alpha,** in the same message: "we're in pre-alpha
    and really shouldn't care about deprecation or breaking things in a way that in
    concerned with backwards compatibility. Let's just get the better change in place."
    So nothing here is deprecated or kept for compatibility. Old behaviour is replaced
    outright, and the only neutrality tests kept are those that prove correctness.
* **Priority:** the maintainer's words, 2026-10-19: "merge and then let's prioritize this
  planned work in units immediately after … I think fixing this units picking behavior is
  [top] priority after the merge." It's built right after PR #1, and before ADR-0023.
* **Owners:**
  * UI/UX & Design owns this document and everything the user sees.
  * Calculator Engine owns the engine and API sections: declarations, the input
    contract, the parser's role, arithmetic, output conversion, the CLI and JSON,
    plugins, and the engine slices.
* **Builds on:** ADR-0019 (the units registry), ADR-0013 §9 (numeric intent), ADR-0017
  (result fields), ADR-0018 (Conversions), ADR-0020 (localization) and ADR-0023 (the
  layout contract).
* **Measured at:** PR #1's head as of eb74663, natively on Windows 11, Qt 6.12, Segoe UI
  9 pt.
  * The mockup patches the real window's widgets after each page is built
    (`units-study/mockup.py`). No app code was changed.

## Context

* **One window-wide unit.**
  * The window has one Units box (`window.py:468`, in or mm). It sets
    `DisplayPrefs.length_unit` for every calculator.
  * A number typed without a unit is read in that unit (`formatting.entry_unit`), and
    every length, area and stress is shown in it or derived from it.
  * Switching the box keeps each quantity and rewrites the field's number in the new
    unit (ADR-0013 §9's "a unit switch keeps the base value").
* **Units are typed into fields.** A field also accepts a unit in its text: "25 mm",
  `1'-4 3/16"`, "sq in". The registry's parser (ADR-0019 §3) reads the alias and the
  compound forms. So the same field can mean two things, and a typed unit silently
  overrides the box.
* **Conversions shows every unit as a row.** PR #1's Conversions family (ADR-0018 §3)
  takes one value and shows it in every unit of its kind: the Length converter has 12
  rows, which makes it a long page under ADR-0023.
* **The maintainer's view,** 2026-10-19: "I just don't feel the calculators really work as
  they are now."

## The maintainer's decisions (2026-10-19, in their words, lightly trimmed)

| # | Decided |
|---|---|
| D1 | **The units registry stays central.** "I believe it is correct that the application use a centralized units database or registry. But using a common units picker in every calculator is likely a mistake." |
| D2 | **Each input field gets a context-aware units picker after it, and the pickers are the only way to give a unit.** "We would remove the ability to input units and have only the pickers be authors. The user could input numbers or equations, but not units or aliases." |
| D3 | **Outputs: one picker for the whole output of a calculator, as a rule.** "In cases where a group of results are output together, it can be one picker. If the user wants to see multiple units output, it would be simple enough to switch the picked unit for the group. There may be some edge cases where individual outputs need unique pickers, but that can be an exception when needed." |
| D4 | **No global preference until there are saved preferences.** "Once we do, we can have an Imperial vs Metric or other units preferences. For now, we'll just use rational defaults for the calculators." |
| D5 | **Results show in the chosen units, not in every unit.** "Shows the entire output of a given calculator in one unit or one set of units (eg mixed where necessary, maybe IPS, Inches and degrees, cubic inches and radians if a certain calculator needed that combination). But we don't need to show a comprehensive list of every possible unit." |
| D6 | **Calculators are split by unit family and by style.** For example, a fraction-to-decimal converter in the Conversions family: type `3/16`, pick inches, and read the decimal out in a chosen unit such as mm. |
| D7 | **Arithmetic in fields (was Q1): option A, decided 2026-10-19:** "Let's go with the AutoCAD or industry standard meaning then." No prefix: numbers, fractions, mixed numbers, + − × ÷ and parentheses, with no names or functions, evaluated as exact fractions by Engine's own parser (E3). AutoCAD's rule: a hyphen with no space on either side, between a whole number and a proper fraction, joins them, so `1-3/16` is 1 3/16. Any other hyphen is minus. Feet-and-inches and DMS fields take their form's grammar only. **Rejected along the way: segmented fields** (separate boxes for the whole number, numerator and denominator, or for feet and inches, set by the picker), so that a hyphen could only ever mean minus. The maintainer raised it, and agreed against it on PM's four reasons: pasting a CAD value breaks; arithmetic on mixed lengths is lost; typing is slower; and the row reflows when the unit changes. In the maintainer's words: "my proposal was mistaken. And I've used online calculators that forced the separation and it's not a good user experience." Also rejected: B, arithmetic only after "="; and C, numbers and fractions only. |
| D8 | **The "reads as" echo (was Q15), the maintainer's own decision, 2026-10-19:** "I like the evaluation echo. That is helpful for a user to see what the arithmetic evaluated to." Shown inside the field, trailing, in the secondary text colour** (`1-3/16   = 1 3/16 in`). Shown only when the text isn't a plain decimal: a fraction, a mixed number, an expression, a form, or a bare number in an ft-in field (Q2). It's also the field's accessible description ("reads as 1 and 3 sixteenths inches"), so it's spoken on focus. When the field is too narrow for the text and the echo, the echo hides, and stays in the tooltip and the document's Inputs block. Why: D7's hyphen rule makes `1-3/16` and `1 - 3/16` differ by a space, and the echo is where the user sees which was read. Engine's E3 and Q2 already assume one. Measured natively (segment page, 9 pt; renders `units-study/render/echo-*.png`): 0 px of height and width (738 → 738 in en, 754 → 754 in en_XA). The field is 581 px wide at the target and 200 at the least window (en, without pickers). The longest echo, `= 40°30′15.00″`, is 78 px, plus 57 px of typed text (`0.25 - 1/32`). With pickers the least-window field is about 126 px (calculated), so the echo hides there for long texts. Cost: a small overlay label and text margins on each field, in U1; tests for when it shows, its text, its description, and hiding when there's no room. Rejected: An echo on a line under the field, as override notes sit: +22 px for each field that shows one (738 → 760, measured), and the page moves while you type. Or no echo: the document's Inputs block already lists each value as read, but it's out of sight, below the results. |

## Decision

### 1. The input row: a number, then its unit's picker

* **Every input with a unit gets a picker after its field.** That covers calculator
  pages and family settings pages alike: thickness, radius, an angle, a stress. The
  picker takes the place of today's unit label, so the row is `label · field · picker`.
* **The field takes a number, a fraction or a mixed number** (`0.1046`, `3/16`,
  `1 3/16`), and an expression (D7). It never takes a unit or an alias. The
  number is read in the picker's unit.
* **A unitless input has no picker** (the K-factor, a count of sides). Its field ends
  where a picker would begin, so every field on a page ends on the same line, and the
  pickers stand in one column.
  * **The picker column:** every picker on a page is as wide as the widest choice among
    them, measured from the font (`picker_min_chars`, below).
  * The mockup showed why: unequal pickers (68 px for lengths, 64 for angles) leave
    ragged right edges.
* **Forms are choices too.** Feet and inches (`ft-in`) is a choice for a length, and
  degrees-minutes-seconds (`° ′ ″`) for an angle. With `ft-in` picked, the field reads
  feet and inches by the form's grammar (§4 below, and D7).
* **What a picker offers** is its dimension's units and forms, from the registry, in a
  fixed order: inch-pound first (in, ft-in, ft), then SI (mm, cm, m).
  * A param may restrict its list, for example a thickness that never makes sense in
    metres. The restriction is declared, not coded in the GUI.
* **What it shows** (Q3):
  * Closed, the picker shows the symbol: `in`, `ft-in`, `mm`, `°`, `rad`, `ksi`.
  * Open, the list shows the symbol and the name ("mm — millimeters"), translated.
  * Its accessible name is "{field label} unit" ("Material thickness unit"), and its
    value is spoken as the name ("millimeters").

### 2. Switching an input's picker (Q4)

* **A number the user typed is kept and re-read in the new unit.** 25 stays 25, now in
  mm.
  * The picker says what the typed number means, so the usual reason to switch it is
    "I typed 25 but meant millimeters".
  * Conversion is the output picker's job.
  * Switching back is the undo: the number never changed.
* **A value the user didn't type keeps its quantity, and is shown converted:** a
  default, a family value, a course example. 0.1046 in becomes 2.65684 mm. This is
  ADR-0013 §9 rule 2: only the user's own typing is intent, so there's no typed number
  to re-read.
* **Each switch is announced.**
  * A status message and a screen-reader announcement (`QAccessibleAnnouncementEvent`)
    say "Material thickness: 25 now read as millimeters", or "Material thickness:
    shown in millimeters, 2.65684".
  * The results then update as on any edit.

### 3. Pickers that share a dimension (Q6)

* **One picker per field** (the maintainer's default).
* **"Follow until set," decided (Q6).**
  * The first time the user changes a length picker on a calculator, the calculator's
    other length pickers that the user hasn't set follow it.
  * **A field the user has typed a number in is set,** so it never follows: the user
    typed that number in the unit its picker showed. Only fields showing a value the
    user didn't type follow: a default, a family value or a course example. Each keeps
    its quantity and is shown converted.
  * The announcement names only the fields that moved ("Lengths now in millimeters:
    radius, formed view dimension").
  * **It runs once the choice settles:** when the picker loses focus, Enter is pressed,
    or a choice is made in its open list. It doesn't run on each arrow-key step through a
    closed picker. The picker's own field is re-read at each step (§2), which is
    reversible.
  * *Amended 2026-10-19, from UI/UX's review of U1 (H2, M1):* this replaces "each moves
    under §2's rules". That wording made a typed follower re-read its number, so 0.06 in
    became 0.06 mm. It also let the first arrow-key step lead the others.
  * After that, each picker is the user's.
  * A segment drawn in mm then takes one change, not three, with no group control and
    no global preference (D4).

### 4. Paste and typed units (Q5)

* **A unit in the text is refused, and the fix is offered.** Typing or pasting "25 mm"
  into a length field set to inches leaves the field outlined, with the message
  "Units go in the picker. Use 25 mm?" and a button that sets the picker to mm and the
  text to 25.
  * The picker stays the only author (D2), because the user's click sets it.
  * Nothing is silently misread as 25 in.
* **In an `ft-in` field the marks are the form's own punctuation,** so `1'-4 3/16"`
  pastes as is. The picker already says feet and inches, so a mark can't disagree with
  it.
* **A unit of the wrong dimension** ("25 MPa" in a length) is refused with the usual
  "a length is expected" message, and no offer.
* The parser recognizes the unit for the message only (Engine §E2).

### 5. The output picker (Q7)

* **One picker for the calculator's results,** in the results header between the title
  and Copy all: `Results · Show in: [in ▾] · Copy all`. It adds no row.
* **Its choices are sets (Engine E1, `UnitSet`).** By default, one set is generated per
  length choice: `in`, `in, nearest 1/16`, 1/32, 1/64, `ft-in`, `ft`, `mm`, `cm`, `m`.
  * Area is the length's square, stress follows the system (ksi beside inch-pound, MPa
    beside metric), and angle is degrees.
  * A set is labelled by what it names, for the dimensions the calculator outputs:
    `in · ° · in²` on the right triangle, plain `in` on a sheet-metal page.
  * A calculator may declare more sets, such as "Inches and DMS"
    (`{LENGTH: in, ANGLE: dms, AREA: in²}`) for the right triangle. That's how the
    maintainer's "cubic inches and radians" combination is written.
* **Fraction denominators are output choices,** not a separate control: `in, nearest
  1/16`, 1/32 and 1/64. An input needs none, since it reads any fraction typed.
* **The inch-fraction hint `(≈ 5/16")` goes (Q8):** the fractions are choices now.
* **Exceptions (D3):** an output with a fixed unit or form (`Output.unit`, `Output.form`)
  keeps it, and shows its unit in its row as now. An output that must have its own
  picker declares one (`Output.picks`), and it sits in its row in place of the unit.
* **What follows the set:**
  * The fields, Copy value, Copy with unit and Copy all, in its units.
  * Copy full precision stays full precision, in the set's units.
  * Speech: "Flat pattern dimension, FPD: 25.776 millimeters".
  * The Work: the inputs table lists each input as typed, with its unit, and its value
    in the set's units where they differ ("T 0.1046 in = 2.65684 mm"). The steps are
    written in the set's units.
  * Its accessible name is "Results units".

### 6. Defaults (Q9)

* **Each calculator declares its default input units and output set,** in its spec.
* **The rule for a "rational" default:**
  1. The unit its primary cited source states its worked example in. The course's sheet
     metal is in inches, and the Handbook's examples are in inches.
  2. Otherwise inches for lengths, degrees for angles and ksi for stress, since our
     users are US drafters.
  3. A converter's output defaults to the other system's counterpart: in → mm, ft →
     m, in² → mm², ksi → MPa, ° → rad.
* **The output set starts by following the inputs.**
  * While the user hasn't set the output picker, it follows the calculator's length
    inputs when they all share one unit. Otherwise it keeps its declared default.
  * Once set, it's the user's for the session.
  * A converter's output follows the input to its counterpart (in → mm, mm → in) until
    it's set.

### 7. Calculators split by unit family and style (Q10)

| Today (PR #1) | Becomes | Page |
|---|---|---|
| Length converter: 1 input, 12 rows | **Length** (`conversions.length`): one length in, one length out, each with a picker | input [value][picker] → output [value][picker] |
| (the three nearest-fraction rows and their errors) | **Decimal to fraction** (`conversions.decimal_to_fraction`): a length and a fineness (1/16, 1/32 or 1/64) in; the nearest fraction (fixed form `in_64`, which shows any 1/16 or 1/32 exactly) and its signed error out | two inputs, two rows |
| (none) | **Fraction to decimal** (`conversions.fraction_to_decimal`): type `3/16`, pick in, read the decimal in a chosen unit | input [3/16][in] → output [0.1875][in ▾] |
| Angle converter: deg, rad, DMS rows | **Angle**: one in, one out (DMS is a picker form) | as Length |
| Area converter: 5 rows | **Area**: one in, one out | as Length |
| Stress converter: 4 rows | **Stress and pressure**: one in, one out | as Length |
| Geometry and Sheet Metal calculators | unchanged: they compute one thing and aren't unit-specific | pickers only |

* **Fraction to decimal is Length with fraction-first wording.** It shares Length's code,
  and is listed separately because drafters look for it by that name (D6).
* **The ids:** each unit-to-unit converter keeps its id, with input `value` and output
  `value` (E7).
* **The fineness is an input, not a picker choice,** since the error depends on it
  (Q10). It shows as a choice box in the form: `Fineness [1/16 ▾]`.

### 8. Layout and accessibility, under ADR-0023

* **The picker fits the row's existing height.** In the mockup, the input pickers are
  26 px tall, the same as the fields, so input rows add nothing.
* **The output picker sits in the results header.** Measured cost: 2 px on the segment
  page (738 → 740) and 0 on the right triangle (788 → 788). The header is a
  `ReflowLayout`, so at narrow widths the picker moves under the title rather than
  squeezing it.
* **The least width:** at the window's least size (521 px wide in English), nothing
  clips on any of the three pages: the suite's `_clipped` check, and no widget past the
  window's edge. The page's least width is 372 px.
* **en_XA:** the least window is 554–635 px (the page 405–486), and nothing clips. The
  pickers' symbols aren't translated, so the pickers keep their English widths. Only
  "Show in:" and the list's names grow.
* **Tab order:** field, then its picker, down the page. Then the output picker, Copy
  all, and the result fields.
* **Keyboard:** a closed picker takes ↑/↓ to change its choice, and the first letter
  to jump (`m` for mm); Alt+↓ opens it.
* **Tokens (ADR-0023 §6):** `picker_min_chars` (measured: the widest choice on the page,
  so not typed in), and no pixel literal.

### 9. The mockup, measured

* **Renders:** `units-study/render/{segment_flat_length,right_triangle,length}-{en,en_XA}-{target,least}.png`.
  Native and hidden, at 9 pt, at the 1100 × 736 target and at the least window.
* **What was mocked:**
  * The window's Units box is hidden.
  * Each input's unit label is replaced by a picker of its dimension's choices.
  * A "Show in:" picker is added to the results header.
  * For the new Length converter, every row but one is hidden.
* **Method:** the least window height at which the page doesn't scroll, at 1100 px wide
  (ADR-0023's method: a 350 ms settle, resetting to 2400 px before each probe).

| Page | Today | With pickers | Note |
|---|---|---|---|
| Segment (K-factor), en | 738 | 740 | +2, from the header. ADR-0023's slice 1 (A1 and A2 paired) still brings it under 736 |
| Right triangle (two legs), en | 788 | 788 | still long (seven results) |
| Length converter, en | 1016 | **444** | one input, one output: no longer long |
| Segment, en_XA | 754 | 756 | |
| Right triangle, en_XA | 820 | 820 | |
| Length, en_XA | 1048 | 476 | |

* **Pickers:** 26 px tall, like the fields. Closed, 68 px for a length and 64 for an
  angle, at the widest symbol. Equalized to the page's widest under §1.
* **The output picker** is 127 px wide; its longest set, `ft-in · ° · ft²`, needs 82 px
  of text.
* These figures are at eb74663. The right triangle needed 786 at 8410aa8 (ADR-0023's
  table) and 788 here.

## Engine and API (Calculator Engine's sections)

Written by Calculator Engine against PR #1's head c7b1772, and merged here unchanged except for
heading levels. Engine's own D-numbers (not this ADR's D1–D8) map to it as: D1 → D7 (decided), D2 → Q2, D3 → Q4, D4 → Q8,
D5 → Q11, D6 → Q12, D7 → Q10, D8 → Q13. Where it says "UI/UX", the UI sections above apply.

**Pre-alpha, so no compatibility machinery** (the maintainer, through PM, 2026-10-19).
The better design wins over compatibility. Nothing here is deprecated or kept working for a
release: what a slice replaces, it removes.

Facts this rests on, checked in that head:
* No release has been tagged. The Conversions family is under `[Unreleased]` in the
  CHANGELOG.
* Domain settings are `Param`s (`Domain.settings`). No family stores a length preference.
  A settings field reads a bare number in the window's display unit (`entry_unit`) and
  stores a `TypedValue`. So "the family settings that hold a length preference" are these
  fields, and they get pickers as calculator fields do.
* The registry already has every choice the pickers need: units by dimension
  (`units_for`), and the compound forms `ft_in`, `dms`, `in_16`, `in_32` and `in_64`
  (`NearestInches` is output only: it reads nothing).
* `core.expr` has an exact evaluator (`evaluate_exact`, rational arithmetic), but it parses
  with Python's `ast`. That would accept `0x10`, `1_000` and `1j` as numbers, and it has no
  mixed numbers, × or ÷.

### E1. Declarations

**One choice id names what a picker offers:** a unit's key symbol (`in`, `mm`, `deg`,
`MPa`, `in²`) or a compound form's key (`ft_in`, `dms`, `in_16`, `in_32`, `in_64`). These
are the registry's public names already (ADR-0019 §2), so no new list is made.
* The registry answers `entry_choices(dimension)`: the dimension's units, then its forms
  that read input (`ft_in`, `dms`). It also answers `output_choices(dimension)`: the units,
  then every form, `in_16`/`in_32`/`in_64` too. A form declares whether it reads
  (`CompoundForm.reads`).
* Fineness belongs to the form, so a finer feet-and-inches is another registered instance
  with its own key (`ft_in_32`, `ft_in_64`), as `in_16` to `in_64` are now. `ft_in` keeps
  1/16.
* Plugin units appear in every picker of their dimension as soon as they're registered
  (ADR-0019 U2). A plugin can't add a form, as now.

**`Param` gains two fields. `default` stays text with its unit:**
```python
unit: str = ""  # the picker's default choice id; "" = the unit `default` names
units: tuple[str, ...] = ()  # restrict the offered choices; () = entry_choices(dimension)
```
* Most declarations need no change: `"0.1046 in"` already says inches, so the picker
  defaults to inches. `validate_spec` refuses a Param that has more than one choice and no
  resolvable default unit: it has no `unit`, and its default names no unit or there is no
  default. A unitless dimension (a ratio, a count) has its one unnamed unit and shows no
  picker.
* `default` stays parsed by `parse_quantity` (developer text, E2), so defaults, gauge and
  material data, and plugins keep one grammar.

**A calculator declares its output sets, and `Output` gains a per-output exception:**
```python
@dataclass(frozen=True)
class UnitSet:
    key: str  # public, e.g. "in", "mm", "in_dms"
    label: str  # N_("Inches and degrees")
    choices: Mapping[Dimension, str]  # one choice id per dimension its outputs use


class Calculator:
    output_sets: ClassVar[tuple[UnitSet, ...]] = ()  # () = generated (below); [0] = default


class Output:
    picks: tuple[str, ...] = ()  # its own picker, first is the default (the exception)
    # unit / form stay as today: fixed, with no picker
```
* **Generated sets** reuse ADR-0019's display rules. There's one set per length choice
  (`in`, `in_16`, `in_32`, `in_64`, `ft_in`, `ft`, `mm`, `cm`, `m`). In each:
  * area is the length's square, `in²` for every inch form (by `derivation`);
  * stress follows the system (`shown_with`: ksi beside inch-pound, MPa beside metric);
  * angle is degrees;
  * a ratio and a count are plain.

  So **the display rule stops deciding what's shown and becomes the generator of default
  sets.** With the `in` and `mm` sets, every built-in calculator shows exactly what it
  shows today, which is E-3's neutrality test.
* A calculator whose angles matter declares its own sets. The right triangle could add
  "Inches and DMS" (`{LENGTH: "in", ANGLE: "dms", AREA: "in²"}`). This is how the
  maintainer's "cubic inches and radians" combination is written.
* `validate_spec` checks four things:
  * every set covers every dimension its outputs use, apart from outputs with a fixed unit
    or their own picks;
  * every choice exists for its dimension;
  * set keys are unique;
  * an output gives `picks` or a fixed `unit`/`form`, not both.
* **The rational default** is the first set, plus each Param's default unit. UI/UX's rule
  is the right one: the unit the primary cited source states its example in. On the
  engine's side, the default is simply what the declarations say.

### E2. The engine's input contract

**A field gives the engine a text and a choice id, never a text with a unit.**
```python
TypedValue.read(text, choice, dimension, *, decimal=".") -> TypedValue
```
* **`TypedValue`** keeps `value` (base units, exact parse), `text` (the user's own),
  `decimal`, and `unit`. It gains `choice`, the picked id: a unit symbol, or a form key
  (whose `full_unit` is then `unit`). `explicit_unit` stays for text with a unit (the CLI,
  defaults) and is False for a picked value. ADR-0013 §9's intent tier holds: the value is
  read once, from the user's own text.
* **Reading in a unit:** the text is a number, a fraction or mixed number, or an
  expression (E3). It's evaluated exactly, as a rational in the picked unit. That's rounded
  once to a double in that unit, then multiplied by `unit.factor`, as `parse_quantity`
  does now. So a plain number reads **bit for bit as today**: `0.1046` picked in inches
  equals `parse_quantity("0.1046 in")`.
* **Reading in a form:** the form's own grammar, in a picked mode where the marks are
  optional, since the picker says what the parts are:
  * ft-in: `10-2`, `10-2 3/16`, `10-2-3/16`, `10 2 3/16`, `10'-2 3/16"`, `10'`, and
    `-10-2` (one sign, at the front). Inches are under 12 and feet are whole, as in U3.
    **A bare `10`** is a decision (D2).
  * DMS: `40 30 15`, `40 30 15.5`, `40°30′15″`, `40d30'15"`. Minutes and seconds are in
    [0, 60).
  * There's no arithmetic in a form field: there, `-` and the space separate the parts.
* **A text that names a unit is refused, with its fix.** The text is read once more with
  `parse_quantity_detailed`, only to recognize the unit, and the message says what to do:
  `"3 mm" names a unit: pick mm and type 3`. The rule holds even when the unit is the
  picked one, as in a pasted `1-3/16"` in an inch field, so it stays one rule (the
  maintainer's decision 2). UI/UX words the message.
* **`parse_quantity` and the compound grammar stay as they are.** They're the grammar of
  text with units, used by:
  * Param and Output declarations;
  * gauge and material stated values;
  * the CLI's `NAME=VALUE`;
  * plugins and tests;
  * paste recognition.

  ADR-0019 §3's identity test keeps holding them. Nothing in the GUI reads a field
  through them.
* **`DomainSettings.set`** takes a choice in place of its `default_unit`, which goes.

### E3. Arithmetic

Under A (UI/UX's lean, and mine), the field evaluator accepts:
* numbers in `parse_number`'s grammar, including the locale's decimal mark. It reads `1e3`
  and `.5` today, and refuses `1_000`, `inf` and `nan`;
* fractions, `3/16`;
* mixed numbers: `1 3/16`, and the hyphen form `1-3/16`, which `parse_number` reads today,
  with the rule below;
* `+ - * /`, `×`, `÷`, `−` (U+2212), unary minus and plus, and parentheses;
* and nothing else: no names, no functions, no `**`, no `0x`, no `j`.

It's its own small tokenizer and recursive-descent parser, about 100 lines in
`core/units/entry.py`, not Python's `ast`. Arithmetic is exact `Fraction` arithmetic,
rounded once in the picked unit, so `1/3*3` is 1, and `3/16` in inches is 0.1875 in exactly, which the inch's factor makes the double nearest 4.7625 mm to 1e-15 (*amended 2026-10-19:* "exactly 4.7625 mm" contradicted E2's one rounding in the unit, then the factor; see the E-1 amendment). Division by zero
is an InputError, "can't divide by zero". The text's length and nesting are bounded, as
`expr.parse` bounds them.

**The old grammar clash, and what the picker does to it.** The clash is `1-3/16`. AutoCAD
reads it as one and three sixteenths (UNITMODE help, cited in U3), and **our own Copy
writes it** (`CopyForm.FRACTION`: `1-5/16"`). Arithmetic reads it as thirteen sixteenths.

The picker removes the half of the clash that came from units. `1 + 1in` (Parametric
CADD's I-0035) can't be typed, so ADR-0013 §9.5's rule "each term carries its own unit" is
retired as unneeded. The hyphen remains, with three options:
* **A (recommended): arithmetic with no prefix, with AutoCAD's mixed-number rule.**
  * A hyphen with no space on either side, between a whole number and a proper fraction,
    joins them: `1-3/16` is 1 3/16.
  * Every other hyphen is minus: `1 - 3/16` is 13/16, and so are `2-1` and `1-0.1875`.
  * A mixed number binds tighter than any operator, so `2 × 1 3/16` is 2 3/8.

  The field's echo, the value read, shows what was meant. A drafter who types `5-3/4`
  means five and three quarters, as in AutoCAD.
* **B: arithmetic only after a leading `=`.** There's no clash at all: without `=`, the
  number grammar holds (`1-3/16` is a mixed number). It costs one keystroke, as in a
  spreadsheet.
* **C: numbers, fractions and mixed numbers only, for now.**

Under A or B, the CLI gets the same evaluator through `--unit` (E5), and `NAME=VALUE` text
keeps its own grammar.

### E4. Output conversion

**Results stay in base units. Conversion happens only in `core.formatting`, at
presentation.**
* A resolved `ShownUnits` (the chosen set, plus each per-output pick) replaces
  `DisplayPrefs.length_unit`. It's what these take: `output_parts`, `format_output`,
  `copy_output`, `results_tsv`, `spoken_value`, `render_step`, `describe_note`,
  `describe_error` and `result_json`. `DisplayPrefs` keeps how numbers look: decimals per
  dimension, symbols, and the decimal mark.
* **What each carries:**
  * **The result fields, Copy and speech** show each output in its choice; a form shows
    through its `CompoundText`, as now.
  * **Copy all** (`results_tsv`) writes each row in its own choice, with its unit column.
  * **The work:** a step's value and substitutions are in the set's *unit* for the step's
    dimension. A form shows as its `full_unit` (`ft_in` and `in_N` as inches, `dms` as
    degrees), so a line reads `= 2 × 16.1875 in`, never `2 × 1'-4 3/16"`.
  * **The Inputs block:** each input shows in its own field's choice, as typed.
  * **Notes and messages** (Note quantities, method notes) are in the set's unit for their
    dimension. A range error for an input is worded in that input's choice, "T must be at
    most 0.25 in", since that's the unit the user is typing in.
* **The `(≈ 5/16")` inch-fraction hint** shows a second form beside the value, so it goes
  (the maintainer's decision 5). The `in_16` to `in_64` choices replace it (D4).

### E5. The CLI and JSON (public API)

Support & Review reviewed the earlier, compatible version. Its findings about correctness
stand:
* `.` is the only decimal mark in `--unit` (ADR-0020 §4);
* `shown.value` is unrounded;
* `entered` says whether its text named its unit;
* the options are named `--output-set` and `--output-unit`, not `--show`, which reads as
  the `show` subcommand.

**Input: `NAME=VALUE` keeps the unit in its text** (`T=3mm`, `A=90°`, `L=10'-2"`), read by
`parse_quantity`. A script has no picker, so its text has to say its unit, and then it
reads on its own, in a log or a shell history. It's also the grammar declarations and
reference data are already written in.
* **A bare number** reads in the input's default choice (E1). That's the GUI picker's
  default, which `caddcalc show` lists. Every sheet-metal and geometry length defaults to
  inches and every angle to degrees (S&R measured this at c7b1772).
* **`--unit NAME=ID`, repeatable,** reads that input's VALUE as a picked field reads it.
  * It reads in that choice, with the field grammar: ft-in's `10-2`, DMS's `40 30 15`, and
    arithmetic if E3 allows it (`--unit L=ft_in L=10-2`).
  * Its only decimal mark is `.`, as for `NAME=VALUE`, and a comma is refused the same way.
  * Like a field, it refuses a VALUE that names a unit, even the same one, with E2's
    message, so no text can disagree with its `--unit`. A form's own marks are its
    grammar, not a unit: `--unit L=ft_in L=10'-2"` and `--unit A=dms A=40°30′15″` read,
    but `--unit L=in L=3"` is refused (S&R's L1).
  * It's also how a script repeats a GUI entry from JSON's `entered`.
* **Refused, as mistakes:**
  * a `--unit` for an input with no `NAME=VALUE`;
  * two `--unit`s naming the same input;
  * a choice that isn't one of that input's;
  * an `--output-unit` for an output without its own picks.
* **Removed:** `--units` and `--fraction`. With `--fraction` goes the CLI's `(≈ 1/4")`
  hint (D4). The fraction choices replace both: `--output-set in_16`.

**Output:**
* `--output-set SET` picks the calculator's output set by key (`--output-set mm`,
  `--output-set in_16`); the default is the first.
* `--output-unit KEY=ID` sets an output that has its own picks.
* `--decimals` stays.
* `caddcalc show` lists each input's choices and default, and the output sets.

**JSON, a clean schema.** Every value is given twice, in base units and as shown, and
every input that was given keeps its text. The example comes from a real run,
`caddcalc run sheet_metal.bend_allowance --method course T=0.1046 R=0.125 A=90 --json`, on
main at bbca747 (S&R's corpus has sheet metal identical at c7b1772).
* **Captured:** every `base` value, the source, the step's fields, `notes`, and each
  `text` (from the same run's text output).
* **Computed:** each `shown.value`, as `from_base(base, "in")` written by `json.dumps`.
* **Reshaped by hand:** the keys, into schema 1. So the example is illustrative of the
  shape, and E-4's golden is taken from the built code, not from it.

One input, one output and one step are shown; the rest have the same shape:
```json
{
  "schema": 1,
  "calculator": "sheet_metal.bend_allowance",
  "method": "course",
  "output_set": "in",
  "inputs": {
    "thickness": {
      "dimension": "length",
      "base": {"value": 2.65684, "unit": "mm"},
      "shown": {"unit": "in", "value": 0.1046, "text": "0.1046 in"},
      "entered": {"text": "0.1046", "unit": "in", "unit_in_text": false},
      "source": {"kind": "explicit", "label": "", "domain": null, "reference": null}
    }
  },
  "outputs": {
    "bend_allowance": {
      "dimension": "length",
      "base": {"value": 6.6851275999999995, "unit": "mm"},
      "shown": {"unit": "in", "value": 0.263194, "text": "0.2632 in"}
    }
  },
  "steps": [
    {"symbol": "BA", "label": "Bend allowance", "expression": "(0.64*T + 1.57*R)*A/90",
     "note": "", "substitution": null, "expression_unit": null, "stated": null,
     "dimension": "length",
     "base": {"value": 6.6851275999999995, "unit": "mm"},
     "shown": {"unit": "in", "value": 0.263194, "text": "0.2632 in"}}
  ],
  "notes": []
}
```
An output in a form, such as feet and inches for 411.1625 mm (illustrative, not captured),
has `"shown": {"unit":
"in", "form": "ft_in", "value": 16.1875, "text": "1'-4 3/16\"", "copied": "1'4-3/16\""}`.
* **`base`** is the value the engine computed, in the dimension's base unit. It's what a
  script should calculate with. A count's value is an integer, in `base` and in `shown`.
* **`shown`** is what every front end shows.
  * `unit` is what `value` is in. `value` is unrounded (base ÷ factor); `text` is as
    shown, rounded.
  * A form adds `form`, and `copied` (the CAD input form). Its `value` stays in the form's
    full unit: inches for `ft_in` and `in_N`, degrees for `dms`.
  * An input is shown in its own choice. An output is shown in the set's choice or its own
    pick. A step is shown in the set's unit, never a form (E4).
* **`entered`** is there only for an input the run was given, not for a default or a
  setting.
  * It holds the text as typed and the choice it was read in: `unit`, plus `form` for
    `10'-2"` or a `--unit` form.
  * `unit_in_text` says whether the text named that unit, so a script can tell `T=3mm`
    from a bare `T=3`.
* **A note** keeps today's object: `kind`, `text`, `detail`, `references` and `subjects`.
  Its `text` and `detail` are filled as shown, in the set's units, as the window shows
  them, and each of its `quantities` has `dimension`, `base` and `shown`, as a value does.
* **`schema`** numbers the format, so a script can check what it reads. This change makes
  it 1.
* The top-level `output_set` names the set. Per-output picks are in each output's
  `shown.unit`.
* **Where it's built:** `result_json` in `core.formatting`, which knows the shown units,
  from the `Result` and the entries. `Result.to_dict` goes; the CLI's `--json` is its only
  caller in `src`. `InputSource.to_dict` and `Reference.to_dict` stay, and `result_json`
  uses them. `Note.to_dict` gives way to the shown form above, written in `formatting`.
* It closes the roadmap's item "A converter's JSON rows in their own units" (ADR-0018 m2,
  the cloud review's Minor 4).

**The Python API:** `Calculator.run` still takes base units, and `Result` keeps its base
values. `DisplayPrefs.length_unit`, `entry_unit` and `display_unit` are removed; the
formatting functions take a `ShownUnits`.

### E6. What it removes or supersedes

Each item is removed in the slice that replaces it (E8).

| What | Becomes |
|---|---|
| `DisplayPrefs.length_unit` | Removed; `ShownUnits` replaces it (E-3). |
| The window's Units box | Removed (UI/UX). Nothing in the engine reads it. |
| `entry_unit`, `display_unit` | Removed; the field's choice, and `ShownUnits` (E-3). |
| `entry_text`'s rule (own text shown only while it named its unit, or its unit is the display unit) | The field shows its own text, which never names a unit. A value not typed there (inherited, default, derived) shows converted into the field's choice. |
| Settings fields reading in the display unit (ADR-0013 §8–9); `DomainSettings.set`'s `default_unit` | Each setting field has its own picker (settings are Params), and `set` takes the choice (E-5). A calculator field inheriting a family value shows it in the calculator field's choice, converted, since it wasn't typed there. |
| ADR-0019 §2's display rule; ADR-0005's "display follows the length preference" | No longer the rule for what's shown; kept as the generator of default sets (E1). |
| ADR-0013 §9.5, "each term carries its own unit" | Retired: no term can carry a unit. |
| The inch-fraction hint, in the GUI and the CLI; `--fraction`; `--units` | Removed; the `in_N` choices and `--output-set` replace them (D4, E5). |
| `Result.to_dict` and today's JSON shape | Removed; `result_json`'s schema 1 (E-4). |
| The converters' all-units rows | Gone with the split (E7). `Output.unit`/`form` stay for real exceptions. |

**Plugins (ADR-0006):**
* A plugin calculator needs no change to get pickers: its Params' default texts give
  their units, and its outputs get the generated sets.
* A plugin with a Param that has no resolvable default choice, such as a length with a
  bare-number default, now fails `validate_spec`, with a message naming `Param.unit`. It's
  skipped like any bad plugin, and never stops startup.
* Plugin code that formats with `length_unit`, `entry_unit` or `display_unit` moves to
  `ShownUnits`.
* A plugin domain's settings get pickers the same way.

### E7. The splits, from the engine's side

Conversions only, as UI/UX proposes. Geometry and sheet metal keep their ids, keys and
methods.

| Id | Inputs | Outputs | Note |
|---|---|---|---|
| `conversions.length` | `value` (any length choice, ft-in too) | `value` (one output, in the output picker's choice) | `ctx.given`, as now |
| `conversions.fraction_to_decimal` | `value`, picked `in` by default (takes `3/16`, `1 3/16`) | `value`, decimal inches by default | Length's compute with other defaults: a preset, not a new formula |
| `conversions.decimal_to_fraction` | `value` (any length), `fineness` (16, 32 or 64) | `nearest` (fixed form `in_64`, which shows any 1/16 or 1/32 exactly), `error` (signed, in the set's choice) | Today's nearest and error compute, for one fineness |
| `conversions.angle`, `.area`, `.stress` | `value` | `value` | As length |

* **The fineness is an input,** since the error depends on it, and compute can't read a
  presentation choice. That needs a small core addition, `Param.allowed`: a tuple of
  values, shown as a choice. The alternatives are worse (D7):
  * three methods: methods are formulas and sources, not settings;
  * all three fractions computed, with the picker choosing which outputs show: a picker
    would then hide results.
* The output key is `value` in all four unit-to-unit converters, and JSON's `shown.unit`
  (and `form`) says what it's in. CLI: `caddcalc run conversions.length X=3/16in
  --output-set mm`.

### E8. Build slices, the engine's half

Each slice passes the five checks, native and Linux, and is reviewed. Each carries its own
docs: the ADR amendments it makes true (0005, 0013 §9, 0018, 0019 §2), the CHANGELOG, the
user guide, and the engineering log. E-1 and E-2 change nothing a user sees; the others do.

| Slice | Changes | Tests and figures | Mutation-probe targets |
|---|---|---|---|
| **E-1 Entry reader** | `core/units/entry.py`: tokenizer, evaluator (E3's choice), reading in a picked unit and in a picked form, refusal of a unit with its fix. `TypedValue.read`, `TypedValue.choice`. | For every unit-free text in ADR-0019's identity corpus, the picked reading equals `parse_quantity` in that unit, bit for bit. `1-3/16` = 1.1875; `1 - 3/16` = 0.8125; `2 × 1 3/16` = 2.375; `3/16` in = 0.1875 in, 4.7625 mm to 1e-15 (*amended 2026-10-19*, as in E3); `1/3*3` = 1; `10-2` ft-in = 3098.8 mm; `40 30 15` = 40.504166…°; `1e3` = 1000, as today. Refused: `0x10`, `1_0`, `1j`, `3 mm`, `5'9` in a plain field, `1/0`. | the mixed-number binding; the no-space hyphen rule; rounding once (rational, then one double); the sign at the front only; inches under 12; the unit refusal |
| **E-2 Declarations** | `entry_choices`, `output_choices`, `CompoundForm.reads`, `ft_in_32` and `ft_in_64`; `Param.unit` and `units`; `UnitSet`, `Calculator.output_sets` and the generated sets; `Output.picks`; the `validate_spec` rules, which refuse a plugin Param with no resolvable default choice. | Every built-in resolves a default for every Param. Each rule refuses a bad declaration. The generated `in` and `mm` sets equal today's `display_unit` for every dimension. | set coverage; the default-unit resolution; `picks` exclusive with `unit`/`form`; area following length in every inch form |
| **E-3 Presentation** | `ShownUnits` through `core.formatting`: fields, Copy, Copy all, speech, work, notes, errors. `DisplayPrefs.length_unit`, `entry_unit` and `display_unit` removed. | **Neutrality:** for every built-in calculator × method × the `in` and `mm` sets, every shown, copied, spoken and TSV text equals today's under `DisplayPrefs(length_unit=…)`, captured from c7b1772 as a golden before the field is removed. New: the `ft_in`, `in_16` and `dms` sets show their forms; work lines are in the full unit; an input's range error is in its choice. | a form in work lines; per-output picks over the set; the range error's unit; area following an inch form |
| **E-4 CLI and JSON** | `--unit`, `--output-set`, `--output-unit` and the refusals; `--units`, `--fraction` and the hint removed; `result_json` and schema 1; `Result.to_dict` removed, and the about ten test files that use it move to `result_json` or to `Result`'s fields; amendments to ADR-0013 (its "`Result.to_dict()` includes the source of every input") and ADR-0014's `to_dict` mentions; `caddcalc show` lists choices and sets. | **A schema test:** for every built-in × method, every key E5 lists is present with its type, with `entered` only for given inputs, and `form` and `copied` only with a form. **Golden values in the new shape:** the published examples' figures (`test_published_examples`) as `base` and `shown`, and a form's `copied`. **S&R's CLI corpus as a correctness baseline:** 434 sheet-metal invocations, 114 of them `--json`. Its `clidiff` scripts live in a temporary scratchpad, so they're copied into the project's test tooling or regenerated. Its calls are rewritten keeping their meaning (S&R's M1): `--units in` becomes `--output-set in`, and `--units mm` becomes `--output-set mm` plus "mm" on each bare length value, since `--units mm` also read bare lengths in mm (8 of its 106 `--units mm` cases are bare-number `--json` runs). Angles and ratios need nothing; it has no `--fraction` calls. Then every `base` value must equal c7b1772's. `--unit` refuses a comma and a unit outside its form's grammar. | `base` unrounded; `shown.value` unrounded, `text` rounded; `unit_in_text`; a form's full unit; each refusal |
| **E-5 Settings** | `DomainSettings` stores the choice; `set`'s `default_unit` removed; an inherited value is shown in the calculator field's choice. | A setting typed in mm and inherited by a field picked in inches shows converted, and runs with the same base value (§9). Applied gauge values keep their source. | conversion rather than re-reading; the stored choice surviving a rebuild |
| **E-6 Converter splits** | E7's six calculators, `Param.allowed`. | Every figure PR #1's converter tests hold, through the new shape: 1 in = 25.4 mm, 1 ft² = 92 903.04 mm², 1 psi = 6.89476 kPa, 1 rad = 57.2958°; 1'-11 63/64" at 1/16 → 2'-0"; 3/32 → 1/8 and 7/32 → 1/4 (half to even); the odd-1/128 sweep to 4 ft, either sign, typed in inches and in mm; a value that is exactly its fraction has error 0. The SP 811 examples stay VERIFIED. | the fineness reaching compute; the error's sign; half to even |

**Order with the GUI slices** (UI/UX names its own):
1. E-1 and E-2 first, in either order, then the GUI's field pickers.
2. E-3, then the GUI's output picker and the Units box's removal.
3. E-4 needs only E-3, so it can run beside the GUI's slices.
4. E-5 with the settings page's pickers.
5. E-6 with the converter pages.

There's no removal slice: each slice removes what it replaces. ADR-0024 comes before
ADR-0023, as UI/UX says.

## Decisions delegated to the lanes (Q2–Q14)

The maintainer delegated these on 2026-10-19 (see Status), so each is **decided on the
lanes' recommendation**. They're merged from UI/UX's and Engine's items, with no
duplicates. Q1, arithmetic, and Q15, the echo, are the maintainer's own decisions: D7 and D8. The alternatives are
kept for the record.

| # | Question | Decided | Alternatives |
|---|---|---|---|
| Q2 | **A bare number in an ft-in field** (`10`) | **Inches,** as AutoCAD reads it. The field's echo shows `0'-10"`. | Feet. |
| Q3 | **What a picker shows** | **The symbol when closed** (`in`, `ft-in`, `mm`, `°`). **The symbol and the translated name in the open list.** The accessible name is "{label} unit", and the value is spoken as the name. Symbols aren't translated, so the picker column keeps its width in every language. | Names when closed: wider, and they grow with translation (+40% in en_XA). |
| Q4 | **Switching an input's picker after typing** | **The user's own number is re-read** (25 stays 25, now mm), as Windows Calculator does; the picker says what the text means. **A value the user didn't type keeps its quantity and is shown converted** (a default, family value or course example; ADR-0013 §9). Switching back is the undo. Each switch is announced. | Always convert, keeping the quantity, as today's Units box and CAD's document units do: then "I meant mm" takes a retype. |
| Q5 | **A unit typed or pasted into a field** | **Refuse, and offer the fix:** "Units go in the picker. Use 25 mm?", with a button that sets the picker and the number. The user's click is the author (D2). In an ft-in or DMS field, the marks (`'` `"`, `°` `′` `″`) are accepted as the form's own punctuation. | Strip the unit and set the picker silently: convenient, but the text becomes an author, against D2. Or refuse with no offer. (Stripping it and keeping the picker is rejected outright: 25 mm would read as 25 in.) |
| Q6 | **Several lengths on one calculator** | **One picker per field, with "follow until set":** the first change to a length picker carries to the calculator's other length pickers the user hasn't set, announced by name. | Strictly per field: three changes to enter a segment in mm. Or group pickers: a new control, against the per-field default. |
| Q7 | **The output picker** | **One picker in the results header, choosing a set:** one generated per length choice (`in`, `in, nearest 1/16`, 1/32, 1/64, `ft-in`, `ft`, `mm`, `cm`, `m`). Area is the square; stress follows the system (ksi or MPa); angle is degrees. A calculator may declare more sets, such as "Inches and DMS" for the right triangle. A per-output picker is the declared exception (`Output.picks`). | A picker per dimension in the header ("Length [in] Angle [°]"): two or three controls, and no default pairing. Or a picker per output, which D3 rules out as the norm. |
| Q8 | **The inch-fraction hint** (`(≈ 5/16")`) | **Retired everywhere, the GUI and the CLI.** `in, nearest 1/16` (1/32, 1/64) are output choices (D5): the output picker in the GUI, and `--output-set in_16` in the CLI. `--fraction` is removed (Q11). | Keep the hint beside decimal inches. |
| Q9 | **Defaults** | **The unit the calculator's primary cited source states its worked example in; otherwise in, ° and ksi; converters default to the other system** (in → mm, ksi → MPa, ° → rad). The output set follows the length inputs while they share one unit and the user hasn't set it. | An output independent of the inputs: an mm segment would show inches until set. Or always inches. |
| Q10 | **Splitting the converters** | **Length, Fraction to decimal, Decimal to fraction, Angle, Area and Stress,** each one in and one out, with pickers. Fraction to decimal is Length's compute with fraction-first defaults. **Decimal to fraction takes its fineness (1/16, 1/32, 1/64) as an input** (`Param.allowed`), since its error depends on it, and shows the nearest fraction and its signed error: two rows. | Decimal to fraction with all three fractions and errors (six rows, as today). Or three methods: wrong, since methods are formulas and sources. Or keep one Length converter whose output picker includes the fractions: fewer entries, but D6 asks for the split by style. |
| Q11 | **The CLI** | **NAME=VALUE keeps its unit in the text** (`T=3mm`, `A=90°`, `L=10'-2"`): a script has no picker, so its text has to say its unit, and it then reads on its own in a log. A bare number reads in the input's default choice, which `caddcalc show` lists (inches and degrees for every sheet-metal and geometry input). **`--unit NAME=ID`** reads that input in a picked choice, with the field grammar and arithmetic (D7), "." as the only decimal mark, and refuses any unit named in the VALUE. **`--output-set SET`** and **`--output-unit KEY=ID`** choose the outputs' units. **Refused, as mistakes:** a `--unit` with no NAME=VALUE, two `--unit`s for one input, a choice that isn't the input's, and an `--output-unit` on an output without picks. **`--units` and `--fraction` are removed** (pre-alpha). S&R checks correctness (E5). | A number plus `--unit` only, with no unit in the text: one grammar, but a script's line no longer says its unit. Or `--units`/`--fraction` kept and deprecated: ruled out by the pre-alpha rule. |
| Q12 | **JSON** | **A clean schema 1** (E5). Every input, output and step has `dimension`, `base {value, unit}` (what a script calculates with) and `shown {unit, value, text}`: `value` is unrounded, `text` as shown, and a form adds `form` and `copied`. A given input adds `entered {text, unit[, form], unit_in_text}`. The top level has `schema` and `output_set`. It's built by `formatting.result_json`; `Result.to_dict` and today's shape go. This closes the roadmap's "converter JSON rows in their own units". | Additive keys on today's shape: ruled out by the pre-alpha rule. Or values in the shown units only: a script would have to know every unit to calculate. |
| Q13 | **Facts on a settings page** (gauge thickness and the like) | **In the unit their source states,** with no picker: they're cited facts, not results. | A picker for the page. |
| Q14 | **PR #1's Conversions until they're rebuilt** | **Leave them as merged until slice U3/E-6.** They work, and Length scrolls under PR #1's interim long-page list. | Hide the family until then: users lose working converters for a few slices. |

## The build plan

**It starts right after PR #1 merges** (expected on main as PR #1's head c7b1772 or later),
and goes before ADR-0023. Each slice is one PR. Each passes the five checks, natively and
on Linux, and is reviewed. Each adds an "as built" amendment here with its figures.

| Order | Slice | Owner | Needs | What the user sees |
|---|---|---|---|---|
| 1 | E-1 Entry reader | Engine | PR #1 merged | nothing yet |
| 1 | E-2 Declarations | Engine | PR #1 merged | nothing yet |
| 2 | U1 Input pickers and the echo on calculator pages | UI | E-1, E-2 | pickers and the echo on inputs; the Units box still sets the results |
| 3 | E-3 Presentation (`ShownUnits`, neutral) | Engine | E-2 | nothing: the neutrality test |
| 4 | U2 Output picker, no Units box | UI | E-3, U1 | "Show in:" on every results header |
| 4 | E-4 CLI and JSON | Engine | E-3 | the CLI's unit options and the new JSON schema (S&R confirms correctness) |
| 5 | E-5 + U2b Settings-page pickers | both | U2 | pickers on family settings |
| 6 | E-6 + U3 Converters rebuilt and split | both | U2 | six short converters |
| 7 | U4 ADR notes and the glossary | UI | all | the glossary's new terms |
| then | ADR-0023's slices 1–6, in their own order | UI | U4 | the layout contract |

* **Engine's slices** are specified in §E8 above: what each changes, its tests, its figures
  and its mutation-probe targets.
* **Each slice removes what it replaces, and carries its own docs:** the user guide, the
  CHANGELOG, the engineering log, and the ADR amendments it makes true. There's no
  removal slice and nothing is deprecated (pre-alpha).
* **UI's slices** follow. "Native only" figures are checked by UI/UX's native review;
  everything else runs offscreen in CI.

### Slice U1: input pickers on calculator pages (after E-1 and E-2)

* **What it changes:**
  * `window.py`:
    * The Units box stays until U2. Until then it sets only how results are shown.
    * `_build_form` puts a `UnitPicker` (a `QComboBox` subclass in
      `gui/unit_picker.py`) after each field that has a unit, in place of the unit
      label. Unitless fields get none.
    * The picker column is equalized per page to `picker_min_chars`: the widest choice's
      symbol, measured.
  * **The picker's choices** come from `entry_choices(dimension)` (Engine E1), restricted
    by `Param.units`, in §1's
    order. Each item's text is the symbol, with the translated name as its tooltip and
    in the open list. The accessible name is "{label} unit".
  * **Switching (Q4):** a typed number is re-read; a value the user didn't type is
    converted. The field reads through `TypedValue.read(text, choice, …)` (E2). A status message and a
    `QAccessibleAnnouncementEvent` announce it.
  * **Follow until set (Q6):** per calculator, per dimension, for the session, held in
    the window's state beside `pending_fields`.
  * **A unit in the text (Q5):** a refusal with the message and a "Use 25 mm" button
    in the field's note area. The ft-in field accepts the marks.
  * **The echo (D8):** a trailing label inside the field (`setTextMargins` plus an
    overlay `QLabel` in the secondary text role), showing "= 1 3/16 in" while the text
    isn't a plain decimal. The same text is the field's accessible description. It hides
    when the typed text and the echo don't both fit, and stays in the tooltip.
  * Tab order: field → picker, through `_chain_tabs`.
* **Tests:**
  * every unit-bearing input has a picker, and every unitless one has none
  * the pickers on a page share one width, which holds the widest choice in en and
    en_XA
  * switching re-reads typed text and converts a default, a family value and a course
    example; switching back restores
  * the announcement's text
  * follow-until-set: the first change carries to the untouched pickers only
  * "25 mm" in an inch field is refused and offers mm, and the button sets the picker
    and the text
  * `1'-4 3/16"` in an ft-in field reads as 16.1875 in
  * the echo: `1-3/16` shows "= 1 3/16 in", `1 - 3/16` shows "= 0.8125 in" (D7), and a
    bare `10` in ft-in shows "= 0'-10\"" (Q2). A plain decimal shows none. The
    accessible description matches. The echo hides when it doesn't fit
  * "25 MPa" in a length field is refused with no offer
  * the accessible names; Tab goes field → picker
  * `_clipped` is empty at the least window and the target, in en and en_XA, on every
    built-in page
* **The figures it must reproduce:**
  * **Native only:**
    * pickers 26 px tall, like the fields; the echo adds 0 px of height and width (738 → 738 on the segment page)
    * at the least window (about 521 px in English), nothing clips
    * no page's need grows by more than 2 px over ADR-0023's table, apart from the
      header's
  * **Offscreen:** the structural and behavioural tests above.

### Slice U2: the output picker, and no Units box (after E-3)

* **What it changes:**
  * `window.py`: the Units box, its label, its 16 px spacing and `_on_units_changed`
    go (and with them ADR-0023's `options_gap`).
  * `result_fields.ResultsPanel`'s header becomes a `ReflowLayout` holding title,
    "Show in:", the picker and Copy all.
  * The picker's sets come from the calculator's declaration (Engine E1).
  * The fields, Copy value, Copy with unit, Copy all, speech and the Work are written
    in the chosen set (through E-3's `ShownUnits`).
  * The set follows the inputs until set (Q9).
  * A fixed-unit output keeps its unit. A declared per-output picker sits in its row.
* **Tests:**
  * the set changes every field's unit, its copy, its speech and the Work together
  * follow-until-set for the output
  * a fixed-unit output ignores the set
  * the picker's accessible name is "Results units"
  * at the least width, the picker moves under the title and nothing clips
  * Copy all writes each row's unit in its unit column
  * no Units box exists, and `_on_units_changed` is gone (E-3 removed `DisplayPrefs.length_unit`)
  * the `(≈ 5/16")` hint is gone (Q8)
  * changing the method never moves the output picker (ADR-0023's invariant, moved)
* **The figures it must reproduce:**
  * **Native only:** the header costs at most 2 px (the segment, 738 → 740), and the
    output picker is 26 px tall.
  * **Offscreen:** the tests above.

### Slice U2b: settings-page pickers (with E-5)

* **What it changes:**
  * Each family settings field gets a picker, as on calculator pages.
  * A calculator field that inherits a family value shows it converted into its own
    choice.
  * Cited facts on the page keep their source's unit (Q13).
* **Tests:** a setting typed in mm and inherited by a field picked in inches shows the
  value converted, with the same base value. The settings form's pickers have their
  accessible names, and nothing clips in en_XA at the least window.
* **The figures it must reproduce:** **native only:** the settings page doesn't scroll
  sideways at the least window (ADR-0021 §7).

### Slice U3: the converters, rebuilt and split (with E-6)

* **What it changes:**
  * Conversions becomes Length, Fraction to decimal, Decimal to fraction, Angle, Area
    and Stress (§7, Q10): Engine E3's calculators, with U1's and U2's pickers.
  * PR #1's interim `LONG_PAGES` loses `conversions.length`.
  * The user guide's `conversions.md` is rewritten.
* **Tests:**
  * each converter has one input with a picker, and one output with the output picker
    (Decimal to fraction: a fineness input and two rows)
  * 3/16 in → 0.1875 in, and 4.7625 mm to 1e-15 (E3, as amended)
  * 0.1875 in → 3/16" with an error of 0
  * an angle in DMS → rad
  * Length's need at the target is under 736 px
* **The figures it must reproduce:**
  * **Native only:** Length about 444 px (the mockup), and Decimal to fraction about 528
    (calculated), both under 736.
  * **Offscreen:** the conversion values, exactly as ADR-0018's tests have them.

### Slice U4: ADR notes and the glossary (last)

* Each earlier UI slice carries its own user-guide changes:
  * U1: the pickers, the echo, typed units refused, switching, and follow until set,
    in `calculators.md` and the sheet-metal and geometry guides
  * U2: the output picker
  * U2b: the settings pickers
  * U3: `conversions.md`
* U4 is the last pass:
  * the glossary gains "unit picker", "output units" and "reads as"
  * the "What this supersedes" notes that no earlier slice made land: ADR-0013 §8, 0017
    §4–5, and ADR-0023's amendment
  * a read-through of the guides for consistency across the slices
* **Test:** the docs' link and term checks pass, and no guide still mentions the Units
  box, a typed unit in a field, or `--units` or `--fraction`.

## Reconciling ADR-0023 (the layout contract)

**ADR-0024 is built first.** ADR-0023's slices follow it, in their own order. What
changes for ADR-0023 goes in its dated note (below):

* **Length stops being long.** It needs 444 px with one output, so ADR-0023's
  `long_page` list is the right triangle only. Decimal to fraction (two inputs, two rows)
  needs about 444 + 32 + 52 = 528, calculated, so it fits.
* **The budget figures move by the header's 0–2 px.** The cone (726, 10 px under) is
  still the tightest. The budget test measures the real pages, so no figure is typed in.
* **ADR-0023's slice 1 (paired rows) still holds.** A paired row's sub-fields each get
  their picker: `End 1 (A1) [90] [° ▾]   End 2 (A2) [0] [° ▾]`. At the least width, the
  pair stacks.
* **The Units-box invariant becomes the pickers'.** ADR-0023 §3's "changing method never
  moves the Units box" becomes "changing method never moves the output picker".
* **Tokens:** `picker_min_chars` (measured) joins ADR-0023 §6. `options_gap` (16, the
  space before the Units box) goes with the box, so slice 3's `addSpacing(16)` fix
  disappears.
* **Its test matrix** (slice 5) gains the pickers: their accessible names, the Tab
  order, and no clipping of the picker column in en_XA.

**ADR-0023's dated note** is its amendment "2026-10-19: ADR-0024 (units on fields) is built
first". It covers the order, long pages (the right triangle only), the Units box and
`options_gap`, the invariant moved to the output picker, `picker_min_chars`, the paired
rows' pickers, the budget's 0–2 px, and the matrix's additions.

## What this supersedes

| ADR and section | Superseded | The note |
|---|---|---|
| ADR-0013 §8, GUI | "switching units"; "on a unit switch, a bare number in it gains the unit it was typed in ('5' becomes '5 in')" | "Superseded by ADR-0024: there's no window-wide unit switch. Each field has its own picker, and switching it re-reads a typed number (ADR-0024 §2)." |
| ADR-0013 §9, rule 3 | "A field shows the user's own spelling while it names its unit or its unit is the display unit" | "A field holds a number only; its unit is its picker (ADR-0024 §1). Typed text is still kept beside the value." |
| ADR-0013 §9, rule 5 | "If an input ever accepts expressions, each term carries its own unit" | "Superseded by ADR-0024 D7: no term carries a unit; all are in the picker's unit." |
| ADR-0017 §4 and §5 | Copy, Copy all and the spoken text in "the display unit" | "In the output picker's set (ADR-0024 §5)." |
| ADR-0018 §3 | "shows the same quantity in every unit of that kind at once"; the converter table | "Superseded by ADR-0024 §7 (D5, D6): one in, one out, each with a picker; Decimal to fraction and Fraction to decimal are their own converters." |
| ADR-0018, amendment m2 | The rows as fixed-unit outputs; "The launch height" paragraph | "The rows go (ADR-0024 §7). Length isn't a long page (ADR-0023's note)." |
| ADR-0019 §2, display rules | "the unit shown for each length choice (LENGTH follows it …)"; `follows_length` | "Display follows the output picker's set, not a length preference (ADR-0024 §5). `follows_length` becomes 'follows the set's length'." |
| ADR-0019 §3, the parser | Its role in GUI fields | "In the GUI it only recognizes a unit, to offer the picker fix (ADR-0024 §4). It still reads declarations, data, the CLI and plugins (Engine §E2)." |
| ADR-0019 U3 | "Input accepts all the common forms" in a field | "In the GUI, the ft-in picker's grammar (ADR-0024 D7); the forms listed stay for the CLI." |
| ADR-0023 §3, §6, §8 | `long_page` on Length; `options_gap`; the Units-box invariant | as in "Reconciling ADR-0023" |
| ADR-0021 §3 | nothing | none: the launch is unchanged |

Engine's §E6 lists what the engine removes or supersedes in code (`DisplayPrefs.length_unit`,
`entry_unit`, `entry_text`'s rule, ADR-0005's display rule, the inch-fraction hint, the
converters' rows) and what it means for plugins (ADR-0006). ADR-0005 gets the note "display
follows the output picker's set (ADR-0024); the length preference is kept as the generator of
default sets", and ADR-0006 the note "a plugin length Param with a bare-number default needs
`Param.unit` (ADR-0024 §E6)".

## Prior art (official documentation, paraphrased; collected 2026-10-19)

* **Every CAD tool surveyed takes units typed into fields, and converts.** This ADR
  departs from them on purpose (D2).
  * **SOLIDWORKS:** a document unit system (IPS, MMGS and others). The Modify box acts
    as a calculator. A unit can be typed, or chosen from a type-ahead list. A leading
    "=" starts an equation, and mixed units show in the document's units.
    (help.solidworks.com: Units options, the Modify dialog, creating equations)
  * **Fusion:** a bare number is read in the active units, and "3 in" is always inches.
    "3/2" is 3 active units divided by 2, and expressions keep their units.
    (help.autodesk.com: the Units and Parameter expression API pages)
  * **Inventor:** document units. Typing 12 mm in an inch file displays 0.472 and keeps
    the typed 12 mm. The suffix `ul` marks a unitless value, and units bind before
    arithmetic. (help.autodesk.com: Inventor Document Settings, Units in edit boxes)
  * **Onshape:** workspace units. Any field takes any unit and converts it, and shows
    the original text again on edit. A unit mixed with a bare number (`3in+2`) is
    invalid. (cad.onshape.com: numeric fields; workspace units)
  * **AutoCAD:** Architectural units. Its feet-and-inches input separates the parts by
    a dash, a space or nothing, so subtraction needs a space. (help.autodesk.com: UNITS,
    and CAL's feet-inch input)
* **What the departure buys:** a field can't mean two things, and arithmetic needs no
  units grammar. AutoCAD's dash-or-subtraction clash is the reason D7 keeps arithmetic
  out of ft-in fields.
* **Converters place a picker beside or under each value, one in and one out:**
  * **Windows Calculator** (the open-source microsoft/calculator, `UnitConverter.xaml`
    and `UnitConverter.cpp`): a value with its unit box under it, twice. **Changing a
    unit keeps the typed number and recalculates**, which is this ADR's Q4. Its pickers are named "Input unit" and "Output unit".
  * **macOS Calculator's Convert mode** (support.apple.com): two fields, each with a
    unit menu beside it, and a Swap Units button.
  * **ConvertWorld:** value, From, a swap button, To and the result, plus a table of
    every unit. That table is the every-unit view D5 drops.
* **Accessibility:**
  * The WAI-ARIA APG combobox pattern (w3.org/WAI/ARIA/apg): a picker needs its own
    accessible name, separate from its value ("Thickness unit, inches"). Tab focuses
    it, and Alt+↓ opens it.
  * WinUI's NumberBox (learn.microsoft.com) evaluates + − × ÷ ^ and parentheses with
    `AcceptsExpression`, which is precedent for D7.
  * Apple's HIG on pop-up buttons asks for a useful default and a label that predicts
    the options.

## Amendments

### 2026-10-19: as built, E-1 and E-2 (with F0)

**E-1, the entry reader** (`core/units/entry.py`, `TypedValue.read`, `TypedValue.choice`):
* `evaluate` is its own tokenizer and recursive-descent parser, in exact `Fraction`
  arithmetic, with D7's mixed-number rule. Two cases the ADR left open are refused,
  as typos: two signs in a row (`--3`, `2--3`; `2*-3` reads), and a whole number
  straight after a fraction's slash, so `1/2 1/4` is two numbers with nothing between
  them, never 1/(2 1/4). A space joins a whole number and any fraction after it,
  `1 5/4` as `parse_number` reads it; a hyphen joins only a proper fraction, so `1-5/4`
  is -1/4.
* Bounds: 200 characters, 50 levels of parentheses and signs, and 100,000 bits for a
  numerator or denominator, checked on each written number before it's built and after
  each operation.
* **Rounding:** as E2 says, the exact value is rounded once to a double in the picked
  unit and then multiplied by its factor, as `parse_quantity` does. So `3/16` in reads as
  4.762499999999999 mm, bit for bit `parse_quantity("3/16 in")`, not the double nearest
  4.7625; E-1's figure "3/16 in = 4.7625 mm" holds to 1e-15. Converting exactly into
  millimetres first would round once less, but every typed value would then differ by
  up to a unit in the last place from today's, and E-3's neutrality would fail.
* **Forms:** feet and inches read with marks optional; a bare number is inches of any
  size (`30` is 2'-6"), and the inches after feet are under 12. A whole number and a
  proper fraction are a mixed number of inches first, so `1-3/16` in an ft-in field is
  1 3/16 in, and `10-2-3/16` is 10'-2 3/16". DMS parts go in order, an unmarked part
  taking the next place (`40°30` is 40°30′); degrees and minutes are whole, and a
  decimal before the seconds is refused with "pick ° for decimal degrees". Both read
  exactly and round once in their full unit. Only the 1/16 feet-and-inches form reads:
  `ft_in_32` and `ft_in_64` are output forms, since a field reads any fraction typed.
* **A unit in the text** raises `UnitInTextError`, an `InputError` that carries the fix
  (`choice`, `number`) for U1's button. It's found in order: a form's marked grammar
  (`1'-4"` → ft-in), a number and the unit ending it (`3 mm`, `1-3/16"` → pick in, type
  `1-3/16`), then a form read with its marks optional (`5'9` → ft-in). A unit of another
  dimension keeps `parse_quantity`'s message, with no offer. A ratio's field has no
  picker, so `44 %` there offers the plain number, 0.44.
* **Figures** (offscreen, `tests/test_entry.py`, 134 tests): the identity corpus's 11
  number forms in each of the 21 units a field takes, and 20,000 random decimals,
  fractions and mixed numbers in in, mm, ft and m, read bit for bit as `parse_quantity`
  reads them. Mutants of the mixed-number binding, the no-space hyphen rule, the proper
  fraction, exact arithmetic, rounding in the unit before the factor, the sign at the
  front (ft-in and arithmetic), inches under 12 and the unit refusal are each killed.

**E-2, the declarations:**
* `UnitRegistry.entry_choices` and `output_choices` order a dimension's units inch-pound,
  then accepted, then SI, each form after its full unit: a length field offers `in,
  ft_in, ft, mm, cm, m`, an angle `deg, dms, arcmin, arcsec, rad`. A ratio and a count
  offer `""` alone. `UnitRegistry.choice` resolves an id; `generated_sets` gives the nine
  sets of §5 (`in, in_16, in_32, in_64, ft_in, ft, mm, cm, m`, by `CompoundForm.sets`).
* `CompoundForm` gains `symbol` (`ft-in`, `° ′ ″`, `in 1/16`, `ft-in 1/32`), `name`
  (marked for translation), `reads`, `sets` and `read`. `FORMS` is ordered so a picker
  lists the nearest-inch forms, then feet and inches, after the inch.
* `Param.unit`, `Param.units`, `Param.choices` and `Param.default_choice`;
  `Output.picks` and `Output.follows_set`; `UnitSet`; `Calculator.output_sets` and
  `Calculator.unit_sets`, whose generated labels name the choices for the dimensions the
  calculator shows (`in · ° · in²` on the right triangle). `validate_spec` checks each
  of E1's rules; it checks a default's value before its picker, so a bad default keeps
  its own message.
* Domain settings have no defaults (ADR-0013), so their pickers' starting choice is
  E-5's, with U2b; E-2 checks calculator parameters only.
* **Figures** (`tests/test_unit_choices.py`, 28 tests): every built-in parameter starts
  its picker in a choice it offers, every sheet-metal and geometry length in inches and
  every angle in degrees; the generated `in`, `mm`, `ft`, `cm` and `m` sets equal today's
  `display_unit` for every dimension; every inch form's area is in². Mutants of set
  coverage, the default-unit resolution, `picks` exclusive with a fixed unit, and the
  inch forms' area are each killed.

E-1 and E-2 change nothing a user sees; the user guide changes with U1.

### 2026-10-19: as built, U1

* `gui/unit_picker.py`: `UnitPicker`, a `QComboBox` whose closed face is the choice's
  symbol (`in`, `ft-in`, `°`, `° ′ ″`) and whose list draws "symbol — name"; its
  accessible name is "{label} unit", and its description and tooltip are the choice's
  name, the plural ("millimeters"). `picked` is emitted on the user's activation only.
  `EchoField`, the field with the echo: a label in the placeholder role inside the
  field's right edge, shown only while the text, a gap of one "X" and the echo fit the
  contents rect; the echo is always in the tooltip, after the help, and is the
  accessible description. `picker_min_chars` measures the widest symbol among a page's
  pickers in widths of "X", and every picker takes it, so they share one width.
* `window.py`: each field is read by `TypedValue.read` in its choice. A field's choice is
  its parameter's default until picked (`field_choices`, per calculator and key, for
  the session). A unitless field has a spacer as wide as the page's pickers, so the
  fields end on one line. Tab goes field → picker → its "Use … value" box. A pick ends
  the page's edits, then re-reads a typed text, pending text included, in the new
  choice, or shows a value the user didn't type converted (`choice_text`,
  `picked_text`). The first pick of a dimension on a calculator carries to its other
  pickers of that dimension that offer the choice and don't show it already
  (`led_dimensions`); before it none of them can be the user's, so no "untouched"
  filter is needed, and a mutant without the once-only guard fails a test with a
  length that defaults to mm. The status bar shows, and `announce` says, "Material
  thickness: 25 now read as millimeters", "…: shown in millimeters, 2.65684", and
  "Lengths now in millimeters: inside bend radius". A `UnitInTextError` shows in the
  field's note area as "Units go in the picker. Use 25 mm?" with a "Use 25 mm" button,
  which picks (as the user's pick, so it leads) and applies the number as typed; a
  unit of another dimension shows the usual message with no offer.
* `core.formatting`: `choice_text`, `picked_text`, `echo` and `Echo`, with `READS_AS`
  marked for translation. The echo of a lone fraction or mixed number is a mixed number
  (`= 1 3/16 in`, said "reads as 1 and 3 sixteenths inches"), of other text its value
  at field precision (`= 0.8125 in`), and of a form the form as shown, unless the text
  is that already. A plain decimal has none.
* A pick shows the fields in their choices in place (`_show_choices`), never by
  rebuilding the form, which would delete the picker while it emits `activated`.
* **For UI/UX:** ↑ and ↓ on a closed picker activate each choice in turn, so the first
  step leads: from `in`, three ↓ presses leave the thickness in mm and the radius, which
  followed the first step, in ft-in.
* The Units box stays until U2 and sets only the results; settings fields keep their
  grammar until U2b (KI-027).
* **Figures, offscreen** (`tests/test_unit_pickers.py`, 44 tests, and the updated page
  tests): every input of every built-in calculator and method has a picker with its
  parameter's choices, starting at its default, and every ratio and count input none;
  the bend's three pickers share one width, wider than their widest symbol, and with the
  K-factor method every field ends at the same x; nothing clips on any calculator page
  at the launch size, in English and en_XA, nor on any page at the least size. A
  settings page is left out of the launch-size check: `_clipped` compares a group box
  with its least height at its least width, where its labels wrap most, so at 1,105 px
  it reports the Sheet Metal settings box, 522 px tall, as short of 543 px, while its
  page scrolls as designed; the same report is on the F0 commit, before any picker.
  Mutants of re-reading, the once-only follow, the fix's offer, the unit's refusal,
  the echo's hiding, Tab to the picker, and the shared width are each killed.
* **Native only, for UI/UX's review:** pickers 26 px tall like the fields; the echo's
  0 px of height and width; nothing clipping at the 521 px least window; and no page
  growing past ADR-0023's table but for the header.

### 2026-10-19: as built, the stop-1 reviews' fixes (U1)

From UI/UX's native review (2 High, 2 Medium, 4 Low) and Support & Review's (3 Low; its
third, the domain settings' default choices, goes with U2b):
* **H1:** `_mixed_size`'s `touch` read past the last token, so `1-` and `12-`, on every
  keystroke path to `1-3/16`, raised IndexError and the error hook's box. It's bounded;
  every prefix of thirteen valid entries, in each choice, reads or is refused, through
  the reader and typed key by key into a field with the error hook watched; and 30,000
  random texts of the grammars' characters raise nothing but a refusal.
* **H2 and M1:** §3 as amended above. `UnitPicker.stepped` is emitted at each ↑/↓ step
  of a closed picker, which re-reads only its own field (`_on_stepped`); `picked` once
  the choice settles, on Enter, focus out, or a choice in the open list, and only when
  it differs from the choice settled before. Followers skip a field the user typed in,
  or has text pending in (`_typed_in`), and the announcement names the fields that moved.
* **M2:** the echo takes `secondary_text` in the scheme shown, recoloured on a palette
  change, not the placeholder role: 5.80:1 on the light fields' surface, at least 4.5:1
  in both schemes (tested).
* **L1:** a picker's face is `sizeFromContents` of the page's widest symbol, with no
  icon's reserve (`picker_text_width`, `UnitPicker.set_text_width`).
* **L2:** a bend angle offers `deg`, `dms` and `rad` (`Param.units`, in sheet metal's
  `bend_angle`).
* **L3:** a text that ends partway through a mixed number, `1 3`, `1 3/`, `1-3/`, says it
  "isn't finished"; `1/2 3` stays two numbers, and `1-3` is a subtraction the echo shows.
* **L4:** "Check the inputs" says the text names a unit; the fix's sentence and button
  are by the field alone.
* **S&R L1:** `parse_number` reads a fraction or mixed number exactly and rounds once,
  so `3 78/100` mm is 3.78, not 3.7800000000000002, and zero has one sign, +0.0, for
  `-0` and `-0/16` alike. The two paths are compared by `float.hex`, over the corpus,
  non-dyadic mixed numbers and zeros, and 20,000 random numbers.
* **S&R L2:** `1-3 /16` and `1-3/ 16` are 13/16, and `1e99999999` is refused in under
  0.5 s.
* Thirteen mutants, one for each of these guards, are each killed; without its bound,
  `1e99999999` outlasts a 60 s timeout.

### 2026-10-19: as built, the cloud review's fixes at stop 1

The cloud review of 6bc88ec asked for changes (2 High, 2 Medium); its H1 and M2 were
UI/UX's H1 and M1, already fixed in 1a0357b. The rest:
* **H1, the window's half:** a pick or a step shows the fields in their choices in a
  `finally`, so a picker and its field's reading never part; typing `1-`, picking mm,
  then typing `2` runs 2 mm, with nothing raised.
* **H2:** "Use …" applies its number as typed in the choice the click set, never as an
  edit judged to end where it began, so `25 mm` pasted into a field already in mm runs
  25 mm; and `1-3/16"`, `45°` and `44 %` the same, each tested.
* **M1:** a default with no unit in its text is in the unit its picker starts in, so
  `default="0.1046", unit="in"` is 0.1046 in; and a default written in a form that reads,
  `1'-4"`, starts the picker in that form.
* **Lows:**
  * **L4:** `parse_quantity`'s feet and inches and DMS read exactly and round once, as a
    picked field does; 20,000 random texts of each read alike by their bits, or are both
    refused (inches after feet read an improper mixed number as its sum on both paths).
  * **L5:** a refusal names the unit as written: `3 μm` names μm, `10 ft-in` names ft-in.
  * **L6:** a calculator whose every output has its own unit, form or picks has no
    output sets.
  * **L7:** unreadable text is announced as "can't be read in", and the follow names
    only the fields shown, though every follower moves.
  * **L8:** a pick sets only the fields whose text changes, so the others keep their undo.
  * **L9:** tests for left-to-right subtraction, one sign in feet and inches, the echo's
    unit, no echo on a plain decimal, and no stale echo.
  * **L3 and L10:** documented in ADR-0019's amendment and KI-026.
* **From the notes:**
  * The minus sign U+2212 is always minus; only a hyphen joins a mixed number.
  * DMS takes `-` between its parts (`40-30-15`), as E2 says, while `40 -30` stays
    refused.
  * An output set's key and label can't be empty.
  * A fix writes `30°`, close up.
  * E3 and E8's "exactly 4.7625" are amended.
* **Low 1 and Low 2,** the ≈ hint's test and its huge-size disagreement, PR #1's Lows 1
  and 3, go with E-4, which removes the hint and `--fraction`.
* Seventeen mutants, one for each of these guards and for each of the review's surviving
  ones, are each killed.


### 2026-10-19: as built, E-3

* **`ShownUnits`** (`core.formatting`) is an output set resolved: a choice for every
  dimension, each output's pick, each input's field choice, and the set's key. It's
  built by `ShownUnits.generated(length)` or `ShownUnits.of(unit_set, picks=…,
  inputs=…)`, which takes a declared set's missing dimensions, such as a note's stress,
  from the generated set for its length; one missing a dimension is refused, and its
  mappings are read-only. `unit(dimension)` is a form's full unit, which the work, notes
  and messages use.
* **What takes it,** after `DisplayPrefs`'s place: `value_parts`, `format_value`,
  `output_parts`, `format_output`, `copy_text`, `copy_output`, `results_tsv`,
  `render_step`, `describe_note`, `method_notes`, `describe_error`, the CLI's
  `format_result`, and the window's results panel and document. `input_parts` and
  `format_input` show an input in its field's choice; `describe_override` takes the
  field's choice, `entry_text` a unit, and `unit_suffix` a unit. `DisplayPrefs.length_unit`,
  `display_unit`, `entry_unit` and `display_value` are removed.
* **Neutrality:** zero differences. The golden is captured at 68e01ee, the head before
  E-3, with its own API, rather than at c7b1772, so F0's declared changes don't count
  (engineering log). It's every built-in calculator and method, in the `in` set with
  "." and "," and the `mm` set, run on the defaults, with each input out of range, and
  with each input scaled by 0.01, 0.1, 10 and 100: 912 runs, 312 of them refused and 60
  with notes. Each output is shown, said and copied in every form but the fraction,
  with the tab-separated rows, the work, the notes, the method's notes, the inputs, the
  CLI's report and each error message. The 240 unscaled runs are held in full text and
  the 672 scaled ones by digest (`tests/test_shown_units_neutral.py`).
* **New, each tested:** the `ft_in` and `in_16` sets show lengths in their forms and areas
  in in²; a declared set shows angles in DMS; the work reads `2 · 8.0938` and
  `16.1875 in` in `ft_in`; a fixed-unit output ignores every set; the Inputs list and a
  range error are in each field's choice, in the window and in `core`.
* **An output with its own picker never follows the set.** Until it's picked, it shows in
  its first pick, as E1's declaration says; a pick it doesn't offer is a `UsageError`.
* **A unit too coarse for its dimension's places declares its own** (`Unit.decimals`):
  the radian, at 4. At the angle's 2 places, 90° picked in rad was listed `1.57 rad`,
  0.01 rad being 0.57°. No generated set has the radian, so neutrality holds.
* **Until U2:** the Units box sets the window's set, `ShownUnits.generated("in")` or
  `("mm")`, and a settings field shows and reads in its unit (KI-027). **Until E-4:**
  `--units` names the CLI's generated set, a bare number reads in its unit, and the
  `(≈ 5/16")` hint stays.
* **Low 3,** the tie window's unit, stays the shown unit: ADR-0019's amendment of this
  date.
* Eleven mutants, one for each guard (the first pick, the refused pick, every
  dimension, read-only mappings, the set by its length, the input's choice, the range
  error's unit, a unit's decimals, the window's field choices, the settings' unit and
  the CLI's bare number), are each killed. Offscreen: 2,251 tests pass.

### 2026-10-19: as built, U2

* **The Units box is gone,** with its label, its 16 px spacing, `_on_units_changed`, and
  the settings page's renaming of unapplied text on a switch (`_name_pending_units`),
  which has no switch left to guard. ADR-0023's `options_gap` was never built, so
  nothing else goes with it. The method row is the page's options row alone.
* **The header** (`ResultsPanel.header`) is a `Reflow` of the title and a row of "Show
  in:", the picker and Copy all, so the row goes under the title when the two don't fit.
  "Show in:" is the picker's buddy; the picker's accessible name is "Results units", and
  it's the panel's first Tab stop, before the copy buttons. A calculator with no sets,
  such as a converter, hides both and drops the stop.
* **The set** is the window's per calculator, for the session (`MainWindow.output_sets`).
  Until one is picked, it's the first set whose length choice every length field of the
  calculator shares, all of them and not only the method's, so a method change can't
  move it; otherwise the first set. A pick is made in the open list or by a step on the
  closed picker: picking a set changes only how values show, so it needs no settle.
* **A per-output picker** is a `UnitPicker` in the field's row, in place of its unit
  label, after its value; the window keeps its pick for the session, and it's in the
  Tab order before its copy button.
* **The Inputs list** adds a column only when some input's field is in another choice than
  the set's: `0.1046 in = 2.6568 mm`, the second value as the results show it.
* **Settings** show and read in the inch set until U2b (`_settings_units`, KI-027).
* **The `(≈ 5/16")` hint** goes with E-4, which removes it from `core.formatting`.
* **Offscreen figures:** the header is 23 px tall at launch, the title's height, so it
  adds nothing; the picker is 23 px. At the least window, 492 × 158, the header stacks,
  at 46 px. Every page that fit at launch still fits, with every method, and its output
  picker never moves. The native figures (at most 2 px, a 26 px picker) are UI/UX's.
* Nine mutants, one for each guard (a pick is the user's, kept, and restored; the follow
  needs one shared choice and counts every length; the picker's Tab stop; its hiding;
  the Inputs list's second value; the settings' inches), are each killed.

### 2026-10-19: as built, E-4

* **Input:** `parse_inputs` returns each given input as a `TypedValue`. A `NAME=VALUE` is
  read by `TypedValue.parse`, a bare number in the input's default choice's unit (a form's
  full unit); a `--unit NAME=ID` input by `TypedValue.read`, the field's reader, with "."
  only. A unit in its text is refused in the CLI's words, "'3mm' names a unit, mm, but
  --unit T=in reads it in in; give the number alone, or drop the --unit", since E2's
  message says "pick". Each refusal E5 lists is tested, and malformed `--unit` and
  `--output-unit` arguments are refused too.
* **Output:** `--output-set` (the first set by default; refused for a key the calculator
  hasn't) and `--output-unit` (refused for an output without picks, a pick it doesn't
  offer, or an output named twice). **Each input is shown in the choice it was read in:**
  its `--unit`, the form its marks write (`10'-2"`), the unit its text names when that's
  an output choice, or else its default. So the CLI's Inputs lines are in the typed unit,
  and ADR-0019's last tie-window case, typed in one unit and shown in an inch form, is
  left to family settings until U2b.
* **The hint goes everywhere:** `DisplayPrefs.fraction_denominator`, `ValueParts.fraction`,
  `CopyForm.FRACTION` and the "Copy fraction" item, `to_fraction`, `Unit.fractions` and the
  result field's hint label. That closes the cloud review's Lows 1 and 2 at stop 1 (the
  hint's test and its disagreement at huge sizes), PR #1's Lows 1 and 3.
* **JSON** is `formatting.result_json`, as E5's example, which a run reproduces key for key.
  `Result.to_dict` and `Note.to_dict` are removed; ADR-0013 and ADR-0014 are amended.
  `output_set` is `null` for a calculator with no sets. The roadmap's "a converter's JSON
  rows in their own units" is done.
* **`caddcalc show`** lists each input's choice ids, its default marked, each output's
  picks or fixed unit, and the output sets with the default marked.
* **The corpus:** S&R's scripts weren't in the repository, so it's regenerated as E8
  allows: 448 sheet-metal invocations from a fixed seed, 112 with `--json`, 219 that
  run, captured with c7b1772's CLI (`tests/tooling/capture_cli_corpus.py`). Each is
  rewritten as E8 says (`--units in` → `--output-set in`; `--units mm` →
  `--output-set mm` and " mm" on each bare length). All 448 exit as they did, and every
  input, output and step `base` value of the 219 equals c7b1772's bit for bit.
* **Tests:** the schema test over every built-in and method; MH31 Fig. 13's figures as
  `base` and `shown`, and in `in_16` with its `copied`; each refusal; `--units` and
  `--fraction` gone. Thirteen mutants, one for each guard (the CLI's refusal, a `--unit`
  without its input, twice, or not offered; an unknown set; an output without picks; an
  input shown as read; a bare number in the default choice; `entered` only when given; a
  whole count; a form's `copied`; an unrounded `shown.value`; a signed step's plus), are
  each killed.
