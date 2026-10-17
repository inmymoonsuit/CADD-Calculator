"""Shared parameters, the precedence rule, and input provenance (ADR-0013 §3-§5)."""

from __future__ import annotations

from typing import override

import pytest

from caddcalc.core import (
    Calculator,
    Context,
    Dimension,
    Domain,
    DomainValues,
    InputError,
    InputSource,
    Method,
    Output,
    Param,
    Registry,
    SourceKind,
    SpecError,
    Verification,
)
from caddcalc.core.formatting import describe_source

L = Dimension.LENGTH
SHOP = Domain(
    "shop",
    "Shop",
    "A domain for precedence tests.",
    settings=(Param("thickness", "T", "Thickness", L, minimum=0.0, min_inclusive=False),),
)
SET_T = DomainValues("shop", "Shop settings", {"thickness": 3.0})


class _Plate(Calculator):
    id = "shop.plate"
    name = "Plate"
    domain = "shop"
    summary = "Adds a thickness to a width."
    params = (
        Param(
            "thickness",
            "T",
            "Thickness",
            L,
            default="1 mm",
            minimum=0.0,
            maximum=10.0,
            min_inclusive=False,
            methods=("sum",),
            shared=True,
        ),
        Param("width", "W", "Width", L, default="20 mm"),
    )
    outputs = (Output("total", "S", "Total", L),)
    methods = (
        Method("sum", "Sum", "S = W + T", Verification.UNVERIFIED),
        Method("width_only", "Width only", "S = W", Verification.UNVERIFIED),
    )

    @override
    def compute(self, ctx: Context) -> None:
        expression = "W + T" if ctx.method == "sum" else "W"
        ctx.calc("S", expression, label="Total", dimension=L, output="total")


class _LocalPlate(_Plate):
    """The same calculator, but its thickness is not shared."""

    id = "shop.local_plate"
    params = (
        Param("thickness", "T", "Thickness", L, default="1 mm", methods=("sum",)),
        Param("width", "W", "Width", L, default="20 mm"),
    )


def kinds(result_sources: dict[str, InputSource]) -> dict[str, SourceKind]:
    return {key: source.kind for key, source in result_sources.items()}


def test_shared_parameters_register_against_their_domain() -> None:
    registry = Registry()
    registry.register_domain(SHOP)
    assert registry.register(_Plate).id == "shop.plate"


def test_without_settings_every_value_is_a_default() -> None:
    result = _Plate().run()
    assert result.outputs["total"] == pytest.approx(21.0)
    assert kinds(dict(result.input_sources)) == {
        "thickness": SourceKind.DEFAULT,
        "width": SourceKind.DEFAULT,
    }


def test_a_set_domain_value_beats_the_default() -> None:
    result = _Plate().run(settings=SET_T)
    assert result.outputs["total"] == pytest.approx(23.0)
    assert result.source_of("thickness") == InputSource(
        SourceKind.DOMAIN, "Shop settings", domain="shop"
    )
    assert result.source_of("width").kind is SourceKind.DEFAULT


def test_an_explicit_value_beats_the_domain_value() -> None:
    result = _Plate().run({"thickness": 5.0}, settings=SET_T)
    assert result.outputs["total"] == pytest.approx(25.0)
    assert result.source_of("thickness").kind is SourceKind.EXPLICIT


def test_a_method_that_does_not_use_a_shared_parameter_ignores_its_setting() -> None:
    result = _Plate().run(method="width_only", settings=SET_T)
    assert "thickness" not in result.inputs
    assert "thickness" not in result.input_sources


def test_a_parameter_that_is_not_shared_ignores_a_setting_with_its_key() -> None:
    result = _LocalPlate().run(settings=SET_T)
    assert result.outputs["total"] == pytest.approx(21.0)
    assert result.source_of("thickness").kind is SourceKind.DEFAULT


def test_unset_settings_change_nothing() -> None:
    plain = _Plate().run()
    empty = _Plate().run(settings=DomainValues("shop", "Shop settings", {}))
    assert empty.outputs == plain.outputs
    assert empty.input_sources == plain.input_sources


def test_an_out_of_range_domain_value_fails_and_names_its_source() -> None:
    too_thick = DomainValues("shop", "Shop settings", {"thickness": 50.0})
    with pytest.raises(InputError, match=r"at most 10 \(value from Shop settings\)\. Override it"):
        _Plate().run(settings=too_thick)


def test_settings_from_another_domain_are_refused() -> None:
    with pytest.raises(SpecError, match="given settings for 'press'"):
        _Plate().run(settings=DomainValues("press", "Press settings", {"thickness": 3.0}))


def test_to_dict_reports_each_inputs_source() -> None:
    data = _Plate().run(settings=SET_T).to_dict()
    assert data["inputs"]["thickness"]["source"] == {
        "kind": "domain",
        "label": "Shop settings",
        "domain": "shop",
        "reference": None,
    }
    assert data["inputs"]["width"]["source"]["kind"] == "default"


@pytest.mark.parametrize(
    ("source", "wording"),
    [
        (InputSource(SourceKind.EXPLICIT), "entered"),
        (InputSource(SourceKind.DEFAULT), "default"),
        (
            InputSource(SourceKind.DOMAIN, "Sheet Metal settings", domain="sheet_metal"),
            "Sheet Metal settings",
        ),
        (
            InputSource(SourceKind.DERIVED, "Steel, 304", reference="materials v1"),
            "Steel, 304, materials v1",
        ),
    ],
)
def test_sources_are_worded_once_for_every_front_end(source: InputSource, wording: str) -> None:
    assert describe_source(source) == wording
