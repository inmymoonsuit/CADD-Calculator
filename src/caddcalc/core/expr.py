"""A small, safe arithmetic-expression evaluator for calculator formulas.

A formula is written once, as text such as ``pi/180*A*(R + K*T)``, and this module
both *evaluates* it and *renders* it for the "show work" display. Because the same
string drives both, the displayed formula cannot drift from the computed one (ADR-0004).

Only numbers, symbol names, ``pi``, the whitelisted functions below, ``+ - * / **``
and parentheses are allowed. Python's ``eval`` is never used.

Angles are in degrees, so the trig helpers take and return degrees.
"""

from __future__ import annotations

import ast
import keyword
import math
import operator
import re
from collections.abc import Callable, Mapping
from decimal import Decimal, DecimalException, Overflow, localcontext
from fractions import Fraction
from functools import lru_cache

from caddcalc.core.errors import CalculationError, SpecError, UsageError


def _tand(deg: float) -> float:
    """Tangent of an angle in degrees, refusing angles where it is undefined."""
    if abs(math.cos(math.radians(deg))) < 1e-12:
        raise ValueError(f"tan is undefined at {deg:g}°")
    return math.tan(math.radians(deg))


FUNCTIONS: dict[str, Callable[..., float]] = {
    "sqrt": math.sqrt,
    "abs": abs,
    "min": min,
    "max": max,
    "sind": lambda deg: math.sin(math.radians(deg)),
    "cosd": lambda deg: math.cos(math.radians(deg)),
    "tand": _tand,
    "asind": lambda x: math.degrees(math.asin(x)),
    "acosd": lambda x: math.degrees(math.acos(x)),
    "atand": lambda x: math.degrees(math.atan(x)),
    "atan2d": lambda y, x: math.degrees(math.atan2(y, x)),
}


# (minimum, maximum) argument counts; None means unlimited.
ARITY: dict[str, tuple[int, int | None]] = {
    "sqrt": (1, 1),
    "abs": (1, 1),
    "min": (2, None),
    "max": (2, None),
    "sind": (1, 1),
    "cosd": (1, 1),
    "tand": (1, 1),
    "asind": (1, 1),
    "acosd": (1, 1),
    "atand": (1, 1),
    "atan2d": (2, 2),
}

CONSTANTS: dict[str, float] = {"pi": math.pi}

# Limits that keep hostile or runaway formulas (e.g. from future data files) cheap to reject.
# Only expression nodes count (not Load contexts or operator tokens): a flat sum of N
# terms has about 2N nodes and depth N. Python's ~1000-frame limit leaves room for these.
MAX_LENGTH = 1000
MAX_NODES = 400
MAX_DEPTH = 200

# How names are shown in the "show work" display.
DISPLAY_NAMES: dict[str, str] = {
    "pi": "π",
    "sqrt": "√",
    "sind": "sin",
    "cosd": "cos",
    "tand": "tan",
    "asind": "asin",
    "acosd": "acos",
    "atand": "atan",
    "atan2d": "atan2",
}

_BINARY_OPS: dict[type[ast.operator], Callable[[float, float], float]] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
}
_UNARY_OPS: dict[type[ast.unaryop], Callable[[float], float]] = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}


@lru_cache(maxsize=512)
def parse(expression: str) -> ast.expr:
    """Parse and validate an expression's syntax. Raises SpecError for disallowed syntax."""
    if len(expression) > MAX_LENGTH:
        raise SpecError(f"Formula is longer than {MAX_LENGTH} characters")
    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError as exc:
        raise SpecError(f"Invalid formula {expression!r}: {exc.msg}") from None
    except (RecursionError, MemoryError):
        raise SpecError("Formula is too deeply nested") from None
    nodes = list(ast.walk(tree))
    if sum(isinstance(n, ast.expr) for n in nodes) > MAX_NODES:
        raise SpecError(f"Formula has more than {MAX_NODES} elements")
    if _depth(tree) > MAX_DEPTH:
        raise SpecError(f"Formula is too complex (more than {MAX_DEPTH} levels of operations)")
    for node in nodes:
        allowed = (
            ast.Expression,
            ast.BinOp,
            ast.UnaryOp,
            ast.Constant,
            ast.Name,
            ast.Call,
            ast.Load,
            *_BINARY_OPS,
            *_UNARY_OPS,
        )
        if not isinstance(node, allowed):
            raise SpecError(
                f"Formula {expression!r} uses unsupported syntax: {type(node).__name__}"
            )
        if isinstance(node, ast.Constant) and (
            isinstance(node.value, bool) or not isinstance(node.value, int | float)
        ):
            raise SpecError(f"Formula {expression!r} contains a non-numeric constant")
        if isinstance(node, ast.Call):
            if (
                not isinstance(node.func, ast.Name)
                or node.func.id not in FUNCTIONS
                or node.keywords
            ):
                raise SpecError(f"Formula {expression!r} calls an unsupported function")
            lo, hi = ARITY[node.func.id]
            if len(node.args) < lo or (hi is not None and len(node.args) > hi):
                raise SpecError(
                    f"Formula {expression!r}: {node.func.id}() takes "
                    f"{lo if lo == hi else f'at least {lo}'} argument(s)"
                )
    return tree.body


def _depth(tree: ast.Expression) -> int:
    """Depth counting expression nodes only."""
    deepest = 0
    stack: list[tuple[ast.AST, int]] = [(tree.body, 1)]
    while stack:
        node, depth = stack.pop()
        deepest = max(deepest, depth)
        stack.extend(
            (child, depth + 1)
            for child in ast.iter_child_nodes(node)
            if isinstance(child, ast.expr)
        )
    return deepest


def is_usable_symbol(name: str) -> bool:
    """Return whether ``name`` can stand for a value in formulas.

    It must be an identifier that isn't a Python keyword or the name of a function or
    constant the evaluator provides.
    """
    return (
        name.isidentifier()
        and not keyword.iskeyword(name)
        and name not in FUNCTIONS
        and name not in CONSTANTS
    )


def names(expression: str) -> set[str]:
    """Return the symbol names an expression refers to (excluding functions and constants)."""
    found: set[str] = set()
    for node in ast.walk(parse(expression)):
        if isinstance(node, ast.Name) and node.id not in FUNCTIONS and node.id not in CONSTANTS:
            found.add(node.id)
    return found


def evaluate(expression: str, symbols: Mapping[str, float]) -> float:
    """Evaluate ``expression`` with the given symbol values."""
    node = parse(expression)
    shown = render_symbolic(expression)
    try:
        result = _eval(node, symbols, expression)
    except ZeroDivisionError:
        raise CalculationError(f"Division by zero in {shown}") from None
    except (ValueError, OverflowError, TypeError) as exc:
        raise CalculationError(f"Cannot evaluate {shown}: {exc}") from None
    if not math.isfinite(result):
        raise CalculationError(f"{shown} does not give a finite number")
    return result


def _eval(node: ast.expr, symbols: Mapping[str, float], expression: str) -> float:
    if isinstance(node, ast.Constant):
        if isinstance(node.value, bool) or not isinstance(node.value, int | float):
            raise SpecError(f"Formula {expression!r} contains a non-numeric constant")
        return float(node.value)
    if isinstance(node, ast.Name):
        if node.id in CONSTANTS:
            return CONSTANTS[node.id]
        if node.id in symbols:
            return symbols[node.id]
        raise SpecError(f"Formula {expression!r} refers to unknown symbol {node.id!r}")
    if isinstance(node, ast.BinOp):
        op = _BINARY_OPS[type(node.op)]
        value = op(_eval(node.left, symbols, expression), _eval(node.right, symbols, expression))
        if isinstance(value, complex):  # e.g. a negative base to a fractional power
            raise ValueError("the result is not a real number")
        return float(value)
    if isinstance(node, ast.UnaryOp):
        return _UNARY_OPS[type(node.op)](_eval(node.operand, symbols, expression))
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
        args = [_eval(a, symbols, expression) for a in node.args]
        return float(FUNCTIONS[node.func.id](*args))
    raise SpecError(f"Formula {expression!r} uses unsupported syntax")  # pragma: no cover


_EXACT_BINARY_OPS: dict[type[ast.operator], Callable[[Fraction, Fraction], Fraction]] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
}

MAX_EXACT_BITS = 100_000
"""The most bits ``evaluate_exact`` lets a numerator or denominator reach.

Every operation's result is checked, and a whole power is refused before it is computed
if its estimated size is over, so nested powers, products, and sums can't grow a value
without bound.
"""


def evaluate_exact(
    expression: str, symbols: Mapping[str, Fraction | Decimal | int], *, digits: int
) -> Fraction:
    """Evaluate ``expression`` exactly, for a value a standard defines, such as a gauge's.

    The same parser and allow-list as ``evaluate`` apply, so one expression is both
    evaluated and shown. Arithmetic is exact rational arithmetic, and a decimal literal is
    read as written. A power with a non-integer exponent has no exact value in general, so
    it alone is computed as a ``Decimal`` to ``digits`` significant digits and carried on
    exactly from there. Functions and ``pi`` have no exact value and are refused.

    Args:
        expression: The formula, e.g. ``"(w + c) / 16 / B"``.
        symbols: Each symbol's exact value. A float or a bool is refused: a float has
            already lost the exactness this evaluator exists for.
        digits: Significant digits for a non-integer power.

    Raises:
        UsageError: A symbol's value isn't an exact ``Fraction``, ``Decimal``, or ``int``,
            or ``digits`` is under 1.
        SpecError: The expression is malformed, calls a function, uses ``pi``, or names an
            unknown symbol.
        CalculationError: It divides by zero (including zero to a negative power),
            raises a negative number to a fractional power, or would make a value larger
            than ``MAX_EXACT_BITS``. Zero to the power zero is 1, as in ``evaluate``.
    """
    if isinstance(digits, bool) or not isinstance(digits, int) or digits < 1:
        raise UsageError(f"evaluate_exact() needs digits of 1 or more, not {digits!r}")
    exact: dict[str, Fraction] = {}
    for name, value in symbols.items():
        if isinstance(value, bool) or not isinstance(value, Fraction | Decimal | int):
            raise UsageError(
                f"evaluate_exact() needs exact values; {name} is {type(value).__name__} {value!r}"
            )
        if isinstance(value, Decimal) and not value.is_finite():
            raise UsageError(f"evaluate_exact() needs finite values; {name} is {value}")
        exact[name] = _bounded(Fraction(value))
    node = parse(expression)
    shown = render_symbolic(expression)
    try:
        return _exact(node, exact, expression, digits)
    except ZeroDivisionError:
        raise CalculationError(f"Division by zero in {shown}") from None
    except (ValueError, OverflowError, DecimalException) as exc:
        raise CalculationError(f"Cannot evaluate {shown} exactly: {exc}") from None


def _exact(
    node: ast.expr, symbols: Mapping[str, Fraction], expression: str, digits: int
) -> Fraction:
    if isinstance(node, ast.Constant):
        # parse() admits only int and float literals; a float reads as its shortest text.
        literal = (
            Fraction(node.value) if isinstance(node.value, int) else Fraction(repr(node.value))
        )
        return _bounded(literal)
    if isinstance(node, ast.Name):
        if node.id in CONSTANTS:
            raise SpecError(f"Formula {expression!r}: {node.id} has no exact value")
        if node.id in symbols:
            return symbols[node.id]
        raise SpecError(f"Formula {expression!r} refers to unknown symbol {node.id!r}")
    if isinstance(node, ast.BinOp):
        left = _exact(node.left, symbols, expression, digits)
        right = _exact(node.right, symbols, expression, digits)
        if isinstance(node.op, ast.Pow):
            return _bounded(_power(left, right, digits))
        return _bounded(_EXACT_BINARY_OPS[type(node.op)](left, right))
    if isinstance(node, ast.UnaryOp):
        operand = _exact(node.operand, symbols, expression, digits)
        return -operand if isinstance(node.op, ast.USub) else operand
    if isinstance(node, ast.Call):
        raise SpecError(f"Formula {expression!r}: functions have no exact value")
    raise SpecError(f"Formula {expression!r} uses unsupported syntax")  # pragma: no cover


def _bits(value: Fraction) -> int:
    return max(value.numerator.bit_length(), value.denominator.bit_length())


def _bounded(value: Fraction) -> Fraction:
    if _bits(value) > MAX_EXACT_BITS:
        raise ValueError(f"a value would exceed {MAX_EXACT_BITS} bits")
    return value


def _power(base: Fraction, exponent: Fraction, digits: int) -> Fraction:
    if base == 0:
        if exponent < 0:
            raise ZeroDivisionError
        return Fraction(1 if exponent == 0 else 0)
    if exponent.denominator == 1:
        if abs(base) == 1:
            return Fraction(-1 if base < 0 and exponent.numerator % 2 else 1)
        if abs(exponent.numerator) * _bits(base) > MAX_EXACT_BITS:
            raise ValueError(f"a value would exceed {MAX_EXACT_BITS} bits")
        return base**exponent.numerator
    if base < 0:
        raise ValueError("the result is not a real number")
    with localcontext() as context:
        context.prec = digits
        b = Decimal(base.numerator) / Decimal(base.denominator)
        e = Decimal(exponent.numerator) / Decimal(exponent.denominator)
        try:
            result = b**e
        except Overflow:
            raise ValueError(f"a value would exceed {MAX_EXACT_BITS} bits") from None
    # Ten is a little over three bits, so this bounds the Fraction the Decimal becomes.
    if (abs(result.adjusted()) + digits) * 4 > MAX_EXACT_BITS:
        raise ValueError(f"a value would exceed {MAX_EXACT_BITS} bits")
    return Fraction(result)


_TOKEN = re.compile(r"\d+\.?\d*(?:[eE][-+]?\d+)?|\.\d+|[A-Za-z_]\w*|\*\*|\*")


def _render(expression: str, name_text: Callable[[str], str]) -> str:
    def replace(m: re.Match[str]) -> str:
        lexeme = m.group(0)
        if lexeme == "**":
            return "^"
        if lexeme == "*":
            return "·"
        if lexeme[0].isalpha() or lexeme[0] == "_":
            return name_text(lexeme)
        return lexeme

    return _TOKEN.sub(replace, expression)


def render_symbolic(expression: str) -> str:
    """``pi/180*A*(R + K*T)`` → ``π/180·A·(R + K·T)``."""
    return _render(expression, lambda name: DISPLAY_NAMES.get(name, name))


def render_numeric(expression: str, values: Mapping[str, str]) -> str:
    """Render with each symbol replaced by its pre-formatted value text."""
    return _render(expression, lambda name: values.get(name) or DISPLAY_NAMES.get(name, name))
