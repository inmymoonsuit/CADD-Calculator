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
  `caddcalc.calculators.default_registry()` assembles the built-ins and plugins. Core only
  provides the `Registry` machinery and never imports the calculators layer.
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

## Amendments

### 2026-10-17: domains as plugins (ADR-0013 §10)

* **A second entry-point group, `caddcalc.domains`,** names a `Domain` or an iterable of
  them. `default_registry()` registers every domain, built-in and plugin, before any
  calculator, because a calculator's domain must already exist.
* A calculator naming an unknown domain fails registration with a "did you mean" hint
  that matches domain IDs and names. A plugin can't redefine a built-in domain.
* An entry point naming an iterable is registered item by item. A bad item is recorded
  as `name[index]` in `plugin_errors`, and the rest still load.
* **Calculator IDs** are lowercase and dotted, with at least two parts. `domain.name`
  above is the built-ins' convention, checked by a test; a plugin may use its own prefix
  in any domain, e.g. `acme.flange_check`.
* The public, stable API also covers domain IDs, domain setting keys, and both
  entry-point group names.
* Tests pass a fake entry-point source (`Registry(entry_points=...)`,
  `default_registry(entry_points=...)`) instead of patching `importlib.metadata`.
