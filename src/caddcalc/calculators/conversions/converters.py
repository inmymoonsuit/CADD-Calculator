"""The unit converters, one value in and one out (ADR-0018 §3, split by ADR-0024 §7).

They're Length, Fraction to decimal, Decimal to fraction, Angle, Area, and Stress and
pressure. Each unit-to-unit converter takes one value, in its input's picked unit, and gives it as
one output, ``value``, in its own picker's unit (``Output.picks``). Until that's picked,
it's the counterpart of the input's unit in the other system, in → mm and mm → in
(``Output.follows``, ADR-0024 §6). The output is the value itself, so it adds no work
(``Context.given``). The typed value was read through its unit's factor, as every value
is, and is shown converted on to the picked unit, from the units' factors, each its
exact definition in NIST SP 811 rounded once (ADR-0019 §2). Only a value that isn't
finite, or that would overflow in the smallest unit it can be shown in, is refused:
zero passes, and so does a sign, which is an offset, a compression, or a direction.
Decimal to fraction gives a length's nearest inch fraction, to a fineness picked as an
input, and the fraction's error.
"""

from __future__ import annotations

import math
import sys
from typing import override

from caddcalc.calculators.conversions.domain import DOMAIN
from caddcalc.core import (
    N_,
    Calculator,
    Context,
    Dimension,
    InputError,
    Method,
    Output,
    Param,
    Reference,
    Verification,
)
from caddcalc.core.units import Precision, from_base, to_base
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

VALUE_NOTE = (
    "The value as typed, read through its unit's factor, converted to the picked unit, each "
    "factor its unit's exact definition rounded once. It shows six significant figures; "
    "Copy gives what's shown, and full precision ten digits."
)
FIGURES = Precision(6, significant=True)
"""A converted value's figures, whatever its size: as the converters' rows had them."""


def _method(scope: str, note: str, *references: Reference) -> Method:
    """The converter's one method: its units' exact definitions, verified for ``scope``."""
    return Method(
        "exact",
        "Exact definitions",
        "The value in the picked unit, from the units' exact definitions",
        Verification.VERIFIED,
        references=references,
        notes=(VALUE_NOTE,),
        scope=scope,
        verification_note=note,
    )


def _value(
    dimension: Dimension, label: str, default: str, examples: str, *, unit: str = ""
) -> Param:
    """The converter's input: any finite value, of any sign, in its picked unit."""
    return Param(
        "value",
        "X",
        label,
        dimension,
        default=default,
        unit=unit,
        help=f"Pick its unit, then type it, such as {examples}. Zero and negative values "
        "convert too.",
    )


def _converted(
    dimension: Dimension, label: str, picks: tuple[str, ...], counterparts: dict[str, str]
) -> Output:
    """The converter's output: the value, in its own picker's unit (ADR-0024 §7)."""
    return Output(
        "value",
        "Y",
        label,
        dimension,
        picks=picks,
        precision=FIGURES,
        follows="value" if counterparts else "",
        counterparts=counterparts,
    )


class _Converter(Calculator):
    """A unit-to-unit converter: its one output is its one input, shown in another unit."""

    @override
    def compute(self, ctx: Context) -> None:
        _refuse_overflow(ctx["value"], self.outputs[0].picks)
        ctx.given("X", output="value")


def _refuse_overflow(value: float, units: tuple[str, ...]) -> None:
    """Refuse a value that would overflow in one of ``units``, as psi does beside MPa.

    It's refused, never shown as inf (ADR-0018, amendments). A form is shown in its full
    unit, which is checked with the units.

    Raises:
        InputError: The value is too large to show in the smallest unit.
    """
    shown = [u for u in units if not u.startswith(("in_", "ft_in", "dms"))]
    if any(not math.isfinite(from_base(value, unit)) for unit in shown):
        smallest = min(shown, key=lambda unit: to_base(1, unit))
        raise InputError(
            f"This value is too large to show in {smallest}: its size must be under "
            f"{sys.float_info.max:.6g} {smallest}."
        )


LENGTHS = ("in", "ft_in", "ft", "mm", "cm", "m")
"""The units and forms a converted length is shown in, decimal and feet and inches."""
LENGTH_COUNTERPARTS = {"in": "mm", "ft_in": "mm", "ft": "m", "mm": "in", "cm": "in", "m": "ft"}
"""Each length's counterpart in the other system (ADR-0024 §6)."""
LENGTH_METHOD = _method(
    "for in and ft",
    "Verified against NIST SP 811, Appendix B.8, which gives the inch and the foot "
    "in meters exactly.",
    SP811_B8,
    SP811_SI,
    FR_1959,
)


class LengthConverter(_Converter):
    """A length, in any length unit or in feet and inches."""

    id = "conversions.length"
    name = N_("Length")
    domain = DOMAIN.id
    summary = N_(
        "A length in another unit: inches, feet, millimeters, centimeters, meters, or feet "
        "and inches."
    )
    params = (_value(LENGTH, "Length", "1 in", "3/16 in, 5 mm, or 1'-4 3/16\""),)
    outputs = (_converted(LENGTH, "Converted length", LENGTHS, LENGTH_COUNTERPARTS),)
    methods = (LENGTH_METHOD,)


class FractionToDecimal(_Converter):
    """A fraction of an inch, or of any length unit, as a decimal (ADR-0024 D6)."""

    id = "conversions.fraction_to_decimal"
    name = N_("Fraction to decimal")
    domain = DOMAIN.id
    summary = N_("A fraction, such as 3/16 or 1 3/16 inches, as a decimal, in any length unit.")
    params = (_value(LENGTH, "Fraction", "3/16 in", "3/16, 1 3/16, or 1-3/16", unit="in"),)
    outputs = (_converted(LENGTH, "Decimal", ("in", "ft", "mm", "cm", "m"), {}),)
    methods = (LENGTH_METHOD,)


FINENESS = ((16.0, "1/16"), (32.0, "1/32"), (64.0, "1/64"))
"""The inch fractions a length is shown to the nearest of."""


class DecimalToFraction(Calculator):
    """A length as its nearest fraction of an inch, to a fineness, with its error."""

    id = "conversions.decimal_to_fraction"
    name = N_("Decimal to fraction")
    domain = DOMAIN.id
    summary = N_("A length as its nearest 1/16, 1/32, or 1/64 inch, with the fraction's error.")
    params = (
        _value(LENGTH, "Length", "0.19 in", "a decimal in inches or millimeters"),
        Param(
            "fineness",
            "F",
            "Fineness",
            Dimension.COUNT,
            default="16",
            allowed=FINENESS,
            help="The fraction of an inch to round to: 1/16, 1/32, or 1/64.",
        ),
    )
    outputs = (
        Output(
            "nearest",
            "N",
            "Nearest fraction",
            LENGTH,
            "The length rounded to the nearest fraction of an inch at the fineness, half to even.",
            form="in_64",
        ),
        Output(
            "error",
            "E",
            "Error",
            LENGTH,
            "The nearest fraction less the length: positive where the fraction is longer.",
            signed=True,
        ),
    )
    methods = (
        _method(
            "for in and ft",
            "Verified against NIST SP 811, Appendix B.8, which gives the inch and the foot "
            "in meters exactly. The rounding to the nearest fraction, half to even, is this "
            "calculator's own rule; no published example covers it.",
            SP811_B8,
            SP811_SI,
            FR_1959,
        ),
    )

    @override
    def compute(self, ctx: Context) -> None:
        _refuse_overflow(ctx["value"], ("in",))
        denominator = round(ctx["fineness"])
        # As the parser builds a length typed in inches, so a value typed in inches as
        # this very fraction has an error of exactly 0, not a rounding's worth.
        nearest = to_base(float(nearest_inches(ctx["value"], denominator)), "in")
        if abs(nearest - ctx["value"]) <= math.ulp(ctx["value"]):
            # Within the value's own last place, as 411.1625 mm is of 16 3/16 in, the
            # fraction is the value, so its error is 0 (ADR-0018, amendments).
            nearest = ctx["value"]
        ctx.record(
            "N",
            nearest,
            label="Nearest fraction",
            dimension=LENGTH,
            note=f"The length rounded to the nearest 1/{denominator} inch, half to even.",
            output="nearest",
        )
        ctx.calc("E", "N - X", label="Error", dimension=LENGTH, output="error")


class AngleConverter(_Converter):
    """An angle, in degrees, minutes and seconds, or radians."""

    id = "conversions.angle"
    name = N_("Angle")
    domain = DOMAIN.id
    summary = N_("An angle in another unit: degrees, radians, or degrees, minutes, and seconds.")
    params = (_value(ANGLE, "Angle", "1 deg", "30°, 1 rad, or 40°30′15″"),)
    outputs = (
        _converted(
            ANGLE,
            "Converted angle",
            ("deg", "dms", "arcmin", "arcsec", "rad"),
            {"deg": "rad", "dms": "rad", "arcmin": "rad", "arcsec": "rad", "rad": "deg"},
        ),
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
    """An area, in square inches, feet, millimeters, centimeters, or meters."""

    id = "conversions.area"
    name = N_("Area")
    domain = DOMAIN.id
    summary = N_(
        "An area in another unit: square inches, square feet, square millimeters, square "
        "centimeters, or square meters."
    )
    params = (_value(AREA, "Area", "1 ft²", "3 sq in, 2 ft², or 500 mm²"),)
    outputs = (
        _converted(
            AREA,
            "Converted area",
            ("in²", "ft²", "mm²", "cm²", "m²"),
            {"in²": "mm²", "ft²": "m²", "mm²": "in²", "cm²": "in²", "m²": "ft²"},
        ),
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
    """A stress or pressure, in psi, ksi, kPa, MPa, or GPa."""

    id = "conversions.stress"
    name = N_("Stress and pressure")
    domain = DOMAIN.id
    summary = N_("A stress or pressure in another unit: psi, ksi, kPa, MPa, or GPa.")
    params = (_value(STRESS, "Stress or pressure", "1 psi", "36 ksi, 250 MPa, or 14 psi"),)
    outputs = (
        _converted(
            STRESS,
            "Converted stress or pressure",
            ("psi", "ksi", "kPa", "MPa", "GPa"),
            {"psi": "kPa", "ksi": "MPa", "kPa": "psi", "MPa": "ksi", "GPa": "ksi"},
        ),
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
