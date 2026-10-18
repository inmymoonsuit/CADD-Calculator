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
| `36 ksi`, `36000 psi`, `248 MPa` | a stress, such as a strength; a bare number is ksi when the system is `in`, MPa when it's `mm` |
| `3 in²`, `3 in^2`, `3 in2`, `3 sq in`, `3 square inches` | an area; `ft²`, `mm²`, `cm²` and `m²` are typed the same ways, and a bare number is in the square of your unit system's length |

Units can be typed by name, in US or British spelling: `3 millimeters` or
`3 millimetres`, `1 meter` or `1 metre`, `44 percent` or `44 per cent`.

Type your regional format's decimal mark, or "." in any format: in German, `0,125` and
`0.125` are the same. Digits are never grouped, so `1.234` is always 1.234, and a comma
where your format's mark is "." is refused rather than guessed at. The minus sign `−`
works as `-` does. Numbers the app fills in, such as the course example, are written in
your format; what you typed stays as you typed it.

Not supported yet: combined feet and inches such as `3'-4 1/2"`.

## Precision and rounding

* Calculations use full double precision, the same as Excel.
* **Rounding happens only for display.** Results show 4 decimals by default (angles show 2,
  stresses 1).
  The CLI's `--decimals` changes this, and `--fraction 64` adds the nearest 1/64".
* Stresses follow the unit system: ksi when it's `in`, MPa when it's `mm`.
* Areas follow it too, as the square of the length unit: in² when it's `in`, mm² when
  it's `mm`, to 4 decimals. They're always written `in²` and `mm²`, however you typed
  them.
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
