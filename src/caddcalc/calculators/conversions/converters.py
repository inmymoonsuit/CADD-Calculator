"""The Length, Angle, Area, and Stress converters (ADR-0018 §3).

Each takes one value typed in any unit of its kind, and shows it in every unit of that
kind at once, each row an output fixed in its unit (``Output.unit``) or written in a
compound form (``Output.form``). A row is the value itself, so it adds no work
(``Context.given``); the units registry converts it, from the units' exact definitions
in NIST SP 811, rounding once (ADR-0019 §2). Only a value that isn't finite is refused:
zero passes, and so does a sign, which is an offset, a compression, or a direction.
"""

from __future__ import annotations

from typing import ClassVar, override

from caddcalc.calculators.conversions.domain import DOMAIN
from caddcalc.core import (
    N_,
    Calculator,
    Context,
    Dimension,
    Method,
    Output,
    Param,
    Reference,
    Verification,
)
from caddcalc.core.units import Precision, to_base
from caddcalc.core.units.compound import nearest_inches

LENGTH, ANGLE, AREA, STRESS = (
    Dimension.LENGTH,
    Dimension.ANGLE,
    Dimension.AREA,
    Dimension.STRESS,
)

SP811 = "NIST Special Publication 811, 2008 Edition"
SP811_URL = "https://www.nist.gov/pml/special-publication-811"
SP811_B8 = Reference(
    SP811,
    "Appendix B.8, Factors for Units Listed Alphabetically",
    url=SP811_URL,
)
SP811_SI = Reference(
    SP811,
    "Table 1 (meter), Table 3 (radian, pascal), and Table 5 (SI prefixes)",
    url=SP811_URL,
)
SP811_TABLE_6 = Reference(
    SP811,
    "Table 6, units accepted for use with the SI: the degree, minute, and second",
    url=SP811_URL,
)
FR_1959 = Reference(
    "Refinement of Values for the Yard and the Pound, 24 FR 5348 (July 1, 1959)",
    "the inch and the pound, exactly",
    url="https://www.govinfo.gov/app/details/FR-1959-07-01",
)

ROWS_NOTE = (
    "Each row is the value in its unit, converted from the units' exact definitions and "
    "rounded once, to six significant figures; Copy gives what's shown, and full precision "
    "ten digits."
)


def _method(scope: str, note: str, *references: Reference) -> Method:
    """The converter's one method: its units' exact definitions, verified for ``scope``."""
    return Method(
        "exact",
        "Exact definitions",
        "Each row is the value in its unit, from the units' exact definitions",
        Verification.VERIFIED,
        references=references,
        notes=(ROWS_NOTE,),
        scope=scope,
        verification_note=note,
    )


def _value(dimension: Dimension, label: str, default: str, examples: str) -> Param:
    """The converter's one input: any finite value, of any sign, in any unit."""
    return Param(
        "value",
        "X",
        label,
        dimension,
        default=default,
        help=f"Type it in any unit, such as {examples}. Zero and negative values convert too.",
    )


def _rows(dimension: Dimension, *rows: tuple[str, str, str]) -> tuple[Output, ...]:
    """Outputs fixed in a unit each, from (key, unit symbol, label)."""
    return tuple(Output(key, unit, label, dimension, unit=unit) for key, unit, label in rows)


class _Converter(Calculator):
    """A converter: every row but the computed ones is the value, shown in its unit."""

    computed: ClassVar[tuple[str, ...]] = ()
    """The outputs ``compute`` works out itself rather than give the value."""

    @override
    def compute(self, ctx: Context) -> None:
        for output in self.outputs:
            if output.key not in self.computed:
                ctx.given("X", output=output.key)


FRACTIONS = (16, 32, 64)
"""The inch fractions a length is shown to the nearest of, each with its error."""


class LengthConverter(_Converter):
    """A length in inches, feet, millimeters, centimeters, meters, and feet and inches."""

    id = "conversions.length"
    name = N_("Length")
    domain = DOMAIN.id
    summary = N_(
        "A length in inches, feet, millimeters, centimeters, meters, and feet and inches, "
        "and to the nearest 1/16, 1/32, and 1/64 inch, each with its error."
    )
    params = (_value(LENGTH, "Length", "1 in", "3/16 in, 5 mm, or 1'-4 3/16\""),)
    outputs = (
        *_rows(
            LENGTH,
            ("in", "in", "Inches"),
            ("ft", "ft", "Feet"),
            ("mm", "mm", "Millimeters"),
            ("cm", "cm", "Centimeters"),
            ("m", "m", "Meters"),
        ),
        Output("ft_in", "ft-in", "Feet and inches", LENGTH, form="ft_in"),
        *(
            row
            for denominator in FRACTIONS
            for row in (
                Output(
                    f"nearest_{denominator}",
                    f"N{denominator}",
                    f"Nearest 1/{denominator} inch",
                    LENGTH,
                    form=f"in_{denominator}",
                ),
                Output(
                    f"error_{denominator}",
                    f"E{denominator}",
                    f"Error of the nearest 1/{denominator}",
                    LENGTH,
                    "The nearest fraction less the value: positive where the fraction is longer.",
                    unit="in",
                    precision=Precision(6),
                ),
            )
        ),
    )
    computed = tuple(f"{kind}_{d}" for d in FRACTIONS for kind in ("nearest", "error"))
    methods = (
        _method(
            "for in and ft",
            "Verified against NIST SP 811, Appendix B.8, which gives the inch and the foot "
            "in meters exactly.",
            SP811_B8,
            SP811_SI,
            FR_1959,
        ),
    )

    @override
    def compute(self, ctx: Context) -> None:
        super().compute(ctx)
        for denominator in FRACTIONS:
            # As the parser builds a length typed in inches, so a value typed in inches as
            # this very fraction has an error of exactly 0, not a rounding's worth.
            nearest = to_base(float(nearest_inches(ctx["value"], denominator)), "in")
            ctx.record(
                f"N{denominator}",
                nearest,
                label=f"Nearest 1/{denominator} inch",
                dimension=LENGTH,
                note=f"The value rounded to the nearest 1/{denominator} inch, half to even.",
                output=f"nearest_{denominator}",
            )
            ctx.calc(
                f"E{denominator}",
                f"N{denominator} - X",
                label=f"Error of the nearest 1/{denominator}",
                dimension=LENGTH,
                output=f"error_{denominator}",
            )


class AngleConverter(_Converter):
    """An angle in degrees, radians, and degrees, minutes and seconds."""

    id = "conversions.angle"
    name = N_("Angle")
    domain = DOMAIN.id
    summary = N_("An angle in degrees, radians, and degrees, minutes, and seconds.")
    params = (_value(ANGLE, "Angle", "1 deg", "30°, 1 rad, or 40°30′15″"),)
    outputs = (
        *_rows(ANGLE, ("deg", "deg", "Degrees"), ("rad", "rad", "Radians")),
        Output("dms", "DMS", "Degrees, minutes, and seconds", ANGLE, form="dms"),
    )
    methods = (
        _method(
            "for the degree",
            "Verified against NIST SP 811, Appendix B.8, which gives the degree in radians, "
            "to its printed digits.",
            SP811_TABLE_6,
            SP811_SI,
            SP811_B8,
        ),
    )


class AreaConverter(_Converter):
    """An area in square inches, feet, millimeters, centimeters, and meters."""

    id = "conversions.area"
    name = N_("Area")
    domain = DOMAIN.id
    summary = N_(
        "An area in square inches, square feet, square millimeters, square centimeters, "
        "and square meters."
    )
    params = (_value(AREA, "Area", "1 ft²", "3 sq in, 2 ft², or 500 mm²"),)
    outputs = _rows(
        AREA,
        ("in2", "in²", "Square inches"),
        ("ft2", "ft²", "Square feet"),
        ("mm2", "mm²", "Square millimeters"),
        ("cm2", "cm²", "Square centimeters"),
        ("m2", "m²", "Square meters"),
    )
    methods = (
        _method(
            "for in² and ft²",
            "Verified against NIST SP 811, Appendix B.8, which gives the square inch and the "
            "square foot in square meters exactly.",
            SP811_B8,
            SP811_SI,
            FR_1959,
        ),
    )


class StressConverter(_Converter):
    """A stress or pressure in psi, ksi, kPa, and MPa."""

    id = "conversions.stress"
    name = N_("Stress and pressure")
    domain = DOMAIN.id
    summary = N_("A stress or pressure in psi, ksi, kPa, and MPa.")
    params = (_value(STRESS, "Stress or pressure", "1 psi", "36 ksi, 250 MPa, or 14 psi"),)
    outputs = _rows(
        STRESS,
        ("psi", "psi", "Pounds per square inch"),
        ("ksi", "ksi", "Kips per square inch"),
        ("kpa", "kPa", "Kilopascals"),
        ("mpa", "MPa", "Megapascals"),
    )
    methods = (
        _method(
            "for psi and ksi",
            "Verified against NIST SP 811, Appendix B.8, which gives the pound-force per "
            "square inch and the kip per square inch in pascals, to its printed digits. "
            "The factors here come from the exact pound, inch, and standard free fall, "
            "since B.8 rounds them.",
            SP811_B8,
            SP811_SI,
            FR_1959,
        ),
    )
