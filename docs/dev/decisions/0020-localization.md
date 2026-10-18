# ADR-0020: Localization, starting with a skeleton

* **Status:** **Accepted** (not built). The maintainer asked on 2026-10-17 for spelling to
  follow the user's language settings, and for the localization system's skeleton to be
  built now. After UI/UX's and Support & Review's reviews, the maintainer approved L1–L5
  as recommended on 2026-10-18 ("Approve all").
* **Builds on:** ADR-0003 (layers: core and calculators are standard library only),
  ADR-0019 (units registry), ADR-0017 (result fields; R1, and F5, the decimal separator)

## Context

* Every user-facing string is English, written inline: labels, help, notes, errors,
  menus, and unit names. Unit names currently use British spelling ("millimetre").
* The maintainer wants the spelling, and later the language, to follow the user's
  settings.
* Numbers are always written with "." as the decimal point (ADR-0017 F5). Most of
  continental Europe writes ",", though en_GB and de_CH write "." too.
* Strings come from three layers: core and calculators (no Qt), the CLI, and the GUI (Qt).
  One system has to serve all three.
* Many strings are declarations evaluated at import time: calculator labels, help, method
  notes and unit names.

## Decision

### 1. One translation system for every layer: GNU gettext (L1)

* Python's standard-library `gettext`, with `.po` source catalogs and compiled `.mo`
  files, in a new `caddcalc.core.i18n` module that core, calculators, the CLI and the GUI
  all use. It needs no Qt, so it fits ADR-0003's layers. Qt for Python's own
  "Translating Applications" tutorial documents this route beside Qt Linguist, and
  comparable PyQt apps (MusicBrainz Picard, Electrum) use it.
* **The API is deferred translation.** Declarations mark text with a no-op `N_()`, and
  `pgettext` context where a short word is ambiguous ("in" the unit, "Copy" the verb).
  Text is translated where it's shown: the GUI, the CLI, `describe_note`, spoken names.
  So the language never has to be chosen before a calculator module is imported. A test
  imports a calculator before the locale is set and still sees the test locale's text.
* `core.i18n` holds one `GNUTranslations` object and exposes its bound functions (`_`,
  `ngettext`, `pgettext`, `npgettext`), cached and clearable for tests. It never calls
  `install()` into builtins (Python's guidance for libraries). `_("")` is guarded, as
  gettext returns the catalog header for it.
* **Translatable text is one template per sentence, with named placeholders**
  (`{value}`, `{limit}`), so translators can reorder words. Accessible names and status
  messages too. A test checks that every translation keeps its source's placeholder set.
* **Qt's own strings** (standard dialog buttons) use Qt's shipped catalogs:
  `QTranslator.load(locale, "qtbase", "_", QLibraryInfo.path(TranslationsPath))`,
  installed before any widget is built.
* **Tooling:** Babel as a dev dependency (BSD-3-Clause) extracts and compiles. Its default
  keywords already cover `_`, `N_`, `ngettext`, `pgettext` and `npgettext`. There's no
  runtime dependency: the standard library reads the `.mo` files.
* **Catalogs:** `.po` files are committed; `.mo` files are compiled in the build and in a
  test. The `.mo` files and PySide6's `qtbase_*.qm` go on ADR-0009's packaging checklist.

### 2. The source language is US English (L2)

* Strings are written in US English, as NIST SP 811 is: its Preface says it uses the
  American spellings "meter", "liter" and "deka".
* British English is the first catalog: "millimetre", "metre", "colour". It proves the
  pipeline with almost no translation work.
* **It serves every English locale outside the US,** following CLDR's parent locales
  (en_001): en_GB, en_AU, en_NZ, en_IE, en_ZA, en_IN and en_CA all get it. Canada writes
  "metre" and "colour" too. en_US and the US territories use the source text.

### 3. Locale selection (L3)

* **GUI, words:** `QLocale.system().uiLanguages()` (underscore form), passed as gettext's
  `languages=`. It's the same list `QTranslator` walks, so our strings and Qt's always
  pick the same language.
* **GUI, numbers:** `QLocale.system()`, which follows the regional-format setting. "English
  words, German number format" is a normal setup, and it gets English words with "0,3119".
* **CLI:** `--lang` or `CADDCALC_LANG` wins, then `LANGUAGE`, `LC_ALL`, `LC_MESSAGES` and
  `LANG`, as Python's gettext reads them, then the source language. Those variables are
  usually unset on Windows and macOS, so reading the OS setting in the CLI is a later
  step. Until then the CLI there writes the source language and ".".
* A missing catalog falls back to the source language, never to an error.
* **A language change takes effect at the next start,** including the later Preferences
  setting, which then wins over the system.

### 4. Numbers (L4)

* **Only the decimal separator comes from the locale.** Digits stay Latin, the minus sign
  stays ASCII "-", and there's no digit grouping, so decimal alignment and pasting keep
  working. The front end supplies the separator (`NumberSymbols` in `DisplayPrefs`); core
  never uses Python's `locale` module, which isn't thread-safe and changes the whole
  process.
* **On screen,** numbers the app formats use the locale's separator: "0,3119 mm".
  Numbers quoted from a source ("gives 0.16 in at 0.063 in") and document numbers
  ("AC 43.13-1B") stay as published. Text is never converted by replacing "." with ",".
* **Typed input:**
  * the locale's decimal separator, and "." always
  * group separators are never accepted, so "1.234" is 1.234 in every locale
  * a "," where it isn't the locale's decimal is refused with a clear message, never read
    as a group separator: in en_US, "1,5" is an error, not 15
  * one decimal mark per number; U+2212 (−) is accepted as a minus sign
  * text the app writes into a field (defaults, the shared thickness) uses the locale;
    text the user typed is kept as typed
* **Copy (the decision in L4).** Recommended:
  * The Copy button and Ctrl+C write "." in every locale, as ADR-0017 R1 already says.
    AutoCAD reads "," as the separator between coordinates (AutoCAD help, "To Enter
    Absolute 2D Cartesian Coordinates": `x,y`), so "0,3119" pasted into a command is
    read as a point: silently wrong geometry. Autodesk's support article "Customizing
    dimension number formats in AutoCAD products" (2025) says AutoCAD uses a point as
    the decimal separator for displaying and entering decimal numbers, with dimension
    styles the exception. A "." pasted into a comma-locale spreadsheet fails visibly
    instead.
  * Copy all (tab-separated, for spreadsheets) uses the locale's separator. Tabs separate
    the cells, so a comma can't break a row.
  * In comma locales, the context menu adds "Copy 0,3119", named by its effect.
  * The status bar quotes exactly what was copied.
  * "With unit" and "full precision" follow the same rule as Copy.
* **JSON and the CLI's machine output always use ".",** and JSON's labels and notes stay
  in the source language, which is stable for scripts. A `lang` field comes only if JSON
  text is ever localized.
* This resolves ADR-0017's F5; its KI closes when this is built.

### 5. Plurals

* Displayed values use symbols, which are never pluralized, so they need no plural form.
* Spoken names choose singular or plural from the number **as shown**, by CLDR's plural
  rules for the language: English says "1 inch" but "1.0000 inches" and "0.5 inches".
  `core.i18n` gets a plural-category function, with English first and a rule per shipped
  language. gettext's `ngettext` is used only with whole counts, since its rules are
  integer-only and Python warns on a float.
* Spoken compound forms ("1 foot 4 and 3 sixteenths inches") are grammar, not just words.
  They're per language, with English first.

### 6. The skeleton, now; the sweep, later (L5)

The skeleton covers:
* `core.i18n` with the deferred API above, locale selection, catalog loading, and the
  plural-category function
* the extraction and compile tooling, and a check that the catalogs are current
* the British catalog for unit names and a few common words
* units' shown and spoken names, through the registry (ADR-0019), marked with `N_()`
* a **pseudo-locale** for tests, `en_XA`, made by a small generator in `tests/` from the
  `.pot` and never shipped. It accents letters (Latin-1 and Latin Extended-A only), pads
  each string by about 40%, wraps it in `⟦…⟧`, and fills every plural form. It never
  touches placeholders, numbers, unit symbols, the product name, or "&" mnemonics. A
  string shown plain or only partly bracketed is unmarked, translated too early, or
  pieced together from fragments. A test checks that nothing clips at the minimum window
  size, and that the welcome card's version pane stays inside its safe area.
* calculator-list tooltips for names that elide
* a rule in the guidelines: new user-facing strings are marked from now on, with `N_()`
  in declarations, named placeholders, and a context for short words

Marking every existing string (labels, help, notes, errors, menus) is a separate sweep,
done calculator by calculator, with the pseudo-locale test showing progress. A domain's
`Fact` still fills positional `{}` fields; the sweep moves it to named ones.

## Decisions

All five were decided by the maintainer as recommended on 2026-10-18. The alternatives are
kept for the record.

| | Question | Decided | Alternatives |
|---|---|---|---|
| L1 | Translation system | GNU gettext (standard library) for all our strings, with deferred translation; Qt's own catalogs for Qt's built-in strings | Qt Linguist (`tr()`, .ts files) everywhere, which can't reach the Qt-free core and CLI |
| L2 | Source language | US English, with a British catalog for every English locale outside the US | British English as the source |
| L3 | Locale selection | The system's language and regional-format settings (GUI); `--lang`, `CADDCALC_LANG` and the standard variables (CLI); a change applies at the next start | Always English until a preference exists |
| L4 | Numbers | The locale's decimal separator on screen and in typing (no grouping); **Copy and Ctrl+C always "."** for CAD; Copy all in the locale's form for spreadsheets, with "Copy 0,3119" in the menu; "." in JSON | Copy follows the locale, with a decimal-point copy in the menu; or a "Decimal separator: system / point" preference; or "." everywhere, as now |
| L5 | Scope now | The skeleton: infrastructure, the British catalog, the pseudo-locale test, unit names, and the guideline. The full string sweep comes later | The full sweep now |

## Consequences

* Spelling follows the user's settings from the first release that has the skeleton.
* New strings are marked from day one, so the later sweep only covers existing code.
* Translators work in standard .po files, which common tools support.
* A comma-locale user sees and types their own decimal mark, and a one-click copy still
  pastes correctly into CAD.
