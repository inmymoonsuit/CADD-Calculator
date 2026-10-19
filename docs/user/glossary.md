# Glossary

**Across corners**: a regular polygon's size across two opposite corners: the diameter of
its circumscribed circle, 2R. With an odd number of sides, no two corners are opposite.

**Across flats**: a regular polygon's size across two parallel flats: the diameter of its
inscribed circle, 2r. With an odd number of sides there are no parallel flats, so a
caliper held from a flat to the opposite corner reads r + R instead.

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
the inside surface. Cited starting values are 0.445 for aircraft aluminum (FAA), about
0.408 to 0.452 by material (*Machinery's Handbook*), and the textbook's 0.4.
Mid-thickness, 0.5, is often assumed (FAA); see
[materials-data-sources.md](../dev/research/materials-data-sources.md#4-neutral-axis-k-factor),
§4. It is best measured from a test bend in your own shop. The **Fixed K-factor
(≈ 0.41)** method is the course's formula, 0.64T + 1.57R: K fixed at about 0.408, with
π/2 rounded to 1.57.

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
Manufacturers' Standard Gauge for steel sheet, 0.109375 in in US Standard 1893 (some tables
print 0.1093), and 0.0808 in in AWG. Always name the system; the Sheet Metal page's gauge
picker makes you choose one.

**Truncated cone (frustum)**: a cone with its tip cut off parallel to the base. Its flat
pattern is an annular sector.

**V-die opening (V, FDO)**: the width of the V in the bottom (female) die.

**Sagitta (h)**: the rise of an arc: the distance from the middle of its chord to the arc,
at right angles to the chord.
