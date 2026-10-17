"""Built-in calculators, one subpackage per domain.

To add a domain (e.g. ``tolerancing``), create a subpackage that exposes a
``CALCULATORS`` tuple and add it below. See CONTRIBUTING.md, "Adding a calculator".
"""

from caddcalc.calculators import sheet_metal

BUILTIN_CALCULATORS = (*sheet_metal.CALCULATORS,)
