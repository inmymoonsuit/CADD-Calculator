# ADR-0025: Saved preferences, starting with light and dark

* **Status:** **Accepted; not yet built** (maintainer, 2026-10-28). The maintainer asked
  for this ADR, drafted by the Calculator Engine lane with the other lanes' sections and
  reviewed by Support & Review (relayed by PM). Its amendments to other ADRs took effect
  on acceptance.
* **Date:** 2026-10-28
* **Deciders:** the maintainer (M1–M5, relayed by PM, 2026-10-28); PM (C1–C6, where the
  lanes' proposals differed)
* **Drafted by:** Calculator Engine (the model, the store, isolation), UI/UX & Design (the
  theme and the dialog), Packaging & Builds (install, uninstall, the smoke test); prior
  art by Support & Review
* **Builds on:** ADR-0003 (layers), ADR-0013 decision B (session-only settings), ADR-0015
  W1 and W3 (Preferences in the menus), ADR-0020 (translated text, next-start language),
  [design/palette.md](../design/palette.md)

## Context

* The app saves nothing between runs. ADR-0013 B made family settings session-only, and
  its Context says the app creates no user files. Several ADRs wait on a store:
  * ADR-0015 W1, "Don't show again" on the welcome screen
  * ADR-0021 §3 item 6, the window's size and position
  * ADR-0023 C8, a text size
  * ADR-0024 D4 and §6, a unit system and remembered pickers
  * ADR-0020 §3, a language setting
* The maintainer wants a foundation for saved preferences, with a light and dark choice
  as its pilot, in clean, properly bounded code that later preferences build on.
* Today the scheme follows the system only. `gui/icons.py`'s `current_scheme()` reads
  `QStyleHints.colorScheme()`, falling back to the palette's lightness. Only
  `gui/window.py` connects to `colorSchemeChanged`; the focus ring, result fields, unit
  pickers and welcome screen call `current_scheme()` when they draw. `gui/window.py`
  writes colours inline into its HTML.
* The app sets its organization and application names both to "CADD Calculator", so
  Qt's own folder for it would be `CADD Calculator\CADD Calculator` (measured by S&R).

### Prior art (official documentation and source; paraphrased)

S&R's measurements were on Windows 11 with PySide6 6.12.0.

* **Storage:**
  * QSettings' native format uses the registry on Windows, where `setPath` doesn't
    move it, so there's no file to delete and no portable mode. It's Qt-only.
  * QSettings' INI format returns strings unless the values are type-tagged. On a
    malformed file it flags an error, then drops the lines it couldn't parse at its next
    write.
  * QStandardPaths' AppConfigLocation is Local AppData on Windows and
    `~/Library/Preferences` on macOS. With this app's names it doubles the folder.
  * platformdirs' `user_config_dir` is Local AppData on Windows too. It's a new
    dependency.
  * The standard library's `json` reads and writes. `tomllib` only reads.
* **The scheme (`QStyleHints.setColorScheme`, Qt 6.8 and later):**
  * On Windows the windows11, Fusion and Windows styles follow it, and the signal fires.
    **windowsvista keeps a light palette while `colorScheme()` reports Dark.**
  * **Offscreen it does nothing and never signals.**
  * macOS follows it fully. On Linux, gtk3 and KDE follow it in recent Qt versions; the
    portal and generic themes ignore it, and gtk3 can report Dark while drawing light.
  * Windows' high contrast overrides it.
* **Apps:**
  * KiCad keeps JSON with one integer version and step-by-step migrations. It doesn't
    migrate a file from a newer version, skips bad keys one at a time, and writes
    atomically, only when the bytes change.
  * FreeCAD and LibreCAD store only the user's overrides.
  * Inkscape runs on defaults when the file is bad, keeps the bad file, and stops saving.
  * Spyder writes every key, so it needs a snapshot of old defaults to update them.
  * Portable modes are one override each: `KICAD_CONFIG_HOME`, `FREECAD_USER_HOME`,
    `INKSCAPE_PROFILE_DIR`, and the AppImage's `.config` folder beside the file.
* **Lessons:** version the file with one integer, and never overwrite a newer one; on a
  bad file, run on defaults, keep the file and say so once; write atomically and only
  on change; store overrides only, so an improved default reaches users.

Sources:
* Qt: [QSettings](https://doc.qt.io/qt-6/qsettings.html),
  [QStandardPaths](https://doc.qt.io/qt-6/qstandardpaths.html),
  [QStyleHints](https://doc.qt.io/qt-6/qstylehints.html),
  [what's new in 6.10](https://doc.qt.io/qt-6/whatsnew610.html); qtbase's `qsettings.cpp`,
  `qwindowstheme.cpp`, `qwindowsvistastyle.cpp`, `qcocoatheme.mm`, `qkdetheme.cpp`;
  QTBUG-130385, QTBUG-132929, QTBUG-134022, QTBUG-134023, QTBUG-145386
* Python: [json](https://docs.python.org/3.12/library/json.html),
  [tomllib](https://docs.python.org/3.12/library/tomllib.html),
  [os.replace and os.fsync](https://docs.python.org/3.12/library/os.html#os.replace)
* Folders: [XDG Base Directory Specification](https://specifications.freedesktop.org/basedir-spec/latest/),
  [Flatpak's conventions](https://docs.flatpak.org/en/latest/conventions.html),
  [Apple's File System Programming Guide](https://developer.apple.com/library/archive/documentation/FileManagement/Conceptual/FileSystemProgrammingGuide/MacOSXDirectories/MacOSXDirectories.html),
  [Microsoft's KNOWNFOLDERID](https://learn.microsoft.com/en-us/windows/win32/shell/knownfolderid),
  [platformdirs](https://platformdirs.readthedocs.io/en/latest/platforms.html)
* Apps: [KiCad](https://docs.kicad.org/9.0/en/kicad/kicad.html) and its
  `json_settings.cpp` and `settings_manager.cpp`; FreeCAD's `Parameter.cpp`; Inkscape's
  `preferences.cpp`; LibreCAD's `rs_settings.cpp`; Spyder's `config/user.py`;
  [AppImage portable mode](https://docs.appimage.org/user-guide/portable-mode.html)

## The maintainer's decisions (2026-10-28, relayed by PM)

| # | Decided |
|---|---|
| M1 | **The CLI never follows saved preferences.** Explicit flags stay the way to choose. |
| M2 | **Standard controls keep each platform's native style.** Brand colours stay on the app's own surfaces: results, the welcome screen, the document. |
| M3 | **Only how the app looks and behaves is saved.** Family settings and inputs stay session-only, so ADR-0013 B holds for them. |
| M4 | **Reserved in the design, not built in the pilot:** pack-supplied defaults (built-in, then the pack, then the user), and a portable mode beyond the environment override. |
| M5 | **Where the platform ignores the request, an explicit Light or Dark is honoured, non-native** (S&R's MD2, chosen over disabling them there with "Your system decides"). It switches to the Fusion fallback in our palette, so the choice still works. Match system stays native everywhere, and Windows 11 and macOS stay native for all three choices. High contrast still beats everything: the app follows the system, with no fallback (§8). |

## Decision

### 1. What a preference is (M3)

* A preference is a choice about how the app looks or behaves, the same whatever is
  being calculated: the colour scheme now; later the welcome screen at startup, the
  window's geometry, a text size, remembered pickers, a language.
* **Not a preference:** a family setting (thickness, radius, K), an input, a method, a
  result. They stay session-only (ADR-0013 B). Saved sessions remain a separate roadmap
  item, with their own decision.
* Nothing in `core` or `calculators` reads a preference. A later key that changes what's
  shown, such as remembered pickers, is turned by the GUI into what it already passes
  down (`ShownUnits`, `DisplayPrefs`), so a result never depends on a hidden file.

### 2. One new Qt-free layer, `caddcalc.preferences` (C1)

```
caddcalc.cli ──▶ caddcalc.gui ──▶ caddcalc.preferences ──▶ caddcalc.calculators ──▶ caddcalc.core
```

* **`preferences/model.py`:** the definitions and their kinds, the registry, the frozen
  snapshot, and the codec with its migrations (§3). Pure: no files, no environment.
* **`preferences/paths.py`:** the folder, by our own resolver of about 25 lines (§4).
* **`preferences/store.py`:** reading and writing one file (§5).
* **`gui/preference_keys.py`:** the GUI's own keys, starting with the colour scheme. It
  imports no Qt.
* It's standard library only, and may import `core` (for `core.i18n`, so its messages
  are translatable). An import-linter layer puts it between `gui` and `calculators`, and
  it and `gui/preference_keys.py` join the no-Qt contract.
* **The CLI never imports it (M1),** enforced by a forbidden contract from `caddcalc.cli`
  to `caddcalc.preferences` with indirect imports allowed, since `caddcalc gui` hands
  over to the GUI, which reads them.
* **Why its own layer, not `core.preferences` with a services layer above:** nothing in
  `core` or `calculators` uses preferences (M1, §1), so a model in `core` would put app
  chrome inside the calculation engine's boundary. One layer keeps the model and its
  file handling together, and keeps both out of the GUI so they're tested without Qt.
* **Composition goes up** (guidelines §1.5): the layer offers the mechanism; the GUI
  declares its keys and builds the registry from them, as `calculators` decides which
  calculators exist.

### 3. The model

* **A definition, `Preference[T]`:**
  * `key`: two or more dotted segments, lowercase with underscores, checked when it's
    defined. A built-in key has two, `section.name`, such as `appearance.color_scheme`;
    a plugin's, later, start with its own segment (§11).
  * `kind`: how a value is checked, encoded and decoded. The pilot builds `Choice`, a
    value from a fixed tuple of stable ids. `Flag`, `Number` and `Text` are added with
    their first key, each one class against the same interface.
  * `default`: the built-in value, checked against the kind when it's defined.
  * `applies`: `live`, or `next_start` for a key the app reads only at startup, such as
    the language (ADR-0020 §3).
  * The user's words: a label, a help line, and for a choice each option's label. They're
    marked with `N_` and translated when they're shown, as calculators' names are
    (ADR-0020; no import-time side effects, guidelines §2.4). A page shows them, as a
    calculator's form shows a `Param`'s.
* **`PreferenceRegistry`:** a frozen set of definitions. A duplicate key, or a key
  that's the start of another key (`a.b` beside `a.b.c`), is refused when it's built.
* **`Preferences`:** a frozen snapshot of the user's overrides.
  * `get(pref)` gives the override, or the definition's default.
  * `with_value(pref, value)` and `without(pref)` give new snapshots. `without` is
    Reset.
  * It also carries, untouched, the keys this build doesn't know, and the raw value of
    any key whose stored value was invalid.
  * It's passed in where it's needed, never read as a global (guidelines §2.4).
* **The codec:** `decode(data) → (Preferences, problems)` and
  `encode(Preferences) → bytes`.
  * The file is one JSON object: `"schema": 1`, and `"preferences"`, a flat object of
    dotted keys and their values.
  * Encoding is UTF-8 with LF, two-space indents and sorted keys, ending with a newline,
    so the same snapshot always gives the same bytes. NaN and the infinities are
    refused both ways.
  * **Migrations** are pure functions, one schema step each, kept in `model.py`. There
    are none at schema 1. Before the first release a renamed or dropped key is simply
    gone, with no shim (pre-alpha).

### 4. Where the file is (C3)

The store takes an explicit path. The app resolves one with `paths.config_dir(platform,
env, home, names)`, then uses `preferences.json` in it.

* **The resolver is a pure function.** It never reads `os.environ`, `sys.platform` or
  `Path.home()` itself: the app passes in the real ones, and a test passes its own. (On
  Windows `Path.home()` follows `USERPROFILE`, not `HOME`, so only a resolver that takes
  the home folder can be tested on every branch from every platform.)
* **The folder names come from the GUI,** from `gui.branding`, the one source of the
  product's name: `CADD Calculator` for Windows and macOS, `cadd-calculator` for Linux.
  A test pins them.

| Platform | Folder | Why |
|---|---|---|
| Windows | `%APPDATA%\CADD Calculator\` | The Roaming folder (FOLDERID_RoamingAppData) is for a user's settings that follow them between machines; Local is for caches and machine-bound data. |
| macOS | `~/Library/Application Support/CADD Calculator/` | Apple's guide reserves `~/Library/Preferences` for the defaults system, and puts an app's own files in Application Support. |
| Linux | `$XDG_CONFIG_HOME/cadd-calculator/`, else `~/.config/cadd-calculator/` | The XDG spec. No spaces, matching Packaging's other Linux names. Inside the Flatpak, `XDG_CONFIG_HOME` is the sandbox's own folder, with no extra permissions. |

* **`CADDCALC_CONFIG_DIR` overrides all three,** as `CADDCALC_BRANDING` names a pack.
  It's the portable mode for now.
* A variable that's set must be an absolute path; XDG says a relative one is invalid and
  ignored. An override that can't be used never falls back to the real profile: the
  store then runs in memory, with one notice. So does a platform folder that can't be
  found (no `APPDATA`, no home).
* **The folder is created on the first save,** never on reading.
* **The same folder in every edition,** since its names come from the product's name,
  which every edition shares (ADR-0016 S4), and the public and edition installers share
  an `AppId` (§10). Qt's application name no longer decides where anything is saved
  (ADR-0011, amendments).
* **Why not QStandardPaths:** it gives Local AppData on Windows, doubles the folder with
  today's names, and uses `~/Library/Preferences` on macOS. It would also put the path
  in Qt, where the store couldn't reach it without Qt.

### 5. The store (C4, C5)

* **`PreferenceStore(path, registry)`;** with no path it keeps everything in memory and
  writes nothing.
  * `load()` gives the snapshot and its problems.
  * `write(pref, value)` and `reset(pref)` save one key's change and return a problem
    or none.
* **The session's snapshot is the GUI's,** as its `DomainSettings` is (ADR-0013 §7).
  The GUI updates it whatever the store returns, so a failed save never undoes a choice.
* **Only overrides are saved.** An override equal to the effective default is dropped,
  and Reset deletes the key, so an improved default reaches users. The effective default
  is the definition's today, and a pack's once there are pack defaults (§11), so a user
  who picks the built-in value under a pack's other default is saved. In the pilot,
  choosing Match system is Reset.
* **Unknown keys are kept** when writing, so an older and a newer build can share the
  file.
* **An invalid value** falls back to the default, with a problem naming the key, and its
  raw value is kept in the file until the user sets that key.
* **Writes:**
  * **atomic:** a temporary file with a name unique to this write (`tempfile.mkstemp` in
    the same folder, so two copies of the app never share one), flushed and fsynced,
    then `os.replace`, then on POSIX the folder fsynced too. A failed write removes its
    temporary file and leaves the old file whole.
  * **only when the bytes change**
  * **one key at a time:** the store re-reads the file, changes that one key, and writes.
    Several running copies of the app each keep the others' keys; the last write of a key
    wins. There's no locking and no live sync.
  * **no retry on failure** (guidelines §2.3): the session keeps the value, and the user
    gets one notice.
* **A file that can't be read** (an `OSError`, such as a lock held by antivirus, the
  indexer or another copy of the app): the session runs in memory and writes nothing,
  with one notice. The file isn't corrupt and is never moved aside.
* **A corrupt file** is bad content only: over 1 MiB (checked from its size before it's
  read), not UTF-8, not JSON, not an object, or no integer schema. Defaults for the
  session, and one non-modal message. The first save moves it to `preferences.json.bad`,
  replacing an older one, and only then writes the new file. It's never silently
  overwritten.
* **A newer schema** is read best effort, for the keys this build knows, and never
  written. Changes then last for the session, and the user is told once.
* **The re-read before each write follows the same rules:** if it fails, or finds a
  newer schema, nothing is written; if it finds the file corrupt, it's moved aside
  first.
* **No file contents are logged** or shown in a message, only the key and what's wrong.
* **Problems are values** (`PreferenceProblem`: kind, key, message), never exceptions
  past the store. The GUI shows each kind once per session.

### 6. Isolation in tests and smoke runs (C6)

* **An autouse conftest fixture** sets `CADDCALC_CONFIG_DIR` to the test's `tmp_path`,
  and points `APPDATA`, `XDG_CONFIG_HOME`, `HOME` and `USERPROFILE` into it too.
* **A guard test** runs every platform's branch of the resolver on every OS, with the
  environment and home the fixture gives, and checks each result is under `tmp_path`,
  so the suite can't touch the maintainer's real profile (§4).
* **They land in the same commit as the store** (E2), never after it.
* **`--smoke-test=DIR`** uses `DIR/preferences/`. Without a DIR it keeps everything in
  memory and writes nothing.
* **The scheme:** offscreen `setColorScheme` does nothing, so offscreen tests take the
  Fusion fallback (§8), never the native path. The native path is tested through an
  injected seam, and each platform gets a native check, recorded. The fallback being
  what offscreen runs is what makes §8's switching test possible there.

### 7. The command line (M1)

`caddcalc run` and `caddcalc list` read no preferences. Every display choice stays an
explicit option (`--unit`, `--output-set`, `--lang`), so a script's output never
depends on a hidden per-user file (ADR-0013 §7).

The forbidden contract (§2) stops only direct imports, so a behaviour test backs it:
`caddcalc run`, plain and with `--json`, gives the same output with a dark, an odd and a
corrupt `preferences.json` under `CADDCALC_CONFIG_DIR` as with none.

### 8. The theme (UI/UX's section; M2)

* **`gui/theme.py`, a `Theme` QObject,** holds the choice, the resolved scheme, a
  `changed(scheme)` signal, and `apply(choice)`.
  * The choice's ids (`system`, `light`, `dark`) are the colour-scheme definition's in
    `gui/preference_keys.py` (E1). The Theme takes them from there, so there's one list.
  * It alone calls `QStyleHints.setColorScheme` and `unsetColorScheme`. System follows
    the OS live.
  * The effective scheme is checked against the palette, since windowsvista and gtk3 can
    report Dark while drawing light.
* **When a request counts as ignored:** once the change is delivered, the palette's
  window lightness disagrees with the requested scheme, or the hint stays Unknown. By this rule
  offscreen, windowsvista, and Linux's portal and generic themes ignore it. The Theme
  then falls back to Fusion with a `QPalette` built from the UI palette, so an explicit
  Light or Dark still works there, without the native look (M5). Match system never
  takes the fallback: it stays native everywhere.
* **When the check runs:** after the change is delivered, on `colorSchemeChanged` or on
  the next turn of the event loop, never straight after the call. On Windows the palette
  updates at once (S&R measured a window lightness of 30 straight away); Linux's gtk3
  and KDE themes may deliver it later. If the native palette later agrees with the
  request, the Theme leaves the fallback. S2's native Linux check confirms this.
* **High contrast wins.** While the system asks for high contrast
  (`styleHints().accessibility().contrastPreference()`), or reports an Unknown scheme
  for that reason, the Theme follows the system and applies no fallback, whatever the
  choice; the Appearance page says why. A test drives it through the seam.
* **Explicit palettes are sticky** (S&R measured both, natively):
  * A widget given an explicit palette role keeps it across a switch, while its other
    roles follow. So every widget palette the app sets is reapplied on `Theme.changed`.
  * An application palette set with `setPalette` survives `unsetColorScheme`. So leaving
    the fallback resets it with `setPalette(QPalette())` and restores the style the app
    started with.
  * A test switches Light, Dark, System and back, walking every widget, an open welcome
    card and dialog included, and finds no colour from the other scheme in any palette
    or stylesheet. It runs offscreen, on the fallback path (§6).
* **The fallback palette is S2's to design:** a full `QPalette` needs roles the UI
  palette doesn't have yet (Base, AlternateBase, Button, ButtonText, Highlight,
  HighlightedText, PlaceholderText, Link, ToolTip, and the Disabled group), and in dark
  the window and the fields must differ. The mapping, its contrast tests and
  [design/palette.md](../design/palette.md) land in S2.
* **`app.py` creates one `Theme`** before the first window, so nothing flashes, and
  passes it down. `current_scheme()` and the direct `colorSchemeChanged` connection are
  removed outright (pre-alpha).
* **Colours:** `window.py`'s inline HTML colours become classes, with one
  `QTextDocument` stylesheet per scheme generated from the palette's roles. Labels
  coloured by `setStyleSheet` move to the widget palette, reapplied on each change as
  above. Contrast tests run for both schemes. This is the 0.3 roadmap's light and dark
  item.
* No conflict with ADR-0023. A text size (C8) becomes a later Appearance key.

### 9. The Preferences dialog (UI/UX's section; amends ADR-0015 W1 and W3)

* **`gui/preferences/`:** a `PreferencesDialog`, and a `PreferencesPage` base that edits
  a draft value and never touches the store. A list of pages appears only once there
  are two.
* **The pilot's Appearance page:** "&Match system" (the default), "&Light" and "&Dark",
  with the help "Follows your computer's light or dark setting."
* **Changes apply and save at once,** and the dialog has one Close button. It's
  window-modal, over the welcome screen too.
* **File > Preferences…** is `AppActions`' Preferences command (ADR-0015 §5), with
  `PreferencesRole` and `StandardKey.Preferences`.
* **Open for UI/UX before S4:** the welcome screen has had no menus since ADR-0015's
  amendment of 2026-10-17, only an About button and the X. How Preferences is reached
  while the card is up (a shortcut, a button beside About, or not at all) is UI/UX's to
  settle; the dialog's window-modality over the card stands either way. S&R measured
  that `StandardKey.Preferences` has no binding on Windows (an empty list); it's ⌘, on
  macOS and depends on the desktop on Linux. So the standard key alone is no way in on
  Windows: it would take a fixed Ctrl+, or a button.

### 10. Install, uninstall and the smoke test (Packaging's section)

* **Uninstalling leaves the file,** Inno Setup's default, so the `.iss` doesn't change:
  * a reinstall keeps the user's choice
  * the public and edition installers share an `AppId` and the file
  * silent and winget uninstalls can't ask
* **User docs, in the same commit as S5,** since main is public and the pages must be
  true the moment the app saves a file. Packaging supplies the text:
  * `installing.md` and `code-signing.md`'s "Removing the app" give the folder, one line
    per platform; the Flatpak's is `flatpak uninstall --delete-data`. The two pages'
    Linux wording, which disagrees today, is fixed.
  * `code-signing.md`'s Privacy says the app saves your preferences in one small file
    on your computer, and nothing is sent anywhere.
* **The smoke test:**
  * `build.py` empties `DIR/preferences`. Run 1 reads `system` and saves `dark`; runs 2
    and 3 load `dark`.
  * The report gains `"preferences"`: `file`, `loaded`, `saved` and `color_scheme`.
    `color_scheme` is required on Windows and macOS only.
  * `build.py` fails if the file is outside DIR.
  * `test_installer.py` checks that a silent uninstall leaves a seeded file.
* No dependency is added (C2), so the notices don't change.

### 11. Reserved, not built (M4)

* **Pack defaults:** a branding pack may later supply defaults, layered built-in, then
  the pack, then the user. `get` reads a default from the definition today; the layer
  slots in there, as a later amendment to ADR-0011 with its own `branding.toml` table.
  Overrides are compared with the effective default (§5), so a pack's default changes
  reach users too.
* **A portable mode beyond the override:** a marker folder beside the executable, checked
  to be writable, never under Program Files, as ADR-0011 looks beside it for a pack.
* **Plugin keys:** later, through a `caddcalc.preferences` entry-point group (ADR-0006).
  A plugin's keys start with its own segment, so they have three or more
  (`acme.section.name`), and built-in sections are reserved.
* **Later keys, each added by its own ADR's amendment:** the welcome screen at startup
  (ADR-0015 W1), the window's geometry (ADR-0021), a text size (ADR-0023 C8),
  remembered pickers and a unit system (ADR-0024 D4), the language (ADR-0020 §3,
  `next_start`).
* **The window's geometry is machine-bound,** yet the file is in Roaming on Windows
  (§4). That's tolerable: ADR-0021 §3 item 6 checks a saved geometry against the
  current screens before using it, so a roamed one that doesn't fit is ignored. If
  more machine-bound keys come, they'd get a second file in Local, by their own
  amendment.

### 12. Public surface

`preferences.json`'s format, its key names, and `CADDCALC_CONFIG_DIR` join the public
surface (guidelines §1.6). Before the first release they may change outright
(pre-alpha); after it, a renamed key needs a migration.

## PM's calls where the lanes differed

| | Called | Why | Not taken |
|---|---|---|---|
| C1 | One layer, `caddcalc.preferences` (§2) | Nothing below the GUI uses preferences, so the model doesn't belong in `core`. | `core.preferences` plus a services layer (Engine); the model in `gui` (no Qt-free tests) |
| C2 | `preferences.json`, the standard library's `json` | No dependency and no writer to maintain; KiCad is the model; the dialog is how to edit, so hand-editing isn't a goal. | TOML with our own writer (Engine); TOML with `tomli-w` (a dependency; comments are lost on rewrite anyway) |
| C3 | Our own resolver and folders (§4) | Roaming on Windows, Application Support on macOS, no doubled folder, and no Qt in the store. | QStandardPaths (S&R); platformdirs (a dependency, Local on Windows) |
| C4 | Overrides only; Reset deletes; unknown keys kept; an invalid value's raw kept (§5) | Improved defaults reach users, and builds can share the file. | Writing every key, as Spyder does, which needs a defaults snapshot |
| C5 | Atomic, on change, one key, no retry; bad content to `.bad`; a failed read and a newer schema read-only (§5) | Never lose the file, never fight another copy of the app, never hide a failure. | Writing on exit (lost on a crash, as FreeCAD found); file locking; overwriting a newer file |
| C6 | The fixture and the guard in the store's commit; smoke in `DIR/preferences/` (§6) | A test or smoke run must never write the maintainer's real profile. | Isolation added after the store |

## The build order

1. **This ADR,** reviewed by S&R and accepted by the maintainer.
2. **Engine E1, the model,** first, since the Theme takes its ids from it (§8):
   `preferences/model.py`, `gui/preference_keys.py`, and the import-linter contracts
   (the layer, the no-Qt list, the CLI's forbidden import), with
   `docs/dev/architecture.md` and guidelines §1.1, §1.3, §1.6 and §2.4 updated in the
   same commit.
3. **Then in parallel, sharing no files:**
   * **Engine E2, in one commit:** `paths.py`, `store.py`, the conftest fixture and the
     guard test, and §7's behaviour test for the CLI.
   * **UI/UX S1 to S3:** the `Theme` injected with no change in behaviour; the native
     apply with the Fusion fallback, and the smoke fields `theme_style` and
     `theme_scheme`, with the fallback palette and its contrast tests (§8); HTML
     classes and label palettes. None needs the store.
4. **UI/UX S4,** the dialog and the menus, session-only; **then S5,** persistence through
   the store, with the user docs (§10) in S5's own commit.
5. **Packaging:** the smoke save and reload, and `docs/dev/packaging.md`, in the same
   release as S5.

## Consequences

* The app creates one user file, only when the user changes a preference, and says
  where it is.
* Later preferences are a definition and a page each, with nothing new in the store.
* A new layer, with its place in the layer contract, the no-Qt contract and the CLI's
  forbidden import. `core` and `calculators` are unchanged, and the CLI stays
  reproducible.
* The window's colours become palette roles and classes, so both schemes are tested.
* The file's format and keys are a contract with users' disks once released.
* The native path can't be tested offscreen, so each platform needs a recorded native
  check. The fallback is tested offscreen (§6).
* Where the platform ignores the request, an explicit Light or Dark comes from Fusion in
  our palette and loses that platform's native look, by the maintainer's choice (M5).
  M2 holds for Match system everywhere, and for all three choices on Windows 11 (its
  default style) and macOS. Under high contrast nothing changes the system's look.

## Alternatives considered

* **QSettings, native:** the Windows registry, no file to delete, no portable mode, and
  Qt-only.
* **QSettings, INI:** values come back as strings, and a malformed file's lines are
  dropped on the next write.
* **QStandardPaths or platformdirs for the folder:** see C3.
* **TOML:** see C2.
* **The model in `core`, the I/O in a services layer:** see C1.
* **Saving family settings too:** declined (M3); ADR-0013 B holds.
* **The CLI following preferences:** declined (M1).
* **Per-version folders, as KiCad and FreeCAD keep:** too heavy before 1.0; one integer
  schema and kept unknown keys cover side-by-side builds.
* **Fusion with our palette everywhere:** consistent, but loses each platform's native
  look (M2).
* **Asking at uninstall whether to delete the file:** silent and winget uninstalls can't
  ask, and another user's profile is out of reach.

## Revisit when

* A preference needs to be shared by the GUI and the CLI. That would revisit M1.
* A pack needs its own defaults (M4), or a lab install needs a portable folder.
* A preference outgrows one flat file, such as a list of recent files.
