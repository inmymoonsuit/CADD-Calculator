# Units and precision

## Typing values

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
two units in its last digit of the half counts as the half. A value so large that a
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
