# ADR-0020: Localization, starting with a skeleton

* **Status:** **Accepted**; the skeleton is being built, so far its `core.i18n` module and
  catalog tooling (i1), the British catalog, the pseudo-locale and its tests (i2),
  units' names and plurals (i3), and numbers and the locale's wiring (i4; see
  Amendments). The maintainer asked on 2026-10-17 for spelling to
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

## Amendments

### 2026-10-18: `core.i18n` and the catalog tooling as built (i1)

* **The API.** `N_`, `_`, `pgettext`, `ngettext` and `npgettext` are functions of
  `core/i18n.py` that look up the cached translator on each call, not one object's bound
  methods (§1): a bound method taken at import would keep the old catalog after
  `clear()`. `_` and `pgettext` return `""` for `""`.
* **The translator** chains one `GNUTranslations` per catalog found, most wanted first,
  each language before its base (`en_GB`, then `en`), with `NullTranslations` last. So a
  string or a whole catalog that's missing gives the source text, never an error.
* **Choosing languages.** `use(languages, *, directories=())` takes language tags in
  either form, BCP 47 from Qt (`en-GB`) or POSIX from the environment (`en_GB.UTF-8`), and
  `posix_language` turns them into gettext's catalog names, dropping any script. The
  `directories` are searched before the shipped catalogs, for tests and the coming
  pseudo-locale. The chosen languages are the module's one piece of state besides its
  cache: the front end sets them once, at startup (§3), and `use(())` goes back to the
  source. The engineering guidelines (§2, item 4) name this exception.
* **Plurals (§5).** `ngettext` and `npgettext` refuse a count that isn't an `int`, a
  `bool` included, with a `UsageError`, where Python would only warn.
  `plural_category(shown, language)` has English's CLDR rule ("one" for i = 1 and v = 0).
  A language without a rule of its own takes English's until its catalog ships with one.
* **Where catalogs are.** `caddcalc/locale/<language>/LC_MESSAGES/caddcalc.mo`, read
  through `importlib.resources`; the template is `caddcalc/locale/caddcalc.pot`. What the
  wheel and the frozen builds take is i5's, on ADR-0009's checklist.
* **The tooling.** `scripts/i18n.py` has `extract`, `update`, `compile` and `check`, on
  Babel (the dev group). The template is written sorted, without line numbers, and with a
  fixed creation date, so extracting again changes it only when marked text changes.
  `check` compares the template with the code and each language with the template,
  checks that each translation keeps its source's placeholders, and compiles each
  language; the tests run it.
* **Nothing is marked yet,** so the template is only a header. The British catalog (i2)
  and the units' names (i3) come next. The rule for new text is in CONTRIBUTING
  ("Translating") and the engineering guidelines (§2, item 10).

### 2026-10-18: the British catalog, the pseudo-locale, and their tests (i2)

* **The British catalog is en_001's,** CLDR's own name for the English that most locales
  outside the US share, at `caddcalc/locale/en_001/`. A locale reads its catalog, then its
  parents', then its language's: `core.i18n.lineage("en_AT")` is en_AT, en_150, en_001,
  en. The parents are CLDR 47's (`common/supplemental/supplementalData.xml`,
  `parentLocales`), kept in `core.i18n` as region lists. A test checks them against the
  CLDR data that Babel ships, so a newer CLDR that moves a locale fails it.
* **en_CA is ours, not CLDR's.** CLDR 47 keeps en_CA under en, as it does en_PH, en_AE
  and en_BI. §2 puts Canada on the British catalog because it writes "metre" and
  "colour", so `core.i18n` adds that one parent. The other three keep the source
  spelling, as CLDR does.
* **What's marked.** The calculators' and the domain's names and summaries, declared with
  `N_()` and translated where they're shown: the calculator list and its tooltips, the
  page's title and summary, and the CLI's `list` and `show`. JSON keeps the source text
  (§4). The welcome card's text is marked too: its version line, its accessible name, and
  its buttons' tooltips and names, with a `button` context for "About" and "Close". A name
  inside a sentence that isn't marked yet, such as "Use Sheet Metal value", waits for the
  sweep, which marks the whole sentence.
* **The British catalog** translates what British English writes differently: so far,
  "licence" in the About button's tooltip. An empty translation means the US English
  text is right there too, so the catalog lists every string. The units' names (i3) add
  "millimetre" and "metre".
* **The tooling** gains `init LANG`, which starts a language's .po from the template, and
  `check` now reports a fuzzy translation, Babel's guess after a source changed, which is
  never compiled until someone confirms it.
* **The pseudo-locale** is `tests/pseudo_locale.py`, made from the template as §6 says and
  never shipped. Its letters come from Latin-1 and Latin Extended-A; it pads each string
  by 40% with accented filler words, so the text still wraps; and it fills every plural
  form. A test checks each rule, and that its catalog keeps every placeholder.
* **The tests.** A calculator module imported before the language is chosen still shows
  en_XA text in the list, its tooltips, and the page. At the window's least size, every
  page, in English and in en_XA, is checked for any text widget smaller than its least
  size, any wrapped label shorter than its text, any combo box that elides, and anything
  past the window's edge. The welcome card's version line stays inside its safe area in
  both languages.
* **What doesn't fit yet.** That test found three things that are cut short at the
  window's least size today, in both languages: the disclaimer, the method box, and the
  family settings page, which scrolls sideways. They're KI-023, for the window-layout
  work; the test allows those three and nothing else. It found a fourth on Linux, now
  fixed: the result fields' value and unit columns were sized to the nearest pixel of
  their text's width, so a fractional width lost the text's last pixel. They round up.
* **Tooltips for elided names.** `gui/name_tips.py` draws the list's rows as usual. When a
  row is too narrow for its name, its tooltip gives the whole name above the summary.
  Whether a name is elided is measured the way the style lays out the row's text. In
  Fusion and windows11, the painted row changes exactly at the width where the test flips.
* **CLDR's license.** The parent table and the English plural rule come from CLDR, which
  is under the Unicode License v3; THIRD_PARTY_NOTICES.md carries its notice.

### 2026-10-18: units' names and plurals (i3)

* **A plural pair, marked where it's declared.** `NP_(context, singular, plural)` marks
  a pair as one message, as `npgettext` takes it; Babel reads it through one more
  keyword. The units declare their names with it, in the "unit" context (ADR-0019 U5).
* **A form chosen by the number as shown (§5).** `npgettext_shown(context, singular,
  plural, shown)` finds the number's CLDR category in the language the text is shown in,
  then asks the catalog for that category's form. gettext chooses a form by a whole
  count, so each language's rule in `core.i18n` gives a count in each of its categories:
  1 for English's "one", 2 for its "other". `plural_category` reads "." or "," as the
  decimal mark, since a shown number has no grouping (§4).
* **The language text is shown in** is `text_language()`: the first chosen language
  with a catalog, or the source. A chosen language without a catalog shows the source
  text, so it takes English's rule, never its own rule over English words.
* **en_CA's own catalog** holds only what CLDR 47's en_CA writes differently from
  en_001, "percent". It's the first catalog that falls back to another, which showed a
  compile bug: Babel compiles an untranslated plural as the source text, which would
  hide en_001's. `compile_to` now leaves untranslated messages out, so the next catalog
  answers, and `check` reports a plural translated in some forms but not all.
* **Spoken names** are in the British spelling where a British catalog is read, "0.3119
  millimetres", and US spelling otherwise, from the source. Until §3's locale wiring
  (i4), the app shows the source.

### 2026-10-18: numbers and the locale's wiring (i4)

* **`NumberSymbols`** in `DisplayPrefs` holds the decimal mark, one character that isn't
  a digit, a sign or a space. The GUI reads it from `QLocale.system()`, which carries
  the user's own changes to their regional format, as `QLocale()` doesn't. A mark Qt
  gives as more than one character falls back to ".". The window takes the symbols as an
  argument, so the tests don't follow the machine's format.
* **On screen,** `format_number` writes the mark, so values, fields, notes' values and
  range errors all take it. A line of work is math: it's built with "." and then
  `typeset`, number by number, so the formula's own constants match the values in it
  ("0,64·T + 1,57·R"). Where the mark is ",", a function's arguments are split with ";",
  as comma-locale spreadsheets write them: "max(2,5; 0)". A step's note, and the notes'
  phrases quoted from a source, are prose and stay as written.
* **Typing** takes the locale's mark and ".", at most one mark in a number in a comma
  locale. A comma that isn't the mark is refused, saying why. U+2212 reads as "-", and
  "_", which Python's `float()` takes as grouping, is refused too. The identity test
  allows the clearer message for "3,5 mm", which was refused before as well.
* **Text in a field.** `TypedValue` keeps the mark it was read with, so it reads its own
  text again. `entry_text` shows text read in another mark than the screen's, such as a
  course example or a stated table value written with ".", converted into the locale's
  mark; text the user typed was read in the screen's mark, so it stays as typed.
* **Copying.** Copy, Ctrl+C, "with unit", "full precision" and "fraction" write ".".
  `CopyForm.SHOWN` copies the number as shown; the menu offers it as "Copy 0,3119" only
  where the mark isn't ".". Copy all writes the locale's mark. The status bar quotes
  the copied text, as it did.
* **Words.** `gui/regional.py` sets our languages from `uiLanguages()` in the underscore
  form; Qt lists a script too ("en_Latn_GB"), which `posix_language` drops. It installs
  Qt's `qtbase` translator with the same locale, before the first widget, and `main()`
  deletes it with its windows. Both are read once, so a change applies at the next start.
* **The CLI** chooses its words by `--lang`, then `CADDCALC_LANG`, then `LANGUAGE`,
  `LC_ALL`, `LC_MESSAGES` and `LANG`; "C" or "POSIX" in a list means the source from
  there on, as gettext reads it. Its numbers stay ".", for typing and output alike: its
  output is read by scripts, and §3 has the CLI write "." until it reads the OS's own
  setting. A regional mark for its plain-text output would come with that later step.
* **Tests** run in the source language and with ".": `tests/conftest.py` resets the
  language around every test, since `main()` sets the system's.
* **KI-022 is resolved,** and ADR-0017's F5 with it.
* **The calculator list's tooltip** gives an elided name in bold, escaped (UI/UX's i2
  review).

### 2026-10-18: rebased onto the window layout

* The localization commits, u1 to i4, were rebased onto main's window and page layout
  (ADR-0021) and its later fixes. The British catalog's tooltip test lowers the list's
  least width, which ADR-0021 added, so the names still elide.
* **KI-023 is resolved.** ADR-0021 §7's fixes cover all three shortfalls i2's clipping
  test allowed, so the test now allows nothing: every page fits at the least size, in
  English and en_XA, offscreen and natively.

### 2026-10-18: the reviews' findings on i1 to i4 (i4b)

UI/UX's i4 review and Support & Review's reviews of i1 to i3 found these; they're built
together.

* **One language for the whole window** (UI/UX's M1). Qt's own text, such as a field's
  context menu and a dialog's buttons, is in the language our text is in: the first
  display language we have a catalog for (`i18n.text_language()`), or the source, US
  English. Its Qt catalog is loaded for that language, not for the system's. A German
  user sees an all-English window until we ship a German catalog, never English words
  with German menus. Qt's shortcut names follow: with a German catalog, Copy all's
  tooltip reads "Strg+Umschalt+C", from `QKeySequence.toString(NativeText)` (L3).
* **A comma locale's copy menu names each item by what it copies** (L1): "Copy 0.3119",
  "Copy 0,3119", "Copy 0.3119 in", and the full-precision value. A "." locale's names
  are unchanged.
* **A method's notes give the app's own numbers as values** (L2): `Method.quantities`
  names them, in base units, for the notes' `{name}` fields, as a result's notes already
  do, and they're written in the user's units and mark where shown
  (`formatting.method_notes`). The cone's note gives the course example's angles so. The
  string sweep, a test, finds every number typed into the calculators' prose, and each is
  quoted from a source, which stays as published (§4).
* **A decimal bound in a comma locale** reads in its mark in a field's message, through
  the window as well as in core.
* **The catalog check** (S&R's i1 L1) refuses a marked text with a positional `{}` or a
  printf-style `%s` or `%(name)s`, which a translation can't reorder and the check
  couldn't see, and checks a plural's forms one by one: the first may leave out the
  count, as "one inch" does, where the language has more than one form. The
  pseudo-locale keeps printf placeholders as they are too (S&R's i2 L1).
* **The chosen languages are one value, replaced whole** (S&R's i1 L2), and the catalogs
  are cached by it: a lookup begun before a `use()` caches under the old choice, and
  can't answer for the new one. A test runs that race.
* **Language tags** (S&R's i1 L4 and L5): a script is kept only where it isn't the
  language's usual one, from CLDR's likely subtags, so `zh-Hant-TW` reads `zh_Hant_TW`
  and then `zh_Hant`, never Simplified Chinese, and `sr@latin` reads `sr_Latn`; `en-Latn-GB`
  is still `en_GB`. `C`, `POSIX` and private-use tags, such as `x-pseudo`, name no
  language, so the source.
* **Nothing is translated at import time,** a test checks: no translation call at a
  module's or a class's level, in a decorator or a default (S&R's i1).
* **"per cent" reads however its words are spaced** (S&R's i3 L2): a run of spaces of any
  kind, a no-break space among them, reads as one space.
* **The translator comes out in `main()`'s `finally`,** with the font, however it ends.
* **Tests' tooltips** are shown at once natively: the test turns off Qt's tooltip
  animation, which kept it from being visible yet.
* **Moot:** S&R's i2 L2, the clipping test's broad third allowance, went with the
  allowance (KI-023). S&R's i3 L1, the plural rule of the first catalog rather than the
  message's, waits for the next language with its own rule.

### 2026-10-18: the catalogs in every build (i5)

* **The frozen build** compiles our catalogs before Nuitka reads the package data, and
  includes PySide6's `qtbase_*.qm`, and nothing else of Qt's translations, in
  `PySide6/translations/`, where its Qt looks. It fails for a missing one, and its smoke
  test checks the built app finds our catalogs and that Qt loads its own from the build
  (ADR-0009's checklist).
* **The wheel** compiles them in hatchling's build hook (`hatch_build.py`), so a wheel
  built from a checkout or the sdist carries them; Babel is a build requirement.
* **`scripts/i18n.py compile`** writes them into the source tree, for an editable install
  and the frozen build; they stay git-ignored. `core.i18n.shipped_languages()` lists the
  languages a folder has compiled catalogs for.
