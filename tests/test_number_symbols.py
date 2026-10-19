"""Numbers in the user's regional format: on screen, typed, and copied (ADR-0020 §4)."""

from __future__ import annotations

import re

import pytest

from caddcalc.calculators import default_registry
from caddcalc.calculators.sheet_metal.domain import DOMAIN
from caddcalc.core import Calculator, DomainSettings, Result
from caddcalc.core.errors import InputError, UsageError
from caddcalc.core.formatting import (
    POINT,
    CopyForm,
    DisplayPrefs,
    NumberSymbols,
    ShownUnits,
    copy_output,
    describe_error,
    entry_text,
    field_text,
    format_value,
    render_step,
    results_tsv,
    typeset,
    value_parts,
)
from caddcalc.core.provenance import InputSource, SourceKind
from caddcalc.core.spec import OutOfRangeError
from caddcalc.core.units import Dimension, TypedValue, get_unit, parse_quantity

COMMA = NumberSymbols(",")
IN_COMMA = DisplayPrefs(symbols=COMMA)
IN = ShownUnits.generated("in")
INCH = 25.4
LENGTH, ANGLE, RATIO = Dimension.LENGTH, Dimension.ANGLE, Dimension.RATIO


def _bend() -> tuple[Calculator, Result]:
    """Bend allowance with the course method and its example: BA = 0.3119 in."""
    calc = default_registry(load_plugins=False).get("sheet_metal.bend_allowance")
    return calc, calc.run(method="course")


@pytest.mark.parametrize("mark", ["", "..", "1", "-", "+", "−", " "])
def test_a_decimal_mark_is_one_character_but_a_digit_sign_or_space(mark: str) -> None:
    with pytest.raises(UsageError, match="decimal mark"):
        NumberSymbols(mark)


def test_numbers_on_screen_take_the_locales_decimal_mark() -> None:
    assert value_parts(0.3119 * INCH, LENGTH, IN, IN_COMMA).number == "0,3119"
    assert format_value(0.3119 * INCH, LENGTH, IN, IN_COMMA) == "0,3119 in"
    assert format_value(-0.25 * INCH, LENGTH, IN, IN_COMMA) == "-0,2500 in", "an ASCII minus"
    assert format_value(132.7, ANGLE, IN, IN_COMMA) == "132,70°"
    assert format_value(0.44, RATIO, IN, IN_COMMA) == "0,4400"
    assert format_value(1234.5 * INCH, LENGTH, IN, IN_COMMA) == "1234,5000 in", "no grouping"
    assert field_text(2.65684, get_unit("mm"), IN_COMMA) == "2,65684"
    assert field_text(25.4, get_unit("in"), IN_COMMA) == "1", "no mark when there are no decimals"


def test_work_is_typeset_in_the_locales_mark_and_its_note_left_as_written() -> None:
    _calc, result = _bend()
    for step in result.steps:
        point = render_step(step, result, IN, DisplayPrefs())
        comma = render_step(step, result, IN, IN_COMMA)
        assert comma[1:] == tuple(
            None if line is None else typeset(line, COMMA) for line in point[1:]
        )
        lines = [line for line in comma[1:] if line is not None]
        assert not any(re.search(r"\d\.\d", line) for line in lines), lines
    first = render_step(result.steps[0], result, IN, IN_COMMA)
    assert first[0] == "(0,64·T + 1,57·R)·A/90" and first[2] == "0,3119 in"


@pytest.mark.parametrize(
    ("math", "comma"),
    [
        ("max(2.5 - 0.0625, 0)", "max(2,5 - 0,0625; 0)"),
        ("π/180·A·(R + K·T)", "π/180·A·(R + K·T)"),
        ("0.1046 in = 2.6568 mm", "0,1046 in = 2,6568 mm"),
        ("-0.25", "-0,25"),
    ],
)
def test_math_is_typeset_number_by_number(math: str, comma: str) -> None:
    """A function's arguments are split with ";" where "," is the decimal mark."""
    assert typeset(math, COMMA) == comma
    assert typeset(math, POINT) == math
    assert typeset(math, NumberSymbols("٫")) == math.replace(".", "٫"), "Arabic"


def test_copy_writes_a_point_and_copy_all_and_the_shown_form_the_locales_mark() -> None:
    """Ctrl+C pastes into CAD, which reads a comma between coordinates (ADR-0020 §4)."""
    calc, result = _bend()
    output = calc.outputs[0]
    value = result.outputs[output.key]
    assert copy_output(output, value, IN, IN_COMMA, CopyForm.VALUE) == "0.3119"
    assert copy_output(output, value, IN, IN_COMMA, CopyForm.WITH_UNIT) == "0.3119 in"
    assert "," not in copy_output(output, value, IN, IN_COMMA, CopyForm.FULL)
    assert copy_output(output, value, IN, IN_COMMA, CopyForm.SHOWN) == "0,3119"
    assert copy_output(output, value, IN, DisplayPrefs(), CopyForm.SHOWN) == "0.3119"
    rows = results_tsv(calc, result, IN, IN_COMMA)
    assert rows.splitlines()[0] == "BA\tBend allowance\t0,3119\tin"


def test_a_range_errors_bound_is_shown_in_the_locales_mark() -> None:
    calc, _result = _bend()
    thickness = calc.params[0]
    error = OutOfRangeError(
        thickness, 1.0, bound=0.5 * INCH, above=True, source=InputSource(SourceKind.EXPLICIT)
    )
    assert "0,5 in" in describe_error(error, IN, IN_COMMA)
    assert "0.5 in" in describe_error(error, IN, DisplayPrefs())


@pytest.mark.parametrize(
    ("text", "decimal", "value"),
    [
        ("0,0625", ",", 0.0625),
        ("0.0625", ",", 0.0625),
        ("1.234", ",", 1.234),
        ("1,234", ",", 1.234),
        ("1.234", ".", 1.234),
        ("−2", ".", -2.0),
        ("−0,5", ",", -0.5),
        ("1-1/2", ",", 1.5),
        ("1e3", ".", 1000.0),
    ],
)
def test_typing_takes_the_locales_mark_and_a_point(text: str, decimal: str, value: float) -> None:
    """A point always reads, so "1.234" is 1.234 in every locale: digits aren't grouped."""
    assert parse_quantity(text, RATIO, decimal=decimal) == pytest.approx(value)


@pytest.mark.parametrize(
    ("text", "decimal", "message"),
    [
        ("1,5", ".", "has a comma, which isn't a decimal mark here: the decimal mark is '.'"),
        ("1.234,5", ",", "more than one decimal mark"),
        ("1,2,3", ",", "more than one decimal mark"),
        ("1_000", ".", "digits aren't grouped"),
        ("1_000", ",", "digits aren't grouped"),
    ],
)
def test_a_comma_that_isnt_the_mark_or_grouping_is_refused(
    text: str, decimal: str, message: str
) -> None:
    """In en_US, "1,5" is an error, never 15 (ADR-0020 §4)."""
    with pytest.raises(InputError, match=re.escape(message)):
        parse_quantity(text, RATIO, decimal=decimal)


def test_a_typed_value_keeps_the_mark_it_was_read_with() -> None:
    typed = TypedValue.parse("0,0625 in", LENGTH, decimal=",")
    assert (typed.decimal, typed.value) == (",", pytest.approx(0.0625 * INCH))
    with pytest.raises(UsageError, match=r"is not a value"):
        TypedValue(typed.value, typed.text, typed.unit, typed.explicit_unit)


def test_a_field_shows_the_users_text_as_typed_and_the_apps_in_the_locales_mark() -> None:
    """Text the app writes, such as a default, follows the locale (ADR-0020 §4)."""
    inch = get_unit("in")
    default = TypedValue.parse("0.0625", LENGTH, "in")
    assert entry_text(default, inch, IN_COMMA) == "0,0625"
    assert entry_text(default, inch, DisplayPrefs()) == "0.0625"
    stated = TypedValue.parse("1.5875 mm", LENGTH)
    assert entry_text(stated, inch, IN_COMMA) == "0,0625", "the field's unit, in the locale's mark"
    for typed in ("0.0625", "0,0625"):
        entry = TypedValue.parse(typed, LENGTH, "in", decimal=",")
        assert entry_text(entry, inch, IN_COMMA) == typed


def test_a_family_setting_reads_the_locales_mark() -> None:
    settings = DomainSettings().set_text(DOMAIN, "thickness", "0,0625", "in", decimal=",")
    entry = settings.get(DOMAIN, "thickness")
    assert entry is not None and entry.value == pytest.approx(0.0625 * INCH)
