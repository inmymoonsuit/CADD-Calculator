"""The bend check: a bend's inside radius against its material's cited minimum (ADR-0014 §3).

It is a result check (``Calculator.checks``): it runs after a bend calculator's compute and
reads the gauge, material, and temper the user chose, which compute never sees. Where a
cited minimum applies it replaces the phase 1 rule of thumb, an inside radius below the
thickness, so the two can't contradict each other; where none applies, the note says so
and the rule of thumb still speaks.

Each note leads with its verdict and numbers, and its detail and sources follow (ADR-0017
F1). The wording is whole sentences with named fields: values are filled in the user's
display units when shown, and every name, source, and stated value comes from the data
as a phrase, so the scope of each value reads exactly as its source states it (ADR-0014
§5.5).
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
from caddcalc.core import Context, Dimension, NoteKind, Reference, SourceKind

MAX_ANGLE = 90.0
"""The largest bend angle, in degrees, that the minimum radii are read for.

The sources are for 90° bends or state no angle. A bend up to 90° takes the 90° value, and
one past it has no applicable value (the maintainer's decision D10).
"""

LENGTH = Dimension.LENGTH

RULE_OF_THUMB = (
    "Inside radius {R} is less than the thickness {T}. This is a rule of thumb, not a cited limit."
)
RULE_OF_THUMB_DETAIL = (
    "Check the material's minimum bend radius; tight bends can crack, especially in hard tempers."
)
GAUGE_MISMATCH = (
    "The gauge system may not suit the material: {gauge}, {system} gives a nominal {T}, "
    "but {material} is ordered by {usual} gauge numbers."
)
GAUGE_MISMATCH_DETAIL = (
    "The same gauge number is a different thickness in each system, so check the "
    "thickness, or enter it as a decimal."
)
K_MISMATCH = "K = {stated} is a starting value {source} gives for {covered}, not for {material}."
K_MISMATCH_DETAIL = "Confirm it with a test bend."
K_MISMATCH_OFFERED = (
    "Confirm it with a test bend, or apply a starting value given for this material."
)
NO_SOURCE_FOR = "no minimum radius to check for {material}."
NO_SOURCE_LISTS = "no minimum radius to check for {material}: no source lists it."
PAST_90 = (
    "bend angle {symbol_1} = {angle_1} is past 90°, and the minimum radii for {material} "
    "are for bends up to 90°."
)
PAST_90_MANY = (
    "bend angles {angles} are past 90°, and the minimum radii for {material} are for bends "
    "up to 90°."
)
PAST_90_DETAIL = "No source covers larger bends or hems."
# Templates with "{i}" are said once per bend or source: "{i}" becomes its number, so
# each one's fields are named apart, e.g. "{source_1}" and "{source_2}".
ANGLE = "{symbol_{i}} = {angle_{i}}"
THICKNESS_UNCOVERED = "thickness {T} is outside every minimum-radius source for {material}."
LISTS = "{source_{i}} lists {coverage_{i}}."
PARTIAL = (
    "Checked against {alone} only: {other} lists {material} for {coverage}, and {T} is "
    "outside that."
)
LIMIT = (
    "inside radius {R} is below {minimum}, the recommended minimum this check uses, for "
    "{material} at {T}, in {practice}."
)
GIVES_AT = "{source_{i}} gives {stated_{i}} at {column_{i}}"
GIVES_FOR_SHEET = "{source_{i}} gives {stated_{i}} for sheet {column_{i}}"
FROM_ROW = ", from {label_{i}}"
LARGER = "The larger minimum governs."
RANGE = "A range is checked at its upper bound."
LARGER_AND_RANGE = "The larger minimum governs, and a range is checked at its upper bound."
SOURCE_NOTE = "{note_{i}}"
PRACTICE = "{advice}"

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
    * A part with bends on both sides of 90° is checked for the bends up to 90°, and its
      bends past 90° get their own no-applicable-value note. The rule of thumb speaks only
      when no bend was checked against a source, so the two never contradict.
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
            self._check_applied_k(ctx, material, temper, selections)
            referenced = self._check_minimum(ctx, material, temper)
        if not referenced and ctx["inside_radius"] < ctx["thickness"]:
            # A rule of thumb, not a cited limit: published minimums go below 1T for some
            # alloys and tempers, so this is a warning.
            ctx.warn(
                RULE_OF_THUMB,
                subjects=_RADIUS,
                detail=RULE_OF_THUMB_DETAIL,
                quantities={"R": (ctx["inside_radius"], LENGTH), "T": (ctx["thickness"], LENGTH)},
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
            GAUGE_MISMATCH,
            subjects=("thickness",),
            detail=GAUGE_MISMATCH_DETAIL,
            quantities={"T": (ctx["thickness"], LENGTH)},
            phrases={
                "gauge": gauge.label,
                "system": system.group,
                "material": material.name_in(temper),
                "usual": usual,
            },
        )

    def _check_applied_k(
        self,
        ctx: Context,
        material: Material,
        temper: str | None,
        selections: Mapping[str, str],
    ) -> None:
        """Warn when the K-factor in use was applied for other materials than this one.

        An applied starting value keeps its citation when the material changes, so its
        source would otherwise read as covering a material it doesn't. A calculator's copy of
        one keeps the citation too (an explicit source with a reference), and is checked
        the same way. The warning offers a starting value for this material only when one
        is given for it.
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
        offered = bool(self.materials.starting_values(selections))
        ctx.warn(
            K_MISMATCH,
            subjects=("k_factor",),
            detail=K_MISMATCH_OFFERED if offered else K_MISMATCH_DETAIL,
            phrases={
                "stated": start.value.text,
                "source": short(start.source),
                "covered": covered,
                "material": material.name_in(temper),
            },
        )

    def _check_minimum(self, ctx: Context, material: Material, temper: str | None) -> bool:
        """Check the inside radius against the material's sources; say whether one applied."""
        name = material.name_in(temper)
        if material.radius_note:
            ctx.note(
                NO_SOURCE_FOR,
                NoteKind.NO_APPLICABLE_VALUE,
                subjects=_RADIUS,
                detail="{why}",
                phrases={"material": name, "why": material.radius_note},
            )
            return False
        sources = self.materials.materials.radius_sources(material.key, temper)
        if not sources:
            ctx.note(
                NO_SOURCE_LISTS,
                NoteKind.NO_APPLICABLE_VALUE,
                subjects=_RADIUS,
                phrases={"material": name},
            )
            return False
        cited = tuple(s.source.reference for s in sources)
        thickness = ctx["thickness"]
        past = [k for k in self.angle_keys if ctx[k] > MAX_ANGLE]
        if past:  # those bends aren't covered; any up to 90° are checked below
            numbered = list(enumerate(past, 1))
            angles = and_list(ANGLE.replace("{i}", str(i)) for i, _ in numbered)
            ctx.note(
                PAST_90 if len(past) == 1 else PAST_90_MANY.replace("{angles}", angles),
                NoteKind.NO_APPLICABLE_VALUE,
                references=cited,
                subjects=past,
                detail=PAST_90_DETAIL,
                quantities={f"angle_{i}": (ctx[k], Dimension.ANGLE) for i, k in numbered},
                phrases={"material": name} | {f"symbol_{i}": _symbol(ctx, k) for i, k in numbered},
            )
            if len(past) == len(self.angle_keys):
                return False
        found = [(source, source.at(thickness)) for source in sources]
        covering = [(source, value) for source, value in found if value is not None]
        if not covering:
            listing = list(enumerate(sources, 1))
            ctx.note(
                THICKNESS_UNCOVERED,
                NoteKind.NO_APPLICABLE_VALUE,
                references=cited,
                subjects=("thickness",),
                detail=" ".join(LISTS.replace("{i}", str(i)) for i, _ in listing),
                quantities={"T": (thickness, LENGTH)},
                phrases={"material": name}
                | {f"source_{i}": _short(s) for i, s in listing}
                | {f"coverage_{i}": s.coverage for i, s in listing},
            )
            return False
        alone = and_list(_short(s) for s, _ in covering)
        for source, value in found:
            if value is None:
                # A warning: the check still applies, through the sources that cover it.
                ctx.warn(
                    PARTIAL,
                    subjects=("thickness",),
                    quantities={"T": (thickness, LENGTH)},
                    phrases={
                        "alone": alone,
                        "other": _short(source),
                        "material": name,
                        "coverage": source.coverage,
                    },
                )
        minimum = max(value.minimum(thickness) for _, value in covering)
        radius = ctx["inside_radius"]
        if radius < minimum and not math.isclose(radius, minimum, rel_tol=_SAME):
            detail, phrases = _limit_detail(covering)
            ctx.note(
                LIMIT,
                NoteKind.LIMIT_EXCEEDED,
                references=_references(covering),
                subjects=_RADIUS,
                detail=detail,
                quantities={
                    "R": (radius, LENGTH),
                    "minimum": (minimum, LENGTH),
                    "T": (thickness, LENGTH),
                },
                phrases={"material": name, "practice": practices(s for s, _ in covering)} | phrases,
            )
            # Only beside a limit: a standing note on every passing bend would be ignored.
            practice = self.materials.materials.practice
            ctx.note(
                PRACTICE,
                references=(practice.source.reference,),
                subjects=("inside_radius",),
                phrases={"advice": practice.note},
            )
        return True


def _limit_detail(
    covering: Sequence[tuple[RadiusSource, RadiusValue]],
) -> tuple[str, dict[str, str]]:
    """Say what each source gives, and how far it applies (ADR-0014 §5.5).

    That's each source's recommended minimum and the thickness it's read at, as the
    source states them, then any stand-in label, how the check decided, and the sources'
    own notes. Return the detail's template and its phrases.
    """
    sentences: list[str] = []
    phrases: dict[str, str] = {}
    for i, (source, value) in enumerate(covering, 1):
        gives = GIVES_AT if source.listed else GIVES_FOR_SHEET
        sentence = gives + (FROM_ROW if source.label else "") + "."
        sentences.append(sentence.replace("{i}", str(i)))
        phrases |= {
            f"source_{i}": _short(source),
            f"stated_{i}": value.stated,
            f"column_{i}": value.column,
            f"label_{i}": source.label,
        }
    larger = len(covering) > 1
    ranged = any(isinstance(v.value, tuple) and v.value[0] != v.value[1] for _, v in covering)
    if larger or ranged:
        sentences.append(LARGER_AND_RANGE if larger and ranged else LARGER if larger else RANGE)
    for i, (source, _value) in enumerate(covering, 1):
        if source.note:
            sentences.append(SOURCE_NOTE.replace("{i}", str(i)))
            phrases[f"note_{i}"] = source.note
    return " ".join(sentences), phrases


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
