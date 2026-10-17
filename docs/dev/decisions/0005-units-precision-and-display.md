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

## Amendments

### 2026-10-17: numeric intent (ADR-0013 §9, decision J)

* **Three tiers.** *Intent* is what the user typed: its text and its exact parse in base
  units. *Computation* uses doubles. *Presentation* is rounded display text.
* **Display text is never read back as intent.** A unit switch, an inherited value, and a
  loaded example keep their base value; only the user's own typing creates intent. This
  fixed KI-017, where a unit switch rounded typed values to six decimals.
* `TypedValue` keeps the text, its exact parse, the unit applied, and whether the text
  named that unit, from `parse_quantity_detailed()`; `parse_quantity` wraps it. A
  `TypedValue` built directly must agree with its own text.
* `core.formatting.entry_text()` is the one display rule for a typed value: the user's
  text while it names its unit or its unit is the display unit, and otherwise the value
  converted, through `field_text()`. Unapplied bare-number text gains the unit it was
  typed in when the display unit changes.
* Doubles stay: there is no float32 tier, and the formulas are transcendental.
* A test checks that every `Dimension` has its base unit, display unit, and wording, so
  adding one (such as stress, ADR-0014) can't miss a table.
