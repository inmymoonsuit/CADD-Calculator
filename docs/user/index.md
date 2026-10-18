# CADD Calculator: user guide

CADD Calculator answers the numeric questions that come up while drafting: the area or
angles of a shape, how long to cut a part so it bends to the right size, what V-die to
use, and how to lay out a cone.
Every answer shows its work.

* [Getting started](getting-started.md): install it and run your first calculation
* [Geometry calculators](calculators/geometry.md): circles, rectangles, triangles, polygons, arcs
* [Sheet-metal calculators](calculators/sheet-metal.md): what each one computes, and the formulas
* [Results and copying](results.md): the result fields, copying values, the keyboard
* [Units and precision](units-and-precision.md): typing fractions and mm, rounding
* [Glossary](glossary.md): bend angle, K-factor, outside setback, and other terms

## How to read a result

Each result shows:

1. **Inputs**, with where each value came from: *entered* (you typed it), *default*
   (the calculator's built-in value), or a family setting such as *Sheet Metal
   settings*.
2. **Results**, the numbers you asked for, rounded for display only. In the desktop app
   they sit in their own fields, which you can copy from; see
   [Results and copying](results.md).
3. **Work**, each formula in symbols, then with your numbers substituted, then the value.
4. **Method**, which formula family was used, with references and a **status**:

| Status | Meaning |
|---|---|
| `verified` | Checked against a cited published source, with a worked example in the test suite |
| `unverified` | Not yet checked against a published worked example. Use with care. |
| `· reproduces legacy` (added to either) | Matches the original course spreadsheets exactly. Good for coursework; see the method notes for caveats. |

5. **Notes**, such as a radius smaller than the thickness, or a segment too short for its
   bends. Each leads with its verdict and numbers, then says what its sources give, then
   names them. In the desktop app they come strongest first. Each is marked by kind:
   * a *warning*: something to check, such as a rule of thumb
   * *limit exceeded*: past a limit a cited source states, shown in red with the source
   * *no applicable value*: no source covers the case, so it couldn't be checked
   * *not makeable*: the inputs describe something that can't be made, shown in red; the
     numbers are still shown so you can see why

   In the desktop app, the input fields a note concerns are outlined.

## Disclaimer

Results are for drafting and education. Real parts depend on tooling, material lot,
grain direction, temper, and bending method. Verify against your shop's data and test
bends before manufacturing. The software comes with no warranty.
