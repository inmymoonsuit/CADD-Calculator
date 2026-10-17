"""The in-memory domain settings model and typed values (ADR-0013 §7, §9)."""

from __future__ import annotations

import pytest

from caddcalc.calculators.sheet_metal import DOMAIN as SHEET_METAL
from caddcalc.calculators.sheet_metal import BendAllowance
from caddcalc.core import (
    Dimension,
    Domain,
    DomainSettings,
    DomainValues,
    InputError,
    OutOfRangeError,
    Param,
    SourceKind,
    TypedValue,
    UsageError,
    parse_quantity_detailed,
)
from caddcalc.core.units import get_unit

OTHER = Domain(
    "other",
    "Other",
    "A second domain.",
    settings=(Param("thickness", "T", "Thickness", Dimension.LENGTH),),
)


def test_typed_values_keep_the_users_text_and_its_exact_parse() -> None:
    third = TypedValue.parse(" 1/3 ", Dimension.LENGTH, "in")
    assert third == TypedValue(1 / 3 * 25.4, "1/3", get_unit("in"), explicit_unit=False)
    assert third.dimension is Dimension.LENGTH


@pytest.mark.parametrize(
    ("text", "dimension", "default", "unit", "explicit"),
    [
        ("3 mm", Dimension.LENGTH, "in", "mm", True),
        ("3", Dimension.LENGTH, "in", "in", False),
        ('1-1/2"', Dimension.LENGTH, "mm", "in", True),
        ("0.44", Dimension.RATIO, None, "", False),
        ("44%", Dimension.RATIO, None, "%", True),
        ("90", Dimension.ANGLE, None, "deg", False),
    ],
)
def test_typed_values_record_the_unit_actually_applied(
    text: str, dimension: Dimension, default: str | None, unit: str, explicit: bool
) -> None:
    entry = TypedValue.parse(text, dimension, default)
    assert (entry.unit.symbol, entry.explicit_unit) == (unit, explicit)
    parsed = parse_quantity_detailed(text, dimension, default)
    assert (parsed.value, parsed.unit, parsed.explicit_unit) == (
        entry.value,
        entry.unit,
        entry.explicit_unit,
    )


def test_nothing_is_set_at_first() -> None:
    settings = DomainSettings()
    assert settings.get(SHEET_METAL, "thickness") is None
    values = settings.for_domain(SHEET_METAL)
    assert (values.domain_id, values.label, dict(values.values)) == (
        "sheet_metal",
        "Sheet Metal settings",
        {},
    )


def test_setting_text_keeps_intent_and_returns_a_new_model() -> None:
    empty = DomainSettings()
    settings = empty.set_text(SHEET_METAL, "thickness", "1/3", "in")
    assert empty.get(SHEET_METAL, "thickness") is None, "the model is immutable"
    entry = settings.get(SHEET_METAL, "thickness")
    assert entry == TypedValue.parse("1/3", Dimension.LENGTH, "in")
    assert settings.for_domain(SHEET_METAL).values == {"thickness": 1 / 3 * 25.4}


def test_settings_are_validated_against_the_domain() -> None:
    settings = DomainSettings()
    with pytest.raises(UsageError, match="no setting 'gauge'; its settings are: thickness"):
        settings.set_text(SHEET_METAL, "gauge", "12")
    with pytest.raises(OutOfRangeError, match="greater than 0"):
        settings.set_text(SHEET_METAL, "thickness", "0", "in")
    with pytest.raises(OutOfRangeError, match="at most 1"):
        settings.set_text(SHEET_METAL, "k_factor", "1.2")
    with pytest.raises(InputError, match="Cannot read a value"):
        settings.set_text(SHEET_METAL, "inside_radius", "abc", "in")
    with pytest.raises(InputError, match="'3 deg' is an angle, but a length is expected"):
        settings.set_text(SHEET_METAL, "thickness", "3 deg", "in")


def test_a_typed_value_of_another_dimension_is_refused() -> None:
    angle = TypedValue.parse("90 deg", Dimension.ANGLE)
    with pytest.raises(UsageError, match="is a length, but '90 deg' is an angle"):
        DomainSettings().set(SHEET_METAL, "thickness", angle)


def test_the_constructor_takes_no_values() -> None:
    negative = TypedValue.parse("-5", Dimension.LENGTH, "mm")
    with pytest.raises(TypeError):
        DomainSettings({"sheet_metal": {"inside_radius": negative}})  # type: ignore[call-arg]


@pytest.mark.parametrize("method", ["get", "clear"])
def test_lookups_and_clears_reject_unknown_keys(method: str) -> None:
    settings = DomainSettings().set_text(SHEET_METAL, "k_factor", "0.44")
    with pytest.raises(UsageError, match="no setting 'kfactor'"):
        getattr(settings, method)(SHEET_METAL, "kfactor")


def test_domains_are_independent_and_can_be_cleared() -> None:
    settings = (
        DomainSettings()
        .set_text(SHEET_METAL, "thickness", "0.1046", "in")
        .set_text(SHEET_METAL, "k_factor", "0.44")
        .set_text(OTHER, "thickness", "2 mm")
    )
    assert set(settings.values(SHEET_METAL)) == {"thickness", "k_factor"}
    assert settings.for_domain(OTHER).values == {"thickness": 2.0}

    without_k = settings.clear(SHEET_METAL, "k_factor")
    assert set(without_k.values(SHEET_METAL)) == {"thickness"}
    cleared = settings.clear_domain(SHEET_METAL)
    assert dict(cleared.values(SHEET_METAL)) == {}
    assert cleared.for_domain(OTHER).values == {"thickness": 2.0}


def test_models_compare_by_value_and_are_not_hashable() -> None:
    set_k = DomainSettings().set_text(SHEET_METAL, "k_factor", "0.44")
    assert set_k == DomainSettings().set_text(SHEET_METAL, "k_factor", "0.44")
    assert set_k.clear(SHEET_METAL, "k_factor") == DomainSettings()
    with pytest.raises(TypeError, match="unhashable"):
        hash(set_k)


def test_the_values_view_is_read_only() -> None:
    settings = DomainSettings().set_text(SHEET_METAL, "k_factor", "0.44")
    view = settings.values(SHEET_METAL)
    with pytest.raises(TypeError):
        view["k_factor"] = TypedValue.parse("0.5", Dimension.RATIO)  # type: ignore[index]


def test_domain_values_are_checked_and_labelled_in_one_place() -> None:
    values = SHEET_METAL.values(thickness=2.0, k_factor=0.44)
    assert values == DomainValues(
        "sheet_metal", "Sheet Metal settings", {"thickness": 2.0, "k_factor": 0.44}
    )
    assert SHEET_METAL.settings_label == "Sheet Metal settings"
    with pytest.raises(UsageError, match="no setting 'thicknes'"):
        SHEET_METAL.values(thicknes=2.0)
    with pytest.raises(OutOfRangeError, match="at most 1"):
        SHEET_METAL.values(k_factor=1.5)


def test_domain_values_need_a_label() -> None:
    with pytest.raises(UsageError, match="needs a label"):
        DomainValues("sheet_metal", " ", {})


def test_a_calculator_runs_with_the_session_settings() -> None:
    settings = DomainSettings().set_text(SHEET_METAL, "k_factor", "0.44")
    result = BendAllowance().run(method="k_factor", settings=settings.for_domain(SHEET_METAL))
    source = result.source_of("k_factor")
    assert (source.kind, source.label, source.domain) == (
        SourceKind.DOMAIN,
        "Sheet Metal settings",
        "sheet_metal",
    )
    assert result.inputs["k_factor"] == pytest.approx(0.44)


@pytest.mark.parametrize("dimension", list(Dimension))
def test_every_dimension_has_its_name_with_an_article(dimension: Dimension) -> None:
    article, name = dimension.with_article.split()
    assert (article, name) == ("an" if name[0] in "aeiou" else "a", dimension.value)
