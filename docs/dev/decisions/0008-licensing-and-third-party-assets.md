# ADR-0008: Licensing, and keeping third-party assets out of the repo

* **Status:** **Accepted**: the Apache-2.0 code license, the asset rules, and the branding
  policy (item 4), all decided by the maintainer on 2026-10-16.
* **Date:** 2026-10-16

## Context

The project is meant to be open source. The maintainer's local `resources/` folder from
the 2024 prototype holds material we do not have the right to redistribute: the original
course spreadsheets, trademarks, third-party code and icons with unknown or restrictive
licenses, purchased assets, and artwork that is not part of the public project. The
reference standards and books used to check formulas (ASME Y14.5, ISO 128, BS 8888,
*Machinery's Handbook*, *Engineering Drawing and Design*, …) are copyrighted and kept
outside the project.

**Facts and formulas are not copyrightable. Specific text, tables, drawings, and logos are.**

## Decision

1. `resources/` and `builds/` are git-ignored. Nothing from them is committed.
2. We transcribe the **formulas and worked numbers** from the legacy workbooks into
   `docs/dev/legacy-workbooks.md` and golden tests, in our own words with attribution.
3. Standards and books are **cited** (edition, section, page), never quoted at length or
   copied as tables. Data tables, such as K-factors or minimum bend radii, need a source
   whose license allows redistribution, or must be our own measurements.
4. **Branding.**
   * The public build (the repo, GitHub Releases, and PyPI) is **unbranded**. It may say
     in plain text where the project began.
   * Its logo and splash will be original art released permissively (recommended: CC BY
     4.0, or CC0 for no conditions at all), with an `ASSETS-LICENSE` notice next to the
     files. It is built only from assets whose licenses allow that.
   * **Branded editions**, for example for a school or a shop, are built outside this repo.
     A *branding pack* (name, icon, splash, About text) is applied at build time through
     the generic branding hook. Branding packs, third-party marks, and their art never
     enter this repo; `/branding/` is git-ignored for local packs.
   * Branded editions are never attached to public releases. Whoever builds one is
     responsible for permission to use the marks and art it contains.
   * If marks are ever added to the public repo, add `TRADEMARKS.md` saying forks must
     remove them. Apache-2.0 §6 already excludes trademark rights.
5. **Code license: Apache-2.0** (decided 2026-10-16). It is permissive, so shops and schools
   can adopt and embed it, and it has an explicit patent grant. The full text is in
   `LICENSE.md`, and `pyproject.toml` declares `license = "Apache-2.0"`. Alternatives considered:
   * **MIT**: similar, shorter, no patent grant.
   * **GPL-3.0-or-later**: keeps all derivatives open, but discourages embedding in
     closed tools.
   * **LGPL-3.0**: what Qt and FreeCAD use. It lets the library be linked from closed apps
     while keeping changes to the library itself open.

   Apache-2.0 and MIT code can also be included in GPL-3.0 projects (a one-way
   compatibility), such as a GPL-3.0-or-later Blender extension. Apache-2.0 is not
   compatible with GPL-2.0-only.
6. PySide6 is LGPL-3.0, which is compatible with all of the above as long as we ship Qt as
   replaceable shared libraries. pyside6-deploy and Nuitka standalone builds do this.
7. Contributions are accepted under the project license, using inbound = outbound.
   We'll consider a DCO sign-off once there are outside contributors.

## Consequences

* The repository can be made public safely.
* New art and icons must be original or carry compatible licenses, recorded in
  `THIRD_PARTY_NOTICES.md` once any are added.

## Remaining

* Add `NOTICE` and `THIRD_PARTY_NOTICES.md` when the first bundled third-party asset or
  library notice requires them. Installers that bundle Qt will need the LGPL notices.
