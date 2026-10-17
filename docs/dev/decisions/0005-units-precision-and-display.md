# ADR-0005: Units, numeric precision, and display rounding

* **Status:** Accepted
* **Date:** 2026-10-16

## Context

Drafters work in decimal inches, fractional inches (to 1/64"), feet-and-inches, and
millimetres, often mixed. Rounding too early is a classic source of flat-pattern error.
Excel used IEEE-754 doubles, and the golden tests must match it.

## Decision

* **Dimensions:** `LENGTH`, `ANGLE`, `RATIO`. More (force, stress, area, ...) will be added
  when a domain needs them, each with an ADR amendment.
* **Base units:** millimetre for length, degree for angle, and plain numbers for ratios.
  All calculation happens in base units. Conversion happens only when parsing input and
  formatting output.
* **Input parsing** (`parse_quantity`) accepts decimals, fractions, and mixed numbers
  (`1/8`, `1-1/2`, `1 1/2`), unit suffixes (`in`, `"`, `mm`, `ft`, `'`, `°`, `rad`, `%`),
  and a default unit (the user's unit system) when none is typed.
* **Numbers are IEEE doubles** (Python `float`). We do not use `Decimal`: the formulas are
  transcendental (trig, π, √), and doubles match the legacy spreadsheets.
* **Rounding only happens for display** (`DisplayPrefs`: decimals, length unit, optional
  nearest-fraction such as 1/64"). Stored and exported (JSON) results are full precision,
  in base units, and name their unit.
* Angles always display in degrees, by drafting convention.
* Expressions use degree-based trig helpers (`sind`, `cosd`, `tand`, ...), so formulas read
  like the textbook.

## Consequences

* Inch to mm to inch round trips cost about 1e-15 relative. Tests use `rel=1e-12`.
* "Show work" substitutes values in display units. That is only meaningful for
  *dimensionally homogeneous* formulas. Formulas with unit-specific empirical constants
  (e.g. press-brake tonnage in tons/ft) must convert explicitly and say so (KI-005).
* We own a small units module instead of depending on `pint` (ADR-0003). Pint also does
  not parse drafting notation such as `1-1/2"`.

## Alternatives considered

* **Calculate in the user's unit**: simpler for homogeneous formulas, but it breaks with
  mixed-unit input and with empirical formulas.
* **Base length in inches**: equally valid. We chose mm because SI base units are
  conventional and the choice is invisible to users.
* **`pint`**: robust, but a dependency, with no fractional-inch parsing.

## Revisit when

* Feet-and-inches input (`3'-4 1/2"`) is implemented (KI-009).
* A domain needs forces, stresses, or areas.
