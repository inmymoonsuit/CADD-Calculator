# Geometry calculators

Each Geometry calculator takes the dimensions that define a shape and gives every common
property of it at once, so you don't choose "area" or "perimeter" first. Lengths can be
typed in any unit, including feet and inches (`1'-4 3/16"`); areas show in the square of
your length unit (in² or mm²), to 6 significant figures. Angles are in degrees.

Input that describes no real shape is refused with a message, never computed: every
length must be greater than zero, and each calculator's own limits are below. A length
must also be from 10⁻⁷⁰ mm to 10⁷⁰ mm, far past any drawing: outside that the arithmetic
can't hold the products of the lengths, and an angle or an area would come out wrong.

## Sources

The formulas are from *Machinery's Handbook*, 31st edition (Industrial Press, 2020),
Mathematics: "Dimensions of Plane Figures" (printed pp. 75–80), "Polygons" (pp. 81–82),
and "Solution of Triangles" (pp. 96–101; p. 101 is under the running head "Solution of
Oblique Triangles"). The triangles also cite the NIST Digital Library of
Mathematical Functions, §4.42. π comes from the computer's full-precision value, not the
Handbook's rounded constants.

**For students:** the *Machinery's Handbook Pocket Companion* (32nd edition, Industrial
Press, 2024) covers the same figures more briefly: "Dimensions of Plane Figures",
pp. 1–6, "Segments of Circles", pp. 7–9, for the arc, and the triangles, pp. 16–19. Each
method lists it last, as "see also"; the 31st edition is the source of record.

None of these methods is marked *verified* yet: that needs a published worked example
in the test suite (see the user guide's [status table](../index.md#how-to-read-a-result)).

## Circle

| Method | You give | You get |
|---|---|---|
| From the diameter | diameter D | radius r = D/2, circumference C = π·D, area S = π·D²/4 |
| From the radius | radius r | diameter D = 2·r, circumference C = 2·π·r, area S = π·r² |

## Rectangle

Give the length L and width W. You get the perimeter P = 2·(L + W), the area S = L·W,
and the diagonal d = √(L² + W²).

## Triangle (three sides)

Give the three sides a, b and c. You get the perimeter, the area, and the three angles
A, B and C, each opposite the side of the same letter.

* **The sides must make a triangle:** the longest must be shorter than the other two
  together. A flat "triangle", whose longest side equals the other two, is refused too,
  even where the computer's arithmetic puts it a hair over, as 0.1 + 0.2 is over 0.3.
* **Each angle comes from the tangent of half of it,** in W. Kahan's arrangement: the
  law of cosines (p. 96) rearranged so a tiny angle, or one nearly 180°, keeps its
  digits. A needle-thin triangle with sides 10, 10 and 0.0000001 has an angle of
  0.000000573°, which the plain law of cosines gives as 0. The Handbook's procedure for
  three known sides (p. 101) takes its second angle from the law of sines instead,
  which can't give an angle over 90°: for sides 3, 7 and 5 it would give 60° where the
  angle is 120°. This calculator departs from the Handbook there on purpose.
* **The area** is Heron's formula, arranged as W. Kahan shows so that a needle-thin
  triangle keeps its digits: sides 10, 10 and 0.0000001 give an area of 0.0000005.

## Right triangle

Legs a and b meet at the right angle, c is the hypotenuse, and A and B are the acute
angles opposite a and b. Give any two of them, as long as one is a length:

| Method | You give |
|---|---|
| Two legs | a and b |
| A leg and the hypotenuse | a and c; c must be longer than a |
| A leg and its opposite angle | a and A |
| The hypotenuse and an angle | c and A |

An acute angle must be greater than 0° and less than 90°; one so near 90°, within about
6e-11°, that its tangent can't be computed counts as 90° and is refused, in either angle
method. Two angles alone fix no size, so they aren't a method. You get all three sides,
both acute angles, the area and the perimeter.

## Regular polygon

Give the number of sides N, a whole number from 3 to 1 000 000, and one of its sizes. N is a
count: it's shown without decimals, and a unit or a percent on it, such as `600 %`, is
refused.

* the **side** a
* **across flats (inscribed circle)**: the inscribed circle's diameter, 2r
* **across corners (circumscribed circle)**: the circumscribed circle's diameter, 2R

You get the other two sizes, the perimeter and the area. A hexagon with sides of 1 in is
1.7321 in across flats and 2 in across corners.

With an **odd** number of sides, no two flats are parallel, so a caliper doesn't read
the across-flats size. Held from a flat to the opposite corner, it reads r + R, which
the result's note gives; turned another way, it reads more. A pentagon of side 1 in reads
1.5388 in from a flat to its corner, but up to 1.6180 in turned.

## Arc and sector

Give the radius r and the included angle A, greater than 0° and up to 360°; past 180° is
the major arc. You get:

* the arc length, π·r·A/180°
* the chord, 2·r·sin(A/2)
* the sagitta, or rise, from the chord's middle to the arc: 2·r·sin²(A/4), the
  Handbook's r·(1 − cos(A/2)) written so a small angle keeps its digits
* the sector area, π·r²·A/360°

A whole circle's chord, at 360°, is exactly 0: the sine of a whole multiple of 180° is
taken as 0, not the computer's 1.2e-16.
