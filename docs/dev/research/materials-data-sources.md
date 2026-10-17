# Materials data sources for sheet metal (research for ADR-0014)

* **Prepared:** 2026-10-17, by the Support & Review session, for
  [ADR-0014](../decisions/0014-materials-and-reference-data.md).
* **Accessed:** every source below was accessed on 2026-10-17 unless noted otherwise.
* **Not legal advice.** This summarizes research so the project can plan. The project has
  no budget for a legal review, so it ships only what needs no legal defense. See
  ADR-0014 §5 (release checklist) and decision M7.
* **This page follows ADR-0014 §5, as shipped data does.** It holds public-domain
  values, values computed from public-domain definitions, and isolated facts cited from
  books. Where a figure was seen only on a commercial website, or in a source whose terms
  we couldn't read, this page names the source and states the finding, but doesn't carry
  the figure.

## 1. Summary

* **Gauge tables can be computed rather than copied.** Every gauge system the starter
  materials need follows from a public-domain definition: the 1893 statute's weights, a
  stated density basis, the 1931 National Bureau of Standards (NBS) coating rule, and the
  AWG formula.
* **Commercial material data can't be redistributed.** Distributors, mills, CAD vendors
  and job shops either restrict reuse in their terms, or have terms we couldn't read.
* **Government handbooks supply aluminum minimum bend radii, a mild-steel bend rule, and
  aluminum strengths.** They describe aerospace bench practice, not press-brake practice,
  and some of them disagree.
* **No source gives the neutral-axis K-factor or the air-bend ratio P as a material
  property.** Both depend mostly on the process and the tooling.

## 2. Gauge systems

All four systems below can be generated from definitions. Every value in this section
is computed by us from public-domain data, unless it is marked as a cited fact.

### 2.1 Manufacturers' Standard Gauge (steel sheet)

* **Definition.** Take the weight per square foot for each gauge number, from the
  statute (below), and divide by a steel density basis of 41.82 lb/ft² per inch of
  thickness.
* **The statute.** 15 U.S.C. §206 (Act of March 3, 1893, ch. 221, 27 Stat. 746). It is
  public domain, as a US government work (17 U.S.C. §105).
* **The basis.**
  * The 41.82 figure is a fact cited from *Machinery's Handbook*, 29th ed. (MH29),
    "Sheet-Metal Gages", printed p. 2608.
  * We couldn't confirm the AISI origin that is often given for it.
  * NBS Circular 391 (1931) uses 40.80 for steel instead. The basis is a choice, and
    each system must disclose its own.
* **Computed values.**

  | Gauge | Thickness (in) |
  |---|---|
  | 10 | 0.1345 |
  | 12 | 0.1046 |
  | 14 | 0.0747 |
  | 16 | 0.0598 |
  | 20 | 0.0359 |
  | 24 | 0.0239 |

  These agree with MH29 Table 2 (printed p. 2608), which we checked by spot values only.
* **A naming trap.** USAF TO 1-1A-9 Table A-19 lists the same values (we checked 20 ga)
  under a column labelled "USSG (Revised)".

### 2.2 Galvanized sheet gauge

* **Definition.** Add 2.5 oz/ft² to the statute weight, for the coating, then apply the
  same basis.
* **Source of the coating rule.** NBS Circular 391, *Gage Systems* (1931), public domain:
  https://nvlpubs.nist.gov/nistpubs/Legacy/circ/nbscircular391.pdf
* **Computed values at the 41.82 basis:** 12 ga = 0.1084 in, 16 ga = 0.0635 in,
  20 ga = 0.0396 in. These also agree with MH29 Table 2, by spot check.

### 2.3 US Standard Gauge (1893), as commonly used for stainless

* **Definition.** The statute's own "approximate" thickness column: the weight divided
  by 40 lb/ft² per inch (wrought iron).
* **Computed values:** 12 ga = 0.109375 in, 14 ga = 0.078125 in, 16 ga = 0.0625 in.
* **Vendor listings disagree with this column at some gauges,** for example 14 ga. We
  don't reproduce vendor figures.
* **Rounding differs between tables.** MH29 Table 13 (printed p. 1352) lists 12 ga as
  0.1093.

### 2.4 AWG (Brown & Sharpe), formerly used for aluminum

* **Definition.** A geometric series: No. 0000 = 0.4600 in to No. 36 = 0.0050 in, each
  step a fixed ratio (NBS Circular 391). For example, 12 AWG = 0.0808 in.
* **Practice.** In practice, aluminum sheet is ordered by decimal thickness (ASTM B209;
  MH29 p. 2609 describes the same shift to decimals).

### 2.5 Why the system must always be named

Twelve gauge is 0.1046 in (Manufacturers' Standard), 0.1094 in (US Standard 1893),
0.1084 in (galvanized), or 0.0808 in (AWG), depending on the system. Accepting a bare
gauge number can produce a wrong part.

## 3. Minimum inside bend radius

| Material | Source | Status | Notes |
|---|---|---|---|
| 2024, 5052, 6061, 7075 aluminum | FAA AC 43.13-1B with Change 1 (2001), Ch. 4, Table 4-6, p. 4-14: radii for 90° bends, 0.016–0.258 in, as ranges in multiples of t. https://www.faa.gov/documentLibrary/media/Advisory_Circular/AC_43.13-1B_w-chg1.pdf | Public domain | Spot value: 5052-H32 at 0.064 in = ½t–1t. Aerospace bench practice. |
| Aluminum | FAA-H-8083-31B, *AMT Handbook – Airframe* (2023), Ch. 4, Fig 4-124, p. 4-61. https://www.faa.gov/sites/faa.gov/files/FAA-H-8083-31B_Aviation_Maintenance_Technician_Handbook.pdf | Public-domain document, but the figure credits a Raytheon manual, so treat it as cite-only (ADR-0014 §5.3) | **Conflict:** for 6061-T6 at 0.064 in it reads about 2.5t, against 1–2t in AC 43.13. Which column belongs to which alloy is still to be checked visually. |
| 1020/1025 carbon steel | USAF TO 1-1A-9 / NAVAIR 01-1A-9 (basic 1999, Change 14, 2015), Table 2-34, p. 2-128: 2T for 0.016–0.187 in. https://everyspec.com/USAF/USAF-Tech-Manuals/TO_1-1A-9_CHG-14_53433/ | Public domain (Distribution A) | A conservative stand-in for mild cold-rolled sheet. Newer revisions couldn't be fetched. |
| Stainless | TO 1-1A-9 Table A-16 (and Table 2-35) | Public domain | The text extraction is garbled, so the values need a manual reading. |
| Hot-rolled steel | ASTM A1011, Appendix X1 (suggested minimum inside radius by grade) | Cite-only | Check the current edition. |
| Galvanized | No public-domain source found | Gap | A653 has a bend *test*, which is acceptance, not fabrication guidance. |
| Aluminum (industry) | Aluminum Association, *Aluminum Standards and Data* | Cite-only | One supplier catalog reproduces this kind of table without credit. That is one more reason not to source from catalogs. |

## 4. Neutral-axis K-factor

* **No source gives K as a material property.**
* **What sources we can cite imply.**
  * The FAA bend-allowance formula, (0.01743R + 0.0078T)·N, implies k ≈ 0.447. Source:
    FAA-H-8083-31B pp. 4-63–4-64, public domain; aluminum, bench forming.
  * MH29 Eqs (32)–(34), printed p. 1347 (cite-only), imply about 0.35, 0.407, and 0.452
    for three material classes.
  * *Engineering Drawing and Design* (5th ed., Ch. 19) uses 0.4 as an instructional
    value.
  * The neutral axis approaches mid-thickness (K → 0.5) as R/T grows.
* **What trade sources say, without their figures.**
  * A job-shop design guide and articles in *The Fabricator* describe K rising with R/T,
    and differing between air bending, bottoming, and coining.
  * CAD tools ship different defaults: one documented in Onshape's help, and another
    reported only on user forums.
  * We don't reproduce those figures. Their terms weren't checked, or restrict reuse,
    or the source is a forum.
* **Terminology trap.** In FAA AC 43.13-1B (Table 4-7) and FAA-H-8083-31B, "K" is the
  *setback factor* tan(θ/2), not the neutral-axis K-factor.

## 5. Air-bend ratio P (inside radius ÷ V-die opening)

* **Sources.** All are cite-only, and their terms of use couldn't be read:
  * S. Benson, "K-factors, Y-factors, and press brake bending precision," *The
    Fabricator*.
    https://www.thefabricator.com/thefabricator/article/bending/k-factors-y-factors-and-press-brake-bending-precision
  * "Formable aluminum: press brake bending 6061 with the 20% rule."
    https://www.thefabricator.com/thefabricator/article/bending/formable-aluminum-press-brake-bending-6061-with-the-20-rule
  * "When there is no choice but to bend sharp on the press brake."
    https://www.thefabricator.com/thefabricator/article/bending/when-there-is-no-choice-but-to-bend-sharp-on-the-press-brake
  * "How air forming works." https://www.thefabricator.com/article/bending/how-air-forming-works
  * "Bending basics: dissecting bend deductions and die openings."
    https://www.thefabricator.com/thefabricator/article/bending/bending-basics-dissecting-bend-deductions-and-die-openings
* **Findings.**
  * Published P varies widely between articles, including for the same alloy and
    temper.
  * It does not track tensile strength for aluminum. A strength-scaling rule described in
    the same series predicts a lower P for softer aluminum, but the published figure for
    an annealed temper is higher than the figure for harder tempers.
  * One fabricator's online bend calculator implies a ratio above every article's figure
    for the same alloy.
  * P is set by the shop's process and tooling more than by the material.
  * The course spreadsheets' value, 0.156, is the project's own legacy value.
* **No public-domain source for P was found.**

## 6. Strength

| Material | Source | Status | Notes |
|---|---|---|---|
| 5052-H32 sheet | MIL-HDBK-5J (31 Jan 2003), Table 3.5.1.0(b1), p. 3-220: Ftu/Fty 31/23 ksi | Public domain (Distribution A) | — |
| 6061-T6 sheet | MIL-HDBK-5J Table 3.6.2.0(b1), p. 3-264: A-basis (L) 42/36 ksi | Public domain | A-basis is a statistical allowable, not a specification minimum or typical value. |
| AISI 1025, annealed sheet | MIL-HDBK-5J Table 2.2.1.0(b), p. 2-8: 55/36 ksi | Public domain | — |
| 304 | MIL-HDBK-5J covers 304 in a footnote to the AISI 301 table (Table 2.7.1.0(b), p. 2-223) | Public domain | To verify. |
| 304 | ASTM A240 specification minimums | Cite-only | Seen only through vendor pages, so not carried here. |
| 304 | Mills' typical values | Vendor | Well above the specification minimum. Not carried. |
| ASTM A1008 CS | The specification sets no minimum strength | Gap | — |

MIL-HDBK-5J is at https://everyspec.com/MIL-HDBK/MIL-HDBK-0001-0099/MIL_HDBK_5J_139/.
It was cancelled in 2003. Its successor, MMPDS (mmpds.org), is copyrighted and is not
used. Some of 5J's 5052 values (H36/H38) are footnoted as coming from the Aluminum
Association; treat those as cite-only (ADR-0014 §5.3).

## 7. Terms of use we checked

These are paraphrased; no terms are quoted.

| Source | Finding |
|---|---|
| Arconic (arconic.com/legal-notices) | Non-commercial personal use only |
| Kaiser Aluminum (kaiseraluminum.com/terms-and-conditions/) | Limited personal use; no scraping |
| Novelis (novelis.com/terms-of-use/) | Non-commercial reuse with credit. Doesn't fit Apache-2.0. |
| Outokumpu (outokumpu.com/en/legal-notice) | Commercial copying needs written permission |
| Klöckner (kloeckner.com/en/user-notes) | Parent company's notice: reproduction needs consent. US site's terms not read. |
| Ryerson, Online Metals, North American Stainless | Terms couldn't be read |
| SendCutSend, Protolabs, Xometry | Copying or republishing site content needs permission |
| DS SolidWorks, Autodesk | Bundled content, including sample gauge tables, may be used only with the product |
| ASTM (store.astm.org/restricted_copyright-and-permissions) | All content copyrighted; reproduction by paid permission |
| Aluminum Association | Copyrighted |
| *The Fabricator* (FMA Communications) | Terms couldn't be read (pages refused automated access) |

## 8. Legal framing (not legal advice)

**United States: copyright.**
* Facts are not copyrightable. A compilation is protected only in its original
  selection and arrangement, and that protection is thin: *Feist Publications, Inc. v.
  Rural Telephone Service Co.*, 499 U.S. 340 (1991).
* Defined or measured values (statute weights, specification minimums, computed
  thicknesses) can be re-entered with a citation.
* Values that embody expert judgment carry more risk. Courts have found originality in
  valuations: *CCC Information Services v. Maclean Hunter Market Reports*, 44 F.3d 61
  (2d Cir. 1994). Tables of "recommended" radii or "approximate" ranges belong here: take
  isolated values with a citation, and never a table's layout.
* US government works are not copyrighted (17 U.S.C. §105). They can embed third-party
  material, which must be treated as cite-only. NIST Standard Reference Data is an
  exception (15 U.S.C. §290e).

**United States: contract.** Website terms and standards licenses bind as contracts,
whatever copyright says: *ProCD, Inc. v. Zeidenberg*, 86 F.3d 1447 (7th Cir. 1996). This
is the main practical barrier, and the reason the project doesn't take vendor values it
has seen under their terms.

**European Union.**
* The Database Directive (96/9/EC) adds a *sui generis* right (Art. 7) for databases from
  qualifying makers, meaning makers established in the EU or EEA.
* It protects substantial investment in obtaining, verifying, or presenting the
  contents. It bars extracting or re-using a substantial part, and also repeated,
  systematic extraction of insubstantial parts.
* Investment in *creating* the data does not count: *British Horseracing Board v William
  Hill*, C-203/02 (CJEU 2004).
* The EU has no general fair-use doctrine. Its exceptions, such as illustration for
  teaching, are narrow and non-commercial. The UK has an equivalent database right.

**Fair use is not the project's basis.**
* Fair use (17 U.S.C. §107) is a defense. It is decided case by case, only if someone
  challenges a use, and ultimately by a court. Even a successful defense costs money.
* It doesn't reliably override contract terms, and it has no counterpart for the EU
  database right.
* The project is educational, but Apache-2.0 lets anyone reuse its files commercially,
  so that purpose doesn't carry to downstream users.

**What this means for the project.** No legal review is affordable (ADR-0014 M7). The
project therefore ships only an original compilation that needs no defense, as ADR-0014
§5 sets out:
* our own small selection and schema
* public-domain or computed values
* at most isolated facts cited from books and standards
* a citation on every value, which is attribution only and grants no permission

## 9. Risks for the design

1. **K and P follow the process,** not the material: air bending, bottoming, or coining,
   the tooling, R/T, grain direction, and the material lot. Show them as labelled
   starting values with a test-bend prompt, never as verified values (ADR-0014 M2, M3).
2. **Gauge ambiguity produces wrong parts** (§2.5). Never accept a gauge number without
   its system.
3. **Aerospace tables aren't press-brake practice.** Label the scope of every warning.
4. **Sources conflict** (6061-T6 radius; P generally). Show every source, use the
   conservative value in checks, and never average (ADR-0014 M4).
5. **Strength basis matters for safety.** A typical value can be well above the
   specification minimum. Tonnage must use the upper value; strength checks use the
   minimum. Every strength value records its basis.
6. **Public-domain documents can embed third-party content**: the Raytheon and TM
   Technologies charts in FAA-H-8083-31B, and the Aluminum Association values in
   MIL-HDBK-5J. Treat them as cite-only.
7. **Data goes stale.** Record the edition and access date for every value, and flag
   superseded sources: MIL-HDBK-5J is cancelled, and newer TO 1-1A-9 revisions are
   unread.

## 10. Open verification items

* FAA-H-8083-31B Fig 4-124: confirm the alloy-to-column mapping visually.
* TO 1-1A-9 Tables 2-35 and A-16: read the stainless values manually.
* MIL-HDBK-5J Table 2.7.1.0(b): confirm 304's coverage and its values.
* ASTM B209 → ANSI H35.2 (aluminum tolerances): confirmed from referenced-document
  listings only; read ASTM's own B209 page.
* The Fabricator's terms of use: read them before anything from the series is
  considered (ADR-0014 §5.2, M3).
