# ADR-0019: A units registry, the one source of unit knowledge

* **Status:** **Accepted** (not built). The maintainer asked for this ADR on 2026-10-17
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
* `core/units.py`: the `Dimension` enum, `_WITH_ARTICLE`, the `UNITS` tuple (float
  factors, one of them `180/π`), `BASE_UNITS`, the alias lookup, and a parser whose unit
  token is a hand-written character class (`[A-Za-z°%"'″′]+`).
* `core/formatting.py`: `_SHOWN_IN`, `_STRESS_WITH_LENGTH`, `display_unit`'s per-dimension
  branches, `_decimals`'s branches, `DisplayPrefs`' per-dimension decimal fields, the
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
