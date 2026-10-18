"""Result fields: one boxed field per output, for every calculator (ADR-0017)."""

from __future__ import annotations

from typing import Any

import pytest

from caddcalc.core.formatting import DisplayPrefs, output_parts
from tests.qt_helpers import open_window, results_text, type_into

pytestmark = [pytest.mark.gui, pytest.mark.usefixtures("qt")]


def test_every_calculator_gets_one_field_per_output_in_order() -> None:
    window = open_window()
    for calc in window.registry:
        window.select_calculator(calc.id)
        fields = window.results.panel.fields
        assert list(fields) == [o.key for o in calc.outputs], calc.id
        for output in calc.outputs:
            field = fields[output.key]
            assert (field.symbol.text(), field.label.full_text) == (output.symbol, output.label)
    window.close()


def test_a_field_shows_its_output_as_the_core_presents_it() -> None:
    window = open_window()
    window.select_calculator("sheet_metal.bend_allowance")
    window.method_box.setCurrentIndex(0)  # course: BA = 0.3119 in
    result, calc = window.result, window.calculator
    assert result is not None and calc is not None
    for output in calc.outputs:
        field = window.results.panel.fields[output.key]
        parts = output_parts(output, result.outputs[output.key], DisplayPrefs())
        assert field.parts == parts
        assert (field.value.text(), field.unit.text()) == (parts.number, parts.unit)
        assert field.copy_button.isEnabled()
    assert "BA Bend allowance 0.3119 in" in results_text(window)
    document = window.output.toPlainText()
    assert "Results" not in document.splitlines()[0], "the document starts after the results"
    assert "Inputs" in document and "Work" in document
    window.close()


def test_invalid_inputs_blank_every_field_so_no_old_value_shows() -> None:
    window = open_window()
    window.select_calculator("sheet_metal.bend_allowance")
    _param, thickness = window.fields["thickness"]
    type_into(thickness, "abc", enter=False)
    for field in window.results.panel.fields.values():
        assert field.parts is None and field.value.text() == "—"
        assert not field.copy_button.isEnabled()
        assert field.copy_button.toolTip() == "No value to copy"
    type_into(thickness, "0.1046")
    assert all(f.parts is not None for f in window.results.panel.fields.values())
    window.close()


def test_a_note_about_an_output_outlines_its_field() -> None:
    """The formed segment's flat length goes negative when the segment is too short."""
    window = open_window()
    window.select_calculator("sheet_metal.segment_flat_length")
    type_into(window.fields["formed_dimension"][1], "0.05")
    fields = window.results.panel.fields
    flat = fields["flat_length"]
    assert flat.outline is not None
    assert (flat.outline.role, flat.outline.width) == ("outline_note", 2)
    assert fields["bend_allowance_1"].outline is None
    window.close()


def test_values_line_up_on_the_decimal_point() -> None:
    """The cone shows lengths to 4 places and its angle to 2; their points align."""
    from PySide6.QtCore import QPoint
    from PySide6.QtGui import QFontMetricsF

    window = open_window()
    window.select_calculator("sheet_metal.truncated_cone_layout")
    window.show()
    panel = window.results.panel
    points = []
    for field in panel.fields.values():
        label = field.value
        _whole, _point, places = label.text().partition(".")
        metrics = QFontMetricsF(label.font())
        right = label.mapTo(panel, QPoint(label.width(), 0)).x()
        point = right - label.contentsMargins().right() - metrics.horizontalAdvance("." + places)
        points.append(round(point))
    assert len(set(points)) == 1, points
    assert {len(f.value.text().partition(".")[2]) for f in panel.fields.values()} == {2, 4}
    window.close()


def test_the_document_keeps_its_height_and_the_results_scroll() -> None:
    """At a short window, the results shrink and scroll; the document keeps 160 px."""
    from caddcalc.gui.ui_style import ui_style

    window = open_window()
    window.select_calculator("sheet_metal.truncated_cone_layout")
    window.resize(1100, 420)
    window.show()
    from PySide6.QtWidgets import QApplication

    QApplication.processEvents()
    assert window.output.height() >= ui_style().result_field.document_min_height
    area = window.results
    assert area.height() >= area.panel.first_field_height()
    assert area.verticalScrollBar().maximum() > 0, "the fields scroll on their own"
    window.close()


def test_a_plugin_calculator_gets_fields_with_no_code_of_its_own() -> None:
    from caddcalc.core import Registry
    from caddcalc.gui.window import MainWindow
    from tests.test_domains import ACME, _AcmeWidget

    registry = Registry()
    registry.register_domain(ACME)
    registry.register(_AcmeWidget)
    window = MainWindow(registry=registry)
    window.select_calculator("acme.widget")
    (field,) = window.results.panel.fields.values()
    assert (field.symbol.text(), field.value.text(), field.unit.text()) == ("Y", "1.0000", "in")
    window.close()


def test_the_disclaimer_comes_back_after_a_passing_message() -> None:
    from caddcalc.core.formatting import DISCLAIMER

    window = open_window()
    window.show()
    assert window.disclaimer.text() == DISCLAIMER and window.disclaimer.isVisible()
    window.statusBar().showMessage("Copied BA = 0.3119 to the clipboard")
    window.statusBar().clearMessage()
    assert window.disclaimer.isVisible()
    window.close()


@pytest.mark.parametrize("scheme", ["light", "dark"])
def test_a_field_draws_its_border_and_its_outline(
    scheme: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    from caddcalc.gui import result_fields
    from caddcalc.gui.icons import role_color
    from caddcalc.gui.outlines import Outline

    monkeypatch.setattr(result_fields, "current_scheme", lambda: scheme)
    window = open_window()
    window.select_calculator("sheet_metal.bend_allowance")
    window.show()
    field: Any = window.results.panel.fields["bend_allowance"]
    frame = field.frame.toRect()
    middle = frame.center().x()
    image = field.grab().toImage()
    assert image.pixelColor(middle, frame.top()).name().upper() == role_color(
        "field_border", scheme
    )
    field.show_parts(field.parts, Outline("outline_limit", "solid", 2, 3))
    image = field.grab().toImage()
    limit = role_color("outline_limit", scheme)
    assert image.pixelColor(middle, frame.top()).name().upper() == limit
    assert image.pixelColor(middle, frame.top() + 1).name().upper() == limit, "2 px"
    window.close()
