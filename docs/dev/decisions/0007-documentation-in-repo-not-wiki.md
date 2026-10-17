# ADR-0007: Documentation lives in the repo, not a wiki

* **Status:** Accepted
* **Date:** 2026-10-16

## Context

We need two kinds of documentation:

1. **Developer docs:** architecture, decisions, known issues, and attempted or reverted work.
2. **User docs:** how to use each calculator, its formulas, units, and a glossary.

GitHub Wikis are a tempting home, but a wiki is a *separate* git repository. It isn't
reviewed in pull requests, isn't versioned with the code (so docs for v1.2 can't sit
next to v1.2), isn't carried by forks, and can't be checked in CI.

## Decision

* All documentation is Markdown in this repository:
  * `docs/dev/` for developers (ADRs, architecture, known issues, the engineering log,
    the roadmap, and the legacy-workbook transcription).
  * `docs/user/` for users.
* A change that alters behavior updates the docs **in the same pull request**.
* User docs are written so a static-site generator can publish them later without
  rewriting. Choosing that generator is deferred until there is a release to document.
  Candidates: MkDocs-Material or its successor Zensical, or Sphinx with MyST.
* The GitHub Wiki stays **disabled**, so there is one source of truth.
* Per-calculator help in the app comes from the calculator's own metadata (ADR-0004).
  Later, the user-doc calculator pages can be generated from that metadata as well.

## Consequences

* GitHub renders the docs as-is today. No tooling is needed yet.
* Docs are reviewed like code, and the history shows when a formula's documentation changed.
* We still owe a docs site before the first public release (roadmap).

## Alternatives considered

* **GitHub Wiki**: rejected for the reasons above.
* **Picking a site generator now**: premature. The Markdown carries over.
