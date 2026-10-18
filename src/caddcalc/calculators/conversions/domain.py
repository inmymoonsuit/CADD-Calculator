"""The Conversions domain: unit converters, with no shared settings (ADR-0018 §1)."""

from __future__ import annotations

from caddcalc.core import N_, Domain

DOMAIN = Domain(
    id="conversions",
    name=N_("Conversions"),
    summary=N_(
        "One value in every unit of its kind at once: lengths, angles, areas, and stresses."
    ),
)
