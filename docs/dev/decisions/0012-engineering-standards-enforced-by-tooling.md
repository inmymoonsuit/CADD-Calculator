# ADR-0012: Write down the engineering standards, and enforce them with tooling

* **Status:** Accepted
* **Date:** 2026-10-17

## Context

The maintainer's experience on a larger project is that problems introduced early grow
expensive later. Examples are boundary violations, patch-style workarounds, and long
comments that go stale. The usual causes are standards that exist only in people's
heads, and rules nothing checks. This project is small, and fixing the codebase is cheap
now.

A measurement on 2026-10-17 shows the starting point. The codebase passed ruff's basic
rule set and `mypy --strict`, yet:

* `core.registry.default_registry()` imported `caddcalc.calculators` inside the function,
  so the bottom layer depended on the layer above it.
* About 75 public functions, classes, and methods had no docstring.
* Some comments and config notes carried dates, measurements, and version-specific bug
  history.

## Decision

1. **The written standard is [engineering-guidelines.md](../engineering-guidelines.md).**
   [AGENTS.md](../../../AGENTS.md) and [CONTRIBUTING.md](../../../CONTRIBUTING.md) point
   to it.
2. **Enforce what can be enforced, in CI:**
   * **Layers** (ADR-0003) with [import-linter](https://import-linter.readthedocs.io/):
     a `layers` contract (CLI, then GUI, then calculators, then core) and a `forbidden`
     contract that keeps Qt out of core, calculators, and the branding loader. Unlike the
     earlier custom test, it also catches imports inside functions.
   * **Docstrings** with ruff's pydocstyle rules, using the Google convention
     ([PEP 257](https://peps.python.org/pep-0257/),
     [Google Python Style Guide §3.8](https://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings)).
   * **Best-practice lint families** in ruff: pep8-naming, comprehensions, returns,
     pathlib, tidy imports (absolute only), pygrep hooks (no blanket suppressions),
     eradicate (no commented-out code), blind except, unused arguments, pylint errors
     and warnings, and bandit security rules. Each one left out is listed with a reason
     in the guidelines (§6).
   * `mypy --strict` and the test suite, as before.
3. **Perishable prose lives in the docs.** History, measurements, status, and long
   explanations go in the engineering log, ADRs, known issues, or design docs, and code
   points to them with a short reference (guidelines §3.3).
4. **Fix the current codebase now** to meet these standards, in the same change. That
   means moving registry composition into the calculators layer, adding the missing
   docstrings, and moving perishable comments into the docs.

## Consequences

* New contributors and AI agents get a single, specific standard, and CI reports
  violations before review.
* Docstrings and comments cost a little more to write, but less to maintain, because
  they don't need updates when facts elsewhere change.
* Some rules need justified exemptions, such as Qt's camelCase overrides and the
  packaging tools' subprocess calls. Every exemption is visible as a named suppression or
  a per-file setting, with a reason.

## Alternatives considered

* **Guidelines without enforcement:** they drift. This is what the maintainer wants to
  avoid.
* **A custom script for import boundaries** (the earlier stdlib-only test): it can't see
  imports between internal layers. import-linter is the established tool for this. The
  stdlib-only test stays, because import-linter's `forbidden` contracts must name
  packages one at a time.
* **Every ruff rule family:** some are noisy for engineering code (magic numbers) or
  clash with Qt's API (boolean positional arguments). The guidelines list what is left
  out, and why.
