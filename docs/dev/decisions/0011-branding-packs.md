# ADR-0011: Brand editions with a branding pack folder

* **Status:** **Proposed**. Implemented on 2026-10-17 in the packaging spike; to be
  accepted once the maintainer has reviewed the pack format.
* **Date:** 2026-10-17
* **Amended:** 2026-10-17 by [ADR-0015](0015-welcome-screen.md), which replaces the
  `splash` key with a `[welcome]` table (`art`, `art_focus`, `logo`) and the splash
  screen with a welcome screen.
* **Amended:** 2026-10-17 by [ADR-0016](0016-welcome-style-system.md) (S4): the product
  name is fixed as "CADD Calculator" in every edition, so the pack's `name` key is
  removed, and a pack that still has one is refused with a message saying so, as
  `splash` was. A branded build is identified by its art, its logo, and its About text.
* **Amended:** 2026-10-26 by [ADR-0015](0015-welcome-screen.md), amendments: the
  `[welcome]` `logo` key is renamed `organization_logo`, and an optional `product_logo`
  is added for a modified build's own title logo. See "Amendments" below.
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

## Amendments

### 2026-10-26: the welcome screen's logo keys (UI/UX)

The welcome screen's title became the project's logo, and its left strip a slot for an
organization's logo (ADR-0015, amendments). The maintainer proposed the layout, and
approved PM's plan for it (relayed by PM).

* **`[welcome]` `logo` is renamed `organization_logo`.** It's the strip's logo, an
  organization's, such as a school's. A pack that still sets `logo` is refused, with a
  message naming the new key, as `splash` and `name` were.
* **`[welcome]` `product_logo` is added,** optional: a modified build's own title logo,
  so it can comply with TRADEMARKS.md. It's checked as `organization_logo` is: SVG or
  PNG, inside the pack, within the 8 MB budget, and, as SVG, self-contained. Official
  builds and branded editions don't set it.
* **`schema` stays 1.** The Consequences ask for `schema = 2` and a loader that reads
  both when a key is renamed. Before the first release, the project makes no
  compatibility promise (pre-alpha), so the rename is outright, as `splash` and `name`
  were removed under schema 1. The one pack outside the repository is updated by PM.

### 2026-10-28: pack defaults and a portable folder, reserved (ADR-0025)

The maintainer reserved two things in ADR-0025's design without building them (ADR-0025
M4, relayed by PM):

* **Pack defaults:** a pack may later supply defaults for saved preferences, layered
  built-in, then the pack, then the user. It would be a new optional `branding.toml`
  table, added by an amendment here.
* **A portable folder:** a marker folder beside the executable, checked to be writable,
  like this ADR's `branding/` lookup there (item 3). Until then `CADDCALC_CONFIG_DIR`
  is the portable mode, as `CADDCALC_BRANDING` names a pack.
* **Item 6's reason is superseded:** the Qt application name no longer decides where
  settings are stored. ADR-0025's own resolver decides the folder (ADR-0025 §4), from
  folder names the GUI passes in from `gui.branding`'s product name, which is the same
  in every edition (ADR-0016 S4). So a branded and a generic build share one file. The
  Qt application name still stays "CADD Calculator" in every edition, as item 6 says.
