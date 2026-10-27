# CADD Calculator brand

The project's mark is a drafting set-square forming a "C", in crimson and black, or in
crimson and white on dark backgrounds. The app icon sets it in white on a crimson tile.
This guide says which file to use where, and the rules that keep the mark readable.

## The files

The SVGs are the source of truth: plain, flat paths, each with its semantic id
(`symbol-C-upper`, `symbol-C-lower`, `symbol-drafting-square`, `word-CADD`,
`word-Calculator`). The Illustrator files are the authoring masters, in CMYK.
`tests/test_brand.py` holds every SVG to the rules under "Editing".

| File | What it is | Where it's used |
|---|---|---|
| `src/caddcalc/gui/assets/brand/app-icon.svg` | The tile: the white mark on a crimson rounded square | The app icon from 48 px up |
| `src/caddcalc/gui/assets/brand/app-icon-16.svg`, `-24.svg`, `-32.svg` | The tile, redrawn for 16, 24 and 32 px (see "Small sizes") | The app icon at those sizes |
| `src/caddcalc/gui/assets/brand/symbol.svg` | The mark: a black C and a crimson square | On white and light backgrounds |
| `src/caddcalc/gui/assets/brand/symbol-reversed.svg` | A white C and a crimson square | On dark backgrounds |
| `src/caddcalc/gui/assets/brand/symbol-monochrome.svg`, `-reversed.svg` | The mark all black, or all white | One-colour uses, and a mark under 24 px on a dark background |
| `src/caddcalc/gui/assets/brand/logo-outlined.svg` | The mark with "CADD Calculator", lettering outlined, with its clear space | On light backgrounds: the welcome screen's title on a light fill, the README, documents |
| `src/caddcalc/gui/assets/brand/logo-outlined-reversed.svg` | The same, reversed | On dark backgrounds: the welcome screen's title on a dark fill |
| `docs/dev/design/brand/masters/*.ai` | Illustrator masters: app icon, symbol, monochrome symbol, logo | Editing (see "Editing") |
| `src/caddcalc/gui/assets/welcome/welcome-art.jpg` | The official build's welcome art, 1920 × 1080: art, not a mark | The welcome screen, under the title and the version |
| `docs/dev/design/brand/social-preview.png` | 1280 × 640: the logo on white over a crimson band | GitHub's social preview (Settings → General); redrawn by `packaging/make_social_preview.py` |

## Palette

| Colour | Hex | Use |
|---|---|---|
| Crimson | `#A31D31` | The square and "CADD" on every background, and the app icon's tile |
| Black | `#000000` | The C and "Calculator" on light backgrounds |
| White | `#FFFFFF` | The C and "Calculator" on dark backgrounds; the mark on the tile |

**On dark backgrounds, crimson stays crimson** (the maintainer's decision, 2026-10-25,
relayed by PM).
* A lighter crimson for dark backgrounds was tried, `#DF495F`. The maintainer found it
  looked pink, and saw no problem with the original's contrast, perhaps because of its
  saturation. So the reversed files use crimson, as the maintainer drew them.
* **Why that's within WCAG 2:**
  * Crimson is 7.56:1 on white, and about 2:1 on dark backgrounds (2.15:1 on `#202020`).
  * But SC 1.4.3 exempts text that's part of a logo or brand name.
  * And a logo isn't a graphical object needed to understand content, which is what SC
    1.4.11 covers.
* **The reversed marks stay legible through their white parts:** the C and
  "Calculator" are 13.77:1 to 18.92:1 on the dark backgrounds they meet (`#2D2D2D` to
  GitHub's `#0D1117`).
* **Where the mark is under 24 px on a dark background,** use the white monochrome. At
  that size the square's colour carries too little area to read as a separate part.
* **The app icon's tile** is a container. Its white mark has 7.56:1 on the crimson,
  whatever is behind the tile, so the tile itself needs no lighter version.
* The UI palette's crimson (`#A3122F`, `palette.toml`) is a separate, older value for
  the interface's own controls. The brand files use `#A31D31`.

## Clear space and minimum sizes

* **Clear space:** keep a margin around the symbol, and around the logo's symbol, at
  least the height of the C's upper arm. That's 46 of the symbol's 280 units, about a
  sixth of its width. Nothing else sits in it: no text, rule or edge.
* **The symbol:** at least 24 px tall in colour. Below that, use the app icon's small
  drawings, or the monochrome symbol.
* **The logo:** at least 160 px wide on screen. "Calculator" is too small to read below
  that, so use the symbol alone.
* **The app icon:** down to 16 px, through its small drawings.

## Small sizes

At 16 and 24 px, the master's square has a hole only a pixel across, and the gap between
the square and the C is under a pixel, so both blur shut. The small drawings are redrawn
on each size's pixel grid:
* **Edges on whole pixels:** every straight edge of the tile's mark lies on a pixel
  boundary.
* **A wider gap:** two units between the square's long edge and the C's cut, so one row
  of pixels is wholly clear all along the diagonal.
* **No hole at 16 and 24 px.** At 32 px the hole stays, 4 px on a side, with 3 px of
  square around it.

The master is used from 48 px up.

## Which variant where

* **Window, taskbar, `.ico`, `.icns`, Linux:** the app icon, with the small drawings at
  16, 24 and 32 px.
* **The About box:** the app icon.
* **The welcome screen's title:** the outlined logo, upright, 72 px tall, at the top
  right. Its pane picks whichever reads over the art: the reversed logo on a dark fill,
  or the logo on a light one (ADR-0015, amendments). The strip at the art's left edge is
  an organization's, not the project's: empty in the official build.
  *Supersedes* slice 3's vertical lockup, symbol over a rotated wordmark, which is
  retired with its file.
* **The installer:** the white symbol on crimson in the welcome and finish pages' left
  panel, and the app icon on white in the inner pages' header, each drawn at its image
  area's exact size for every scale from 100% to 250%, so Inno never stretches them
  (`packaging/icons.py`, `wizard_images`).
* **README and documents:** the outlined logo, normal on light and reversed on dark.
* **One-colour reproduction** (engraving, stamps, faxes, a print that can't hold the
  crimson): the monochrome symbol.

## Provenance and licence

* **Made by** the maintainer, working with ChatGPT, and finalised in Adobe Illustrator,
  as the maintainer told PM on 2026-10-25 (relayed). So the artwork's provenance
  includes AI assistance. The maintainer left its sizing, simplification and placement
  in the app to the project's lanes.
* **The wordmark** is set in Montserrat ExtraBold, under the SIL Open Font License 1.1,
  and outlined: the files hold paths, not the font. The OFL doesn't apply to documents
  made with the font, so the outlined lettering carries no font licence obligation, and
  no font is shipped for it.
* **Checked clean:** the files contain vector paths only, with no embedded images or
  fonts. PM checked this, and `tests/test_brand.py` keeps it so.
* **Prepared for the repo** by UI/UX & Design: the exports cleaned (hidden duplicate
  layers and comments dropped, styles resolved into fills), and the small drawings made.
* **Licence: Apache-2.0, and a trademark policy.** The name and the marks are protected
  differently from the code, by the maintainer's decision of 2026-10-26 (relayed by PM).
  * The files are under Apache-2.0, like the rest of the repo.
  * The marks belong to the maintainer, and using them to identify a product is governed
    by [TRADEMARKS.md](../../../TRADEMARKS.md). Anyone may refer to the project, and
    redistribute unmodified official builds and source with the marks. A modified
    version needs its own name, icon and logo; a fork may keep the files in its repo,
    but its builds mustn't present themselves with them.
  * ADR-0008, item 4, amendments, has the record.

## The welcome art

Welcome art © inmymoonsuit (the maintainer), not under Apache-2.0: it may be used only
as part of CADD Calculator, with credit ([ART-LICENSE.md](../../../ART-LICENSE.md)). It's
art, not a mark, so it isn't covered by TRADEMARKS.md, and it lives beside the brand's
files, not among them (`gui/assets/welcome/`). It's the Viking with the abacus, the
maintainer's own character, which the Ridgewater edition shows too. It's a light scene,
so the title shows the logo in black at its least fill; the version, over the shield's
rim, fills more to read. It ships
as the maintainer delivered it, less its metadata.

## Editing

1. Edit the Illustrator master, then export each variant as SVG.
2. Clean the export into the repo's form:
   * one flat `<path>` (or `<rect>`) per shape, with a `fill` attribute
   * a `transform` attribute may place a path
   * no `<style>`, classes, comments, `<text>`, `<image>`, or hidden (`display: none`)
     layers
   * no external references
   * only the palette's three colours: crimson, black and white
3. File names use hyphens throughout: `symbol-reversed.svg`, not `symbol_reversed.svg`.
4. Run `uv run pytest tests/test_brand.py`.
