# Release checklist record: the built-in units' citations

The ADR-0014 §5 checklist, applied to the works the built-in units cite (ADR-0019 §4). The
units aren't a reference table: their factors are definitions, declared in code
(`src/caddcalc/core/units/builtin.py`), not measured values. But they ship cited, so the
works they cite are held to the same checklist.

* **Works cited:**
  * NIST Special Publication 811, *Guide for the Use of the International System of
    Units (SI)*, 2008 Edition (web version 3.2, July 2008), A. Thompson and B. N. Taylor,
    https://www.nist.gov/pml/special-publication-811
  * the National Bureau of Standards' notice "Refinement of Values for the Yard and the
    Pound", *Federal Register* Vol. 24, No. 128, p. 5348: 24 FR 5348 (July 1, 1959),
    https://www.govinfo.gov/app/details/FR-1959-07-01
* **Prepared by:** the Calculator Engine session, 2026-10-18, building ADR-0019's u1.
* **Not legal advice.** This records the checks; it isn't a legal review (ADR-0014 M7).

| # | Item | Result | Evidence |
|---|---|---|---|
| 1 | Sources (copyright) | pass | Both are works of the U.S. government, public domain under 17 U.S.C. §105. SP 811 is a NIST Technical Series publication by NIST employees, and isn't Standard Reference Data under 15 U.S.C. §290e, which the SRD Act lets NIST copyright. The 1959 notice is a National Bureau of Standards notice in the *Federal Register*. What ships is facts: each unit's name, symbol, and factor, with its table or appendix as the locator; no text or table is copied. `test_every_unit_cites_its_definition_and_its_exact_factor` checks each citation's kind, licence, and basis through `core.citations.check_publication`. |
| 2 | Online terms and license agreements | pass | Neither is an article or a website. SP 811's url is on nist.gov, and the 1959 notice's on govinfo.gov, both on the public-domain host allowlist (`core.citations.PUBLIC_DOMAIN_HOSTS`). |
| 3 | Embedded third-party content | pass | SP 811 gives the SI as the CIPM and BIPM define it. Only definitions are used: the metre and its prefixes, the pascal, the radian, and the degree, which are facts. B.8 rounds the pound-force, psi, ksi and degree factors, so those come from exact definitions: the pound, standard gravity and the inch. B.8 prints the inch and the foot as exact. psi and ksi cite B.8's pound (footnote 22), pound-force (footnote 23), and standard free fall, and ksi the kip. |
| 4 | Safety rules | pass | Every factor is its exact definition, a rational, or for the radian 180/π to 50 digits, rounded once to a double. Factors built on others are held to their parts: the foot is 12 inches, psi is a pound-force on a square inch, and ksi is 1000 psi (`test_derived_factors_equal_their_definitions`). Every text that parsed before parses to the same value and unit, and every error reads the same, over more than 10,000 texts that include every parameter default and every value a shipped table states (`test_every_text_reads_as_it_always_has`). Rounding once moved one factor: psi, by one unit in the last place, recorded below. |
| 5 | Liability labels | not applicable | A unit is a definition, not a limit or a recommendation, so there's no scope to label. Display rounding is said in the user guide's "Units and precision". |
| 6 | Currency | pass, with a note | SP 811's 2008 edition predates the 2019 revision of the SI, which redefined the base units through fixed constants but changed none of the definitions cited here: the metre's length, the prefixes, the pascal, the radian, and the degree. NIST's page says the 2008 edition hasn't been updated for 2019 and points to SP 330 (2019) for the SI itself. The yard and pound of 1959 stand. The 1959 notice was published July 1, 1959 (govinfo: Vol. 24, No. 128, pp. 5327–5356); NIST's list gives June 30, likely its filing date. Re-check at each release. |
| 7 | Corrections and removal | pass | CONTRIBUTING.md, "Reporting a wrong or rights-encumbered value", and `.github/ISSUE_TEMPLATE/reference_value.md` cover units as they do table values. Every unit names its source and locator. |

## The one changed factor

psi's factor was computed in doubles, `0.45359237 × 9.80665 / 25.4²`, which rounds three
times. It's now its exact definition rounded once: 0.006894757293168362 MPa, one unit in
the last place above the 0.006894757293168361 before. No value shown at display precision
changes. ksi's factor, 1000 psi rounded once, is unchanged.

## Sign-off

* Maintainer: version 1 approved for release by the maintainer (unit definitions from
  NIST SP 811 and 24 FR 5348; behaviour unchanged apart from psi's recorded one-ulp
  change): "Sign and push." Date: 2026-10-18
* Review session (Support & Review): verified 84ceaba (rewritten from 55e20a7, with the same source code), and its rebased forms ac1d2c5 and 97f0f00, whose `core/units` and `citations.py` are identical to 84ceaba's by git tree. All seven items pass: SP 811's licence basis (17 U.S.C. §105; NIST Technical Series, not Standard Reference Data under 15 U.S.C. §290e); each unit's locator in SP 811, and in 24 FR 5348 (July 1, 1959, govinfo) for the inch, foot, psi and ksi; every factor exact and rounded once; and every parse and display rule unchanged by an independent diff of 411,844 results against 1ed4f4c, apart from psi's recorded one-ulp change. Date: 2026-10-18
* Rebased onto main on 2026-10-18, more than once as main moved: u1b, signed as 84ceaba,
  is now d9417f0, by way of ac1d2c5, 97f0f00 and 74c8ccc. Its `core/units` and
  `citations.py` are still the same git trees as 84ceaba's (`6e1a9cad…` and
  `4459e973…`), and this record is unchanged by the rebases. At the branch tip, every
  built-in unit's definition, factor, system and sources are identical to ac1d2c5's; i3
  changes their names to US spelling with British aliases, and i4 the parsing of typed
  numbers, both by ADR-0020, reviewed separately.

## Version 2: the squares and the minute and second (ADR-0019, u2 and u3), for review

The new units cite the same two works, which pass every item above; what's new is each
one's locator. Each square's factor is its length unit's exact factor squared, not a
factor read from SP 811; the minute is 1/60 degree and the second 1/3600, exactly.

| Unit | Locator in SP 811 | Also cited |
|---|---|---|
| mm² | Table 2 (area: square meter) and Table 5 (milli) | |
| cm² | Table 2 (area: square meter) and Table 5 (centi) | |
| m² | Table 2 (area: square meter) | |
| in² | Appendix B.8 (square inch to square meter) | 24 FR 5348, with the inch |
| ft² | Appendix B.8 (square foot to square meter) | 24 FR 5348, with the foot |
| arcmin | Table 6 (minute), §7.2 | |
| arcsec | Table 6 (second), §7.2 | |

* **Prepared by:** the Calculator Engine session, 2026-10-18, building u2 and u3.

### Sign-off, version 2

* Maintainer:
* Review session (Support & Review):

