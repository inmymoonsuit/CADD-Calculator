"""The bend check: inside radius against the material's cited minimum (ADR-0014 §3).

The cases follow the maintainer's decisions D1–D4 and D10 and the 2b plan's flags, with
thicknesses and radii in inches.
"""

from __future__ import annotations

import pytest

from caddcalc.calculators.sheet_metal import (
    DOMAIN,
    BendAllowance,
    FormedSegmentFlatLength,
    TruncatedConeLayout,
    VDieOpening,
)
from caddcalc.calculators.sheet_metal.materials import MATERIAL_TABLE, load_materials
from caddcalc.core import DomainSettings, Note, NoteKind, Result
from caddcalc.core.formatting import describe_note

IN = 25.4
RULE_OF_THUMB = "Inside radius is smaller than the material thickness."
PRACTICE = "Form across the grain where possible"
LIMIT, GAP, WARNING = NoteKind.LIMIT_EXCEEDED, NoteKind.NO_APPLICABLE_VALUE, NoteKind.WARNING


def bend(
    thickness: float | None,
    radius: float,
    material: str | None = None,
    *,
    angle: float = 90.0,
    gauge: str | None = None,
) -> Result:
    """Run the bend allowance with the family's material and gauge, if any.

    A thickness of ``None`` takes the family's: the gauge's, when one is chosen.
    """
    settings = DomainSettings()
    if material is not None:
        settings = settings.set_choice(DOMAIN, "material", material)
    if gauge is not None:
        settings = settings.set_choice(DOMAIN, "gauge", gauge)
    inputs = {"inside_radius": radius * IN, "bend_angle": angle}
    if thickness is not None:
        inputs["thickness"] = thickness * IN
    return BendAllowance().run(inputs, "k_factor", settings=settings.for_domain(DOMAIN))


def kinds(result: Result) -> list[NoteKind]:
    return [n.kind for n in result.notes]


def notes(result: Result, kind: NoteKind) -> list[Note]:
    return [n for n in result.notes if n.kind is kind]


def rule_of_thumb(result: Result) -> bool:
    return any(n.text.startswith(RULE_OF_THUMB) for n in result.notes)


def test_only_the_bend_calculators_check_the_radius() -> None:
    """V-die opening and the cone take no check (flag 4)."""
    assert BendAllowance.checks and FormedSegmentFlatLength.checks
    assert VDieOpening.checks == () and TruncatedConeLayout.checks == ()


def test_without_a_material_the_rule_of_thumb_speaks_as_before() -> None:
    tight = bend(0.25, 0.1)
    assert [(n.kind, n.subjects) for n in tight.notes] == [
        (WARNING, ("inside_radius", "thickness"))
    ]
    assert rule_of_thumb(tight)
    assert bend(0.25, 0.3).notes == ()


@pytest.mark.parametrize(
    ("thickness", "radius", "exceeded"),
    [
        (0.063, 0.15, True),  # TO's 0.16 in governs AC's 2T, 0.126 in (D1)
        (0.063, 0.16, False),  # a radius equal to the minimum passes
        (0.182, 0.70, True),  # AC's 4T, 0.728 in, governs TO's 0.69 in (D1)
        (0.182, 0.73, False),
    ],
)
def test_6061_is_held_to_the_larger_source_at_each_thickness(
    thickness: float, radius: float, exceeded: bool
) -> None:
    result = bend(thickness, radius, "al:6061")
    limits = notes(result, LIMIT)
    assert bool(limits) == exceeded
    assert not rule_of_thumb(result), "a referenced check replaces the rule of thumb"
    practice = any(n.text.startswith(PRACTICE) for n in notes(result, WARNING))
    assert practice == exceeded, "bending practice only beside a limit"
    if exceeded:
        (limit,) = limits
        assert [r.short_title for r in limit.references] == ["AC 43.13-1B", "TO 1-1A-9"]
        assert limit.text.count("TO 1-1A-9 gives") == 1, "the text names the short title"
        assert "Engineering Series for Aircraft Repair" in describe_note(limit), "in full"
        assert "The check uses the larger." in limit.text
        assert limit.subjects == ("inside_radius", "thickness")
        assert "aircraft repair practice" in describe_note(limit), "each source's scope"


def test_a_range_is_checked_at_its_upper_bound_and_shown_whole() -> None:
    """5052-H32 at 0.064 in is ½T–1T: below 1T exceeds (D2)."""
    (limit,) = notes(bend(0.064, 0.05, "al:5052"), LIMIT)
    assert "½T–1T" in limit.text and "upper bound" in limit.text
    assert notes(bend(0.064, 0.064, "al:5052"), LIMIT) == []


def test_a_zero_minimum_allows_a_sharp_bend() -> None:
    result = bend(0.032, 0.0, "al:5052")
    assert notes(result, LIMIT) == [] and not rule_of_thumb(result)


def test_304_uses_the_half_hard_row_as_a_labelled_stand_in() -> None:
    """D3: 2T, from TO's only 304 row, with the generic annealed figure in the note."""
    (limit,) = notes(bend(0.05, 0.09, "ss:304"), LIMIT)
    assert "½ Hard" in limit.text and "about 1T" in limit.text
    assert "Change 14" in limit.references[-1].edition, "the 2015 edition's row is cited"


@pytest.mark.parametrize(
    ("material", "thickness", "listed"),
    [
        ("ss:304", 0.10, "0.012–0.090 in and 0.190–0.250 in"),  # Table 2-16's gap
        ("cs:a1008", 0.25, "0.016–0.187 in"),  # mild steel stops at 0.187 in (D4)
        ("al:6061", 0.30, "0.016–0.258 in and TO 1-1A-9 lists 0.012–0.250 in"),
    ],
)
def test_a_thickness_no_source_lists_is_said_aloud(
    material: str, thickness: float, listed: str
) -> None:
    result = bend(thickness, 0.01, material)
    (gap,) = notes(result, GAP)
    assert "don't cover this thickness" in gap.text and listed in gap.text
    assert gap.subjects == ("thickness",)
    assert notes(result, LIMIT) == []
    assert rule_of_thumb(result), "no referenced check applies, so the rule of thumb does"


def test_where_one_source_covers_the_thickness_it_is_used_alone() -> None:
    """Flag 5: AC lists nothing as thin as 0.012 in, so TO checks it alone."""
    result = bend(0.012, 0.02, "al:6061")
    (gap,) = notes(result, GAP)
    assert gap.text.startswith("AC 43.13-1B lists 0.016–0.258 in")
    assert "uses TO 1-1A-9 alone" in gap.text
    (limit,) = notes(result, LIMIT)
    assert "0.03 in" in limit.text and "uses the larger" not in limit.text


def test_a_bend_past_90_degrees_has_no_applicable_value() -> None:
    """D10: up to 90° takes the 90° value; past it, and hems, nothing applies."""
    result = bend(0.063, 0.05, "al:6061", angle=120)
    (gap,) = notes(result, GAP)
    assert "past 90°" in gap.text and gap.subjects == ("bend_angle",)
    assert notes(result, LIMIT) == [] and rule_of_thumb(result)
    assert notes(bend(0.063, 0.05, "al:6061", angle=45), LIMIT), "under 90° takes the 90° value"

    settings = DomainSettings().set_choice(DOMAIN, "material", "al:6061").for_domain(DOMAIN)
    segment = FormedSegmentFlatLength().run(
        {"thickness": 0.063 * IN, "inside_radius": 0.2 * IN, "bend_angle_2": 135.0},
        "k_factor",
        settings=settings,
    )
    (gap,) = notes(segment, GAP)
    assert "A2 is past 90°" in gap.text and gap.subjects == ("bend_angle_2",)


@pytest.mark.parametrize(
    ("material", "says"),
    [
        ("cs:a653", "zinc coating can flake or crack"),
        ("cs:a1011", "hot-rolled pickled and oiled"),
    ],
)
def test_a_material_without_a_source_says_so(material: str, says: str) -> None:
    result = bend(0.06, 0.03, material)
    (gap,) = notes(result, GAP)
    assert says in gap.text and "No public-domain source" in gap.text
    assert rule_of_thumb(result)


@pytest.mark.parametrize(
    ("material", "gauge", "warned"),
    [
        ("al:6061", "msg:16", True),
        ("ss:304", "msg:16", True),
        ("cs:a1008", "galv:16", True),
        ("cs:a653", "msg:16", True),
        ("cs:a1008", "awg:16", True),
        ("al:6061", "awg:16", False),
        ("cs:a1008", "msg:16", False),
        ("cs:a653", "galv:16", False),
        ("ss:304", "uss:16", False),
    ],
)
def test_a_gauge_from_another_materials_system_is_warned_about(
    material: str, gauge: str, warned: bool
) -> None:
    """Flag 9: a warning, never a block, naming both and suggesting a decimal thickness."""

    def mismatch(result: Result) -> list[Note]:
        return [n for n in result.notes if n.text.startswith("The gauge is")]

    warning = mismatch(bend(None, 0.2, material, gauge=gauge))
    assert bool(warning) == warned
    if warned:
        (note,) = warning
        assert note.kind is WARNING and note.subjects == ("thickness",)
        assert note.text.startswith("The gauge is 16 ") and "enter it as a decimal" in note.text
    assert mismatch(bend(0.06, 0.2, material, gauge=gauge)) == [], "a typed thickness"


def test_every_source_a_check_cites_states_its_scope() -> None:
    """ADR-0014 §1: a note says how far its source applies."""
    materials = load_materials(MATERIAL_TABLE.load())
    cited = [r.source for r in materials.radii]
    cited += [s for r in materials.radii for s in r.see_also]
    cited.append(materials.practice.source)
    assert all(source.reference.scope for source in cited)
