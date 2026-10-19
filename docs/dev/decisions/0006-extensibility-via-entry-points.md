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

### 2026-10-18: a plugin's unexpected errors are reported, not lost

Support & Review found that a plugin's compute raising an error other than caddcalc's
own, a ZeroDivisionError say, went to Python's default `sys.excepthook`: stderr, or
nothing in the packaged app, while the window showed the previous method's results.

* **The core wraps a compute's error** that isn't a `CaddCalcError` as a `SpecError`
  naming the calculator and method, caused by the original, as it already wrapped a
  result check's. Errors worded for users, such as an `InputError` or a
  `CalculationError`, pass through as they are. So every front end reports it: the
  window blanks its results and shows it (ADR-0017, amendments), and the CLI exits with
  status 2 and the message, with or without `--json`.
* **The app's error hook** (`gui.app.install_error_hook`) catches what's left, such as
  an error raised in a Qt slot, which goes to `sys.excepthook` past every isolation
  boundary. It still writes the error to stderr, then shows it in a message box with its
  traceback in the details, which can be copied into a report. It shows nothing as the
  application closes down, when windows are going (KI-019), and never a second box while
  one shows. `main()` installs it and puts the previous hook back however it ends; a
  smoke test leaves the default hook, so it never blocks.
* **The launch measure** opened each further method directly, not through the method
  box's signal, so a page that failed to show was left out with a warning (ADR-0021,
  amendments). The measure was removed on 2026-10-19, with the tallest-page term it
  served (ADR-0021's amendment of that date; the engineering log), so no calculator's
  page runs before it's chosen.

### 2026-10-18: a plugin family's code too (Support & Review's review of a1f0735)

A plugin domain supplies code of its own: its resolver (`options`, `derive`) and its
details (`facts`, `starting_values`). S&R found the window reached it outside every
boundary: reading a calculator's fields before the recalculation's boundary, building
the calculator's form, and the whole settings page. With `derive` raising, the window
kept 0.3119 under the new method, a stale result again.

* **The core wraps it.** `Domain.options`, `derived`, `facts` and `starting_values` run
  the domain's code through one helper, which raises an error that isn't caddcalc's own
  as a `SpecError`, "Domain 'id': its resolver's derive failed: …", from the original.
* **The window's boundaries cover it.** The recalculation reads the fields inside its
  boundary. Building the calculator's form is a boundary too: if it fails, the form is
  cleared and the error shows. Each settings-page action is one, through a decorator
  (`_settings_boundary`): opening the page, a choice's change, applying a setting or a
  starting value, and clearing the settings. If it fails, the page shows the error in
  place of its form, never a half-built one, until it's built again. The form is hidden
  at once and cleared once control is back in the event loop, since the failure can come
  from a signal of one of its own boxes (engineering log, 2026-10-18).
* **A bug's traceback goes to stderr,** with its cause: an error that isn't caddcalc's
  own, or a wrapped one, in the window and in the CLI. So a plugin's author can find
  where it failed; an input the user can fix stays a one-line message.
* **The error hook** writes to stderr only, from the application's `aboutToQuit` on, as
  well as while it closes down, so no box shows during teardown (KI-019).
