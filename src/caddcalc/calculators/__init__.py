"""Built-in domains and calculators, one subpackage per domain, and the default registry.

This layer decides which domains and calculators exist. ``caddcalc.core`` only provides
the machinery (ADR-0003, ADR-0006, ADR-0013). To add a domain, create a subpackage that
exposes ``DOMAIN`` and a ``CALCULATORS`` tuple, and add them to ``BUILTIN_DOMAINS`` and
``BUILTIN_CALCULATORS``; see CONTRIBUTING.md.
"""

from importlib import metadata

from caddcalc.calculators import conversions, geometry, sheet_metal
from caddcalc.calculators.sheet_metal.gauges import GAUGE_TABLE
from caddcalc.calculators.sheet_metal.materials import MATERIAL_TABLE
from caddcalc.core.refdata import TableSpec
from caddcalc.core.registry import EntryPointSource, Registry

BUILTIN_DOMAINS = (geometry.DOMAIN, conversions.DOMAIN, sheet_metal.DOMAIN)
"""In the order they're listed: general tools first (ADR-0018 §1)."""
BUILTIN_CALCULATORS = (
    *geometry.CALCULATORS,
    *conversions.CALCULATORS,
    *sheet_metal.CALCULATORS,
)
REFERENCE_TABLES: tuple[TableSpec, ...] = (GAUGE_TABLE, MATERIAL_TABLE)
"""Every reference table the built-in domains ship (ADR-0014 §1)."""


def default_registry(
    *, load_plugins: bool = True, entry_points: EntryPointSource = metadata.entry_points
) -> Registry:
    """Build a registry of the built-in domains and calculators, plus installed plugins.

    Every domain, built-in or plugin, is registered before any calculator.

    Args:
        load_plugins: Also register what installed packages advertise through the
            ``caddcalc.domains`` and ``caddcalc.calculators`` entry-point groups.
        entry_points: Where to find those entry points. Tests pass a fake.

    Returns:
        A new registry. Plugin load failures are recorded in its ``plugin_errors``.
    """
    registry = Registry(entry_points=entry_points)
    for domain in BUILTIN_DOMAINS:
        registry.register_domain(domain)
    if load_plugins:
        registry.load_plugin_domains()
    for calc in BUILTIN_CALCULATORS:
        registry.register(calc)
    if load_plugins:
        registry.load_plugin_calculators()
    return registry
