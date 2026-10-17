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
  template generator, and docs/dev/design/welcome-screen.md share.
* **Connections:** the welcome screen uses bound methods only, so KI-019's weak slot
  helper stays private to `gui/window.py`; nothing needed to move.
* **Commands:** File (Exit) and Help (Welcome Screen; About). Exit closes every window
  and carries `QuitRole` and the platform's Quit shortcut; About carries `AboutRole`.
* **Fallbacks:** art that's unreadable, missing, or over 4096 px, and a logo that isn't
  a valid SVG or a usable PNG, are replaced by the generic parts with a warning. The smoke
  report's `welcome_art` and `welcome_logo` say which was shown.
* **Platform checks** that CI can't run are listed in KI-020.

