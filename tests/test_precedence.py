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
    OutOfRangeError,
    Output,
    Param,
    Reference,
    Registry,
    SourceKind,
    UsageError,
    Verification,
)
from caddcalc.core.formatting import DisplayPrefs, describe_error, describe_source

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
    with pytest.raises(OutOfRangeError) as caught:
        _Plate().run(settings=too_thick)
    error = caught.value
    assert (error.param.key, error.value, error.bound, error.above) == (
        "thickness",
        50.0,
        10.0,
        True,
    )
    assert error.source.kind is SourceKind.DOMAIN
    assert str(error) == (
        "Thickness (T) from Shop settings is 50 mm, but this calculator needs at most 10 mm. "
        "Override it in this calculator."
    )
    assert describe_error(error, DisplayPrefs(length_unit="in")) == (
        "Thickness (T) from Shop settings is 1.9685 in, but this calculator needs at most "
        "0.393701 in. Override it in this calculator."
    )


def test_an_out_of_range_explicit_value_is_worded_in_display_units() -> None:
    with pytest.raises(OutOfRangeError) as caught:
        _Plate().run({"thickness": 0.0})
    assert caught.value.source.kind is SourceKind.EXPLICIT
    assert str(caught.value) == "Thickness (T) must be greater than 0 mm"
    inches = describe_error(caught.value, DisplayPrefs(length_unit="in"))
    assert inches == "Thickness (T) must be greater than 0 in"
    assert describe_error(InputError("plain"), DisplayPrefs()) == "plain"


def test_settings_from_another_domain_are_refused_as_api_misuse() -> None:
    with pytest.raises(UsageError, match="given settings for 'press'") as caught:
        _Plate().run(settings=DomainValues("press", "Press settings", {"thickness": 3.0}))
    assert isinstance(caught.value, ValueError)


def test_domain_values_keep_a_read_only_copy() -> None:
    given = {"thickness": 3.0}
    values = DomainValues("shop", "Shop settings", given)
    given["thickness"] = 50.0
    assert values.values == {"thickness": 3.0}
    with pytest.raises(TypeError):
        values.values["thickness"] = 1.0  # type: ignore[index]


def test_a_result_reports_sources_only_for_its_inputs() -> None:
    result = _Plate().run(method="width_only")
    with pytest.raises(KeyError):
        result.source_of("thickness")


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
        (InputSource(SourceKind.DOMAIN, domain="sheet_metal"), "domain settings"),
        (
            InputSource(
                SourceKind.DERIVED,
                "Steel, 304",
                reference=Reference("Materials table", "version 1"),
            ),
            "Steel, 304, Materials table, version 1",
        ),
    ],
)
def test_sources_are_worded_once_for_every_front_end(source: InputSource, wording: str) -> None:
    assert describe_source(source) == wording


def test_explicit_inputs_can_carry_a_label_without_changing_precedence() -> None:
    example = InputSource(SourceKind.EXPLICIT, "course example")
    result = _Plate().run(
        {"thickness": 5.0, "width": 30.0},
        settings=SET_T,
        explicit_sources={"thickness": example},
    )
    assert result.outputs["total"] == pytest.approx(35.0)
    assert result.source_of("thickness") == example
    assert result.source_of("width") == InputSource(SourceKind.EXPLICIT)
    assert describe_source(result.source_of("thickness")) == "course example"
    assert describe_source(result.source_of("width")) == "entered"


@pytest.mark.parametrize(
    ("labels", "message"),
    [
        ({"width": InputSource(SourceKind.EXPLICIT, "x")}, "not in inputs"),
        ({"thickness": InputSource(SourceKind.DOMAIN, "x")}, "only hold explicit"),
    ],
)
def test_explicit_source_labels_are_checked(labels: dict[str, InputSource], message: str) -> None:
    with pytest.raises(UsageError, match=message):
        _Plate().run({"thickness": 5.0}, explicit_sources=labels)


def test_a_reference_serialises_as_its_fields() -> None:
    reference = Reference("Materials table", "version 1", "https://example.org/materials")
    source = InputSource(SourceKind.DERIVED, "Steel, 304", reference=reference)
    assert source.to_dict()["reference"] == {
        "title": "Materials table",
        "detail": "version 1",
        "url": "https://example.org/materials",
        "edition": "",
        "locator": "",
        "accessed": None,
        "scope": "",
        "short_title": "",
    }
