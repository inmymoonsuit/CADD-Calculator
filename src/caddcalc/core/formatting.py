"""Turning base-unit values into display text. Rounding happens only here (ADR-0005).

It formats numbers; which unit a value is shown in, and how that unit is written, it asks
the units registry (ADR-0019 §1), so it holds no unit tables of its own.
"""

from __future__ import annotations

import math
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace
from decimal import ROUND_HALF_EVEN, Decimal
from enum import Enum
from fractions import Fraction
from types import MappingProxyType
from typing import Any

from caddcalc.core import expr
from caddcalc.core.calculator import Calculator, Result
from caddcalc.core.errors import CaddCalcError, UsageError
from caddcalc.core.i18n import N_, _
from caddcalc.core.notes import Note, NoteKind
from caddcalc.core.provenance import InputSource, SourceKind
from caddcalc.core.spec import Method, OutOfRangeError, Output, UnitSet
from caddcalc.core.steps import Step
from caddcalc.core.units import (
    BASE_UNITS,
    CompoundForm,
    CompoundText,
    Dimension,
    Precision,
    TypedValue,
    Unit,
    from_base,
    get_unit,
    registry,
)
from caddcalc.core.units.compound import (
    MEASURE_SPOKEN,
    NEGATIVE_SPOKEN,
    PARTS,
    POSITIVE_SPOKEN,
    NearestInches,
)
from caddcalc.core.units.entry import lone_fraction

# Translators: shown under every calculator's results, after the command line's results,
# and in About.
DISCLAIMER = N_(
    "Verify results and test according to your organization's policies or industry best "
    "practice before manufacturing."
)
"""The one disclaimer for every family, in the maintainer's words (ADR-0020, amendments),
marked for translation; it's translated where it's shown."""


@dataclass(frozen=True)
class NumberSymbols:
    """How the app writes a number it formats: only the decimal mark follows the locale.

    Digits stay Latin, the minus sign stays an ASCII "-", and digits are never grouped, so
    decimal alignment and pasting keep working (ADR-0020 §4). A front end takes the mark
    from the user's regional format; core never reads the process locale.

    Raises:
        UsageError: The mark is empty, longer than one character, a digit, a sign, or a
            space.
    """

    decimal: str = "."
    """The decimal mark, such as ``"."`` or ``","``."""

    def __post_init__(self) -> None:
        mark = self.decimal
        if len(mark) != 1 or mark.isdigit() or mark.isspace() or mark in "+-\u2212":
            raise UsageError(
                f"A decimal mark is one character, not a digit, sign or space: {mark!r}"
            )


POINT = NumberSymbols()
"""The "." that text read by machines always has: copies for CAD, JSON, and data files."""


@dataclass(frozen=True)
class DisplayPrefs:
    """How numbers look: their decimals and their symbols.

    Which unit or form each value is shown in is ``ShownUnits``' (ADR-0024 E4).
    """

    decimals: int = 4
    angle_decimals: int = 2
    stress_decimals: int = 1
    symbols: NumberSymbols = POINT
    """How numbers on screen are written: the locale's decimal mark (ADR-0020 §4)."""

    def precision_for(self, dimension: Dimension) -> Precision:
        """Return the precision ``dimension`` is shown with.

        That's the user's choice of decimals for it, or, for a dimension with no choice of
        its own, the precision its declaration gives (ADR-0019 §2): an area's six
        significant figures.
        """
        chosen = {
            Dimension.LENGTH: self.decimals,
            Dimension.RATIO: self.decimals,
            Dimension.ANGLE: self.angle_decimals,
            Dimension.STRESS: self.stress_decimals,
        }.get(dimension)
        return registry().dimension(dimension).precision if chosen is None else Precision(chosen)

    def decimals_for(self, dimension: Dimension) -> int:
        """Return the decimal places ``dimension`` is shown with.

        Raises:
            UsageError: ``dimension`` is shown to significant figures, as an area is.
        """
        precision = self.precision_for(dimension)
        if precision.significant:
            raise UsageError(f"{dimension.value} is shown to significant figures, not decimals")
        return precision.digits


@dataclass(frozen=True)
class ShownUnits:
    """The unit or form each value is shown in (ADR-0024 E4).

    It's a calculator's output set, resolved: a choice for every dimension, with each
    output's own pick and each input's field choice where it has one. Results stay in
    base units; they're converted only here, at presentation (ADR-0005).
    """

    choices: Mapping[Dimension, str]
    """The id of a unit or form for each dimension, e.g. ``{LENGTH: "in", AREA: "in²"}``."""
    picks: Mapping[str, str] = field(default_factory=dict)
    """The choice of each output with its own picker (``Output.picks``), by output key."""
    inputs: Mapping[str, str] = field(default_factory=dict)
    """The choice each input's field is picked in, by parameter key; an input not named
    is shown in its dimension's choice."""
    key: str = ""
    """The output set's key, e.g. ``"mm"``; empty for one not named by a set."""

    def __post_init__(self) -> None:
        missing = [d.value for d in Dimension if d not in self.choices]
        if missing:
            raise UsageError(f"ShownUnits has no choice for {', '.join(missing)}")
        for name in ("choices", "picks", "inputs"):
            object.__setattr__(self, name, MappingProxyType(dict(getattr(self, name))))

    @classmethod
    def generated(cls, length: str = "in") -> ShownUnits:
        """Return the generated output set for a length choice, e.g. ``"mm"`` or ``"ft_in"``.

        Its other dimensions follow ADR-0019 §2's rule: an area is the length's square,
        stress follows its system, and an angle is in degrees (``generated_sets``).

        Raises:
            UsageError: No generated set has that length choice.
        """
        sets = dict(registry().generated_sets())
        if length not in sets:
            raise UsageError(f"No output set for {length!r}; there's {', '.join(sets)}")
        return cls(sets[length], key=length)

    @classmethod
    def of(
        cls,
        unit_set: UnitSet,
        *,
        picks: Mapping[str, str] | None = None,
        inputs: Mapping[str, str] | None = None,
    ) -> ShownUnits:
        """Return a declared or generated set as shown, with any picks and input choices.

        A set names only the dimensions its calculator's outputs show in it, so the rest,
        such as a note's stress, take the generated set's for its length choice.
        """
        base = cls.generated(unit_set.choices.get(Dimension.LENGTH, "in")).choices
        return cls(
            {**base, **unit_set.choices}, dict(picks or {}), dict(inputs or {}), unit_set.key
        )

    def with_inputs(self, inputs: Mapping[str, str]) -> ShownUnits:
        """Return these units with each input shown in its field's choice."""
        return replace(self, inputs=dict(inputs))

    def choice(self, dimension: Dimension) -> str:
        """Return the id of the unit or form ``dimension`` is shown in."""
        return self.choices[dimension]

    def unit(self, dimension: Dimension) -> Unit:
        """Return the unit ``dimension`` is shown in, a form's full unit for a form.

        The work, notes and messages use it: a line of work reads ``= 2 × 16.1875 in``,
        never ``2 × 1'-4 3/16"`` (ADR-0024 E4).
        """
        return choice_unit(self.choice(dimension), dimension)

    def output_choice(self, output: Output) -> str:
        """Return the id an output is shown in: its fixed unit or form, its pick, or the set's.

        An output with its own picker never follows the set: until it's picked, it shows
        in its first pick (``Output.picks``).

        Raises:
            UsageError: The output is picked in a choice it doesn't offer.
        """
        if output.form or output.unit:
            return output.form or output.unit
        if not output.picks:
            return self.choice(output.dimension)
        picked = self.picks.get(output.key, output.picks[0])
        if picked not in output.picks:
            raise UsageError(
                f"Output {output.key!r} offers {', '.join(output.picks)}, not {picked!r}"
            )
        return picked

    def input_choice(self, key: str, dimension: Dimension) -> str:
        """Return the id an input is shown in: its field's choice, or the set's."""
        return self.inputs.get(key) or self.choice(dimension)


def choice_unit(choice: str, dimension: Dimension) -> Unit:
    """Return the unit of a choice, by its id: the unit itself, or a form's full unit.

    Raises:
        UsageError: ``choice`` isn't one of ``dimension``'s.
    """
    picked = registry().choice(choice, dimension)
    if isinstance(picked, CompoundForm):
        return registry().find(picked.full_unit, dimension)
    return picked


def unit_suffix(unit: Unit) -> str:
    """Return a unit as written after a value, e.g. ``" in"``, ``" ksi"``, or ``"°"``."""
    return _suffix(unit.written)


def _close_up(written: str) -> bool:
    """Whether the unit written as ``written`` goes against its number, as ``°`` does."""
    unit = registry().written(written)
    return unit is not None and unit.close_up


def _suffix(unit: str) -> str:
    """Return ``unit`` as written after a number: close up for °, spaced otherwise."""
    if _close_up(unit):
        return unit
    return f" {unit}" if unit else ""


def decimal_separator(prefs: DisplayPrefs) -> str:
    """Return the decimal mark values are shown with: the locale's (ADR-0020 §4)."""
    return prefs.symbols.decimal


def format_number(value: float, decimals: int, decimal: str = ".") -> str:
    """Return ``value`` rounded to ``decimals`` places, never as negative zero.

    Args:
        value: The number.
        decimals: Its decimal places.
        decimal: The decimal mark to write it with.
    """
    text = f"{value:.{decimals}f}"
    text = "0" + text[2:] if text.startswith("-0") and float(text) == 0 else text
    return text.replace(".", decimal)


PLAIN_EXPONENTS = (-6, 16)
"""The decimal exponents ``format_significant`` writes in plain decimals, from 10⁻⁶ up to
but not including 10¹⁶; outside them it writes an exponent."""


def format_significant(value: float, digits: int, decimal: str = ".") -> str:
    """Return ``value`` to ``digits`` significant figures, as plain decimals.

    It rounds the value's exact binary value, half to even, as ``format_number`` does,
    so 123.4575, a little under that in binary, is ``123.457`` to six. It keeps trailing
    zeros, which say how many figures are shown (``25.4000`` to six), and is never a
    negative zero. A rounding that carries into a new place keeps the count, so 9.999997
    to six is ``10.0000``. Zero is ``0.00000`` to six. A value of at least 10⁻⁶ and under
    10¹⁶ is written in plain decimals; one outside that range (``PLAIN_EXPONENTS``) is
    written with an exponent, as ``1.00000e+300``, not 301 digits.

    Args:
        value: The number.
        digits: Its significant figures, at least one.
        decimal: The decimal mark to write it with.
    """
    if not math.isfinite(value):
        return str(value)
    exact = Decimal(value)
    if not exact:
        return format_number(0.0, digits - 1, decimal)

    def rounded(adjusted: int) -> Decimal:
        step = Decimal(1).scaleb(adjusted - digits + 1)
        return exact.quantize(step, rounding=ROUND_HALF_EVEN)

    text = rounded(exact.adjusted())
    if text.adjusted() > exact.adjusted():  # the rounding carried, as 9.99 to 10.0
        text = rounded(text.adjusted())
    if not PLAIN_EXPONENTS[0] <= text.adjusted() < PLAIN_EXPONENTS[1]:
        mantissa = text.scaleb(-text.adjusted())
        written = f"{format(mantissa, 'f')}e{text.adjusted():+03d}"
        return written.replace(".", decimal)
    return format(text, "f").replace(".", decimal)


def format_precise(value: float, precision: Precision, decimal: str = ".") -> str:
    """Return ``value`` to ``precision``: decimal places, or significant figures."""
    if precision.significant:
        return format_significant(value, precision.digits, decimal)
    return format_number(value, precision.digits, decimal)


_DECIMAL_NUMBER = re.compile(r"(?<![\w.])(\d+)\.(\d+)")
"""A number with decimals, as the app writes it, never part of a longer word."""


def typeset(text: str, symbols: NumberSymbols) -> str:
    """Return math the app wrote with ``"."``, such as a line of work, in ``symbols``.

    Each number's decimal point becomes the locale's mark. Where that mark is ``","``,
    the comma between a function's arguments becomes ``";"``, as comma-locale
    spreadsheets write it, so ``max(2,5; 0)`` reads one way. Only math is typeset;
    prose, and numbers quoted from a source, are never converted (ADR-0020 §4).
    """
    mark = symbols.decimal
    if mark == ".":
        return text
    if mark == ",":
        text = text.replace(",", ";")
    return _DECIMAL_NUMBER.sub(lambda m: f"{m.group(1)}{mark}{m.group(2)}", text)


@dataclass(frozen=True)
class ValueParts:
    """A value as shown, in parts: its number and its unit, or its compound form.

    ``format_value`` joins them, so a value shown whole and a value shown in parts, such
    as a result field's, can't disagree.
    """

    number: str
    """The number, rounded in the display unit, e.g. ``"0.3119"``: an ASCII ``-`` and the
    locale's decimal mark (``DisplayPrefs.symbols``), never a negative zero."""
    unit: str
    """The unit's symbol, e.g. ``"in"``, ``"ksi"``, or ``"°"``; ``""`` for a ratio."""
    compound: CompoundText | None = None
    """The value in a compound form, when it's shown in one, e.g. feet and inches. Its
    ``number`` is then the form as shown, with no unit of its own, and it's copied and
    spoken as the form writes it."""

    @property
    def with_unit(self) -> str:
        """The number and its unit, e.g. ``"0.3119 in"`` or ``"120.00°"``."""
        return self.number + _suffix(self.unit)

    @property
    def unit_close_up(self) -> bool:
        """Whether the unit is written against the number, as ``°`` is, with no space."""
        return _close_up(self.unit)


def value_parts(
    value: float, dimension: Dimension, units: ShownUnits, prefs: DisplayPrefs
) -> ValueParts:
    """Return a base-unit value as shown in its dimension's choice, in parts (``ValueParts``).

    Args:
        value: The value in base units.
        dimension: What the value measures.
        units: The unit or form each dimension is shown in.
        prefs: The decimals, fraction preference and symbols.
    """
    return choice_parts(value, units.choice(dimension), dimension, prefs)


def choice_parts(
    value: float, choice: str, dimension: Dimension, prefs: DisplayPrefs
) -> ValueParts:
    """Return a base-unit value as shown in a unit or form, by its id, in parts.

    A unit shows the value to its dimension's precision; a form, as the form writes it.
    """
    picked = registry().choice(choice, dimension)
    if isinstance(picked, CompoundForm):
        written = picked.text(value, prefs.symbols.decimal)
        return ValueParts(written.shown, "", written)
    return unit_parts(value, picked, prefs)


def unit_parts(value: float, unit: Unit, prefs: DisplayPrefs) -> ValueParts:
    """Return a base-unit value as shown in ``unit``, in parts.

    It's to the unit's own decimals, if it declares them (``Unit.decimals``), else to its
    dimension's precision.
    """
    precision = prefs.precision_for(unit.dimension)
    if unit.decimals is not None:
        precision = Precision(unit.decimals)
    return _parts(value, unit, precision, prefs)


def input_parts(
    key: str, value: float, dimension: Dimension, units: ShownUnits, prefs: DisplayPrefs
) -> ValueParts:
    """Return an input's value as shown in its field's choice, or else the set's."""
    return choice_parts(value, units.input_choice(key, dimension), dimension, prefs)


def _parts(value: float, unit: Unit, precision: Precision, prefs: DisplayPrefs) -> ValueParts:
    """Return a base-unit value as shown in ``unit``, to ``precision``, in parts."""
    number = format_precise(from_base(value, unit), precision, prefs.symbols.decimal)
    return ValueParts(number, unit.written)


def format_value(
    value: float,
    dimension: Dimension,
    units: ShownUnits,
    prefs: DisplayPrefs,
    *,
    unit: bool = True,
) -> str:
    """Return a base-unit value as display text, e.g. ``0.3119 in``.

    Args:
        value: The value in base units.
        dimension: What the value measures.
        units: The unit or form each dimension is shown in.
        prefs: The decimals, fraction preference and symbols.
        unit: Append the unit (and the nearest fraction, when enabled).
    """
    parts = value_parts(value, dimension, units, prefs)
    return parts.with_unit if unit else parts.number


def format_input(
    key: str, value: float, dimension: Dimension, units: ShownUnits, prefs: DisplayPrefs
) -> str:
    """Return an input's value as display text, in its field's choice or else the set's."""
    return input_parts(key, value, dimension, units, prefs).with_unit


def spoken_value(parts: ValueParts) -> str:
    """Return a value as a screen reader should say it, e.g. ``"0.3119 inches"``.

    The unit is named in full, singular only after a shown ``1`` (``Unit.spoken``); a
    ratio is only its number, and a compound form is said as it says itself, e.g. "1 foot
    4 inches". A sign is said in words, by the templates compound forms use: "minus 0.3119
    inches", and "plus 0.0025 inches" where a plus sign is shown.
    """
    if parts.compound is not None:
        return parts.compound.spoken
    number, sign = parts.number, parts.number[:1]
    if sign in ("-", "+"):
        number = number[1:]
    unit = registry().written(parts.unit)
    name = "" if unit is None else unit.spoken(number)
    said = _(MEASURE_SPOKEN).format(number=number, unit=name) if name else number
    if sign == "-":
        return _(NEGATIVE_SPOKEN).format(value=said)
    return _(POSITIVE_SPOKEN).format(value=said) if sign == "+" else said


def output_unit(output: Output, units: ShownUnits) -> Unit:
    """Return the unit an output is shown in: its own, or its choice's, a form's full unit.

    An output in a compound form gives the form's full-precision unit, such as the inch
    for feet and inches.
    """
    return choice_unit(units.output_choice(output), output.dimension)


def output_parts(
    output: Output, value: float, units: ShownUnits, prefs: DisplayPrefs
) -> ValueParts:
    """Return a calculator output's value as shown, in parts.

    Every front end presents outputs through here or ``format_output``, so an output's
    own presentation applies in one place. An output with a fixed unit, as a converter's
    row has (ADR-0018 §3), is shown in it, whatever the set, to its own
    ``Output.precision`` or else the registry's precision for the unit; one with a fixed
    form, in that form; one with its own picker, in its pick; and any other in its
    dimension's choice in the set, a unit or a form (ADR-0024 E4). A signed output
    (``Output.signed``) shows a plus sign above zero; a form writes its own sign.
    """
    if output.unit:
        unit = output_unit(output, units)
        precision = output.precision or registry().precision_for(unit)
        parts = _parts(value, unit, precision, prefs)
    else:
        parts = choice_parts(value, units.output_choice(output), output.dimension, prefs)
    if output.signed and parts.compound is None:
        return replace(parts, number=_plus(parts.number))
    return parts


def _plus(number: str) -> str:
    """Return a shown number with a plus sign if it's above zero; zero, as shown, has none."""
    return f"+{number}" if number[:1] != "-" and any(c in "123456789" for c in number) else number


def format_output(output: Output, value: float, units: ShownUnits, prefs: DisplayPrefs) -> str:
    """Return a calculator output's value as display text, e.g. ``0.3119 in``."""
    return output_parts(output, value, units, prefs).with_unit


class CopyForm(Enum):
    """What copying a value puts on the clipboard (``copy_text``)."""

    VALUE = "value"
    """The number as shown, without its unit, e.g. ``0.3119``: it pastes cleanly into a
    spreadsheet cell or a CAD dimension box working in the drawing's units. Its decimal
    mark is always ``"."``, which CAD reads: AutoCAD reads a comma as the separator
    between coordinates (ADR-0020 §4)."""
    SHOWN = "shown"
    """The number exactly as shown, e.g. ``0,3119``, in the locale's decimal mark: for a
    spreadsheet set to the same locale. It's offered only where that mark isn't ``"."``."""
    WITH_UNIT = "with_unit"
    """The number as shown, with its unit, e.g. ``0.3119 in``."""
    FULL = "full"
    """The value in the unit it's shown in, a form's full unit for a form, unrounded to
    ``FULL_DIGITS`` significant digits."""


FULL_DIGITS = 10
"""Significant digits a full-precision copy keeps: far past any drafting tolerance."""


def copy_text(
    value: float, dimension: Dimension, units: ShownUnits, prefs: DisplayPrefs, form: CopyForm
) -> str:
    """Return a base-unit value as clipboard text, in ``form``.

    Every number form writes plain decimals, never an exponent, with an ASCII ``-`` and
    never a negative zero, so it pastes into a spreadsheet or a CAD input as it reads.
    Each writes ``"."`` for its decimal point, but ``SHOWN``, which writes the locale's
    mark. A value in a compound form copies as CAD takes it.
    """
    parts = value_parts(value, dimension, units, _copy_prefs(prefs, form))
    return _copied(parts, from_base(value, units.unit(dimension)), form)


def copy_output(
    output: Output, value: float, units: ShownUnits, prefs: DisplayPrefs, form: CopyForm
) -> str:
    """Return a calculator output's value as clipboard text, as ``output_parts`` shows it."""
    shown = from_base(value, output_unit(output, units))
    return _copied(output_parts(output, value, units, _copy_prefs(prefs, form)), shown, form)


def _copy_prefs(prefs: DisplayPrefs, form: CopyForm) -> DisplayPrefs:
    """Return the preferences a copy in ``form`` is written with: ``"."`` but for ``SHOWN``."""
    return prefs if form is CopyForm.SHOWN else replace(prefs, symbols=POINT)


def _copied(parts: ValueParts, shown: float, form: CopyForm) -> str:
    """Return a shown value's clipboard text in ``form``; ``shown`` is it unrounded."""
    if parts.compound is not None and form in (CopyForm.VALUE, CopyForm.WITH_UNIT):
        return parts.compound.copied  # as CAD takes it, e.g. 1'4-3/16"
    if form in (CopyForm.VALUE, CopyForm.SHOWN):
        return parts.number
    if form is CopyForm.WITH_UNIT:
        return parts.with_unit
    return _significant(shown, FULL_DIGITS)


def _significant(value: float, digits: int) -> str:
    """Return ``value`` to ``digits`` significant digits, as plain decimals."""
    if not math.isfinite(value):
        return str(value)
    exact = Decimal(value)
    if not exact:
        return "0"
    step = Decimal(1).scaleb(exact.adjusted() - digits + 1)
    text = format(exact.quantize(step, rounding=ROUND_HALF_EVEN), "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return "0" if text in ("-0", "") else text


def results_tsv(calc: Calculator, result: Result, units: ShownUnits, prefs: DisplayPrefs) -> str:
    """Return a result's outputs as tab-separated rows, for pasting into a spreadsheet.

    Each row is the output's symbol, its label, its value as shown without its unit, and
    its unit, in the calculator's output order, each row ending in a line break. A tab or
    line break inside a cell becomes a space, since tab-separated text can't escape them.
    The value has the locale's decimal mark, as a spreadsheet in that locale reads it;
    tabs separate the cells, so a comma can't break a row (ADR-0020 §4).

    A text cell that a spreadsheet would read as a formula, one starting with ``=``,
    ``+``, ``-``, or ``@`` (or their full-width forms), after any whitespace, gets a
    leading apostrophe, which spreadsheets take as "this is text" (OWASP, "CSV
    Injection"). So does one starting with ``"``, which a paste might take as the start of
    a quoted field. A tab or line break, which OWASP also lists, is already a space here.
    The value cell never gets one, since a negative number or a signed error's
    "+0.002500" must paste as a number, unless it's a compound form, such as ``-1'-4"``,
    which is text.
    """
    rows = []
    for output in calc.outputs:
        parts = output_parts(output, result.outputs[output.key], units, prefs)
        symbol, label, unit = (_text_cell(t) for t in (output.symbol, output.label, parts.unit))
        # A compound value isn't a number, so it's kept from being read as a formula too.
        value = _cell(parts.number) if parts.compound is None else _text_cell(parts.number)
        rows.append("\t".join((symbol, label, value, unit)) + "\n")
    return "".join(rows)


_CELL_BREAKS = str.maketrans({"\t": " ", "\n": " ", "\r": " "})
"""Tabs and line breaks, which a tab-separated cell can't hold."""


def _cell(text: str) -> str:
    """Return ``text`` with every tab and line break as a space, for one TSV cell."""
    return text.replace("\r\n", "\n").translate(_CELL_BREAKS)


_FORMULA_STARTS = tuple('=+-@\uff1d\uff0b\uff0d\uff20"')
"""What a spreadsheet may read a cell as a formula from: = + - @, and the full-width
forms some locales' spreadsheets take for them (OWASP, "CSV Injection"), and a quote,
which may open a quoted field."""


def _text_cell(text: str) -> str:
    """Return ``text`` as one TSV text cell, never read as a formula."""
    cell = _cell(text)
    return f"'{cell}" if cell.lstrip().startswith(_FORMULA_STARTS) else cell


FIELD_DECIMALS = 6
"""Decimal places a form field shows for a value it converted, before trailing zeros go.

Values under about 5e-7 of a display unit show as 0. That is far finer than any drafting
dimension, and more places would make every converted field long.
"""


def field_text(value: float, unit: Unit, prefs: DisplayPrefs) -> str:
    """Return a base-unit value as form-field text in ``unit``, e.g. ``2.65684``.

    It has no unit, because the field labels its unit, and no trailing zeros. Its
    decimal mark is the locale's: the app writes it into the field (ADR-0020 §4).
    """
    mark = prefs.symbols.decimal
    shown = format_number(from_base(value, unit), FIELD_DECIMALS, mark)
    return shown.rstrip("0").rstrip(mark)


def choice_text(value: float, choice: str, dimension: Dimension, prefs: DisplayPrefs) -> str:
    """Return a base-unit value as the text of a field picked in ``choice`` (ADR-0024 §2).

    In a unit it's the number alone, as ``field_text`` writes one, since the picker says
    the unit: ``2.65684`` in mm. In a form it's the form as shown, ``1'-4 3/16"``, whose
    marks the field reads as its own. Its decimal mark is the locale's.
    """
    picked = registry().choice(choice, dimension)
    mark = prefs.symbols.decimal
    if isinstance(picked, Unit):
        shown = format_number(from_base(value, picked), FIELD_DECIMALS, mark)
        return shown.rstrip("0").rstrip(mark) if mark in shown else shown
    return picked.text(value, mark).shown


def picked_text(entry: TypedValue, choice: str, prefs: DisplayPrefs) -> str:
    """Return the text a picked field shows for a value: the user's own, or converted.

    The user's own text shows while the field is picked in what it was read in, in the
    locale's mark (ADR-0024 §2). A value read otherwise, such as a family value typed
    with its unit or a default, shows converted into the field's choice.
    """
    own_mark = entry.decimal == prefs.symbols.decimal or "." not in entry.text
    if entry.choice == choice and own_mark:
        return entry.text
    return choice_text(entry.value, choice, entry.dimension, prefs)


_PLAIN = re.compile(r"[+\-−]?(?:\d+(?:[.,]\d*)?|[.,]\d+)")
"""A plain decimal, with the point or the locale's comma, which needs no echo."""


@dataclass(frozen=True)
class Echo:
    """What a picked field reads its text as, shown after it (ADR-0024 D8)."""

    text: str
    """As shown in the field, e.g. ``= 1 3/16 in`` or ``= 0'-10"``."""
    spoken: str
    """As its accessible description says it, e.g. "reads as 1 and 3 sixteenths inches"."""


def echo(entry: TypedValue, prefs: DisplayPrefs) -> Echo | None:
    """Return what a picked field's text reads as, or ``None`` for a plain decimal.

    A form shows as the form does, unless the text is already the form as shown. A lone
    fraction or mixed number shows as a mixed number, so ``1-3/16`` echoes ``= 1 3/16
    in``; any other text, such as ``1 - 3/16``, as its value, ``= 0.8125 in``.
    """
    if entry.choice is None:
        return None  # text that names its unit reads as it says
    picked = registry().choice(entry.choice, entry.dimension)
    mark = prefs.symbols.decimal
    if isinstance(picked, CompoundForm):
        written = picked.text(entry.value, mark)
        if written.shown == entry.text:
            return None
        return Echo(f"= {written.shown}", _(READS_AS).format(value=written.spoken))
    if _PLAIN.fullmatch(entry.text):
        return None
    fraction = lone_fraction(entry.text, entry.decimal)
    if fraction is not None:
        number = _mixed_text(fraction)
        words = _mixed_spoken(fraction, picked)
    else:
        number = choice_text(entry.value, entry.choice, entry.dimension, prefs)
        words = _(MEASURE_SPOKEN).format(number=number, unit=picked.spoken(number)).strip()
    return Echo(f"= {number}{_suffix(picked.written)}", _(READS_AS).format(value=words))


# Translators: a field's accessible description: what its text reads as, e.g. "reads as 1
# and 3 sixteenths inches".
READS_AS = N_("reads as {value}")


def _mixed_text(fraction: Fraction) -> str:
    """Write an exact value as a mixed number, ``1 3/16``, or a fraction, ``-3/16``."""
    sign = "-" if fraction < 0 else ""
    whole, part = divmod(abs(fraction), 1)
    if not part:
        return f"{sign}{whole}"
    written = f"{part.numerator}/{part.denominator}"
    return f"{sign}{whole} {written}" if whole else f"{sign}{written}"


def _mixed_spoken(fraction: Fraction, unit: Unit) -> str:
    """Say a mixed number of ``unit`` as its echo is said."""
    if unit.symbol == "in" and abs(fraction).denominator in PARTS:
        return NearestInches(abs(fraction).denominator).text(float(fraction) * unit.factor).spoken
    # The unit's form follows the value as a decimal: "1/3 millimeters".
    decimal = format_number(float(fraction), FIELD_DECIMALS)
    number = _mixed_text(fraction)
    return _(MEASURE_SPOKEN).format(number=number, unit=unit.spoken(decimal)).strip()


def entry_text(entry: TypedValue, unit: Unit, prefs: DisplayPrefs) -> str:
    """Return the text a field labelled ``unit`` shows for a value typed with its unit.

    The user's own text is shown when it named its unit, or when its unit is still the
    field's. Otherwise the value is shown converted, so a field never shows a bare number
    in a unit other than the one it labels. The value itself never changes (ADR-0013 §9).

    Text read in another decimal mark than the screen's is the app's, such as a default
    written with ".", so it's shown converted too, in the locale's mark; the user's own
    text is read in the locale's mark, so it stays as typed (ADR-0020 §4).
    """
    own_mark = entry.decimal == prefs.symbols.decimal or "." not in entry.text
    as_typed = entry.explicit_unit or entry.unit == unit
    if own_mark and as_typed:
        return entry.text
    return field_text(entry.value, unit, prefs)


def render_step(
    step: Step, result: Result | None, units: ShownUnits, prefs: DisplayPrefs
) -> tuple[str, str | None, str]:
    """Return (symbolic, substituted, value) text for one step of the work.

    The work is in the set's unit for each dimension, a form's full unit for a form, so
    a line reads ``= 2 × 16.1875 in``, never ``2 × 1'-4 3/16"`` (ADR-0024 E4).
    Substitution shows each symbol in those units, which is only meaningful for formulas
    that are dimensionally homogeneous. All built-in formulas are (see known-issues KI-005).
    A step with its own ``substitution``, such as a derived value's work, needs no result.
    A step with an ``expression_unit`` shows its value in that unit first, then in the
    shown unit, e.g. ``0.1046 in = 2.6568 mm``, so the substituted line stays true. A
    stated value is shown as stated, e.g. ``0.109375 in``, never rounded for display.

    Each line is math, so its numbers take the locale's decimal mark (``typeset``); a
    step's note is prose and stays as written.

    Raises:
        UsageError: ``result`` is ``None`` for a step that substitutes the run's values.
    """
    symbolic, substituted, value = _step_lines(step, result, units, replace(prefs, symbols=POINT))
    value = typeset(value, prefs.symbols)
    if substituted is None:
        return (step.note, None, value)
    return (typeset(symbolic, prefs.symbols), typeset(substituted, prefs.symbols), value)


def _step_lines(
    step: Step, result: Result | None, units: ShownUnits, prefs: DisplayPrefs
) -> tuple[str, str | None, str]:
    """Return a step's formula, substitution, and value, with ``"."`` decimal points.

    A step with no formula has neither: its formula is ``""`` and its substitution
    ``None``.
    """
    value_text = unit_parts(step.value, units.unit(step.dimension), prefs).with_unit
    if step.signed:
        number, space, written = value_text.partition(" ")
        value_text = _plus(number) + space + written
    if step.expression_unit is not None:
        unit = get_unit(step.expression_unit, step.dimension)
        yielded = step.stated
        if yielded is None:
            precision = prefs.precision_for(step.dimension)
            yielded = f"{format_precise(from_base(step.value, unit), precision)} {unit.symbol}"
        if unit.symbol != units.unit(step.dimension).symbol:
            value_text = f"{yielded} = {value_text}"
        elif step.stated is not None:
            value_text = step.stated
    if step.expression is None:
        return ("", None, value_text)
    symbolic = expr.render_symbolic(step.expression)
    if step.substitution is not None:
        return (symbolic, expr.render_numeric(step.expression, step.substitution), value_text)
    if result is None:
        raise UsageError("render_step() needs the result to show this step's values")
    values: dict[str, str] = {}
    for name in expr.names(step.expression):
        v, dim = result.symbols[name]
        parts = unit_parts(v, units.unit(dim), prefs)
        text = parts.with_unit if dim is Dimension.ANGLE else parts.number
        values[name] = f"({text})" if text.startswith("-") else text
    return (symbolic, expr.render_numeric(step.expression, values), value_text)


def describe_source(source: InputSource) -> str:
    """Return how an input's source is shown to users, e.g. ``"Sheet Metal settings"``.

    A domain value the user applied from a citation names it, e.g. ``"Sheet Metal
    settings, starting value from FAA-H-8083-31B, p. 4-63"`` (ADR-0014 M2). A reference is
    named by its short form (``Reference.short``). The GUI and the CLI both use this, so
    they word sources the same way (ADR-0013 §5).
    """
    if source.kind is SourceKind.EXPLICIT:
        return source.label or "entered"
    if source.kind is SourceKind.DEFAULT:
        return "default"
    domain = source.kind is SourceKind.DOMAIN
    label = source.label or ("domain settings" if domain else "derived")
    if source.reference is None:
        return label
    if domain:
        return f"{label}, starting value from {source.reference.short}"
    return f"{label}, {source.reference.short}"


_NOTE_HEADINGS = {
    NoteKind.WARNING: "",
    NoteKind.LIMIT_EXCEEDED: "Limit exceeded",
    NoteKind.NO_APPLICABLE_VALUE: "No applicable value",
    NoteKind.INFEASIBLE: "Not makeable",
}
"""How each kind of note is introduced; a plain warning needs no heading."""


@dataclass(frozen=True)
class NoteText:
    """A note as users read it, in parts (ADR-0017 F1): lead, detail, then sources.

    A front end styles each part: the GUI sets the sources smaller, and the CLI indents
    the detail and the sources under the lead.
    """

    heading: str
    """How its kind is introduced, e.g. ``"Limit exceeded"``; empty for a warning."""
    lead: str
    """The verdict, with its numbers in display units."""
    detail: str
    """What follows, if anything; empty for none."""
    sources: str
    """The sources, e.g. ``"Sources: AC 43.13-1B, Table 4-6: aircraft repair practice"``;
    empty for a note with none."""

    @property
    def first_line(self) -> str:
        """The heading and the lead, e.g. ``"Limit exceeded: inside radius …"``."""
        return HEADED.format(heading=self.heading, lead=self.lead) if self.heading else self.lead

    @property
    def lines(self) -> tuple[str, ...]:
        """The parts as lines: the first line, then the detail and the sources if any."""
        return tuple(line for line in (self.first_line, self.detail, self.sources) if line)


HEADED = "{heading}: {lead}"
"""How a note's heading introduces its lead."""
SOURCES = "Sources: {sources}"
"""How a note's sources are introduced."""


def describe_note(note: Note, units: ShownUnits, prefs: DisplayPrefs) -> NoteText:
    """Return a note as users read it, in parts, with its values in the set's units.

    Each source is named by its short form (``Reference.short``) and followed by its scope,
    when it has one, so a note says how far its source applies, e.g. "AC 43.13-1B,
    Table 4-6: aerospace bench practice". The full citations stay in the note's
    references and in JSON. The GUI and the CLI both use this, so a note reads the same
    in both.
    """

    def show(value: float, dimension: Dimension) -> str:
        # The number and its unit, a form's full unit for a form; a fraction beside it
        # would break the sentence, and the result fields show it already.
        return unit_parts(value, units.unit(dimension), prefs).with_unit

    cited = " · ".join(f"{r.short}: {r.scope}" if r.scope else r.short for r in note.references)
    return NoteText(
        _NOTE_HEADINGS[note.kind],
        note.fill(note.text, show),
        note.fill(note.detail, show),
        SOURCES.format(sources=cited) if cited else "",
    )


def method_notes(method: Method, units: ShownUnits, prefs: DisplayPrefs) -> tuple[str, ...]:
    """Return a method's notes as users read them, their values in the set's units.

    Each value is written as the results write it, in the user's number format.
    """
    return method.notes_shown(
        lambda value, dimension: unit_parts(value, units.unit(dimension), prefs).with_unit
    )


def describe_setting_uses(uses: Sequence[tuple[Calculator, Sequence[Method]]]) -> list[str]:
    """Return one line per calculator that uses a domain setting, for the settings page.

    A calculator that uses the setting in every method is named alone; otherwise the
    methods follow, e.g. ``"V-die opening (air bending): 8 × thickness rule of thumb"``.

    Args:
        uses: What ``Registry.setting_uses`` returns.
    """
    lines = []
    for calc, methods in uses:
        if len(methods) == len(calc.methods):
            lines.append(calc.name)
        else:
            lines.append(f"{calc.name}: {', '.join(m.label for m in methods)}")
    return lines


def describe_override(
    family: str,
    inherited: float,
    own: float,
    dimension: Dimension,
    choice: str,
    prefs: DisplayPrefs,
) -> str:
    """Return the note under a field that overrides a set family value, with both values.

    For example: ``"Sheet Metal value is 0.2500 in; this calculator uses 0.1046 in."``

    Args:
        family: The domain's display name.
        inherited: The family value, in base units.
        own: The calculator's value, in base units.
        dimension: What the values measure.
        choice: The unit or form the calculator's field is picked in, which both are
            shown in.
        prefs: The decimals and symbols.
    """
    inherited_text = choice_parts(inherited, choice, dimension, prefs).with_unit
    own_text = choice_parts(own, choice, dimension, prefs).with_unit
    return f"{family} value is {inherited_text}; this calculator uses {own_text}."


def describe_error(error: CaddCalcError, units: ShownUnits, prefs: DisplayPrefs) -> str:
    """Return an error's message for users, with any values in the units shown.

    An input's range error is worded in that input's field's choice, a form's full unit
    for a form, since that's the unit the user is typing in: "T must be at most 0.25 in"
    (ADR-0024 E4). The GUI and the CLI both use this, so an error reads the same in both.
    """
    if isinstance(error, OutOfRangeError):
        param = error.param
        unit = choice_unit(units.input_choice(param.key, param.dimension), param.dimension)
        return error.describe(lambda v: quantity_text(v, unit, prefs))
    return str(error)


def quantity_text(value: float, unit: Unit, prefs: DisplayPrefs) -> str:
    """Write a value in ``unit`` for a message, e.g. ``0.393701 in``.

    It keeps six significant digits rather than the display decimals, so a bound in a
    message isn't rounded to a value the rejected input seems to satisfy.
    """
    shown = from_base(value, unit)
    whole = unit.dimension is Dimension.COUNT and shown.is_integer()
    number = f"{shown:.0f}" if whole else f"{shown:g}"  # a count is never "1e+06"
    return typeset(number, prefs.symbols) + unit_suffix(unit)


JSON_SCHEMA = 1
"""The number of ``result_json``'s format, which a script can check (ADR-0024 E5)."""


def result_json(
    calc: Calculator,
    result: Result,
    units: ShownUnits,
    prefs: DisplayPrefs,
    entered: Mapping[str, TypedValue] | None = None,
) -> dict[str, Any]:
    """Return a result as JSON's schema 1: every value in base units and as shown.

    Each input, output and step gives its ``dimension``, its ``base`` value and unit,
    which a script calculates with, and its ``shown`` unit, unrounded value and text, a
    form adding ``form`` and ``copied``. An input is shown in its own choice, an output in
    its fixed unit, its pick or the set's choice, and a step in the set's unit, never a
    form (ADR-0024 E4, E5). An input the run was given adds ``entered``: its text, the
    unit or form it was read in, and whether the text named it.

    Args:
        calc: The calculator that ran.
        result: Its result.
        units: The units it's shown in, with each input's choice.
        prefs: The decimals, for each ``text``.
        entered: The text of each input the run was given, by parameter key.
    """
    entered = entered or {}
    inputs: dict[str, Any] = {}
    for key, value in result.inputs.items():
        dimension = result.dimensions[key]
        choice = units.input_choice(key, dimension)
        parts = choice_parts(value, choice, dimension, prefs)
        item = {
            "dimension": dimension.value,
            "base": _base_json(value, dimension),
            "shown": _shown_json(value, choice_unit(choice, dimension), parts, choice),
        }
        if key in entered:
            item["entered"] = _entered_json(entered[key])
        item["source"] = result.source_of(key).to_dict()
        inputs[key] = item
    outputs: dict[str, Any] = {}
    for output in calc.outputs:
        value = result.outputs[output.key]
        parts = output_parts(output, value, units, prefs)
        unit = output_unit(output, units)
        outputs[output.key] = {
            "dimension": output.dimension.value,
            "base": _base_json(value, output.dimension),
            "shown": _shown_json(value, unit, parts, units.output_choice(output)),
        }
    steps = []
    for step in result.steps:
        unit = units.unit(step.dimension)
        parts = unit_parts(step.value, unit, prefs)
        if step.signed:
            parts = replace(parts, number=_plus(parts.number))
        steps.append(
            {
                "symbol": step.symbol,
                "label": step.label,
                "expression": step.expression,
                "note": step.note,
                "substitution": None if step.substitution is None else dict(step.substitution),
                "expression_unit": step.expression_unit,
                "stated": step.stated,
                "dimension": step.dimension.value,
                "base": _base_json(step.value, step.dimension),
                "shown": _shown_json(step.value, unit, parts, unit.symbol),
            }
        )
    return {
        "schema": JSON_SCHEMA,
        "calculator": result.calculator_id,
        "method": result.method,
        "output_set": units.key or None,
        "inputs": inputs,
        "outputs": outputs,
        "steps": steps,
        "notes": [_note_json(note, units, prefs) for note in result.notes],
    }


def _base_json(value: float, dimension: Dimension) -> dict[str, Any]:
    """Return a value in its dimension's base unit, as JSON: a count as a whole number."""
    return {"value": _json_number(value, dimension), "unit": BASE_UNITS[dimension]}


def _json_number(value: float, dimension: Dimension) -> float | int:
    return int(value) if dimension is Dimension.COUNT else value


def _shown_json(value: float, unit: Unit, parts: ValueParts, choice: str) -> dict[str, Any]:
    """Return a value as shown, as JSON: its unit, its unrounded value, and its text.

    A form adds its key and its copied text, and its value is in its full unit.
    """
    shown: dict[str, Any] = {
        "unit": unit.symbol,
        "value": _json_number(from_base(value, unit), unit.dimension),
    }
    if parts.compound is not None:
        return {**shown, "form": choice, "text": parts.number, "copied": parts.compound.copied}
    return {**shown, "text": parts.with_unit}


def _entered_json(entry: TypedValue) -> dict[str, Any]:
    """Return an input's text as entered, the unit or form it was read in, as JSON."""
    entered: dict[str, Any] = {"text": entry.text, "unit": entry.unit.symbol}
    form = entered_form(entry)
    if form is not None:
        entered["form"] = form
    entered["unit_in_text"] = entry.explicit_unit
    return entered


def entered_form(entry: TypedValue) -> str | None:
    """Return the form an input's text was read in: its pick, or the form its marks write.

    ``None`` for text read in a unit, as ``3 mm`` or a bare ``3`` is.
    """
    units = registry()
    if entry.choice is not None:
        picked = units.choice(entry.choice, entry.dimension)
        return picked.key if isinstance(picked, CompoundForm) else None
    for form in units.compounds_for(entry.dimension):
        try:
            if form.reads and form.parse(entry.text, entry.decimal) is not None:
                return form.key
        except CaddCalcError:
            continue
    return None


def _note_json(note: Note, units: ShownUnits, prefs: DisplayPrefs) -> dict[str, Any]:
    """Return a note as JSON: its text as shown, and each value it names twice."""
    text = describe_note(note, units, prefs)
    quantities = {}
    for name, (value, dimension) in note.quantities.items():
        unit = units.unit(dimension)
        parts = unit_parts(value, unit, prefs)
        quantities[name] = {
            "dimension": dimension.value,
            "base": _base_json(value, dimension),
            "shown": _shown_json(value, unit, parts, unit.symbol),
        }
    return {
        "kind": note.kind.value,
        "text": text.lead,
        "detail": text.detail,
        "quantities": quantities,
        "references": [reference.to_dict() for reference in note.references],
        "subjects": list(note.subjects),
    }
