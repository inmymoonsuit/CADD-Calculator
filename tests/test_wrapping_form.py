"""A form that wraps long rows and never squeezes a field (KI-031, ADR-0021 §7)."""

from __future__ import annotations

from typing import Any

import pytest

pytestmark = [pytest.mark.gui, pytest.mark.usefixtures("qt")]

FIELD = 100
"""The field's least width, in pixels."""


def _form(form_class: Any) -> tuple[Any, Any, Any, Any, Any]:
    """A form of one row: a label, and a field of a layout holding a widget ``FIELD`` wide."""
    from PySide6.QtWidgets import QFormLayout, QHBoxLayout, QWidget

    page = QWidget()
    form = form_class(page)
    form.setContentsMargins(0, 0, 0, 0)
    form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
    widget = QWidget()
    widget.setMinimumWidth(FIELD)
    field = QHBoxLayout()
    field.setContentsMargins(0, 0, 0, 0)
    field.addWidget(widget)
    if hasattr(form, "add_row"):
        form.add_row("Material thickness", field)
    else:
        form.addRow("Material thickness", field)
    label = form.itemAt(0, QFormLayout.ItemRole.LabelRole).widget()
    page.show()
    return page, form, label, field, widget


def _at(page: Any, width: int) -> None:
    from PySide6.QtWidgets import QApplication

    page.resize(width, 200)
    QApplication.processEvents()


def test_qt_squeezes_a_field_when_its_row_is_within_the_gap_of_fitting() -> None:
    """KI-031 as Qt has it: a plain form keeps the row side by side and squeezes the field.

    If this fails, Qt counts the gap now, and ``WrappingForm`` can go.
    """
    from PySide6.QtWidgets import QFormLayout

    page, form, label, field, widget = _form(QFormLayout)
    gap = form.horizontalSpacing()
    assert gap > 1
    _at(page, label.sizeHint().width() + FIELD + gap // 2)
    assert widget.y() == label.y(), "side by side"
    assert field.geometry().width() < FIELD, "given less than its least width"
    page.close()


def test_a_wrapping_form_gives_every_field_its_least_width() -> None:
    """At every width from too narrow to roomy, the field is whole, beside or below."""
    from caddcalc.gui.reflow import WrappingForm

    page, form, label, field, widget = _form(WrappingForm)
    gap = form.gap
    assert gap > 1 and form.horizontalSpacing() == 0
    text = label.sizeHint().width() - gap  # the label's own text, without the gap
    beside = []
    for width in range(text + FIELD - 2, text + gap + FIELD + 3):
        _at(page, width)
        assert field.geometry().width() >= FIELD <= widget.width(), width
        if widget.y() == label.y():
            assert widget.x() >= text + gap, f"the gap is kept at {width}"
            beside.append(width)
        else:
            assert widget.y() > label.y(), f"below its label at {width}"
    assert beside == list(range(text + gap + FIELD, text + gap + FIELD + 3))
    page.close()


def test_the_settings_page_builds_its_form_as_a_wrapping_form() -> None:
    """Each of its labels keeps the gap, and the form adds none of its own."""
    from PySide6.QtWidgets import QFormLayout

    from caddcalc.gui.reflow import WrappingForm
    from tests.qt_helpers import open_window

    window = open_window()
    window.select_domain("sheet_metal")
    form = window.settings_form
    assert isinstance(form, WrappingForm) and form.horizontalSpacing() == 0
    assert form.rowWrapPolicy() == QFormLayout.RowWrapPolicy.WrapLongRows
    labels = [form.itemAt(r, QFormLayout.ItemRole.LabelRole) for r in range(form.rowCount())]
    margins = {item.widget().contentsMargins().right() for item in labels if item is not None}
    assert margins == {form.gap}
    window.close()


def _squeezed(window: Any) -> list[Any]:
    """Every clipped widget narrower than its least width, or past the window's right edge.

    A wrapped label short of its text's height at one width is KI-032, tested below.
    """
    from PySide6.QtCore import QPoint
    from PySide6.QtWidgets import QGroupBox

    from tests.test_translated_gui import _clipped

    return [
        w
        for w in _clipped(window)
        if not isinstance(w, QGroupBox)
        and (
            w.width() < w.minimumSizeHint().width()
            or w.mapTo(window, QPoint(w.width(), 0)).x() > window.width()
        )
    ]


def test_no_settings_row_is_squeezed_at_any_window_width() -> None:
    """The settings page at each width from its least to 400 px wider, a pixel at a time.

    Before ``WrappingForm``, its choice boxes lost up to the gap at some widths (KI-031).
    Group boxes are left out, as the domain page's picker test leaves them out: the check
    measures a group box's least height at its least width (ADR-0024's U1 amendment).
    """
    from tests.qt_helpers import open_window, settle
    from tests.test_translated_gui import _described

    window = open_window()
    window.show()
    window.select_domain("sheet_metal")
    settle(window)
    least = window.minimumSizeHint()
    found = []
    for extra in range(400):
        window.resize(least.width() + extra, least.height())
        settle(window)
        found += [f"+{extra} px: {_described(w, window)}" for w in _squeezed(window)]
    assert not found, "\n".join(found[:6])
    window.close()


def _short_labels(window: Any) -> list[Any]:
    """Every shown word-wrapped label given less height than its text needs at its width."""
    from PySide6.QtWidgets import QLabel

    return [
        label
        for label in window.settings_box.findChildren(QLabel)
        if label.isVisible()
        and label.wordWrap()
        and label.height() < label.heightForWidth(label.width())
    ]


def test_qt_gives_a_form_the_wrong_heights_at_exactly_its_preferred_width() -> None:
    """KI-032 as Qt has it: at its preferred width a form's wrapped labels fall short.

    One pixel either side, they're whole. If this fails, Qt lays the form out right at that
    width now: the sweep above can check labels' heights as well, and KI-032 can close.
    """
    from tests.qt_helpers import open_window, settle

    window = open_window()
    window.show()
    window.select_domain("sheet_metal")
    settle(window)
    form = window.settings_form
    height = window.minimumSizeHint().height()

    def at(width: int) -> int:
        window.resize(width, height)
        settle(window)
        return int(form.sizeHint().width() - form.geometry().width())

    width = window.width()
    for _ in range(8):  # the form widens as the window does, a pixel for a pixel
        short_by = at(width)
        if short_by == 0:
            break
        width += short_by
    assert at(width) == 0, "the window reaches the form's preferred width"
    assert _short_labels(window), "short at the preferred width"
    for beside in (width - 1, width + 1):
        at(beside)
        assert _short_labels(window) == [], beside
    window.close()
