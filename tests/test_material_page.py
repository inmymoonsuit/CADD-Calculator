"""The material and temper pickers on the Sheet Metal page (ADR-0014 §3).

Skipped when PySide6 is not installed.
"""

from __future__ import annotations

import pytest

from caddcalc.calculators.sheet_metal import DOMAIN as SHEET_METAL
from tests.qt_helpers import open_window, type_into

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
    assert window.domain_settings.choice(SHEET_METAL, "temper") == "temper:annealed"
    no_groups, tempers = window.choice_rows["temper"]
    assert no_groups is None and tempers.currentData() == "temper:annealed"
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
