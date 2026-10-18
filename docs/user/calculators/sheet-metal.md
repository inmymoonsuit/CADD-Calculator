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
default. **Clear all** unsets every one, and returns any choice the family offers to its
default. Settings last until you close the app; nothing is saved.

A value applies when you press Enter or leave the field. As you type, text that can't be
used is outlined in red and explained. It isn't applied, so the setting keeps the value
it had, and the text stays, with its explanation, until you fix it or clear the field.
If you switch units meanwhile, a number typed without a unit gains the unit you typed it
in, so "5" becomes "5 in" and keeps its meaning.

In the table, a calculator named alone uses the setting in every method; otherwise the
methods that use it follow the colon.

| Setting | Used by |
|---|---|
| Material thickness (T) | Bend allowance & deduction; Flat length of a formed segment; Truncated cone flat pattern; V-die opening (air bending): 8 × thickness rule of thumb |
| Inside bend radius (R) | Bend allowance & deduction; Flat length of a formed segment; V-die opening (air bending): Inside-radius percentage rule |
| K-factor (K) | Bend allowance & deduction: K-factor (neutral axis); Flat length of a formed segment: K-factor (neutral axis) |

* **Thickness:** enter the decimal thickness, or choose a gauge (below). Gauge numbers
  mean different thicknesses in different gauge systems (see *Thickness* in the
  [glossary](../glossary.md)).
* **K-factor:** cited starting values are 0.445 for aircraft aluminum (FAA-H-8083-31B,
  p. 4-63); about 0.408 for aluminum and soft steel and 0.452 for cold-rolled steel,
  implied by *Machinery's Handbook* (31st ed., p. 1421, Eqs (33) and (34)); and the
  textbook's 0.4. The neutral axis is often assumed to be at mid-thickness, 0.5
  (FAA-H-8083-31B, p. 4-59). Use your shop's test-bend value for production. The course
  methods have their factor built in, so they don't use this setting.
* The V-die calculator's die ratio P is not shared; each calculation sets its own.

The settings page shows the same list under each field.

### Choosing a gauge

The **Gauge** row picks a gauge system, then a gauge number in it. No gauge is chosen
until you pick one, so by default you type the decimal thickness.

| System | Gauges | Stated to |
|---|---|---|
| Manufacturers' Standard, steel sheet | 3 to 38 | 4 decimal places |
| Galvanized, coated steel sheet | 8 to 34 | 4 decimal places |
| US Standard 1893, as commonly used for stainless; practice varies | 7/0 to 38 | the statute's exact decimals |
| AWG (Brown & Sharpe), nonferrous | 4/0 to 40 | 4 decimal places, 5 below 0.0100 in |

* The boxes change by click or keyboard, not by the mouse wheel, so scrolling past
  them can't change the gauge.
* **Name the system, always.** 12 ga is 0.1046 in in Manufacturers' Standard, 0.1084 in
  galvanized, 0.109375 in in US Standard, and 0.0808 in in AWG. A gauge number alone
  can't be chosen, and changing the system clears the number.
* **The thickness follows the gauge.** Choosing 12 ga Manufacturers' Standard makes the
  thickness 0.1046 in for every calculator that shares it. The field shows it in grey,
  and under it the page shows where it comes from, a caution, and the work, e.g.
  T = (w + c) / 16 / B = (70 + 0) / 16 / 41.82 = 0.1046 in, which is 0.1046150167… in
  before rounding to the system's published 4 decimal places.
* **A thickness you type takes precedence.** Typing a thickness in the field overrides
  the gauge; clearing the field returns to the gauge's value.
* **The caution.** A gauge thickness is nominal: mills roll to a tolerance. Every result
  that uses one carries a note such as "Nominal thickness; mill tolerances apply (see
  ASTM A568/A568M, 2025, rev. a). Check the material's specification or measure before
  cutting." Each system points to its own tolerance standard.
* Each value comes from a cited definition: the 1893 gauge statute (15 U.S.C. §206),
  NBS Circular 391, and one fact from *Machinery's Handbook*. Results name the table,
  "Gauge systems, version 3". To report a value that looks wrong, see
  [Reporting a wrong value](#reporting-a-wrong-value).

### Choosing a material

The **Material** row picks a group, then a material: aluminum 5052 or 6061; mild
cold-rolled (ASTM A1008 CS), galvanized (ASTM A653), or hot-rolled pickled and oiled
(ASTM A1011) carbon steel; or 304 stainless, annealed (2B finish). The **Temper** row
then offers that material's tempers: 5052 comes in H32, 6061 in T6, 304 annealed, and
each carbon steel as supplied, each selected as soon as you pick the material. If you
change the material, its own temper is selected, and a temper you chose that the new
material doesn't come in is reset, with a notice.

* **A material sets no value.** The thickness, inside radius, and K-factor stay as you
  set them; nothing about a result's numbers changes when you pick one.
* The material's data, with every value cited, is in the table "Sheet-metal materials,
  version 1".

### What the page shows about a material

Under the Temper row, **Facts** shows, for the chosen material and temper:

* **Minimum inside radius:** which sources its bends are checked against, the thicknesses
  each lists, any stand-in label, and each source's scope. Galvanized and hot-rolled steel
  say why they have none.
* **Bending practice:** form across the grain where possible, and bend a test piece first.
* **Strength:** the tensile strengths, ultimate (F_tu) and yield (F_ty), along (L) and
  across (LT) the rolling direction, with their basis and source. They show in ksi when
  the unit system is `in`, and MPa when it's `mm`.

### K-factor starting values

For a material with a cited K-factor, buttons under the **K-factor** field offer it:
FAA-H-8083-31B's 0.445 for the aluminums, and *Engineering Drawing and Design*'s 0.4 for
aluminum, mild steel, and 304. Clicking one sets the family K-factor to that value, as
your own setting, but keeps its source: the field's help names it, results list K as a
"starting value from …", and every result that uses it carries a note to confirm it with
a test bend. Typing your own K-factor drops the citation and the note. *Machinery's
Handbook*'s values are given in the field's help, to type yourself.

### The minimum-radius check

With a material chosen, *Bend allowance & deduction* and *Flat length of a formed
segment* check the inside radius against the material's cited minimum bend radius. Each
note names its sources and how far each applies.

* **What the minimums are.** They are the recommended minimums of aircraft-repair (FAA AC
  43.13-1B) and USAF/NAVAIR (TO 1-1A-9) practice, for bends up to 90°. Press-brake
  production can differ with tooling, grain direction, and the material lot, so make a
  test bend before production.

* **Limit exceeded** when the inside radius is below the minimum. Where sources differ,
  the larger minimum applies and every source is shown: 6061-T6 is checked against both
  AC 43.13-1B and TO 1-1A-9. A range, such as AC 43.13's ½T–1T, is checked at its upper
  bound and shown whole.
* **Between listed thicknesses** a sheet within 2% of a listed thickness reads at it, so
  0.063 in reads at 0.064 in; otherwise it reads at the next thickness listed above it.
  Nothing is interpolated.
* **No applicable value** is said aloud, never left silent: for a thickness no source
  lists (TO's stainless table has none between 0.090 and 0.190 in, and mild steel stops
  at 0.187 in), for a bend past 90° or a hem, and for galvanized and hot-rolled steel,
  which have no public-domain source. Where only one source lists the thickness, the note
  says the check uses it alone. A part with bends on both sides of 90° is still checked
  for its bends up to 90°; only those past 90° get the no-applicable-value note.
* **Stand-ins are labelled.** Mild steel uses TO's 2T for 1020/1025, and 304 annealed uses
  TO's 2T for 304 ½ Hard, its only 304 row; both are conservative.
* When the inside radius is below the minimum, a second note gives TO's bending
  practice: form across the grain where possible, and bend a test piece first.
* **The rule of thumb.** Without a material, or where no source applies, an inside radius
  below the thickness still gets the warning "Inside radius is smaller than the material
  thickness". A cited check replaces it, so the two never disagree.
* **The gauge and the material.** A gauge from a system the material isn't ordered by,
  such as Manufacturers' Standard (steel sheet) with aluminum, gets a warning that names
  both and suggests entering the decimal thickness. It applies only while the thickness
  in use is the gauge's.
* **On a calculator's page,** a limit-exceeded note shows in red, and the fields it
  concerns are outlined in red; a field no source could check gets a dashed grey
  outline. A field several notes concern takes the strongest outline.

### Using a family value in a calculator

* Once a Sheet Metal value is set, each calculator field that shares it shows the value
  and a ticked **Use Sheet Metal value** box. The field is read-only while the box is
  ticked, and the result lists the value as *Sheet Metal settings*.
* A gauge's thickness works the same way. The result lists it by its gauge, e.g.
  *12 ga, Manufacturers' Standard, steel sheet (nominal), Gauge systems, version 3*,
  carries the caution, and shows the gauge's work before the calculator's own.
* To give one calculator its own value, **untick the box**. The field keeps an exact
  copy of the family value, so nothing changes until you edit it; the result lists it
  as *copied from Sheet Metal settings*, and as *entered* once you type a new value.
  The override lasts for the session, even if the family value changes later; the
  copy is then listed as *copied earlier from Sheet Metal settings*. A copy of a gauge's
  thickness is listed as *copied from 12 ga, Manufacturers' Standard, steel sheet
  (nominal), …*, and keeps the caution until you type a new value.
* While a field overrides a set value, a note under it shows both values, e.g.
  "Sheet Metal value is 0.2500 in; this calculator uses 0.1046 in." Tick the box to
  use the family value again. The settings page shows how many calculators override
  each setting, and which.
* A value that's unset in the family leaves each calculator its own default, and its
  fields work as ordinary inputs. Results follow your typing, but an edit counts only
  when it ends: when you press Enter, leave the field, or switch page or units. An edit
  that ends on the value already in use, or on text that can't be read, changes
  nothing, so retyping a value never gives the calculator an override.
* Text that can't be read is outlined in red and explained, and stays, through page
  and unit switches, until you fix it or clear the field. If the field starts using a
  family value meanwhile, the text is discarded and a note says so. Clearing a field
  returns it to the calculator's default, shown in grey as, e.g., "default 0.1046".
* **Load course example** fills the course method's inputs with the course example,
  overrides the family values, and switches to the course method, so the lesson's
  numbers come out exactly. Inputs the course doesn't use, such as K, are left exactly
  as they were. The result lists the course values as *course example*. For example, with
  thickness set to 0.1046 in, the cone's course method gives a 132.30° sweep; loading
  the course example restores its 0.0747 in and the lesson's 132.70°.

---

## Bend allowance & deduction: `sheet_metal.bend_allowance`

The bend allowance (BA) is the length of the neutral axis through the bend: how much flat
material the bend consumes. The outside setback (OSSB) is the distance from where the bend
starts to the virtual sharp. The bend deduction (BD) is what you subtract from the sum of
outside flange dimensions.

| Method | Formula | Status |
|---|---|---|
| Fixed K-factor (≈ 0.41) | BA = (0.64·T + 1.57·R)·A/90 | verified for BA · reproduces legacy |
| K-factor | BA = (π/180)·A·(R + K·T) (Engineering Drawing and Design, Ch. 19) | verified for BA at 90° |

Each is verified against a published worked example: the fixed K-factor against
*Machinery's Handbook* (31st ed.) Fig. 13, p. 1421, a soft-steel part's bend allowances,
and the K-factor at 90° against *Engineering Drawing and Design* (5th ed.) Fig. 19.12,
p. 785. Both examples check the bend allowance, not the setback or the deduction, so the
status says "for BA". Rest the pointer on the status to see its source.

Both methods then compute:

* OSSB = tan(A/2)·(R + T)
* BD = 2·OSSB − BA

The fixed K-factor is the formula taught in the original coursework, *Machinery's
Handbook* (31st ed.) Eq. (33), p. 1421: the neutral-axis arc with K fixed at about 0.408
and π/2 rounded to 1.57. It is for 90° bends in half-hard copper and brass, soft steel,
and aluminum, and is scaled by A/90 for other angles. The Handbook's Eqs (32) and (34)
are the same arc with K about 0.35 and 0.45. With K = 0.4074 the K-factor method gives
the same T term and a radius term 0.05% larger, so the two can differ in the fourth
decimal. For other materials, or for production work, use the K-factor method with your
shop's measured K.

**Course example:** T = 0.1046, R = 0.156, A = 90° gives BA = 0.311864 in.

## Flat length of a formed segment: `sheet_metal.segment_flat_length`

This is the flat-pattern length of one segment of a part, dimensioned to the outside
(FVD), with a bend at one or both ends. Set **A2 = 0°** if only one end is bent.

FPD = FVD − OSSB₁ − OSSB₂ + BA₁/2 + BA₂/2

| Method | BA | Status |
|---|---|---|
| Fixed K-factor (≈ 0.41) | as in Bend allowance & deduction | unverified · reproduces legacy |
| K-factor | as in Bend allowance & deduction | verified at 90° |

The K-factor is verified at 90° against *Engineering Drawing and Design* (5th ed.)
Fig. 19.12, p. 785, a part with one bend. The fixed K-factor is verified for a bend
allowance (above), but no published worked example checks a segment's flat length with it.

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
| Course spreadsheet | unverified · reproduces legacy | The radii use the diameters as given, while the angle uses (Db − T). See below. Refuses a bottom diameter no larger than the thickness, which would give a sweep of 0° or less |
| Mean diameter | unverified | Treats the diameters as outside diameters and develops the mid-thickness surface throughout. Refuses a top diameter (other than 0, a pointed cone) or a bottom diameter no larger than the thickness, which leave no mid-surface |

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

## Reporting a wrong value

Every reference value, such as a gauge thickness, cites its source, and a result names the
table it came from. If a value looks wrong, or you believe it can't be redistributed,
please report it with the [*Reference value* issue template](https://github.com/inmymoonsuit/CADD-Calculator/issues/new?template=reference_value.md); see
[Reporting a wrong or rights-encumbered value](../../../CONTRIBUTING.md#reporting-a-wrong-or-rights-encumbered-value).
We fix or remove a reported value promptly.

