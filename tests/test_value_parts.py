"""Values shown in parts, copied, and tabulated (core.formatting; ADR-0005)."""

from __future__ import annotations

from itertools import product

import pytest

from caddcalc.core import Calculator, Context, Method, Output, Param, Verification
from caddcalc.core.formatting import (
    CopyForm,
    DisplayPrefs,
    ValueParts,
    copy_text,
    display_value,
    format_number,
    format_value,
    results_tsv,
    to_fraction,
    unit_suffix,
    value_parts,
)
from caddcalc.core.units import Dimension, get_unit

L, A, R, S = Dimension.LENGTH, Dimension.ANGLE, Dimension.RATIO, Dimension.STRESS


def _decimals(dimension: Dimension, prefs: DisplayPrefs) -> int:
    if dimension is A:
        return prefs.angle_decimals
    if dimension is S:
        return prefs.stress_decimals
    return prefs.decimals


def format_value_as_it_was(
    value: float, dimension: Dimension, prefs: DisplayPrefs, *, unit: bool = True
) -> str:
    """``format_value`` before it was built on ``value_parts``, kept to hold it identical."""
    shown = display_value(value, dimension, prefs)
    text = format_number(shown, _decimals(dimension, prefs))
    if unit:
        text += unit_suffix(dimension, prefs)
    if (
        unit
        and dimension is L
        and prefs.fraction_denominator
        and get_unit(prefs.length_unit).symbol == "in"
    ):
        text += f'  (≈ {to_fraction(shown, prefs.fraction_denominator)}")'
    return text


VALUES = (0.0, -0.0, 1e-9, -1e-9, -0.00001, 0.5, 7.9223, -3.75, 25.4, 1234.5678, 1e6)
PREFS = [
    DisplayPrefs(length, decimals, angle, stress, fraction)
    for length, decimals, angle, stress, fraction in product(
        ("in", "mm", "ft", "cm", "m"), (0, 2, 4), (1, 2), (0, 1), (None, 16, 64)
    )
]


def test_format_value_is_unchanged_by_being_built_on_value_parts() -> None:
    differ = [
        (value, dimension, prefs, unit)
        for value, dimension, prefs, unit in product(VALUES, (L, A, R, S), PREFS, (True, False))
        if format_value(value, dimension, prefs, unit=unit)
        != format_value_as_it_was(value, dimension, prefs, unit=unit)
    ]
    assert differ == []


@pytest.mark.parametrize(
    ("value", "dimension", "prefs", "parts"),
    [
        (7.9223, L, DisplayPrefs(), ValueParts("0.3119", "in")),
        (7.9223, L, DisplayPrefs(fraction_denominator=64), ValueParts("0.3119", "in", "5/16")),
        (
            7.9223,
            L,
            DisplayPrefs(length_unit="mm", fraction_denominator=64),
            ValueParts("7.9223", "mm"),
        ),
        (120.0, A, DisplayPrefs(), ValueParts("120.00", "°")),
        (0.44, R, DisplayPrefs(), ValueParts("0.4400", "")),
        (275.8, S, DisplayPrefs(), ValueParts("40.0", "ksi")),
        (275.8, S, DisplayPrefs(length_unit="mm"), ValueParts("275.8", "MPa")),
        (-0.00001, L, DisplayPrefs(), ValueParts("0.0000", "in")),
    ],
)
def test_a_value_is_shown_in_parts(
    value: float, dimension: Dimension, prefs: DisplayPrefs, parts: ValueParts
) -> None:
    assert value_parts(value, dimension, prefs) == parts


def test_the_unit_joins_spaced_except_a_degree_sign() -> None:
    assert ValueParts("0.3119", "in").with_unit == "0.3119 in"
    assert ValueParts("120.00", "°").with_unit == "120.00°"
    assert ValueParts("0.4400", "").with_unit == "0.4400"
    close_up = {unit: ValueParts("1", unit).unit_close_up for unit in ("in", "°", "", "ksi")}
    assert close_up == {"in": False, "°": True, "": False, "ksi": False}


@pytest.mark.parametrize(
    ("value", "dimension", "prefs", "copied"),
    [
        (7.9223, L, DisplayPrefs(fraction_denominator=64), ("0.3119", "0.3119 in", "0.3119015748")),
        (-1.0668, L, DisplayPrefs(), ("-0.0420", "-0.0420 in", "-0.042")),
        (120.0, A, DisplayPrefs(), ("120.00", "120.00°", "120")),
        (0.44, R, DisplayPrefs(), ("0.4400", "0.4400", "0.44")),
        (-0.0, L, DisplayPrefs(), ("0.0000", "0.0000 in", "0")),
        (-1e-12, L, DisplayPrefs(length_unit="mm"), ("0.0000", "0.0000 mm", "-0.000000000001")),
        (
            1e9,
            L,
            DisplayPrefs(length_unit="mm"),
            ("1000000000.0000", "1000000000.0000 mm", "1000000000"),
        ),
    ],
)
def test_copying_writes_plain_decimals_in_each_form(
    value: float, dimension: Dimension, prefs: DisplayPrefs, copied: tuple[str, str, str]
) -> None:
    forms = (CopyForm.VALUE, CopyForm.WITH_UNIT, CopyForm.FULL)
    assert tuple(copy_text(value, dimension, prefs, form) for form in forms) == copied


def test_full_precision_rounds_to_ten_significant_digits_without_an_exponent() -> None:
    prefs = DisplayPrefs(length_unit="mm")
    assert copy_text(1 / 3, L, prefs, CopyForm.FULL) == "0.3333333333"
    assert copy_text(123456789012.5, L, prefs, CopyForm.FULL) == "123456789000"
    assert copy_text(2.5e-12, L, prefs, CopyForm.FULL) == "0.0000000000025"
    for value in (1e-30, 1e30, -7e-15):
        text = copy_text(value, L, prefs, CopyForm.FULL)
        assert "e" not in text.lower() and float(text) == pytest.approx(value, rel=1e-9)


def test_no_copy_carries_the_fraction() -> None:
    prefs = DisplayPrefs(fraction_denominator=64)
    for form in CopyForm:
        assert "/" not in copy_text(7.9223, L, prefs, form)


class _Bracket(Calculator):
    id = "test.bracket"
    name = "Bracket"
    domain = "test"
    summary = "A test calculator whose labels hold a tab and a line break."
    params = (Param("length", "X", "Length", L, default="1 in", minimum=0.0),)
    outputs = (
        Output("half", "H", "Half\tof it", L),
        Output("angle", "θ", "Angle,\nshown", A),
    )
    methods = (Method("only", "Only", "H = X/2", Verification.UNVERIFIED),)

    def compute(self, ctx: Context) -> None:
        ctx.calc("H", "X/2", label="Half", dimension=L, output="half")
        ctx.calc("θ", "30", label="Angle", dimension=A, output="angle")


def test_results_tabulate_one_row_per_output_without_breaking_cells() -> None:
    result = _Bracket().run()
    assert results_tsv(_Bracket(), result, DisplayPrefs()) == (
        "H\tHalf of it\t0.5000\tin\nθ\tAngle, shown\t30.00\t°\n"
    )
    assert results_tsv(_Bracket(), result, DisplayPrefs(length_unit="mm")).startswith(
        "H\tHalf of it\t12.7000\tmm\n"
    )


def test_a_fraction_that_rounds_to_zero_is_never_negative() -> None:
    assert to_fraction(-0.001, 64) == "0"
    assert to_fraction(-0.5, 64) == "-1/2" and to_fraction(-1.015625, 64) == "-1-1/64"
    prefs = DisplayPrefs(fraction_denominator=64)
    assert format_value(-0.00001, L, prefs) == '0.0000 in  (≈ 0")'
    assert value_parts(-0.00001, L, prefs).fraction == "0"
