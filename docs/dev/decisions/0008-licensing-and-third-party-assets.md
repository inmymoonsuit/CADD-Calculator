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

## Amendments

### 2026-10-26: the project's logo and app icon (item 4)

* **The artwork:** the maintainer drew the logo and the app icon, working with ChatGPT,
  and finalised them in Adobe Illustrator (as the maintainer told PM, relayed). So their
  provenance includes AI assistance, and docs/dev/design/brand.md says so.
  * The wordmark is Montserrat ExtraBold (SIL OFL 1.1), outlined into paths. The OFL
    doesn't cover documents made with the font, so no font ships and no notice is due.
  * The files hold vector paths only.
* **Its licence: Apache-2.0, with a trademark policy.** PM first chose Apache-2.0 under
  the maintainer's delegation. The maintainer then decided, on 2026-10-26 (relayed by
  PM), that the name and logo be protected differently from the code, as a short,
  friendly trademark policy. How is PM's choice, under the maintainer's delegation:
  * The files' copyright licence stays Apache-2.0, like the rest of the repo, so the
    repo has one licence and anyone may copy and change the files.
  * The name "CADD Calculator", the symbol, the logo and the app icon are also the
    maintainer's trademarks. Apache-2.0 grants no right to use them to identify a
    product (§6); [TRADEMARKS.md](../../../TRADEMARKS.md) says what's allowed.
  * Use by name, and unmodified redistribution, are allowed without asking. A modified
    version needs its own name, icon and logo, and mustn't suggest endorsement. A fork
    may keep the files in its history and repo, but its builds mustn't present
    themselves with them. That refines item 4's "forks must remove them": removing them
    from history isn't asked.
  * That replaces item 4's recommended CC BY 4.0 or CC0 for the public build's logo. No
    `ASSETS-LICENSE` notice is needed.
* **Where it lives:** `src/caddcalc/gui/assets/brand/` (shipped) and
  `docs/dev/design/brand/` (the logos, the Illustrator masters and the social preview),
  with the brand guide at docs/dev/design/brand.md.
* **`TRADEMARKS.md` is added,** as item 4 asks once marks are in the public repo. That
  closes item 4's open question.
* **Branded editions are unchanged:** a pack's own icon and logo still apply. A pack
  that names no icon shows the project's icon.

### 2026-10-27: the welcome art has its own licence

The maintainer decided (2026-10-27) that the welcome art, the Viking with the abacus,
is the maintainer's illustration for this project only, shown in every build, and that
the maintainer must be credited where it's used.

* **It's excluded from Apache-2.0,** so the repo no longer has one licence for every
  file. [ART-LICENSE.md](../../../ART-LICENSE.md) gives the terms: © inmymoonsuit, all
  rights reserved, except redistribution as part of CADD Calculator (official builds,
  and unmodified copies and forks of the repo) and showing it to talk about the project,
  with the credit "Welcome art © inmymoonsuit". No other project, no modified build, no
  derivative works.
* **A modified build must show its own art,** as it must its own name and logo; a fork
  may keep the file in its repo. A branding pack's `[welcome]` `art` supplies it.
* **Where it's said:** About, the installer's license page, THIRD_PARTY_NOTICES.md,
  the README, and the wheel's metadata: `license = "Apache-2.0 AND
  LicenseRef-CADD-Calculator-Welcome-Art"`, with ART-LICENSE.md among its PEP 639
  license files. The build copies it beside the executable, with the other notices.
* It's still art, not a mark: TRADEMARKS.md doesn't cover it.
