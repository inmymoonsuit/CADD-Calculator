# Legacy workbooks: transcription and reuse inventory

The original files are kept locally in the git-ignored `resources/` folder (ADR-0008). This page
records **what they computed**, in our own words, so they can be retired safely. The formula
text was read from the files themselves (see the [engineering log](engineering-log.md)), not
inferred.

Symbols: T = material thickness, R = inside bend radius, FVD = formed view dimension
(outside), A = bend angle (from flat), BA = bend allowance, FPD = flat pattern dimension,
FDO = female (V) die opening.

## Lesson 2: 90 Degree Bend Calculation (`.xls`)

| Cell | Name | Formula (as written) | Example value |
|---|---|---|---|
| B1 | MATL (T) | input | 0.1046 |
| B2 | RADIUS (R) | input | 0.156 |
| B3 | FVD | input | 1.12 |
| B5 | BA | `=(0.64*B1)+(1.57*B2)` | 0.311864 |
| B9 | FPD, one 90° bend | `=B3-(B2+B1)+B5/2` | 1.015332 |
| B13 | FPD, two 90° bends | `=B3-2*(B1+B2)+B5` | 0.910664 |
| B16 | FDO | `=B2/0.156` | 1 |

The sheet says: "Do not type in red cells as the equations will be erased."

**Source:** `0.64T + 1.57R` is *Machinery's Handbook* 31st ed., Allowances for Bending Sheet
Metal, Eq. (33), printed p. 1421 (p. 1347 in the 29th ed.). `R/0.156` is not in that book (KI-003).

The formula is the neutral-axis arc, (π/2)·(R + K·T) at 90°, with K fixed at about
0.408 and π/2 rounded to 1.57, which is why the app names the method **Fixed K-factor
(≈ 0.41)** (ADR-0010, amendments). Its key stays `course`.

**In the app:** `sheet_metal.bend_allowance` (method `course`),
`sheet_metal.segment_flat_length` (`course`; one bend is A2 = 0°), and
`sheet_metal.v_die_opening` (`radius_ratio`, P = 0.156). Golden tests:
`tests/test_legacy_golden.py`.

## Lesson 4: Cone Spread Sheet (`.xls`)

| Cell | Name | Formula (as written) | Example value |
|---|---|---|---|
| B1 | Top Dia (Dt) | input | 6 |
| B2 | Bot Dia (Db) | input | 10 |
| B3 | Cone H | input | 5 |
| B4 | MT (T) | input | 0.0747 |
| B11 | CH, cone hypotenuse | `=SQRT((((B2/2)-(B1/2))^2+(B3)^2))` | 5.385164807134504 |
| B6 | FPIR | `=(B11*(B1/2))/((B2/2)-(B1/2))` | 8.077747210701755 |
| B7 | FPOR | `=B6+B11` | 13.46291201783626 |
| B9 | FPA (degrees) | `=(360*((B2-B4)*(PI())))/(2*B7*(PI()))` | 132.70189968062587 |

FPA simplifies to `180·(Db − T)/FPOR`. See **KI-001**: only this cell uses T.

**In the app:** `sheet_metal.truncated_cone_layout` (method `course`).

## CADD Calculator Rough Draft V1 / V2 (`.xlsm`, 2024)

V1 and V2 are functionally identical. V2 adds empty event handlers.

**Sheet "Non-90 Degree Bend Calculations"** (inputs B1 to B5 = T, R, FVD, A1, A2):

| Cell | Name | Formula |
|---|---|---|
| B6 | BA1 | `=((0.64*B1)+(1.57*B2))*B4/90` |
| B7 | BA2 | `=((0.64*B1)+(1.57*B2))*B5/90` |
| B10 | FPD, one bend | `=((B3-((TAN(B4/2*PI()/180))*(B2+B1)))+(B6/2))` |
| B14 | FPD, two bends | `=((B3-((TAN(B4/2*PI()/180))*(B2+B1))-((TAN(B5/2*PI()/180))*(B2+B1)))+(B6/2)+(B7/2))` |
| B17 | FDO | `=B2/0.156` |

These generalize Lesson 2: `(R + T)` becomes the outside setback `tan(A/2)·(R + T)`, which equals
`R + T` at 90°. No example values were saved (all inputs were 0), so the golden tests
evaluate these formulas by hand at chosen angles.

**Other sheets:** "Dashboard" (shape buttons, a "Calculator Types" label), "Calculators
Backend" (empty), and "Admin" (a `tblResetValues` table listing cells to reset to 0).

**VBA:** `Workbook_Open` shows a splash form, and dashboard shapes open other forms.
`ResetWorkbook` loops over `tblResetValues`. `formBasicCalculator` is a four-function
calculator adapted from a third-party example (**not reused**). `formNon90DegreeBends`
was an empty stub.

## Reuse inventory

| Asset | Reuse? | Notes |
|---|---|---|
| Formulas and example values | **Yes** | Transcribed above, implemented as `course` methods, pinned by golden tests |
| Calculator list and UX ideas (splash, about, dashboard, "reset to defaults") | **Yes, as ideas** | The GUI keeps last-used values per calculator. A reset button is on the roadmap. |
| VBA code | No | Excel-specific. The basic calculator is third-party. |
| The workbook files themselves, images, icons, and other assets | No (kept local) | Not redistributable (ADR-0008). Formulas and facts are transcribed instead. |
