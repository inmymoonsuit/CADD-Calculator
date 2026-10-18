"""Turning base-unit values into display text. Rounding happens only here (ADR-0005)."""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
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
from caddcalc.core.units import Dimension, TypedValue, Unit, from_base, get_unit

DISCLAIMER = (
    "Results are for drafting and education. Verify against your shop's tooling, "
    "material data, and test bends before manufacturing."
)


@dataclass(frozen=True)
class DisplayPrefs:
    """How values are shown: length unit, decimals, and optional inch fractions.

    Stresses follow the length unit (``display_unit``), so there is no stress unit here.
    """

    length_unit: str = "in"
    decimals: int = 4
    angle_decimals: int = 2
    stress_decimals: int = 1
    fraction_denominator: int | None = None
    """When set (e.g. 64) and the length unit is inches, also show the nearest fraction."""


def unit_suffix(dimension: Dimension, prefs: DisplayPrefs) -> str:
    """Return the unit text shown after a value, e.g. ``" in"``, ``" ksi"``, or ``"°"``."""
    return _suffix(_shown_unit(dimension, prefs))


def _shown_unit(dimension: Dimension, prefs: DisplayPrefs) -> str:
    """Return the unit symbol shown with a value: ``"°"`` for angles, else the display unit's."""
    return "°" if dimension is Dimension.ANGLE else display_unit(dimension, prefs).symbol


_CLOSE_UP = frozenset({"°"})
"""Units written against their number, as in ``90°``, rather than after a space."""


def _suffix(unit: str) -> str:
    """Return ``unit`` as written after a number: a degree sign close up, others spaced."""
    if unit in _CLOSE_UP:
        return unit
    return f" {unit}" if unit else ""


_SHOWN_IN = {Dimension.ANGLE: "deg", Dimension.RATIO: ""}
"""Display units of the dimensions whose unit doesn't follow the length preference."""

_STRESS_WITH_LENGTH = {"in": "ksi", "ft": "ksi"}
"""The stress unit shown with each inch-pound length unit; metric lengths show MPa."""


def display_unit(dimension: Dimension, prefs: DisplayPrefs) -> Unit:
    """Return the unit values of ``dimension`` are shown in.

    Lengths use the preferred unit. Stresses follow it: ksi with inches or feet, MPa
    with metric lengths, so one choice sets both (ADR-0005, amendments). Angles show in
    degrees, and ratios as plain numbers.
    """
    if dimension is Dimension.LENGTH:
        return get_unit(prefs.length_unit)
    if dimension is Dimension.STRESS:
        length = get_unit(prefs.length_unit).symbol
        return get_unit(_STRESS_WITH_LENGTH.get(length, "MPa"))
    return get_unit(_SHOWN_IN[dimension])


def entry_unit(dimension: Dimension, prefs: DisplayPrefs) -> str:
    """Return the unit a value typed without one is read in: its display unit's symbol.

    A bare number in a field then means what the field's unit label says, in every
    dimension.
    """
    return display_unit(dimension, prefs).symbol


def _decimals(dimension: Dimension, prefs: DisplayPrefs) -> int:
    """Return the decimal places ``dimension`` is shown with."""
    if dimension is Dimension.ANGLE:
        return prefs.angle_decimals
    if dimension is Dimension.STRESS:
        return prefs.stress_decimals
    return prefs.decimals


def display_value(value: float, dimension: Dimension, prefs: DisplayPrefs) -> float:
    """Convert a base-unit value to the display unit, without rounding."""
    return from_base(value, display_unit(dimension, prefs))


def decimal_separator(prefs: DisplayPrefs) -> str:
    """Return the decimal separator values are shown with: ``"."`` for now.

    Everything that reads a shown number's decimals asks here, so a separator preference
    (ADR-0017 F5, KI-022) changes one place.
    """
    del prefs  # every preference writes "." until there's a separator preference
    return "."


def format_number(value: float, decimals: int) -> str:
    """Return ``value`` rounded to ``decimals`` places, never as negative zero."""
    text = f"{value:.{decimals}f}"
    return "0" + text[2:] if text.startswith("-0") and float(text) == 0 else text


@dataclass(frozen=True)
class ValueParts:
    """A value as shown, in parts: its number, its unit, and its nearest inch fraction.

    ``format_value`` joins them, so a value shown whole and a value shown in parts, such
    as a result field's, can't disagree.
    """

    number: str
    """The number, rounded in the display unit, e.g. ``"0.3119"``: an ASCII ``-`` and a
    ``.`` decimal point, never a negative zero."""
    unit: str
    """The unit's symbol, e.g. ``"in"``, ``"ksi"``, or ``"°"``; ``""`` for a ratio."""
    fraction: str | None = None
    """The nearest drafting fraction of an inch length, e.g. ``"5/16"``, when it's shown."""

    @property
    def with_unit(self) -> str:
        """The number and its unit, e.g. ``"0.3119 in"`` or ``"120.00°"``, without the fraction."""
        return self.number + _suffix(self.unit)

    @property
    def unit_close_up(self) -> bool:
        """Whether the unit is written against the number, as ``°`` is, with no space."""
        return self.unit in _CLOSE_UP


def value_parts(value: float, dimension: Dimension, prefs: DisplayPrefs) -> ValueParts:
    """Return a base-unit value as shown, in parts (``ValueParts``).

    Args:
        value: The value in base units.
        dimension: What the value measures.
        prefs: The display unit, decimals, and fraction preference.
    """
    shown = display_value(value, dimension, prefs)
    fraction = None
    if (
        dimension is Dimension.LENGTH
        and prefs.fraction_denominator
        and get_unit(prefs.length_unit).symbol == "in"
    ):
        fraction = to_fraction(shown, prefs.fraction_denominator)
    number = format_number(shown, _decimals(dimension, prefs))
    return ValueParts(number, _shown_unit(dimension, prefs), fraction)


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
    ratio is only its number.
    """
    name = get_unit(parts.unit).spoken(parts.number)
    return SPOKEN.format(number=parts.number, unit=name) if name else parts.number


def output_parts(output: Output, value: float, prefs: DisplayPrefs) -> ValueParts:
    """Return a calculator output's value as shown, in parts.

    Every front end presents outputs through here or ``format_output``, so an output's
    own presentation, such as a converter row's fixed unit (ADR-0018), will apply in one
    place. Today it's the output's dimension, as ``value_parts`` shows it.
    """
    return value_parts(value, output.dimension, prefs)


def format_output(output: Output, value: float, prefs: DisplayPrefs) -> str:
    """Return a calculator output's value as display text, e.g. ``0.3119 in``."""
    return _shown(output_parts(output, value, prefs))


class CopyForm(Enum):
    """What copying a value puts on the clipboard (``copy_text``)."""

    VALUE = "value"
    """The number as shown, without its unit, e.g. ``0.3119``: it pastes cleanly into a
    spreadsheet cell or a CAD dimension box working in the drawing's units."""
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

    Every number form writes plain decimals, never an exponent, with an ASCII ``-`` and a
    ``.`` decimal point, and never a negative zero, so it pastes into a spreadsheet or a
    CAD input as it reads. Only ``FRACTION`` copies the inch fraction.

    Raises:
        UsageError: ``FRACTION`` for a value shown without one.
    """
    parts = value_parts(value, dimension, prefs)
    return _copied(parts, display_value(value, dimension, prefs), form)


def copy_output(output: Output, value: float, prefs: DisplayPrefs, form: CopyForm) -> str:
    """Return a calculator output's value as clipboard text, as ``output_parts`` shows it.

    Raises:
        UsageError: ``FRACTION`` for a value shown without one.
    """
    shown = display_value(value, output.dimension, prefs)
    return _copied(output_parts(output, value, prefs), shown, form)


def _copied(parts: ValueParts, shown: float, form: CopyForm) -> str:
    """Return a shown value's clipboard text in ``form``; ``shown`` is it unrounded."""
    if form is CopyForm.VALUE:
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

    A text cell that a spreadsheet would read as a formula, one starting with ``=``,
    ``+``, ``-``, or ``@`` (or their full-width forms), after any spaces, gets a leading
    apostrophe, which spreadsheets take as "this is text" (OWASP, "CSV Injection"). A
    tab or line break, which OWASP also lists, is already a space here. The value cell
    never gets one: a negative number must paste as a number.
    """
    rows = []
    for output in calc.outputs:
        parts = output_parts(output, result.outputs[output.key], prefs)
        symbol, label, unit = (_text_cell(t) for t in (output.symbol, output.label, parts.unit))
        rows.append("\t".join((symbol, label, _cell(parts.number), unit)) + "\n")
    return "".join(rows)


_CELL_BREAKS = str.maketrans({"\t": " ", "\n": " ", "\r": " "})
"""Tabs and line breaks, which a tab-separated cell can't hold."""


def _cell(text: str) -> str:
    """Return ``text`` with every tab and line break as a space, for one TSV cell."""
    return text.replace("\r\n", "\n").translate(_CELL_BREAKS)


_FORMULA_STARTS = tuple("=+-@\uff1d\uff0b\uff0d\uff20")
"""What a spreadsheet may read a cell as a formula from: = + - @, and the full-width
forms some locales' spreadsheets take for them (OWASP, "CSV Injection")."""


def _text_cell(text: str) -> str:
    """Return ``text`` as one TSV text cell, never read as a formula."""
    cell = _cell(text)
    return f"'{cell}" if cell.lstrip(" ").startswith(_FORMULA_STARTS) else cell


FIELD_DECIMALS = 6
"""Decimal places a form field shows for a value it converted, before trailing zeros go.

Values under about 5e-7 of a display unit show as 0. That is far finer than any drafting
dimension, and more places would make every converted field long.
"""


def field_text(value: float, dimension: Dimension, prefs: DisplayPrefs) -> str:
    """Return a base-unit value as form-field text in the display unit, e.g. ``2.65684``.

    It has no unit, because the field labels its unit, and no trailing zeros.
    """
    shown = format_number(display_value(value, dimension, prefs), FIELD_DECIMALS)
    return shown.rstrip("0").rstrip(".")


def entry_text(entry: TypedValue, prefs: DisplayPrefs) -> str:
    """Return the text a form field shows for a value the user typed (ADR-0013 §9).

    The user's own text is shown when it named its unit, or when its unit is still the
    display unit. Otherwise the value is shown converted, so a field never shows a bare
    number in a unit other than the one it labels. The value itself never changes.
    """
    if entry.explicit_unit or entry.unit == display_unit(entry.dimension, prefs):
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

    Raises:
        UsageError: ``result`` is ``None`` for a step that substitutes the run's values.
    """
    value_text = format_value(step.value, step.dimension, prefs)
    if step.expression_unit is not None:
        unit = get_unit(step.expression_unit)
        yielded = step.stated
        if yielded is None:
            decimals = _decimals(step.dimension, prefs)
            yielded = f"{format_number(from_base(step.value, unit), decimals)} {unit.symbol}"
        if unit.symbol != display_unit(step.dimension, prefs).symbol:
            value_text = f"{yielded} = {value_text}"
        elif step.stated is not None:
            value_text = step.stated
    if step.expression is None:
        return (step.note, None, value_text)
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
        return format_value(value, dimension, prefs)

    cited = " · ".join(f"{r.short}: {r.scope}" if r.scope else r.short for r in note.references)
    return NoteText(
        _NOTE_HEADINGS[note.kind],
        note.fill(note.text, show),
        note.fill(note.detail, show),
        SOURCES.format(sources=cited) if cited else "",
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
    return f"{display_value(value, dimension, prefs):g}{unit_suffix(dimension, prefs)}"
