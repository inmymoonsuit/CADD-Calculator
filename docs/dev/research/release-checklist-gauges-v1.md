# Release checklist record: Gauge systems, version 1

The ADR-0014 §5 checklist, applied to the gauge table before its first public release.

* **Table:** `src/caddcalc/calculators/sheet_metal/data/gauges.toml`, "Gauge systems",
  version 1, digest `3542868c5b82651082115ffa5c36f75524f8b760ab1d2a49496deb3ee13a343d`
  (pinned in `tests/test_refdata.py`).
* **Prepared by:** the Calculator Engine session, 2026-10-17, from Support & Review's dry
  run in its review of the gauge data (2a.3). The dry run passed items 1 to 6, and item 7
  was fixed by bcf13b7.
* **Not legal advice.** This records the checks; it isn't a legal review (ADR-0014 M7).

| # | Item | Result | Evidence |
|---|---|---|---|
| 1 | Sources (copyright) | pass | The weights are the statute's (15 U.S.C. §206, public domain). The 40 lb/ft² per inch basis, the galvanized coating rule, and the AWG definition are NBS Circular 391's (public domain). The 41.82 steel basis is the one cite-only fact, from *Machinery's Handbook*, 29th ed. Every thickness is computed from those definitions; no thickness table or table layout is copied. The cap of one value per cite-only work is enforced per publication and across every shipped table (`test_the_handbook_defines_only_the_steel_basis`, `test_no_cite_only_work_exceeds_the_ceiling_across_the_shipped_tables`). |
| 2 | Online terms and license agreements | pass | The table has no article or website publication, so no online terms govern a value. Its urls are the official GPO text of the statute (govinfo.gov), NBS Circular 391 at nvlpubs.nist.gov, and two ASTM store abstract pages, cited, not reused. Nothing comes from The Fabricator. The schema refuses an online source without recorded terms that permit reuse. |
| 3 | Embedded third-party content | pass | Circular 391 reprints 1927–1929 ASTM and industry tolerance tables; none is used. Only the Bureau's own definitions ship. The statute credits no one else. |
| 4 | Safety rules | pass | Phase 2a ships no strengths, limits, or checks, so no conservative value or basis is at stake. A derived thickness out of a calculator's range is refused, and the error names the gauge. |
| 5 | Liability labels | pass | A gauge's thickness is labelled "(nominal)", and every result that uses it, or a copy of it, carries "Nominal thickness; mill tolerances apply (see …). Check the material's specification or measure before cutting." Its references carry their scope (`test_choosing_a_gauge_derives_the_thickness_with_its_caution`, `test_an_unticked_copy_keeps_the_gauges_name_and_its_caution`). |
| 6 | Currency | pass | Every source records its access date (2026-10-17) and every publication its edition: the statute's 2024 edition (its url pinned to 2024), Circular 391 (1931), MH29 29th ed., and each ASTM and ANSI revision; B209 is marked "latest revision seen, as of 2026-10-17". No superseded source is used. Re-check the ASTM revisions at each release. |
| 7 | Corrections and removal | pass | CONTRIBUTING.md, "Reporting a wrong or rights-encumbered value", and `.github/ISSUE_TEMPLATE/reference_value.md` promise to fix or remove a value promptly. The README and the sheet-metal user guide link to them (bcf13b7). Every value is traceable through its source. |

## Sign-off

* Maintainer: ______________________ Date: ____________
* Review session (Support & Review): ______________________ Date: ____________
