# ADR-0011: Brand editions with a branding pack folder

* **Status:** **Proposed**. Implemented on 2026-10-17 in the packaging spike; to be
  accepted once the maintainer has reviewed the pack format.
* **Date:** 2026-10-17
* **Deciders:** the maintainer set the branding policy (ADR-0008 item 4); this ADR
  proposes the mechanism

## Context

ADR-0008 item 4: the public build is unbranded. Branded editions, for example for a school
or a shop, are built outside this repository by applying a *branding pack* (name, icon,
splash, About text) at build time through a generic branding hook. Packs, third-party
marks, and their art never enter this repository.

The hook has to:

* change the app name, window icon, executable icon, splash screen, and About text;
* work at build time, and at run time from a source checkout (for testing a pack);
* stay out of `caddcalc.core` and `caddcalc.calculators`, which are stdlib-only (ADR-0003);
* make a branded build hard to produce or publish by accident.

## Decision

1. A **branding pack** is a folder with a `branding.toml` file (schema 1) naming the
   `edition` slug, the display `name`, and optional `icon`, `splash`, and `about` files.
   Unknown keys, missing files, and paths outside the folder are errors. The format is in
   [packaging.md](../packaging.md#branding-packs).
2. `caddcalc.gui.branding` loads and checks packs. It uses only the standard library
   (`tomllib`) and does not import Qt, so the build script and tests can use it headless.
   The unbranded defaults are `branding.GENERIC`.
3. The app looks for a pack in the `CADDCALC_BRANDING` environment variable, then in a
   `branding/` folder next to the executable of a packaged app. No pack means generic.
   A broken pack at run time warns and falls back to generic.
4. `packaging/build.py --branding PACK` bundles the pack into the app with Nuitka's
   `--include-data-dir`. `PACK` is a folder, or the name of one under the git-ignored
   `branding/` folder. The script copies only `branding.toml`, the files it names, and
   notice or license files (names containing NOTICE, LICENSE, LICENCE, or COPYING). It
   refuses any branded build when `CI` or `GITHUB_ACTIONS` is set.
5. Help > About always shows the version, the disclaimer, and the link to the source
   code. A pack replaces only the description.
6. The Qt *application name*, which decides where settings are stored, stays
   "CADD Calculator" in every edition. Only the display name changes.

## Consequences

* A branded edition is the generic code plus a folder. There is no fork and no branded
  code path to maintain.
* The pack keys are a contract with packs kept outside this repository. Adding an
  optional key is fine; renaming or removing one needs `schema = 2` and a loader that
  reads both.
* Anyone can drop a pack next to a generic executable. That is acceptable: the hook is
  generic, marks stay their owners', and Apache-2.0 §6 grants no trademark rights.
* This repository can test the branded path only with generated placeholder art
  (`packaging/make_placeholder_pack.py`).

## Alternatives considered

* **A Python module of brand constants, swapped at build time**: needs code edits per
  brand and makes committing the private module easy.
* **A Qt resource file (`.qrc`) per brand**: needs `pyside6-rcc` and a compiled module per
  brand, and still needs a way to choose it. A folder is simpler to inspect and swap.
* **The environment variable only**: users would have to set it before launching. Fine
  for testing, not for an installed app.
* **A fork with the branding committed**: it would drift from the public code.

## Revisit when

* An edition needs something the pack can't express, such as a mandatory notice screen.
* Installers need the pack outside the app folder, such as a per-machine pack in
  `ProgramData` for lab images.
