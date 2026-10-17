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
