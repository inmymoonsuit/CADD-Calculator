# Welcome screen: art specification and design tokens

How to make art and a logo for the welcome screen of an edition (ADR-0015), and the
design tokens that lay the screen out (ADR-0016). Every number here is a token in
`src/caddcalc/gui/assets/welcome_style.toml`, read and checked by
`caddcalc.gui.welcome_style`; a test checks that this page still quotes each one, so the
specification can't drift from the code.

## The layout

```
╭───────────────────────────────────────────────────────────╮
│                                                    ⓘ  ✕  │  top bar, 32 px
├───────────────────────────────────────────────────────────┤
│  ┌────┐                                 ┌──────────────┐  │
│  │    │                                 │  name pane   │  │
│  │logo│          art slot               └──────────────┘  │
│  │box │          960 × 540                                │
│  │    │                                                   │
│  └────┘                                      ┌ version ┐ │
╰───────────────────────────────────────────────────────────╯
  96 px logo region, over the art
```

All sizes are logical pixels (a 100% display scale). The art slot is **960 × 540**, exactly
16:9, and spans the card's full width under a 32 px top bar, with the About button (ⓘ)
and the X. The logo's box floats over the art's left edge (ADR-0016, S2). A 1 px line
borders the card, runs under the top bar, and borders the logo box; the card's outer
corners are rounded by about 5 px, and everything inside is square.

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
* **No text in the art.** The app's name and the version are live text over the art, in
  panes, so they're always current, follow the light and dark themes, and can be read by
  a screen reader. Leave the safe areas below free of detail: the logo box floats over
  the art's left edge, and the panes over its corners.
* **Safe areas,** in the slot's logical pixels, from its upper-left corner (double them on
  1920 × 1080 art):

  | Area | x | y | width | height |
  |---|---|---|---|---|
  | Logo box | 0 | 0 | 96 | 540 |
  | Name pane | 560 | 24 | 376 | 88 |
  | Version pane | 754 | 510 | 200 | 24 |

  The logo box sits inside its area, and each pane hugs its text at its corner of its
  area.
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

The logo sits in a box that floats over the art's left edge, inside a 96 px logo region.
The box keeps at least 16 px from the card's left edge and from the art's top and
bottom. It takes the logo's shape, plus 8 px of padding, as large as the region allows,
centred, and never smaller than 48 × 160 px. The logo is drawn inside the padding,
fitted whole and centred ("contain"), never stretched or cropped. So a tall banner
fills the region's height, and a square mark or a wide wordmark gets a short box,
centred. The box has a fill and a 1 px border. An **SVG** is preferred, since it scales
to any display; a PNG works too. An SVG must be **self-contained**: an `<image>` or `<use>` may
embed its data (`data:`) or point within the file (`#…`), never to another file, which a
build wouldn't bundle. The same 8 MB budget applies. Without a logo, the box fills the
region and shows the app icon and the name set upright.

## The pack

```toml
[welcome]
art = "welcome-art.png"      # optional; the generic art when absent
art_focus = [0.35, 0.5]      # optional; the point kept in view when cropping
logo = "logo-vertical.svg"   # optional; the app icon and name when absent

[welcome.style.logo]         # optional; see "Restyling a pack's screen" below
fill_role = "welcome_paper"

[welcome.style.panes]
fill_opacity_min = 0.25
```

* The files go in the branding pack folder, as `icon` and `about` do (docs/dev/packaging.md).
* **Ship a notice for the art.** A pack that includes art must include a notice or
  license file for it, such as `ART-NOTICE.md`, saying who made it and on what terms. The
  build copies files whose names contain NOTICE, LICENSE, LICENCE, or COPYING. Third-party
  art never goes in this repository (ADR-0008, item 4).
* To try a pack without building, point `CADDCALC_BRANDING` at its folder.

### Restyling a pack's screen

A pack may override a few of the design tokens below, in `[welcome.style.logo]` and
`[welcome.style.panes]` tables that mirror `welcome_style.toml` (ADR-0016, S5):

* `logo.fill_role`: the logo box's fill, a palette role. The default follows the
  theme, white in light and ink in dark, so a logo drawn for a white background may
  want `welcome_paper`, white in both themes.
* `logo.margin_left`, `logo.margin_top`, `logo.margin_bottom`, and `logo.padding`.
* `panes.fill_role` and `panes.fill_opacity_min`: the panes' fill and its least
  opacity. The contrast guarantee still applies above it.

Each value is checked as the token file's is. The fonts, the frame, the sizes, and
every other token stay the same in every edition, so a pack that sets anything else
is refused, with a message naming what it may set. So is one whose margins leave the
logo box less than its least size, whose padding leaves no room for the logo, or
whose pane fill no text role can read on, in either theme.

## Typography

The name is set in **VT323**, a pixel face by Peter Hull, drawn bold (ADR-0016, S1).
It ships unmodified under the SIL Open Font License 1.1, in `gui/assets/fonts/vt323/`
beside its `OFL.txt`, pinned to one google/fonts commit and hashed in `manifest.toml`.
The app loads it into Qt when the welcome screen opens (`gui/fonts.py`). VT323 has
only a regular weight, so its bold is the one Qt synthesizes. If the face can't be
loaded, the name falls back to the fallback families, with a warning, and the screen
still starts. The version uses the system's UI font.

To check the vendored files offline, or to move the pin to another commit:

```bash
uv run python packaging/fetch_fonts.py --check
```

```bash
uv run python packaging/fetch_fonts.py --commit SHA
```

## On screen

* **Smaller screens.** The card's preferred size is its tokens' (960 × 572). On a screen
  whose available area is smaller, the whole card scales down to fit, and the art slot
  stays 16:9. The corners' radius is a fraction of the card's height, so it shrinks in
  proportion. Lines never get thinner than one device pixel.
* **High-DPI.** The art is drawn at the display's device pixel ratio: 2× art is
  downsampled at 100% and 150% scale, and upsampled slightly at 300%. The generic art is
  drawn at the display's ratio.
* **The generic art** is drawn in code from the palette (`gui/welcome_art.py`), until the
  roadmap's commissioned generic art replaces it.
* **The panes stay quiet, and readable** (ADR-0016, S3). Each pane's fill starts at 15%
  opacity. When the screen opens, it measures the art under each pane, as it's drawn,
  at the 5th and 95th percentiles of luminance. It raises the fill's opacity only as
  far as the text needs to reach 4.5:1 contrast against the fill over both. The text
  takes whichever of ink and white needs less, and the pane's border follows the text.
  On calm art the panes stay at 15%; on dark art the text turns white; on busy art the
  fill rises. The screen blends in 8 bits, so the contrast is checked a level either
  side of each blend.
* **Corners and platforms.** The card is frameless with its own bar on every platform.
  It's drawn in a translucent window, so its rounded corners show the desktop. Where
  the windowing system may not composite (X11, and other platforms but Windows, macOS,
  and Wayland), the card keeps square corners. Some behaviour depends on the windowing
  system and needs checking by hand; see KI-020.

## Design tokens

To restyle the screen, edit `welcome_style.toml`; the loader refuses an unknown key, a
wrong type, or a value out of range. Colours are palette roles (`palette.toml`), never
hex values, so both themes and the palette's contrast tests apply.

| Token | Value | Meaning |
|---|---|---|
| `art.slot` | 960 × 540 | The art's area, 16:9 |
| `art.supplied_scale` | 2 | Art is supplied at this multiple of the slot |
| `art.formats` | .png, .jpg, .jpeg | The art's file formats |
| `art.max_bytes` | 8,000,000 | The largest art or logo file a pack may name, in bytes |
| `art.max_px` | 4096 | The largest art width or height |
| `art.grid` | 60 | The art template's grid |
| `card.corner_radius` | 0.0087 | The outer corners' radius, as a fraction of the card's height: about 5 px |
| `card.border_width` | 1 | The card's border |
| `card.border_role` | welcome_line | Its colour role |
| `top_bar.height` | 32 | The top bar's height |
| `top_bar.padding` | 4 | The space beside its buttons |
| `top_bar.separator_width` | 1 | The line under the top bar |
| `top_bar.separator_role` | welcome_line | Its colour role |
| `logo.formats` | .svg, .png | The logo's file formats |
| `logo.region_width` | 96 | The logo region's width, over the art's left edge |
| `logo.margin_left` | 16 | The box's least distance from the card's left edge |
| `logo.margin_top` | 16 | ... from the art's top |
| `logo.margin_bottom` | 16 | ... from the art's bottom |
| `logo.padding` | 8 | The space inside the box, around the logo |
| `logo.min_size` | 48 × 160 | The box's least width and height |
| `logo.border_width` | 1 | The box's border |
| `logo.border_role` | welcome_line | Its colour role |
| `logo.fill_role` | welcome_scrim | The box's fill |
| `panes.fill_role` | welcome_scrim | The panes' fill |
| `panes.fill_opacity_min` | 0.15 | The fill's least opacity |
| `panes.border_width` | 1 | The panes' border, in the text's role |
| `panes.text_roles` | welcome_ink, welcome_paper | The text roles to choose between, dark then light |
| `panes.min_contrast` | 4.5 | The least contrast of the text against the fill over the art |
| `panes.percentiles` | 5 × 95 | The percentiles of the art's luminance measured under a pane |
| `name_pane.anchor` | top_right | The corner the name pane hugs |
| `name_pane.inset` | 24 | Its distance from that corner's edges |
| `name_pane.padding` | 10 × 16 | Around its text: vertical × horizontal |
| `name_pane.font` | display | The display face |
| `name_pane.font_size` | 44 | Its text's pixel size |
| `name_pane.safe_area` | 376 × 88 | The area art keeps clear of detail |
| `version_pane.anchor` | bottom_right | The corner the version pane hugs |
| `version_pane.inset` | 6 | Its distance from that corner's edges |
| `version_pane.padding` | 2 × 6 | Around its text: vertical × horizontal |
| `version_pane.font` | body | The system's UI font |
| `version_pane.font_size` | 11 | Its text's pixel size |
| `version_pane.safe_area` | 200 × 24 | The area art keeps clear of detail |
| `typography.display_family` | VT323 | The display face's family |
| `typography.display_file` | fonts/vt323/VT323-Regular.ttf | Its vendored file, under the assets folder |
| `typography.display_weight` | 700 | The weight it's drawn at: bold (S1) |
| `typography.fallback_families` | Consolas, DejaVu Sans Mono, Menlo, monospace | Tried in order when the display face can't be loaded |
| `typography.min_font_size` | 9 | The least size text shrinks to on a small screen |
