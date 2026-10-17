"""Exception types shared by the core and the front ends."""


class CaddCalcError(Exception):
    """Base class for all errors raised by caddcalc."""


class InputError(CaddCalcError):
    """A user-supplied value is missing, unparseable, or out of range."""


class CalculationError(CaddCalcError):
    """A formula could not be evaluated, e.g. division by zero or a math domain error."""


class SpecError(CaddCalcError):
    """A calculator definition is malformed. This is a bug in the calculator, not in user input."""


class UnknownCalculatorError(CaddCalcError, KeyError):
    """No calculator with the requested id is registered."""


class UnknownDomainError(CaddCalcError, KeyError):
    """No domain with the requested id is registered."""
