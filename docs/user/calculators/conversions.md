# Conversions

Each converter takes one value, typed in any unit of its kind, and shows it in every unit
of that kind at once. Each row has its own Copy button, so type a length in millimeters
and copy it in inches, or the other way round.

* **Each row stays in its unit,** whatever the unit system: the millimeter row reads mm
  when the app shows inches. Rows show 6 significant figures, such as `25.4000 mm` or
  `0.0833333 ft`; Copy gives what's shown, and **Copy full precision** 10 digits.
* **Any finite value converts,** zero and negative values included: a negative length
  is an offset, a negative stress a compression, a negative angle a direction.
* **The factors are the units' exact definitions,** from NIST Special Publication 811
  (2008), Appendix B.8, and the 1959 definitions of the inch and the pound: 1 in is
  25.4 mm exactly, and 1 ft² is 92 903.04 mm² exactly. Where SP 811 prints a rounded
  factor, as for psi, the converter uses the exact pound, inch, and standard free fall
  instead.

Each converter is *verified* against SP 811's Appendix B.8 for the units its status
names.

## Length

Type a length in any unit: `3/16 in`, `4.7625 mm`, `0.25 ft`, `1'-4 3/16"`. It's shown in:

| Row | Shows | Copy gives |
|---|---|---|
| Inches, Feet, Millimeters, Centimeters, Meters | `16.1875 in` | `16.1875` |
| Feet and inches | `1'-4 3/16"`, to the nearest 1/16 inch | `1'4-3/16"` |
| Nearest 1/16, 1/32, and 1/64 inch | `16 3/16"` | `16-3/16"` |
| Error of each nearest fraction | `+0.002500 in` | `+0.002500` |

The error is the nearest fraction less the value, in inches to six decimals: positive
where the fraction is longer than the value, and shown with its `+` so its direction
reads at a glance. The error row's tooltip says so too. A value that is that very
fraction has an error of exactly 0, whether it's typed in inches or in millimeters, such
as `411.1625 mm` for 16 3/16 in. A value half-way between two fractions takes the one
with the even numerator: `3/32 in` and `2.38125 mm` are both `1/8"` to the nearest 1/16,
as the `(≈ …")` beside the inch row says too ([Units and precision](../units-and-precision.md)).
An error has no `(≈ …")` of its own, and a value and its negative show the same error,
signs apart.

Stress and pressure have a smaller largest value than the others: every stress is held
in MPa, which is larger than kPa and psi, so a value whose kPa or psi row would be
too large for the computer to hold, about 1.8 × 10³⁰⁸ kPa, is refused rather than shown
as infinite. A number too large to calculate with in any unit, such as `1e308 ft`, is
refused as too large.

## Angle

Type an angle in degrees, radians, or degrees, minutes and seconds: `30`, `1 rad`,
`40°30′15″`. It's shown in degrees, radians, and degrees, minutes and seconds
(`40°30′15.00″`, copied as `40d30'15.00"`).

## Area

Type an area in any unit: `3 in²`, `3 sq in`, `2 ft²`, `500 mm²`. It's shown in in², ft²,
mm², cm², and m².

## Stress and pressure

Type a stress or pressure in psi, ksi, kPa, or MPa. It's shown in all four.
