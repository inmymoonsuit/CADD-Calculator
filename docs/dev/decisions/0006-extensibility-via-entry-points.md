# ADR-0006: Extensibility, with built-ins listed explicitly and plugins found via entry points

* **Status:** Accepted
* **Date:** 2026-10-16

## Context

We want new calculator domains (structural, tolerancing, threads, piping, ...) added both
in this repository and by third parties, such as a shop's private calculators, without
forking the app.

## Decision

* **Built-in calculators** live in `caddcalc.calculators.<domain>`. Each domain package
  exposes a `CALCULATORS` tuple, and `caddcalc.calculators.BUILTIN_CALCULATORS` lists them.
  The list is explicit, not discovered, so compiled and frozen builds (Nuitka, ADR-0009)
  don't depend on package metadata being bundled.
* **Third-party calculators** register through the Python entry-point group
  `caddcalc.calculators`. Each entry point names a `Calculator` subclass or an iterable
  of them.
* `Registry.register` validates every calculator's spec: ID format, unique keys and
  symbols, and that each method a parameter names exists. A plugin that fails to load is
  recorded in `registry.plugin_errors` and shown to the user. **It never crashes the app.**
* Calculator IDs (`domain.name`), parameter keys, and method keys are a **public,
  stable API**: saved files, the CLI, and scripts depend on them. Renaming one is a breaking
  change and needs a deprecation alias.

## Consequences

* A shop can `pip install` a private package and its calculators show up in the GUI and CLI.
* Plugins run arbitrary Python when loaded, so installing a plugin means trusting it.
  We will say so in the user docs.
* The frozen desktop app cannot `pip install` plugins. A "plugins folder" for the
  packaged app is future work (roadmap).

## Alternatives considered

* **Discovering built-ins through entry points too**: elegant, but fragile in frozen builds.
* **Scanning a folder and importing every .py file**: no packaging or versioning story.
