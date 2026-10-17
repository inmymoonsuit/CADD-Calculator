# ADR-0001: Record architecture decisions

* **Status:** Accepted
* **Date:** 2026-10-16

## Context

This project will run for years, maybe with long gaps and changing contributors (human
and AI). An earlier attempt (Excel/VBA, 2024) left no record of *why* things were done.
We want to avoid re-arguing settled questions and repeating failed experiments.

## Decision

* Significant decisions go in numbered ADRs in `docs/dev/decisions/`.
* Experiments that were tried and abandoned or reverted go in
  [`docs/dev/engineering-log.md`](../engineering-log.md), even when nothing was committed.
* Known limitations and formula doubts go in [`docs/dev/known-issues.md`](../known-issues.md),
  with stable IDs (`KI-NNN`) that code and docs can reference.
* Actionable work items go in GitHub Issues, which link to KI and ADR IDs.

## Consequences

* A pull request that makes a significant decision must include an ADR.
* A small amount of writing overhead with each decision.

## Alternatives considered

* **Commit messages only**: hard to find, and they only capture what was committed, not what was abandoned.
* **A wiki**: see ADR-0007.
