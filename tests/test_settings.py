"""The in-memory domain settings model and typed values (ADR-0013 §7, §9)."""

from __future__ import annotations

import pytest

from caddcalc.calculators.sheet_metal import DOMAIN as SHEET_METAL
from caddcalc.calculators.sheet_metal import BendAllowance
from caddcalc.core import (
    Dimension,
    Domain,
    DomainSettings,
    InputError,
    Param,
    SourceKind,
    SpecError,
    TypedValue,
)

OTHER = Domain(
    "other",
    "Other",
    "A second domain.",
    settings=(Param("thickness", "T", "Thickness", Dimension.LENGTH),),
)


def test_typed_values_keep_the_users_text_and_its_exact_parse() -> None:
    third = TypedValue.parse(" 1/3 ", Dimension.LENGTH, "in")
    assert third == TypedValue(1 / 3 * 25.4, "1/3", "in")
    assert TypedValue.parse("3 mm", Dimension.LENGTH, "in").value == 3.0
    assert TypedValue.parse("0.44", Dimension.RATIO).unit is None


def test_nothing_is_set_at_first() -> None:
    settings = DomainSettings()
    assert settings.get("sheet_metal", "thickness") is None
    values = settings.for_domain(SHEET_METAL)
    assert (values.domain_id, values.label, dict(values.values)) == (
        "sheet_metal",
        "Sheet Metal settings",
        {},
    )


def test_setting_text_keeps_intent_and_returns_a_new_model() -> None:
    empty = DomainSettings()
    settings = empty.set_text(SHEET_METAL, "thickness", "1/3", "in")
    assert empty.get("sheet_metal", "thickness") is None, "the model is immutable"
    entry = settings.get("sheet_metal", "thickness")
    assert entry == TypedValue(1 / 3 * 25.4, "1/3", "in")
    assert settings.for_domain(SHEET_METAL).values == {"thickness": 1 / 3 * 25.4}


def test_settings_are_validated_against_the_domain() -> None:
    settings = DomainSettings()
    with pytest.raises(SpecError, match="no setting 'gauge'"):
        settings.set_text(SHEET_METAL, "gauge", "12")
    with pytest.raises(InputError, match="greater than 0"):
        settings.set_text(SHEET_METAL, "thickness", "0", "in")
    with pytest.raises(InputError, match="at most 1"):
        settings.set_text(SHEET_METAL, "k_factor", "1.2")
    with pytest.raises(InputError, match="Cannot read a value"):
        settings.set_text(SHEET_METAL, "inside_radius", "abc", "in")
    with pytest.raises(InputError, match="measures angle, but length is expected"):
        settings.set_text(SHEET_METAL, "thickness", "3 deg", "in")


def test_domains_are_independent_and_can_be_cleared() -> None:
    settings = (
        DomainSettings()
        .set_text(SHEET_METAL, "thickness", "0.1046", "in")
        .set_text(SHEET_METAL, "k_factor", "0.44")
        .set_text(OTHER, "thickness", "2 mm")
    )
    assert set(settings.values("sheet_metal")) == {"thickness", "k_factor"}
    assert settings.for_domain(OTHER).values == {"thickness": 2.0}

    without_k = settings.clear("sheet_metal", "k_factor")
    assert set(without_k.values("sheet_metal")) == {"thickness"}
    cleared = settings.clear_domain("sheet_metal")
    assert dict(cleared.values("sheet_metal")) == {}
    assert cleared.for_domain(OTHER).values == {"thickness": 2.0}


def test_the_values_view_is_read_only() -> None:
    settings = DomainSettings().set_text(SHEET_METAL, "k_factor", "0.44")
    view = settings.values("sheet_metal")
    with pytest.raises(TypeError):
        view["k_factor"] = TypedValue(0.5, "0.5")  # type: ignore[index]


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
