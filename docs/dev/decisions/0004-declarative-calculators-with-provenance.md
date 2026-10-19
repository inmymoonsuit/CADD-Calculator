# ADR-0004: Declarative calculators, with formulas as data, provenance, and a verification status

* **Status:** Accepted
* **Date:** 2026-10-16

## Context

The tool will compute values that people use to cut metal. "Industry-standard" values
come from many sources (Machinery's Handbook, textbooks, ASME/ISO standards, press-brake
tooling vendors, shop test bends), and they often disagree. Students also need to *see
the work*, not just the answer. The legacy spreadsheets had good formulas but no record
of where they came from.

## Decision

Every calculator is a `Calculator` subclass that **declares**:

* `params`: key, formula symbol, label, dimension (length/angle/ratio), default, range,
  help text, and which methods use it.
* `outputs`: key, symbol, label, dimension.
* `methods`: one or more ways to compute the outputs. Each has a summary, **references**
  (edition, section, page; never copied text), notes, and a **verification status**:
  * `unverified`: no published worked example has been checked yet.
  * `verified`: checked against at least one cited published source, with that worked
    example committed as a test.

  A separate **`legacy`** flag means the method reproduces the original course spreadsheets
  exactly (golden tests). The two are independent, so a method can be "verified ·
  reproduces legacy". (Amended 2026-10-16. The first draft used a single ladder with
  `reproduces-legacy` between the two, which couldn't say both.)

`compute(ctx)` builds results with `ctx.calc(symbol, "formula", ...)`. The formula string is
**both evaluated and displayed** by `caddcalc.core.expr`, a whitelisted AST evaluator
that never calls `eval`. The displayed work therefore cannot disagree with the computed value.
`ctx.record(...)` covers values computed in code, such as table lookups, and requires a note.
`ctx.warn(...)` adds engineering warnings, e.g. a radius below the material's minimum.

The front ends show the method, status, references, and a disclaimer next to every result.

## Consequences

* Adding a calculator means declaring metadata and writing formulas. No GUI or CLI code.
* "Show work" comes free and is trustworthy. That matters for teaching and for audits.
* Disagreeing sources become *methods*, not arguments: we can offer the course formula,
  the K-factor method, and later a vendor's table side by side.
* Formulas are limited to the expression language (arithmetic, `sqrt`, degree-based trig,
  `min`/`max`/`abs`). Anything else goes through `ctx.record` with a note.
* Formula strings are plain data, so a later version could load **user-defined
  calculators or shop-specific methods** from files without code changes. The evaluator
  has no code-execution path. It checks arity, caps formula length, size, and nesting,
  and turns every math failure into a `CalculationError`.
* Tests enforce the rules: every method runs on its defaults, every step renders, and a
  status above `unverified` requires a reference.

## Alternatives considered

* **Plain Python functions plus separate display strings**: the two drift apart.
* **SymPy** for symbolic formulas: powerful but heavy (ADR-0003) and slow to import.
* **Formulas defined only in data files (TOML)**: too limiting for calculators that need
  logic. It can be layered on top later.

## Amendments

### 2026-10-19: sine and cosine are exactly 0 where they are 0 (ADR-0018, fix round 2)

* `sind` is exactly 0 at a whole multiple of 180°, and `cosd` at an odd multiple of 90°.
  The multiple is found exactly, with `math.fmod`, as IEEE 754's `sinPi` and `cosPi`
  are exact at whole numbers (IEEE 754-2019, §9.2). Everywhere else they're computed as
  before, from `radians`, so no other value changes; π/180 is rounded, so
  `sin(radians(180))` is 1.2e-16, which made a whole circle's chord 2.4e-15 in long.
  Support & Review's Note 2 on ADR-0018's m1 found it. No sheet-metal formula uses
  either function, and every golden test passes unchanged.
* `expr.tan_is_undefined` is the test `tand` refuses by, public so a calculator can
  refuse the same angle before another method computes from it (ADR-0018, fix round 2).
