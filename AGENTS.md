# Instructions for AI coding agents

This file is the shared brief for any AI agent working in this repo (Claude Code reads
it through `CLAUDE.md`). Human contributors: see `CONTRIBUTING.md`.

## Project in one paragraph

CADD Calculator is an open-source desktop and CLI app (Python 3.12+, PySide6) of drafting
calculators, starting with sheet metal. It replaces Excel/VBA coursework tools. Layers:
`caddcalc.core` (framework, stdlib only), then `caddcalc.calculators.<domain>` (stdlib only),
then `caddcalc.cli` and `caddcalc.gui`. Read `docs/dev/architecture.md` first.

## Commands

```bash
uv sync --extra gui
uv run pytest                      # all tests; GUI test is offscreen
uv run ruff check . && uv run ruff format --check .
uv run mypy
uv run caddcalc run sheet_metal.bend_allowance --method course
```

Run all four checks before saying work is done.

## Rules

1. **Formulas are sacred.** Never change a formula, default, or golden value without a
   cited source or the maintainer's explicit approval. Never "fix" a legacy `course`
   method; add a new method instead (ADR-0010).
2. **Every method has provenance:** references (edition, section, page) and an honest
   `Verification` status. Never set `verified` without a cited worked example as a test.
3. **Formulas go through `ctx.calc("SYM", "expression", ...)`** so the displayed work
   matches the computation. No formulas in GUI or CLI code.
4. **Base units** inside calculators: mm, degrees, ratio. Round only in `core.formatting`.
5. **Stdlib only** in `core` and `calculators`. A new dependency needs an ADR.
6. **Stable IDs:** calculator IDs, parameter keys, and method keys are public API.
7. **Copyright:** never commit anything from `resources/` (git-ignored). Never copy text or
   tables from the standards or handbooks the maintainer keeps locally. Cite them.
8. **Document as you go, in the same change:**
   * a significant decision gives a new ADR in `docs/dev/decisions/` (and update its index)
   * a failed or reverted attempt gives an entry in `docs/dev/engineering-log.md`
   * a limitation or formula doubt gives a `KI-NNN` in `docs/dev/known-issues.md`
   * changed behavior means updating `docs/user/` and `CHANGELOG.md` (Unreleased)
9. Don't commit or push unless the maintainer asks.

## Terminology

Bend angle = measured from flat (not the included angle). Dimensions are to the outside
mold line. See `docs/user/glossary.md`.
