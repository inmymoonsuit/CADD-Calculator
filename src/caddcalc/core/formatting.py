"""Turning base-unit values into display text. Rounding happens only here (ADR-0005).

It formats numbers; which unit a value is shown in, and how that unit is written, it asks
the units registry (ADR-0019 §1), so it holds no unit tables of its own.
"""

from __future__ import annotations

import math
import re
from collections.abc import Sequence
from dataclasses import dataclass, replace
from decimal import ROUND_HALF_EVEN, Decimal
from enum import Enum
from fractions import Fraction

from caddcalc.core import expr
from caddcalc.core.calculator import Calculator, Result
from caddcalc.core.errors import CaddCalcError, UsageError
from caddcalc.core.notes import Note, NoteKind
from caddcalc.core.provenance import InputSource, SourceKind
from caddcalc.core.spec import Method, OutOfRangeError, Output
from caddcalc.core.steps import Step
from caddcalc.core.units import (
    CompoundText,
    Dimension,
    Precision,
    TypedValue,
    Unit,
    from_base,
    get_unit,
    registry,
)

DISCLAIMER = (
    "Results are for drafting and education. Verify against your shop's tooling, "
    "material data, and test bends before manufacturing."
)


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
    """How values are shown: length unit, decimals, optional inch fractions, and symbols.

    Stresses follow the length unit (``display_unit``), so there is no stress unit here.
    """

    length_unit: str = "in"
    decimals: int = 4
    angle_decimals: int = 2
    stress_decimals: int = 1
    fraction_denominator: int | None = None
    """When set (e.g. 64) and the length unit is inches, also show the nearest fraction."""
    symbols: NumberSymbols = POINT
    """How numbers on screen are written: the locale's decimal mark (ADR-0020 §4)."""

    def decimals_for(self, dimension: Dimension) -> int:
        """Return the decimal places ``dimension`` is shown with.

        That's the user's choice for it, or, for a dimension with no choice of its own, the
        default its declaration gives (ADR-0019 §2).
        """
        chosen = {
            Dimension.LENGTH: self.decimals,
            Dimension.RATIO: self.decimals,
            Dimension.ANGLE: self.angle_decimals,
            Dimension.STRESS: self.stress_decimals,
        }.get(dimension)
        return registry().dimension(dimension).decimals if chosen is None else chosen


def unit_suffix(dimension: Dimension, prefs: DisplayPrefs) -> str:
    """Return the unit text shown after a value, e.g. ``" in"``, ``" ksi"``, or ``"°"``."""
    return _suffix(_shown_unit(dimension, prefs))


def _shown_unit(dimension: Dimension, prefs: DisplayPrefs) -> str:
    """Return the symbol written after a value, e.g. ``"in"``, or ``"°"`` for an angle."""
    return display_unit(dimension, prefs).written


def _close_up(written: str) -> bool:
    """Whether the unit written as ``written`` goes against its number, as ``°`` does."""
    unit = registry().written(written)
    return unit is not None and unit.close_up


def _suffix(unit: str) -> str:
    """Return ``unit`` as written after a number: close up for °, spaced otherwise."""
    if _close_up(unit):
        return unit
    return f" {unit}" if unit else ""


def display_unit(dimension: Dimension, prefs: DisplayPrefs) -> Unit:
    """Return the unit values of ``dimension`` are shown in.

    Lengths use the preferred unit. Stresses follow it: ksi with inches or feet, MPa
    with metric lengths, so one choice sets both (ADR-0005, amendments). Angles show in
    degrees, and ratios as plain numbers. Each dimension declares its rule in the units
    registry (ADR-0019 §2).
    """
    return registry().shown_unit(dimension, get_unit(prefs.length_unit, Dimension.LENGTH))


def entry_unit(dimension: Dimension, prefs: DisplayPrefs) -> str:
    """Return the unit a value typed without one is read in: its display unit's symbol.

    A bare number in a field then means what the field's unit label says, in every
    dimension.
    """
    return display_unit(dimension, prefs).symbol


def _decimals(dimension: Dimension, prefs: DisplayPrefs) -> int:
    """Return the decimal places ``dimension`` is shown with (``DisplayPrefs.decimals_for``)."""
    return prefs.decimals_for(dimension)


def display_value(value: float, dimension: Dimension, prefs: DisplayPrefs) -> float:
    """Convert a base-unit value to the display unit, without rounding."""
    return from_base(value, display_unit(dimension, prefs))


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


def format_significant(value: float, digits: int, decimal: str = ".") -> str:
    """Return ``value`` to ``digits`` significant figures, as plain decimals.

    It keeps trailing zeros, which say how many figures are shown (``25.4000`` to six),
    writes no exponent, and is never a negative zero. A rounding that carries into a new
    place keeps the count, so 9.999997 to six is ``10.0000``. Zero is ``0.00000`` to six.

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
    """A value as shown, in parts: its number, its unit, and its nearest inch fraction.

    ``format_value`` joins them, so a value shown whole and a value shown in parts, such
    as a result field's, can't disagree.
    """

    number: str
    """The number, rounded in the display unit, e.g. ``"0.3119"``: an ASCII ``-`` and the
    locale's decimal mark (``DisplayPrefs.symbols``), never a negative zero."""
    unit: str
    """The unit's symbol, e.g. ``"in"``, ``"ksi"``, or ``"°"``; ``""`` for a ratio."""
    fraction: str | None = None
    """The nearest drafting fraction of an inch length, e.g. ``"5/16"``, when it's shown."""
    compound: CompoundText | None = None
    """The value in a compound form, when it's shown in one, e.g. feet and inches. Its
    ``number`` is then the form as shown, with no unit of its own, and it's copied and
    spoken as the form writes it."""

    @property
    def with_unit(self) -> str:
        """The number and its unit, e.g. ``"0.3119 in"`` or ``"120.00°"``, without the fraction."""
        return self.number + _suffix(self.unit)

    @property
    def unit_close_up(self) -> bool:
        """Whether the unit is written against the number, as ``°`` is, with no space."""
        return _close_up(self.unit)


def value_parts(value: float, dimension: Dimension, prefs: DisplayPrefs) -> ValueParts:
    """Return a base-unit value as shown, in parts (``ValueParts``).

    Args:
        value: The value in base units.
        dimension: What the value measures.
        prefs: The display unit, decimals, and fraction preference.
    """
    return _parts(value, display_unit(dimension, prefs), _decimals(dimension, prefs), prefs)


def _parts(value: float, unit: Unit, precision: int | Precision, prefs: DisplayPrefs) -> ValueParts:
    """Return a base-unit value as shown in ``unit``, to ``precision``, in parts.

    ``precision`` is a number of decimal places, or a ``Precision``.
    """
    shown = from_base(value, unit)
    fraction = None
    if prefs.fraction_denominator and unit.fractions:
        fraction = to_fraction(shown, prefs.fraction_denominator)
    mark = prefs.symbols.decimal
    if isinstance(precision, Precision):
        number = format_precise(shown, precision, mark)
    else:
        number = format_number(shown, precision, mark)
    return ValueParts(number, unit.written, fraction)


def format_value(
    value: float, dimension: Dimension, prefs: DisplayPrefs, *, unit: bool = True
) -> str:
    """Return a base-unit value as display text, e.g. ``0.3119 in``.

    Args:
        value: The value in base units.
        dimension: What the value measures.
        prefs: The display unit, decimals, and fraction preference.
        unit: Append the unit (and the nearest fraction, when enabled).
    """
    parts = value_parts(value, dimension, prefs)
    return _shown(parts) if unit else parts.number


def _shown(parts: ValueParts) -> str:
    """Return a value's parts as one text: number, unit, and any fraction."""
    if parts.fraction is None:
        return parts.with_unit
    return f'{parts.with_unit}  (≈ {parts.fraction}")'


SPOKEN = "{number} {unit}"
"""How a value and its unit's spoken name are said together."""


def spoken_value(parts: ValueParts) -> str:
    """Return a value as a screen reader should say it, e.g. ``"0.3119 inches"``.

    The unit is named in full, singular only after a shown ``1`` (``Unit.spoken``); a
    ratio is only its number, and a compound form is said as it says itself, e.g. "1 foot
    4 inches".
    """
    if parts.compound is not None:
        return parts.compound.spoken
    unit = registry().written(parts.unit)
    name = "" if unit is None else unit.spoken(parts.number)
    return SPOKEN.format(number=parts.number, unit=name) if name else parts.number


def output_unit(output: Output, prefs: DisplayPrefs) -> Unit:
    """Return the unit an output is shown in: its fixed unit, or its dimension's display unit.

    An output in a compound form gives the form's full-precision unit, such as the inch
    for feet and inches.
    """
    if output.form:
        return get_unit(registry().compound(output.form).full_unit, output.dimension)
    if output.unit:
        return get_unit(output.unit, output.dimension)
    return display_unit(output.dimension, prefs)


def output_parts(output: Output, value: float, prefs: DisplayPrefs) -> ValueParts:
    """Return a calculator output's value as shown, in parts.

    Every front end presents outputs through here or ``format_output``, so an output's
    own presentation applies in one place. An output with a fixed unit, as a converter's
    row has (ADR-0018 §3), is shown in it, whatever the display unit, to the registry's
    precision for it; one with a compound form, in that form; and any other as
    ``value_parts`` shows its dimension.
    """
    if output.form:
        written = registry().compound(output.form).text(value, prefs.symbols.decimal)
        return ValueParts(written.shown, "", None, written)
    if not output.unit:
        return value_parts(value, output.dimension, prefs)
    unit = output_unit(output, prefs)
    return _parts(value, unit, registry().precision_for(unit), prefs)


def format_output(output: Output, value: float, prefs: DisplayPrefs) -> str:
    """Return a calculator output's value as display text, e.g. ``0.3119 in``."""
    return _shown(output_parts(output, value, prefs))


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
    """The value in the display unit, unrounded to ``FULL_DIGITS`` significant digits."""
    FRACTION = "fraction"
    """The nearest inch fraction as shown, with the inch mark, e.g. ``5/16"`` or
    ``1-5/16"``: a bare ``5/16`` would paste into a spreadsheet as a date. Only a value
    shown with a fraction has one."""


FULL_DIGITS = 10
"""Significant digits a full-precision copy keeps: far past any drafting tolerance."""


def copy_text(value: float, dimension: Dimension, prefs: DisplayPrefs, form: CopyForm) -> str:
    """Return a base-unit value as clipboard text, in ``form``.

    Every number form writes plain decimals, never an exponent, with an ASCII ``-`` and
    never a negative zero, so it pastes into a spreadsheet or a CAD input as it reads.
    Each writes ``"."`` for its decimal point, but ``SHOWN``, which writes the locale's
    mark. Only ``FRACTION`` copies the inch fraction.

    Raises:
        UsageError: ``FRACTION`` for a value shown without one.
    """
    parts = value_parts(value, dimension, _copy_prefs(prefs, form))
    return _copied(parts, display_value(value, dimension, prefs), form)


def copy_output(output: Output, value: float, prefs: DisplayPrefs, form: CopyForm) -> str:
    """Return a calculator output's value as clipboard text, as ``output_parts`` shows it.

    Raises:
        UsageError: ``FRACTION`` for a value shown without one.
    """
    shown = from_base(value, output_unit(output, prefs))
    return _copied(output_parts(output, value, _copy_prefs(prefs, form)), shown, form)


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
    if form is CopyForm.FRACTION:
        if parts.fraction is None:
            raise UsageError("This value is shown without a fraction, so there's none to copy")
        return f'{parts.fraction}"'
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


def results_tsv(calc: Calculator, result: Result, prefs: DisplayPrefs) -> str:
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
    The value cell never gets one, a negative number must paste as a number, unless it's
    a compound form, such as ``-1'-4"``, which is text.
    """
    rows = []
    for output in calc.outputs:
        parts = output_parts(output, result.outputs[output.key], prefs)
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


def field_text(value: float, dimension: Dimension, prefs: DisplayPrefs) -> str:
    """Return a base-unit value as form-field text in the display unit, e.g. ``2.65684``.

    It has no unit, because the field labels its unit, and no trailing zeros. Its
    decimal mark is the locale's: the app writes it into the field (ADR-0020 §4).
    """
    mark = prefs.symbols.decimal
    shown = format_number(display_value(value, dimension, prefs), FIELD_DECIMALS, mark)
    return shown.rstrip("0").rstrip(mark)


def entry_text(entry: TypedValue, prefs: DisplayPrefs) -> str:
    """Return the text a form field shows for a value the user typed (ADR-0013 §9).

    The user's own text is shown when it named its unit, or when its unit is still the
    display unit. Otherwise the value is shown converted, so a field never shows a bare
    number in a unit other than the one it labels. The value itself never changes.

    Text read in another decimal mark than the screen's is the app's, such as a default
    written with ".", so it's shown converted too, in the locale's mark; the user's own
    text is read in the locale's mark, so it stays as typed (ADR-0020 §4).
    """
    own_mark = entry.decimal == prefs.symbols.decimal or "." not in entry.text
    as_typed = entry.explicit_unit or entry.unit == display_unit(entry.dimension, prefs)
    if own_mark and as_typed:
        return entry.text
    return field_text(entry.value, entry.dimension, prefs)


def to_fraction(value: float, denominator: int = 64) -> str:
    """Nearest drafting fraction: ``1.015625`` → ``1-1/64``, ``0.5`` → ``1/2``."""
    if not math.isfinite(value):
        return str(value)
    frac = Fraction(round(abs(value) * denominator), denominator)
    sign = "-" if value < 0 and frac else ""  # a value that rounds to 0 is never "-0"
    whole, rem = divmod(frac.numerator, frac.denominator)
    if rem == 0:
        return f"{sign}{whole}"
    part = f"{rem}/{frac.denominator}"
    return f"{sign}{whole}-{part}" if whole else f"{sign}{part}"


def render_step(
    step: Step, result: Result | None, prefs: DisplayPrefs
) -> tuple[str, str | None, str]:
    """Return (symbolic, substituted, value) text for one step of the work.

    Substitution shows each symbol in display units, which is only meaningful for formulas
    that are dimensionally homogeneous. All built-in formulas are (see known-issues KI-005).
    A step with its own ``substitution``, such as a derived value's work, needs no result.
    A step with an ``expression_unit`` shows its value in that unit first, then in the
    display unit, e.g. ``0.1046 in = 2.6568 mm``, so the substituted line stays true. A
    stated value is shown as stated, e.g. ``0.109375 in``, never rounded for display.

    Each line is math, so its numbers take the locale's decimal mark (``typeset``); a
    step's note is prose and stays as written.

    Raises:
        UsageError: ``result`` is ``None`` for a step that substitutes the run's values.
    """
    symbolic, substituted, value = _step_lines(step, result, replace(prefs, symbols=POINT))
    value = typeset(value, prefs.symbols)
    if substituted is None:
        return (step.note, None, value)
    return (typeset(symbolic, prefs.symbols), typeset(substituted, prefs.symbols), value)


def _step_lines(
    step: Step, result: Result | None, prefs: DisplayPrefs
) -> tuple[str, str | None, str]:
    """Return a step's formula, substitution, and value, with ``"."`` decimal points.

    A step with no formula has neither: its formula is ``""`` and its substitution
    ``None``.
    """
    value_text = format_value(step.value, step.dimension, prefs)
    if step.expression_unit is not None:
        unit = get_unit(step.expression_unit, step.dimension)
        yielded = step.stated
        if yielded is None:
            decimals = _decimals(step.dimension, prefs)
            yielded = f"{format_number(from_base(step.value, unit), decimals)} {unit.symbol}"
        if unit.symbol != display_unit(step.dimension, prefs).symbol:
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
        text = format_value(v, dim, prefs, unit=dim is Dimension.ANGLE)
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


def describe_note(note: Note, prefs: DisplayPrefs) -> NoteText:
    """Return a note as users read it, in parts, with its values in display units.

    Each source is named by its short form (``Reference.short``) and followed by its scope,
    when it has one, so a note says how far its source applies, e.g. "AC 43.13-1B,
    Table 4-6: aerospace bench practice". The full citations stay in the note's
    references and in JSON. The GUI and the CLI both use this, so a note reads the same
    in both.
    """

    def show(value: float, dimension: Dimension) -> str:
        # The number and its unit; a fraction beside it would break the sentence, and the
        # result fields show it already.
        return value_parts(value, dimension, prefs).with_unit

    cited = " · ".join(f"{r.short}: {r.scope}" if r.scope else r.short for r in note.references)
    return NoteText(
        _NOTE_HEADINGS[note.kind],
        note.fill(note.text, show),
        note.fill(note.detail, show),
        SOURCES.format(sources=cited) if cited else "",
    )


def method_notes(method: Method, prefs: DisplayPrefs) -> tuple[str, ...]:
    """Return a method's notes as users read them, their values in the display units.

    Each value is written as the results write it, in the user's number format.
    """
    return method.notes_shown(
        lambda value, dimension: value_parts(value, dimension, prefs).with_unit
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
    family: str, inherited: float, own: float, dimension: Dimension, prefs: DisplayPrefs
) -> str:
    """Return the note under a field that overrides a set family value, with both values.

    For example: ``"Sheet Metal value is 0.2500 in; this calculator uses 0.1046 in."``

    Args:
        family: The domain's display name.
        inherited: The family value, in base units.
        own: The calculator's value, in base units.
        dimension: What the values measure.
        prefs: The display unit and decimals.
    """
    return (
        f"{family} value is {format_value(inherited, dimension, prefs)}; "
        f"this calculator uses {format_value(own, dimension, prefs)}."
    )


def describe_error(error: CaddCalcError, prefs: DisplayPrefs) -> str:
    """Return an error's message for users, with any values in display units.

    The GUI and the CLI both use this, so an error reads the same in both.
    """
    if isinstance(error, OutOfRangeError):
        dimension = error.param.dimension
        return error.describe(lambda v: _quantity_text(v, dimension, prefs))
    return str(error)


def _quantity_text(value: float, dimension: Dimension, prefs: DisplayPrefs) -> str:
    """Write a value for a message, e.g. ``0.393701 in``.

    It keeps six significant digits rather than the display decimals, so a bound in a
    message isn't rounded to a value the rejected input seems to satisfy.
    """
    number = f"{display_value(value, dimension, prefs):g}"
    return typeset(number, prefs.symbols) + unit_suffix(dimension, prefs)
