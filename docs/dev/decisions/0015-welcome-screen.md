# ADR-0015: A welcome screen composed from branding-pack parts

* **Status:** **Accepted** and **built** (2026-10-17; see the as-built amendment). The
  maintainer approved W1–W5 as recommended on 2026-10-17.
* **Date:** 2026-10-17
* **Builds on:** ADR-0011 (branding packs; amends its `splash` key), ADR-0008 (generic
  public build, third-party art outside the repo), ADR-0003 (layers), ADR-0013 decision B
  (session-only settings), KI-019 (window ownership and disposal),
  [design/palette.md](../design/palette.md)

## Context

Today the app shows a pack's `splash` image in a `QSplashScreen` while the main window
builds, and closes it as soon as the window appears. That is a single flat picture: any
logo, title, or version must be painted into the art. The art then goes stale with every
release, can't follow the light and dark themes, and isn't readable by a screen reader.

The maintainer wants a welcome screen in the spirit of the original course app, with:
* a slot for art that is easy to change
* a vertical logo field on the left
* the app's name in the upper right
* the version in a lower corner
* a bar across the top with a menu (About, and Preferences once it exists)
* an X at the upper right to close it

It has to work in the public build, with generic art, and in branded editions, with a
pack's art, without any edition-specific code.

## Decision

### 1. One screen does both jobs: the startup splash and the welcome

`WelcomeScreen` appears as soon as the `QApplication` exists, before the main window is
built and the reference tables load: it paints during startup, and responds once the
main window is built. It stays until the user closes it, and blocks the main window
meanwhile (W5). Help > Welcome Screen reopens
it. The `QSplashScreen` goes away, so there's one screen, not two.

### 2. Composed from parts, never baked into the art

The screen is a fixed layout of regions:

```
┌──────────────────────────────────────────────────────────┐
│ File  Help                                            ✕ │  top bar: shared menus, close
├──────┬───────────────────────────────────────────────────┤
│      │                              ┌──────────────────┐ │
│  L   │                              │  CADD Calculator │ │  name panel: live text
│  O   │          art slot            └──────────────────┘ │  on a theme-coloured scrim
│  G   │     (pack art, or generic;                        │
│  O   │      scaled to cover, with                        │
│      │      an optional focal point)                     │
│      │                         Version 0.2.0 · Edition   │  version: live text
└──────┴───────────────────────────────────────────────────┘
```

* **Logo strip (left):** the pack's `logo`, an SVG or a PNG, drawn upright in a fixed-width
  strip. The generic build shows the app icon and the name, set vertically.
* **Art slot:** the pack's `art`, scaled to cover the slot and cropped around
  `art_focus` (x and y from 0 to 1; the centre by default). The generic build uses
  generated art drawn from the palette until the roadmap's commissioned generic art
  exists.
* **Name panel and version line:** live text from `Branding.name`, `__version__`, and
  the edition. They are never part of the art, so they're always current, follow the
  theme, and can be read by a screen reader.
* **Colours:** palette roles only (gui/assets/palette.toml), with new roles for the scrim
  and its text. The existing contrast tests extend to them (4.5:1 for text).

### 3. A documented art specification and a template

* The art slot is exactly 16:9, 960 × 540 logical pixels, and the art is supplied at 2×,
  **1920 × 1080**, as PNG or JPEG, so it's sharp on high-DPI screens and matches the
  usual render size. The logo strip (72 px) and the top bar (32 px) sit outside the slot,
  so the whole screen is 1032 × 572 logical pixels. Art in another aspect ratio is
  cropped to cover the slot, around its focal point.
* The usual composition leaves the upper right open for the name panel, and the lower
  right clear enough for the version line.
* docs/dev/design/welcome-screen.md gives:
  * the sizes
  * the safe areas the name panel and version line cover
  * the focal-point rule
  * the formats and a file-size budget
  * the requirement that a pack ship a notice for its art
* `packaging/make_welcome_template.py` generates a guide image with those safe areas
  marked, for whoever makes the art. The placeholder pack generator gains welcome parts,
  so the repo's tests use generated art only.
* A branded edition's real art is tried locally from its private pack (ADR-0011 §3,
  through `CADDCALC_BRANDING`), never copied into the repo or the tests.

### 4. Branding-pack keys (amends ADR-0011)

A `[welcome]` table replaces the single `splash` file:

```toml
[welcome]
art = "welcome-art.png"      # optional; generic art when absent
art_focus = [0.35, 0.5]      # optional; the point kept in view when cropping
logo = "logo-vertical.svg"   # optional; the app icon and name when absent
```

The pack loader stays standard-library only (ADR-0011 §2). It checks the files and the
focus range, and the build script bundles the named files as it does today, through
`Branding.files`. The `splash` key is removed (W4).

### 5. Shared application commands

* A new `caddcalc.gui.actions.AppActions` owns one `QAction` per app-wide command. The
  main window's menu bar and the welcome screen's top bar use the same objects, so a
  command is defined, enabled, and tested once:
  * About
  * Welcome Screen
  * Preferences, once it exists
  * Quit
* Each action carries its Qt menu role (AboutRole, PreferencesRole, QuitRole), so on
  macOS Qt moves them to the application menu, as that platform expects.
* A menu lists only commands that exist. Preferences appears when there are preferences.

### 6. Lifecycle, ownership, and failure (lessons of KI-019)

* `app.main()` creates, shows, and disposes of the welcome screen the way it does the main
  window: closed and deleted while the application runs.
* Connections use bound methods, or KI-019's weak slot helper (`_slot`, private to
  `gui/window.py` today; it moves to a module both windows import), never `partial` or
  a lambda.
* A regression test checks that a closed welcome screen is freed.
* Pack art that is missing, unreadable, larger than the budget (e.g. 4096 px or 8 MB), or
  in an unsupported format logs a warning and falls back to the generic art. Startup
  never fails or stalls because of art.
* The smoke report's `splash_shown` gives way to `welcome_shown`, `welcome_art`
  ("pack" or "generic"), and `welcome_logo`, and `packaging/build.py`'s smoke check
  follows. The smoke test doesn't wait for anyone to close it.

### 7. Layering

The screen is entirely in `caddcalc.gui`: `welcome.py` for the widget, `actions.py` for
the shared commands, and `branding.py` for the pack keys, which stays free of Qt. The size
and safe-area constants live in one module that tests and the template generator import,
so the specification can't drift from the code.

## Decisions by the maintainer

Approved on 2026-10-17, each as recommended. The alternatives stay on record.

| | Question | Recommended | Alternatives |
|---|---|---|---|
| W1 | "Show at startup" | It shows at every start and closes with one click or Esc. There's no saved setting, consistent with ADR-0013 B (session-only). | A "Don't show again" box. That would be the app's first saved preference, so it needs its own ADR on a preferences store, which Preferences will need anyway. |
| W2 | Window frame | A frameless card with its own top bar and an X at the upper right on every platform, matching the design. It's movable by dragging the bar (`startSystemMove`, which also works on Wayland). | The operating system's title bar: reliable, but the X follows the OS, and is at the upper left on macOS. |
| W3 | Menus | File (Preferences…, once it exists; Exit) and Help (Welcome Screen; About), the Windows and Linux convention. Qt moves About, Preferences, and Quit to the macOS app menu. | One menu button (☰) holding everything |
| W4 | The pack's `splash` key | Replace it with `[welcome]` parts. ADR-0011 is still Proposed, and the only pack is the private one, so this is the cheapest moment. That pack then supplies art without baked-in text, plus a separate vertical logo. | Keep `splash` as an alternative full-image mode |
| W5 | Blocking | The welcome screen blocks the main window until it's closed (window-modal), like the original. | It floats on top, but the main window can still be used |

## Consequences

* The art can be swapped by replacing one file in a pack, with no code change and no
  re-baking of text. The version on screen is always right.
* The public build gets a proper welcome screen now, with generated art, and its own
  commissioned art when the roadmap item lands.
* About and Preferences gain one shared home for every future command.
* The private edition's pack needs reworking. It needs art without the title or logo
  painted in, and a separate vertical logo. Those files stay outside the repo.

## Alternatives considered

* **Keep `QSplashScreen` with a pre-composed image:** it can't hold menus or a close
  button, closes itself, and bakes text into the art.
* **Paint the whole screen with `QPainter`:** precise, but it loses the layout engine,
  accessibility, and theme handling that widgets provide.
* **A web view (QtWebEngine):** far too heavy for one screen, and it isn't part of
  PySide6-Essentials.

## Amendments

### 2026-10-17: decisions on the build plan's questions (maintainer)

* **Blocking (W5).** The screen is application-modal: unparented when it opens at startup,
  before the main window exists, and parented to the main window when Help > Welcome
  Screen reopens it. That blocks the main window until it's closed, as W5 intends,
  without reparenting a shown window, and it avoids macOS's sheets, which window-modal
  dialogs become.
* **Startup.** The main window is built from `QTimer.singleShot(0, …)` once the screen has
  painted, so the screen is never blank. It responds once the main window is built (§1).
* **The pixel budget is checked in two places.** The pack loader, standard library only,
  checks each file's suffix, path, and size in bytes. The screen reads the art's pixel
  size through `QImageReader` before decoding it, and falls back to the generic art if
  it's too large.
* **Pack schema.** The pack format stays `schema = 1`: ADR-0011 is still Proposed, so its
  contract isn't settled. A pack that still names `splash` is refused with a message
  that names its replacement, `[welcome]`.
* **Size.** 1032 × 572 is the preferred size. On a smaller screen the whole card scales
  down to fit the available area, keeping the art slot at 16:9 (`welcome_layout.fit_scale`).

### 2026-10-17: as built

* **Modules:** `gui/welcome.py` (`WelcomeScreen`), `gui/actions.py` (`AppActions`), and
  `gui/welcome_layout.py`, the specification's constants, which the widget, the tests, the
  template generator, and docs/dev/design/welcome-screen.md share. (ADR-0016 moved the
  constants into design tokens, `gui/assets/welcome_style.toml`.)
* **Connections:** the welcome screen uses bound methods only, so KI-019's weak slot
  helper stays private to `gui/window.py`; nothing needed to move.
* **Commands:** File (Exit) and Help (Welcome Screen; About). Exit closes every window
  and carries `QuitRole` and the platform's Quit shortcut; About carries `AboutRole`.
* **Fallbacks:** art that's unreadable, missing, or over 4096 px, and a logo that isn't
  a valid SVG or a usable PNG, are replaced by the generic parts with a warning. The smoke
  report's `welcome_art` and `welcome_logo` say which was shown.
* **Platform checks** that CI can't run are listed in KI-020.

### 2026-10-17: an About button on the welcome screen, not menus (maintainer)

This replaces, for the welcome screen, W3 and §5's shared top bar.

* **The welcome screen has no menus.** Its top bar holds an About button (ⓘ) and the X.
  The File and Help menus live only in the main window, where they belong.
* **The About button opens About,** the same box as Help > About: the name and version,
  the description, the license (Apache-2.0), the disclaimer, the link to the source
  code, and the third-party notices. About now names the license.
* **About is one command.** `AppActions` shows it over whichever window is active, so the
  button and Help > About share it, and it works before the main window exists.
* With no menus in the card, nothing there can reach macOS's global menu bar; About and
  Exit still carry their menu roles in the main window.

### 2026-10-17: review fixes (maintainer)

* **A failed startup ends the app.** If building the main window fails, the app logs the
  traceback, says so (a message over the welcome screen, or on stderr in smoke mode),
  and exits with status 1, instead of running on with no window.
* **SVG logos must be self-contained.** The loader refuses an SVG logo whose `<image>`
  or `<use>` refers to anything but its own data (`data:`) or its own elements (`#…`):
  another file would escape the pack folder, and a build wouldn't bundle it.
* **The version line is just the version.** The name panel already names the edition,
  and the edition's slug is a build-folder id, so the line reads "Version x.y.z".

### 2026-10-18: a stable startup (maintainer; UI/UX)

The maintainer saw "a sort of flickering between the initial splash, the app loading,
then the splash screen again. It feels very sloppy", and proposed "a minimum static
splashscreen of just a few seconds even, while the app was prepared and then launched
stable". UI/UX diagnosed it on real launches: the startup showed the main window, which
Windows activates and animates in on top of the card, then raised the card again, so the
card was covered for about a quarter of a second. The project decided UI/UX's rule: every
window shows once, in a stable order. W1 and W5 stand: the card shows at every start,
and stays, modal, until the user closes it.

* **The card shows once, final:** at its place and size, decided before it shows, and
  it's never hidden, moved, re-shown or raised during startup.
* **The main window is prepared hidden:** built, with its first calculator computed and
  the launch height measured, then fitted to the card's screen, all before it shows.
* **It's revealed once, behind the card, without taking the focus.** The card becomes a
  window the main window owns (`setTransientParent`), so the system keeps it above its
  owner with no raise, and the main window shows with `WA_ShowWithoutActivating`, so the
  card keeps the focus and Esc still closes it. When the card closes, the main window
  takes the focus. Qt reads the attribute as it makes the native window, which fitting
  does, and again after the show, so it's set before fitting and cleared only then.
* **A hold before the reveal: `startup.hold_ms`, 1500 ms from the card's first paint.**
  The main window is revealed when it's ready and the hold is over, so the card is
  alone and still for a moment, never just flashing. It doesn't delay the user: the card
  is modal, so the window can't be used until the card closes anyway. A card closed
  before the hold reveals the window at once, or as soon as it's ready. The token is
  tunable; the maintainer suggested "a few seconds". A smoke test reveals at once, as it
  runs no event loop to wait in.
* **Not done:** turning off Windows' open animation (`DWMWA_TRANSITIONS_FORCEDISABLED`).
  The animation now plays behind the card, so it's left unless a fade is still noticed.
* **What a real launch now does** (Windows, natively): the card paints at 2.9 s, the
  main window is ready, hidden, at 3.3 s, and shows behind the card at 4.4 s, 1.5 s after
  the card's paint, without activating; closing the card activates it. The card's late
  first paint, about 2 s of font work, is a separate slice.
* **Tests** record every window's show, hide, move, resize and activation through a
  launch: the card shows once and never moves, the window shows once and never resizes
  after, nothing is raised, the window isn't activated while the card is open, and it's
  revealed no earlier than the hold, or at once when the card closes first. Raising the
  card, skipping the hold, dropping the owner, or letting the window take focus each
  fails them. Offscreen, Qt activates every window it shows, so the activation itself is
  checked only on a real platform.
* **KI-020** gains a check by hand: that the owned card stays above the main window on
  Windows, macOS and Wayland, where stacking requests are ignored.

### 2026-10-18: the card owned before it shows (UI/UX's real-launch review)

Two reviews found, independently, that the card wasn't owned: natively, its owner
(`GW_OWNER`) was none. UI/UX found it on real launches; Support & Review found it from
outside the app, with a watcher that samples the app's windows through Win32, and
measured the card covered, and proposed placing the window under the card with
`SetWindowPos`. Qt gives a top-level window its owner only as the window
shows, and the card was already showing when it was given to the main window. With the
raise gone, the main window then showed on top of the card, which never came back: a
window the user couldn't use, blocked by a modal card they couldn't see.

* **The main window's shell comes first.** `MainWindow(build=False)` is the bare
  window, with no calculator loaded; `build()` loads them and builds its contents
  later. Startup makes the shell and its native window, gives the card to it
  (`setTransientParent`), and only then shows the card. The build and the fit still
  come after the card's first paint, into the shell, hidden; the reveal is as before.
* **What the shell costs the card's first paint.** Support & Review measured the
  first paint at 1.41–1.54 s with the shell first, against 1.19–1.37 s before it:
  about 0.2 s more. Of that, importing `gui.window`, which imported the calculators,
  took 106–158 ms, and the shell's native window (`winId()`) about 155 ms. So the
  calculators load in `build()`, after the first paint, and importing `gui.window`
  loads none (a test checks it in its own process). Measured from the process's
  launch, natively, on the machine of ADR-0016's figures: the first paint went from
  1.38–1.46 s (8 launches) to 1.27–1.34 s (16), and the import from 85–97 ms to
  35–40 ms. The shell's step, that import included, takes 192–205 ms; the rest of it
  is the native window, which the card's owner must have before the card shows.
* **The shell is placed on the card's screen** before its native window is made.
  Made unplaced, Windows put it on the pointer's screen, and an owner on a screen of
  another scale made Windows rescale the card it owns, at 125%, to four fifths of its
  size.
* **A failed build** still ends the app with status 1: building is the step that can
  fail, as it loads the registry and plugins, so it's inside the isolation boundary.
  So is making the shell (Support & Review's L2): if even that fails, the app says so
  and ends with status 1, and the card isn't shown.
* **Tests:** natively, after the reveal, the card's owner is the main window, and the
  card is above it in the system's z-order, walked from the top. Giving the card its
  owner at the reveal, as before, fails that. A real launch through `main()`: the card
  shows once, at 960 × 572; the window shows behind it at the hold, once, at its launch
  size; the card is owned and above it; closing the card activates it. KI-020's check
  by hand covers macOS and Wayland.
* **Watched from outside the app,** with Support & Review's watcher, which samples the
  app's windows through Win32 every 8 ms, over three real launches: the main window was
  above the card for 0 ms, and the card held the top and the foreground until it closed.
  So Support & Review's fallback, placing the hidden window under the card with
  `SetWindowPos`, isn't needed.
* **The native test** also checks what's on screen: after the reveal, the window at the
  card's centre (`WindowFromPoint`) is the card. On the first stable startup, its owner
  check and its z-order check each fail on their own.
* **The hold's timer is tied to the card** (`QTimer.singleShot` with the card as its
  context), so a card deleted first takes its pending hold with it, and the reveal does
  nothing once the main window is gone (Support & Review's L1).

### 2026-10-26: the generic logo strip, from the brand's symbol (UI/UX)

*Superseded the same day by "the title logo and the organization slot", below: the lockup
is retired, and the strip holds only an organization's logo.*

The maintainer drew the project's logo and handed its placement to the lanes (relayed
by PM). §2's logo strip, "the app icon and the name, set vertically", is now built from
it (`src/caddcalc/gui/assets/brand/welcome-lockup.svg`, docs/dev/design/brand.md).

* **The lockup:** the symbol at the top, then the outlined wordmark "CADD Calculator",
  turned to read from the bottom up, as a drawing's vertical text reads from its right
  side. A gap of one C arm sits between them, the brand's clear space.
  * It's drawn from the logo's own paths, with no font.
  * Its 248 × 1178 shape fills the box's inside at the box's cap: 64 × 304 px inside a
    box 80 × 320 px at full size.
* **Colours:** the brand's, for white: a black C and "Calculator", and a crimson square
  and "CADD". The box's fill is white in both themes, so crimson is 7.56:1 and black
  21:1 on it, whatever the theme.
* **What it replaces:** ADR-0016's slice h made the generic mark the app icon alone, because a
  white upright name vanished on the white box in the dark theme. Fixed brand colours
  for white can't vanish. The name also stays in the title pane.
* **A pack's logo is unchanged.** A branded edition's pack that supplies its own logo
  still shows it.
* **Test:** in both themes, the generic box is the cap's height and a vertical strip,
  and draws crimson and black at least 3:1 on its white fill, with only the fill around
  the lockup.

### 2026-10-26: the title logo and the organization slot (UI/UX)

The maintainer proposed this layout: retire the text title, use its place for the
project's logo and wordmark upright, and keep the strip, where a branded edition's logo
sits, for a secondary organization's logo: empty in the official build, an organization's
in a branded edition, and a fork's to use as it sees fit. They approved PM's refined plan
for it (both relayed by PM). The details are UI/UX's, under the maintainer's delegation.

* **The title** is the project's logo, the symbol and the wordmark, upright, at the top
  right: 312 × 72 px at full size, 24 px in from the art's edges, inside §2's 376 × 88
  safe area. It's read as "CADD Calculator". The maintainer chose 72 px from renders at
  56, 64, 72 and 80 px, over the generic art and their mockup of the primary edition's
  art (relayed by PM).
  * The logo's file holds its clear space, 48 of its 344 units on every side, so the pane
    is the logo itself (`brand/logo-outlined.svg` and `-reversed.svg`, moved from
    `docs/dev/design/brand/` to ship with the app).
  * It sits in a quiet pane, as the version does (ADR-0016 §5), held to 3:1 for its
    white or black parts, as for graphics. The pane picks its pair as before; the dark
    fill shows the reversed logo, white C and "Calculator", and the light fill the logo
    in black. PM's brief named the reversed logo, since it sits on the art; over light
    art that would fail, so the pane chooses, and over the generic art it's the reversed
    one, at the 15% floor. The crimson stays crimson on both (brand.md).
* **The strip** holds an organization's logo, from the pack's renamed
  `organization_logo`, in its box as before (ADR-0016 §3). Without one there's no box,
  and the art shows there: the official build has none.
* **Forks:** a pack's `product_logo` replaces the title. It's boxed as the organization
  logo is, white with a border and padding, 72 px tall and at most the safe area's width,
  since a pack's logo may be drawn for white. If it can't be read, the title is left
  out, rather than show the project's logo on a modified build.
* **The smoke report** says which were shown: `welcome_title` (`brand`, `pack`, or
  `none`) and `welcome_organization_logo` (`pack` or `none`), in place of `welcome_logo`.
  The build checks both against the pack.
* **Tests:**
  * The title is the logo, upright, with its name, sized and placed as above, in both
    themes; over the generic art, the C's upper arm is white and the set-square crimson.
  * The title and the version read over light, dark, busy and saturated art; over light
    art the title shows the normal logo, and over dark art the reversed one.
  * Without an organization logo, the strip's pixels are the art's.
  * A pack's organization logo shows in the strip; a pack's product logo replaces the
    title, with nothing of the project's logo, and one that can't be read leaves no
    title.
  * The old `logo` key is refused, naming `organization_logo`.

### 2026-10-26: the generic art is the maintainer's (UI/UX)

§3's generated stand-in, drawn from the palette, is replaced by the maintainer's own art
for the official build (relayed by PM, as are the decisions below).

* **The file:** `src/caddcalc/gui/assets/welcome/welcome-art.jpg`, 1920 × 1080, 16:9, as
  §3 asks. It's beside the brand's files, not among them: it's art, not a mark, so
  TRADEMARKS.md doesn't cover it.
  * **JPEG at quality 95,** 305 KB, from the 2.0 MB PNG the maintainer delivered,
    unchanged. The smooth wall carries its grain, so it doesn't band, even stretched 12
    times in contrast; the largest channel error is 17 levels, and 4 on the wall.
  * **No metadata:** the delivered file's editing history isn't carried over; a test
    allows only the image's own segments.
* **Rights:** © inmymoonsuit, the maintainer, who holds them. The maintainer left the
  licence to PM, who chose Apache-2.0 with the project. THIRD_PARTY_NOTICES.md and
  brand.md say so. No provenance is recorded, by the maintainer's decision.
* **The fallback:** a pack's art that can't be used falls back to this art, as §3's
  fallbacks did to the generated art. If even this can't be read, the card's background
  shows, and the art's source is `none`, which the build's smoke test refuses. The
  generated art, `gui/welcome_art.py`, is removed.
* **Over it:** the art is light and calm, so the title picks the logo in black, and both
  panes stay at the 15% floor, ink on white, in both themes and in en_XA. `art_focus`
  stays at its default: the art is 16:9, so it's never cropped.
* **Tests:** the art is 1920 × 1080, in budget, outside the brand's folder, and carries
  no metadata; the panes stay quiet over it, the title shows the logo in black, and the
  reversed logo still shows over dark art; with no readable art, the background shows;
  and the build's smoke test refuses `none` for the official build.

### 2026-10-27: the Viking with the abacus, in every build (PM)

The maintainer chose (2026-10-27) to show one art in every build: the Viking with the
abacus, until now the Ridgewater edition's. It's the maintainer's own character, not
the college's iconography, so the official build may show it too.

* **The file:** the same `gui/assets/welcome/welcome-art.jpg`, 1920 × 1080, 979 KB: the
  edition's JPEG with its EXIF, XMP, Photoshop and Adobe segments dropped, losslessly.
  Its pixels are the delivered file's, and the Adobe segment only said YCbCr, the
  default.
* **Its licence is its own** ([ART-LICENSE.md](../../../ART-LICENSE.md); ADR-0008,
  amendments): for this project only, credited, not under Apache-2.0.
* **Over it:** the scene is light, as before, so the title keeps the logo in black at
  the 15% floor. The version sits over the shield's rim, so its fill rises (to 178 of
  255 at 100%) to read; both stay ink on white.

### 2026-10-28: Preferences, and W1's saved setting (ADR-0025)

ADR-0025 brings the preferences store that W1 and W3 waited for. With it accepted (2026-10-28):

* **W1 stands:** the card shows at every start. Its alternative, a "Don't show again"
  box, no longer needs an ADR of its own: it becomes a later Appearance or Startup key
  in ADR-0025's store (ADR-0025 §11), with an amendment here when it's built.
* **W3 and §5:** "Preferences…, once it exists" and "Preferences appears when there are
  preferences" are met by ADR-0025 §9. From UI/UX's slice S4, `AppActions` owns a
  Preferences command, with `PreferencesRole` and `StandardKey.Preferences`, in the
  main window's File menu; Qt moves it to the application menu on macOS.
* **The welcome screen has no menus** (the amendment of 2026-10-17 above), so how
  Preferences is reached while the card is up is left to UI/UX before S4 (ADR-0025 §9).
