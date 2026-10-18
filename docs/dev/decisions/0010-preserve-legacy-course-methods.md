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

### 2026-10-18: methods verified by published worked examples (maintainer)

The maintainer: "We can promote the verified methods based on the published data, yes."

* **A method is verified in a calculator** only where a published worked example runs
  through that calculator, as a test in `tests/test_published_examples.py`, which also
  checks that no other method is verified. The course and K-factor methods are shared by
  the two bend calculators, so each has its own copy.

  | Calculator | Method | Verified by | Scope |
  |---|---|---|---|
  | `bend_allowance` | `course` (Fixed K-factor) | MH31 Fig. 13, p. 1421: a soft-steel part's bend allowances, 1.338 at 180° and 0.707 at 60°, and its flat length, 5.545 | Eq. (33)'s materials, its 90° value scaled by A/90. The example checks the allowance, not the setback or the deduction. Its 180° bend is the 90° value scaled, since the calculator refuses 180° (KI-014). |
  | `bend_allowance` | `k_factor` | EDD5 Fig. 19.12, p. 785: Z = 0.275 | 90° only; the allowance |
  | `segment_flat_length` | `k_factor` | the same example: the flat length, 16.900 | 90° only, a part with one bend; past 90°, KI-013 |

* **Each method's notes** say what its example checks, and the method cites it.
* **Still unverified:** the course method in `segment_flat_length`, which no published
  example runs through for a segment's flat length; the cone methods (KI-001, KI-007);
  and the V-die rules (KI-003, KI-004).
* **The course method stays legacy** (`legacy=True`), so its status reads "verified for
  BA · reproduces legacy" in `bend_allowance`, and "unverified · reproduces legacy" in
  `segment_flat_length`. Verification and legacy are independent (ADR-0004).
* **The default method is unchanged:** the course method is still listed first in both
  calculators. The decision above says a legacy method isn't the default where a
  better-verified method exists, and the roadmap's open decision recommends the course
  formula first until a general method is verified. The K-factor now is, at 90°, so
  which method opens first is the maintainer's call, still open.
* **Each status says what its example covers** (UI/UX's promotion review): a verified
  method's `scope`, a few words, follows "verified", as "verified at 90°" and "verified
  for BA · reproduces legacy". Its `verification_note`, which names the source or says
  why the method isn't verified here, is the status's tooltip and its last note. The
  status keeps the same quiet colour either way, and its label keeps the width of the
  calculator's widest status, so changing the method changes only the words.

### 2026-10-18: the course method renamed "Fixed K-factor (≈ 0.41)" (maintainer)

* **The maintainer:** "I approved keeping the course method as its own method, renamed
  'Fixed K-factor (≈ 0.41)'." It stays a method of its own, since it reproduces the
  course's answers digit for digit, and its name says what it does. Its formula,
  0.64T + 1.57R, is the neutral-axis arc with K fixed at about 0.408 (0.64/1.57) and π/2
  rounded to 1.57.
* **Unchanged:** its key, `course`, so saved command lines and JSON keep working;
  `legacy=True`; the golden tests; and the default method.
* **Its notes** say that the Handbook's Eqs (32) to (34) have the same form as the arc,
  with K about
  0.35, 0.41 and 0.45, and that with K = 0.4074 the K-factor method gives the same 0.64·T
  and a radius term 0.05% larger, π/2 against 1.57, so the two can differ in the fourth
  decimal. The CLI's and JSON's method label follow the name.
