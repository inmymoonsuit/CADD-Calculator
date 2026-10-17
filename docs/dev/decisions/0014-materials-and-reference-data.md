# ADR-0014: Materials and reference data for sheet metal (ADR-0013 phase 2)

* **Status:** **Accepted**; **phase 2a built** (gauge systems, 2026-10-17), phase 2b not
  started. The design as built is in the [Amendments](#amendments), which refine §1,
  §2, and §5. The maintainer approved M1–M7 as
  recommended on 2026-10-17. This ADR supersedes parts of ADR-0013: decision A's "P
  derived from material" (M3), decision E for K and P (M2), and §11's phase-2 list (see
  Consequences).
* **Date:** 2026-10-17. Revised 2026-10-17 as built (structured result notes, and
  `Reference.scope` planned for phase 2); the decisions are unchanged.
* **Builds on:** ADR-0013 (domains and shared settings; §9 numeric intent, §11 phase 2,
  decisions A and E), ADR-0004 (provenance and verification), ADR-0005 (units, precision,
  and display rounding), ADR-0008 (licensing), ADR-0009 (packaging)
* **Research:** [materials-data-sources.md](../research/materials-data-sources.md) (Support &
  Review session, 2026-10-17), with full citations and its legal framing
* **Not legal advice.** The legal points below summarize research for planning. The
  project has no budget for a legal review, so the design stays inside what needs no
  legal judgment (§5, M7).

## Context

ADR-0013 reserved phase 2 for materials. A user picks a material and a gauge on the Sheet
Metal page, and the calculators use values that follow from that choice. Every shipped
value must carry a citation and a trust level (ADR-0004), and we may only ship what we
are allowed to redistribute (ADR-0008).

The research changed what phase 2 can promise.

1. **Gauge tables can be computed, not copied.**
   * The 1893 gauge statute (15 U.S.C. §206) is public domain. Its weights, divided by a
     steel density basis, give Manufacturers' Standard Gauge: 12 ga = 4.375 ÷ 41.82 =
     0.1046 in.
   * **The density basis is a choice, and we disclose it.** 41.82 lb/ft² per inch comes
     from MH29 (a cite-only fact); its AISI origin is unconfirmed. NBS Circular 391 uses
     40.80 instead. We use 41.82 because it reproduces MH29 Table 2. During research it
     also matched one vendor's galvanized 18 ga; that is reasoning only, and the vendor
     value never ships or appears in tests (§5.2). Each gauge system records its own
     basis and source.
   * NBS Circular 391 (public domain) adds the galvanized rule (+2.5 oz/ft²) and the AWG
     formula.
   * Spot checks match:
     * MH29 Table 2 at 12, 14, 16, 20, and 24 ga (Manufacturers' Standard), and at 16,
       20, and 22 ga (galvanized)
     * TO 1-1A-9 Table A-19 at a single value (20 ga). Its column is labelled "USSG
       (Revised)" but lists Manufacturers' Standard values, which is a naming trap.
2. **Commercial material data can't be redistributed.**
   * Every distributor, mill, CAD vendor (including bundled sample gauge tables), and job
     shop whose terms we could read restricts commercial reuse. Our Apache-2.0 license
     allows commercial use.
   * Several sites' terms couldn't be read. A few, such as Novelis, allow non-commercial
     reuse only, which doesn't fit Apache-2.0.
   * ASTM, the Aluminum Association, Machinery's Handbook, and The Fabricator are
     cite-only.
3. **US government handbooks are usable, but they describe aerospace bench practice.**
   * FAA AC 43.13-1B and FAA-H-8083-31B give minimum bend radius for aluminum.
   * USAF TO 1-1A-9 gives 2T for 1020/1025 steel, a conservative stand-in for mild
     cold-rolled steel, and values for 304.
   * MIL-HDBK-5J gives strengths, including A-basis (statistical) allowables. It was
     cancelled in 2003 and superseded by MMPDS, which is copyrighted and which we don't
     use.
   * Some disagree: 6061-T6 at 0.064 in is about 1–2T in AC 43.13 and about 2.5T in 31B.
     The 31B reading is pending a visual check of which column belongs to which alloy.
     Its chart also credits a Raytheon manual (a third-party origin), so warnings use
     AC 43.13.
4. **K-factor and the air-bend ratio P are not material properties.** They depend on the
   process (air bending, bottoming, coining), the tooling, the R/T ratio, the grain
   direction, and the material lot.
   * No source gives K per material. Sources we can cite imply starting values of about
     0.35 to 0.45: the FAA bend-allowance formula about 0.447, MH29 Eqs 32–34 about
     0.35–0.45, and EDD 0.4. The neutral axis approaches mid-thickness (K → 0.5) as R/T
     grows. Trade articles and a job-shop guide describe the same dependence on R/T and
     process (research §4; their figures aren't reproduced).
   * Published P varies widely between articles, even for the same aluminum alloy, and
     one fabricator's online calculator implies a ratio above all of them (research §5;
     figures not reproduced).
   * **Strength scaling doesn't predict P for aluminum.** A strength-scaling rule
     described in *The Fabricator* predicts a lower P for softer aluminum, but the same
     series publishes a higher figure for an annealed temper than for harder ones. For
     steels the result would also depend on whether a minimum or a typical strength is
     used. We saw the rule only in search summaries, and the publication's terms
     couldn't be read (§5.2).
5. **The legal position is an original compilation.**
   * **Copyright:** facts aren't copyrightable in the US (*Feist v. Rural*, 1991).
     Expert judgments, such as "recommended" radii or valuations, carry more risk
     (*CCC v. Maclean Hunter*, 2d Cir. 1994).
   * **Contract is the main practical barrier.** Website terms and standards licenses
     bind whatever copyright says (*ProCD v. Zeidenberg*, 7th Cir. 1996). That is why
     we don't take vendor values seen under their terms.
   * **EU database right:** it protects databases from qualifying (EU or EEA) makers. It
     bars extracting a substantial part, and also repeated, systematic extraction of
     insubstantial parts. The UK has an equivalent right.
   * **The safe approach:**
     * our own small selection and our own schema
     * public-domain or computed values
     * at most isolated cite-only facts
     * a citation on every value (attribution only; it grants no permission)
   * **Fair use is not our basis.**
     * Fair use (17 U.S.C. §107) is a US defense, weighed case by case. It is decided
       only if someone challenges a use, ultimately by a court, and even a winning
       defense costs money this project doesn't have.
     * It doesn't reliably override website terms; whether copyright law pre-empts such
       contracts is contested.
     * The EU has no general fair use. Its exceptions to the database right, such as
       illustration for teaching, are narrow and non-commercial.
     * Our educational purpose doesn't carry to downstream users, because Apache-2.0
       lets anyone reuse our files commercially, and fair use is judged per use.

     So we ship only what needs no defense (§5).
6. **A terminology trap.** In the FAA handbooks, "K" means the setback factor tan(θ/2),
   not the neutral-axis K-factor.

## Decision

### 1. A reference-data layer: built-in, versioned, cited

* **Format.** Reference data ships as TOML files inside the package, read with `tomllib`
  through `importlib.resources` (both standard library). Domain-specific tables live
  with their domain, e.g. `calculators/sheet_metal/data/gauges.toml` and
  `materials.toml`. Each file declares its sources once (title, edition, locator, URL,
  date accessed, license, and a third-party flag) and its values refer to them by id.
  The license field has no "vendor" value, so vendor data can't even be expressed.
* **Packaging.** A test loads every table through `importlib.resources`. Frozen builds
  (ADR-0009) must include the data files, so this goes on the packaging checklist, and
  the frozen build's smoke report counts the tables it loaded; a missing table would
  otherwise only show up in the shipped app.
* **Machinery in core.** Generic, standard-library code in `core` provides
  `ReferenceTable` (with a name and version) and `ReferenceValue`. A `ReferenceValue`
  holds:
  * a value in base units, plus the stated `TypedValue` (ADR-0013 §9) when the source
    states the value literally. A computed value such as 4.375 ÷ 41.82 has no typed
    text of its own, and inventing text from a float would break `TypedValue`'s
    self-consistency rule. A min/typical/max range is three such values.
  * a thickness band with inclusivity, following `Param`'s min/max pattern, looked up by
    band and **never interpolated across sources**. Band edges are in base units, and
    bands in one table don't overlap.
  * conditions: temper, finish, bend axis relative to the rolling direction, bend angle,
    process, and tooling
  * its basis: specification minimum, typical, A-basis, or rule of thumb
  * a `Reference` and the date accessed. `Reference` today has only a title, detail, and
    URL, so it gains optional structured fields: edition, locator (table, figure, or
    page), date accessed, and **scope**, the practice a source describes, e.g.
    "aerospace bench practice". Only the data-table validator requires them, and it
    requires a scope on any source a check uses; existing references and `to_dict` keep
    working. `describe_note` shows a reference's scope, so a note says how far its
    source applies.
  * its license: public domain, cite-only fact, or our own measurement
  * its trust level: verified derivation, handbook rule, specification guidance, or rule
    of thumb. This is a separate type from `Verification`, which rates *methods*
    (ADR-0004), and it gets a distinct name.
* **New dimension.** Strength needs a stress `Dimension` (ksi, MPa). Adding a dimension
  touches several unit tables, so a test checks that every dimension is covered by all
  of them.
* **Tests enforce what can be checked mechanically.**
  * Every source id resolves, and every source has a title, locator, access date, and
    known license; books also need an edition.
  * K and P are marked no higher than "rule of thumb".
  * Bands don't overlap.
  * §5.1's "not drawn substantially from one cite-only source" gets a mechanical stand-in:
    per table, at most N values whose only source is cite-only. The maintainer sets N
    when 2b's data is written; 2a's only cite-only value is the 41.82 basis.
  * Spot checks use isolated cited values as test data (§2).
  * What can't be automated stays on the human checklist: §5.2's terms, §5.3's embedded
    content beyond the third-party flag, and §5.6's re-checks. The fields make them
    reviewable.
* **Provenance.** A value that comes from a table reaches results as the **derived**
  source of ADR-0013, with `InputSource.reference` naming the table and its version, e.g.
  "12 ga, Manufacturers' Standard (nominal); Gauge systems, version 1". The per-entry
  citation (the statute and the MH29 basis) stays reachable through the table entry.
* **Derived values, added without breaking ADR-0013's surface.**
  * `DomainValues` carries one label for all its values, but derived values each need
    their own source. It gains a `derived` mapping (each value with its `InputSource`),
    empty by default; `values` keeps its one domain label.
  * Precedence is explicit, then domain values, then derived, then the default.
  * `DomainSettings` gains `set_choice()` and `clear_choice()`, and resolves choices
    through the domain's tables into `derived`.
  * `run()`'s signature doesn't change.
* **Structured result notes.** The GUI needs to style "no applicable value" apart from
  "radius too small", and tests need to assert which one appeared, so results carry
  structured notes. They landed in phase 1's close-out (ADR-0013 slice 7), before that
  surface was released:
  * `Result.notes` holds `Note`s (`core.notes`), each with a `NoteKind`, its text, its
    `references` (every source, when sources disagree, M4), and its `subjects`, the
    parameter or output keys it concerns.
  * The kinds are `warning` (something to check, such as a rule of thumb),
    `limit_exceeded` (past a limit a cited source states), `no_applicable_value` (no
    source covers the case), and `infeasible` (the inputs describe something that
    can't be made; the numbers are still shown).
  * A `limit_exceeded` note must cite at least one reference, so "limit" always means a
    cited limit. The minimum-radius checks below are the first to make them.
* **Formulas.** Gauge derivations (weight ÷ density basis, the coating rule, the AWG
  formula) run through `core.expr`, so they show their work and are tested like
  calculator steps (AGENTS rule 3).
* **No user files.** Under the session-only model there are no user or shop tables.
  Reading a shop table in, even read-only, would be a separate decision.

### 2. Phase 2a: gauge systems

* **Four named systems,** each stored as its *definition*, not a copied table:
  * Manufacturers' Standard (steel): the statute weights and the density basis
  * Galvanized: the statute weights plus the coating rule
  * US Standard 1893, labelled "as commonly used for stainless": the statute's
    approximate column. Vendor listings differ from this column at some gauges (14 ga,
    for example; vendor figures aren't reproduced), and A480 reportedly discourages gauge numbers (to be verified). Tables
    also round it differently: 12 ga is 4.375 ÷ 40 = 0.109375 in (7/64), which MH29
    Table 13 lists as 0.1093.
  * AWG: the formula
* **Every system records:**
  * its density basis or formula, with its source
  * its rounding and a "nominal" flag. The rounding is part of the system's published
    definition, not display rounding: Manufacturers' Standard 12 ga is
    4.375 ÷ 41.82 = 0.104615…, published as **0.1046 in**. The derived thickness is that
    nominal at the system's recorded precision, which is the standard's own stated
    value, so it can be held as exact text ("0.1046 in") in a `TypedValue`. It then
    equals the course default, and the golden results don't drift. The unrounded
    derivation is shown as work. Each system's precision rule cites its source; the US
    Standard column's precision is to be checked against the statute text.
  * its tolerance standard, as a citation:
    * A568 for uncoated steel sheet
    * A924 for coated (galvanized) sheet, which A653 references (to be verified)
    * A480 for stainless
    * B209 for aluminum, which points to ANSI H35.2 for tolerances (to be verified)
* **Tests:** a handful of spot-check values against MH29 Table 2 and TO 1-1A-9 Table
  A-19 only, never a reproduced table and never a vendor value.
* **Choices belong to the domain, not to calculators.** Every numeric path assumes
  numbers: `Param.check`, `run()`'s inputs, the formula symbols, `Result`, the CLI's
  NAME=VALUE parsing, and `DomainValues`. So material, gauge system, and gauge number
  are not calculator `Param`s:
  * core gains a separate spec type, `Choice` (key, label, and where its options come
    from), and `Domain` gains a `choices` field
  * the Sheet Metal page resolves a choice into **derived** numeric values for the
    existing params, so calculators, the CLI, and formulas stay numeric
  * options can depend on another choice (system → numbers in 2a, material → temper in
    2b). That is designed in now, so 2b doesn't redo it.
  * a calculator-level categorical `Param` waits until a calculator truly needs one,
    such as a gauge-lookup calculator
  * choices get their own validator, separate from `Domain.validate`, because a choice
    may need a default where a setting may not
* **A bare gauge number can't be expressed.** The gauge is one compound choice (system
  plus number, e.g. option key "msg:12"), so the rule is structural rather than a check.
  Option keys are public identifiers (AGENTS rule 5). Options list only defined entries,
  so a choice can't silently fall back to a default.
* **The CLI is unchanged.** ADR-0013 §7 gives the CLI no settings, so a CLI user passes
  T. A gauge-lookup command could come later.
* **On the Sheet Metal page,** choosing a system and a gauge fills thickness as a
  **derived** value, e.g. "0.1046 in (12 ga, Manufacturers' Standard, gauges v1)".
  * Typing a thickness breaks the link by precedence alone: a typed (domain) value
    beats a derived one, and clearing it restores the link. No extra link state.
  * Range errors name a derived source the way they name a domain one, e.g. "from 12 ga,
    Manufacturers' Standard (gauges v1) is …".
* **Aluminum defaults to decimal thickness entry.** AWG is offered but isn't the default,
  because aluminum is ordered by decimal thickness.

### 3. Phase 2b: materials

* **Starter set:** 5052-H32, 6061-T6, mild cold-rolled steel (CS), and 304 annealed (2B).
  Galvanized and hot-rolled pickled and oiled (HR P&O) ship as gauge plus base-steel
  notes only, until we find a source for them.
* **Minimum-radius warnings** are checks, not inputs. They run as a post-run domain check
  over the resolved R and T and the chosen material, and add structured notes to the
  `Result`, so no calculator's compute step needs the material:
  * aluminum: AC 43.13 Table 4-6, labelled "aerospace bench practice"
  * mild steel: 2T from TO 1-1A-9's 1020/1025 entry, labelled as a conservative stand-in
  * 304: TO 1-1A-9, after a manual check of the table
  * Where sources disagree, warn at the **larger** radius and cite every source (M4).
  * Whenever a referenced minimum-radius check applies, the phase 1 rule-of-thumb
    warning (inside radius below the thickness) is dropped, so the two can't contradict
    each other. It still appears where no check applies.
  * **No applicable value is said aloud, never silent.** When no source covers the
    case, the app says so, with a `NoteKind.NO_APPLICABLE_VALUE` note. Examples: a
    thickness outside the table's band, an unlisted temper, a 180° hem against 90°
    tables, and galvanized or HR P&O, which have no source. Silence would read as "OK".
* **Strength** (stored now; used later for tonnage):
  * MIL-HDBK-5J for aluminum. A1008 stays unset.
  * 304: MIL-HDBK-5J, which covers it in a footnote to the AISI 301 table (Table
    2.7.1.0(b), p. 2-223); the values are to be verified. The A240 minimum we've seen
    came only through vendor pages, so it can't ship (§5.2). The fallback is the
    maintainer reading A240 in a legitimately accessed copy, if its license permits
    citing one isolated fact.
  * every strength value records its basis: specification minimum, typical, A-basis, or
    rule of thumb
  * tonnage must use the upper value, and strength checks the minimum. 304's typical
    value also came only from a vendor bulletin, so 304 tonnage waits for a source
    that passes §5.
* **K-factor and P** follow decisions M2 and M3. They are never shown as one confident
  value, and never marked verified.

### 4. Terminology

The glossary separates the neutral-axis **K-factor** from the FAA handbooks' setback
factor "K" = tan(θ/2). Help text that cites an FAA source says which one it means.

### 5. Release checklist for reference data (in place of a legal review)

The maintainer and the review session check every public release that adds or changes
reference data, phase 2a included. A release ships only if every item holds.

1. **Sources (copyright).** Every value is one of:
   * public domain
   * computed from a public-domain definition or a published formula
   * our own measurement
   * an isolated fact cited from a book or standard consulted in a legitimate copy, such
     as the 41.82 basis from MH29

   No value set is drawn substantially from a single cite-only source, and no table's
   layout is copied.
2. **Online terms and license agreements (contract).** Nothing comes from a website
   whose terms of use restrict reuse or couldn't be read, or from a document whose
   license agreement forbids it. This excludes The Fabricator for now, because its terms
   couldn't be read: nothing from Benson ships, not even an isolated fact in help text,
   until they can.
3. **Embedded third-party content.** Values that a government document credits to
   someone else are treated as cite-only. Examples:
   * the Raytheon chart and the TM Technologies chart (©1997) in 31B
   * the Aluminum Association values footnoted in MIL-HDBK-5J, such as 5052 H36/H38
4. **Safety rules hold.**
   * Where sources disagree, every check and warning uses the conservative value (M4).
   * Every strength used in a calculation states its basis. Tonnage uses the upper
     value and strength checks the minimum; for 304 the two differ widely.
   * A case with no applicable value is reported, not passed silently (§3).
5. **Liability labels.** Apache-2.0 already disclaims warranty and liability (sections 7
   and 8), and results already carry the app's disclaimer. Phase 2 adds:
   * gauge-derived thickness labelled **nominal**, with "check the material's
     specification or measure before cutting"
   * every warning labelled with its scope, e.g. "aerospace bench practice", from the
     `scope` field of the `Reference` it cites (§1)
6. **Currency.** Every value records its edition and access date. Superseded sources
   are flagged and re-checked at each release: for example, MIL-HDBK-5J was cancelled in
   2003, and TO 1-1A-9's newer revisions haven't been read.
7. **Corrections and removal.** The contributor docs invite anyone to report a wrong or
   rights-encumbered value. We fix or remove it promptly, and the citation on every value
   makes it traceable.

## Decisions by the maintainer

Approved on 2026-10-17, each as recommended. The alternatives stay on record.

| | Question | Recommended | Alternatives |
|---|---|---|---|
| M1 | Phasing | 2a gauge systems first; they are fully sourceable, high-confidence, and exercise all the new machinery: the reference layer, packaged data files, `Choice`, per-value derived sources, and provenance. Then 2b, materials, which adds data, checks, and the stress dimension. | Both at once |
| M2 | Revisit ADR-0013 decision E for K | Material choices drive only **material facts** live: gauge → thickness, minimum-radius warnings, and strength. K stays a user input. The material offers a **labeled starting value** (e.g. "0.447: FAA, aluminum bench forming"), applied only when the user clicks, with a prompt to calibrate by test bend. Once applied it is the user's own (domain) value, but it keeps its citation. | Keep E as approved (K derived live from the material); or offer no K suggestions at all |
| M3 | Whether to suggest P | **No P suggestion for now.** P stays a user input, the course's 0.156 stays the V-die default, and the help prompts a test bend. Revisit only if Benson's rule can be read first-hand under terms that pass §5.2. | (a) Strength scaling for steels only, stating the UTS basis, once the rule is verified and its terms pass §5.2; aluminum doesn't follow it. (b) A cited min/median/max range per material. Not advised: it draws a value set from one cite-only source, which the §5 checklist excludes |
| M4 | Sources that disagree | Show the range and every source. Checks and warnings use the conservative value. Never average. | Pick one preferred source per value |
| M5 | License of our data files | Apache-2.0, the same as the code: one license, with values attributed per entry. Public-domain values stay public domain. | CC0 for our compilation (most permissive); or CC BY 4.0 (requires attribution) |
| M6 | Starter material set | 5052-H32, 6061-T6, mild CR (CS), and 304 2B; galvanized and HR P&O as gauge plus notes. | A smaller set (aluminum only) or a larger one (wait for more sources) |
| M7 | Legal review | **None (not affordable).** The design ships only what needs no legal judgment, and the §5 checklist gates every public release of reference data, 2a included. | If a later feature needs something §5 excludes, look for free help first (e.g. a law-school IP clinic) rather than relaxing the checklist |

## Consequences

* The app can name exactly where every number came from, down to the table version, and
  how far to trust it.
* Gauge confusion, a real source of wrong parts, is designed out: a gauge is never
  accepted without its system, and each system discloses its density basis.
* The app doesn't pretend to know a shop's K-factor or die ratio. It suggests, labels,
  and asks for a test bend.
* Phase 2 adds the `Choice` spec type and the reference-data machinery to core, both
  standard library only. Calculators, the CLI, and formulas stay numeric.
* The packaging checklist gains the data files, with a test that loads them.
* Every public release of reference data runs the §5 checklist. Some useful data stays
  out until a source passes it: cited P ranges, recommended-radius tables, anything from
  The Fabricator, and 304 tonnage.
* ADR-0013 is marked "superseded in part by ADR-0014" at:
  * decision A: P is no longer derived from material (M3)
  * decision E: K and P are no longer live derived values (M2)
  * §11's phase-2 list: choices are domain-level rather than a calculator parameter
    kind, and "one active gauge table" becomes one compound gauge choice
* §11's "domain-level default bend method" is deferred to the ADR-0010 default-method
  question; it isn't part of phase 2.

## Alternatives considered

* **Shipping vendor or CAD-tool tables:** their terms forbid it.
* **Interpolating between sources:** this creates values no source states.
* **Material-driven K and P as live values:** this suggests a precision no source
  supports (M2).
* **Strength-scaled P for all materials** (the first draft's M3): it doesn't match the
  published aluminum figures, and the rule hadn't been read first-hand (Context 4).

## Amendments

### 2026-10-17: implementation clarifications for phase 2a

Accepted with the phase 2a plan; the decisions above are unchanged.

* **Source kind (§1, §5).** Each source declares its `kind`: book, standard, statute,
  government document, article, or website (`PublicationKind`). A book or a standard
  must name its edition, which makes that rule mechanically checkable. A source that
  credits its content to a third party (`third_party = true`) must be licensed as a
  cite-only fact (§5.3).
* **Bands and conditions wait for phase 2b (§1).** Thickness bands and conditions
  (temper, finish, bend axis, and so on) arrive with the data that needs them, so 2a
  adds no code for them. `ReferenceValue` holds a value in base units, its sources, its
  basis, its trust level, and the stated `TypedValue` when a source states the value.
* **Nominal precision (§2).** A standard's stated precision, such as Manufacturers'
  Standard 12 ga published as 0.1046 in, is data, not display rounding. It is applied in
  one place, `core.refdata.nominal()`, which takes the value in the unit the standard
  states and a `decimal` rounding mode, because systems differ (half-up, or truncation).
  This is the one exception to ADR-0005's display-only rounding, recorded in the
  guidelines (§2.7).
* **A basis for nominal values (§1).** `Basis` gains `nominal_definition`, for a value
  taken from a published definition, such as a gauge thickness.
* **Formulas live in code (§1).** Derivation expressions, such as weight ÷ density
  basis, live in the domain module and are reviewed and tested like calculator formulas
  (AGENTS rule 3). The TOML holds constants and definitions only.
* **No gauge by default in 2a (§2).** In phase 2a no gauge is selected by default, so
  thickness is entered as a decimal. The aluminum rule needs a material choice and
  moves to phase 2b.
* **The cite-only cap is per table (§1, §5.1).** Each table's `[table]` header sets
  `cite_only_cap`. For the 2a gauge table it is 1: the 41.82 density basis. Phase 2b
  sets its own with the maintainer.
* **Table schema.** A table has a `[table]` header (`name`, `version`,
  `cite_only_cap`), its `[[source]]` list, and domain content that its module reads.
  Unknown keys are refused, so a typo can't pass as an omission.

### 2026-10-17: the gauge choice and the nominal caution (maintainer, phase 2a)

* **D1: one compound gauge choice (§2).** The gauge is one `Choice` whose option keys
  name the system and the number, e.g. `"msg:12"`, so a bare gauge number can't be
  expressed. Each `Option` carries a `group`, the system, so a front end can show two
  levels. Truly dependent choices (`depends_on`) arrive in phase 2b, with material →
  temper.
* **D5: results carry the nominal caution (§5.5).** A `DerivedValue` may carry a `Note`,
  and `run()` adds it to the result whenever that derived value is actually used, not
  when a typed or explicit value overrides it. It is a warning whose subjects are the
  parameter keys and whose reference is the table. One note is added however many
  inputs derive from the same choice.
* **As built in `core.choices` and `core.domain`:**
  * `Choice(key, label, help, default)`: a choice may have a default option, which is
    why choices have their own check (`Domain.validate_choices`).
  * `Option(key, label, group)`. Option keys are public and stable, and follow
    `group:item` in lowercase letters, digits, and underscores.
  * `ChoiceResolver`, a protocol on `Domain.resolver`: `options(choice)` and
    `derive(selections)`.
  * `DerivedValue(value, source, stated, note)`, whose source must be a derived one.
  * `DomainValues.derived`, empty by default. `DomainSettings.set_choice()`,
    `clear_choice()`, and `choice()`, and `for_domain()` fills `derived` through
    `Domain.derived()`, which refuses a value for a key that isn't a setting or one
    outside the setting's range.
  * Precedence: explicit, then a set domain value, then a derived value, then the
    default. A range error names a derived source the way it names a domain one.
  * `nominal()` takes a `Fraction` (or a float at its exact binary value) and rounds by
    exact rational arithmetic, so a value exactly halfway rounds as the standard says.

### 2026-10-17: table schema hardened after review (phase 2a)

These replace the per-table cap and the float input of `nominal()` recorded above.

* **Schema version.** `[table]` declares `schema = 1`; a table in an unknown schema is
  refused. The domain module declares its content keys, and any other top-level key is
  refused, so a misspelt `[[sytem]]` fails loudly.
* **Kind and license agree (§5.1).** A public-domain source must be a statute or a
  government document, or state its `public_domain_basis` (e.g. "published before
  1930"). A book or a standard is a cite-only fact unless it states that basis.
* **Online terms are recorded (§5.2).** An article or website needs a `url`, a
  `terms_url`, the date its terms were checked (`terms_checked`), and
  `terms_outcome = "permits_reuse"`; anything else is refused. So a site whose terms
  couldn't be read can't be entered at all.
* **A defining source per value.** Each `ReferenceValue` names the one source its
  number comes from, separate from the sources that corroborate it. The value's license
  is its defining source's.
* **The cite-only cap is per source.** A cite-only source declares `cite_only_cap`, the
  number of values it may define; the gauge table's MH29 basis has 1. A code-level
  ceiling, `MAX_CITE_ONLY_PER_SOURCE` (1), bounds every cap. Raising it takes a code
  change and an amendment here.
* **Data is tied to its version.** A table's digest, a hash of its parsed content, is
  pinned per name and version in the tests, so changing data without bumping the
  version fails.
* **`nominal()` takes exact input only.** It accepts a `Fraction` or a `Decimal` and
  refuses a float, because some exact ties, such as US Standard 26 ga at 0.01875 in, sit
  just below the tie as floats. A value with no exact form, such as an AWG diameter, is
  computed as a `Decimal` at a stated working precision.

### 2026-10-17: dependent choices and derived provenance (maintainer, phase 2a)

These replace, in the gauge-choice entry above, the deferral of `depends_on` to phase 2b,
the resolver's `options(choice)`, and the wording of the derived note's subjects.

* **Derived provenance is required.** A `DerivedValue`'s source must name its table and
  version (`reference`), and `Domain.derived()` refuses a value whose source names
  another domain. Neither is filled in silently: a resolver that omits one has a bug,
  and the check fails as soon as the value is derived.
* **Dependent choices.** `Choice.depends_on` names the choices whose selections decide
  its options, as a temper depends on a material. The resolver's
  `options(choice, selections)` receives them.
  * Registration checks only the static parts: choice keys, that each parent is another
    declared choice, and that there is no cycle. Options are checked when they are
    computed; a malformed or repeated option key, or an option without a label, is a
    definition error.
  * Choices resolve in dependency order (`Domain.ordered_choices()`). Each takes the
    option the user chose if it is offered, else its default if that is offered, else
    nothing. A dependent choice's default applies only where its parents offer it; an
    independent choice whose default it doesn't offer is a definition error.
  * `set_choice()` accepts only an option offered under the current selections. When a
    selection changes, each dependent selection still offered is kept and the rest are
    cleared, so a change is never refused. `DomainSettings.cleared_choices()` names the
    ones cleared, so the GUI can announce them (2a.4).
* **Clear all restores each choice's default,** not no selection. The gauge has no
  default.
* **The derived note names its inputs.** Its subjects are the keys of the parameters
  that took the derived value, merged into one note when several did. A result carries
  a note only through a value that is used, so every `DerivedValue` a caution applies
  to carries the note itself.
* **Identifiers (Q3).**
  * Gauge option groups: `msg` (Manufacturers' Standard), `galv` (galvanized), `uss`
    (US Standard), and `awg`.
  * Phase 2b normalizes a designation into an option item by lowercasing it and turning
    `-`, `.`, and spaces into `_`, e.g. `al:6061_t6`, `ss:304_2b`.
  * A temper stays a separate, dependent choice; an option key never has a second colon.

### 2026-10-17: publications apart from sources (maintainer, phase 2a)

These replace, in the schema-hardening entry above, the source fields, the per-source
cap, and the rule that a statute or government document is public domain without a
stated basis. The schema changed before any table shipped, so it stays `schema = 1`.

* **A publication is declared once.** A table lists each work it cites as a
  `[[publication]]`: `id`, `kind`, `title`, `edition`, `url`, `license`,
  `public_domain_basis`, the online terms (`terms_url`, `terms_checked`,
  `terms_outcome`), `third_party`, and `cite_only_cap`. Each `[[source]]` cites a place
  in one: `id`, `publication`, `locator`, `accessed`, `scope`, and `detail`.
  * Kind, license, terms, and the cap belong to the publication, so citing a book in
    several places can't multiply its cap. The cap is counted per publication, under
    `MAX_CITE_ONLY_PER_PUBLICATION` (1), renamed from `MAX_CITE_ONLY_PER_SOURCE`.
  * A value still names one defining source, whose publication gives its license.
  * Two publications with the same title and edition are refused. They are compared
    casefolded, with whitespace and punctuation removed, so spelling variants of one
    work can't stand as two.
* **Every public-domain publication states its basis,** statutes and government
  documents included, e.g. "17 U.S.C. §105". A basis on a publication that isn't public
  domain is refused.
* **Public-domain hosts are allowlisted.** A test over the shipped tables requires each
  public-domain publication's url to be on a US government or military host (`.gov`,
  `.mil`) or a named mirror (everyspec.com, for DoD documents). A new host fails CI
  until someone adds it to the test on purpose. The allowlist is a tripwire, not a
  ruling: the basis states the claim, and a state `.gov` work needs its own, since
  17 U.S.C. §105 covers federal works only. The US Standard statute's url is the
  official one at uscode.house.gov, not a private mirror.
* **Own measurements are their own kind.** `PublicationKind.own_measurement` takes the
  `own_measurement` license, and no other kind does.
* **What the validator can't check.** It can't tell whether a value's defining source
  really states that value, or whether two differently worded editions are one work.
  Both stay with the release checklist (§5).
* **Correction to the identifiers above.** Phase 2b's material options name the
  designation without a temper, e.g. `al:6061` and `ss:304`. The temper is its own
  dependent choice, e.g. `temper:t6` or `temper:h32`. The example `al:6061_t6` was
  wrong.

### 2026-10-17: declared parents and derived-note subjects (maintainer, phase 2a)

These refine the dependent-choices entry above.

* **A resolver sees only the parents a choice declares.** `options()` receives the
  selections of the choices in `depends_on` and no others, so the declaration is a
  fact. A choice can't read a parent it doesn't declare and then lose its option
  silently when that parent changes.
* **A cleared choice says what it fell back to.** `cleared_choices()` returns
  `ClearedChoice(key, outcome)`, where the outcome is `"default"` or `"none"`, so the
  GUI can say "reset to its default" or "cleared".
* **Only `run()` names a derived note's subjects.** A `DerivedValue` whose note already
  has subjects is refused.
* **A kept dependent may be offered under another parent selection.** A dependent option
  is kept wherever the parents' new selections still offer it, including when a parent
  falls back to its default. So it may survive under a different parent selection than
  the one it was chosen under, e.g. an O temper chosen under one alloy, kept when the
  material falls back to a default alloy that also offers O.

### 2026-10-17: the gauge table as built (maintainer, phase 2a)

These settle the open items of §2 for the four gauge systems.

* **The data.** `caddcalc/calculators/sheet_metal/data/gauges.toml` ("Gauge systems",
  version 1) holds each system's definition, never a copied thickness table: the
  statute's weight column, the cited constants, and each system's range, published
  precision, and tolerance citation. The formulas live in `sheet_metal/gauges.py`, which
  evaluates every thickness exactly (a `Fraction`, or a `Decimal` at 40 digits for AWG)
  and states it with `nominal()`.
* **Its sources.**
  * 15 U.S.C. §206, the weights, read in the official GPO text (2024 edition) at
    govinfo.gov. uscode.house.gov returned server errors when this was checked, so the
    url is GPO's; both are official, and the private mirror isn't used.
  * NBS Circular 391: the 40 lb/ft² per inch wrought-iron basis, the galvanized
    coating rule, and the AWG definition.
  * Machinery's Handbook, 29th ed.: the 41.82 lb/ft² per inch steel basis, its one
    cite-only value.
* **Ranges and precision.** Manufacturers' Standard 3–38 and galvanized 8–34, both at 4
  decimals rounded half up; US Standard 0000000–38 at the statute's exact decimals; AWG
  0000–40 at 4 decimals rounded half up, and 5 below 0.0100 in.
* **Galvanized 32 ga ships as computed.** The definition gives 0.013450… in, 0.0135 at
  4 decimals; Machinery's Handbook Table 2 lists 0.0134, though every other gauge it
  lists matches. 32 ga isn't a spot check.
* **Tolerance citations, by designation only.** A568 for Manufacturers' Standard; A924
  for galvanized, to which A653 conforms; A480 for US Standard; B209 with ANSI H35.2 for
  AWG, as aluminum sheet. The B209 → H35.2 link is confirmed from referenced-document
  listings, not from ASTM's own page.
* **Withdrawn from §2:** "A480 reportedly discourages gauge numbers". It wasn't
  confirmed; restore it only if someone reads it in a legitimately obtained copy.
* **The caution.** A result that uses a gauge's thickness carries "Nominal thickness;
  check the material's specification or measure before cutting." Its references are
  the table and the system's tolerance standards, since the note sends users to the
  specification.
* **The choice.** The Sheet Metal domain offers `gauge`, with no default. Option keys
  are the system and the size, e.g. `msg:12`, `uss:0000000`; a multi-zero size reads as
  Machinery's Handbook writes it ("7/0 ga", "4/0 AWG"), and `GaugeSystems.key()` accepts
  either form. The Sheet Metal page offers it in 2a.4.
* **Formulas shown and evaluated agree.** Each formula is also kept as the expression
  users will see (`FORMULAS`). A test evaluates that expression for every gauge and
  requires the same stated thickness as the exact evaluation.
* **Correction to the identifiers above.** The example `ss:304_2b` is dropped: 2B is a
  finish, not a temper, and how to model a finish is a phase 2b question.

### 2026-10-17: printed works, editions, and the cap across tables (maintainer, phase 2a)

These refine the publications entry above.

* **A printed public-domain work is named on purpose.** The host-allowlist test treats a
  public-domain publication with no url as off the list, unless the test names it by
  table and publication id, with a comment on why it is public domain. None ships.
* **Editions compare by their leading number.** An edition that starts with a number is
  that number in the duplicate check, so "29", "29th", and "29th ed." are one edition.
  Any other edition compares loosely, like the title.
* **The cap holds across tables.** Each `TableSpec` says how its domain module builds the
  table's values (`values`). A test counts the values each cite-only work defines across
  every shipped table, by its loose title and edition, against
  `MAX_CITE_ONLY_PER_PUBLICATION`.

### 2026-10-17: one formula string, evaluated exactly and shown (maintainer, phase 2a)

This replaces, in the gauge-table entry above, the formulas kept twice.

* **`core.expr.evaluate_exact`.** It uses the same parser and allow-list as `evaluate`,
  so one expression is both evaluated and shown.
  * Arithmetic is exact rational arithmetic (`Fraction`), and a decimal literal is read
    as written.
  * A power with a non-integer exponent alone is computed as a `Decimal` to the stated
    `digits`, then carried on exactly. A whole exponent above 1000 is refused.
  * A float or bool input is refused, as are functions and `pi`, which have no exact
    value.
* **Each gauge formula exists once,** as its expression in `gauges.FORMULAS`; the Python
  evaluators are gone. The float agreement test now holds `evaluate_exact` against
  `evaluate` for every gauge, at its system's precision.
* **A derived value shows its work.** `DerivedValue.work` is an optional `Step`, whose
  value must equal the derived value. When an input takes the value, `run()` gives the
  step that input's symbol and places it ahead of the calculator's own work.
  * `Step` moves to `core.steps` and gains `substitution`: the shown values of the
    expression's symbols, when they aren't the calculator's.
  * A gauge's work reads T = (w + c) / 16 / B = (70 + 0) / 16 / 41.82 = 0.1046 in, and
    its note says how the exact value was stated, e.g. "0.1046150167… in before
    rounding to 4 decimal places". The front ends show that note from 2a.4.

### 2026-10-17: the corrections path and the gauge table's citations (maintainer, phase 2a)

These settle release-checklist item 7 and refine the gauge-table entries above.

* **Corrections (§5.7).** CONTRIBUTING.md has a "Reporting a wrong or rights-encumbered
  value" section, and `.github/ISSUE_TEMPLATE/reference_value.md` asks for the table and
  version, the value or option key, what's wrong, the evidence, and any rights concern.
  Both promise to fix or remove a value promptly. The README and the sheet-metal user
  guide link to it.
* **The caution points to the standard.** Each system's caution reads, e.g., "Nominal
  thickness; mill tolerances apply (see ASTM A568/A568M, 2025, rev. a). Check the
  material's specification or measure before cutting." The pointer is built from the
  tolerance publications, so each designation is written once, as a title and an
  edition.
* **Tolerance scopes say only what the abstracts confirm.** A568: general requirements
  for carbon and HSLA steel sheet (A1008, A1011). A924: general requirements for hot-dip
  metallic-coated sheet (A653). A480: general requirements for flat-rolled stainless,
  with dimensional-tolerance annexes. ANSI H35.2: its title. B209, 2021 rev. a, is the
  latest revision seen, as of 2026-10-17.
* **The statute's url is pinned to the 2024 edition** (`year=2024`), matching its
  recorded edition.
* **The US Standard label keeps its scope**, e.g. "12 ga, US Standard 1893, as commonly
  used for stainless; practice varies (nominal)".
* **Version bumps start with the first public release.** The gauge table hasn't been
  released, so these changes keep it at version 1 and re-pin its digest. From the first
  release on, any change to a table's data bumps its version.

### 2026-10-17: a copied derived value keeps its caution (maintainer, phase 2a)

* **An explicit input can carry a note.** `run(explicit_notes=...)` gives some explicit
  inputs a note, such as the caution of the derived value an input was copied from.
  `run()` adds it like a derived value's note, naming the inputs that carry it, and
  merges it with the same note from a derived value. A note for a key that isn't an
  input, or one that already has subjects, is refused. This is how the calculator page
  keeps the caution on a copy of a gauge thickness (review item M3).

### 2026-10-17: the gauge picker (maintainer, phase 2a)

* **The settings page.** A choice whose options have groups shows two boxes, the group
  (the system) and the option (the number); changing the group clears the option. A
  choice without a default starts at "None", so thickness is typed. A setting's derived
  value shows as its placeholder, and under it with its source, caution, and work; a
  typed value overrides it by precedence, and clearing restores it. Choices a change
  cleared are announced, with what each fell back to.
* **Calculator pages (review M3).** A derived value is a family value: it shows,
  inherits read-only, and copies on untick exactly like a set one. The copy is named
  "copied from" the derived value's source and carries its note into results
  (`run(explicit_notes=...)`), until the user types a new value. The run gets the
  family's set and derived values minus the keys the calculator overrides.
* **Work notes.** The app and the CLI show a step's note under formula steps too, so a
  derived value's "before rounding" line appears with its work.

### 2026-10-17: exact evaluation bounded, and work shown in its own unit (maintainer, phase 2a)

These refine the one-formula-string entry above; they replace its exponent limit.

* **Values are bounded, not just exponents.** `evaluate_exact` refuses any value whose
  numerator or denominator would pass `MAX_EXACT_BITS` (100,000 bits). It checks every
  operation's result, and estimates a whole power's size before computing it, so nested
  powers, products, and sums can't run away; `((10 ** 1000) ** 1000) ** 1000` is refused
  at once.
* **Zero to a power.** A negative exponent is a division by zero; a positive one gives
  0; and `0 ** 0` is 1, as in `evaluate` and Python's own power.
* **Work in its own unit (KI-005).** A derived value's expression yields its own unit,
  such as inches for a gauge, whatever the display unit. `Step.expression_unit` names it,
  and the work shows the value in it, then in the display unit:
  T = (w + c) / 16 / B = (70 + 0) / 16 / 41.82 = 0.1046 in = 2.6568 mm. It must be a
  unit of the step's dimension, on a formula step.
* **JSON lists both keys for every step.** `substitution` maps the formula's symbols to
  the text shown for them, not to numbers, and `expression_unit` names the unit; each is
  `null` for an ordinary step.

### 2026-10-17: gauge-table citations and labels after review (maintainer, phase 2a)

These refine the corrections-path and gauge-picker entries above.

* **Standards are cited by designation only,** with no url: the ASTM store urls are
  removed rather than unverified ones added.
* **ANSI H35.2 is cited at its current edition, 2024,** found on the ANSI webstore. Only
  the citation changes; no H35.2 content ships.
* **Each system's label names its material,** as US Standard's already did:
  "Manufacturers' Standard, steel sheet", "Galvanized, coated steel sheet", and
  "AWG (Brown & Sharpe), nonferrous". Results name it in the derived value's source.
* **The wheel doesn't change a choice.** A choice's boxes take the focus only by click or
  tab, and ignore the mouse wheel, so scrolling past them can't change a gauge unseen.
* The table stays at version 1 and its digest is re-pinned; it hasn't been released.

