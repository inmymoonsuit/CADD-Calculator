"""Built-in domains and calculators, one subpackage per domain, and the default registry.

This layer decides which domains and calculators exist. ``caddcalc.core`` only provides
the machinery (ADR-0003, ADR-0006, ADR-0013). To add a domain, create a subpackage that
exposes ``DOMAIN`` and a ``CALCULATORS`` tuple, and add them to ``BUILTIN_DOMAINS`` and
``BUILTIN_CALCULATORS``; see CONTRIBUTING.md.
"""

from caddcalc.calculators import sheet_metal
from caddcalc.core.registry import Registry

BUILTIN_DOMAINS = (sheet_metal.DOMAIN,)
BUILTIN_CALCULATORS = (*sheet_metal.CALCULATORS,)


def default_registry(*, load_plugins: bool = True) -> Registry:
    """Build a registry of the built-in domains and calculators, plus installed plugins.

    Every domain, built-in or plugin, is registered before any calculator.

    Args:
        load_plugins: Also register what installed packages advertise through the
            ``caddcalc.domains`` and ``caddcalc.calculators`` entry-point groups.

    Returns:
        A new registry. Plugin load failures are recorded in its ``plugin_errors``.
    """
    registry = Registry()
    for domain in BUILTIN_DOMAINS:
        registry.register_domain(domain)
    if load_plugins:
        registry.load_plugin_domains()
    for calc in BUILTIN_CALCULATORS:
        registry.register(calc)
    if load_plugins:
        registry.load_plugin_calculators()
    return registry
