"""CADD Calculator: open-source calculators for computer-aided drafting and design.

The package is layered (see docs/dev/architecture.md):

* ``caddcalc.core``: units, the formula evaluator, the calculator model, and the registry.
  Standard library only.
* ``caddcalc.calculators``: built-in calculators, grouped by domain (sheet metal, ...).
* ``caddcalc.cli`` and ``caddcalc.gui``: thin front ends over the core.
"""

__version__ = "0.1.0a1"
