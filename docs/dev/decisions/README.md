# Architecture Decision Records (ADRs)

An ADR records one significant decision: the context, what we chose, what we gave up,
and what we rejected. ADRs are **append-only history**. To change a decision, write a new
ADR that supersedes the old one, and set the old one's status to
`Superseded by ADR-NNNN`. Do not rewrite history.

Write an ADR when a choice is hard to reverse, affects contributors or users, or would
otherwise be re-argued later: languages, frameworks, file formats, units, licensing,
public APIs, and how formulas are verified.

Start from [template.md](template.md). Number sequentially and never reuse numbers.

| # | Title | Status |
|---|---|---|
| [0001](0001-record-architecture-decisions.md) | Record architecture decisions | Accepted |
| [0002](0002-python-and-pyside6.md) | Python 3.12+ with PySide6 (Qt) for the desktop app | Accepted |
| [0003](0003-layered-core-with-no-dependencies.md) | Layered architecture with a dependency-free core | Accepted |
| [0004](0004-declarative-calculators-with-provenance.md) | Declarative calculators: formulas as data, provenance, verification status | Accepted |
| [0005](0005-units-precision-and-display.md) | Units, numeric precision, and display rounding | Accepted |
| [0006](0006-extensibility-via-entry-points.md) | Extensibility: built-ins listed explicitly, plugins via entry points | Accepted |
| [0007](0007-documentation-in-repo-not-wiki.md) | Documentation lives in the repo, not a wiki | Accepted |
| [0008](0008-licensing-and-third-party-assets.md) | Licensing, and keeping third-party assets out of the repo | Accepted (Apache-2.0) |
| [0009](0009-packaging-and-distribution.md) | Packaging and distribution | Accepted (pyside6-deploy + Nuitka); installers, macOS/Linux, signing still proposed |
| [0010](0010-preserve-legacy-course-methods.md) | Preserve the legacy course methods alongside general methods | Accepted; amended to allow approved guards on impossible input |
| [0011](0011-branding-packs.md) | Brand private editions with a branding pack folder | **Proposed**; its `splash` key is replaced by 0015, and its `name` key is removed by 0016 |
| [0012](0012-engineering-standards-enforced-by-tooling.md) | Write down the engineering standards, and enforce them with tooling | Accepted |
| [0013](0013-domains-with-shared-settings.md) | Domains with shared settings that their calculators inherit | Accepted (phase 1 built); superseded in part by 0014 |
| [0014](0014-materials-and-reference-data.md) | Materials and reference data for sheet metal (ADR-0013 phase 2) | Accepted (phases 2a and 2b built; 2b's release sign-offs pending) |
| [0015](0015-welcome-screen.md) | A welcome screen composed from branding-pack parts | Accepted (built) |
| [0016](0016-welcome-style-system.md) | A style system for the welcome screen | Accepted |
| [0017](0017-result-fields.md) | Result fields: one boxed, copyable component for every calculator | Accepted; built |
| [0018](0018-geometry-and-conversions.md) | Geometry and Conversions families | Accepted; built (m1, m2) |
| [0019](0019-units-registry.md) | A units registry, the one source of unit knowledge | Accepted (its behaviour-neutral first step built, u1 and u1b; U5's spellings in i3) |
| [0020](0020-localization.md) | Localization, starting with a skeleton | Accepted (its skeleton being built: i1 to i4) |
| [0021](0021-window-and-page-layout.md) | Window and page layout, in text units | Accepted; built |
| [0022](0022-distribution-and-signing.md) | Distribution and signing, starting free | Accepted; not yet built |
| [0023](0023-layout-contract.md) | The layout contract | Accepted; not yet built (after 0024) |
| [0024](0024-units-on-fields.md) | Units on fields | Accepted; not yet built |
