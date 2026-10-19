"""The Geometry domain: everyday plane figures, with no shared settings (ADR-0018 §1)."""

from __future__ import annotations

from caddcalc.core import N_, Domain

DOMAIN = Domain(
    id="geometry",
    name=N_("Geometry"),
    summary=N_(
        "Areas, perimeters, and angles of plane figures: circles, rectangles, triangles, "
        "regular polygons, and arcs."
    ),
)
