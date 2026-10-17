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
from tests.qt_helpers import open_window, type_into

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
    return f"Sheet Metal settings, starting value from {table.sources[entry.source].reference}"


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
    assert "Limit exceeded: The inside radius is below the minimum for 6061-T6" in shown
    assert "Inside radius is smaller than the material thickness" not in shown
    window.close()
