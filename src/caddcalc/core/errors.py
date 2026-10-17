"""Exception types shared by the core and the front ends."""

from typing import override


class CaddCalcError(Exception):
    """Base class for all errors raised by caddcalc."""


class InputError(CaddCalcError):
    """A user-supplied value is missing, unparseable, or out of range."""


class CalculationError(CaddCalcError):
    """A formula could not be evaluated, e.g. division by zero or a math domain error."""


class SpecError(CaddCalcError):
    """A calculator definition is malformed. This is a bug in the calculator, not in user input."""


class _NotFoundError(CaddCalcError, KeyError):
    """A failed lookup by ID. Unlike a plain ``KeyError``, its message prints unquoted."""

    @override
    def __str__(self) -> str:
        return str(self.args[0]) if self.args else ""


class UnknownCalculatorError(_NotFoundError):
    """No calculator with the requested id is registered."""


class UnknownDomainError(_NotFoundError):
    """No domain with the requested id is registered."""
