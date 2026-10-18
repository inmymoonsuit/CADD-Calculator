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
        fields = window.results.fields
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
        field = window.results.fields[output.key]
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
    for field in window.results.fields.values():
        assert field.parts is None and field.value.text() == "—"
        assert not field.copy_button.isEnabled()
        assert field.copy_button.toolTip() == "No value to copy"
    type_into(thickness, "0.1046")
    assert all(f.parts is not None for f in window.results.fields.values())
    window.close()


def test_a_note_about_an_output_outlines_its_field() -> None:
    """The formed segment's flat length goes negative when the segment is too short."""
    window = open_window()
    window.select_calculator("sheet_metal.segment_flat_length")
    type_into(window.fields["formed_dimension"][1], "0.05")
    fields = window.results.fields
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
    panel = window.results
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


def _shown_at(width: int, height: int, calc_id: str) -> Any:
    """A window of that size, showing ``calc_id``, laid out."""
    from PySide6.QtWidgets import QApplication

    window = open_window()
    window.select_calculator(calc_id)
    window.resize(width, height)
    window.show()
    for _ in range(3):  # the page area settles over a few layout passes
        QApplication.processEvents()
    return window


def _in_full_view(window: Any, field: Any) -> bool:
    """Whether every pixel of ``field``, at its full height, is in the page's view."""
    from PySide6.QtCore import QPoint, QRect

    view = window.page_scroll.viewport()
    rect = QRect(field.mapTo(view, QPoint(0, 0)), field.size())
    full = field.height() == field.sizeHint().height()
    return full and QRect(QPoint(0, 0), view.size()).contains(rect)


@pytest.mark.parametrize(
    "calc_id", ["sheet_metal.bend_allowance", "sheet_metal.truncated_cone_layout"]
)
def test_every_field_shows_in_full_at_the_default_size(calc_id: str) -> None:
    """The results are never hidden behind their own scroll bar (ADR-0017 R3, amended)."""
    from PySide6.QtWidgets import QAbstractScrollArea, QScrollBar

    window = _shown_at(1100, 720, calc_id)
    panel = window.results
    assert not isinstance(panel, QAbstractScrollArea)
    assert not panel.findChildren(QScrollBar), "the results have no scroll bar of their own"
    assert panel.height() == panel.sizeHint().height()
    for key, field in panel.fields.items():
        assert _in_full_view(window, field), key
    window.close()


def test_a_short_window_scrolls_the_page_and_reaches_every_field_in_full() -> None:
    from caddcalc.gui.ui_style import ui_style

    window = _shown_at(1100, 420, "sheet_metal.truncated_cone_layout")
    page = window.page_scroll
    assert page.verticalScrollBar().maximum() > 0, "the page scrolls as a whole"
    panel = window.results
    assert panel.height() == panel.sizeHint().height(), "the results are never squeezed"
    least = ui_style().result_field.document_min_height
    assert window.output.height() == least, "a page that scrolls keeps no spare document"
    from PySide6.QtWidgets import QApplication

    for key, field in panel.fields.items():
        page.ensureWidgetVisible(field, 0, 0)
        QApplication.processEvents()
        assert _in_full_view(window, field), key
    window.close()


def test_the_document_still_scrolls_on_its_own() -> None:
    window = _shown_at(1100, 420, "sheet_metal.truncated_cone_layout")
    page, document = window.page_scroll.verticalScrollBar(), window.output.verticalScrollBar()
    assert document.maximum() > 0
    before = page.value()
    document.setValue(document.maximum())
    assert document.value() == document.maximum() and page.value() == before
    window.close()


def test_the_page_is_never_narrower_than_its_content() -> None:
    """The page scrolls vertically only, so a narrower page would clip its right side."""
    from PySide6.QtWidgets import QApplication

    window = _shown_at(1100, 720, "sheet_metal.truncated_cone_layout")
    window.resize(1, 720)  # as narrow as the window allows
    for _ in range(3):
        QApplication.processEvents()
    page = window.page_scroll
    assert page.widget().width() <= page.viewport().width()
    window.close()


def test_a_family_page_is_not_made_to_scroll_by_the_hidden_calculator_page() -> None:
    from PySide6.QtWidgets import QApplication

    window = _shown_at(1100, 420, "sheet_metal.truncated_cone_layout")
    assert window.page_scroll.verticalScrollBar().maximum() > 0
    window.select_domain("sheet_metal")
    for _ in range(3):
        QApplication.processEvents()
    assert window.page_scroll.verticalScrollBar().maximum() == 0
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
    (field,) = window.results.fields.values()
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
    field: Any = window.results.fields["bend_allowance"]
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
