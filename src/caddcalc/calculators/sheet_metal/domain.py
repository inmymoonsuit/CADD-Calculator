"""The sheet-metal domain, the settings its calculators share, and its choices.

Each setting declares the shared quantity: its key, symbol, label, dimension, and range
(ADR-0013). The calculators' parameters in ``common.py`` are built from these settings,
adding their own defaults, help, and method scoping, so a shared key can't drift from its
setting. The gauge choice derives the thickness (ADR-0014 §2; ``gauges.py``). The material
and temper choices derive nothing; result checks read them (§3; ``materials.py``).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from caddcalc.calculators.sheet_metal.gauges import GAUGE, GAUGE_TABLE, GaugeResolver
from caddcalc.calculators.sheet_metal.materials import (
    MATERIAL,
    MATERIAL_TABLE,
    TEMPER,
    MaterialResolver,
)
from caddcalc.core import (
    DerivedValue,
    Dimension,
    Domain,
    Fact,
    Option,
    Param,
    SpecError,
    StartingValue,
)

DOMAIN_ID = "sheet_metal"

THICKNESS_SETTING = Param(
    "thickness",
    "T",
    "Material thickness",
    Dimension.LENGTH,
    minimum=0.0,
    min_inclusive=False,
    help=(
        "Sheet thickness for every sheet-metal calculator that uses it. Enter the decimal "
        "thickness, or choose a gauge; a thickness entered here takes precedence over the "
        "gauge. Gauge numbers mean different thicknesses in different gauge systems."
    ),
)
INSIDE_RADIUS_SETTING = Param(
    "inside_radius",
    "R",
    "Inside bend radius",
    Dimension.LENGTH,
    minimum=0.0,
    help="Radius on the inside surface of the bend, for every calculator that uses it.",
)
K_FACTOR_SETTING = Param(
    "k_factor",
    "K",
    "K-factor",
    Dimension.RATIO,
    minimum=0.0,
    maximum=1.0,
    help=(
        "Neutral-axis position as a fraction of thickness, measured from the inside surface. "
        "Cited starting values: 0.445 for aircraft aluminum (FAA-H-8083-31B, p. 4-63); about "
        "0.408 for aluminum and soft steel and 0.452 for cold-rolled steel, implied by "
        "Machinery's Handbook (31st ed., p. 1421, Eqs (33) and (34)); and the textbook's 0.4. "
        "It approaches 0.5 for large R/T. Use your shop's test-bend value for production. "
        "Used by K-factor methods; course methods have the factor built in."
    ),
)


class SheetMetalResolver:
    """The domain's resolver: the gauge choice, then the material and temper choices.

    Each part resolves its own choices from its own table, and only the gauge derives a
    value.
    """

    def __init__(self, gauges: GaugeResolver, materials: MaterialResolver) -> None:
        """Combine the gauge resolver and the material resolver."""
        self.gauges = gauges
        self.materials = materials

    def options(self, choice: str, parents: Mapping[str, str]) -> Sequence[Option]:
        """Return the options of ``choice`` from the part that owns it."""
        if choice == GAUGE.key:
            return self.gauges.options(choice, parents)
        return self.materials.options(choice, parents)

    def facts(self, selections: Mapping[str, str]) -> Sequence[Fact]:
        """Return the chosen material's facts (``SelectionDetails``)."""
        return self.materials.facts(selections)

    def starting_values(self, selections: Mapping[str, str]) -> Sequence[StartingValue]:
        """Return the chosen material's K starting values (``SelectionDetails``)."""
        return self.materials.starting_values(selections)

    def derive(self, selections: Mapping[str, str]) -> Mapping[str, DerivedValue]:
        """Return what the parts derive from ``selections``; they never derive the same key."""
        gauge, material = self.gauges.derive(selections), self.materials.derive(selections)
        both = sorted(set(gauge) & set(material))
        if both:
            raise SpecError(f"The gauge and the material both derive {both}")
        return {**gauge, **material}


GAUGES = GaugeResolver(DOMAIN_ID, THICKNESS_SETTING)
"""The gauge part of the resolver, which result checks also read."""
MATERIALS = MaterialResolver(K_FACTOR_SETTING)
"""The material part of the resolver, which result checks also read."""
RESOLVER = SheetMetalResolver(GAUGES, MATERIALS)
"""The domain's resolver, which also tells what its selections mean."""

DOMAIN = Domain(
    id=DOMAIN_ID,
    name="Sheet Metal",
    summary="Bends, flat patterns, press-brake tooling, and developments of sheet-metal parts.",
    settings=(THICKNESS_SETTING, INSIDE_RADIUS_SETTING, K_FACTOR_SETTING),
    choices=(GAUGE, MATERIAL, TEMPER),
    resolver=RESOLVER,
    tables=(GAUGE_TABLE, MATERIAL_TABLE),
    details=RESOLVER,
)
