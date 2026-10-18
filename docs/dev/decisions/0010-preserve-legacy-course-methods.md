# ADR-0010: Preserve the legacy course methods alongside general methods

* **Status:** Accepted
* **Date:** 2026-10-16

## Context

The original coursework taught specific formulas, such as `BA = 0.64T + 1.57R` for 90°
bends (*Machinery's Handbook* Eq. 33). Students and instructors need answers that match the
course exactly. Those formulas are also material-specific approximations (K ≈ 0.408),
and the cone sheet uses two different diameter bases (KI-001).

## Decision

* Every legacy formula is implemented as its own **method**, keyed `course`, with
  `legacy=True`. Golden tests pin it to the spreadsheet's cached values. Its verification
  status is tracked separately (ADR-0004).
* General methods (K-factor, mean-diameter cone, ...) sit next to it as separate methods.
* We **never "fix" the legacy method in place**. If a legacy formula is shown to be wrong,
  it stays available (and is documented as wrong in known-issues and the method notes),
  and the corrected approach becomes another method.
* Legacy methods are not the default when a better-verified method exists. For now,
  `course` is listed first because it is the only method with checked numbers.

## Consequences

* Coursework answers stay reproducible forever.
* Users always see which method produced a number, and how far it has been checked.

## Amendments

### 2026-10-17: guards on impossible input

* With the maintainer's approval, a legacy method may refuse input where the method's
  formula gives a meaningless result, such as a zero or negative angle, or a division by
  zero. Such a guard changes no formula and no result for valid input: it only turns a
  meaningless answer into an input error.
* The first is the cone's course method, which now refuses a bottom diameter no larger
  than the thickness, as the mean-diameter method does (KI-021, resolved). The
  maintainer: "Yes, add the same input guard to the course cone method; it doesn't change
  the formula." Its golden tests pass unchanged.
