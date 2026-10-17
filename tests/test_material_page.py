"""The material and temper pickers on the Sheet Metal page (ADR-0014 §3).

Skipped when PySide6 is not installed.
"""

from __future__ import annotations

import pytest

from caddcalc.calculators.sheet_metal import DOMAIN as SHEET_METAL
from tests.qt_helpers import open_window

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
