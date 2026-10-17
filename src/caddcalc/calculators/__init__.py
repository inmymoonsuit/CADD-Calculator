"""Built-in calculators, one subpackage per domain, and the default registry.

This layer decides which calculators exist. ``caddcalc.core`` only provides the
machinery (ADR-0003, ADR-0006). To add a domain, create a subpackage that exposes a
``CALCULATORS`` tuple and add it to ``BUILTIN_CALCULATORS``; see CONTRIBUTING.md.
"""

from caddcalc.calculators import sheet_metal
from caddcalc.core.registry import Registry

BUILTIN_CALCULATORS = (*sheet_metal.CALCULATORS,)


def default_registry(*, load_plugins: bool = True) -> Registry:
    """Build a registry of the built-in calculators, plus installed plugins.

    Args:
        load_plugins: Also register calculators advertised by installed packages
            through the ``caddcalc.calculators`` entry-point group.

    Returns:
        A new registry. Plugin load failures are recorded in its ``plugin_errors``.
    """
    registry = Registry()
    for calc in BUILTIN_CALCULATORS:
        registry.register(calc)
    if load_plugins:
        registry.load_plugins()
    return registry
