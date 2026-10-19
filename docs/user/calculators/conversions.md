# Conversions

Each converter takes one value and gives it in another unit. Pick the value's unit in the
picker after its field, and type the number; pick the result's unit in the picker in its
row. Until you pick the result's unit, it's the other system's counterpart of the one you
typed in: inches give millimeters and millimeters give inches, feet give meters, ksi
gives MPa, degrees give radians. Once you pick it, it stays, for as long as the app is
open.

* **The result shows 6 significant figures,** such as `25.4000 mm` or `0.0833333 ft`;
  Copy gives what's shown, and **Copy full precision** 10 digits. A number too small for
  the computer to hold to six figures, near 10⁻³²⁴, shows only the figures it holds.
* **Any finite value converts,** zero and negative values included: a negative length
  is an offset, a negative stress a compression, a negative angle a direction.
* **The factors are the units' exact definitions,** from NIST Special Publication 811
  (2008), Appendix B.8, and the 1959 definitions of the inch and the pound: 1 in is
  25.4 mm exactly, and 1 ft² is 92 903.04 mm² exactly. Where SP 811 prints a rounded
  factor, as for psi, the converter uses the exact pound, inch, and standard free fall
  instead.

Each converter is *verified* against SP 811's Appendix B.8 for the units its status
names. A unit-to-unit converter has no **Show in** picker, since its result has its
own; Decimal to fraction has one, for its error.

## Length

Type a length in inches, feet and inches, feet, millimeters, centimeters, or meters:
`3/16` in inches, `4.7625` in millimeters, `1'-4 3/16"` in feet and inches. Pick the result
in any of them. In feet and inches it's `1'-4 3/16"`, to the nearest 1/16 inch, copied as
`1'4-3/16"`.

## Fraction to decimal

Type a fraction of an inch, such as `3/16`, `1 3/16` or `1-3/16`, and read it as a
decimal: `0.187500 in`. Pick the decimal's unit to read it in millimeters, `4.76250 mm`,
or another length unit. The input starts in inches; pick another unit to type a fraction
of a millimeter or a foot.

## Decimal to fraction

Type a length in any unit, and pick the **Fineness**: 1/16, 1/32 or 1/64 inch. It gives
two results:

| Result | Shows | Copy gives |
|---|---|---|
| Nearest fraction | `3/16"`, at the fineness | `3/16"` |
| Error | `-0.0025 in`, in the Show in picker's unit | `-0.0025` |

The error is the nearest fraction less the length: positive where the fraction is longer
than the length, and shown with its `+` so its direction reads at a glance. The error's
tooltip says so too. A length that is that very fraction has an error of exactly 0,
whether it's typed in inches or in millimeters, such as `411.1625 mm` for 16 3/16 in. A
length half-way between two fractions takes the one with the even numerator: `3/32 in`
and `2.38125 mm` are both `1/8"` to the nearest 1/16
([Units and precision](../units-and-precision.md)). A length and its negative show the
same error, signs apart.

## Angle

Type an angle in degrees, degrees, minutes and seconds, minutes or seconds of arc, or
radians: `30`, `40 30 15` in degrees, minutes and seconds. Pick the result in any of
them: `0.706931 rad`, or `40°30′15.00″`, copied as `40d30'15.00"`.

## Area

Type an area in in², ft², mm², cm², or m², and pick the result in any of them.

## Stress and pressure

Type a stress or pressure in psi, ksi, kPa, MPa, or GPa, and pick the result in any of
them.

## Very large values

A value is refused if it would be too large for the computer to hold in a unit its
result can be picked in: every stress is held in MPa, which is larger than kPa and psi,
so a value whose kPa would pass about 1.8 × 10³⁰⁸ is refused rather than shown as
infinite, and so is an angle too large in seconds of arc. A number too large to calculate
with in any unit, such as `1e308 ft`, is refused as too large. A value too large to count
in feet and inches, inch fractions, or degrees, minutes and seconds is shown in inches or
degrees, to 6 significant figures, rather than as hundreds of digits.
