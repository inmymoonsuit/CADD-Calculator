"""Test helpers: run calculators in inches, as the legacy spreadsheets did."""

from __future__ import annotations

from caddcalc.core import Calculator, Dimension
from caddcalc.core.units import from_base, to_base


def run_inches(calc: Calculator, method: str | None = None, **inputs: float) -> dict[str, float]:
    """Run with lengths in inches and angles in degrees. Returns outputs the same way."""
    base: dict[str, float] = {}
    for key, value in inputs.items():
        p = next(p for p in calc.params if p.key == key)
        base[key] = to_base(value, "in") if p.dimension is Dimension.LENGTH else value
    result = calc.run(base, method=method)
    return {
        o.key: from_base(result.outputs[o.key], "in")
        if o.dimension is Dimension.LENGTH
        else result.outputs[o.key]
        for o in calc.outputs
    }
