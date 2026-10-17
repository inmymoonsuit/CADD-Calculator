# Welcome screen: art specification

How to make art and a logo for the welcome screen of an edition (ADR-0015). The numbers
here come from `caddcalc.gui.welcome_layout`, and a test checks that this page still
quotes them, so the specification can't drift from the code.

## The layout

```
┌──────────────────────────────────────────────────────────┐
│                                                    ⓘ  ✕ │  top bar, 32 px
├──────┬───────────────────────────────────────────────────┤
│      │                              ┌──────────────────┐ │
│  L   │                              │   name panel     │ │
│  O   │          art slot            └──────────────────┘ │
│  G   │          960 × 540                                │
│  O   │                                                   │
│      │                               ┌──── version ────┐ │
└──────┴───────────────────────────────────────────────────┘
 72 px
```

All sizes are logical pixels (a 100% display scale). The whole screen is **1032 × 572**:
a 72 px logo strip at the left, a 32 px bar across the top, with the About button (ⓘ)
and the X, and the **960 × 540** art slot, which is exactly 16:9.

## The art

* **Size:** supply the art at **1920 × 1080** pixels, twice the slot's size, so it stays
  sharp on high-DPI displays. Other sizes work: art is scaled to cover the slot and
  cropped, but art smaller than the slot looks soft.
* **Formats:** PNG or JPEG (`.png`, `.jpg`, `.jpeg`). Use JPEG for photographs and renders
  and PNG for flat art.
* **Budget:** at most **8 MB** on disk, and at most **4096 px** in width or height. The
  pack loader refuses a larger file; the screen checks the pixel size before it decodes the
  art, and shows the generic art with a warning if the art is too large, unreadable, or
  missing.
* **No text in the art.** The app's name and the version are live text over the art, so
  they're always current, follow the light and dark themes, and can be read by a screen
  reader. Leave the safe areas below free of detail.
* **Safe areas,** in the slot's logical pixels, from its upper-left corner (double them on
  1920 × 1080 art):

  | Area | x | y | width | height |
  |---|---|---|---|---|
  | Name panel | 560 | 24 | 376 | 88 |
  | Version line | 560 | 492 | 376 | 28 |

  The name panel is an opaque card in the theme's colours; the version line hugs its
  text at the right of its area.
* **Focal point:** if the art isn't 16:9, it's scaled to cover the slot, and the overflow
  is cropped around `art_focus`, the point kept in view, as fractions of the art's width
  and height (`[0.5, 0.5]`, the centre, by default). A focal point near an edge is kept
  as near the centre as the art's edges allow.

`packaging/make_welcome_template.py` writes a 1920 × 1080 guide with the safe areas
shaded and a grid every 60 logical pixels. Draw the art on a layer above it, then hide
the guide.

```bash
uv run python packaging/make_welcome_template.py builds/welcome-template.png
```

## The logo

The logo strip is 72 px wide and 540 px tall. An **SVG** is preferred, since it scales to
any display; a PNG works too, at 144 × 1080 px for 2×. An SVG must be
**self-contained**: an `<image>` or `<use>` may embed its data (`data:`) or point within
the file (`#…`), never to another file, which a build wouldn't bundle. The logo is drawn upright, fitted
inside the strip, centred, and never stretched. The same 8 MB budget applies. Without a
logo, the strip shows the app icon and the name set vertically.

## The pack

```toml
[welcome]
art = "welcome-art.png"      # optional; the generic art when absent
art_focus = [0.35, 0.5]      # optional; the point kept in view when cropping
logo = "logo-vertical.svg"   # optional; the app icon and name when absent
```

* The files go in the branding pack folder, as `icon` and `about` do (docs/dev/packaging.md).
* **Ship a notice for the art.** A pack that includes art must include a notice or
  license file for it, such as `ART-NOTICE.md`, saying who made it and on what terms. The
  build copies files whose names contain NOTICE, LICENSE, LICENCE, or COPYING. Third-party
  art never goes in this repository (ADR-0008, item 4).
* To try a pack without building, point `CADDCALC_BRANDING` at its folder.

## On screen

* **Smaller screens.** 1032 × 572 is the preferred size. On a screen whose available area
  is smaller, the whole card scales down to fit, and the art slot stays 16:9.
* **High-DPI.** The art is drawn at the display's device pixel ratio: 2× art is
  downsampled at 100% and 150% scale, and upsampled slightly at 300%. The generic art is
  drawn at the display's ratio.
* **The generic art** is drawn in code from the palette, until the roadmap's commissioned
  generic art replaces it.
* **Platforms.** The card is frameless with its own bar on every platform. Some behaviour
  depends on the windowing system and needs checking by hand; see KI-020.
