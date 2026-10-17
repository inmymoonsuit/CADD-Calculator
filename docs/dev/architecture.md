# Architecture

This is the short version. The *why* is in the [ADRs](decisions/README.md).

## Layers

```
┌──────────────────────── front ends (no formulas) ────────────────────────┐
│  caddcalc.gui (PySide6)    caddcalc.cli (argparse)    future: web, CAD   │
│  gui.branding: optional branding packs, no Qt imports (ADR-0011)         │
└──────────────────────────────────┬────────────────────────────────────────┘
                                   ▼
┌────────────── caddcalc.calculators.<domain>  (stdlib only) ──────────────┐
│  sheet_metal: BendAllowance, FormedSegmentFlatLength, VDieOpening,       │
│               TruncatedConeLayout                                        │
│  (future)   tolerancing, fasteners, structural, geometry, ...            │
└──────────────────────────────────┬────────────────────────────────────────┘
                                   ▼
┌───────────────────── caddcalc.core  (stdlib only) ───────────────────────┐
│  units.py       Dimension, Unit, parse_quantity (fractions, suffixes)    │
│  expr.py        safe formula evaluator + symbolic/numeric rendering      │
│  spec.py        Param, Output, Method, Verification, OutOfRangeError     │
│  reference.py   Reference: a citation (title, detail, URL)               │
│  calculator.py  Calculator (base), Context, Step, Result                 │
│  provenance.py  SourceKind, InputSource: where each input came from      │
│  notes.py       Note, NoteKind: warnings and limits a result carries     │
│  domain.py      Domain: a calculator family and its shared settings      │
│  registry.py    Registry of domains and calculators; plugin loading      │
│  settings.py    DomainSettings: domain settings for the session          │
│  formatting.py  DisplayPrefs, rounding, fractions, render_step           │
└───────────────────────────────────────────────────────────────────────────┘
```

## Lifecycle of a calculation

1. A front end calls `caddcalc.calculators.default_registry()`, which registers the built-ins
   and any plugins, and looks up a calculator by ID (e.g. `sheet_metal.bend_allowance`).
2. It builds a form or argument list from `calc.params_for(method)`.
3. User text goes through `parse_quantity(text, dimension, default_unit)` and becomes **base units**.
4. `calc.run(inputs, method, settings=...)` picks each input by the precedence rule
   (explicit, then a shared parameter's domain setting, then the default; ADR-0013),
   range-checks it, records its source, and calls `compute(ctx)`.
5. `compute` calls `ctx.calc("BA", "pi/180*A*(R + K*T)", ...)`. The formula string is
   evaluated by `core.expr` *and* stored as a `Step`.
6. It returns a `Result`: outputs, steps, symbols, warnings, and each input's source,
   all in base units.
7. The front end formats it with `DisplayPrefs`. Rounding only happens here.
   `render_step` produces the three-line work: `BA = π/180·A·(R + K·T)`, the substituted
   values, and the result.

## Adding a calculator

See [CONTRIBUTING.md](../../CONTRIBUTING.md#adding-a-calculator). In short: subclass
`Calculator`, declare params, outputs, and methods with references and verification
status, write `compute` with `ctx.calc`, add it to the domain's `CALCULATORS` tuple, and add
tests (a golden or worked example per method).

## Invariants (enforced in CI)

The full rule set is in [engineering-guidelines.md](engineering-guidelines.md).


* Layers import only downward: CLI, then GUI, then calculators, then core. Function-level
  imports count too (`uv run lint-imports`).
* `caddcalc.core` and `caddcalc.calculators` import nothing outside the standard library,
  and they and `gui.branding` never import Qt.
* Every method of every built-in calculator runs on its defaults, and every step renders.
* A method that is `verified` or flagged `legacy` has at least one reference.
* Legacy methods reproduce the spreadsheet values to 1e-12 relative.
* Calculator IDs, parameter keys, and method keys are stable public API (ADR-0006).

## Repository layout

```
src/caddcalc/            the package (src layout)
tests/                   pytest; golden legacy tests in test_legacy_golden.py
docs/dev/                developer docs (this folder)
docs/user/               user docs
.github/                 CI workflow, issue and PR templates
packaging/               build script, packaged-app launcher, icon helpers (packaging.md)
scripts/                 developer launcher for the work-in-progress app (launching.md)
resources/   (ignored)   local-only legacy and third-party material (ADR-0008)
branding/    (ignored)   local branding packs for branded editions (ADR-0011)
builds/      (ignored)   local packaging output
```
