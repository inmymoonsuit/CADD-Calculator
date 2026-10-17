"""The bend check: a bend's inside radius against its material's cited minimum (ADR-0014 §3).

It is a result check (``Calculator.checks``): it runs after a bend calculator's compute and
reads the gauge, material, and temper the user chose, which compute never sees. Where a
cited minimum applies it replaces the phase 1 rule of thumb, an inside radius below the
thickness, so the two can't contradict each other; where none applies, the note says so
and the rule of thumb still speaks.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence

from caddcalc.calculators.sheet_metal.gauges import GAUGE, GaugeResolver
from caddcalc.calculators.sheet_metal.materials import (
    MATERIAL,
    TEMPER,
    Material,
    MaterialResolver,
    RadiusSource,
    RadiusValue,
    and_list,
    practices,
    short,
)
from caddcalc.core import Context, NoteKind, Reference, SourceKind

MAX_ANGLE = 90.0
"""The largest bend angle, in degrees, that the minimum radii are read for.

The sources are for 90° bends or state no angle. A bend up to 90° takes the 90° value, and
one past it has no applicable value (the maintainer's decision D10).
"""

_RADIUS = ("inside_radius", "thickness")
_SAME = 1e-9
"""Relative difference under which a radius counts as equal to its minimum, so a radius
typed as the minimum isn't flagged for a difference in its last bit."""


class BendCheck:
    """Checks a bend calculator's run against the chosen material (ADR-0014 §3).

    * A gauge thickness from a system the material isn't ordered by gets a warning (flag 9).
    * A K starting value applied for other materials than the chosen one gets a warning.
    * With a material whose sources cover the case, the inside radius is checked against
      the larger of their recommended minimums (D1), each range at its upper bound (D2),
      and every source is shown with the practice it comes from. A radius below it also
      gets the sources' bending practice.
    * Where no source covers the case, a no-applicable-value note says why: no source for
      the material, a bend past 90° (D10), or a thickness no source lists (D4). Then, as
      with no material chosen, an inside radius below the thickness gets the rule of thumb.
    """

    def __init__(
        self, materials: MaterialResolver, gauges: GaugeResolver, angle_keys: Sequence[str]
    ) -> None:
        """Check runs against ``materials`` and ``gauges``, at the bends ``angle_keys`` name."""
        self.materials = materials
        self.gauges = gauges
        self.angle_keys = tuple(angle_keys)

    def __call__(self, ctx: Context, selections: Mapping[str, str], /) -> None:
        """Add the check's notes to a finished run."""
        material = None
        if MATERIAL.key in selections:
            material = self.materials.materials.by_key[selections[MATERIAL.key]]
        referenced = False
        if material is not None:
            temper = selections.get(TEMPER.key)
            self._check_gauge(ctx, material, temper, selections.get(GAUGE.key))
            self._check_applied_k(ctx, material, temper)
            referenced = self._check_minimum(ctx, material, temper)
        if not referenced and ctx["inside_radius"] < ctx["thickness"]:
            # A rule of thumb, not a cited limit: published minimums go below 1T for some
            # alloys and tempers, so this is a warning.
            ctx.warn(
                "Inside radius is smaller than the material thickness. Check the material's "
                "minimum bend radius; tight bends can crack, especially in hard tempers.",
                subjects=_RADIUS,
            )

    def _check_gauge(
        self, ctx: Context, material: Material, temper: str | None, gauge_key: str | None
    ) -> None:
        """Warn when the gauge's system isn't one the material is ordered by (flag 9).

        Only a run whose thickness comes from the gauge is warned, by its source, not its
        value: a thickness the user typed doesn't depend on the gauge's system, even when it
        equals the gauge's. A calculator's copy of the gauge's thickness keeps the gauge
        table as its explicit source's reference, and is warned the same way.
        """
        thickness = ctx.sources.get("thickness")
        kinds = (SourceKind.DERIVED, SourceKind.EXPLICIT)
        if gauge_key is None or thickness is None or thickness.kind not in kinds:
            return
        gauges = self.gauges.gauges
        system, gauge = gauges.by_key[gauge_key]
        if system.id in material.gauges or thickness.reference != gauges.table.reference:
            return
        usual = " or ".join(s.name for s in gauges.systems if s.id in material.gauges)
        ctx.warn(
            f"The gauge is {gauge.label}, {system.group}, but {material.name_in(temper)} is "
            f"ordered by {usual} gauge numbers. Each system gives a gauge number a different "
            "thickness, so check the thickness, or enter it as a decimal.",
            subjects=("thickness",),
        )

    def _check_applied_k(self, ctx: Context, material: Material, temper: str | None) -> None:
        """Warn when the K-factor in use was applied for other materials than this one.

        An applied starting value keeps its citation when the material changes, so its
        source would otherwise read as covering a material it doesn't. A calculator's copy of
        one keeps the citation too (an explicit source with a reference), and is checked
        the same way.
        """
        source = ctx.sources.get("k_factor")
        applied = source is not None and source.kind in (SourceKind.DOMAIN, SourceKind.EXPLICIT)
        if source is None or not applied or source.reference is None:
            return
        data = self.materials.materials
        start = next((k for k in data.k_starts if k.source.reference == source.reference), None)
        if start is None or material.key in start.materials:
            return
        covered = and_list(
            m.name_in(m.tempers[0].key) for m in data.materials if m.key in start.materials
        )
        ctx.warn(
            f"The K starting value from {short(start.source)} was given for {covered}, not "
            f"for {material.name_in(temper)}; confirm it with a test bend.",
            subjects=("k_factor",),
        )

    def _check_minimum(self, ctx: Context, material: Material, temper: str | None) -> bool:
        """Check the inside radius against the material's sources; say whether one applied."""
        name = material.name_in(temper)
        if material.radius_note:
            ctx.note(material.radius_note, NoteKind.NO_APPLICABLE_VALUE, subjects=_RADIUS)
            return False
        sources = self.materials.materials.radius_sources(material.key, temper)
        if not sources:
            ctx.note(
                f"No minimum-radius source lists {name}.",
                NoteKind.NO_APPLICABLE_VALUE,
                subjects=_RADIUS,
            )
            return False
        cited = tuple(s.source.reference for s in sources)
        past = [k for k in self.angle_keys if ctx[k] > MAX_ANGLE]
        if past:
            ctx.note(
                f"The minimum radii for {name} are for bends up to 90°, and "
                f"{and_list(_symbol(ctx, k) for k in past)} {'is' if len(past) == 1 else 'are'} "
                "past 90°. No source covers larger bends or hems.",
                NoteKind.NO_APPLICABLE_VALUE,
                references=cited,
                subjects=past,
            )
            return False
        thickness = ctx["thickness"]
        found = [(source, source.at(thickness)) for source in sources]
        covering = [(source, value) for source, value in found if value is not None]
        if not covering:
            listed = and_list(f"{_short(s)} lists {s.coverage}" for s in sources)
            ctx.note(
                f"The minimum-radius sources for {name} don't cover this thickness: {listed}.",
                NoteKind.NO_APPLICABLE_VALUE,
                references=cited,
                subjects=("thickness",),
            )
            return False
        alone = and_list(_short(s) for s, _ in covering)
        for source, value in found:
            if value is None:
                # A warning: the check still applies, through the sources that cover it.
                ctx.warn(
                    f"{_short(source)} lists {source.coverage} for {name}, which doesn't reach "
                    f"this thickness, so the check uses {alone} alone.",
                    subjects=("thickness",),
                )
        minimum = max(value.minimum(thickness) for _, value in covering)
        radius = ctx["inside_radius"]
        if radius < minimum and not math.isclose(radius, minimum, rel_tol=_SAME):
            ctx.note(
                _limit(name, covering),
                NoteKind.LIMIT_EXCEEDED,
                references=_references(covering),
                subjects=_RADIUS,
            )
            # Only beside a limit: a standing note on every passing bend would be ignored.
            practice = self.materials.materials.practice
            ctx.note(
                practice.note,
                references=(practice.source.reference,),
                subjects=("inside_radius",),
            )
        return True


def _limit(name: str, covering: Sequence[tuple[RadiusSource, RadiusValue]]) -> str:
    """Say what the radius is below, and how far that applies (ADR-0014 §5.5).

    That is each source's recommended minimum, as the source states it, and the practice
    it comes from.
    """
    sources = [source for source, _ in covering]
    given = []
    for source, value in covering:
        where = f"at {value.column}" if source.listed else f"for sheet {value.column}"
        label = f" ({source.label})" if source.label else ""
        given.append(f"{_short(source)} gives {value.stated} {where}{label}")
    text = (
        f"The inside radius is below the recommended minimum for {name} in "
        f"{practices(sources)} at this thickness: {and_list(given)}."
    )
    if len(covering) > 1:
        text += " The check uses the larger."
    if any(isinstance(v.value, tuple) and v.value[0] != v.value[1] for _, v in covering):
        text += " A range is checked at its upper bound."
    return " ".join([text, *(source.note for source, _ in covering if source.note)])


def _references(covering: Sequence[tuple[RadiusSource, RadiusValue]]) -> tuple[Reference, ...]:
    """Every source of the minimum, then the sources its notes cite."""
    sources = [source for source, _ in covering]
    cited = [s.source.reference for s in sources]
    cited += [extra.reference for s in sources for extra in s.see_also]
    return tuple(dict.fromkeys(cited))


def _short(source: RadiusSource) -> str:
    """Return a source's publication as note texts name it, e.g. ``"AC 43.13-1B"``."""
    return short(source.source)


def _symbol(ctx: Context, key: str) -> str:
    return next(p.symbol for p in ctx.calculator.params if p.key == key)
