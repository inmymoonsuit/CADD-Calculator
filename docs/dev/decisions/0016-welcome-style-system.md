# ADR-0016: A style system for the welcome screen

* **Status:** **Accepted** (not built). The maintainer approved S1–S5 as recommended on
  2026-10-17.
* **Date:** 2026-10-17
* **Builds on:** ADR-0015 (the welcome screen), ADR-0011 (branding packs),
  [design/palette.md](../design/palette.md), ADR-0008 (third-party assets)

## Context

The welcome screen (ADR-0015) is built, and the maintainer has reviewed it against the
original course app. The requested changes:
* a retro, pixel-style display typeface
* a boxed logo with minimum margins, fitted and centred
* 1 px ink borders around the logo box, around the card, and under the top bar
* the card's outer corners rounded by about 5 px, with square inner panes
* the name and version panes made quiet: a low-opacity fill, a thin border, and the
  version tucked into the corner
* no edition name, because a branded build is the same app

The maintainer asked for these as a **formal, reusable style system** whose parameters
and themes are easy to tweak, not as one-off adjustments. Today the screen's numbers are
spread through `welcome_layout.py` and `welcome.py`.

## Decision

### 1. Design tokens in one file, read by one loader

* All of the screen's visual parameters live in `gui/assets/welcome_style.toml`
  (`schema = 1`). A stdlib-only loader (`gui/welcome_style.py`) types, range-checks and
  documents every token, and refuses unknown keys, as the branding-pack loader does.
* The widget reads tokens only. A test bans layout and colour literals in `welcome.py`,
  as `test_palette` already bans hex colours in the GUI.
* Colours are palette **roles**, never hex values, so light and dark themes and the
  palette's contrast tests apply.
* `docs/dev/design/welcome-screen.md` documents each token. A test checks that the doc
  quotes the shipped values, as the art spec does today.

Token groups (initial values in brackets; "px" means logical pixels, so 1 px is one
device pixel on an HD display at 100% scaling and scales with the system DPI):

| Group | Tokens |
|---|---|
| card | size [1032 × 572] or the art-slot rule; `corner_radius` as a fraction of the card's height [0.0087, about 5 px]; `border_width` [1 px, never less than 1 device px]; `border_role` [ink] |
| top bar | `height` [32 px]; `separator_width` [1 px]; `separator_role` [ink] |
| logo box | `region_width` [96 px]; `margin_left`, `margin_top`, `margin_bottom` minimums [16 px]; `padding` [8 px]; `min_size` [48 × 160 px]; `border_width` [1 px]; `border_role` [ink]; `fill_role` [a background role]; the fit is "contain", centred |
| panes (shared style) | `fill_role`; `fill_opacity_min` [0.15]; `border_width` [1 px]; `border_role` [ink]; corners square |
| name pane | anchor [top right]; `inset` [24 px]; `padding` [10 × 16 px]; display font size [44 px] |
| version pane | anchor [bottom right]; `inset` [6 px]; `padding` [2 × 6 px]; body font size [11 px] |
| typography | `display_font` (a vendored file and its family); `display_weight`; a fallback family list; the body font is the system UI font |

### 2. A vendored, open-source display typeface (S1)

* The display face ships in the app under the SIL Open Font License 1.1, vendored the way
  the Tabler icons are:
  * a pinned source (google/fonts at a commit)
  * a manifest with SHA-256 hashes and a fetch script
  * `OFL.txt` shipped beside the font
  * a THIRD_PARTY_NOTICES.md entry, and a credit in About
* It's loaded with `QFontDatabase.addApplicationFont`. If loading fails, the screen
  falls back to the fallback list with a warning, and never fails to start.
* The OFL allows bundling with any software, but forbids selling the font on its own and
  using its Reserved Font Name for modified versions. We ship it unmodified.

### 3. The logo box (S2)

* The logo sits in a bordered box in a left **logo region** of `region_width`, inset by
  at least the minimum margins from the left edge and from the top and bottom.
* The box takes the logo's aspect ratio and is scaled to the largest size the region
  allows (padding included). It's centred vertically, and never smaller than `min_size`.
* So a tall banner, a square mark, or a wide wordmark all fit without the pack having to
  fight the layout. A wide logo becomes a small, centred box, never a cropped one.
* S2 decides whether the region is a separate white strip, as today, or floats over the
  art's left edge, as in the original.

### 4. The card's frame

* The outer corners are rounded by `corner_radius × card height`, so they stay in
  proportion when the card shrinks to fit a small screen (ADR-0015, amendments). Inner
  panes stay square.
* The window is frameless with a translucent background, and paints its own rounded
  card and border.
* Platform notes, added to KI-020:
  * Where a desktop has no compositor (some X11 setups), translucency isn't available,
    so the card falls back to square corners, detected through
    `QGuiApplication.platformName()` and the screen's capabilities.
  * On Windows 11, the system's own rounding doesn't apply to frameless windows, so the
    painted radius is what shows.

### 5. Quiet panes that stay readable (S3)

* Both panes share one style: a fill at `fill_opacity_min`, a 1 px border, square
  corners, and tight padding.
* **A contrast guarantee.** At startup, the screen measures the art's luminance under
  each pane, at the 5th and 95th percentiles of the region. It picks the text role that
  contrasts best, ink or the light role, and raises the fill's opacity above the minimum
  only as far as needed for 4.5:1 text contrast against both measurements.
  * On calm, light art like the current render, the panes stay at 15%.
  * On dark or busy art, they become as opaque as they need to be, so the text is never
    lost.
  * The border role follows the text role.
* Tests cover light, dark, and busy generated art, and assert the measured contrast.

### 6. One product name (S4)

* The screen always shows the product's name, "CADD Calculator". A branded build is the
  same app; it's identified by its art, its logo, and its About text.
* S4 decides whether packs keep a display-name setting at all.

### 7. What a pack may change (S5)

A pack's `[welcome.style]` table may override a short, whitelisted set of tokens, checked
by the same loader. Anything else is refused, so a pack can't break the layout or the
contrast guarantee.

## Decisions by the maintainer

Approved on 2026-10-17, each as recommended. The alternatives stay on record.

| | Question | Recommended | Alternatives |
|---|---|---|---|
| S1 | Display typeface | **VT323**, drawn bold. The comparison shows the original title was very likely VT323 with bold applied; the letterforms match. | Jersey 10 (a true bold pixel face); Pixelify Sans Bold; any other row of the sheet |
| S2 | Where the logo box sits | **Floating over the art's left edge, as in the original.** The art then spans the card's full width (still 16:9), and the art spec gains a left safe area for the box. | Inside a separate white strip, as today |
| S3 | Pane opacity | **15% as a floor, raised automatically only where the art would make the text hard to read** | A fixed 15% everywhere |
| S4 | The product name | **Fixed as "CADD Calculator" in every edition**: window title, welcome screen, and About heading. The pack's `name` key is removed (ADR-0011 is still Proposed). | Keep the pack setting, and set the private pack's name to "CADD Calculator" |
| S5 | Pack overrides | **A short whitelist**: logo-box fill role, pane fill role, `fill_opacity_min`, and logo margins and padding. Fonts and frame geometry stay app-wide. | No overrides (one look for every edition); or every token |

## Consequences

* Restyling the screen means editing one documented file, and every value is checked.
* The public build gains a display typeface with its license and credit.
* The private pack's art and logo work unchanged. Its `name` either goes away (S4) or
  becomes "CADD Calculator".
* The art spec gains a left safe area if S2 is accepted.

## Amendments

### 2026-10-17: the tokens as built (slice b)

* **Files.** `gui/assets/welcome_style.toml` (`schema = 1`) and its stdlib-only loader
  `gui/welcome_style.py`, which types each token in a dataclass per table, range-checks
  it, refuses unknown or missing keys, and checks each role exists in both themes of
  `palette.toml`. `welcome_layout.py` keeps only the placing rules (cover crop, contain
  fit, a pane at its corner, fit to screen). The generated art and the generic logo are
  content, not layout, and move to `gui/welcome_art.py`.
* **Roles.** The maintainer's "ink" lines are the new role `welcome_line`: ink in the
  light theme, slate in the dark one, since ink vanishes against the dark top bar. Pane
  text chooses between `welcome_ink` and `welcome_paper`, ink and white in both themes,
  because the art beneath is the same in both.
* **Tokens beyond the table above:** `art.formats`, `art.max_bytes`, `art.max_px`, and
  `art.grid` (the art budget and template, from `welcome_layout`), `logo.formats`,
  `top_bar.padding`, `panes.text_roles`, `panes.min_contrast`, `panes.percentiles`, each
  pane's `font` and `safe_area`, and `typography.min_font_size`.
* **Until slice e:** the logo region still sits beside the art, at its new 96 px width,
  and the panes are drawn fully opaque, which meets the contrast rule at any art.

### 2026-10-17: the display face as vendored (slice c)

* **Source.** VT323 comes from google/fonts at commit `2da41909d08a` (`ofl/vt323`),
  with its `OFL.txt`. It's in `gui/assets/fonts/vt323/`, and `manifest.toml` records
  the commit, the copyright, and each file's SHA-256. `packaging/fetch_fonts.py` checks
  the files offline (`--check`) or moves the pin (`--commit`). It refuses a license that
  isn't the OFL 1.1, a font file that isn't a font, and a file that changed since it was
  recorded. `.gitattributes` marks `*.ttf` binary, so line-ending conversion can't change
  the font's hash.
* **Loading.** `gui/fonts.py` adds the face with `QFontDatabase.addApplicationFont`
  when the welcome screen opens, and checks that it holds the family the tokens name.
  Otherwise it warns, and text uses the fallback families. VT323 has only a regular
  weight, so the bold of S1 is the one Qt synthesizes.
* **Build and credits.** The build checks that every file the manifest lists is in the
  app folder. The smoke report gains `display_font`, the family or `fallback`, and the
  build's smoke test requires the family. THIRD_PARTY_NOTICES.md carries the full OFL,
  and About credits the face.
* **Sources:** the font and its license in github.com/google/fonts at the pinned commit,
  and the project github.com/phoikoi/VT323; the SIL Open Font License 1.1
  (openfontlicense.org); Qt's `QFontDatabase` reference, whose `addApplicationFont`
  returns -1 when a font can't be loaded.

### 2026-10-17: one product name (slice d)

* `gui/branding.py` defines `PRODUCT_NAME`, "CADD Calculator". The window title, the
  application's display name, the welcome screen, About, the build's product name, and
  the smoke report all use it. `Branding` no longer has a `name`.
* A pack with a `name` key is refused, with a message saying to delete it, as `splash`
  was (ADR-0011, amended). At run time such a pack falls back to the generic branding
  with a warning; the build stops with the message.
