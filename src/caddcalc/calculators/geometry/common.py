"""Citations and shared pieces of the Geometry calculators (ADR-0018 §2).

Every method cites *Machinery's Handbook*, 31st ed. (MH31), Mathematics, by section and
printed page, and the triangles also the NIST DLMF. The *Pocket Companion* is a "see
also" for students, never the source of record. Constants come from ``math.pi`` and
``math.radians`` (through ``ctx.calc``'s ``pi`` and degree trig), not the Handbook's
rounded ones.
"""

from __future__ import annotations

from caddcalc.core import Context, Dimension, InputError, Method, Param, Reference, Verification

LENGTH, ANGLE, AREA, COUNT = Dimension.LENGTH, Dimension.ANGLE, Dimension.AREA, Dimension.COUNT

LENGTH_SCALE = (1e-70, 1e70)
"""The least and greatest length a Geometry calculator works with, in mm (KI-026).

Its formulas multiply up to four lengths, as Heron's and Kahan's do, and a product of
four lengths in this range is a normal double, with room for the constant factors: a
smaller length's work underflows and loses its digits, and a larger one's overflows.
"""

MH31 = "Machinery's Handbook, 31st ed."
MH31_RECTANGLE = Reference(
    MH31, "Mathematics: Dimensions of Plane Figures, rectangle, printed p. 75"
)
MH31_TRIANGLE = Reference(
    MH31, "Mathematics: Dimensions of Plane Figures, triangles, printed p. 76"
)
MH31_CIRCLE = Reference(
    MH31, "Mathematics: Dimensions of Plane Figures, circle and circular sector, printed p. 78"
)
MH31_POLYGON = Reference(
    MH31, "Mathematics: Dimensions of Plane Figures, regular polygon, printed p. 78"
)
MH31_POLYGON_TABLE = Reference(
    MH31, "Mathematics: Polygons, Formulas and Table for Regular Polygons, printed p. 82"
)
MH31_SEGMENT = Reference(
    MH31, "Mathematics: Dimensions of Plane Figures, circular segment, printed p. 79"
)
MH31_LAW_OF_COSINES = Reference(
    MH31,
    "Mathematics: Solution of Triangles, the law of cosines, printed p. 96, which Kahan's "
    "angle formula rearranges",
)
MH31_RIGHT_TRIANGLES = Reference(
    MH31, "Mathematics: Solution of Triangles, Solution of Right Triangles, printed p. 98"
)
MH31_THREE_SIDES = Reference(
    MH31,
    "Mathematics: Solution of Oblique Triangles, All Three Sides Known, printed p. 101; its "
    "second angle, from the law of sines, isn't followed (see the method's notes)",
)
DLMF_TRIANGLES = Reference(
    "NIST Digital Library of Mathematical Functions",
    "§4.42, Solution of Triangles",
    url="https://dlmf.nist.gov/4.42",
)
KAHAN_NEEDLE = Reference(
    "W. Kahan, Miscalculating Area and Angles of a Needle-like Triangle",
    "Heron's formula with the sides sorted, longest first, and each angle from its "
    "half-angle tangent with μ as defined there (lecture notes, University of California, "
    "Berkeley)",
    url="https://people.eecs.berkeley.edu/~wkahan/Triangle.pdf",
)
POCKET = "Machinery's Handbook Pocket Companion, 32nd ed. (Industrial Press, 2024)"
POCKET_PLANE_FIGURES = Reference(
    POCKET, "see also, for students: Dimensions of Plane Figures, pp. 1-6"
)
POCKET_SEGMENTS = Reference(POCKET, "see also, for students: Segments of Circles, pp. 7-9")
POCKET_TRIANGLES = Reference(POCKET, "see also, for students: triangles, pp. 16-19")

UNVERIFIED = (
    "Not verified: no published worked example runs through this calculator in the tests "
    "yet (ADR-0010)."
)


def method(
    key: str,
    label: str,
    summary: str,
    *references: Reference,
    notes: tuple[str, ...] = (),
) -> Method:
    """Declare a Geometry method: unverified until a published example tests it."""
    return Method(
        key,
        label,
        summary,
        Verification.UNVERIFIED,
        references=references,
        notes=notes,
        verification_note=UNVERIFIED,
    )


def length(key: str, symbol: str, label: str, default: str, help: str, *methods: str) -> Param:
    """Declare a length input: finite and greater than zero (ADR-0018 §2)."""
    return Param(
        key,
        symbol,
        label,
        LENGTH,
        default=default,
        minimum=0.0,
        min_inclusive=False,
        help=help,
        methods=methods,
    )


def check_scale(ctx: Context) -> None:
    """Refuse a length the method uses outside ``LENGTH_SCALE``, whose work would be wrong.

    Raises:
        InputError: A length is too small or too large to work with.
    """
    least, greatest = LENGTH_SCALE
    for p in ctx.calculator.params_for(ctx.method):
        value = ctx[p.key]
        if p.dimension is LENGTH and not least <= value <= greatest:
            size = "small" if value < least else "large"
            raise InputError(
                f"{p.named} is too {size} to work with: Geometry lengths are from "
                f"{least:g} mm to {greatest:g} mm.".replace("e+", "e")
            )
