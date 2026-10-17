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

## 2026-10-17: Nuitka 4.3 builds that crash when they open
**Tried:** building the app with pyside6-deploy and the newest Nuitka, 4.3, which uv
chose for `nuitka>=4.1.1`.
**Outcome:** failed. The app exited with an access violation while building the main
window ("Nuitka: A segmentation fault has occurred"). faulthandler pointed into
`caddcalc.core.expr.render_symbolic` during the first calculation, and gdb showed the fault
inside Nuitka-compiled code, reading a bad free-list pointer. It crashed the same way with
MinGW gcc 15.2 and with Zig 0.16, with uv's CPython 3.12 and python.org's CPython 3.14, and
with LTO off. The pre-branding `app.py` crashed too, so it wasn't the new code. Small
scripts running the same calculation inside a Qt signal didn't crash; creating
`MainWindow` right after `QApplication` did. Nuitka 4.1.1, the version pyside6-deploy
6.12's `default.spec` names, builds a working app from the same code.
**Instead:** pin `nuitka==4.1.1` in the `build` dependency group, and move the pin with
pyside6-deploy's `default.spec` when PySide6 is upgraded. Not reported upstream yet; the
smallest reproduction so far is "create a QApplication, then `MainWindow()`".

## 2026-10-17: A MinGW header "missing" when building inside the Claude desktop app
**Tried:** the first pyside6-deploy build, started from a Claude Code session in the
desktop app.
**Outcome:** failed with `propsys.h: fatal error: structuredquerycondition.h: No such file
or directory`, although the file was there.
**Why:** the desktop app is a packaged (MSIX) app, so `%LOCALAPPDATA%` was redirected to
`…\Packages\Claude_<id>\LocalCache\Local\`, and Nuitka's cache with it. gcc's
unnormalized include path (`…\bin\..\lib\gcc\…\..\..\..\..\x86_64-w64-mingw32\include\`)
plus that header's long name passed Windows' 260-character limit. Shorter header names
still fit, which made it look like a broken download.
**Instead:** set `NUITKA_CACHE_DIR` to a short folder, e.g. `C:\Users\<you>\.cache\nuitka`.
Builds from a normal terminal aren't affected.

## 2026-10-17: Smoke-test screenshots with boxes instead of text
**Tried:** checking the packaged build with `--smoke-test`, which saves a screenshot.
**Outcome:** fixed the same day. Every character in the screenshot was a box, and the
window had no DPI scaling.
**Why:** the build script's icon helper set `QT_QPA_PLATFORM=offscreen` in its own
environment to draw icons without a display, and the app under test inherited it. On
Windows, Qt's offscreen platform has no fonts. The packaged app itself was fine.
**Instead:** `packaging/icons.py` uses the offscreen platform only on Linux without a
display, and only while it creates its QGuiApplication.

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
