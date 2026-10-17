# Engineering guidelines

These rules apply to every change: code, tests, scripts, configuration, and the docs that
go with them, whether a person or an AI agent writes it. ADR-0012 explains why the project
has them. Rules marked **[CI]** are checked automatically; the rest are checked in review.

A change that can't follow a rule should change the design, not bend the rule. When a rule
itself is wrong, change it here in its own pull request, with an ADR if it matters.

## 1. Architecture and boundaries

1. **Layers.** `caddcalc.core` is at the bottom, then `caddcalc.calculators`, then the
   front ends (`caddcalc.gui`, then `caddcalc.cli`). A module imports only from its own
   layer or the layers below it, and that includes imports inside functions.
   **[CI: import-linter]** (ADR-0003)
2. **Dependencies.** `core` and `calculators` use only the Python standard library.
   **[CI: test]** Adding a third-party dependency anywhere needs an ADR.
3. **Qt stays in the GUI.** `core`, `calculators`, and `gui.branding` never import Qt.
   **[CI: import-linter]**
4. **Single responsibility per layer.** Engineering logic (formulas, units, validation,
   the precedence of shared settings) lives in `core` and `calculators`. Front ends only
   present calculator metadata and results; they contain no formulas and no engineering
   decisions. User-facing wording of input sources, errors, and result notes comes from
   `core.formatting`, so every front end says the same thing (ADR-0013 §5).
5. **Composition goes up, not down.** Lower layers expose mechanisms; higher layers decide
   what to assemble. For example, `core` provides `Registry`, and `calculators` decides
   which calculators are registered.
6. **Stable public surface.** Calculator IDs, parameter keys, method keys, domain IDs and
   their setting keys, entry-point group names, the names exported by `caddcalc.core`,
   file formats (`branding.toml`, `palette.toml`, manifests), and CLI options are public.
   Changing one needs a deprecation path and a CHANGELOG entry.
7. **No boundary workarounds.** If a boundary blocks a change, redesign the change and
   record it in an ADR. Don't route around the boundary with a deferred import, a
   duplicated helper, or a callback hook.

## 2. Design and implementation

1. **Research before choosing.** Before adopting a library, tool, algorithm, file format,
   or engineering method, check primary sources: official documentation, PEPs, published
   standards, and textbooks. Also check maintenance status and license compatibility
   (ADR-0008). Record significant choices in an ADR with links to those sources.
2. **Prefer the standard way.** Use the standard library first, then established,
   maintained, permissively licensed packages. Don't hand-roll what a standard tool
   already does well, unless an ADR records why.
3. **Fix root causes.** Don't hide symptoms with retries, sleeps, broad `except`
   blocks, or special cases for a test or machine. If a temporary workaround truly can't
   be avoided, it needs all three of the following:
   * a `KI-` entry in [known-issues.md](known-issues.md)
   * a test that pins the current behavior
   * a one-line comment pointing to the `KI-` entry
4. **No hidden state.** No monkeypatching of third-party code, no import-time side
   effects, and no module-level mutable state except caches with an explicit way to clear
   them. Pass dependencies in (a registry, branding, display preferences, a plugin
   entry-point source) rather than reaching for globals.
5. **Errors.**
   * Raise specific exceptions from the `CaddCalcError` hierarchy, and catch only what
     you can handle. Each kind of error has one meaning: `InputError` for user input
     (`OutOfRangeError` carries the parts of a range error), `SpecError` for a bug in a
     calculator or domain definition, including a bad default, and `UsageError` for
     calling the API wrongly.
   * Catch `Exception` broadly only at an isolation boundary, such as loading a plugin or
     the top of a UI event handler, with a reason on the suppression. **[CI: BLE]**
   * Don't use `assert` for checks in shipped code, because Python skips asserts under
     `-O`. **[CI: S101]**
6. **Types.** Everything in `src/` and `packaging/` passes `mypy --strict`. **[CI]**
7. **Engineering values.**
   * Formulas go through `ctx.calc`, so the displayed work can't drift from the computed
     value (ADR-0004). A value a standard defines, such as a gauge thickness, is computed
     in its domain module by `expr.evaluate_exact` from the one expression its work shows
     (ADR-0014, amendments).
   * Calculations work in base units, and only `core.formatting` rounds (ADR-0005). The
     one exception is a standard's own stated precision, such as a gauge thickness
     published to four decimals: that is data, applied only by
     `core.refdata.nominal()` (ADR-0014, amendments).
   * Display text is never read back as a value. Keep what the user typed as a
     `TypedValue`, and show values through `entry_text` and `field_text` (ADR-0013 §9).
   * Every method cites its source.
8. **Security.**
   * No `eval` or `exec`.
   * Run subprocesses with argument lists, never `shell=True`.
   * Validate paths that come from files or environment variables before using them.
   * Fetch from the network only in developer tools, only from pinned official sources,
     with integrity checks.

   **[CI, in part: bandit `S` rules]**
9. **Tests.**
   * Every behavior change comes with a test.
   * Every formula has a cited worked example.
   * Tests are deterministic, run offline, and don't depend on the machine (fonts, paths,
     installed software). GUI tests run offscreen.

## 3. Comments and docstrings

1. **Standards.** Follow PEP 8 and PEP 257, with the **Google docstring convention**
   (Google Python Style Guide, §3.8). **[CI: ruff `D`, `convention = "google"`]**
   * Every public module, class, function, and method in `src/` and `packaging/` has a
     docstring. Tests are exempt; their names describe the behavior.
   * Start with a one-line summary that ends with a period. Add detail after a blank line.
   * Add `Args:`, `Returns:`, and `Raises:` sections when the signature and types don't
     already make them obvious. Don't restate the types: the annotations are the source
     of truth.
   * Mark inline code with double backticks (``` ``like_this`` ```). That renders as code
     in both reStructuredText and Markdown, so it works whichever docs generator ADR-0007
     settles on. Don't use Sphinx roles such as `:func:`.
   * A method that overrides a documented base method uses `@typing.override` and
     inherits its docstring.
2. **Comments explain *why*, never *what*.** Make the code say what it does: use clear
   names and small functions. A comment earns its place by explaining a reason, a
   constraint, or a non-obvious consequence.
3. **Keep perishable prose out of code.** Code, comments, docstrings, and config files
   hold only statements that stay true for as long as the code is unchanged. Anything
   that can go stale goes in the docs, and the code points there with a short reference:

   | Belongs in the docs, not the code | Where |
   |---|---|
   | History: what was tried, reverted, or replaced | [engineering-log.md](engineering-log.md) |
   | Decisions and their reasons | an ADR in [decisions/](decisions/README.md) |
   | Measurements, benchmarks, timing, test figures, version-specific bugs | the ADR, `KI-` entry, or design doc they support |
   | Status words: dates, "currently", "for now", "temporary", "interim", "new" | a `KI-` entry or the roadmap |
   | Explanations longer than a few lines | the relevant doc under `docs/` |

   The pointer is a short reference, e.g. `# Pinned: see ADR-0009.` or
   `# Workaround for KI-016.` or
   `# See docs/dev/packaging.md, "Troubleshooting".`

   This doesn't cover a test's own data. Expected values and the source they come from
   belong in the test.
4. **No commented-out code.** **[CI: ERA]** Delete it; git has the history.
5. **TODOs** name their tracking entry, as in `TODO(KI-013): …`. A bare TODO isn't
   allowed.
6. **Suppressions** (`# noqa`, `# type: ignore`) name the exact rule and give the reason.
   A suppression that no longer suppresses anything is removed. **[CI: PGH, RUF100]**

## 4. Codebase hygiene

1. **Formatting and linting** use ruff, with the rule set in `pyproject.toml`. **[CI]**
2. **Imports** are absolute, never relative. **[CI: TID]** Use `pathlib`, not `os.path`.
   **[CI: PTH]**
3. **Naming** follows PEP 8. **[CI: N]** A name a framework requires, such as a Qt
   override like `loadResource`, keeps that name, with `# noqa: N802` and the reason.
4. **Files written by tools** are UTF-8 with LF line endings, set explicitly (for example
   `write_text(..., encoding="utf-8", newline="\n")`).
5. **Vendored and generated files** (icons, manifests, lock files) are never edited by
   hand. Regenerate them with their script or tool.
6. **Commits.**
   * Each commit holds one logical change.
   * The subject is imperative.
   * The body explains why.
   * Docs, tests, and the CHANGELOG change in the same commit as the behavior they cover.

## 5. Definition of done

A change is done when all of these hold:

- [ ] `uv run ruff check .` and `uv run ruff format --check .` pass.
- [ ] `uv run mypy` passes.
- [ ] `uv run lint-imports` passes.
- [ ] `uv run pytest` passes, with new tests for new behavior.
- [ ] Docs are updated:
  * user docs
  * an ADR for a significant decision
  * the engineering log for anything tried and abandoned
  * a `KI-` entry for any new limitation
  * the CHANGELOG
- [ ] No perishable prose in code (section 3.3), and no names or details that belong
      only in private notes.

## 6. Lint rules we deliberately don't use

| Rule | Why not |
|---|---|
| `PLR2004` magic values | Engineering constants read best inline next to their citation, as in `0.64*T + 1.57*R`. |
| `FBT` boolean positional arguments | Qt's API takes positional booleans, as in `blockSignals(True)`. |
| `T20` print | The CLI and developer scripts print by design. |
| `PLC0415` imports inside functions | The optional GUI dependency (PySide6) is imported lazily on purpose. Layering is enforced by import-linter instead. |
| `PLR0913` too many arguments | Keyword-only parameters with defaults are clearer than parameter objects at this size. |
| `S603`/`S607` subprocess, in `packaging/` only | Build tools run fixed developer executables with argument lists. |
