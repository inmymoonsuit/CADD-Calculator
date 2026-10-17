# Engineering log: attempts, dead ends, and reversions

Newest first. This file records **what was tried and didn't work, or was undone**, so
nobody repeats it. Successful decisions belong in ADRs, and limitations belong in
known-issues. Keep entries short: what, why, outcome, and what to do instead.

Template:

```
## YYYY-MM-DD: Short title
**Tried:** …
**Outcome:** worked / failed / reverted (commit or PR link if any)
**Why:** …
**Instead / next time:** …
```

---

## 2026-10-16: Wrong claim that the Handbook doesn't scale by A/90

**Tried:** documenting (KI-012 and the course method note) that scaling 0.64T + 1.57R by A/90
was the prototype's own extension, after checking only the Eq. (33) page.
**Outcome:** reverted the same day. The review session pointed to MH29 p. 1351 ("Angle of Bend
Other Than 90 Degrees"), and reading that page confirmed the rule.
**Instead / next time:** search the whole section, not just the equation's page, before
writing that a source doesn't support something.

## 2026-10-16: Reading formulas out of the legacy `.xls` files

**Tried:** extracting cell formulas from `Lesson 2 …xls` and `Lesson 4 …xls` (Excel 97
BIFF format) with the Python library `xlrd`.
**Outcome:** failed for formulas. `xlrd` only returns cached *values* from BIFF files, not formula text.
**Instead:** opened the files through Excel's COM automation, **read-only with macros
force-disabled** (`AutomationSecurity = 3`), and read `Range.Formula`. The `.xlsm` rough
drafts are Open XML, so `openpyxl` reads their formulas directly. VBA modules were
read with `oletools`' `olevba`, which never runs macros. Results are in
[legacy-workbooks.md](legacy-workbooks.md).

## 2026-10-16: First reconstruction of formulas from values only

**Tried:** reverse-engineering the lesson formulas from the cached values before the real
formulas were available.
**Outcome:** superseded. The guesses (e.g. `BA = 1.57R + 0.64T`, `FPD = FVD − (R+T) + BA/2`)
turned out right, but guesses are not evidence.
**Instead:** always read the actual formula text. Treat value-matching as a check only.

## 2024 (prototype era): Excel/VBA "CADD Calculator Rough Draft" V1 and V2

**Tried:** building the app inside Excel. It had a VBA startup form, a dashboard sheet
with shape buttons, a basic arithmetic calculator form (adapted from a third-party
example), and an "Admin" reset table that restored input cells.
**Outcome:** abandoned for a standalone app (ADR-0002).
**Why:** Windows and Excel only. Formulas tied to cell addresses. No tests, no version
control, macro security prompts, and it can't be distributed as open source with
third-party assets inside.
**Kept:** the formulas (as `course` methods), the "reset to defaults" idea, and the
splash/about/dashboard UX ideas.
