"""Domain choices and the values they derive (ADR-0014 §2, ADR-0013 §4).

The domain here is invented: a "plate" choice derives thickness and inside radius.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import override

import pytest

from caddcalc.core import (
    Calculator,
    Choice,
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
    TypedValue,
    UsageError,
    Verification,
)
from caddcalc.core.formatting import DisplayPrefs, describe_error, describe_source
from caddcalc.core.provenance import InputSource

L = Dimension.LENGTH
TABLE = Reference("Plates", "version 1")
CAUTION = Note(
    NoteKind.WARNING,
    "Nominal thickness; check before cutting.",
    references=(TABLE,),
    subjects=("thickness",),
)
PLATES = {"std:1": 2.0, "std:2": 4.0}
"""Each plate's thickness in mm; its inside radius is half that."""


class _Plates:
    """A resolver: two standard plates, each deriving thickness and inside radius."""

    def __init__(self, *, stray: bool = False) -> None:
        self.stray = stray

    def options(self, choice: str) -> Sequence[Option]:
        return (
            [Option(key, f"plate {key[-1]}", "Standard") for key in PLATES]
            if choice == "plate"
            else []
        )

    def derive(self, selections: Mapping[str, str]) -> Mapping[str, DerivedValue]:
        key = selections["plate"]
        source = InputSource(
            SourceKind.DERIVED, f"plate {key[-1]}, Standard (nominal)", reference=TABLE
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

    def options(self, _choice: str) -> Sequence[Option]:
        return self._options

    def derive(self, _selections: Mapping[str, str]) -> Mapping[str, DerivedValue]:
        return {}


@pytest.mark.parametrize(
    ("domain", "message"),
    [
        (Domain("d", "D", "x", choices=(Choice("plate", "P"),)), "no resolver"),
        (
            Domain(
                "d",
                "D",
                "x",
                settings=SETTINGS,
                choices=(Choice("thickness", "T"),),
                resolver=_Bad([]),
            ),
            "already used",
        ),
        (
            Domain(
                "d",
                "D",
                "x",
                choices=(Choice("plate", "P"), Choice("plate", "Q")),
                resolver=_Bad([]),
            ),
            "already used",
        ),
        (
            Domain(
                "d", "D", "x", choices=(Choice("plate", "P"),), resolver=_Bad([Option("12", "12")])
            ),
            "group:item",
        ),
        (
            Domain(
                "d",
                "D",
                "x",
                choices=(Choice("plate", "P"),),
                resolver=_Bad([Option("Std:1", "1")]),
            ),
            "group:item",
        ),
        (
            Domain(
                "d",
                "D",
                "x",
                choices=(Choice("plate", "P"),),
                resolver=_Bad([Option("s:1", "1"), Option("s:1", "1")]),
            ),
            "repeats",
        ),
        (
            Domain(
                "d", "D", "x", choices=(Choice("plate", "P"),), resolver=_Bad([Option("s:1", " ")])
            ),
            "needs a label",
        ),
        (
            Domain(
                "d",
                "D",
                "x",
                choices=(Choice("plate", "P", default="s:9"),),
                resolver=_Bad([Option("s:1", "1")]),
            ),
            "not one of its options",
        ),
    ],
)
def test_choices_are_validated_when_their_domain_registers(domain: Domain, message: str) -> None:
    with pytest.raises(SpecError, match=message):
        Registry().register_domain(domain)


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
    assert result.notes == (CAUTION,), "one note, though two inputs derive from one choice"


def test_a_set_value_beats_a_derived_one_and_clearing_it_restores_the_link() -> None:
    settings = chosen().set_text(SHOP, "thickness", "1.5", "mm")
    result = _Bend().run(settings=settings.for_domain(SHOP))
    assert (result.inputs["thickness"], result.source_of("thickness").kind) == (
        1.5,
        SourceKind.DOMAIN,
    )
    assert result.source_of("inside_radius").kind is SourceKind.DERIVED

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


def test_a_resolver_deriving_an_unknown_setting_is_a_domain_bug() -> None:
    stray = Domain(
        "shop",
        "Shop",
        "x",
        settings=SETTINGS,
        choices=(Choice("plate", "Plate"),),
        resolver=_Plates(stray=True),
    )
    with pytest.raises(SpecError, match="derives 'width', which isn't a setting"):
        DomainSettings().set_choice(stray, "plate", "std:1").for_domain(stray)


def test_a_derived_value_needs_a_derived_source_and_a_matching_stated_value() -> None:
    domain_source = InputSource(SourceKind.DOMAIN, "Shop settings", domain="shop")
    with pytest.raises(SpecError, match="needs a derived source"):
        DerivedValue(2.0, domain_source)
    derived_source = InputSource(SourceKind.DERIVED, "plate 1")
    with pytest.raises(SpecError, match="doesn't equal"):
        DerivedValue(2.0, derived_source, stated=TypedValue.parse("3 mm", L))


def test_no_choice_means_no_derived_values() -> None:
    assert dict(DomainSettings().for_domain(SHOP).derived) == {}
    assert _Bend().run(settings=DomainSettings().for_domain(SHOP)).source_of("thickness").kind is (
        SourceKind.DEFAULT
    )
