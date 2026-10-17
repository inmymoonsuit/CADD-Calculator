# Sheet-metal calculators

Conventions for every sheet-metal calculator:

* **Bend angle (A)** is measured *from flat*. 0° means no bend and 90° is a square bend.
  It is not the included angle between the flanges.
* **Formed dimensions are to the outside** of the material (the outside mold line).
* Defaults reproduce the course examples: T = 0.1046 in (12 ga, Manufacturers' Standard
  Gauge for steel sheet) and R = 0.156 in. The K-factor defaults to 0.4, the textbook's
  instructional value.

## Family settings

Select **Sheet Metal** in the calculator list to open its settings page. These are the
values the sheet-metal calculators share, so you can set them once for the whole
family. An empty field means the setting is unset, and each calculator uses its own
default. **Clear all** unsets every one. Settings last until you close the app; nothing
is saved.

| Setting | Used by |
|---|---|
| Material thickness (T) | Bend allowance & deduction; Flat length of a formed segment; Truncated cone flat pattern; V-die opening, 8 × thickness method |
| Inside bend radius (R) | Bend allowance & deduction; Flat length of a formed segment; V-die opening, inside-radius percentage method |
| K-factor (K) | The K-factor methods of Bend allowance & deduction and Flat length of a formed segment |

* **Thickness:** enter the decimal thickness. Gauge numbers mean different thicknesses in
  different gauge systems (see *Thickness* in the [glossary](../glossary.md)).
* **K-factor:** typically 0.3 to 0.5. Use your shop's test-bend value for production.
  The course methods have their factor built in, so they don't use this setting.
* The V-die calculator's die ratio P is not shared; each calculation sets its own.

The settings page shows the same list under each field. In this build it keeps the
values for the session, but the calculators don't use them yet; that comes with each
field's *Use Sheet Metal value* switch.

---

## Bend allowance & deduction: `sheet_metal.bend_allowance`

The bend allowance (BA) is the length of the neutral axis through the bend: how much flat
material the bend consumes. The outside setback (OSSB) is the distance from where the bend
starts to the virtual sharp. The bend deduction (BD) is what you subtract from the sum of
outside flange dimensions.

| Method | Formula | Status |
|---|---|---|
| Course formula | BA = (0.64·T + 1.57·R)·A/90 | unverified · reproduces legacy |
| K-factor | BA = (π/180)·A·(R + K·T) (Engineering Drawing and Design, Ch. 19) | unverified |

Both methods then compute:

* OSSB = tan(A/2)·(R + T)
* BD = 2·OSSB − BA

The course formula is *Machinery's Handbook* (29th ed.) Eq. (33). It is for 90° bends in
half-hard copper and brass, soft steel, and aluminum, and is scaled by A/90 for other angles.
It equals the K-factor formula with K ≈ 0.408. For other materials, or for production work,
use the K-factor method with your shop's measured K.

**Course example:** T = 0.1046, R = 0.156, A = 90° gives BA = 0.311864 in.

## Flat length of a formed segment: `sheet_metal.segment_flat_length`

This is the flat-pattern length of one segment of a part, dimensioned to the outside
(FVD), with a bend at one or both ends. Set **A2 = 0°** if only one end is bent.

FPD = FVD − OSSB₁ − OSSB₂ + BA₁/2 + BA₂/2

> **Bends past 90°:** this calculator measures outside dimensions to the virtual sharp.
> Some drawings (for example *Engineering Drawing and Design*, Fig. 19.11b) dimension such
> bends to the tangent of the outside arc instead, which gives a different result. Check how
> your drawing is dimensioned (KI-013).

To get a whole part, add the FPDs of its segments. A whole-part calculator is planned.

**Course examples:** with FVD = 1.12 in, one 90° bend gives FPD = 1.015332 in and two 90°
bends give FPD = 0.910664 in.

## V-die opening (air bending): `sheet_metal.v_die_opening`

| Method | Formula | Status |
|---|---|---|
| Inside-radius percentage rule | V = R / P | unverified · reproduces legacy |
| 8 × thickness | V = 8·T | unverified |

In air bending, the inside radius forms at roughly a fixed fraction **P** of the die
opening. The course used **P = 0.156**, a mild-steel value. P varies by material, so check
your tooling supplier's data.

## Truncated cone flat pattern: `sheet_metal.truncated_cone_layout`

This is the layout of a cone frustum as an annular sector: inside radius FPIR, outside
radius FPOR, and sweep angle FPA.

| Method | Status | Notes |
|---|---|---|
| Course spreadsheet | unverified · reproduces legacy | The radii use the diameters as given, while the angle uses (Db − T). See below. |
| Mean diameter | unverified | Treats the diameters as outside diameters and develops the mid-thickness surface throughout |

Course method:

* CH = √(((Db − Dt)/2)² + H²)
* FPIR = CH·(Dt/2)/((Db − Dt)/2)
* FPOR = FPIR + CH
* FPA = 180·(Db − T)/FPOR

> **Note:** for the course example (6 in to 10 in, 5 in tall, 0.0747 in thick), the course
> method gives FPA = 132.70° and the mean-diameter method gives 133.70°. That is 0.235 in of
> arc at the outside edge. A cone's sweep angle is the same on every parallel surface,
> 360·((Db − Dt)/2)/CH (*Engineering Drawing and Design*, Ch. 23), so no choice of inside,
> outside, or mean surface gives 132.70°. `course` reproduces the coursework;
> `mean_diameter` develops the mid-surface from outside diameters. Check the first part
> with a paper template.
