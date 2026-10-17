# Release checklist record: Sheet-metal materials, version 1

The ADR-0014 §5 checklist, applied to the materials table before its first public release.

* **Table:** `src/caddcalc/calculators/sheet_metal/data/materials.toml`, "Sheet-metal
  materials", version 1, digest
  `c064d35b8e642f87db09c96747918186f0ec3cfe0b5b284e89c715b34ce3672f` (pinned in
  `tests/test_refdata.py`).
* **Prepared by:** the Calculator Engine session, 2026-10-17, from Support & Review's
  materials data brief and its §5 dry run in the review of 5f857eb..da31e0c. The dry run
  passed all seven items, conditional on the check stating its scope (review M2), which
  53715ca did.
* **Not legal advice.** This records the checks; it isn't a legal review (ADR-0014 M7).

| # | Item | Result | Evidence |
|---|---|---|---|
| 1 | Sources (copyright) | pass | Every minimum radius is public domain: FAA AC 43.13-1B Table 4-6 and USAF TO 1-1A-9 Tables 2-15, 2-16, and A-31/A-32. Every strength is public domain: MIL-HDBK-5J. FAA-H-8083-31B's K of 0.445 is public domain. The one cite-only value is *Engineering Drawing and Design*'s K of 0.4, its publication's cap of one (`test_edd5_defines_only_its_one_cite_only_value`, `test_no_cite_only_work_exceeds_the_ceiling_across_the_shipped_tables`). *Machinery's Handbook*'s K values appear only as citations in help text (D7). Each value is stated as its source states it, in the table's own structure; no table layout is copied. |
| 2 | Online terms and license agreements | pass | The table has no article or website publication. Its urls are faa.gov and everyspec.com, a named mirror of public-domain DoD and USAF documents (`test_every_shipped_public_domain_url_is_on_the_host_allowlist`). The Fabricator's terms were read and allow non-commercial use only, so nothing from it is used. |
| 3 | Embedded third-party content | pass | FAA-H-8083-31B Fig 4-124 credits a Raytheon manual; it isn't shipped, since TO 1-1A-9 carries the value it was needed for (D1). The TM Technologies chart in 31B isn't used. MIL-HDBK-5J's Aluminum Association-credited values (5052 H36 and H38) aren't used; the 5052-H32, 6061-T6, 1025, and 304 rows carry no third-party credit. |
| 4 | Safety rules | pass | Where sources differ, the check takes the larger minimum (D1, `test_6061_is_held_to_the_larger_source_at_each_thickness`) and holds a range to its upper bound (D2, `test_a_range_is_checked_at_its_upper_bound_and_shown_whole`). Between listed thicknesses it reads the next listing up, which the loader keeps from ever being less conservative (D4, `test_listed_thicknesses_read_within_two_percent_else_at_the_next_listing_up`). Every case without a value is said aloud: a thickness no source lists, Table 2-16's gap, a bend past 90° or a hem, and galvanized and HR P&O (`test_a_thickness_no_source_lists_is_said_aloud`, `test_a_bend_past_90_degrees_has_no_applicable_value`, `test_a_material_without_a_source_says_so`). Strengths are stored with their basis and used in no calculation; tonnage, which needs an upper value, can't use them (`test_strengths_carry_their_basis`). |
| 5 | Liability labels | pass | A limit note says "below the recommended minimum for … in aerospace bending practice", names each source with its locator, and lists each source's scope (`test_every_source_a_check_cites_states_its_scope`). Stand-ins are labelled in the notes and the facts (below). K starting values are rules of thumb, applied only on request, and carry a test-bend prompt while in use (`test_k_starting_values_are_rules_of_thumb_offered_per_material`, `test_applying_a_k_keeps_its_citation_and_prompt_until_typed_over`). The user guide says the sources are aircraft-repair and USAF/NAVAIR practice for 90° bends, and that press-brake production may differ. |
| 6 | Currency | pass | Every source records its access date (2026-10-17) and every publication its edition. AC 43.13-1B is cited at its May 2024 editorial update, Active by the FAA's advisory-circular index. TO 1-1A-9 is cited at its 17 Nov 2016 basic with Change 3 (2020), the newest everyspec lists; the official TO index (ETIMS) isn't public, so a later change can't be ruled out. The 2015 edition (Change 14) is cited only for its generic annealed corrosion-resistant row, in a note, and defines no value. **MIL-HDBK-5J was cancelled in 2003 and is used deliberately:** its successor, MMPDS, is copyrighted, and no public-domain successor exists (D6). Re-check the editions at each release. |
| 7 | Corrections and removal | pass | CONTRIBUTING.md, "Reporting a wrong or rights-encumbered value", and `.github/ISSUE_TEMPLATE/reference_value.md` promise to fix or remove a value promptly, and the sheet-metal user guide links to them. Every value names its source, locator, and scope. |

## Stand-ins, disclosed

Each is labelled where it is shown, in the notes and the material facts.

* **Mild steel's minimum radius** is TO 1-1A-9's 2T for 1020/1025, a conservative
  stand-in for ASTM A1008 CS, which has less carbon. It stops at 0.187 in (D4).
* **Mild steel's strength** is MIL-HDBK-5J's AISI 1025 annealed row, a stand-in for A1008
  CS, whose specification sets no minimum strength.
* **304 annealed's minimum radius** is TO 1-1A-9 Table 2-16's 2T, its only 304 row, which
  is for ½ Hard: conservative for annealed 2B sheet. The 2015 edition's generic annealed
  figure, about 1T, is cited in the note (D3).
* **304's strengths** are MIL-HDBK-5J's for AMS 5513 material; 2B sheet is commonly bought
  to ASTM A240/A480, which wasn't checked against them.

## Sign-off

* Maintainer:
* Review session (Support & Review): verified 914432d, table digest c064d35b8e64…672f; all seven items pass; stand-ins disclosed. Date: 2026-10-17
