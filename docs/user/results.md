# Results and copying

In the desktop app, a calculator's results sit in their own boxed fields, between the
inputs and the notes, work, and method. The command line prints the same values as text.

## The result fields

```
┌──────────────────────────────────────────────────────────────────┐
│ BA     Bend allowance                         0.3119  in   [⧉]  │
└──────────────────────────────────────────────────────────────────┘
```

Each field shows one result: its symbol, its name, its value, its unit, and a copy
button.

## Show in: the results' units

The **Show in** picker, between the Results title and Copy all, sets the units every
result is shown in. Its choices are sets, one per length unit: `in`, `in 1/16`, `in
1/32` and `in 1/64` (inches to the nearest fraction, as `5/16"`), `ft-in`, `ft`, `mm`,
`cm` and `m`. Each names what the calculator shows: the right triangle's are `in · ° ·
in²` and the like, since areas are the square of the length unit, and stresses follow
the system, ksi beside inches and MPa beside metric units. Angles are in degrees.

The open list names each set, as `in 1/16 · ° · in² — inches, nearest 1/16; degrees;
square inches`, and a screen reader says the chosen set's name. The mouse wheel never
changes it; click it, or use the keyboard.

* **Until you choose a set, it follows your inputs:** while every length input the
  method shows has the same unit picked, the results show in it. Pick mm for the
  thickness, and the other lengths and the results follow. While the lengths disagree,
  as with the thickness in mm and the radius in cm, the results stay in the set they
  last followed. An input another method uses, hidden for now, doesn't count. Once you
  choose a set, it's yours for the session, on that calculator.
* **What follows the set:** the fields, Copy, Copy all, what a screen reader says, and
  the work. The Inputs list gives each input in its own picker's unit, then in the
  set's where the unit differs: `0.1046 in = 2.6568 mm`. An inch field has no second
  value in an inch-fraction set, whose unit is inches too. Where a fraction or feet and
  inches would round an input, it's given in the form's unit instead: `2.6568 mm =
  0.1046 in`, never `= 0'-0 1/8"`. A calculator with no Show in picker gives no second
  value.
* **Some results keep their own unit,** such as each row of a unit converter, and a
  result with its own picker in its row is set there. A calculator whose every result
  has its own unit has no Show in picker.
* In a narrow window, the picker and Copy all move under the title.

* Values are rounded for display only, and line up on their decimal points, so a mix of
  lengths (4 decimals) and angles (2 decimals) is easy to read. A degree sign sits
  against its number: `132.70°`.
* When a note is about a result, its field gets the same outline as the inputs the
  note is about: solid for a limit or a warning, dashed when a check couldn't be made.
* While an input holds text that isn't a number, every field shows "—" and its copy
  button is unavailable. So a value you copy always belongs to the inputs on screen.
* In a wide window, the page stops growing at a comfortable width, beside the list, so a
  label and its value don't drift far apart; the rest of the window is left plain.
* The disclaimer is the last line under the results, always whole: it wraps to the
  page's width rather than being cut off.

## Copying

* **Copy a value:** click a field's copy button. It copies the number as shown, without
  its unit, such as `0.3119`, ready for a spreadsheet cell or a CAD dimension box working
  in the drawing's units. The button shows a check for a moment, and the
  status bar says what was copied.
* **Other forms:** right-click a field, or press the Menu key on its copy button, for:
  * **Copy with unit:** `0.3119 in`; not offered for feet and inches or degrees, minutes
    and seconds, whose copy names its units already
  * **Copy full precision:** the value to 10 significant digits, without the display
    rounding, in the display unit, such as `0.311864`; for feet and inches, a decimal in
    inches, and for degrees, minutes and seconds, in degrees, as the item says ("Copy
    full precision, in inches")
* **Copy all:** the button beside the Results title copies every result as rows for a
  spreadsheet, one per result: symbol, name, value, and unit, in columns. A name a
  spreadsheet would take for a formula, such as one starting with `=`, is kept as text.

Numbers on screen use your regional format's decimal mark, such as `0,3119` in German.
Copying a value, with or without its unit, or at full precision, always writes ".", as
`0.3119`, since CAD programs read it: AutoCAD takes a comma as the break between a
point's coordinates. **Copy all** writes your decimal mark, for a spreadsheet set to your
format. Where your mark isn't ".", the menu also copies the number exactly as shown, as
**Copy 0,3119**, and each item is named by what it copies: **Copy 0.3119**, **Copy
0,3119**, **Copy 0.3119 in**. The status bar always quotes what was copied.

## The keyboard

* **Tab** moves down the page: the inputs, then each result's copy button, then Copy
  all, then the notes, inputs, and work below. A focused copy button has a blue ring
  around its field.
* On a focused copy button, **Space**, **Enter**, or **Ctrl+C** (**Cmd+C** on macOS)
  copies its value, and the **Menu** key opens its other forms.
* **Ctrl+Shift+C** (**Cmd+Shift+C** on macOS) copies all results from anywhere in the
  window.
* An input with a note's outline gets the same blue focus ring outside its outline, so
  you can see both.
* Screen readers hear each result in full, such as "Bend allowance, BA: 0.3119 inches",
  and its copy button as "Copy Bend allowance", with the value. They're told what each
  copy put on the clipboard, and the status bar shows it for a few seconds. A sign is
  said in words, "minus 0.3119 inches", and a fraction as it's spoken, "1 and a quarter
  inches".
* Where a result has a note on what it means, such as which way an error runs, its label's
  tooltip gives it, and screen readers hear it as the field's description.

## When the window is short

Results are never hidden on their own. The fields always show in full, and the notes,
inputs, and work below them take the rest of the height, with their own scroll bar.

When the window is too short for the inputs, every result, and a few lines of the notes,
the whole page scrolls instead, results included. The notes, inputs, and work then show
in full under the results, so there's only ever one scroll bar.

## Notes

Notes are listed strongest first: a cited limit, then a warning or a part that can't be
made, then a check that couldn't be made. Each note:

1. leads with its verdict and its numbers, in your units, such as "Limit exceeded:
   inside radius 0.0500 in is below 0.1600 in, the recommended minimum this check uses,
   for 6061-T6 aluminum at 0.0630 in, in aerospace bending practice."
2. then says what each source gives, with each value as its source states it
3. then names its sources, in lighter text

In the Inputs list, each value's source, such as "default", is in the same lighter
text.

The command line prints the same three parts, the second and third indented. In JSON
output, a note's `text` is its lead and `detail` the rest, both with values in base
units, and `quantities` gives each value the note names, with its unit. For the whole
note, join `text` and `detail`; read numbers from `quantities`.
