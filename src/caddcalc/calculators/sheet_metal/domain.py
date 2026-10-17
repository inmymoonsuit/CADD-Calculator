"""The sheet-metal domain, the settings its calculators share, and its gauge choice.

Each setting declares the shared quantity: its key, symbol, label, dimension, and range
(ADR-0013). The calculators' parameters in ``common.py`` are built from these settings,
adding their own defaults, help, and method scoping, so a shared key can't drift from its
setting. The gauge choice derives the thickness (ADR-0014 §2; ``gauges.py``).
"""

from caddcalc.calculators.sheet_metal.gauges import GAUGE, GaugeResolver
from caddcalc.core import Dimension, Domain, Param

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
        "Machinery's Handbook (29th ed., p. 1347, Eqs 33 and 34); and the textbook's 0.4. It "
        "approaches 0.5 for large R/T. Use your shop's test-bend value for production. Used "
        "by K-factor methods; course methods have the factor built in."
    ),
)

DOMAIN = Domain(
    id=DOMAIN_ID,
    name="Sheet Metal",
    summary="Bends, flat patterns, press-brake tooling, and developments of sheet-metal parts.",
    settings=(THICKNESS_SETTING, INSIDE_RADIUS_SETTING, K_FACTOR_SETTING),
    choices=(GAUGE,),
    resolver=GaugeResolver(DOMAIN_ID, THICKNESS_SETTING),
)
