"""The built-in dimensions and units, each declared once with its citation (ADR-0019 §4).

Every factor is its exact definition, rounded once to the nearest double for computation
(ADR-0019 §2). Definitions that build on others are written that way, so a test can hold
them to their parts: the foot is 12 inches, and psi is a pound-force on a square inch.

NIST SP 811 (2008) predates the 2019 revision of the SI, which changes none of the
definitions cited here.
"""

from __future__ import annotations

from decimal import Decimal, localcontext
from fractions import Fraction

from caddcalc.core.citations import License, Publication, PublicationKind, cite
from caddcalc.core.units.model import (
    Dimension,
    DimensionSpec,
    Exact,
    Unit,
    UnitSystem,
)

SP_811 = Publication(
    "nist_sp811",
    PublicationKind.GOVERNMENT_DOCUMENT,
    "Guide for the Use of the International System of Units (SI), NIST Special Publication 811",
    License.PUBLIC_DOMAIN,
    edition="2008 Edition (web version 3.2, July 2008)",
    url="https://www.nist.gov/pml/special-publication-811",
    public_domain_basis=(
        "17 U.S.C. §105: a work of NIST employees (NIST Technical Series); not Standard "
        "Reference Data under 15 U.S.C. §290e"
    ),
    short_title="NIST SP 811",
)
"""The units' citation: their definitions, symbols, and factors."""

FR_1959 = Publication(
    "fr_1959_yard_pound",
    PublicationKind.GOVERNMENT_DOCUMENT,
    "Refinement of Values for the Yard and the Pound (Federal Register notice, July 1, 1959)",
    License.PUBLIC_DOMAIN,
    url="https://www.govinfo.gov/app/details/FR-1959-07-01",
    public_domain_basis=(
        "17 U.S.C. §105: a notice of the National Bureau of Standards, a work of the U.S. "
        "government"
    ),
    short_title="24 FR 5348 (July 1, 1959)",
)
"""The primary source of the inch and the pound: the yard is 0.9144 m, the pound
0.453 592 37 kg. Published July 1, 1959, in the issue govinfo holds."""

YARD_POUND = cite("fr_1959", FR_1959, "Vol. 24, No. 128, p. 5348")

INCH_MM = Fraction("25.4")
"""The inch, exactly: 0.9144 m / 36 (24 FR 5348; SP 811 Appendix B.8)."""
POUND_KG = Fraction("0.45359237")
"""The avoirdupois pound, exactly (24 FR 5348)."""
STANDARD_GRAVITY = Fraction("9.80665")
"""Standard acceleration of free fall, in m/s², exactly (SP 811 Appendix B.8). With the
pound, it defines the pound-force (B.8, footnote 23); B.8's own psi and ksi factors are
rounded, so they come from these definitions instead."""
PSI_MPA = POUND_KG * STANDARD_GRAVITY / INCH_MM**2
"""A pound-force per square inch, in N/mm², which is MPa."""

_PI = Decimal("3.14159265358979323846264338327950288419716939937510582097494459")
with localcontext() as _context:
    _context.prec = 50
    RADIAN_DEG = Decimal(180) / _PI
"""A radian, in degrees: 180/π to 50 significant digits. It's exact only symbolically,
so it's the one factor held as a decimal; it rounds to the same double as ``180/math.pi``."""


def _unit(
    symbol: str,
    name: str,
    plural: str,
    dimension: Dimension,
    exact: Exact,
    system: UnitSystem,
    locator: str,
    *,
    aliases: tuple[str, ...] = (),
    written: str = "",
    close_up: bool = False,
    fractions: bool = False,
    primary: bool = False,
) -> Unit:
    """Declare a built-in unit, citing SP 811 at ``locator``, and 24 FR 5348 if ``primary``."""
    source = cite(f"sp811_{symbol or 'one'}", SP_811, locator)
    return Unit(
        symbol,
        name,
        dimension,
        float(exact),  # the exact definition, rounded once
        aliases,
        plural,
        written=written,
        exact=exact,
        system=system,
        close_up=close_up,
        fractions=fractions,
        sources=(source, YARD_POUND) if primary else (source,),
    )


LENGTH, ANGLE, RATIO, STRESS = Dimension.LENGTH, Dimension.ANGLE, Dimension.RATIO, Dimension.STRESS
SI, ACCEPTED, US, NONE = (
    UnitSystem.SI,
    UnitSystem.ACCEPTED,
    UnitSystem.US_CUSTOMARY,
    UnitSystem.NONE,
)

DIMENSIONS = (
    DimensionSpec(LENGTH, "a length", "mm", 4, follows_length=True),
    DimensionSpec(ANGLE, "an angle", "deg", 2),
    DimensionSpec(RATIO, "a ratio", "", 4),
    DimensionSpec(STRESS, "a stress", "MPa", 1, shown_with={US: "ksi"}),
)
"""Every dimension. A stress follows the length choice: ksi beside inches or feet, MPa
otherwise (ADR-0005, amendments). An angle shows in degrees, a ratio as a number."""

UNITS: tuple[Unit, ...] = (
    _unit(
        "mm",
        "millimetre",
        "millimetres",
        LENGTH,
        Fraction(1),
        SI,
        "Table 1 (meter) and Table 5 (milli)",
        aliases=("millimeter", "millimeters", "millimetres"),
    ),
    _unit(
        "cm",
        "centimetre",
        "centimetres",
        LENGTH,
        Fraction(10),
        SI,
        "Table 1 (meter) and Table 5 (centi)",
        aliases=("centimeter", "centimeters", "centimetres"),
    ),
    _unit(
        "m",
        "metre",
        "metres",
        LENGTH,
        Fraction(1000),
        SI,
        "Table 1 (meter)",
        aliases=("meter", "meters", "metres"),
    ),
    _unit(
        "in",
        "inch",
        "inches",
        LENGTH,
        INCH_MM,
        US,
        "Appendix B.8 (inch to meter)",
        aliases=('"', "″", "inch", "inches"),
        fractions=True,
        primary=True,
    ),
    _unit(
        "ft",
        "foot",
        "feet",
        LENGTH,
        12 * INCH_MM,
        US,
        "Appendix B.8 (foot to meter)",
        aliases=("'", "′", "foot", "feet"),
        primary=True,
    ),
    _unit(
        "deg",
        "degree",
        "degrees",
        ANGLE,
        Fraction(1),
        ACCEPTED,
        "Table 6 (degree), §7.2",
        aliases=("°", "degree", "degrees"),
        written="°",
        close_up=True,
    ),
    _unit(
        "rad",
        "radian",
        "radians",
        ANGLE,
        RADIAN_DEG,
        SI,
        "Table 3 (radian)",
        aliases=("radian", "radians"),
    ),
    _unit("", "ratio", "", RATIO, Fraction(1), NONE, "§7.10 (the unit one)"),
    _unit(
        "%",
        "percent",
        "percent",
        RATIO,
        Fraction(1, 100),
        NONE,
        "§7.10.2 (%)",
        aliases=("percent",),
    ),
    _unit(
        "MPa",
        "megapascal",
        "megapascals",
        STRESS,
        Fraction(1),
        SI,
        "Table 3 (pascal) and Table 5 (mega)",
        aliases=("megapascal", "megapascals"),
    ),
    _unit(
        "kPa",
        "kilopascal",
        "kilopascals",
        STRESS,
        Fraction(1, 1000),
        SI,
        "Table 3 (pascal) and Table 5 (kilo)",
        aliases=("kilopascal", "kilopascals"),
    ),
    _unit(
        "GPa",
        "gigapascal",
        "gigapascals",
        STRESS,
        Fraction(1000),
        SI,
        "Table 3 (pascal) and Table 5 (giga)",
        aliases=("gigapascal", "gigapascals"),
    ),
    _unit(
        "psi",
        "pound per square inch",
        "pounds per square inch",
        STRESS,
        PSI_MPA,
        US,
        "Appendix B.8: pound (avoirdupois), footnote 22; pound-force, footnote 23; "
        "acceleration of free fall, standard",
        primary=True,
    ),
    _unit(
        "ksi",
        "kip per square inch",
        "kips per square inch",
        STRESS,
        1000 * PSI_MPA,
        US,
        "Appendix B.8: pound (avoirdupois), footnote 22; pound-force, footnote 23; "
        "acceleration of free fall, standard; kip (1 kip = 1000 lbf)",
        primary=True,
    ),
)
"""The built-in units, in the order they've always been listed."""
