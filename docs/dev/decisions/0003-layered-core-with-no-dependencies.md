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

## Amendments

### 2026-10-17: domains and session settings (ADR-0013)

* `core` gains the machinery for calculator families, all standard library: `Domain`
  and `DomainValues` (`core.domain`), the session's `DomainSettings` (`core.settings`),
  input provenance (`core.provenance`), citations (`core.reference`), and result notes
  (`core.notes`).
* `DomainSettings` is a pure, immutable model. Core holds no session state: the GUI owns
  the one instance for its window, and the CLI needs none.
* Engineering behavior stays below the front ends: the precedence rule, validation, and
  the wording of sources, errors, and notes (`core.formatting`). A settings feature
  handled in the GUI alone was rejected for that reason (ADR-0013, alternatives).
* `calculators` decides which domains exist (`BUILTIN_DOMAINS`), as it already decides
  which calculators do.
* `core`, `calculators`, and `gui.branding` never import Qt, which an import-linter
  contract enforces alongside the layer order.

### 2026-10-28: a preferences layer (ADR-0025)

Once ADR-0025 is accepted, the layers become:

```
caddcalc.cli ──▶ caddcalc.gui ──▶ caddcalc.preferences ──▶ caddcalc.calculators ──▶ caddcalc.core
```

* `caddcalc.preferences` holds the saved preferences' model, the folder resolver, and
  the store (ADR-0025 §2). It's **standard library only**, and may import `core`.
* It never imports Qt, nor does the GUI's Qt-free `gui.preference_keys`: both join the
  no-Qt contract.
* `core` and `calculators` never import it: nothing below the front ends reads a
  preference (ADR-0025 §1). That's why it isn't in `core` (ADR-0025 C1).
* `caddcalc.cli` never imports it directly (ADR-0025 M1), by a forbidden contract that
  allows the indirect import through `caddcalc gui`, which starts the GUI.
* The import-linter contracts, `docs/dev/architecture.md`, and guidelines §1 change in
  the commit that adds the package (ADR-0025's E1), since they describe the code.
