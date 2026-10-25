# ADR-0016: A style system for the welcome screen

* **Status:** **Accepted**, built on 2026-10-17 (see the amendments). The maintainer
  approved S1–S5 as recommended on 2026-10-17.
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

### 2026-10-17: the restyle as built (slice e)

* **The card (S2).** The art spans the card's full width, so the card is 960 × 572
  (`WelcomeStyle.window`). The logo box is a child of the art, placed by
  `welcome_layout.logo_box` in `WelcomeStyle.logo_area`: the 96 px logo region less its
  minimum margins. The art spec and template gain the logo region as a safe area,
  0, 0, 96 × 540.
* **The frame (§4).** The card is a translucent window. It paints the top bar's
  background, and a frame on top of everything, which takes no mouse events, clears
  what lies outside the rounded outline, then draws the border and the separator. The
  separator sits on the top bar's whole-pixel edge, so it stays crisp when the card
  scales. Corners are rounded only on Windows, macOS, and Wayland. Elsewhere they're
  square: Qt's public API exposes no "this screen composites" capability, so the rule
  goes by `QGuiApplication.platformName()` (KI-020).
* **The panes (§5, S3).** Each pane measures the art beneath it from the art as the slot
  draws it, at one sample per logical pixel, and takes the pixels at the 5th and 95th
  percentiles of luminance (nearest rank). For each text role, the fill's alpha rises
  from the floor, 39 of 255, the least at or above 15%, until the text reaches 4.5:1
  against the fill blended over both pixels. The blend is checked a level either side in
  each channel, as the screen blends in 8 bits. The role needing the least alpha wins;
  if none reaches 4.5:1, the fill is opaque under the role that contrasts more. Tests
  check this on light, dark, and busy generated art, against Qt's own blending.
* This replaces "Until slice e" above.

### 2026-10-17: what a pack may change (slice f)

* A pack's `[welcome]` table may hold `[welcome.style.logo]` and `[welcome.style.panes]`
  tables. They mirror the token file, and hold only the whitelist of S5:
  * `logo.fill_role`, `logo.margin_left`, `logo.margin_top`, `logo.margin_bottom`,
    and `logo.padding`
  * `panes.fill_role` and `panes.fill_opacity_min`
* `welcome_style.with_overrides` checks each value with the token file's own checks and
  refuses any other table or key with a message naming the whitelist. It stays
  standard-library only; the branding loader calls it and reports a `BrandingError`.
* **Whole-style checks.** One check now applies to the shipped tokens and to every pack's
  overrides. The logo area must hold the box's least size; the padding must leave room
  for the logo in that box; and some text role must reach `panes.min_contrast` on an
  opaque pane fill in both themes, so the contrast guarantee can always be met.
* `Branding.welcome_tokens` gives the screen its edition's tokens, and the welcome
  screen reads the logo box's, the panes', and the frame's tokens from it.

### 2026-10-17: design refinements (slice g)

A design review of the built screen proposed refinements M1–M9 and L1–L3, all within
S1–S5. VT323's figures below were measured from the font file: 1000 units to the em,
capitals 560 units tall, and every advance a whole number of 40-unit design pixels.

* **Weight (M1, overridden by the maintainer).** The review proposed drawing bold as a
  one-design-pixel overstrike. The maintainer declined it: "I think the 2-times-shifted
  font is a mistake. Let's just either accept that bold looks different on different
  systems, or we can do without bold." So `typography.display_weight` takes one of two
  values:
  * `regular`, the default, replacing slice c's synthetic bold. It keeps the face on its
    grid and looks the same everywhere.
  * `bold`, Qt's bold, which each platform's text engine draws and widens differently.

  The pane sizes itself from the metrics of the font it draws, bold included.
* **The grid (M2).** `display_em_pixels` is 25, and the name's size snaps to
  `25n` device pixels, `n = max(1, round(size × scale × ratio ÷ 25))`, so 50 px at 100%
  and 125%, 75 at 150%, and 100 at 200%. `name_pane.font_size` is 50. The face is
  unhinted and antialiased, and is drawn as its outline. Qt's DirectWrite engine kept
  its colour (ClearType) fringe even when asked for grey antialiasing, and an outline
  is grey and unhinted on every platform. The text stays the pane's accessible name.
* **Crisp lines (M3).** Every line is `max(1, round(width × ratio))` device pixels, on
  device-pixel centres: the card's border, the separator, the logo box's border, and
  the panes' borders.
* **One outline (M4).** The card's rounded outline is one path, along the border's
  centre line. The card's background and the art are clipped to it, and the border is
  stroked along it last, so the stroke covers the clip's edge and leaves no seam. Only
  that path is antialiased. This replaces clearing the corners.
* **Paired fills (M5).** Each pane text role has its own fill: `panes.fill_roles` puts
  white under the ink text and ink under the white text. Only the paired fill's opacity
  rises. The thresholds are per pane: `name_pane.min_contrast` is 3 (large text, WCAG 2)
  and `version_pane.min_contrast` is 4.5. In the pack whitelist (S5),
  `panes.fill_role` becomes `panes.fill_roles`.
* **The logo box (M6).** `logo.min_short_side`, 48, replaces `logo.min_size`. A box
  whose short side is under it grows, keeping its shape, up to the logo area's edges.
* **The cap band (M8).** The name is centred on its capitals,
  `typography.display_cap_height` 0.56, and its padding, 8 × 16, is the space around
  them. The version, in the system's UI font, stays centred on its line.
* **Corners (L1, L2).** `card.corner_radius` is 5 px, scaled with the card, not a
  fraction of its height. The loader requires each corner-anchored pane's inset to be at
  least the radius plus the card's border.
* **The card's border (L3).** It takes the new role `card_border`: ink in the light
  theme, white in the dark, so the card stays outlined on a dark desktop. The palette's
  contrast tests cover it.
* **Spacing scale.** Insets, margins, and paddings must be 2, 4, 6, 8, 12, 16, 24, or
  32; the loader refuses any other value, in the token file and in a pack. Sizes, such
  as the 96 px logo region and the 24 px top-bar buttons (`top_bar.button_size`), are
  free. `version_pane.padding` is now 2 × 4.
* **The logo box's fill.** `logo.fill_role` is `welcome_paper`, white in both themes, by
  the project's decision: logos are almost always drawn for white, and the original
  had a white box. A pack may still choose another role.
* M7 (the 960 × 572 card and the left safe area) and M9 (refusing `name`) were already
  built, in slices e and d.

### 2026-10-17: after the render review (slice h)

A design review of renders at 1×, 1.25×, 1.5×, and 2× found one High, two Mediums, and
four Lows; the rest of its checklist passed. The project decided the fixes.

* **The generic mark (H1, M1).** In the dark theme, the generic logo's upright name was
  white on the white box. The generic mark is now the app icon alone, 64 px in an 80 px
  square, centred by the box's rule; the name lives in the title pane. The drawn
  generic logo is removed from `welcome_art`.
* **No pillars (M1).** A new token, `logo.max_long_side` (320 px), caps the box's long
  side, so no logo, a pack's included, becomes a full-height pillar. The loader requires
  it to be at least `logo.min_short_side`.
* **125% (M2).** The name snaps to 40 px there, in logical pixels: the grid rule working,
  crisp over blurry. The art spec says so.
* **Ties (L1).** The grid's tie rule is explicit: a half rounds down, to keep the title
  inside its safe area, rather than relying on Python's round-half-even. So 2.5 gives 2
  and 3.5 gives 3, where round-half-even gave 4 at 175%.
* **The version's text (L2).** It's drawn as its outline too, so both panes are grey
  antialiased and match, with no colour fringe; the text stays the pane's accessible
  name.
* L3, the art's rim under the version's safe area, goes to the maintainer; L4, the
  live-window, focus-ring, and font-fallback checks, stays in KI-020.

### 2026-10-17: the exact contrast rule (slice i)

A review of the style system's commits found that the contrast guarantee didn't hold for
saturated art, and that a test helper read freed memory on Linux. The project decided
the fixes.

* **The rule.** The panes' fills blend per sRGB channel, so the pixels at the 5th and
  95th percentiles of luminance don't bound the pixels between them. Over 6% grey, 88%
  pure blue, and 6% white, the old rule measured 3.01:1 and 4.51:1 at those two
  percentiles while the blue got 2.54:1 and 3.64:1. The rule is now exact:
  * Under each pane, the art as drawn is sampled on a fixed grid of at least
    `panes.min_samples` (4096) nearest pixels, or every pixel if there are fewer.
    Nothing is averaged, because averaging hides extremes.
  * For a candidate opacity, every sample is blended under the fill, through per-channel
    tables of linear light, rounded down and up, and its contrast with the text is taken.
  * The opacity is enough when the contrast at the `panes.percentile` (5th) percentile of
    the samples meets the pane's threshold.
  * For a fill on the far side of its text, contrast rises with opacity, so the least
    opacity is found by bisection from the floor. Only an opacity that was checked is
    returned.

  The token `panes.percentiles` becomes `panes.percentile` and `panes.min_samples`.
* **WCAG floors.** `LARGE_TEXT_CONTRAST` (3.0) and `NORMAL_TEXT_CONTRAST` (4.5) are
  constants. The loader refuses a pane's `min_contrast` below its floor. Text of 24 px
  (18 points) or more counts as large, so the name needs at least 3 and the version at
  least 4.5.
* **The Linux failure.** A test helper read `constBits()` from a temporary copy of an
  image. Nothing kept the copy alive, so on Linux its buffer could be freed and reused
  before the bytes were copied. The helper now holds the copy in a name, and a test
  refuses `constBits()` or `bits()` on a call's result anywhere in `src/` or `tests/`.
  The screen's own measuring already held its image.
* **Superseded wording.** The amendments supersede the text above them where they
  differ. Slice g's replaces §1's `fill_role` and `border_role` for the panes (each text
  has its own fill, and the border follows the text) and slice f's `panes.min_contrast`
  (each pane has its own). This one replaces slice e's two-percentile measurement. The
  earlier text stays as the record.

### 2026-10-17: a calm background (slice j)

A re-review confirmed slice i, and found that busy art could meet the contrast and
still not read. Over a black-and-white checker, the name pane's fill rose only until ink
reached 3:1 against the darkest blended pixel, and the background under the letters
still alternated strongly, which broke them up. Per-pixel contrast doesn't measure
texture. The project decided on a second condition in the same bisection.

* **The rule.** Under a pane, the blended background's spread,
  `(L95 + 0.05) / (L5 + 0.05)`, must be at most `panes.max_background_spread` (1.5) as
  well as the text reaching its contrast. L95 and L5 are the luminances of the sampled,
  blended pixels at `100 - panes.percentile` and `panes.percentile` percent: L95 at the
  lighter 8-bit rounding and L5 at the darker, so the check is safe.
* **Bisection still holds.** Blending toward one colour narrows the spread, so the
  calm, like the contrast, grows with opacity, and the bisection still returns only an
  opacity it checked. An opaque fill has a spread of 1.
* **The token.** `panes.max_background_spread` must be at least 1, and a pack can't
  override it.
* **The effect.** Calm art, such as the generic gradient or a quiet render, sits around
  1.1 and stays at 15%. Over a black-and-white checker, the name's fill rises to about
  83% (alpha 211), with a spread of 1.497.

### 2026-10-17: a shared loader core (ADR-0017 preparation)

* The reading and checking that any design-token file needs moved out of
  `gui/welcome_style.py` into `gui/style_tokens.py`, so ADR-0017's app-wide token file
  can share it. That covers `StyleError`, `Size`, `Rect`, the spacing scale, each token's
  check, the table and schema parsing, palette access, and the WCAG contrast helpers.
* `welcome_style.py` keeps the welcome tokens, the pack whitelist, the whole-style
  checks, and the panes' rule, and re-exports what it uses, so nothing that imports it
  changed. The messages are unchanged, there is still one `StyleError`, and every
  existing test passed without an edit.
* `style_tokens` joins the import-linter contract that keeps Qt out of the core, the
  calculators, and the branding loader.

### 2026-10-18: every pixel, at the display's resolution

Support & Review first reported it: natively, at the card's full 960 × 572, the name
pane read 1.35:1 over the striped test art, at the floor fill, and the card's size and
scale were the cause (its layout verification, §8(b)). UI/UX diagnosed why: slice i's
fixed grid aliases with periodic art. Over 1 px stripes every 17 px, 5.7% of the art, a
pane's grid saw 1.1% of them, so the percentile was taken over the wrong pixels and the
fill stopped short. Swept over pane widths of 300 to 340 px and every position in one
period, the grid's share was up to 6.0 percentage points off. The project decided the
fix.

* **The rule.** Every pixel under a pane is measured, at the display's resolution. The
  art is drawn for measuring at the window's device pixel ratio, one image pixel per
  device pixel, and a pane covers every device pixel its rectangle touches
  (`device_rect`). Nothing is sampled or averaged, so detail finer than a logical pixel
  counts as the screen shows it.
* **The token.** `panes.min_samples` is retired. A pack could never override it, so no
  pack changes.
* **Exact, and cheap.** Every measure depends only on how many pixels have each colour,
  so the art is tallied: each distinct colour once, with its count, and blended once at
  each opacity tried. The percentiles are tails of a few percent, so each is found by
  an edge a sample of the colours puts past it, and only the tail is sorted; where the
  sample misjudges, everything is. The results are exactly those over every pixel: they
  matched the earlier every-value code in 43,200 random cases.
* **What it costs** (Windows, native). The generic art under the name pane is 14,608 px
  in 74 colours at 100%: measuring takes 2.5 ms and a fill 1.3 ms, where the grid's
  fill, over 4224 samples, took 7.7 ms. At 200%, it's 56,588 px in 81 colours: 7.8 ms
  and about 4 ms. The worst case is art whose every pixel differs, such as noise: 64 ms
  at 14,608 px and 266 ms at 56,588, where the earlier code, given every pixel, took 115
  and 432 ms.
* **When.** The fills are chosen as soon as the art is measured, before the card
  shows, so its first paint doesn't wait on them; a test checks they're chosen by the
  time `show()` returns.
* **KI-020** loses its high-DPI pane check, which this closes.
* **Tests.** The stripes are measured at their true share, within 0.5 percentage
  points, over the same sweep (the grid fails it); a pane's device rectangle at ratios
  1, 2, and 1.25; and the tally's percentiles against their definition, from either
  end, with and without a sample, and where the sample misjudges.
* **At the card's full size.** The offscreen screen is smaller, so CI's card was
  800 × 477, the art was drawn at another scale, and the grid happened to see the
  stripes. A test now holds the card at its full size over the saturated striped arts;
  the grid fails it offscreen too.
* **At twice the scale,** in its own process, each pane measures exactly the device
  pixels its rectangle covers, and the selection's fallback is pinned where the
  sampled tail holds exactly the pixels past the rank (Support & Review's Lows).
* **The test's own measure** crops the card's grab in device pixels, so it's right on
  a scaled display, and test windows open on the primary screen, so a native run
  doesn't depend on which screen the pointer is on (UI/UX and Support & Review).
* **Superseded wording.** This replaces slice e's "one sample per logical pixel" and
  slice i's grid of at least `panes.min_samples` nearest pixels.

### 2026-10-18: the card's first paint

UI/UX found the welcome card took about 2.8 s to appear on the maintainer's machine,
about 2 s of it inside its first show, in font work. Profiled natively on Windows, with
2,457 font families installed:

* **The cause.** The display font named the fallback families beside the loaded face, so
  the first measure of the name resolved each of them: 1.35 s, where the face alone
  takes 1 ms. The fallbacks are for a face that didn't load, as the token says, so
  they're named only then. The face draws the name either way: the card is
  pixel-identical natively, 0 of 549,120 pixels differing.
* **The effect.** From process start to the card's first paint: 2.58–2.74 s before,
  1.08–1.19 s after, over five runs.
* **The same cost, a second time, in the main window.** The result document set its
  work in CSS's generic `monospace`. Windows has no face by that name, so Qt searched
  its whole fallback list for it at the first use, 1.44 s, and then set the work in
  Tahoma, a proportional face. With the card's fix, that search moved into the main
  window's first show, so the reveal came 2.8 s after the card's paint, not 1.5 s, and
  the card didn't respond meanwhile. The work now names its family. UI/UX chose
  Consolas where it's installed, as on Windows, found in 51 ms the first time, and the
  platform's own fixed-width family elsewhere (`QFontDatabase.systemFont(FixedFont)`),
  on Linux and macOS. On Windows the work's face changes from Tahoma to Consolas.
* **A real launch now** (Windows, natively, through `main()`): the card paints at
  1.07–1.33 s, and the main window shows behind it 1.51–1.52 s later, at the hold.
* **What's left is Qt's.** The first text measure populates Qt's font database, about
  0.6 s with DirectWrite, Qt's default font engine on Windows. The GDI engine populates
  it in about 45 ms, but changes how every text in the app is drawn; UI/UX's review
  keeps DirectWrite.
* **Tests** check that the display font names only its face when it's loaded, and its
  fallbacks after it when it isn't, and that the work names Consolas where it's
  installed, and the platform's fixed-width family elsewhere.

### 2026-10-25: a pane's look doesn't change with its text

Packaging & Builds found that bumping the version to 0.1.0a1 turned the version line from
white on ink to ink on white, on the generic art. The maintainer left the rule to UI/UX
(relayed by PM).

* **The cause.** The pane hugs its text, so its pixels, and the art it chose its pair
  over, change with the text's width: 59 px for "Version 0.1.0", 79 px for "Version
  0.1.0.dev0". Over the generic art both pairs read at the floor, so the tie went to
  whichever had more contrast under the text, and that was a coin toss.
  * Under the pane, measured offscreen, ink on white reached 4.76–4.82:1 and white on
    ink 4.75–4.80:1.
  * "0.1.0a1", "0.1.0" and "1.0.0" tipped to ink on white; "0.1.0.dev0", "0.1.0a10"
    and "10.12.3rc2" stayed white on ink.
  * Every release could have flipped it.
* **The rule.** A pane's pair is chosen over its **safe area**: the corner the art keeps
  clear for it (`safe_area`, §1). That's the same whatever the text, so the choice rests
  on the art alone (`welcome_style.settled_fill`).
  * The area is measured together with the pane's own box, in case a long text, such
    as a translation, outgrows it.
  * The **opacity** is the least, from the area's, at which that pair reads over the
    pane's own pixels. So §5's contrast and calm guarantees still hold on exactly the
    pixels behind the text, as before.
  * An opaque fill covers the art, so a pair the area can read opaque reads opaque
    behind the text too.
* **Rejected:**
  * Measuring at a fixed reference text width: a guess that a longer version, or a
    translation, would outgrow.
  * Hysteresis: there's no previous look to hold on to at launch.
  * A contrast margin before a tie counts: it moves the coin toss rather than removing
    it.
* **What it does.** Over the version pane's safe area (3,340 device pixels offscreen, the
  same for every version), white on ink leads 4.80:1 to 4.35:1. Every version measured
  gets white on ink at the floor, 15%, in both themes: the generic look, as before
  0.1.0a1. The name pane is unchanged.
* **Tests:**
  * The version pane's look is the same, and its text reads by the contrast rule, for
    "0.1.0.dev0", "0.1.0a1", "0.1.0", "0.1.0a10", "1.0.0" and "10.12.3rc2", in both
    themes.
  * Over one near-tie under the text, a lighter or a darker safe area decides the
    pair.
  * Where the pane's own pixels need more than its area, the opacity rises to the
    least that reads there.
