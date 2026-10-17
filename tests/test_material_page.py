"""The material and temper pickers on the Sheet Metal page (ADR-0014 §3).

Skipped when PySide6 is not installed.
"""

from __future__ import annotations

from typing import Any

import pytest

from caddcalc.calculators.sheet_metal import DOMAIN as SHEET_METAL
from caddcalc.calculators.sheet_metal.materials import MATERIAL_TABLE
from caddcalc.core import Dimension, Note, NoteKind, TypedValue, ValueOrigin
from caddcalc.core.formatting import describe_source
from tests.qt_helpers import open_window, plain, type_into

BEND = "sheet_metal.bend_allowance"
TEST_BEND = Note(NoteKind.WARNING, "A starting value: confirm K with a test bend.")


def apply_faa_k(window: Any) -> str:
    """Apply the table's FAA K-factor to the family, as its button will; return its source."""
    table = MATERIAL_TABLE.load()
    entry = next(v for v in MATERIAL_TABLE.values(table) if v.source == "faa_neutral_axis")
    window.domain_settings = window.domain_settings.set(
        SHEET_METAL,
        "k_factor",
        TypedValue.parse("0.445", Dimension.RATIO),
        origin=ValueOrigin.of(table, entry, TEST_BEND),
    )
    return (
        f"Sheet Metal settings, starting value from {table.sources[entry.source].reference.short}"
    )


def open_k_factor_bend(window: Any) -> None:
    window.select_calculator(BEND)
    window.method_box.setCurrentIndex(window.method_box.findData("k_factor"))


def k_source(window: Any) -> str:
    return describe_source(window.result.source_of("k_factor"))


def test_an_unticked_copy_of_an_applied_k_keeps_its_citation_and_note() -> None:
    """Review M1: the copy credits the starting value and carries its prompt."""
    window = open_window()
    applied = apply_faa_k(window)
    open_k_factor_bend(window)
    assert k_source(window) == applied
    window.inherit_boxes["k_factor"].setChecked(False)
    assert window.result is not None, "the page shows a result, not an input error"
    assert k_source(window) == f"copied from {applied}"
    assert [n.subjects for n in window.result.notes if n.text == TEST_BEND.text] == [("k_factor",)]
    *_, settings = window._run_arguments(window.registry.get(BEND))
    assert "k_factor" not in settings.origins, "an overridden key passes no origin"
    type_into(window.fields["k_factor"][1], "0.42")
    assert k_source(window) == "entered"
    assert all(n.text != TEST_BEND.text for n in window.result.notes)
    window.close()


def test_a_calculators_own_k_overrides_an_applied_one() -> None:
    """Review M1: an overriding field's own value runs, with no origin left over."""
    window = open_window()
    open_k_factor_bend(window)
    window.inherit_boxes["k_factor"].setChecked(False)
    type_into(window.fields["k_factor"][1], "0.42")
    apply_faa_k(window)
    open_k_factor_bend(window)
    assert window.result is not None
    assert window.result.inputs["k_factor"] == pytest.approx(0.42)
    assert all(n.text != TEST_BEND.text for n in window.result.notes)
    window.close()


pytestmark = [pytest.mark.gui, pytest.mark.usefixtures("qt")]


def choose(window: Any, group: str, material: str) -> None:
    """Choose a material on the Sheet Metal page, as a user does."""
    window.select_domain("sheet_metal")
    groups, materials = window.choice_rows["material"]
    groups.setCurrentIndex(groups.findData(group))
    materials.setCurrentIndex(materials.findData(material))


def set_family(window: Any, key: str, text: str) -> None:
    window.select_domain("sheet_metal")
    type_into(window.setting_fields[key][1], text)


def facts(window: Any) -> str:
    return plain(window.facts_label.text())


def starts(window: Any) -> list[str]:
    return [b.text() for b in window.start_buttons["k_factor"]]


def test_a_temper_its_material_marks_offers_no_none() -> None:
    window = open_window()
    window.select_domain("sheet_metal")
    _none, tempers = window.choice_rows["temper"]
    assert (tempers.count(), tempers.isEnabled()) == (1, False), "no material: None, disabled"
    choose(window, "Aluminum", "al:6061")
    _none, tempers = window.choice_rows["temper"]
    assert [tempers.itemText(i) for i in range(tempers.count())] == ["T6"]
    window.close()


def test_the_facts_show_the_materials_rule_strengths_and_notes() -> None:
    window = open_window()
    window.select_domain("sheet_metal")
    assert not window.settings_form.isRowVisible(window.facts_label), "nothing chosen"
    choose(window, "Aluminum", "al:6061")
    shown = facts(window)
    assert window.settings_form.isRowVisible(window.facts_label)
    assert (
        "checked against the recommended minimums of AC 43.13-1B (2024 ed. update) and "
        "TO 1-1A-9 (2020 Change 3), aerospace bending practice; where they differ, the larger"
    ) in shown
    assert "aircraft repair practice" in shown, "each source's scope"
    assert "Bending practice: Form across the grain" in shown
    assert "F_tu 42.0 ksi (L)" in shown and "A-basis allowables, MIL-HDBK-5J" in shown
    choose(window, "Stainless steel", "ss:304")
    assert "TO's only 304 row, for ½ Hard" in facts(window)
    choose(window, "Carbon steel", "cs:a653")
    assert "zinc coating can flake" in facts(window) and "Strength" not in facts(window)
    window.close()


@pytest.mark.parametrize(("unit", "shown"), [("in", "F_tu 42.0 ksi"), ("mm", "F_tu 289.6 MPa")])
def test_strengths_follow_the_length_unit(unit: str, shown: str) -> None:
    window = open_window()
    window.units_box.setCurrentIndex(window.units_box.findText(unit))
    choose(window, "Aluminum", "al:6061")
    assert shown in facts(window)
    window.close()


def test_k_starting_values_are_offered_for_the_materials_they_cover() -> None:
    window = open_window()
    window.select_domain("sheet_metal")
    assert starts(window) == []
    choose(window, "Aluminum", "al:6061")
    assert starts(window) == [
        "Use 0.445, FAA-H-8083-31B",
        "Use 0.4, Engineering Drawing and Design (5th ed.)",
    ]
    assert "test bend" in window.start_buttons["k_factor"][0].toolTip()
    choose(window, "Stainless steel", "ss:304")
    assert starts(window) == ["Use 0.4, Engineering Drawing and Design (5th ed.)"]
    choose(window, "Carbon steel", "cs:a653")
    assert starts(window) == []
    window.close()


def test_applying_a_k_keeps_its_citation_and_prompt_until_typed_over() -> None:
    window = open_window()
    choose(window, "Aluminum", "al:6061")
    window.start_buttons["k_factor"][0].click()
    origin = window.domain_settings.origin(SHEET_METAL, "k_factor")
    assert origin is not None and origin.value.source == "faa_neutral_axis"
    assert window.setting_fields["k_factor"][1].text() == "0.445"
    about = plain(window.setting_abouts["k_factor"].text())
    assert "Starting value from FAA-H-8083-31B" in about and "test bend" in about
    open_k_factor_bend(window)
    assert k_source(window).startswith("Sheet Metal settings, starting value from FAA-H-8083-31B")
    (prompt,) = [n for n in window.result.notes if n.text.startswith("K = 0.445")]
    assert prompt.subjects == ("k_factor",) and "test bend" in prompt.text

    set_family(window, "k_factor", "0.42")
    assert window.domain_settings.origin(SHEET_METAL, "k_factor") is None
    open_k_factor_bend(window)
    assert k_source(window) == "Sheet Metal settings"
    assert all(not n.text.startswith("K = ") for n in window.result.notes)
    window.close()


def test_limit_and_no_value_notes_outline_their_fields_distinctly() -> None:
    from caddcalc.gui.icons import role_color

    window = open_window()
    choose(window, "Aluminum", "al:6061")
    set_family(window, "thickness", "0.063")
    set_family(window, "inside_radius", "0.1")
    window.select_calculator(BEND)
    limit = role_color("outline_limit", "light")
    for key in ("inside_radius", "thickness"):
        assert f"1px solid {limit}" in window.fields[key][1].styleSheet(), key
    shown = window.output.toHtml().lower()
    assert role_color("text_limit", "light").lower() in shown, "the limit note's colour"
    set_family(window, "thickness", "0.3")
    set_family(window, "inside_radius", "0.5")
    window.select_calculator(BEND)
    unchecked = role_color("outline_no_value", "light")
    assert f"1px dashed {unchecked}" in window.fields["thickness"][1].styleSheet()
    assert window.fields["inside_radius"][1].styleSheet() == ""
    set_family(window, "inside_radius", "0.1")
    window.select_calculator(BEND)
    note = role_color("outline_note", "light")
    assert f"1px solid {note}" in window.fields["thickness"][1].styleSheet()
    assert f"1px solid {note}" in window.fields["inside_radius"][1].styleSheet(), (
        "the rule of thumb outranks the unchecked outline"
    )
    window.close()


def test_the_wheel_doesnt_change_a_material_or_temper() -> None:
    from PySide6.QtCore import QPoint, QPointF, Qt
    from PySide6.QtGui import QWheelEvent
    from PySide6.QtWidgets import QApplication

    window = open_window()
    choose(window, "Aluminum", "al:6061")
    window.setting_fields["thickness"][1].setFocus()
    boxes = [*window.choice_rows["material"], window.choice_rows["temper"][1]]
    for box in boxes:
        assert box is not None and box.focusPolicy() is Qt.FocusPolicy.StrongFocus
        for delta in (-120, 120):
            tick = QWheelEvent(
                QPointF(5, 5),
                QPointF(5, 5),
                QPoint(0, 0),
                QPoint(0, delta),
                Qt.MouseButton.NoButton,
                Qt.KeyboardModifier.NoModifier,
                Qt.ScrollPhase.NoScrollPhase,
                False,
            )
            QApplication.sendEvent(box, tick)
    assert window.domain_settings.choice(SHEET_METAL, "material") == "al:6061"
    assert window.domain_settings.choice(SHEET_METAL, "temper") == "temper:6061_t6"
    window.close()


def test_choosing_a_material_selects_its_only_temper() -> None:
    window = open_window()
    window.select_domain("sheet_metal")
    groups, materials = window.choice_rows["material"]
    assert groups is not None
    assert [groups.itemText(i) for i in range(1, groups.count())] == [
        "Aluminum",
        "Carbon steel",
        "Stainless steel",
    ]
    groups.setCurrentIndex(groups.findData("Stainless steel"))
    materials.setCurrentIndex(materials.findData("ss:304"))
    assert materials.currentText() == "304, annealed (2B finish)"
    assert window.domain_settings.choice(SHEET_METAL, "temper") == "temper:304_annealed"
    no_groups, tempers = window.choice_rows["temper"]
    assert no_groups is None and tempers.currentData() == "temper:304_annealed"
    window.close()


def test_a_bend_below_the_materials_minimum_says_so_on_its_page() -> None:
    window = open_window()
    window.select_domain("sheet_metal")
    groups, materials = window.choice_rows["material"]
    groups.setCurrentIndex(groups.findData("Aluminum"))
    materials.setCurrentIndex(materials.findData("al:6061"))
    type_into(window.setting_fields["thickness"][1], "0.063")
    type_into(window.setting_fields["inside_radius"][1], "0.1")
    window.select_calculator("sheet_metal.bend_allowance")
    shown = window.output.toPlainText()
    assert "Limit exceeded: The inside radius is below the recommended minimum for 6061-T6" in shown
    assert "Inside radius is smaller than the material thickness" not in shown
    window.close()
