"""The sheet-metal domain and the settings its calculators share (ADR-0013).

Each setting declares the shared quantity: its key, symbol, label, dimension, and range.
The calculators' parameters in ``common.py`` are built from these settings, adding their
own defaults, help, and method scoping, so a shared key can't drift from its setting.
"""

from caddcalc.core import Dimension, Domain, Param

THICKNESS_SETTING = Param(
    "thickness",
    "T",
    "Material thickness",
    Dimension.LENGTH,
    minimum=0.0,
    min_inclusive=False,
    help="Sheet thickness for every sheet-metal calculator that uses it.",
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
        "Used by K-factor methods; course methods have the factor built in."
    ),
)

DOMAIN = Domain(
    id="sheet_metal",
    name="Sheet Metal",
    summary="Bends, flat patterns, press-brake tooling, and developments of sheet-metal parts.",
    settings=(THICKNESS_SETTING, INSIDE_RADIUS_SETTING, K_FACTOR_SETTING),
)
