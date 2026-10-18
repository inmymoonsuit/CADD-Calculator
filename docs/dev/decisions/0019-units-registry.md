# ADR-0019: A units registry, the one source of unit knowledge

* **Status:** **Accepted**; the behaviour-neutral refactor (§7's first step) is built, as
  u1 and u1b, U5's spellings as i3, §7's area and fixed-unit outputs as u2, and its compound
  forms as u3 (see Amendments). The maintainer asked for this ADR
  on 2026-10-17
  ("create a registry of units in our codebase (maybe even a subsystem for units and
  conversions) with definitions and attributes and the ability to add new ones"), decided
  U4 and U5 that day, and approved U1–U3 as recommended on 2026-10-18 ("Approve all"),
  after the Engine's, UI/UX's and Support & Review's reviews.
* **Builds on:** ADR-0005 (units, precision, display), ADR-0013 §9 (numeric intent),
  ADR-0014 (cited reference data), ADR-0006 (plugins), ADR-0017 (result fields),
  ADR-0018 (Geometry and Conversions)
* **Prior art:** the maintainer's Parametric CADD project, whose units style guide makes
  its units subsystem "the controlling reference … no other subsystem defines competing
  tables". Its conventions are adopted here where they apply; no code is copied.

## Context

Unit knowledge is spread across the code today:
* `core/units.py`: the `Dimension` enum, an article table, the `UNITS` tuple (float
  factors, one of them `180/π`), `BASE_UNITS`, the alias lookup, and a parser whose unit
  token is a hand-written character class (`[A-Za-z°%"'″′]+`).
* `core/formatting.py`: the display-unit tables, `display_unit`'s per-dimension branches,
  the per-dimension decimals branches, `DisplayPrefs`' per-dimension decimal fields, the
  close-up rule for "°", and inch-only fractions.
* Planned work would add more: `Unit.spoken_plural` (ADR-0017), and for ADR-0018 an AREA
  dimension touching six places plus the parser, fixed-unit outputs, significant figures,
  degrees-minutes-seconds, and feet-and-inches.

Every new unit or dimension means editing several tables that must agree, which is how
drift and hand-crafted special cases creep in.

## Decision

### 1. One units subsystem

`caddcalc.core.units` becomes a package, still standard library only, that owns all unit
knowledge: dimensions, units, unit systems, conversion, parsing, and the unit facts
display needs (which unit to show, spacing, fractions, compound forms). Everything else
asks it. `core.formatting` keeps number formatting, but no unit tables.

### 2. Declarations, not scattered tables

* **A dimension** declares its key, name, article, base unit, display rule, default
  precision, and, where it's used, a derivation (AREA = LENGTH²), so squares can be
  generated rather than hand-entered. STRESS keeps declared units from their exact
  definitions (psi from the exact pound-force and inch); there's no FORCE dimension to
  derive it from.
* **A unit** declares:
  * its key symbol (public in JSON: "mm", "deg", "MPa"), the symbol it's written with
    ("°" for "deg"), singular and plural names (shown and spoken), and aliases. Names are
    marked for translation with `N_()` and translated where they're shown (ADR-0020),
    never at registration.
  * dimension, and its factor to the base unit as an **exact** value (below)
  * system: SI; accepted for use with the SI (the degree, minute and second, SP 811
    Table 6); US customary; or none (the percent, a plain ratio)
  * how it's written after a number: spaced ("25 mm", and "0.25 %", SP 811 §7.10.2), or
    close up, which is only for °, ′ and ″ ("90°", "6'-8\""; SP 811 §7.2)
  * capabilities: inch fractions, a compound form
  * its citation: NIST SP 811 table and locator
* **Exactness.** Every factor is stored as its exact definition, a rational where one
  exists (a decimal string read as a `Fraction`, "25.4"). The radian's is 180/π, exact
  only symbolically, stored as a high-precision decimal. Each is rounded once to the
  nearest double. Computation stays in doubles (ADR-0013 §9.4): the exact value is for
  storage, checks, generated squares and the converters' exact path (3/16 in → 4.7625 mm),
  not for arithmetic at run time. Two values become correctly rounded, and the change is
  recorded: psi (one unit in the last place) and ft² (92 903.04 mm², where `304.8**2` is
  one unit in the last place off).
* **Generated units:** squares (in², mm²) come from their length unit in exact
  arithmetic, with the aliases people type ("in^2", "in2", "sq in", "square inches").
  Those are input aliases only: display always writes in² and mm² (SP 811 §6.1.8).
* **Display rules are data.** For each dimension: the unit shown for each length choice
  (LENGTH follows it, AREA is its square, STRESS gives ksi with inch-pound and MPa with
  metric, ANGLE is always degrees), and default precision (decimals or significant
  figures). `DisplayPrefs` keeps its existing fields as the user's choices, and a new
  `decimals_for(dimension)` falls back to the registry's default where it has none (AREA,
  converter rows).
* **Compound forms** are registered per dimension, each with a parser and three
  formatters (display, copy, spoken): degrees-minutes-seconds for ANGLE, and
  feet-and-inches for LENGTH (U3). Spoken forms read "1 foot 4 and 3 sixteenths inches"
  and "40 degrees 30 minutes 15 seconds", not the symbols. Rounding carries: 1'-11 63/64" at
  1/16 shows 2'-0", never 1'-12"; at one decimal of seconds, 40°30′59.95″ shows
  40°31′0.0″.

### 3. A derived parser

The parser matches the longest registered alias that ends the text, then reads the rest
as the number, so aliases with spaces ("sq in", "square inches") need no tokenizer, and
"3mm" can never read as metres. A new unit parses as soon as it's registered, including
"in²" and "sq ft".
* Aliases are unique within a dimension, and the parser always knows the dimension it
  expects, so ′ and ″ can be the foot and inch for LENGTH and the minute and second for
  ANGLE (SP 811 Table 6). Compound forms are tried first, and only for their own
  dimension.
* Matching stays case-insensitive, as today ("MPA", "IN" work). Registration refuses an
  alias whose case-fold collides with another, unless both declare themselves
  case-sensitive (a future Mm against mm).
* Registration refuses parser-unsafe aliases: empty, starting with a digit, sign, "/" or
  ".", "e" or "E", or surrounding whitespace.
* Every form that parses today keeps parsing, checked by an identity test over a corpus
  that includes every Param default and every gauge and material stated text.

### 4. Declarations in code, with citations (U1)

The built-in dimensions and units are Python declarations in `core/units/builtin.py`.
Each unit carries a `Reference` to NIST SP 811 (table and locator). A test checks that
every unit cites a source, has an exact factor, and that derived factors equal their
definitions. The registry is built once, lazily, frozen, and cached with an explicit clear
for tests (guideline 4). It must be complete before the calculator registry parses Param
defaults, and nothing parses units at import time.

Units are *not* loaded through ADR-0014's reference-data layer: that layer itself parses
values with units, so loading units through it would be circular and need a bootstrap
special case. Unit factors are definitions rather than measured values, so its value model
(basis, trust level) doesn't fit them either.

* **One citation model.** `Publication`, `Source`, `License`, `PublicationKind`, the
  licence check and the host allowlist move from `core/refdata.py` to a small
  `core.citations` module that both the units and refdata import. There's one citation
  model and no import cycle.
* **The SP 811 record:** kind `government_document`; licence `public_domain`, on the basis
  "17 U.S.C. §105: a work of NIST employees (NIST Technical Series); not Standard
  Reference Data under 15 U.S.C. §290e"; a nist.gov url; edition "2008 Edition (web
  version 3.2, July 2008)", noting that it predates the 2019 SI, which changes none of
  these definitions. The inch and the pound also cite their primary source, the *Federal
  Register* Vol. 24, No. 128, p. 5348 (July 1, 1959).
* ADR-0014's §5 checklist is applied to SP 811 item by item and recorded with the ADR.

### 5. Extensible, with guards (U2)

* Plugins may add **units** to existing dimensions, through an entry-point group
  (`caddcalc.units`) or `register_unit`.
* Every registration is validated:
  * symbols and aliases unique, case rules included
  * parser-safe
  * an exact factor
  * names and plural present
  * a system
  * a citation
* The registry is frozen before first use, like the calculator registry.
* A plugin unit's citation is its own claim, shown as given. ADR-0014's §5 checklist
  gates only what this project ships.
* If a later core release adds a unit that takes a plugin's symbol, that plugin's
  registration fails loudly, with an error naming both.
* **Dimensions stay a closed set in core.** Adding one, such as AREA or VOLUME, is a
  reviewed core change, because calculators, display rules and tests depend on the set.

### 6. Conventions (from the Parametric CADD units standard)

* Unit symbols keep their SI case: lower case, except units named after people (Pa, N)
  and the prefixes M and G (MPa, GPa) (SP 811 §§6.1.2, 6.2.2). Matching stays
  case-insensitive.
* Symbols are never pluralized: "25 mm" (SP 811 §6.1.3).
* Number, space, symbol in formal output (SP 811 §7.2), except °, ′ and ″, which are
  written close up. The percent sign is spaced (§7.10.2).
* `"` and `'` are accepted inch and foot aliases. They're customary marks, not SI symbols.
* An exact value is never rounded into storage. Display precision is presentation only
  (already ADR-0013 §9).

### 7. Migration

* **First, a behaviour-neutral refactor:** every existing public name kept (`Dimension`,
  `Unit`, `get_unit`, `units_for`, `to_base`, `from_base`, `parse_quantity*`,
  `TypedValue`, `BASE_UNITS`), every existing test passing untouched, and an identity test
  over every parse and format.
* **Then additions as data:** AREA and its units, DMS, feet-and-inches, and significant
  figures for converter rows (ADR-0018). The Output presentation (ADR-0018 m2) asks the
  registry for its fixed unit.

## Decisions

All five were decided by the maintainer as recommended (U4 and U5 on 2026-10-17, U1–U3 on
2026-10-18). The alternatives are kept for the record.

| | Question | Decided | Alternatives |
|---|---|---|---|
| U1 | Where the built-in units live | **Python declarations, each citing NIST SP 811.** Industry practice is mixed: libraries meant for end users to extend at run time keep units in a definitions file (Pint, GNU units), while typed libraries keep them in code (Indriya, the Java units reference implementation; Boost.Units), and UnitsNet generates code from JSON. Ours is a small, typed, rarely changing set in a standard-library core, and a data file loaded through the reference-data layer would be circular, since that layer reads units itself. A built-in unit is one reviewed declaration; plugins add units without touching core. | A TOML file with its own small loader (more machinery for definitions that rarely change) |
| U2 | What plugins may add | Units, through `caddcalc.units`, validated; a bad plugin unit is skipped with an error, never stops startup; built-ins always win; dimensions stay core-only | Units and dimensions both open; or nothing open |
| U3 | Feet and inches | Survey (2026-10-17): consumer calculators write `4′ 3 7/8″` (Inch Calculator) or `26 ft 9 1/8 in` (CalculatorSoup). Drafting texts write the dash form: *Engineering Drawing and Design* (5th ed.) writes `3'-10 11/16"`. AutoCAD has two forms: its "report" form, shown by default, uses spaces (`1'-5 1/2"`), and its "input" form has none (`1'5-1/2"`), because "you cannot include spaces when entering measured values" (AutoCAD help, the UNITMODE system variable; AutoLISP help, "About String Conversions"). NCS 4.0 hyphenates the fraction (`5'-2-1/16"`), but its licence makes it cite-only, so it isn't credited. This is house style, not reference data. Our users are drafters, so: **display** in AutoCAD's report form, `1'-4 3/16"`; **copy** in its input form, `1'4-3/16"`. Inch fractions follow the same rule (shown `1 3/16"`, copied `1-3/16"`). Add the row to the Length converter (UI/UX's M6). **Input accepts all the common forms**: `1'-4 3/16"`, `1'-4-3/16"`, `1'4-3/16"`, `1' 4 3/16"`, `1′ 4 3/16″`, and `1 ft 4 3/16 in`. | Hyphenated for display too (`1'-4-3/16"`, NCS's style); or a consumer form (`1′ 4 3/16″`) |
| U4 | Order of work | **Decided by the maintainer: the registry is built before the conversion calculators.** The result fields continue in parallel. | — |
| U5 | Spelling of unit names shown and spoken | **Decided by the maintainer: it follows the user's language settings, through localization (ADR-0020).** Unit names are written once in the source language and translated per locale ("millimeter" in en-US, "millimetre" in en-GB). Every spelling stays accepted as input in every locale. | — |

## Consequences

* Adding a unit is one cited data entry; adding a dimension is one reviewed core change.
* Display, parsing, spoken names and converters all come from the same declarations, so
  they can't disagree.
* The registry refactor comes before ADR-0018's new families, which delays them by one
  core step but avoids rework.

## Amendments

### 2026-10-18: the refactor as built (u1, u1b)

* **The package:** `core/units/` holds `model.py` (Dimension, Unit, DimensionSpec,
  UnitSystem), `builtin.py` (the declarations), `unit_registry.py` (the registry), and
  `parsing.py` (the parser and TypedValue). The registry module isn't called
  `registry.py`, which would clash with `core/registry.py` and with the package's own
  `registry()` function. Entry-point loading moved to `core/plugins.py`, which both
  registries use, so there's no import cycle.
* **Citations** moved to `core/citations.py`, as §4 says. psi and ksi cite SP 811
  Appendix B.8's pound (footnote 22), pound-force (footnote 23) and standard free fall,
  and ksi also the kip; B.8's own psi and ksi factors are rounded. The 1959 notice is cited
  as 24 FR 5348 (July 1, 1959), on govinfo.gov, so it's on the public-domain allowlist.
  The §5 record is `docs/dev/research/release-checklist-units-v1.md`.
* **Neutral, as checked:** an identity test against a frozen copy of the old module, and
  Support & Review's independent diff of the real old and new code over 411,844 results.
  Only psi's factor changed, by one unit in the last place, as §2 says.
* **A name shared across dimensions (Support & Review's u1 M1).** §3 lets two units of
  different dimensions share a name, so a name alone can be ambiguous. Two rules keep a
  plugin from making a built-in's name ambiguous:
  * A plugin unit may not take any built-in's name, case-folded, in any dimension;
    built-ins may still share one with each other, as the foot and the arcminute will.
  * `get_unit(name, dimension)` prefers a unit of `dimension`, and falls back to
    whatever dimension has the name, so its caller can say a value measures the wrong
    thing. Every core caller that knows the dimension gives it: the length preference,
    a parse's default unit, a stated value (`nominal(..., dimension=)`), and a step's
    expression unit. With no dimension and two units of the name, it raises UsageError.
* **Guards beyond §5's list:** an empty alias is refused, and so is any name starting with
  "e" or "E", which is broader than the exponent clash it prevents, but harmless today.

### 2026-10-18: unit names and spellings (U5, built in ADR-0020's i3)

* **Names are US English,** the source language: "millimeter", "meter", "centimeter",
  where u1 kept the old module's "millimetre". Each unit declares its singular and plural
  as one pair, `NP_("unit", "millimeter", "millimeters")`, so a language with more plural
  forms than two can give them all. `Unit.spoken(shown)` translates the pair where it's
  shown, choosing the form by the number's plural category (ADR-0020 §5). The name of a
  unitless ratio isn't spoken, so it isn't marked.
* **The British forms come from the catalog,** from CLDR 47's en_001 unit names:
  "millimetre", "centimetre", "metre", and "per cent". CLDR's en_CA writes "percent", so
  a one-entry en_CA catalog says so; it reads en_001 for the rest.
* **Every spelling reads in every locale.** The British singulars "millimetre",
  "centimetre" and "metre", which u1 didn't accept, are aliases now, and so is "per cent",
  which the parser takes as one name though it has a space. They're built-in names, so a
  plugin can't take one, in any case or dimension. The identity test holds these four to
  their units, since the old module refused them, and holds every other text to what it
  read before.

### 2026-10-18: the area, and outputs in a fixed unit, as built (u2)

* **`Dimension.AREA`**, base mm², declared as a power of the length
  (`DimensionSpec.derivation`, `Derivation(LENGTH, 2)`). It's last in the enum, so the
  old dimensions keep their order, and messages that list the base units end in "mm²".
* **The squares are generated** in `builtin.py` from their length units: mm², cm², m²,
  in² and ft², each with its root's exact factor squared, as a `Fraction`, so ft² is
  92 903.04 mm² exactly (`304.8**2` is 92 903.040 000 000 01). A unit declares its root
  with `Unit.power_of`, and the registry refuses a square whose factor isn't its root's
  exact factor to the dimension's power, or whose root isn't a registered unit of the
  dimension it's a power of. A plugin may add a square the same way.
* **Key symbols are SP 811's symbols,** "mm²" and "in²", as "MPa" is: they're what JSON
  writes. The typed forms are aliases, read but never written (SP 811 §6.1.8): "in^2",
  "in2", "sq in", and the names, in US and British spelling.
* **Display follows the length choice:** an area shows in the square of the chosen
  length unit (`follows_length` with a derivation), or in mm² for a plugin's length with
  no square declared. Areas never show an inch fraction, and they take the registry's 4
  decimals, as `decimals_for` already allowed for a dimension without a preference.
* **Citations:** the metric squares cite SP 811's Table 2 (area, the square meter) and
  their prefix in Table 5; in² and ft² cite Appendix B.8's square inch and square foot,
  and 24 FR 5348 with their root. They're the two works the units' checklist record
  already passes; the new locators are listed there for review.
* **Names** are `NP_("unit", "square inch", "square inches")` pairs; the British catalog
  writes "square millimetre", "square centimetre" and "square metre", and en_CA reads it.
* **An output may fix its unit:** `Output.unit` names a key symbol, checked when the
  calculator is registered (`validate_spec`), and every front end shows the output in it
  through `formatting.output_parts`, `format_output` and `copy_output`. Its precision is
  the registry's for that unit (`UnitRegistry.precision_for`), whatever the preferences:
  each dimension declares one, `DimensionSpec.fixed`, six significant figures for all of
  them so far. `core.units.Precision` holds decimal places or significant figures, and
  `formatting.format_significant` writes the latter as plain decimals with their zeros,
  carrying into a new place without gaining a figure (9.999997 is "10.0000" to six). A
  fixed inch row still shows the inch fraction when it's preferred.
* **The identity test** now runs over the old dimensions and units. Two texts it held as
  refused, "3 m2" and "3 sq in", name a square now: each reads as that area, and
  elsewhere is refused for being an area. Every other text reads exactly as before.

### 2026-10-18: compound forms, as built (u3)

* **`core/units/compound.py`** holds `CompoundForm`, which reads a text written in it
  and writes a value as a `CompoundText`: shown, copied and spoken. The registry holds
  the built-in forms by key, `ft_in` and `dms`, and the parser tries a dimension's forms
  before its units, and only that dimension's. An output names one with `Output.form`
  (never with a unit as well), and the result fields, Copy, Copy all, the document and
  the CLI show it through `formatting.output_parts` with no code of their own.
  `parse_number` moved to `core/units/numbers.py`, which the forms and the parser both
  read, so the registry and the parser don't import each other; `units.parsing` still
  exports it.
* **The minute and second of arc** are units of the angle, `arcmin` and `arcsec`,
  written ′ and ″ close up, with `'` and `"` as aliases too (SP 811 Table 6, §7.2). They
  share those marks with the foot and inch, as §3 allows: in an angle, `30′` is 30
  minutes, and everywhere else ′ and ″ stay the foot and inch. Angles still show in
  degrees.
* **Feet and inches** (U3): shown in AutoCAD's report form, `1'-4 3/16"`, and copied in
  its input form, `1'4-3/16"`. Both always give the feet and the inches, as `0'-4"` and
  `2'-0"`, so a row reads the same whatever its value. The value is rounded once, to the
  nearest 1/16 inch by default (a power of two to 1/64, or whole inches), so it carries:
  1'-11 63/64" is 2'-0". Spoken: "1 foot 4 and 3 sixteenths inches", "1 foot 4 inches",
  and "1 foot 3 sixteenths of an inch". Input takes every form U3 lists, with whole
  feet, inches under 12 with their mark, and one sign at the front. A full-precision
  copy gives the inches.
* **Degrees, minutes and seconds:** shown `40°30′15.00″`, to hundredths of a second by
  default, rounded once so it carries (29.99999999° is 30°0′0.00″), with one sign before
  the degrees (−0.5° is -0°30′0.00″, in ASCII "-") and never a negative zero. It's copied
  as AutoCAD takes an angle in degrees, minutes and seconds, `40d30'15.00"`, with "." for
  the point, which U3's rule implies: CAD's input form. Input takes ° or `d`, ′ or `'`,
  ″ or `"`, and the units' words, two or three parts in order, whole degrees and
  minutes, minutes and seconds in [0, 60), and one sign. Spoken: "40 degrees 30 minutes
  15.00 seconds".
* **Marked for translation:** the spoken templates, one per sentence, with named fields,
  and the fractions' words, `NP_("fraction", "sixteenth", "sixteenths")`; the minute
  and second's names. The new messages for a form that doesn't fit are plain text, as
  the parser's other messages are, until the string sweep (ADR-0020 §6).
* **Copy all** keeps a compound value, which isn't a number, from being read as a
  formula, as it does a text cell, so `-1'-4"` pastes as text.
* **The identity test:** besides u2's area texts, two kinds of text the old module
  refused read now, each held to its new reading: an angle ending in ′, ″, `'` or `"`,
  refused before as a length, reads as minutes or seconds; and `1'4"` is 1 foot 4
  inches, or in an angle 1 minute 4 seconds. Every other text reads as before.

### 2026-10-18: the reviews' findings on u2 and u3 (u3b)

UI/UX & Design's and Support & Review's reviews of u2 and u3 passed both slices, with
these fixes. The project manager relayed the maintainer's approval of the five choices
u3 made, as built: the DMS copy form `40d30'15.00"`, both parts of feet and inches always
shown, inches of 12 or more refused, the precisions (1/16 inch, hundredths of a second,
six significant figures), and the new messages left unmarked until the sweep.

* **Feet and inches sit flush right** (UI/UX's M1). Decimal alignment padded them as if
  they had decimals, 31 px short of the value column's edge. A compound value with no
  decimal point isn't padded; DMS still aligns on its seconds' point.
* **Areas show six significant figures** (UI/UX's L1): `6451.60 mm²`, `10.0000 in²`,
  `0.00645160 m²`, not 4 decimals. A dimension now declares a `Precision`, not a count of
  decimals (`DimensionSpec.precision`), and `DisplayPrefs.precision_for` gives the user's
  decimals or that; `decimals_for` refuses a dimension shown to significant figures.
* **A zero part isn't spoken** (UI/UX's L2): "4 inches", "2 feet", "1 degree 1 minute",
  and "0 inches" or "0 degrees" for zero. Each part is a measure, `{number} {unit}`, and
  measures are said together by one translatable pattern, `{first} {second}`, as CLDR's
  unit list pattern joins them, so a language can order or join them its own way.
* **A negative is spoken "minus"** (UI/UX's L3), by one template, `minus {value}`:
  "minus 1 foot 4 and 3 sixteenths inches", "minus 30 minutes".
* **A lookup with no dimension takes a length** (S&R's L1). `get_unit`, `to_base` and
  `from_base` are public, and with no dimension `'`, `"`, `′` and `″` gave the foot or the
  inch before u3; u3 made them raise UsageError, since the minute and second share them.
  With no dimension given, a length now wins, so they read as before. A name two units
  share with no length among them still needs its dimension (u1's amendment).
* **`format_significant`'s docstring** says it rounds the exact binary value, so 123.4575,
  a little under that in binary, is `123.457` to six; a test holds it (S&R).
* **The input grammar isn't loosened** (the maintainer, through the PM): the inch mark
  stays required, so `5'9` and `5'9-1/2` are refused. Typed arithmetic may come later,
  where a bare hyphen would read as subtraction, and the grammar will be settled in its
  own decision first.
