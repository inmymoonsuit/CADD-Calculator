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
from caddcalc.core.errors import SpecError
from caddcalc.core.i18n import NP_
from caddcalc.core.units.model import (
    Derivation,
    Dimension,
    DimensionSpec,
    Exact,
    Precision,
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
    names: tuple[str, str],
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
    """Declare a built-in unit, citing SP 811 at ``locator``, and 24 FR 5348 if ``primary``.

    Its ``names``, singular and plural, are US English, the source language, marked with
    ``NP_`` in the "unit" context; they're translated where they're shown (ADR-0019 U5).
    """
    source = cite(f"sp811_{symbol or 'one'}", SP_811, locator)
    name, plural = names
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


LENGTH, ANGLE, RATIO, STRESS, AREA = (
    Dimension.LENGTH,
    Dimension.ANGLE,
    Dimension.RATIO,
    Dimension.STRESS,
    Dimension.AREA,
)
SI, ACCEPTED, US, NONE = (
    UnitSystem.SI,
    UnitSystem.ACCEPTED,
    UnitSystem.US_CUSTOMARY,
    UnitSystem.NONE,
)

DIMENSIONS = (
    DimensionSpec(LENGTH, "a length", "mm", Precision(4), follows_length=True),
    DimensionSpec(ANGLE, "an angle", "deg", Precision(2)),
    DimensionSpec(RATIO, "a ratio", "", Precision(4)),
    DimensionSpec(STRESS, "a stress", "MPa", Precision(1), shown_with={US: "ksi"}),
    DimensionSpec(
        AREA,
        "an area",
        "mm²",
        Precision(6, significant=True),
        follows_length=True,
        derivation=Derivation(LENGTH, 2),
    ),
)
"""Every dimension. A stress follows the length choice: ksi beside inches or feet, MPa
otherwise (ADR-0005, amendments). An area is the square of the length choice, in² beside
inches (ADR-0018 §3), to six significant figures. An angle shows in degrees, a ratio as a
number."""


def _square(
    root: Unit,
    symbol: str,
    names: tuple[str, str],
    locator: str,
    *,
    aliases: tuple[str, ...],
) -> Unit:
    """Declare the square of the length unit ``root``, in exact arithmetic (ADR-0019 §2).

    Its factor is ``root``'s exact factor squared, so the square foot is 92 903.04 mm²
    exactly, which ``304.8**2`` misses by a unit in the last place. ``symbol`` is how SP
    811 writes it, in² (§6.1.8 refuses "sq in"), and the forms people type, such as
    ``in^2``, ``in2`` and ``sq in``, are aliases, read but never written.
    """
    if root.exact is None:
        raise SpecError(f"unit {root.symbol!r} has no exact factor to square")
    exact = root.exact**2
    source = cite(f"sp811_{root.symbol}2", SP_811, locator)
    name, plural = names
    typed = (f"{root.symbol}^2", f"{root.symbol}2", f"sq {root.symbol}")
    return Unit(
        symbol,
        name,
        AREA,
        float(exact),  # the exact definition, rounded once
        (*typed, *aliases),
        plural,
        exact=exact,
        system=root.system,
        sources=(source, *root.sources[1:]),
        power_of=root.symbol,
    )


UNITS: tuple[Unit, ...] = (
    _unit(
        "mm",
        NP_("unit", "millimeter", "millimeters"),
        LENGTH,
        Fraction(1),
        SI,
        "Table 1 (meter) and Table 5 (milli)",
        aliases=("millimeter", "millimeters", "millimetre", "millimetres"),
    ),
    _unit(
        "cm",
        NP_("unit", "centimeter", "centimeters"),
        LENGTH,
        Fraction(10),
        SI,
        "Table 1 (meter) and Table 5 (centi)",
        aliases=("centimeter", "centimeters", "centimetre", "centimetres"),
    ),
    _unit(
        "m",
        NP_("unit", "meter", "meters"),
        LENGTH,
        Fraction(1000),
        SI,
        "Table 1 (meter)",
        aliases=("meter", "meters", "metre", "metres"),
    ),
    _unit(
        "in",
        NP_("unit", "inch", "inches"),
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
        NP_("unit", "foot", "feet"),
        LENGTH,
        12 * INCH_MM,
        US,
        "Appendix B.8 (foot to meter)",
        aliases=("'", "′", "foot", "feet"),
        primary=True,
    ),
    _unit(
        "deg",
        NP_("unit", "degree", "degrees"),
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
        NP_("unit", "radian", "radians"),
        ANGLE,
        RADIAN_DEG,
        SI,
        "Table 3 (radian)",
        aliases=("radian", "radians"),
    ),
    _unit("", ("ratio", ""), RATIO, Fraction(1), NONE, "§7.10 (the unit one)"),
    _unit(
        "%",
        NP_("unit", "percent", "percent"),
        RATIO,
        Fraction(1, 100),
        NONE,
        "§7.10.2 (%)",
        aliases=("percent", "per cent"),
    ),
    _unit(
        "MPa",
        NP_("unit", "megapascal", "megapascals"),
        STRESS,
        Fraction(1),
        SI,
        "Table 3 (pascal) and Table 5 (mega)",
        aliases=("megapascal", "megapascals"),
    ),
    _unit(
        "kPa",
        NP_("unit", "kilopascal", "kilopascals"),
        STRESS,
        Fraction(1, 1000),
        SI,
        "Table 3 (pascal) and Table 5 (kilo)",
        aliases=("kilopascal", "kilopascals"),
    ),
    _unit(
        "GPa",
        NP_("unit", "gigapascal", "gigapascals"),
        STRESS,
        Fraction(1000),
        SI,
        "Table 3 (pascal) and Table 5 (giga)",
        aliases=("gigapascal", "gigapascals"),
    ),
    _unit(
        "psi",
        NP_("unit", "pound per square inch", "pounds per square inch"),
        STRESS,
        PSI_MPA,
        US,
        "Appendix B.8: pound (avoirdupois), footnote 22; pound-force, footnote 23; "
        "acceleration of free fall, standard",
        primary=True,
    ),
    _unit(
        "ksi",
        NP_("unit", "kip per square inch", "kips per square inch"),
        STRESS,
        1000 * PSI_MPA,
        US,
        "Appendix B.8: pound (avoirdupois), footnote 22; pound-force, footnote 23; "
        "acceleration of free fall, standard; kip (1 kip = 1000 lbf)",
        primary=True,
    ),
    _unit(
        "arcmin",
        NP_("unit", "minute", "minutes"),
        ANGLE,
        Fraction(1, 60),
        ACCEPTED,
        "Table 6 (minute), §7.2",
        aliases=("′", "'", "arcminute", "arcminutes", "minute", "minutes"),
        written="′",
        close_up=True,
    ),
    _unit(
        "arcsec",
        NP_("unit", "second", "seconds"),
        ANGLE,
        Fraction(1, 3600),
        ACCEPTED,
        "Table 6 (second), §7.2",
        aliases=("″", '"', "arcsecond", "arcseconds", "second", "seconds"),
        written="″",
        close_up=True,
    ),
)
"""The built-in units, in the order they've always been listed, then the minute and second
of arc, which share ′ and ″ with the foot and inch (SP 811 Table 6): a unit of the
expected dimension wins (ADR-0019 §3). The squares follow."""

_ROOTS = {unit.symbol: unit for unit in UNITS}

SQUARES: tuple[Unit, ...] = (
    _square(
        _ROOTS["mm"],
        "mm²",
        NP_("unit", "square millimeter", "square millimeters"),
        "Table 2 (area: square meter) and Table 5 (milli)",
        aliases=(
            "square millimeter",
            "square millimeters",
            "square millimetre",
            "square millimetres",
        ),
    ),
    _square(
        _ROOTS["cm"],
        "cm²",
        NP_("unit", "square centimeter", "square centimeters"),
        "Table 2 (area: square meter) and Table 5 (centi)",
        aliases=(
            "square centimeter",
            "square centimeters",
            "square centimetre",
            "square centimetres",
        ),
    ),
    _square(
        _ROOTS["m"],
        "m²",
        NP_("unit", "square meter", "square meters"),
        "Table 2 (area: square meter)",
        aliases=("square meter", "square meters", "square metre", "square metres"),
    ),
    _square(
        _ROOTS["in"],
        "in²",
        NP_("unit", "square inch", "square inches"),
        "Appendix B.8 (square inch to square meter)",
        aliases=("square inch", "square inches"),
    ),
    _square(
        _ROOTS["ft"],
        "ft²",
        NP_("unit", "square foot", "square feet"),
        "Appendix B.8 (square foot to square meter)",
        aliases=("square foot", "square feet"),
    ),
)
"""The squares of the length units, generated from them (ADR-0018 §3, ADR-0019 §2)."""

UNITS += SQUARES
