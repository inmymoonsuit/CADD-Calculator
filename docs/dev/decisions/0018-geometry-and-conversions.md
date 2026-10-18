# ADR-0018: Geometry and Conversions families

* **Status:** **Accepted** (not built). The maintainer approved the scope below on
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
  MH29, Mathematics: "Areas and Volumes" (printed pp. 70–76) and "Solution of Triangles"
  (pp. 95–102); the DLMF §4.42 is a second source for the triangles. Citing a formula in
  a method is not reference data, so ADR-0014's cap doesn't apply (ADR-0014 D7
  amendment). Constants are computed with `math.pi` and `math.radians`, not MH29's
  rounded ones.
* **Each triangle angle comes from the law of cosines** (MH29 p. 96). MH29's three-sides
  procedure (p. 102) takes the second angle from the law of sines, which can't return an
  obtuse angle: sides 3, 7, 5 would give 60° where the answer is 120°.
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
