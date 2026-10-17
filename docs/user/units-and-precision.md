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

Not supported yet: combined feet and inches such as `3'-4 1/2"`.

## Precision and rounding

* Calculations use full double precision, the same as Excel.
* **Rounding happens only for display.** Results show 4 decimals by default (angles show 2).
  The CLI's `--decimals` changes this, and `--fraction 64` adds the nearest 1/64".
* JSON output (`--json`) is unrounded, in millimetres and degrees, and each value names its unit.

Round only when you put the final number on a drawing. Rounding intermediate values,
such as a bend allowance before adding up a flat pattern, builds up error.
