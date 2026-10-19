"""Reading what's typed into a field whose unit a picker chooses (ADR-0024 D7, E2, E3).

A field's text never names its unit: the picker beside it does. In a unit's field the
text is a number, a fraction, a mixed number, or arithmetic on them, evaluated exactly
as a rational in the picked unit and rounded once, so a plain number reads bit for bit
as ``parse_quantity`` reads it with that unit. In a form's field, such as feet and
inches, the text is the form's own grammar, with its marks optional. A text that names
a unit is refused with its fix (``UnitInTextError``).

The arithmetic is this module's own small tokenizer and recursive-descent parser, not
Python's ``ast``, which would read ``0x10``, ``1_000`` and ``1j`` as numbers.
"""

from __future__ import annotations

import math
import re
import sys
from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal
from fractions import Fraction

from caddcalc.core.errors import InputError
from caddcalc.core.units.compound import CompoundForm
from caddcalc.core.units.model import COUNT_LIMIT, Dimension, Unit
from caddcalc.core.units.numbers import MINUS_SIGN, comma_error
from caddcalc.core.units.unit_registry import registry

MAX_LENGTH = 200
"""The most characters a field's text may have."""
MAX_DEPTH = 50
"""The deepest a field's parentheses and signs may nest."""
MAX_BITS = 100_000
"""The most bits a numerator or denominator may reach while a text is evaluated, so a
text such as ``1e99999999`` is refused before it's built, never computed."""

_SPACES = re.compile(r"\s+")
"""A run of spaces of any kind, a no-break space among them: it reads as one space."""

_OPERATORS = {"+": "+", "-": "-", MINUS_SIGN: "-", "*": "*", "×": "*", "/": "/", "÷": "/"}
"""Each operator's character, by the operation it is: × is *, ÷ is /, and − is -."""

_NUMBER = re.compile(r"(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?")
"""A number, as ``parse_number`` reads one: ``3``, ``0.1046``, ``.5``, ``5.`` or ``1e3``."""


class UnitInTextError(InputError):
    """A field's text names a unit, which belongs in its picker (ADR-0024 Q5).

    It carries the fix, so a front end can offer it: the ``choice`` to pick and the
    ``number`` to type with it. A unitless field, such as a ratio's, has no picker, so a
    percent there is given as the plain number, with ``choice`` its unnamed unit,
    ``""``. Where the text isn't one number and its unit there's no fix, and ``choice``
    is ``None``.
    """

    def __init__(self, text: str, choice: str | None, shown: str, number: str) -> None:
        self.text = text
        self.choice = choice
        """The id of the choice to pick: a unit's key symbol or a form's key."""
        self.shown = shown
        """The unit as it's written, e.g. ``"°"`` or ``"%"``, or a form's symbol."""
        self.number = number
        """The text to type with ``choice`` picked: for a form, the text as it is."""
        if choice is None:
            message = f"{text!r} names a unit, {shown}: units go in the picker"
        elif not choice:
            message = (
                f"{text!r} names a unit, {shown}, which this field doesn't take: type {number}"
            )
        elif number == text:
            message = f"{text!r} is written in {shown}: pick {shown} and type it there"
        else:
            message = f"{text!r} names a unit: pick {shown} and type {number}"
        super().__init__(message)


@dataclass(frozen=True)
class _Token:
    kind: str
    """``"number"``, ``"("`` or ``")"``, or an operation: ``"+"``, ``"-"``, ``"*"``, ``"/"``."""
    start: int
    end: int
    value: Fraction = Fraction(0)
    digits: bool = False
    """Whether a number is written in digits alone, as a mixed number's parts are."""


class _NotArithmeticError(InputError):
    """The text has a character arithmetic has no use for: it may name a unit instead."""


def read(text: str, choice: str, dimension: Dimension, *, decimal: str = ".") -> tuple[float, Unit]:
    """Read a field's ``text`` picked in ``choice``, and return its base-unit value and unit.

    In a unit, the text is evaluated exactly (``evaluate``), rounded once to a double in
    the unit, then multiplied by its factor, as ``parse_quantity`` does. In a form, it's
    read by the form's grammar (``CompoundForm.read``) in the form's full unit, which is
    the unit returned, and converted so. ``decimal`` is the locale's decimal mark, read
    besides ``"."``.

    Raises:
        UnitInTextError: The text names a unit or a form, with the fix where it has one.
        InputError: The text isn't a value in the choice, or is too large for the base
            unit.
        UsageError: ``choice`` isn't one of ``dimension``'s.
    """
    units = registry()
    picked = units.choice(choice, dimension)
    stripped = _SPACES.sub(" ", text).strip()
    try:
        if isinstance(picked, CompoundForm):
            exact = picked.read(stripped.replace(MINUS_SIGN, "-"), decimal)
            unit = units.find(picked.full_unit, dimension)
        else:
            exact, unit = evaluate(stripped, decimal), picked
    except _NotArithmeticError as exc:
        raise _named(stripped, dimension, decimal) or InputError(str(exc)) from None
    except InputError as exc:
        if isinstance(picked, CompoundForm):
            raise _named(stripped, dimension, decimal, but=picked) or exc from None
        raise
    return _base(exact, unit, text), unit


def _base(exact: Fraction, unit: Unit, text: str) -> float:
    """Round an exact value in ``unit`` once, and convert it to the base unit."""
    try:
        number = float(exact)
    except OverflowError:
        raise InputError(f"{text!r} is too large a number to calculate with") from None
    if unit.dimension is Dimension.COUNT and not number.is_integer():
        raise InputError(f"{text!r} isn't a whole number, and a count is")
    if unit.dimension is Dimension.COUNT and abs(number) >= COUNT_LIMIT:
        raise InputError(f"{text!r} is too large a count to hold exactly: give one under 2^53")
    value = number * unit.factor
    if not math.isfinite(value):
        base = registry().dimension(unit.dimension).base
        raise InputError(
            f"{text!r} is too large to calculate with: its size in {base} must be under "
            f"{sys.float_info.max:.6g}"
        )
    return value


def _named(
    text: str, dimension: Dimension, decimal: str, *, but: CompoundForm | None = None
) -> InputError | None:
    """Return the error for a text that names a unit or is written in a form, if it does.

    The unit is recognized for the message only (ADR-0024 §4), in this order: a form in
    its marked grammar, as ``1'-4"`` is; a number and the unit that ends it, as ``3 mm``
    and ``1-3/16"`` are; then a form read with its marks optional, as ``5'9`` is. A
    unit of another dimension is refused as ``parse_quantity`` refuses it, with no offer.
    ``but`` is the form the field is picked in, whose marks are its own.
    """
    units = registry()
    signed = text.replace(MINUS_SIGN, "-")
    forms = [f for f in units.compounds_for(dimension) if f.reads and f is not but]
    for form in forms:
        try:
            if form.parse(signed, decimal) is not None:
                return UnitInTextError(text, form.key, form.symbol, text)
        except InputError:
            pass  # an attempt at the form, read with its marks optional below
    ending = units.ending(text, dimension)
    if ending is not None and ending[0].dimension is not dimension:
        unit = ending[0]
        return InputError(
            f"{text!r} is {unit.dimension.with_article}, but {dimension.with_article} is expected"
        )
    if ending is not None:
        unit, length = ending
        number = text[: len(text) - length].rstrip()
        try:
            amount = evaluate(number, decimal)
        except InputError:
            amount = None
        if amount is not None:
            return _unit_fix(text, unit, number, amount)
    for form in forms:
        try:
            form.read(signed, decimal)
        except InputError:
            continue
        return UnitInTextError(text, form.key, form.symbol, text)
    if ending is not None and but is None:
        # In a form's field a mark ending the text is the form's own, as in "30′ 40°".
        return UnitInTextError(text, None, ending[0].written or ending[0].symbol, "")
    return None


def _unit_fix(text: str, unit: Unit, number: str, amount: Fraction) -> UnitInTextError:
    """Return the fix for a number and a unit of the field's dimension."""
    units = registry()
    shown = unit.written or unit.symbol
    choices = units.entry_choices(unit.dimension)
    if unit.symbol in choices:
        return UnitInTextError(text, unit.symbol, shown, number)
    # A unitless field's one choice is its unnamed unit, so the fix is the plain number:
    # 44 % is 0.44.
    exact = unit.exact if unit.exact is not None else unit.factor
    return UnitInTextError(text, choices[0], shown, repr(float(amount * Fraction(exact))))


def evaluate(text: str, decimal: str = ".") -> Fraction:
    """Evaluate a field's text exactly: numbers, fractions, mixed numbers and arithmetic.

    It reads ``parse_number``'s numbers, with ``decimal`` besides ``"."``; ``+ - * /``,
    ``×``, ``÷`` and ``−``; one sign before a number or a parenthesis; and parentheses.
    AutoCAD's mixed-number rule holds: a hyphen with no space on either side, between a
    whole number and a proper fraction, joins them, so ``1-3/16`` is 1 3/16 and
    ``1 - 3/16`` is 13/16. A whole number, a space and a fraction, ``1 3/16``, is a mixed
    number too, and a mixed number binds tighter than any operator, so ``2 × 1 3/16`` is
    2 3/8 (ADR-0024 D7).

    Raises:
        InputError: The text isn't a number or arithmetic, divides by zero, or is too
            long, too deep, or too large to evaluate.
    """
    tokens = _mixed(_tokens(text, decimal), text)
    parser = _Parser(tokens, text)
    value = parser.sum()
    if parser.at < len(tokens):
        raise InputError(_unreadable(text, tokens[parser.at].start))
    return value


def _tokens(text: str, decimal: str) -> list[_Token]:
    if len(text) > MAX_LENGTH:
        raise InputError(f"{text[:20]!r}… is longer than {MAX_LENGTH} characters")
    if not text.strip():
        raise InputError(f"Cannot read a value from {text!r}")
    if decimal == "." and "," in text:
        raise comma_error(text, decimal)
    if "_" in text:
        raise InputError(f"{text!r} is not a number; digits aren't grouped")
    # The locale's mark is read as ".", which no operator is written with.
    written = text.replace(decimal, ".") if decimal != "." else text
    tokens: list[_Token] = []
    at = 0
    while at < len(written):
        char = written[at]
        if char.isspace():
            at += 1
        elif char in _OPERATORS or char in "()":
            tokens.append(_Token(_OPERATORS.get(char, char), at, at + 1))
            at += 1
        else:
            m = _NUMBER.match(written, at)
            if m is None:
                raise _NotArithmeticError(_unreadable(text, at))
            if m.end() < len(written) and written[m.end()] == ".":
                raise InputError(f"{text!r} has more than one decimal mark; digits aren't grouped")
            number = m.group()
            tokens.append(_Token("number", at, m.end(), _exact(number, text), number.isdigit()))
            at = m.end()
    return tokens


def _exact(number: str, text: str) -> Fraction:
    """Return a written number exactly, refusing one too large to build."""
    _sign, digits, exponent = Decimal(number).as_tuple()
    # A decimal digit is a little under 10/3 bits; a written number's exponent is an int.
    if (len(digits) + abs(int(exponent))) * 10 // 3 > MAX_BITS:
        raise InputError(f"{text!r} is too large a number to calculate with")
    return Fraction(Decimal(number))


def _unreadable(text: str, at: int) -> str:
    rest = text[at:].strip()
    if rest[:1].isalpha():
        return f"{text!r} isn't a number or arithmetic: names and units aren't read here"
    return f"{text!r} isn't a number or arithmetic, from {rest!r}"


def _mixed(tokens: list[_Token], text: str) -> list[_Token]:
    """Join each mixed number's whole number and fraction into one number (``evaluate``).

    ``1-3/16`` joins only with no space around the hyphen and a proper fraction after
    it; ``1 3/16`` joins with a space between them. Either way the fraction is digits over
    digits, with no space around its slash, and the whole number isn't the denominator
    of a fraction before it, so ``1/2 1/4`` stays two numbers.
    """
    joined: list[_Token] = []
    i = 0
    while i < len(tokens):
        size = _mixed_size(tokens, i)
        if size:
            whole, *_between, numerator, _slash, denominator = tokens[i : i + size]
            if denominator.value == 0:
                raise InputError(f"{text!r} can't divide by zero")
            value = whole.value + numerator.value / denominator.value
            joined.append(_Token("number", whole.start, denominator.end, value))
            i += size
        else:
            joined.append(tokens[i])
            i += 1
    return joined


def _mixed_size(tokens: list[_Token], i: int) -> int:
    """Return how many tokens from ``i`` a mixed number takes: 5, 4, or 0 for none."""

    def digits(j: int) -> bool:
        return j < len(tokens) and tokens[j].kind == "number" and tokens[j].digits

    def touch(j: int) -> bool:
        return tokens[j].end == tokens[j + 1].start

    def kind(j: int) -> str:
        return tokens[j].kind if j < len(tokens) else ""

    if not digits(i) or (i > 0 and kind(i - 1) == "/" and touch(i - 1)):
        return 0
    if kind(i + 1) == "-" and touch(i) and touch(i + 1):
        fraction = i + 2
    elif digits(i + 1) and not touch(i):
        fraction = i + 1
    else:
        return 0
    if not (digits(fraction) and kind(fraction + 1) == "/" and digits(fraction + 2)):
        return 0
    if not (touch(fraction) and touch(fraction + 1)):
        return 0
    numerator, denominator = tokens[fraction].value, tokens[fraction + 2].value
    if fraction == i + 2 and not numerator < denominator:
        return 0  # "1-5/4" is 1 - 5/4: the hyphen joins only a proper fraction
    return fraction + 3 - i


class _Parser:
    """A recursive-descent parser over a text's tokens, evaluating as it goes."""

    def __init__(self, tokens: list[_Token], text: str) -> None:
        self.tokens = tokens
        self.text = text
        self.at = 0
        self.depth = 0

    def peek(self) -> str:
        return self.tokens[self.at].kind if self.at < len(self.tokens) else ""

    def sum(self) -> Fraction:
        value = self.product()
        while self.peek() in ("+", "-"):
            operator = self.peek()
            self.at += 1
            if self.peek() in ("+", "-"):
                raise InputError(f"{self.text!r} has two signs in a row")
            right = self.product()
            value = self._bounded(value + right if operator == "+" else value - right)
        return value

    def product(self) -> Fraction:
        value = self.signed()
        while self.peek() in ("*", "/"):
            operator = self.peek()
            self.at += 1
            right = self.signed()
            if operator == "/" and right == 0:
                raise InputError(f"{self.text!r} can't divide by zero")
            value = self._bounded(value * right if operator == "*" else value / right)
        return value

    def signed(self) -> Fraction:
        if self.peek() not in ("+", "-"):
            return self.primary()
        operator = self.peek()
        self.at += 1
        if self.peek() in ("+", "-"):
            raise InputError(f"{self.text!r} has two signs in a row")
        value = self._nested(self.signed)
        return -value if operator == "-" else value

    def primary(self) -> Fraction:
        kind = self.peek()
        if kind == "number":
            value = self.tokens[self.at].value
            self.at += 1
        elif kind == "(":
            self.at += 1
            value = self._nested(self.sum)
            if self.peek() != ")":
                raise InputError(f"{self.text!r} has a parenthesis that isn't closed")
            self.at += 1
        elif not kind:
            raise InputError(f"{self.text!r} ends before its last number")
        else:
            raise InputError(_unreadable(self.text, self.tokens[self.at].start))
        if self.peek() in ("number", "("):
            start = self.tokens[self.at].start
            raise InputError(
                f"{self.text!r} has two numbers with nothing between them, at {self.text[start:]!r}"
            )
        return value

    def _nested(self, parse: Callable[[], Fraction]) -> Fraction:
        self.depth += 1
        if self.depth > MAX_DEPTH:
            raise InputError(f"{self.text!r} nests deeper than {MAX_DEPTH}")
        value = parse()
        self.depth -= 1
        return value

    def _bounded(self, value: Fraction) -> Fraction:
        if max(value.numerator.bit_length(), value.denominator.bit_length()) > MAX_BITS:
            raise InputError(f"{self.text!r} is too large a number to calculate with")
        return value
