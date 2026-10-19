# Units and precision

## Typing into a calculator's field

Each input with a unit has a **unit picker** after it, and the number you type is read
in the unit the picker shows. The picker is the only place a unit is given: closed, it
shows the unit's symbol (`in`, `ft-in`, `mm`, `°`); open, each unit's name too.
Lengths are offered as `in`, `ft-in`, `ft`, `mm`, `cm` and `m`; angles as `°`, `° ′ ″`,
`′`, `″` and `rad`. An input with no unit, such as a K-factor or a number of sides, has
no picker.

| You type | With the picker on | Reads as |
|---|---|---|
| `0.1046` | in | 0.1046 in |
| `3/16`, `1 3/16`, `1-3/16` | in | 3/16 in, and 1 3/16 in |
| `1 - 3/16` | in | 13/16 in: with a space, the hyphen is minus |
| `2 × 1 3/16`, `(1 + 2) / 4` | in | 2 3/8 in, and 3/4 in |
| `10-2 3/16`, `10 2 3/16`, `10'-2 3/16"` | ft-in | 10'-2 3/16" |
| `10` | ft-in | 10 inches, 0'-10" |
| `40 30 15`, `40°30′15″` | ° ′ ″ | 40°30′15″ |
| `0.44` | (no picker) | the ratio 0.44 |

* **Arithmetic** takes `+`, `-` (or `−`), `*` (or `×`), `/` (or `÷`) and parentheses,
  and works exactly, so `1/3*3` is exactly 1. It takes no names, functions or powers.
* **A hyphen between a whole number and a fraction, with no space on either side,
  joins them**, as AutoCAD reads it: `1-3/16` is one and three sixteenths. Every other
  hyphen is minus, so `1 - 3/16` is thirteen sixteenths. A whole number, a space and a
  fraction, `1 3/16`, is a mixed number too.
* **In feet and inches**, the marks are optional: give whole feet, then the inches,
  under 12, joined by a hyphen or a space, or the inches alone, of any size. One sign,
  at the front: `-10-2`.
* **In degrees, minutes and seconds**, the parts go in order, separated by spaces or
  their marks; degrees and minutes are whole, and minutes and seconds are under 60.
* **What it reads as** shows at the field's end, in a lighter colour, whenever your
  text isn't a plain number: `1-3/16` shows `= 1 3/16 in`, and `1 - 3/16` shows
  `= 0.8125 in`. If the field is too narrow for both, it's in the field's tooltip, and
  a screen reader says it.
* **A unit typed into the field is refused**, never guessed at: `25 mm` in a field set
  to inches says "Units go in the picker. Use 25 mm?", with a button that sets the
  picker to mm and the text to 25. A pasted feet-and-inches value offers ft-in. A unit
  of another kind, such as `25 MPa` in a length, is refused with no offer.
* **Switching a picker** re-reads the number you typed in the new unit: 25 stays 25,
  now in millimeters, and switching back is the undo. A value you didn't type, such as
  a default, a family value or the course example, keeps its size and is shown
  converted. Each switch is shown in the status bar and said to screen readers.
* **Your first switch of a picker on a calculator carries** to that calculator's other
  pickers of the same kind, so a part drawn in millimeters takes one change. After
  that, each picker is set on its own, for as long as the app is open.

## Typing with the unit in the text

Family settings fields (until they get pickers, KI-027) and the command line read a
value with its unit in the text:

| You type | Means |
|---|---|
| `0.1046` | 0.1046 in your current unit system (in or mm) |
| `3mm`, `3 mm` | 3 millimetres, whatever the unit system |
| `1/8`, `1/8in` | 0.125 (inches if no unit is typed and the system is `in`) |
| `1-1/2"`, `1 1/2 in` | 1.5 inches |
| `2'` | 2 feet |
| `90`, `90°`, `90 deg` | 90 degrees (angles are always degrees unless you type `rad`) |
| `44%`, `0.44` | the ratio 0.44 (e.g. a K-factor) |
| `6` | a count, such as a polygon's number of sides: a whole number, with no unit or `%` |
| `36 ksi`, `36000 psi`, `248 MPa` | a stress, such as a strength; a bare number is ksi when the system is `in`, MPa when it's `mm` |
| `3 in²`, `3 in^2`, `3 in2`, `3 sq in`, `3 square inches` | an area; `ft²`, `mm²`, `cm²` and `m²` are typed the same ways, and a bare number is in the square of your unit system's length |

Units can be typed by name, in US or British spelling: `3 millimeters` or
`3 millimetres`, `1 meter` or `1 metre`, `44 percent` or `44 per cent`.

Type your regional format's decimal mark, or "." in any format: in German, `0,125` and
`0.125` are the same. Digits are never grouped, so `1.234` is always 1.234, and a comma
where your format's mark is "." is refused rather than guessed at. The minus sign `−`
works as `-` does. Numbers the app fills in, such as the course example, are written in
your format; what you typed stays as you typed it.

### Feet and inches, and degrees, minutes and seconds

A length can be typed in feet and inches, in any of the usual forms: `1'-4 3/16"`,
`1'-4-3/16"`, `1'4-3/16"`, `1' 4 3/16"`, `1′ 4 3/16″`, or `1 ft 4 3/16 in`. Give whole
feet, then inches under 12 with their mark, and at most one sign, at the front:
`-1'-4"`.

An angle can be typed in degrees, minutes and seconds: `40°30′15″`, `40°30'15"`,
`40d30'15.5"` (as AutoCAD takes it), or `40 degrees 30 minutes`. Give whole degrees and
minutes, minutes and seconds under 60, and at most one sign, at the front: `-0°30′`. In
an angle, `′` and `″` (or `'` and `"`) are minutes and seconds, so `30′` is half a
degree; everywhere else they're feet and inches.

Where a result is shown in feet and inches, it reads `1'-4 3/16"`, to the nearest 1/16
inch, and Copy gives `1'4-3/16"`, the form CAD takes. A result in degrees, minutes and
seconds reads `40°30′15.00″`, and Copy gives `40d30'15.00"`. Rounding carries, so
1'-11 63/64" shows as 2'-0", and 29.99999999° as 30°0′0.00″. A value exactly half-way
between two fractions takes the one with the even numerator, so 3/32" shows as 1/8" and
7/32" as 1/4". The computer holds a typed value to about 16 digits, so a half-way value
typed in inches, millimeters, meters or a fraction of a foot, such as `3/32 in`,
`2.38125 mm`, `0.12779375 m` or `317/384 ft`, lands a hair off the half; a value within
two units in its last digit, as written in inches, of the half counts as the half. One
three units off, as `11.976562500000005 in` is, is a value of its own, and rounds as it
is. A value so large that a
sixteenth of an inch is lost in its last digits is rounded as it is. Seconds of an angle
round the same way. Every inch fraction rounds by this one rule: feet and inches, the
nearest 1/16, 1/32 and 1/64 inch, and the `(≈ …")` beside an inch value, so they never
disagree.

## Precision and rounding

* Calculations use full double precision, the same as Excel.
* A value shown to significant figures, such as an area or a converter's row, is written
  in plain decimals from 0.000001 up to 10¹⁶, and with an exponent outside that, as
  `1.00000e+300`.
* **Rounding happens only for display.** Results show 4 decimals by default (angles show 2,
  stresses 1).
  The CLI's `--decimals` changes this, and `--fraction 64` adds the nearest 1/64".
* Stresses follow the unit system: ksi when it's `in`, MPa when it's `mm`.
* Areas follow it too, as the square of the length unit: in² when it's `in`, mm² when
  it's `mm`, to 6 significant figures, such as `6451.60 mm²` or `10.0000 in²`. They're
  always written `in²` and `mm²`, however you typed them.
* Some results are always shown in one unit, whatever the unit system, such as each row
  of a unit converter. They show 6 significant figures, e.g. `25.4000 mm` or
  `0.0833333 ft`.
* JSON output (`--json`) is unrounded, in millimetres, degrees, megapascals, and square
  millimetres, and each value names its unit.
  Each step also gives `substitution`, a map from its formula's symbols to the text shown
  for them (not numbers), `expression_unit`, the unit its formula yields, and `stated`,
  the value as its source states it, e.g. `"0.109375 in"`; all three are `null` for an
  ordinary step, whose formula yields base units.
  Each note gives its lead as `text` and the rest as `detail`, with any values in base
  units, and `quantities` with each value it names and that value's unit.

Round only when you put the final number on a drawing. Rounding intermediate values,
such as a bend allowance before adding up a flat pattern, builds up error.
