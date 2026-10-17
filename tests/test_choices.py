"""Domain choices and the values they derive (ADR-0014 §2, ADR-0013 §4).

The domains here are invented: a "plate" choice derives thickness and inside radius, and
a "temper" choice depends on a "material" choice.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import replace
from typing import override

import pytest

from caddcalc.core import (
    Calculator,
    Choice,
    ClearedChoice,
    Context,
    DerivedValue,
    Dimension,
    Domain,
    DomainSettings,
    Method,
    Note,
    NoteKind,
    Option,
    OutOfRangeError,
    Output,
    Param,
    Reference,
    Registry,
    SourceKind,
    SpecError,
    Step,
    TypedValue,
    UsageError,
    Verification,
)
from caddcalc.core.formatting import DisplayPrefs, describe_error, describe_source
from caddcalc.core.provenance import InputSource

L = Dimension.LENGTH
TABLE = Reference("Plates", "version 1")
CAUTION = Note(NoteKind.WARNING, "Nominal thickness; check before cutting.", references=(TABLE,))
PLATES = {"std:1": 2.0, "std:2": 4.0}
"""Each plate's thickness in mm; its inside radius is half that."""


class _Plates:
    """A resolver: two standard plates, each deriving thickness and inside radius."""

    def __init__(self, *, stray: bool = False, domain: str = "shop") -> None:
        self.stray = stray
        self.domain = domain

    def options(self, choice: str, _selections: Mapping[str, str]) -> Sequence[Option]:
        return (
            [Option(key, f"plate {key[-1]}", "Standard") for key in PLATES]
            if choice == "plate"
            else []
        )

    def derive(self, selections: Mapping[str, str]) -> Mapping[str, DerivedValue]:
        key = selections["plate"]
        source = InputSource(
            SourceKind.DERIVED,
            f"plate {key[-1]}, Standard (nominal)",
            domain=self.domain,
            reference=TABLE,
        )
        thickness = PLATES[key]
        derived = {
            "thickness": DerivedValue(thickness, source, note=CAUTION),
            "inside_radius": DerivedValue(thickness / 2, source, note=CAUTION),
        }
        if self.stray:
            derived["width"] = DerivedValue(1.0, source)
        return derived


SETTINGS = (
    Param("thickness", "T", "Thickness", L, minimum=0.0, min_inclusive=False),
    Param("inside_radius", "R", "Inside radius", L, minimum=0.0),
)
SHOP = Domain(
    "shop",
    "Shop",
    "A domain for choice tests.",
    settings=SETTINGS,
    choices=(Choice("plate", "Plate"),),
    resolver=_Plates(),
)


class _Bend(Calculator):
    id = "shop.bend"
    name = "Bend"
    domain = "shop"
    summary = "Adds thickness and radius, or uses the width only."
    params = (
        Param(
            "thickness",
            "T",
            "Thickness",
            L,
            default="1 mm",
            minimum=0.0,
            maximum=3.0,
            min_inclusive=False,
            shared=True,
        ),
        Param("inside_radius", "R", "Inside radius", L, default="1 mm", minimum=0.0, shared=True),
        Param("width", "W", "Width", L, default="10 mm"),
    )
    outputs = (Output("total", "S", "Total", L),)
    methods = (
        Method("sum", "Sum", "S = W + T + R", Verification.UNVERIFIED),
        Method("width", "Width", "S = W", Verification.UNVERIFIED),
    )

    @override
    def compute(self, ctx: Context) -> None:
        formula = "W + T + R" if ctx.method == "sum" else "W"
        ctx.calc("S", formula, label="Total", dimension=L, output="total")


class _WidthOnly(_Bend):
    params = (
        Param(
            "thickness",
            "T",
            "Thickness",
            L,
            default="1 mm",
            minimum=0.0,
            min_inclusive=False,
            shared=True,
            methods=("sum",),
        ),
        Param(
            "inside_radius",
            "R",
            "Inside radius",
            L,
            default="1 mm",
            minimum=0.0,
            shared=True,
            methods=("sum",),
        ),
        Param("width", "W", "Width", L, default="10 mm"),
    )


def chosen(option: str = "std:1") -> DomainSettings:
    return DomainSettings().set_choice(SHOP, "plate", option)


def test_a_domain_with_choices_registers_and_lists_grouped_options() -> None:
    registry = Registry()
    registry.register_domain(SHOP)
    assert [(o.key, o.label, o.group) for o in SHOP.options("plate")] == [
        ("std:1", "plate 1", "Standard"),
        ("std:2", "plate 2", "Standard"),
    ]


class _Bad:
    def __init__(self, options: list[Option]) -> None:
        self._options = options

    def options(self, _choice: str, _selections: Mapping[str, str]) -> Sequence[Option]:
        return self._options

    def derive(self, _selections: Mapping[str, str]) -> Mapping[str, DerivedValue]:
        return {}


def bad(*choices: Choice, options: Sequence[Option] = ()) -> Domain:
    return Domain("d", "D", "x", settings=SETTINGS, choices=choices, resolver=_Bad([*options]))


@pytest.mark.parametrize(
    ("domain", "message"),
    [
        (Domain("d", "D", "x", choices=(Choice("plate", "P"),)), "no resolver"),
        (bad(Choice("thickness", "T")), "already used"),
        (bad(Choice("plate", "P"), Choice("plate", "Q")), "already used"),
        (bad(Choice("plate", "P", depends_on=("plate",))), "isn't another declared choice"),
        (bad(Choice("plate", "P", depends_on=("grade",))), "isn't another declared choice"),
        (
            bad(
                Choice("a", "A", depends_on=("c",)),
                Choice("b", "B", depends_on=("a",)),
                Choice("c", "C", depends_on=("b",)),
            ),
            "depend on each other: a -> c -> b -> a",
        ),
    ],
)
def test_choices_are_validated_when_their_domain_registers(domain: Domain, message: str) -> None:
    with pytest.raises(SpecError, match=message):
        Registry().register_domain(domain)


@pytest.mark.parametrize(
    ("options", "message"),
    [
        ([Option("12", "12")], "group:item"),
        ([Option("Std:1", "1")], "group:item"),
        ([Option("s:1", "1"), Option("s:1", "1")], "repeats"),
        ([Option("s:1", " ")], "needs a label"),
    ],
)
def test_options_are_checked_when_they_are_computed(options: list[Option], message: str) -> None:
    domain = bad(Choice("plate", "P"), options=options)
    Registry().register_domain(domain)
    with pytest.raises(SpecError, match=message):
        domain.options("plate")


def test_a_default_its_choice_never_offers_is_a_domain_bug() -> None:
    domain = bad(Choice("plate", "P", default="s:9"), options=[Option("s:1", "1")])
    with pytest.raises(SpecError, match="default 's:9' of 'plate' isn't one of its options"):
        DomainSettings().choice(domain, "plate")


def test_choosing_stores_an_option_and_clearing_returns_to_the_default() -> None:
    assert DomainSettings().choice(SHOP, "plate") is None
    settings = chosen("std:2")
    assert settings.choice(SHOP, "plate") == "std:2"
    assert settings.clear_choice(SHOP, "plate") == DomainSettings()
    assert settings.clear_domain(SHOP) == DomainSettings()
    with pytest.raises(UsageError, match="no option 'std:9'"):
        DomainSettings().set_choice(SHOP, "plate", "std:9")
    with pytest.raises(UsageError, match="no choice 'gauge'"):
        DomainSettings().set_choice(SHOP, "gauge", "std:1")


def test_a_choice_default_is_selected_until_the_user_chooses() -> None:
    defaulted = Domain(
        "shop",
        "Shop",
        "x",
        settings=SETTINGS,
        choices=(Choice("plate", "Plate", default="std:2"),),
        resolver=_Plates(),
    )
    assert DomainSettings().choice(defaulted, "plate") == "std:2"
    assert DomainSettings().for_domain(defaulted).derived["thickness"].value == 4.0


def test_a_derived_value_reaches_the_result_with_its_source_and_note() -> None:
    result = _Bend().run(settings=chosen().for_domain(SHOP))
    assert result.inputs["thickness"] == 2.0
    source = result.source_of("thickness")
    assert (source.kind, describe_source(source)) == (
        SourceKind.DERIVED,
        "plate 1, Standard (nominal), Plates, version 1",
    )
    assert result.to_dict()["inputs"]["thickness"]["source"]["kind"] == "derived"
    assert result.notes == (replace(CAUTION, subjects=("thickness", "inside_radius")),), (
        "one note, naming both inputs that took a value from the choice"
    )


def test_a_set_value_beats_a_derived_one_and_clearing_it_restores_the_link() -> None:
    settings = chosen().set_text(SHOP, "thickness", "1.5", "mm")
    result = _Bend().run(settings=settings.for_domain(SHOP))
    assert (result.inputs["thickness"], result.source_of("thickness").kind) == (
        1.5,
        SourceKind.DOMAIN,
    )
    assert result.source_of("inside_radius").kind is SourceKind.DERIVED
    assert result.notes == (replace(CAUTION, subjects=("inside_radius",)),)

    restored = _Bend().run(settings=settings.clear(SHOP, "thickness").for_domain(SHOP))
    assert restored.source_of("thickness").kind is SourceKind.DERIVED


def test_the_note_appears_only_when_a_derived_value_is_used() -> None:
    values = (
        chosen().set_text(SHOP, "thickness", "1.5", "mm").set_text(SHOP, "inside_radius", "1", "mm")
    )
    assert _Bend().run(settings=values.for_domain(SHOP)).notes == ()
    explicit = _Bend().run(
        {"thickness": 1.0, "inside_radius": 1.0}, settings=chosen().for_domain(SHOP)
    )
    assert explicit.notes == ()
    assert _WidthOnly().run(method="width", settings=chosen().for_domain(SHOP)).notes == ()


def test_an_out_of_range_derived_value_names_its_source() -> None:
    with pytest.raises(OutOfRangeError) as caught:
        _Bend().run(settings=chosen("std:2").for_domain(SHOP))
    assert caught.value.source.kind is SourceKind.DERIVED
    assert describe_error(caught.value, DisplayPrefs(length_unit="mm")) == (
        "Thickness (T) from plate 2, Standard (nominal) is 4 mm, but this calculator needs at "
        "most 3 mm. Override it in this calculator."
    )


@pytest.mark.parametrize(
    ("resolver", "message"),
    [
        (_Plates(stray=True), "derives 'width', which isn't a setting"),
        (_Plates(domain="other"), "source naming domain 'other'; it must name 'shop'"),
        (_Plates(domain=""), "source naming domain ''; it must name 'shop'"),
    ],
)
def test_a_resolver_deriving_a_stray_value_is_a_domain_bug(resolver: _Plates, message: str) -> None:
    stray = replace(SHOP, resolver=resolver)
    with pytest.raises(SpecError, match=message):
        DomainSettings().set_choice(stray, "plate", "std:1").for_domain(stray)


def test_a_derived_value_needs_a_derived_source_naming_its_table() -> None:
    domain_source = InputSource(SourceKind.DOMAIN, "Shop settings", domain="shop")
    with pytest.raises(SpecError, match="needs a derived source"):
        DerivedValue(2.0, domain_source)
    untabled = InputSource(SourceKind.DERIVED, "plate 1", domain="shop")
    with pytest.raises(SpecError, match="'plate 1' must name its table and version"):
        DerivedValue(2.0, untabled)
    derived_source = InputSource(SourceKind.DERIVED, "plate 1", domain="shop", reference=TABLE)
    with pytest.raises(SpecError, match="doesn't equal"):
        DerivedValue(2.0, derived_source, stated=TypedValue.parse("3 mm", L))


def test_only_run_names_the_inputs_a_derived_note_is_about() -> None:
    source = InputSource(SourceKind.DERIVED, "plate 1", domain="shop", reference=TABLE)
    about = replace(CAUTION, subjects=("thickness",))
    with pytest.raises(SpecError, match="'plate 1' has subjects; run\\(\\) names"):
        DerivedValue(2.0, source, note=about)


def test_no_choice_means_no_derived_values() -> None:
    assert dict(DomainSettings().for_domain(SHOP).derived) == {}
    assert _Bend().run(settings=DomainSettings().for_domain(SHOP)).source_of("thickness").kind is (
        SourceKind.DEFAULT
    )


# --- A dependent choice: each material offers its own tempers --------------------------------

TEMPERS = {"al:6061": ("temper:o", "temper:t6"), "al:3003": ("temper:o", "temper:h14")}
RADII = {"temper:o": 1.0, "temper:t6": 3.0, "temper:h14": 2.0}
"""Minimum inside radius in mm by temper; invented."""


class _Alloys:
    def options(self, choice: str, selections: Mapping[str, str]) -> Sequence[Option]:
        if choice == "material":
            return [Option(key, key.upper(), "Aluminum") for key in TEMPERS]
        return [Option(key, key[7:].upper()) for key in TEMPERS.get(selections.get("material"), ())]

    def derive(self, selections: Mapping[str, str]) -> Mapping[str, DerivedValue]:
        temper = selections.get("temper")
        if temper is None:
            return {}
        source = InputSource(SourceKind.DERIVED, temper, domain="alloys", reference=TABLE)
        return {"inside_radius": DerivedValue(RADII[temper], source)}


ALLOYS = Domain(
    "alloys",
    "Alloys",
    "A domain for dependent-choice tests.",
    settings=SETTINGS,
    choices=(
        Choice("temper", "Temper", depends_on=("material",)),
        Choice("material", "Material", default="al:6061"),
    ),
    resolver=_Alloys(),
)


def alloy(material: str, temper: str | None = None) -> DomainSettings:
    settings = DomainSettings().set_choice(ALLOYS, "material", material)
    return settings if temper is None else settings.set_choice(ALLOYS, "temper", temper)


def test_a_dependent_choice_offers_the_options_its_parent_selects() -> None:
    Registry().register_domain(ALLOYS)
    assert [c.key for c in ALLOYS.ordered_choices()] == ["material", "temper"]
    assert [o.key for o in ALLOYS.options("temper", {"material": "al:3003"})] == [
        "temper:o",
        "temper:h14",
    ]
    assert ALLOYS.options("temper") == ()
    assert DomainSettings().choice(ALLOYS, "material") == "al:6061"
    assert DomainSettings().choice(ALLOYS, "temper") is None
    settings = DomainSettings().set_choice(ALLOYS, "temper", "temper:t6")
    assert settings.for_domain(ALLOYS).derived["inside_radius"].value == 3.0
    with pytest.raises(UsageError, match="no option 'temper:t6'"):
        alloy("al:3003", "temper:t6")


def test_a_parent_change_clears_a_dependent_selection_it_no_longer_offers() -> None:
    before = alloy("al:6061", "temper:t6")
    after = before.set_choice(ALLOYS, "material", "al:3003")
    assert after.choice(ALLOYS, "material") == "al:3003"
    assert after.choice(ALLOYS, "temper") is None
    assert after == alloy("al:3003")
    assert after.cleared_choices(ALLOYS, before) == (ClearedChoice("temper", "none"),)
    assert dict(after.for_domain(ALLOYS).derived) == {}


def test_a_parent_change_keeps_a_dependent_selection_still_offered() -> None:
    before = alloy("al:6061", "temper:o")
    after = before.set_choice(ALLOYS, "material", "al:3003")
    assert after.choice(ALLOYS, "temper") == "temper:o"
    assert after.cleared_choices(ALLOYS, before) == ()


def test_clearing_a_parent_returns_it_to_its_default_and_clears_what_that_doesnt_offer() -> None:
    before = alloy("al:3003", "temper:h14")
    after = before.clear_choice(ALLOYS, "material")
    assert after.choice(ALLOYS, "material") == "al:6061"
    assert after.choice(ALLOYS, "temper") is None
    assert after.cleared_choices(ALLOYS, before) == (ClearedChoice("temper", "none"),)
    assert before.clear_choice(ALLOYS, "temper").cleared_choices(ALLOYS, before) == ()


def test_clear_all_restores_each_choices_default() -> None:
    cleared = alloy("al:3003", "temper:h14").clear_domain(ALLOYS)
    assert cleared == DomainSettings()
    assert cleared.choice(ALLOYS, "material") == "al:6061"
    assert cleared.choice(ALLOYS, "temper") is None


def test_a_dependent_falls_back_to_its_default_when_its_option_is_cleared() -> None:
    temper = Choice("temper", "Temper", default="temper:o", depends_on=("material",))
    defaulted = replace(ALLOYS, choices=(temper, *ALLOYS.choices[1:]))
    before = DomainSettings().set_choice(defaulted, "temper", "temper:t6")
    after = before.set_choice(defaulted, "material", "al:3003")
    assert after.choice(defaulted, "temper") == "temper:o"
    assert after.cleared_choices(defaulted, before) == (ClearedChoice("temper", "default"),)


def test_a_kept_dependent_may_be_offered_under_another_parent_selection() -> None:
    """O temper, chosen under 3003, stays when the material falls back to its default, 6061."""
    before = alloy("al:3003", "temper:o")
    after = before.clear_choice(ALLOYS, "material")
    assert (after.choice(ALLOYS, "material"), after.choice(ALLOYS, "temper")) == (
        "al:6061",
        "temper:o",
    )
    assert after.cleared_choices(ALLOYS, before) == ()


class _Undeclared:
    """The reviewer's probe: choice "u" declares no parent but reads "a" to decide."""

    def __init__(self) -> None:
        self.seen: list[tuple[str, dict[str, str]]] = []

    def options(self, choice: str, selections: Mapping[str, str]) -> Sequence[Option]:
        self.seen.append((choice, dict(selections)))
        if choice == "a":
            return [Option("a:1", "1"), Option("a:2", "2")]
        return [Option("u:k", "K")] if selections.get("a") == "a:1" else []

    def derive(self, _selections: Mapping[str, str]) -> Mapping[str, DerivedValue]:
        return {}


def test_a_resolver_sees_only_the_parents_a_choice_declares() -> None:
    resolver = _Undeclared()
    probe = Domain(
        "probe",
        "Probe",
        "x",
        choices=(Choice("a", "A", default="a:1"), Choice("u", "U")),
        resolver=resolver,
    )
    Registry().register_domain(probe)
    with pytest.raises(UsageError, match="no option 'u:k'"):
        DomainSettings().set_choice(probe, "u", "u:k")
    assert {choice: seen for choice, seen in resolver.seen if choice == "u"} == {"u": {}}

    declared = replace(probe, choices=(probe.choices[0], Choice("u", "U", depends_on=("a",))))
    before = DomainSettings().set_choice(declared, "u", "u:k")
    after = before.set_choice(declared, "a", "a:2")
    assert after.cleared_choices(declared, before) == (ClearedChoice("u", "none"),)
    assert resolver.seen[-1] == ("u", {"a": "a:2"})


def test_a_derived_values_work_shows_the_value_under_the_inputs_symbol() -> None:
    source = InputSource(SourceKind.DERIVED, "plate 1", domain="shop", reference=TABLE)
    with pytest.raises(SpecError, match=r"work of derived value 'plate 1' gives 3\.0, not 2\.0"):
        DerivedValue(2.0, source, work=Step("X", "Plate", L, 3.0))

    class _Worked(_Plates):
        @override
        def derive(self, selections: Mapping[str, str]) -> Mapping[str, DerivedValue]:
            plain = super().derive(selections)["thickness"]
            work = Step("X", "Plate", L, plain.value, "p / 2", substitution={"p": "4"})
            return {"thickness": replace(plain, work=work)}

    worked = replace(SHOP, resolver=_Worked())
    settings = DomainSettings().set_choice(worked, "plate", "std:1").for_domain(worked)
    result = _Bend().run(settings=settings)
    assert result.steps[0] == Step("T", "Plate", L, 2.0, "p / 2", substitution={"p": "4"})
    assert [s.symbol for s in result.steps] == ["T", "S"]
