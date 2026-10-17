# Materials data sources for sheet metal (research for ADR-0014)

* **Prepared:** 2026-10-17, by the Support & Review session, for
  [ADR-0014](../decisions/0014-materials-and-reference-data.md). **Updated** 2026-10-17
  for phase 2b, from Support & Review's materials data brief and reviews: §3, §6, §7, and
  §10 record what was resolved, and §11 what was newly found.
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
| 2024, 5052, 6061, 7075 aluminum | FAA AC 43.13-1B with Change 1, editorial update (May 2024), Ch. 4, par 4-56, Table 4-6, p. 4-17 (p. 4-14 in the earlier file, values identical): radii for 90° bends, 0.016–0.258 in, as ranges in multiples of t. https://www.faa.gov/documentLibrary/media/Advisory_Circular/AC_43.13-1B_CHG_1_Ed_Upd_FAA.pdf | Public domain | Spot values: 5052-H32 at 0.064 in = ½t–1t; 6061-T6 at 0.064 in = 1t–2t. Aircraft repair practice. **Shipped** for 5052-H32 and 6061-T6. |
| 6061-T6, and its group | USAF TO 1-1A-9 / NAVAIR 01-1A-9 (17 Nov 2016, Change 3, 24 Jan 2020), Tables A-31 and A-32, pp. A-45 and A-47, aluminum rows (Table A-16 in the 2015 edition, aluminum values identical): standard bend radii for 90° cold forming, as radii in inches. https://everyspec.com/USAF/USAF-Tech-Manuals/TO_1-1A-9_CHG-3_24JAN2020_56694/ | Public domain (Distribution A) | Spot value: 6061-T6 at 0.063 in = 0.16 in, about 2.5t, above AC 43.13's 1t–2t. **Shipped**; the check takes the larger of TO and AC's upper bound at each thickness (D1). |
| Aluminum | FAA-H-8083-31B, *AMT Handbook – Airframe* (2023), Ch. 4, Fig 4-124, p. 4-61. https://www.faa.gov/sites/faa.gov/files/FAA-H-8083-31B_Aviation_Maintenance_Technician_Handbook.pdf | Public-domain document, but the figure credits a Raytheon manual, so it is cite-only (ADR-0014 §5.3) | **Resolved:** the alloy-to-column mapping was checked visually, and the chart agrees with TO 1-1A-9 for 6061-T6 at 0.063 in. TO, a public-domain source, carries that value, so the chart isn't shipped (D1). |
| 1020/1025 carbon steel | TO 1-1A-9 (2016, Change 3), Table 2-15, p. 2-88 (Table 2-34, p. 2-128 in the 2015 edition; identical): 2T for 0.016–0.187 in | Public domain (Distribution A) | **Shipped** as a labelled, conservative stand-in for mild cold-rolled sheet (A1008 CS), stopping at 0.187 in (D4). |
| Stainless | TO 1-1A-9 (2016, Change 3), Table 2-16, p. 2-88 (Table 2-35 in 2015; identical); and the 2015 edition's Table A-16 | Public domain | **Read manually.** Table 2-16 lists 304 only for ½ Hard, at 2T, in bands 0.012–0.051, 0.051–0.090, and 0.190–0.250 in. **Shipped** for 304 annealed (2B) as a labelled, conservative stand-in (D3). Table A-16's generic "Corrosion Resistant, Annealed" row, about 1t and naming no alloy, is cited in the note only. |
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
| 304, annealed | MIL-HDBK-5J Table 2.7.1.0(b), p. 2-223: its footnote b applies the AISI 301 table to 304 bought to AMS 5513 (annealed), so 304 annealed takes the Annealed column: S-basis, ≤ 0.187 in, Ftu 73 (L) and 75 (LT) ksi, Fty 26 (L) and 30 (LT) ksi | Public domain | **Resolved and shipped.** The values attach to AMS 5513 material; 2B sheet is commonly bought to ASTM A240/A480, which wasn't checked against them, and the table says so. |
| 304 | ASTM A240 specification minimums | Cite-only | Seen only through vendor pages, so not carried here. |
| 304 | Mills' typical values | Vendor | Well above the specification minimum. Not carried. |
| ASTM A1008 CS | The specification sets no minimum strength | Gap | **Shipped** with MIL-HDBK-5J's AISI 1025 annealed row (S-basis, 55/36 ksi) as a labelled stand-in, which the maintainer accepted. |

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
| *The Fabricator* (FMA Communications) | **Read** (fmamfg.org/terms-of-use, undated; read in a browser on 2026-10-17): personal, non-commercial use only; republishing or reuse for public or commercial purposes needs written permission. That doesn't fit Apache-2.0, so nothing from the series is used. |

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

Open:

* ASTM B209 → ANSI H35.2: confirmed from referenced-document listings only; read
  ASTM's own B209 page.
* TO 1-1A-9's current edition: the 2016 basic with Change 3 is the newest everyspec
  lists. The official TO index (ETIMS) isn't public, so whether a later change exists
  can't be checked.

Resolved for phase 2b (2026-10-17; the materials data brief, ADR-0014 amendments):

* **FAA-H-8083-31B Fig 4-124's mapping** was checked visually: its columns are as the
  chart prints them, and for 6061-T6 at 0.063 in it agrees with TO 1-1A-9. The chart
  credits a Raytheon manual, so it stays cite-only and isn't shipped (D1).
* **TO 1-1A-9's radius tables were read by eye, in both editions** (2015 Change 14, and
  2016 with Change 3): carbon steel (Table 2-34 = 2-15), stainless (Table 2-35 = 2-16),
  and the standard bend radii (Table A-16 = A-31 and A-32). Their aluminum and Chapter 2
  values match between editions.
* **MIL-HDBK-5J covers 304** through footnote b of Table 2.7.1.0(b), for AMS 5513
  (annealed) material; §6 carries its values.
* **TO 1-1A-9 Table A-19's 20 ga** reads .0359 in at 24 oz/ft² in both editions (A-34 in
  2020). Its "US Standard (Revised)" column holds the 41.82-basis Manufacturers' Standard
  values, so a test citing it compares against `msg`, not `uss`.
* **The Fabricator's terms** were read: non-commercial use only, so the series is
  excluded (§7).

Resolved for phase 2a (2026-10-17; ADR-0014 amendments):

* **ASTM A924** is the tolerance citation for coated (galvanized) sheet: ASTM's abstracts
  show that A653 product conforms to it.
* **ASTM B209** lists ANSI H35.2 among its referenced documents, by the standards-store
  listings. Reading ASTM's own page stays open, above.
* **US Standard 1893's precision** is the statute's own exact decimal column, read in the
  official GPO text: 12 ga is .109375 in, and 37 ga .006640625 in. MH29 Table 13's 0.1093
  is the same value truncated.
* **ASTM A480's position on gauge numbers** couldn't be confirmed, so the claim was
  withdrawn rather than resolved.

## 11. Findings from phase 2b (2026-10-17)

* **AC 43.13-1B has a May 2024 editorial update** of the full document with Change 1,
  which the FAA's advisory-circular index lists as Active. Table 4-6 moved to p. 4-17;
  its 5052-H32 and 6061-T6 rows are the same, value for value, as the earlier file's
  p. 4-14, and the update corrects only a typo elsewhere in the table. The materials
  table cites the update.
* **TO 1-1A-9 has a 17 Nov 2016 basic with Change 3 (24 Jan 2020),** a complete
  publication under Distribution A, which renumbers the tables the 2015 edition (Change
  14) had: Tables 2-34 and 2-35 became 2-15 and 2-16 (p. 2-88), and Table A-16 became
  A-31 and A-32. The materials table cites the 2016 edition; the 2015 edition is cited
  only for its generic annealed corrosion-resistant row, which the 2016 tables carry with
  the error below. Its bending practice, to form across the grain where possible and to
  check a practice bend, adding a thickness or more to the radius if it cracks, is on
  p. 2-80 of the 2016 edition (¶2.18.1.2c and ¶¶2.19.1–2.19.1.1).
* **The 2020 Tables A-31 and A-32 carry an apparent column error in their steel rows.**
  The steel, stainless, and titanium rows sit under the aluminum thickness headings,
  which drop two thicknesses and add two, so their values are shifted one column against
  the 2015 Table A-16 and against the same edition's Table 2-15. The aluminum rows match
  between editions. By the maintainer's decision D9, the error isn't reported, and no
  steel or stainless value is taken from those tables: Tables 2-15 and 2-16 supply them.
* **304 has no applicable minimum radius from about 0.094 to 0.1875 in.** Table 2-16 has
  no band between 0.090 and 0.190 in, so common 304 sheet from 13 ga US Standard
  (0.09375 in) to 3/16 in gets a no-applicable-value note rather than a stretched value.
* **MIL-HDBK-5J was cancelled in 2003** and superseded by the copyrighted MMPDS. It is
  used deliberately, since no public-domain successor exists (D6), and the materials
  release record says so.
