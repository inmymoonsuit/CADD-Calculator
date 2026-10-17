# CADD Calculator: user guide

CADD Calculator answers the numeric questions that come up while drafting: how long to
cut a part so it bends to the right size, what V-die to use, and how to lay out a cone.
Every answer shows its work.

* [Getting started](getting-started.md): install it and run your first calculation
* [Sheet-metal calculators](calculators/sheet-metal.md): what each one computes, and the formulas
* [Units and precision](units-and-precision.md): typing fractions and mm, rounding
* [Glossary](glossary.md): bend angle, K-factor, outside setback, and other terms

## How to read a result

Each result shows:

1. **Results**, the numbers you asked for, rounded for display only.
2. **Work**, each formula in symbols, then with your numbers substituted, then the value.
3. **Method**, which formula family was used, with references and a **status**:

| Status | Meaning |
|---|---|
| `verified` | Checked against a cited published source, with a worked example in the test suite |
| `unverified` | Not yet checked against a published worked example. Use with care. |
| `· reproduces legacy` (added to either) | Matches the original course spreadsheets exactly. Good for coursework; see the method notes for caveats. |

4. **Warnings**, such as a radius smaller than the thickness, or a segment too short for its bends.

## Disclaimer

Results are for drafting and education. Real parts depend on tooling, material lot,
grain direction, temper, and bending method. Verify against your shop's data and test
bends before manufacturing. The software comes with no warranty.
