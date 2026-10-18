# Contributing

Thanks for helping! Engineering formulas matter more than code style here. **Every formula
needs a source, and every source needs a test.**

## Development setup

```bash
uv sync --extra gui             # .venv with dev tools and PySide6
uv run pytest                   # tests (the GUI test runs offscreen if PySide6 is installed)
uv run ruff check . && uv run ruff format --check .
uv run mypy                     # strict type checking of src/ and packaging/
uv run lint-imports             # architectural layer contracts
scripts\launch_app.cmd          # run the work-in-progress app (scripts/launch_app.sh elsewhere)
```

**Read [docs/dev/engineering-guidelines.md](docs/dev/engineering-guidelines.md) first.**
It sets out the architecture rules, the coding and docstring standards (Google style), what
belongs in code versus docs, and the definition of done.

To build the standalone app, see [docs/dev/packaging.md](docs/dev/packaging.md).

On Windows, if uv warns about hardlinks (the cache and the project are on different drives),
set `UV_LINK_MODE=copy`.

## Workflow

* Branch from `main` and open a pull request. CI must pass on Windows, macOS, and Linux.
* Use small, focused commits with imperative subjects, e.g. "Add K-factor-from-test-bend calculator".
* Update docs in the same PR (ADR-0007). Significant decisions need an ADR
  ([docs/dev/decisions](docs/dev/decisions/README.md)). Failed experiments go in the
  [engineering log](docs/dev/engineering-log.md). New limitations go in
  [known issues](docs/dev/known-issues.md).
* Add a line to `CHANGELOG.md` under *Unreleased*.

## Adding a calculator

1. Pick the domain package, e.g. `src/caddcalc/calculators/sheet_metal/`. A new family
   needs a new package that exposes a `Domain` as `DOMAIN` and a `CALCULATORS` tuple;
   add both to `calculators/__init__.py` (ADR-0013).
2. Subclass `Calculator`:

```python
class MyCalc(Calculator):
    id = "sheet_metal.my_calc"  # stable public ID: never rename casually
    name = "Human-readable name"
    domain = "sheet_metal"  # the id of a registered Domain; built-in IDs start with it
    summary = "One sentence on what it computes."
    params = (
        THICKNESS,
        Param(
            "width",
            "W",
            "Width",
            Dimension.LENGTH,
            default="2 in",
            minimum=0.0,
            min_inclusive=False,
            help="...",
        ),
    )
    outputs = (Output("area", "S", "Cross-section area", Dimension.LENGTH),)  # see note
    methods = (
        Method(
            "basic",
            "Basic",
            "S = W·T",
            Verification.UNVERIFIED,
            references=(Reference("Book, 3rd ed.", "§4.2, p. 117"),),
        ),
    )

    def compute(self, ctx: Context) -> None:
        ctx.calc("S", "W*T", label="Area", dimension=Dimension.LENGTH, output="area")
```

   (Area needs a new `Dimension`, which needs an ADR-0005 amendment. The example is only
   to show the shape of the code.)
3. Formulas go in `ctx.calc` strings. Use `tand`, `sind`, and so on for degree-based trig.
   Values computed in Python go through `ctx.record(..., note="why")`.
4. Warn about engineering hazards with `ctx.warn(...)`. Lead with the verdict, and name
   any value as a field, e.g. `ctx.warn("Radius {R} is under {T}.", quantities={"R":
   (r, LENGTH), "T": (t, LENGTH)}, detail="Why it matters.")`, so it's shown in the
   user's units (ADR-0017, amendments).
5. **Tests:** at least one worked example per method, from the cited source when there is
   one. Generic tests already check that it runs and renders.

## Verification status

| Status | Requires |
|---|---|
| `legacy=True` (independent flag) | a golden test matching the original course spreadsheet |
| `verified` | a citation (edition, section, page) **and** that source's worked example as a test, reviewed by someone other than the author when possible |

Use the *Formula verification* issue template to propose a promotion or to report a doubt.

## Sources and copyright

Cite; don't copy. Formulas and facts are fine. Verbatim text, tables, and figures from
standards (ASME, ISO, BS) and handbooks are not. Data tables need a redistributable source
or original measurements. Keep anything you can't redistribute in the git-ignored
`resources/` folder (ADR-0008).

## Reporting a wrong or rights-encumbered value

Every value in a reference table, such as a gauge thickness, cites where it comes from
(ADR-0014). If one is wrong, or you believe it can't be redistributed, please open a
[*Reference value* issue](https://github.com/inmymoonsuit/CADD-Calculator/issues/new?template=reference_value.md) and give:

* the table and its version, e.g. "Gauge systems, version 1" (a result names the table it
  used)
* the value or its option key, e.g. `msg:12`
* what's wrong
* your evidence or source: cite it, but don't paste copyrighted text or tables
* any rights concern, and who holds the rights

We fix or remove a reported value promptly once it's checked, and record the change in
the CHANGELOG.

## Code style

The full standard is [docs/dev/engineering-guidelines.md](docs/dev/engineering-guidelines.md)
(ADR-0012). In short:

* `ruff` formats and lints with the rule set in `pyproject.toml`, including Google-style
  docstrings. `mypy --strict` must pass on `src/` and `packaging/`.
* `uv run lint-imports` enforces the layers. `caddcalc.core` and `caddcalc.calculators`
  use only the standard library (ADR-0003).
* Comments explain *why*. History, measurements, and status go in the docs, and the code
  points there.
* Prefer clarity over cleverness: formulas should read like the textbook.

## Translating

The app's text is translated with GNU gettext, through `caddcalc.core.i18n` (ADR-0020).
The source language is US English.

**New user-facing text is marked from now on.** Text that's already there is marked in a
later sweep, calculator by calculator.

* Mark text with `N_()` where it's declared, which returns it unchanged, and translate it
  with `_()` where it's shown. Calculator modules are imported before the language is
  chosen, so a declaration never calls `_()`.
* Give a short or ambiguous word a context: `pgettext("unit", "in")`,
  `pgettext("button", "Copy")`.
* Write one template per sentence, with named placeholders: `"{value} is below {limit}"`,
  never a sentence pieced together from parts. A translation may reorder the
  placeholders, but never drop, add, or rename one; a test checks.
* Choose a plural form with `ngettext` for a whole count. A number shown with decimals
  chooses by its text, with `npgettext_shown`: "1 inch", but "1.0000 inches". Mark a
  singular and plural declared together as one pair, `NP_("unit", "inch", "inches")`,
  so a language with more plural forms can give them all.
* Put a note for translators on the line before the text, starting `# Translators:`.

The template, `src/caddcalc/locale/caddcalc.pot`, and each language's `.po` file are
committed. `.mo` files are compiled, in the build and the tests, and never committed.
After changing marked text, update the template, then the languages:

```bash
uv run python scripts/i18n.py extract
uv run python scripts/i18n.py update
```

`uv run python scripts/i18n.py check`, which the tests also run, fails while a catalog is
out of step. `init LANG` starts a new language's `.po`. The British catalog is `en_001`,
which every English locale outside the US reads (ADR-0020 §2); an empty translation there
means the US English text is right as it is.

The tests also use a pseudo-locale, `en_XA`, made from the template by
`tests/pseudo_locale.py`: every marked string accented, about 40% longer, and in
`⟦…⟧`. Text that shows plain in it isn't marked; text only partly in brackets was pieced
together from parts.
