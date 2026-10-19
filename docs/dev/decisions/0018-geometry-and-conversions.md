# ADR-0018: Geometry and Conversions families

* **Status:** **Accepted, and built:** the units it needs (u2, u3), the Geometry family
  (m1), and the Conversions family (m2); see Amendments. The maintainer approved the scope below on
  2026-10-17 ("Go with your recommendations for both families: names, starting
  calculators, and one converter per kind of quantity"). Revised with Support & Review's
  sources check (formula locators, input to refuse, numerical notes), and built after the
  units registry (ADR-0019, U4).
* **Builds on:** ADR-0004 (declarative calculators, provenance), ADR-0005 (units and
  display), ADR-0006 (built-ins and plugins), ADR-0013 (domains), ADR-0017 (result fields)

## Context

The app so far serves sheet metal. The maintainer wants two general-purpose families for
people in design, drafting and construction, and students in those fields:
* everyday geometry (area, circumference, perimeter)
* unit conversions, mm to inches above all

## Decision

### 1. Two new domains, listed above Sheet Metal

* **Geometry** (`geometry`), first in the list, then **Conversions** (`conversions`), then
  Sheet Metal. The order comes from `BUILTIN_DOMAINS`.
* Neither family has shared settings in this phase.

### 2. Geometry: one calculator per shape, giving every property at once

Each calculator takes the shape's defining dimensions and returns all of its common
properties together, so the user doesn't have to choose "area" or "perimeter" first.

| Calculator | Inputs | Outputs |
|---|---|---|
| Circle | diameter (a radius method too) | circumference, area, radius or diameter |
| Rectangle | length, width | perimeter, area, diagonal |
| Triangle (three sides) | a, b, c | perimeter, area (Heron), the three angles |
| Right triangle | any two of: legs, hypotenuse, an acute angle (methods) | the rest, plus area |
| Regular polygon | number of sides, plus one of side, across flats, or across corners (methods) | perimeter, area, the other two sizes |
| Arc and sector | radius and included angle | arc length, chord, sagitta (rise), sector area |

* **Impossible input is refused, never computed.** Every length must be finite and
  greater than 0. Also refused:

  | Calculator | Refused |
  |---|---|
  | Triangle (three sides) | with the sides sorted a ≤ b ≤ c, c ≥ a + b (a flat triangle included) |
  | Right triangle | a hypotenuse no longer than the given leg; an acute angle outside 0° < A < 90°. Two angles alone aren't a method, since they fix no size. |
  | Regular polygon | N not a whole number, or N < 3 |
  | Arc and sector | an included angle outside 0° < θ ≤ 360° (past 180° is a valid major arc) |

* **Formulas** go through `ctx.calc` and show their work (ADR-0004). Each method cites
  *Machinery's Handbook*, 31st ed. (MH31), Mathematics: "Dimensions of Plane Figures"
  (printed pp. 75–80), "Polygons" (pp. 81–82) and "Solution of Triangles" (pp. 96–101,
  p. 101 under the running head "Solution of Oblique Triangles"); the DLMF §4.42 is a
  second source for the triangles. Citing a formula in a method is not reference data, so
  ADR-0014's cap doesn't apply (ADR-0014 D7 amendment). Constants are computed with
  `math.pi` and `math.radians`, not the Handbook's rounded ones.
* **For students, the Geometry help points to** the *Machinery's Handbook Pocket
  Companion* (32nd ed., Industrial Press, 2024): "Dimensions of Plane Figures", pp. 1–6,
  and the triangles, pp. 16–19. It's a "see also", not the source of record.
* **Each triangle angle comes from the law of cosines** (MH31 p. 96). MH31's three-sides
  procedure ("All Three Sides Known", p. 101) takes the second angle from the law of sines,
  which can't return an obtuse angle: sides 3, 7, 5 would give 60° where the answer is
  120°. We depart from the Handbook there on purpose, and the help says so.
* **Formulas are arranged to keep their digits,** since a full-precision copy carries 10
  significant figures. Heron's area in Kahan's needle-safe form, cosines clamped before
  `acos`, a leg as √((c − a)(c + a)), and the sagitta as 2r sin²(θ/4). Each is the cited
  formula rearranged, recorded as an implementation note.
* **A regular polygon's sizes are named by their circles:** "across flats (inscribed
  circle)" and "across corners (circumscribed circle)". With an odd number of sides there
  are no parallel flats, so the help says that a caliper there reads r + R.

### 3. Conversions: one converter per kind of quantity

Each converter takes one value typed in any unit of its kind (the parser already reads
"3/16 in", "4.7625 mm" or "0.25 ft") and shows the same quantity in every unit of that
kind at once. With the result fields (ADR-0017), each row has its own Copy button.

| Converter | Shows |
|---|---|
| Length | in, ft, mm, cm, m, feet and inches (`1'-4 3/16"`, ADR-0019 U3), and the nearest fraction of an inch (1/16, 1/32, 1/64) with its error |
| Angle | degrees, radians, and degrees-minutes-seconds |
| Area | in², ft², mm², cm², m² |
| Stress and pressure | psi, ksi, kPa, MPa |

* Conversion factors are the exact definitions in NIST SP 811 (public domain), e.g.
  1 in = 25.4 mm exactly and 1 lbf = 4.4482216152605 N, held by the units registry
  (ADR-0019). SP 811's printed factors for the degree, lbf, psi and ksi are rounded and
  aren't used.
* **Converters refuse only non-finite values.** Zero is fine, and the sign passes through:
  a negative length is an offset, a negative stress is compression, a negative angle a
  direction.
* **Degrees-minutes-seconds carry and keep their sign:** 29.99999999° reads 30°0′0.00″,
  never 29°59′60.00″; −0.5° reads −0°30′0.00″; zero never reads −0°.
* This needs two core additions, both built on the units registry (ADR-0019), which comes
  first:
  * an **AREA** dimension (base mm², with in², ft², cm², m²; display follows the length
    preference)
  * an **Output fixed unit**: an Output may name the unit it is always shown in,
    whatever the display preference, with the registry's default precision for it. A
    converter's mm row stays mm when the app shows inches.
* Mm to inches is the Length converter: type a number in mm, read inches (and the
  fraction); type inches, read mm.

### 4. Out of scope for this phase

Volume and mass, temperature (an offset scale, which needs its own handling), slope and
pitch, bolt circles, and editable precision per converter. They're candidates for later.

## Consequences

* The app opens with general tools first, which suits students and non-sheet-metal users.
* Two core additions (AREA, fixed-unit outputs) that later families can reuse.
* Every new calculator gets the result fields, the CLI, JSON and the show-work steps with
  no special code.

## Amendments

### 2026-10-18: *Machinery's Handbook*'s 31st edition (maintainer)

* The citations move from the 29th edition to the 31st (Industrial Press, 2020). MH29's
  "Areas and Volumes" (pp. 70–76) is MH31's "Dimensions of Plane Figures" (pp. 75–82): the
  rectangle p. 75, the triangles p. 76, the regular polygon, circle and sector p. 78, the
  segment p. 79, and "Formulas and Table for Regular Polygons" p. 82. The law of cosines
  stays on p. 96; "Solution of Right Triangles" is p. 98, and "All Three Sides Known"
  p. 101 (MH29's p. 102), with the same law-of-sines step we don't follow.
* The *Pocket Companion* (32nd ed.) is added as the help's pointer for students.

### 2026-10-18: the Geometry family, as built (m1)

* **`calculators/geometry/`**: `Circle`, `Rectangle`, `Triangle`, `RightTriangle`,
  `RegularPolygon` and `ArcSector`, with these public IDs and method keys:

  | ID | Methods |
  |---|---|
  | `geometry.circle` | `diameter`, `radius` |
  | `geometry.rectangle` | `standard` |
  | `geometry.triangle` | `three_sides` |
  | `geometry.right_triangle` | `legs`, `leg_hypotenuse`, `leg_angle`, `hypotenuse_angle` |
  | `geometry.regular_polygon` | `side`, `across_flats`, `across_corners` |
  | `geometry.arc_sector` | `standard` |

* **Symbols.** An area is S in every calculator, since A is an angle in the triangles and
  the arc. The right triangle's legs are a and b, its hypotenuse c, and its acute angles
  A and B opposite a and b; its angle method takes A, opposite leg a. A polygon's side is
  a, across flats AF and across corners AC.
* **Refused,** as §2 says: a length that isn't finite and greater than 0 (each length
  parameter's range); a flat or impossible triangle, compared after sorting the sides; a
  hypotenuse no longer than its leg; an acute angle outside (0°, 90°); an N that isn't
  whole, or under 3; an arc angle outside (0°, 360°]. Each method takes at least one
  length, so two angles alone are never a method.
* **Formulas,** each through `ctx.calc`:
  * The three-sided triangle sorts its sides in the work itself, longest x, middle y and
    shortest z (the middle one as `max(min(a, b), min(max(a, b), c))`, exactly), for
    Kahan's area. It cites Kahan's lecture notes, beside MH31 p. 76.
  * Each angle is `acosd(max(-1, min(1, cos)))`. A test finds a real triangle whose
    cosine rounds to 1.0000000000000002, which acos alone refuses.
  * A right triangle's angles from two sides are `atan2d`, which keeps its digits at
    either end of the range, and the other angle from one is 90° − A.
  * A polygon's area is N·a·AF/4, MH31's n·S·r/2 with r = AF/2.
* **Outputs a method takes as input.** A circle's diameter is an output of its radius
  method and an input of its diameter method, as the right triangle's and polygon's parts
  are. `Context.given(symbol, output=key)` reports the input as the output unchanged,
  with no step, since the inputs show it already; it checks the input exists in this
  run and measures what the output does.
* **The odd polygon's caliper reading** is a warning on the result, with the reading,
  r + R, as a value in the user's units, and the method's note says why.
* **The Pocket Companion** is each method's last reference, its detail starting "see
  also, for students", so it's shown with the sources and can't be taken for one. A
  family's own references aren't shown anywhere yet, so it isn't one.
* **Verification:** every method is unverified, with a note saying so: no published
  worked example with its figures was available to this build to put in
  `test_published_examples.py` (ADR-0010). The exact identities in `tests/test_geometry.py`
  (a 3-4-5 triangle's area of 6, a hexagon's √3, the sector's 5π) check the formulas, not
  a source's example.
* **The order of the families** (§1) is now the order they're registered, built-ins as
  `BUILTIN_DOMAINS` gives them, then plugins' as they load. `Registry` sorted them by
  name, which would have put Conversions first; calculators are still sorted by name
  within a family. The window opens on the first built-in calculator, now Arc and
  sector, the first Geometry calculator by name. (Corrected in fix round 3: this said
  the circle.)
* **The command line** reads an input's exact key or symbol before matching in any
  case: the right triangle's `a` and `A` are a leg and an angle. Matching in any case
  alone made both "unknown".
* **Marked for translation:** the names and summaries, as the sheet-metal calculators'
  are. Labels, help and notes wait for the string sweep, with the sheet-metal ones
  (ADR-0020's list).
* **A limitation,** KI-025: N is a ratio, so it shows as `6.0000`.

### 2026-10-18: the Conversions family, as built (m2)

* **`calculators/conversions/`**: `LengthConverter`, `AngleConverter`, `AreaConverter`
  and `StressConverter`, IDs `conversions.length`, `.angle`, `.area` and `.stress`, each
  with one method, `exact`, and one input, `value` (X), with no range: `Param.check`
  refuses only a value that isn't finite, so zero and any sign pass.
* **Each row is an output fixed in its unit,** `Output(unit=…)`, given the input
  unchanged (`Context.given`), so the rows add no work; the registry shows each in its
  unit to six significant figures. Length's feet and inches and Angle's degrees,
  minutes and seconds are `Output(form=…)` rows.
* **The nearest 1/16, 1/32 and 1/64 inch** are three more compound forms of a length,
  `in_16`, `in_32` and `in_64` (`core.units.compound.NearestInches`), each rounding once,
  half to even: shown `1 3/16"`, copied `1-3/16"` as U3 says inch fractions are, and
  spoken "1 and 3 sixteenths inches". A form of the value only, they read nothing.
* **Each fraction's error** is a row of its own, so it has its own Copy: the fraction,
  recorded as a step (`N16`, the value rounded to the nearest 1/16 inch), less the value,
  `E16 = N16 − X`, through `ctx.calc`. The fraction is built as the parser builds a
  length typed in inches, so a value typed in inches as that fraction has an error of
  exactly 0, where building it from the exact inch left a rounding's worth, shown as
  `0.00000000000000223793 in`. An error's useful precision is absolute, so these rows
  give their own, six decimals (`Output.precision`, which only a fixed-unit output may
  give).
* **Exactness.** `core.units.convert(amount, source, target)` converts an exact amount
  from the units' exact definitions: 1 in is 25.4 mm and 1 ft² 92 903.04 mm² exactly,
  and 1 psi is 6.894 757 293 168 361 kPa rounded once, the brief's test values. A row
  converts the value as typed, which is already a double, with `from_base`, as every
  other value is shown: 1 psi typed reads 6.894757293168362 kPa there, the same at the
  row's six figures and the full copy's ten. Converting that double in exact arithmetic
  was tried and dropped: it's no closer to what was typed (3 ft shown in feet would be
  3.0000000000000004 where plain division gives 3.0), and invisible at either precision.
* **Verified,** each for its scope, against NIST SP 811 Appendix B.8, a published
  figure (`test_published_examples.py`): the inch and the foot in meters, and the square
  inch and the square foot in square meters, which B.8 prints exact; and the pound-force
  and the kip per square inch, and the degree, to B.8's printed digits.
* **The launch height.** The Length converter's twelve rows make it the tallest built-in
  page, which ADR-0021 §3 made the launch height: offscreen, 996 px against Geometry's
  765. The maintainer ruled that the launch height stays main's, 738 px at 9 pt, and the
  Length converter scrolls (ADR-0021's interim amendment, 2026-10-19); so does the right
  triangle.
* **The CLI** needs nothing of its own: `caddcalc run conversions.length X=4.7625mm`
  prints every row, and JSON gives each in base units.

### 2026-10-19: the reviews' findings, fix round 2 (group B, correctness)

* **A flat triangle typed in decimals is refused** (S&R's M1). Sides typed as decimals
  are doubles, so `0.1 + 0.2 − 0.3` comes out 5.55e−17, over 0, and the strict test
  `c ≥ a + b` took sides 0.1, 0.2 and 0.3 in for a triangle. A triangle is now flat when
  `(a + b) − c ≤ 4ε·c`, sorted, with ε the double's machine epsilon
  (`triangles.FLAT_GAP`). The tolerance, from S&R's measurement: over 200,000 flat
  triples typed as decimals, the gap was at most 1.80ε of the longest side, and with the
  fix 80,000 of 80,000 were refused; the triangle the cosine-clamp test needs, the
  nearest to flat a test uses, is 21.98ε. This build's own sweep, 8,000 flat triples
  typed to three decimals in in, mm, ft and m, in every order, peaks at 1.72ε. 4ε leaves
  twice the measured gap and is a fifth of the clamp triangle's. The tests refuse 0.1,
  0.2 and 0.3 in each unit, refuse the sweep, and pin the boundary: a gap of 4ε is flat
  and of 5ε a triangle. Mutants of 3ε and 5ε fail the boundary test, and no tolerance
  fails the decimals tests.
* **N is a count** (UI/UX's M2), shown `6`, with a unit or a percent refused; KI-025 is
  resolved. ADR-0005's amendment of this date has the dimension.
* **The command line never reads a result's symbol as an input** (S&R's L2). In any case,
  `B` matched only the side `b`, so `geometry.right_triangle a=3 B=30` read the angle B
  as the leg b. A name matched in any case must now match one symbol only, the results'
  among them, or it's refused naming each: "could be b/leg_b, B/angle_b (a result)". An
  exact key or symbol still comes first, so `b=30` is the leg, and a lowercase name that
  matches one thing, such as `leg_b`, still reads.
* **The half-way fractions** (S&R's L1) are ADR-0019's amendment of this date: 3/32 in
  is 1/8" in the Length converter's feet and inches and its nearest 1/16 inch.

### 2026-10-19: the reviews' findings, fix round 2 (group C, display, copy and speech)

* **The error rows are signed and say which way they run** (UI/UX's L1): `+0.002500 in`
  (`Output.signed`), with the user guide's sentence as the label's tooltip (ADR-0017's
  amendment of this date). The label keeps its words, "Error of the nearest 1/16".
* **An error within the value's own last place is 0** (S&R's Note 2). 411.1625 mm is
  16 3/16 in exactly, but as doubles the fraction built in inches is one unit in the last
  place from the value, an error of -2.2e-15 in that Copy full precision gave. Where the
  fraction is within one ulp of the value, the fraction is recorded as the value itself,
  so `E16 = N16 − X` is exactly 0 and the fraction shown is the same. This keeps the rows
  honest: a value can't be told from the fraction closer than its own last place, which
  is all such an error measures. A value typed in inches as the fraction was 0 already.
* **A whole circle's chord is exactly 0** (S&R's Note 2): `sind(180)` is 0 (ADR-0004's
  amendment). At 180° the chord is 20 for r = 10, exactly, and the sagitta
  9.999999999999998, which every shown precision and Copy full precision's 10 digits
  give as 10; a sagitta of exactly r there would need an exact sin²(45°), which a double
  hasn't, so it's left.
* **An angle that's 90° to the arithmetic is refused in both angle methods** (S&R's
  Note 3). Within about 6e-11° of 90°, `tand(A)` is undefined, so `leg_angle` failed in
  its work while `hypotenuse_angle` gave, for c = 1 mm, a leg b of 8.7e-13 mm. Both now
  refuse it before computing, saying since fix round 4: "Angle A (opposite a) is so near
  90° that it counts as 90° to the arithmetic: give an angle further below 90°".
* **The locators** (S&R's Note 1): MH31's "Dimensions of Plane Figures" is printed
  pp. 75–80, and the table of regular polygons on p. 82 is under "Polygons", pp. 81–82,
  cited so; p. 101's running head is "Solution of Oblique Triangles". The arc's methods
  add the *Pocket Companion*'s "Segments of Circles", pp. 7–9, as a second "see also".
* **The disclaimer** is one line for every family (S&R's Note 5; ADR-0020's amendment of
  this date).
* **Speech** (UI/UX's L3 and L4): every negative is "minus …", and "1 and a quarter
  inches", "1 and a half inches" (ADR-0020's amendment). "Copy with unit" isn't offered
  for a compound form (UI/UX's L2).

### 2026-10-19: the cloud review's findings, fix round 3 (group D, numerics)

* **Kahan's angles** (the review's Major 3). The law of cosines, clamped, lost a small
  angle's digits: sides (10, 10, 1e−7) gave C = 0 where it's 5.73e−7°, and (1, 1, 1e−6)
  was wrong in the fourth figure. Each angle is now Kahan's half-angle formula, from the
  lecture notes already cited: with the angle's two other sides p ≥ q and the opposite
  side s, `2·atan(√(((p − q) + s)·μ / ((p + (q + s))·((p − s) + q))))`, with μ as
  `s − (p − q)` where q ≥ s and `q − (p − s)` otherwise. The work shows each angle's
  arrangement. It's the law of cosines (MH31 p. 96) rearranged, and still a deliberate
  departure from MH31 p. 101's law-of-sines step.
  * **No clamp.** For a triangle that passes the flat check, every factor under the
    root is 0 or more, and arctan takes any value. The cosine that rounded past 1, for
    sides (0.0716…, 4.4789…, 4.5505…), was clamped to A = 0; Kahan gives the true
    7.10072e−7°. One that rounds past −1 needs a gap under about 0.7ε of the longest
    side, so it's refused as flat: sides 80.572, 10.817 and 91.389 are one.
  * **Tests** compare every angle, in every order of the sides, with 50-digit mpmath
    values held as literals, to 1e−12 relative: two needles, an obtuse C (3, 5, 7), the
    clamp's triangle and one 5ε short of flat. The plain law of cosines, the other μ
    arrangement, and the law of sines for C fail them; so does a right triangle's angle
    off by a part in a million.
* **A stress too large for its smaller units is refused** (the review's Major 4).
  Stress is held in MPa, larger than kPa and psi, so 1e308 MPa is finite and its kPa
  and psi rows overflow. Making kPa the base, as the length's is its smallest unit, was
  considered and not done: MPa is the stress base unit in JSON, in the materials data and
  in messages (ADR-0005's and ADR-0014's), a public format. A converter now refuses a
  value whose row in its smallest unit would overflow, naming the limit, and a test runs
  ±max, 1e308 and ±5e−324 through every converter with no row infinite or not a number.
  A typed number too large for the base unit, such as `1e308 ft`, is refused as "too large
  to calculate with", not as "not a finite number".
* **The polygon's N is at most 1 000 000.** N = 1e300 failed in the area's arithmetic
  with internal text; it's now refused by the range. A polygon of a million sides is its
  circle to about 2 parts in 10¹², far finer than any drawing. Tests pin the odd
  polygon's note at N = 3, 5, 7, 9 and 13 and its absence at even N, and a count a hair
  off whole, such as 4 + 2⁻⁴⁰.

### 2026-10-19: the cloud review's findings, fix round 3 (group E, CLI, core and window)

* **The command line refuses an input it would lose** (the review's Major 2, second
  half). An input the chosen method doesn't use was dropped, so `a=3 B=30 --method
  leg_angle` ran with A at its default, and an input given twice kept the later value.
  Both are now refused, exit 2, with one line naming the method and its inputs, such as
  "Method 'legs' of geometry.right_triangle doesn't use A=30; its inputs are a/leg_a,
  b/leg_b". A differential check ran 2,616 valid sheet-metal invocations (every method,
  every subset of its inputs, by symbol, key and upper case, with `--units mm`, `--json`
  and `--fraction 64`) on the commit before and after: every exit code and output is the
  same. The 34 that give an unused or repeated input now exit 2.
* **Plugin families follow the built-ins, sorted by name** (Minor 4; ADR-0013's
  amendment): their order followed `importlib.metadata`, and so the file system.
* **The window's "open on a built-in" guard is tested** (Minor 5): a plugin's
  calculator in a built-in family, named to sort first, isn't the page the window opens
  on. With plugin families now after the built-ins, that's the case the guard is for, and
  its comment says so.
* **One value per output** (ADR-0004's amendment), and **a form output can't give a
  precision**: `_check_output_unit` refuses it, since a form has its own fineness, as it
  already refused a precision with no unit.
* **`get_unit` with a dimension that has neither unit** raises `UsageError` for a mark
  the foot and the minute of arc share, such as `get_unit("'", Dimension.RATIO)`, which
  gave the foot on main. It's kept, as the right answer, and declared in the CHANGELOG
  (ADR-0019's u3b amendment has the lookup rule).

### 2026-10-19: the cloud review's findings, fix round 3 (group F, text and docs)

* **The caliper note says how it's held** (Minor 3): "a caliper held from a flat to the
  opposite corner reads r + R"; turned, it reads more, up to 1.6180 in for a pentagon of
  side 1 in against r + R's 1.5388.
* **The converters' note says what the code does** (m2 Minor 1): the typed value is
  read through its unit's factor, then converted to each row's unit, each factor its
  exact definition rounded once; rows aren't converted "from the exact definitions,
  rounded once".
* **The command line's label column** is as wide as the longest label, at least 32
  characters, so "Across corners (circumscribed circle)" no longer pushes its value out
  of line; every sheet-metal result is laid out as before.
* **Not now:** each JSON row in its own unit or form (m2 Minor 4) changes a public
  format, so it's an open decision in the roadmap. S&R checked SP 811's B.8 factors
  against the printed publication, which the cloud review couldn't reach; they match.

### 2026-10-19: the cloud review's round-2 findings, fix round 4 (group G, code and tests)

* **A hypotenuse equal to its leg in another unit is refused** (Medium 1): `a=39 in`
  and `c=990.6 mm` gave b = 0 and A = 90°. The leg and hypotenuse are equal within
  `FLAT_GAP`, 4ε of the hypotenuse, as a flat triangle's sides are; equal lengths typed
  in two units differed by at most 1.94ε over 40,000 pairs. Tests refuse 2,000 such
  pairs both ways and pin the bound (4ε refused, 5ε a triangle); a strict test, 3ε and
  5ε each fail them.
* **An angle that counts as 90° to the arithmetic says so** (Low 2): "Angle A (opposite
  a) is so near 90° that it counts as 90° to the arithmetic: give an angle further
  below 90°". 90° itself is still the range's "must be less than 90°".
* **The command line offers only names that can be given** (Note): `B=30` for the
  right triangle is "isn't one: as written it's a result, angle_b. Did you mean b/leg_b?
  Give it exactly".
* **A count from 2⁵³ on is refused** (the review's note): 2⁵³ + 1 reads as 2⁵³, so a
  double can't hold it exactly; `COUNT_LIMIT`, in the parser and `Param.check`.
* **`tand` is exactly 0 at a whole multiple of 180°**, as `sind` is (ADR-0004's
  amendment). An error's work line shows its sign as its row does (`Step.signed`, from
  the output it gives; JSON's shape is unchanged), and an output in a form can't be
  signed.
* **Tests for the surviving mutants** (Low 4): the disclaimer translated at each of its
  three sites, the TSV keeping a "+" value a number, and full precision without the "+".
  Every long page in the layout test is a built-in calculator.
* **The disclaimer** is the maintainer's line (ADR-0020's amendment of this date).
