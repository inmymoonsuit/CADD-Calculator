"""The in-memory domain settings model and typed values (ADR-0013 §7, §9)."""

from __future__ import annotations

import math
from dataclasses import replace

import pytest

from caddcalc.calculators.sheet_metal import DOMAIN as SHEET_METAL
from caddcalc.calculators.sheet_metal import BendAllowance
from caddcalc.core import (
    Dimension,
    Domain,
    DomainSettings,
    DomainValues,
    InputError,
    Note,
    NoteKind,
    OutOfRangeError,
    Param,
    Reference,
    SourceKind,
    TypedValue,
    UsageError,
    ValueOrigin,
    parse_quantity_detailed,
)
from caddcalc.core.formatting import DisplayPrefs, describe_source, entry_text, field_text
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


@pytest.mark.parametrize(
    ("value", "text", "unit", "explicit"),
    [
        (3.0, "90 deg", "mm", True),
        (3.0, "3", "in", False),
        (76.2, "3", "in", True),
        (3.0, "abc", "mm", False),
    ],
)
def test_a_typed_value_must_agree_with_its_own_text(
    value: float, text: str, unit: str, explicit: bool
) -> None:
    with pytest.raises(UsageError, match="TypedValue text"):
        TypedValue(value, text, get_unit(unit), explicit_unit=explicit)


def test_a_typed_value_may_differ_from_its_parse_by_one_ulp() -> None:
    exact = TypedValue.parse("1/3", Dimension.LENGTH, "in").value
    nudged = math.nextafter(exact, math.inf)
    assert TypedValue(nudged, "1/3", get_unit("in"), explicit_unit=False).value == nudged


INCHES, MILLIMETRES = DisplayPrefs(length_unit="in"), DisplayPrefs(length_unit="mm")


def test_a_field_shows_the_users_text_while_its_unit_is_the_display_unit() -> None:
    third = TypedValue.parse("1/3", Dimension.LENGTH, "in")
    switches = [INCHES, MILLIMETRES, INCHES, MILLIMETRES, INCHES]
    assert [entry_text(third, prefs) for prefs in switches] == [
        "1/3",
        "8.466667",
        "1/3",
        "8.466667",
        "1/3",
    ]
    assert third.value == 1 / 3 * 25.4, "showing it never changes the value"


@pytest.mark.parametrize(
    ("text", "dimension", "default", "shown_in_mm"),
    [
        ("3 mm", Dimension.LENGTH, "in", "3 mm"),
        ('1-1/2"', Dimension.LENGTH, "mm", '1-1/2"'),
        ("0.44", Dimension.RATIO, None, "0.44"),
        ("44%", Dimension.RATIO, None, "44%"),
        ("90", Dimension.ANGLE, None, "90"),
        ("2", Dimension.LENGTH, "in", "50.8"),
    ],
)
def test_a_field_keeps_text_that_names_its_unit_or_needs_none(
    text: str, dimension: Dimension, default: str | None, shown_in_mm: str
) -> None:
    assert entry_text(TypedValue.parse(text, dimension, default), MILLIMETRES) == shown_in_mm


def test_field_text_is_the_display_value_without_trailing_zeros() -> None:
    assert field_text(0.1046 * 25.4, Dimension.LENGTH, MILLIMETRES) == "2.65684"
    assert field_text(25.4, Dimension.LENGTH, INCHES) == "1"
    assert field_text(0.0, Dimension.RATIO, INCHES) == "0"


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


FAA = Reference("FAA-H-8083-31B", locator="p. 4-63")
TEST_BEND = Note(NoteKind.WARNING, "A starting value: confirm K with a test bend.", (FAA,))


def applied_k() -> DomainSettings:
    """Settings with a K-factor the user applied from a citation, as a click would."""
    entry = TypedValue.parse("0.445", Dimension.RATIO)
    return DomainSettings().set(SHEET_METAL, "k_factor", entry, origin=FAA, note=TEST_BEND)


def test_an_applied_value_keeps_its_citation_in_results() -> None:
    settings = applied_k()
    assert settings.origin(SHEET_METAL, "k_factor") == ValueOrigin(FAA, TEST_BEND)
    result = BendAllowance().run(method="k_factor", settings=settings.for_domain(SHEET_METAL))
    source = result.source_of("k_factor")
    assert (source.kind, source.reference) == (SourceKind.DOMAIN, FAA)
    assert describe_source(source) == (
        "Sheet Metal settings, starting value from FAA-H-8083-31B, p. 4-63"
    )
    assert replace(TEST_BEND, subjects=("k_factor",)) in result.notes
    reference = result.to_dict()["inputs"]["k_factor"]["source"]["reference"]
    assert (reference["title"], reference["locator"]) == ("FAA-H-8083-31B", "p. 4-63")


def test_typing_over_an_applied_value_drops_its_citation() -> None:
    typed = applied_k().set_text(SHEET_METAL, "k_factor", "0.445")
    assert typed.origin(SHEET_METAL, "k_factor") is None
    assert typed != applied_k(), "models compare their origins too"
    result = BendAllowance().run(method="k_factor", settings=typed.for_domain(SHEET_METAL))
    assert result.source_of("k_factor").reference is None
    assert all(note.text != TEST_BEND.text for note in result.notes)
    assert applied_k().clear(SHEET_METAL, "k_factor") == DomainSettings()
    assert applied_k().clear_domain(SHEET_METAL) == DomainSettings()


def test_an_applied_values_note_needs_its_origin_and_no_subjects() -> None:
    entry = TypedValue.parse("0.445", Dimension.RATIO)
    with pytest.raises(UsageError, match="needs the origin"):
        DomainSettings().set(SHEET_METAL, "k_factor", entry, note=TEST_BEND)
    about_k = replace(TEST_BEND, subjects=("k_factor",))
    with pytest.raises(UsageError, match="has subjects"):
        DomainSettings().set(SHEET_METAL, "k_factor", entry, origin=FAA, note=about_k)
    with pytest.raises(UsageError, match="origins of unset"):
        DomainValues(
            "sheet_metal", "Sheet Metal settings", {}, origins={"k_factor": ValueOrigin(FAA)}
        )


def test_the_domain_values_carry_the_selections_in_effect() -> None:
    values = DomainSettings().set_choice(SHEET_METAL, "gauge", "msg:12").for_domain(SHEET_METAL)
    assert dict(values.selections) == {"gauge": "msg:12"}
    assert dict(DomainSettings().for_domain(SHEET_METAL).selections) == {}
    with pytest.raises(TypeError):
        values.selections["gauge"] = "msg:10"  # type: ignore[index]


@pytest.mark.parametrize("dimension", list(Dimension))
def test_every_dimension_has_its_name_with_an_article(dimension: Dimension) -> None:
    article, name = dimension.with_article.split()
    assert (article, name) == ("an" if name[0] in "aeiou" else "a", dimension.value)
