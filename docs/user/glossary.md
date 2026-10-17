# Glossary

**Air bending**: press-brake bending in which the sheet touches only the punch tip and
the two die shoulders. The inside radius depends mostly on the die opening, not the punch.

**Bend allowance (BA)**: the arc length of the neutral axis through a bend: the flat
length the bend "uses".

**Bend angle (A)**: the angle the material is bent *through*, measured from flat.
A 90° bend makes a square corner. Some sources use the *included angle* instead, the angle
between the flanges, which is 180° − A. This app always uses the bend angle.

**Bend deduction (BD)**: `2·OSSB − BA`. Subtract it from the sum of outside flange
dimensions to get the flat length.

**Family settings**: values set once for a family of calculators and shared by them.
Sheet Metal's are thickness (T), inside radius (R), and K-factor (K); see
[Family settings](calculators/sheet-metal.md#family-settings) for which calculators and
methods use each. An unset setting leaves each calculator its own default.

**Flat pattern dimension (FPD)**: a length measured on the flat blank before bending.

**Formed view dimension (FVD)**: a dimension on the formed part, measured to the outside of
the material in this app.

**Inside radius (R)**: the radius of the inside surface of the bend.

**K-factor (K)**: where the neutral axis sits, as a fraction of the thickness measured from
the inside surface. Cited starting values are about 0.35 to 0.45 (FAA, Machinery's
Handbook, and the textbook's 0.4), approaching 0.5 for large R/T; see
[materials-data-sources.md](../dev/research/materials-data-sources.md#4-neutral-axis-k-factor),
§4. It is best measured from a test bend in your own shop.

**Mold line (OML / IML)**: the line made by extending a flange's flat surface past the
bend radius. The outside surface gives the outside mold line (OML), and the inside surface
gives the inside mold line (IML) (*Engineering Drawing and Design*, Ch. 19).

**Mold point / virtual sharp**: where two mold lines intersect, the corner a perfectly
sharp bend would have. A *mold-line dimension* is measured to the mold point. This app
measures outside dimensions to the outside mold point. These are standard aircraft
sheet-metal layout terms; the FAA's *Aviation Maintenance Technician Handbook – Airframe*
(FAA-H-8083-31, sheet-metal layout chapter) is a public-domain source for them.

**Neutral axis**: the layer inside the material that neither stretches nor compresses
when bent.

**Outside setback (OSSB)**: the distance from the bend's tangent line to the mold point,
`tan(A/2)·(R + T)`. At 90° this is just `R + T`.

**Thickness (T)**: the sheet thickness. Gauge numbers map to thicknesses through tables
that depend on the material **and the gauge system**. For example, 12 ga is 0.1046 in in
Manufacturers' Standard Gauge for steel sheet, but other tables list 0.1093 in. Always name
the system.

**Truncated cone (frustum)**: a cone with its tip cut off parallel to the base. Its flat
pattern is an annular sector.

**V-die opening (V, FDO)**: the width of the V in the bottom (female) die.
