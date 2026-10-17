# ADR-0003: Layered architecture with a dependency-free core

* **Status:** Accepted
* **Date:** 2026-10-16

## Context

The Excel prototype mixed inputs, formulas, presentation, and navigation in the same
sheets and forms, so nothing could be tested or reused on its own. We expect several front
ends (GUI, CLI, maybe web or plugins inside CAD tools) and many calculator domains.

## Decision

Three layers with one-way dependencies:

```
caddcalc.gui  ─┐
caddcalc.cli  ─┼──▶  caddcalc.calculators.<domain>  ──▶  caddcalc.core
(future web)  ─┘
```

* `caddcalc.core` is the framework: units, the expression evaluator, Param/Output/Method,
  Calculator, Result, and Registry. **Standard library only.**
* `caddcalc.calculators.*` holds one subpackage per domain. It depends only on `core`.
  **Standard library only**, unless an ADR approves a dependency.
* Front ends depend on the layers below. They contain **no formulas**: every form is
  generated from calculator metadata.

## Consequences

* The core installs anywhere, fast, with nothing to break (including Pyodide, embedded
  Python, and CAD scripting consoles).
* Every calculator gets the GUI, CLI, JSON output, and "show work" for free.
* We write a little more ourselves (a small units module and an expression evaluator)
  instead of pulling in `pint` or `sympy`. See ADR-0005.
* Any third-party dependency in core or calculators needs a new ADR.

## Alternatives considered

* **Formulas inside GUI handlers**, which is how the VBA version worked. Untestable, and
  duplicated in every front end.
* **Depending on numpy, pint, or sympy from the start**: heavier installs and packaging for
  no current benefit. We can revisit for domains that need them, such as structural
  section properties.
