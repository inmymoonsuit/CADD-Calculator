# Instructions for AI coding agents

The shared brief for any AI agent working in this repo. Claude Code reads it through
`CLAUDE.md`; human contributors start at `CONTRIBUTING.md`. **The full standard is
[docs/dev/engineering-guidelines.md](docs/dev/engineering-guidelines.md). Read it before
changing code.** This file is its summary and doesn't replace it.

## Project in one paragraph

CADD Calculator is an open-source desktop and CLI app (Python 3.12+, PySide6) of drafting
calculators, starting with sheet metal. Its layers, from the bottom up:
1. `caddcalc.core`: the framework, standard library only.
2. `caddcalc.calculators.<domain>`: the calculators, standard library only.
3. `caddcalc.gui`, then `caddcalc.cli` at the top.

Read [docs/dev/architecture.md](docs/dev/architecture.md) and the ADRs in
[docs/dev/decisions/](docs/dev/decisions/README.md) before designing anything.

## Commands

```bash
uv sync --extra gui
uv run ruff check . && uv run ruff format --check .
uv run mypy
uv run lint-imports                # architectural layer contracts
uv run pytest                      # GUI tests run offscreen
```

All five must pass before you report work as done (guidelines §5).

## Non-negotiable rules

1. **Principled design over patches.**
   * Respect the layer boundaries; they are enforced.
   * Fix root causes. A workaround that can't be avoided needs a `KI-` entry, a test,
     and a pointer comment.
   * When a boundary or rule gets in the way, change the design and record an ADR.
     Never route around it.
2. **Research before choosing.** Libraries, tools, formats, and engineering methods come
   from primary sources: official docs, PEPs, standards, textbooks. Check maintenance and
   license, and cite the sources in an ADR.
3. **Formulas are sacred.**
   * Never change a formula, default, or golden value without a cited source or the
     maintainer's explicit approval.
   * Never "fix" a legacy `course` method; add a new method instead (ADR-0010).
   * Every method cites its sources and has an honest `Verification` status.
   * Formulas go through `ctx.calc`. Work in base units, and round only in
     `core.formatting`.
4. **Docstrings and comments** follow PEP 257 with the Google convention.
   * Comments explain *why*.
   * Perishable prose doesn't go in code, comments, or config: history, measurements,
     dates, status words, test figures, or long explanations. It goes in the engineering
     log, an ADR, a `KI-` entry, or a design doc, and the code points there with a short
     reference (guidelines §3.3).
5. **Public surface is stable.** Calculator IDs, parameter keys, method keys, `core`
   exports, file formats, and CLI options need a deprecation path to change.
6. **Copyright and privacy.**
   * Cite standards and handbooks; never copy their text or tables.
   * Branded editions, their permissions, and their art licensing stay outside this
     repository (ADR-0008, item 4). Public files and commit messages describe them only
     in generic terms.
7. **Document in the same change:**
   * an ADR for a decision
   * an engineering-log entry for anything tried and abandoned
   * a `KI-` entry for a new limitation
   * user docs and the CHANGELOG for changed behavior
8. **Don't commit or push unless the maintainer asks.**

## Terminology

The bend angle is measured from flat, not the included angle. Dimensions go to the
outside mold line. See [docs/user/glossary.md](docs/user/glossary.md).
