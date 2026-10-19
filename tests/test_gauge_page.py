"""The gauge picker, and derived values on calculator pages (ADR-0014 §2).

Skipped when PySide6 is not installed.
"""

from __future__ import annotations

from typing import Any

import pytest

from caddcalc.calculators.sheet_metal import DOMAIN as SHEET_METAL
from tests.qt_helpers import open_window, plain, results_text, show_in, type_into

pytestmark = [pytest.mark.gui, pytest.mark.usefixtures("qt")]

BEND = "sheet_metal.bend_allowance"
MSG = "Manufacturers' Standard, steel sheet"
GALVANIZED = "Galvanized, coated steel sheet"
GAUGE_SOURCE = "12 ga, Manufacturers' Standard, steel sheet (nominal), Gauge systems, version 3"
CAUTION = (
    "Nominal thickness; mill tolerances apply (see ASTM A568/A568M, 2025, rev. a). Check the "
    "material's specification or measure before cutting."
)


def pick(window: Any, system: str | None, gauge: str | None = None) -> None:
    """Pick a gauge system, and a gauge in it, on the Sheet Metal page."""
    window.select_domain("sheet_metal")
    systems, gauges = window.choice_rows["gauge"]
    systems.setCurrentIndex(0 if system is None else systems.findData(system))
    if gauge is not None:
        gauges.setCurrentIndex(gauges.findText(gauge))


def gauge(window: Any) -> str | None:
    chosen: str | None = window.domain_settings.choice(SHEET_METAL, "gauge")
    return chosen


def about(window: Any, key: str) -> str:
    return plain(window.setting_abouts[key].text())


def result(window: Any) -> str:
    return results_text(window)


def source_of(window: Any, key: str) -> str:
    from caddcalc.core.formatting import describe_source

    return describe_source(window.result.source_of(key))


def test_no_gauge_is_chosen_by_default_so_thickness_is_typed() -> None:
    window = open_window()
    window.select_domain("sheet_metal")
    systems, gauges = window.choice_rows["gauge"]
    assert [systems.itemText(i) for i in range(systems.count())] == [
        "None",
        "Manufacturers' Standard, steel sheet",
        "Galvanized, coated steel sheet",
        "US Standard 1893, as commonly used for stainless; practice varies",
        "AWG (Brown & Sharpe), nonferrous",
    ]
    assert (gauges.currentText(), gauges.isEnabled()) == ("Choose…", False)
    assert gauge(window) is None
    assert window.setting_fields["thickness"][1].placeholderText() == "not set"
    window.close()


def test_choosing_a_gauge_shows_the_derived_thickness_its_caution_and_work() -> None:
    window = open_window()
    pick(window, MSG)
    _systems, gauges = window.choice_rows["gauge"]
    assert gauges.isEnabled() and gauges.count() == 37, "Choose… and gauges 3 to 38"
    assert gauge(window) is None, "a system alone chooses nothing"

    pick(window, MSG, "12 ga")
    assert gauge(window) == "msg:12"
    thickness = window.setting_fields["thickness"][1]
    assert (thickness.text(), thickness.placeholderText()) == (
        "",
        "0.1046 in (12 ga, Manufacturers' Standard, steel sheet (nominal))",
    )
    text = about(window, "thickness")
    assert f"From {GAUGE_SOURCE}: 0.1046 in" in text
    assert CAUTION in text
    assert (
        "Work: T = (w + c) / 16 / B = (70 + 0) / 16 / 41.82 = 0.1046 in "
        "(0.1046150167… in before rounding to 4 decimal places)"
    ) in text
    window.close()


def test_changing_the_system_resets_the_gauge_number() -> None:
    window = open_window()
    pick(window, MSG, "12 ga")
    pick(window, GALVANIZED)
    _systems, gauges = window.choice_rows["gauge"]
    assert gauge(window) is None
    assert (gauges.currentText(), gauges.count()) == ("Choose…", 28)
    assert window.setting_fields["thickness"][1].placeholderText() == "not set"

    pick(window, GALVANIZED, "12 ga")
    assert gauge(window) == "galv:12"
    pick(window, None)
    assert gauge(window) is None and not window.choice_rows["gauge"][1].isEnabled()
    window.close()


def test_a_typed_thickness_overrides_the_gauge_and_clearing_it_restores_the_gauge() -> None:
    window = open_window()
    pick(window, MSG, "12 ga")
    thickness = window.setting_fields["thickness"][1]
    type_into(thickness, "0.125")
    assert f"Overrides 0.1046 in from {GAUGE_SOURCE}" in about(window, "thickness")
    window.select_calculator(BEND)
    assert source_of(window, "thickness") == "Sheet Metal settings"
    assert window.result.notes == ()

    window.select_domain("sheet_metal")
    type_into(window.setting_fields["thickness"][1], "")
    assert f"From {GAUGE_SOURCE}" in about(window, "thickness")
    window.select_calculator(BEND)
    assert source_of(window, "thickness") == GAUGE_SOURCE
    window.close()


def test_a_derived_thickness_inherits_like_a_set_value_and_shows_its_work_first() -> None:
    window = open_window()
    pick(window, MSG, "12 ga")
    window.select_calculator(BEND)
    window.method_box.setCurrentIndex(window.method_box.findData("course"))

    thickness = window.fields["thickness"][1]
    assert thickness.isReadOnly(), "a derived value is read-only, like a set one"
    box = window.inherit_boxes["thickness"]
    assert not box.isHidden() and box.isChecked()
    assert source_of(window, "thickness") == GAUGE_SOURCE
    shown = result(window)
    assert CAUTION in shown
    work = shown.index("T = (w + c) / 16 / B")
    assert work < shown.index("BA = "), "the derived work comes before the calculator's"
    assert "(0.1046150167… in before rounding to 4 decimal places)" in shown
    assert window.result.outputs == window.registry.get(BEND).run(method="course").outputs
    window.close()


def test_an_unticked_copy_keeps_the_gauges_name_and_its_caution() -> None:
    window = open_window()
    pick(window, MSG, "12 ga")
    window.select_calculator(BEND)
    window.inherit_boxes["thickness"].setChecked(False)
    assert source_of(window, "thickness") == f"copied from {GAUGE_SOURCE}"
    (note,) = window.result.notes
    assert (note.text, note.subjects) == (CAUTION, ("thickness",))
    assert "T = (w + c)" not in result(window), "the copy is explicit; the gauge isn't used"
    *_, settings = window._run_arguments(window.registry.get(BEND))
    assert "thickness" not in settings.derived, "an overridden key passes no derived value"

    pick(window, MSG, "10 ga")
    window.select_calculator(BEND)
    assert source_of(window, "thickness") == f"copied earlier from {GAUGE_SOURCE}"
    assert [n.text for n in window.result.notes] == [CAUTION]

    type_into(window.fields["thickness"][1], "0.125")
    assert source_of(window, "thickness") == "entered"
    assert window.result.notes == ()
    window.close()


def test_the_us_standard_source_keeps_its_scope() -> None:
    window = open_window()
    pick(window, "US Standard 1893, as commonly used for stainless; practice varies", "12 ga")
    window.select_calculator(BEND)
    assert source_of(window, "thickness") == (
        "12 ga, US Standard 1893, as commonly used for stainless; practice varies (nominal), "
        "Gauge systems, version 3"
    )
    assert window.fields["thickness"][1].text().startswith("0.109375")
    window.close()


def test_clear_all_returns_the_gauge_to_none() -> None:
    window = open_window()
    pick(window, MSG, "12 ga")
    window.clear_settings_button.click()
    systems, gauges = window.choice_rows["gauge"]
    assert gauge(window) is None
    assert (systems.currentText(), gauges.isEnabled()) == ("None", False)
    assert window.setting_fields["thickness"][1].placeholderText() == "not set"
    window.close()


def test_the_gauges_work_is_true_in_millimetres() -> None:
    """The work's expression gives inches, so it shows inches, then the results' unit.

    The settings page shows inches until its fields get pickers (KI-027).
    """
    window = open_window()
    pick(window, MSG, "12 ga")
    assert "= (70 + 0) / 16 / 41.82 = 0.1046 in" in about(window, "thickness")
    assert "mm" not in about(window, "thickness")

    window.select_calculator(BEND)
    show_in(window, "mm")
    shown = result(window)
    assert "= (70 + 0) / 16 / 41.82\n" in shown
    assert "= 0.1046 in = 2.6568 mm\n" in shown
    window.close()


def test_the_wheel_doesnt_change_a_gauge() -> None:
    """A wheel tick over a box never changes the gauge while T has the focus."""
    from PySide6.QtCore import QPoint, QPointF, Qt
    from PySide6.QtGui import QWheelEvent
    from PySide6.QtWidgets import QApplication

    window = open_window()
    pick(window, MSG, "12 ga")
    window.setting_fields["thickness"][1].setFocus()
    for box in window.choice_rows["gauge"]:
        assert box.focusPolicy() is Qt.FocusPolicy.StrongFocus
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
    assert gauge(window) == "msg:12"
    systems, gauges = window.choice_rows["gauge"]
    assert (systems.currentText(), gauges.currentText()) == (MSG, "12 ga")
    window.close()


@pytest.mark.parametrize("unit", ["in", "mm"])
@pytest.mark.parametrize(
    ("system", "size", "stated"),
    [
        (
            "US Standard 1893, as commonly used for stainless; practice varies",
            "12 ga",
            "0.109375 in",
        ),
        ("AWG (Brown & Sharpe), nonferrous", "40 AWG", "0.00314 in"),
    ],
)
def test_both_pages_show_the_stated_thickness_in_the_work(
    unit: str, system: str, size: str, stated: str
) -> None:
    """The work gives the stated value, never one rounded to the display decimals."""
    window = open_window()
    show_in(window, unit)
    pick(window, system, size)
    text = about(window, "thickness")
    assert f"= {stated}" in text
    assert "= 0.1094 in" not in text and "= 0.0031 in" not in text
    window.select_calculator(BEND)
    assert f"= {stated}" in result(window)
    window.close()
