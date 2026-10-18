"""The window and its page in text units: launch size, cap, list, least sizes (ADR-0021)."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any, override

import pytest

from caddcalc.gui.style_tokens import Rect, Size
from caddcalc.gui.ui_style import ui_style
from caddcalc.gui.window_layout import Margins, ch, chars, fit_window, launch_size
from tests.qt_helpers import open_window
from tests.test_result_fields import _settle

FRAME = Margins(8, 31, 8, 8)
"""A Windows frame at 100%, as UI/UX measured it: caption and border on top, 7–8 elsewhere."""
LEAST = Size(577, 175)
"""The window's least content size, as built, at 9 pt Segoe UI."""


@pytest.mark.parametrize(
    ("area", "preferred", "content"),
    [
        (Rect(0, 0, 1366, 720), Size(1100, 720), Size(1100, 649)),
        (Rect(0, 0, 1280, 672), Size(1100, 720), Size(1100, 601)),
        (Rect(0, 0, 1920, 1032), Size(1100, 720), Size(1100, 720)),
        (Rect(0, 0, 1366, 720), Size(1374, 900), Size(1318, 649)),
        (Rect(0, 0, 1920, 1032), Size(1374, 900), Size(1374, 900)),
        (Rect(1920, 0, 1536, 816), Size(1374, 900), Size(1374, 745)),
    ],
)
def test_the_launch_size_fits_each_work_area_centred(
    area: Rect, preferred: Size, content: Size
) -> None:
    """UI/UX's table: 1366 × 768, 1080p at 150%, and 1080p at 100%; text at 125% too."""
    margin = ui_style().layout.screen_margin
    placed = fit_window(preferred, LEAST, FRAME, area, margin)
    assert (placed.width, placed.height) == content
    left = placed.x - FRAME.left - area.x
    right = area.x + area.width - (placed.x + placed.width + FRAME.right)
    top = placed.y - FRAME.top - area.y
    bottom = area.y + area.height - (placed.y + placed.height + FRAME.bottom)
    assert min(left, right, top, bottom) >= 0, "the frame is inside the work area"
    assert abs(left - right) <= 1 and abs(top - bottom) <= 1, "centred"


def test_the_launch_height_covers_the_tallest_calculator_page() -> None:
    """``launch_lines`` is the floor; a taller calculator page raises it (KI-024)."""
    layout = ui_style().layout
    assert launch_size(layout, 5.5, 16, 5).height == 736
    assert launch_size(layout, 5.5, 16, 5, pages=726).height == 736, "Windows at 9 pt"
    assert launch_size(layout, 5.5, 14, 5, pages=672).height == 672, "14 px lines"


def test_the_launch_size_never_goes_below_the_least_window() -> None:
    tiny = Rect(0, 0, 400, 150)
    placed = fit_window(Size(1100, 720), LEAST, FRAME, tiny, 16)
    assert (placed.width, placed.height) == LEAST


def test_ch_falls_back_to_0_45_em() -> None:
    assert ch(5.5, 12) == 5.5
    assert ch(0, 12) == pytest.approx(5.4)
    assert chars(148, 5.5) == 814, "the page's cap at 9 pt Segoe UI"
    assert chars(51, 5.5) == 281


@pytest.fixture
def qt_window(qt: Any) -> Iterator[Any]:
    """The bend allowance page, at the window's launch size, laid out."""
    assert qt.QApplication.instance() is not None
    window = open_window()
    window.select_calculator("sheet_metal.bend_allowance")
    window.show()
    _settle(window)
    yield window
    window.close()


def _units(window: Any) -> tuple[float, int]:
    from caddcalc.gui.text_units import text_unit

    unit = text_unit(window.font())
    return unit, chars(ui_style().layout.page_max_chars, unit)


def test_the_window_opens_at_its_launch_size_in_text_units(qt_window: Any) -> None:
    from caddcalc.gui.text_units import line_spacing

    layout = ui_style().layout
    unit, cap = _units(qt_window)
    launch = qt_window.launch_size()
    handle = qt_window.splitter.handleWidth()
    expected = chars(layout.list_width_chars, unit) - 1 + handle + cap
    assert abs(launch.width - (layout.list_width_chars * unit + handle + cap)) <= 1
    assert launch.width >= expected
    floor = layout.launch_lines * line_spacing(qt_window.font())
    assert launch.height == max(floor, qt_window.launch_pages)
    assert (qt_window.width(), qt_window.height()) == (launch.width, launch.height)


def test_fitting_to_the_screen_keeps_the_window_inside_its_work_area(qt_window: Any) -> None:
    screen = qt_window.screen()
    qt_window.hide()
    qt_window.fit_to_screen(screen)
    area = screen.availableGeometry()
    frame = qt_window.frameGeometry()
    least = qt_window.minimumSizeHint()
    # Inside the work area on each axis the least window allows; offscreen fonts can make
    # it wider than the offscreen screen, and then it keeps its least width.
    if least.width() <= area.width():
        assert area.left() <= frame.left() and frame.right() <= area.right(), (area, frame)
    else:
        assert qt_window.width() == least.width()
    if least.height() <= area.height():
        assert area.top() <= frame.top() and frame.bottom() <= area.bottom(), (area, frame)
    centre = area.center() - frame.center()
    assert abs(centre.x()) <= 1 and abs(centre.y()) <= 1, "centred"
    assert not qt_window.isMaximized()


def test_the_page_is_capped_and_left_aligned_and_the_handle_moves_it(qt_window: Any) -> None:
    """The handle moves the page's left edge; the page shrinks only without room (§4.3)."""
    _unit, cap = _units(qt_window)
    handle = qt_window.splitter.handleWidth()
    listed = qt_window.tree.width()
    wide = listed + handle + cap + 400
    qt_window.resize(wide, qt_window.height())
    _settle(qt_window)
    page = qt_window.page_scroll
    assert page.width() == cap and page.x() == 0, "capped, left-aligned in its slot"
    qt_window.splitter.setSizes([listed + 200, wide])
    _settle(qt_window)
    assert qt_window.tree.width() == listed + 200 and page.width() == cap, "moved, not shrunk"
    qt_window.splitter.setSizes([listed + 600, wide])
    _settle(qt_window)
    assert page.width() < cap, "less room than the cap: the page shrinks"
    qt_window.resize(wide + 300, qt_window.height())
    _settle(qt_window)
    assert qt_window.tree.width() == listed + 600, "a window resize goes to the page"


def test_the_list_never_collapses(qt_window: Any) -> None:
    layout = ui_style().layout
    unit, _cap = _units(qt_window)
    splitter = qt_window.splitter
    assert not splitter.childrenCollapsible()
    splitter.setSizes([0, qt_window.width()])
    _settle(qt_window)
    assert qt_window.tree.width() == chars(layout.list_min_chars, unit)


def test_a_larger_base_font_scales_the_whole_layout(qt: Any) -> None:
    """Windows' text size at 125% makes everything larger in proportion (ADR-0021 §2).

    The text-unit sizes grow in proportion: the width, the page's cap, and the launch
    height's floor in lines. Where the tallest calculator page sets the height, it grows
    less, as the fields' heights are in pixels, but never shrinks.
    """
    from caddcalc.gui.text_units import line_spacing, scaled_font

    lines = ui_style().layout.launch_lines
    app = qt.QApplication.instance()
    base = app.font()
    window = open_window()
    normal = window.launch_size()
    normal_cap = window.page_scroll.maximumWidth()
    normal_floor = lines * line_spacing(window.font())
    window.close()
    app.setFont(scaled_font(base, 1.25))
    try:
        larger = open_window()
        grown = larger.launch_size()
        assert grown.width > normal.width * 1.15 and grown.height >= normal.height
        assert lines * line_spacing(larger.font()) > normal_floor * 1.15
        assert larger.page_scroll.maximumWidth() > normal_cap * 1.15
        larger.close()
    finally:
        app.setFont(base)


def _least(window: Any) -> None:
    window.resize(1, 1)
    _settle(window)


@pytest.mark.parametrize(
    "calc_id",
    [
        "sheet_metal.bend_allowance",
        "sheet_metal.segment_flat_length",
        "sheet_metal.truncated_cone_layout",
        "sheet_metal.v_die_opening",
    ],
)
@pytest.mark.usefixtures("qt")
def test_at_the_least_size_the_disclaimer_and_method_are_whole(calc_id: str) -> None:
    """Safety text is never cut off, nor is a method's name (ADR-0021 §7)."""
    from PySide6.QtWidgets import QStyle, QStyleOptionComboBox

    window = open_window()
    window.select_calculator(calc_id)
    window.show()
    _least(window)
    disclaimer = window.results.disclaimer
    assert disclaimer.wordWrap()
    assert disclaimer.height() >= disclaimer.heightForWidth(disclaimer.width())
    assert disclaimer.width() <= window.results.width()
    box = window.method_box
    for index in range(box.count()):
        box.setCurrentIndex(index)
        _settle(window)
        option = QStyleOptionComboBox()
        box.initStyleOption(option)
        room = box.style().subControlRect(
            QStyle.ComplexControl.CC_ComboBox, option, QStyle.SubControl.SC_ComboBoxEditField, box
        )
        name = box.currentText()
        assert box.fontMetrics().horizontalAdvance(name) <= room.width(), name
        assert "[" not in name, "the box shows the name; its status is beside it"
    window.close()


def test_the_method_status_shows_beside_the_box_and_in_the_open_list(qt_window: Any) -> None:
    from PySide6.QtWidgets import QStyleOptionViewItem

    method = qt_window.calculator.get_method(qt_window.method_key)
    assert qt_window.method_status.text() == method.status
    delegate = qt_window.method_box.itemDelegate()
    option = QStyleOptionViewItem()
    delegate.initStyleOption(option, qt_window.method_box.model().index(0, 0))
    assert option.text == f"{method.label}  [{method.status}]", "methods can be compared"
    reflow = qt_window.method_status.parentWidget()
    assert not reflow.stacked, "beside the box at the launch size"
    _least(qt_window)
    assert reflow.stacked == (reflow.width() < reflow.row_width())


@pytest.mark.usefixtures("qt")
def test_the_settings_page_reflows_rather_than_scroll_sideways() -> None:
    from PySide6.QtCore import QPoint, Qt
    from PySide6.QtWidgets import QComboBox, QWidget

    window = open_window()
    window.select_domain("sheet_metal")
    window.show()
    _least(window)
    page = window.domain_page
    assert page.horizontalScrollBarPolicy() is Qt.ScrollBarPolicy.ScrollBarAlwaysOff
    content = page.widget()
    assert content.width() <= page.viewport().width(), "nothing beyond the page's width"
    edge = window.width()
    for widget in content.findChildren(QWidget):
        if widget.isVisible() and isinstance(widget, QComboBox):
            right = widget.mapTo(window, QPoint(widget.width(), 0)).x()
            assert right <= edge, widget.currentText()
            assert widget.width() >= widget.minimumSizeHint().width()
    window.close()


@pytest.mark.usefixtures("qt")
def test_the_welcome_card_is_centred_on_its_screen() -> None:
    from caddcalc.gui.actions import AppActions
    from caddcalc.gui.branding import GENERIC
    from caddcalc.gui.welcome import WelcomeScreen

    welcome = WelcomeScreen(GENERIC, AppActions(GENERIC))
    welcome.show()
    area = welcome.screen().availableGeometry()
    offset = area.center() - welcome.frameGeometry().center()
    assert abs(offset.x()) <= 1 and abs(offset.y()) <= 1, (area, welcome.frameGeometry())
    welcome.close()


def test_windows_text_size_is_read_once_and_guarded(monkeypatch: pytest.MonkeyPatch) -> None:
    """125% gives 1.25; another platform, or a value missing, out of range, or no DWORD, 1."""
    import sys

    from caddcalc.gui import window_layout

    monkeypatch.setattr(sys, "platform", "linux")
    assert window_layout.system_text_scale() == 1.0
    winreg = pytest.importorskip("winreg")
    monkeypatch.setattr(sys, "platform", "win32")

    class Key:
        def __enter__(self) -> Key:
            return self

        def __exit__(self, *_args: object) -> None:
            return None

    for value, expected in (
        ((125, winreg.REG_DWORD), 1.25),
        ((300, winreg.REG_DWORD), 1.0),
        (("125", winreg.REG_SZ), 1.0),  # compared as a number, it would raise at startup
    ):
        monkeypatch.setattr(winreg, "OpenKey", lambda *_a: Key())
        monkeypatch.setattr(winreg, "QueryValueEx", lambda *_a, v=value: v)
        assert window_layout.system_text_scale() == expected

    def missing(*_args: object) -> None:
        raise FileNotFoundError

    monkeypatch.setattr(winreg, "OpenKey", missing)
    assert window_layout.system_text_scale() == 1.0


@pytest.mark.gui
def test_main_scales_the_text_and_fits_the_window_on_the_cards_screen(
    qt: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """At 125% text, main() builds the window in fonts 1.25 times the size.

    It fits the window to the welcome card's screen, and puts the font back on the way
    out, even when the way out fails.
    """
    from caddcalc.gui import app as app_module
    from caddcalc.gui import window_layout
    from caddcalc.gui.window import MainWindow

    app = qt.QApplication.instance()
    base_font = app.font()
    base = base_font.pointSizeF()
    monkeypatch.setattr(window_layout, "system_text_scale", lambda: 1.25)
    fitted: list[tuple[float, Any]] = []
    fit_to_screen = MainWindow.fit_to_screen

    def spy(window: MainWindow, screen: Any = None) -> None:
        fitted.append((window.font().pointSizeF(), screen))
        fit_to_screen(window, screen)

    monkeypatch.setattr(MainWindow, "fit_to_screen", spy)
    dispose = app_module._dispose

    def failing(*objects: Any) -> None:
        dispose(*objects)
        raise RuntimeError("teardown failed")

    try:
        assert app_module.main([f"--smoke-test={tmp_path / 'scaled'}"]) == 0
        [(size, screen)] = fitted
        assert size == pytest.approx(base * 1.25)
        assert screen is not None, "the welcome card's screen"
        assert app.font().pointSizeF() == base, "put back"
        monkeypatch.setattr(app_module, "_dispose", failing)
        with pytest.raises(RuntimeError, match="teardown failed"):
            app_module.main([f"--smoke-test={tmp_path / 'failing'}"])
        assert app.font().pointSizeF() == base, "put back, though the teardown failed"
    finally:
        app.setApplicationDisplayName("")
        app.setFont(base_font)


CALCULATORS = (
    "sheet_metal.bend_allowance",
    "sheet_metal.segment_flat_length",
    "sheet_metal.truncated_cone_layout",
    "sheet_metal.v_die_opening",
)


def _too_short(window: Any) -> list[str]:
    """Every shown part of the window's pages that's shorter than it needs at its width."""
    from PySide6.QtWidgets import (
        QAbstractButton,
        QComboBox,
        QGroupBox,
        QLabel,
        QLineEdit,
        QWidget,
    )

    from caddcalc.gui.reflow import Reflow
    from caddcalc.gui.result_fields import ResultField

    kinds = (QLabel, QAbstractButton, QComboBox, QLineEdit, QGroupBox, Reflow, ResultField)
    short = []
    for page in (window.page_scroll.widget(), window.domain_page.widget()):
        for widget in page.findChildren(QWidget):
            if not widget.isVisible() or not isinstance(widget, kinds):
                continue
            if widget.hasHeightForWidth():
                needed = widget.heightForWidth(widget.width())
            else:
                needed = widget.sizeHint().height()
            if widget.height() < needed:
                name = getattr(widget, "text", lambda: "")() or type(widget).__name__
                short.append(f"{name}: {widget.height()} < {needed}")
    return short


@pytest.mark.usefixtures("qt")
def test_every_part_of_every_page_is_as_tall_as_it_needs() -> None:
    """At the launch size and the least: UI/UX's H1 (0 px choice boxes) and M1."""
    window = open_window()
    window.show()
    pages = [("calculator", c) for c in CALCULATORS] + [("domain", "sheet_metal")]
    for size in ("launch", "least"):
        for kind, page_id in pages:
            if kind == "calculator":
                window.select_calculator(page_id)
            else:
                window.select_domain(page_id)
            launch = window.launch_size()
            window.resize(
                *(round(launch.width), round(launch.height)) if size == "launch" else (1, 1)
            )
            _settle(window)
            assert _too_short(window) == [], (size, page_id)
    window.close()


def test_the_method_row_grows_and_shrinks_with_its_status(qt_window: Any) -> None:
    """Narrow, the status goes under the box and the row grows; wide again, it shrinks."""
    row, reflow = qt_window.method_row, qt_window.method_status.parentWidget()
    launch = qt_window.launch_size()
    wide = qt_window.width()
    assert not reflow.stacked
    one_line = row.height()
    qt_window.resize(1, round(launch.height))
    _settle(qt_window)
    assert reflow.stacked, "the least window is narrower than the box and its status"
    assert row.height() > one_line
    box = qt_window.method_box
    assert box.height() >= box.sizeHint().height(), "the box isn't cut through its text"
    qt_window.resize(wide, round(launch.height))
    _settle(qt_window)
    assert not reflow.stacked and row.height() == one_line


@pytest.mark.usefixtures("qt")
def test_the_segment_page_fits_1100_by_720() -> None:
    """With the list at its 9 pt width, as the results tests have it (ADR-0021 §7)."""
    from tests.test_result_fields import _shown_at

    window = _shown_at(1100, 720, "sheet_metal.segment_flat_length")
    assert window.page_scroll.verticalScrollBar().maximum() == 0
    assert not window.output.full
    window.close()


DESIGN_LINE = 16
"""The line spacing the layout's heights were measured in: 9 pt Segoe UI (ADR-0021 §3)."""


@pytest.mark.usefixtures("qt")
def test_each_calculator_page_is_measured_at_its_shown_height(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Laid out hidden, each page measures what it needs once shown (``pages.lay_out``).

    The results panel's height follows its own width, which a hidden page doesn't have
    until it's laid out once; a single pass overstates the first page measured.
    """
    from caddcalc.gui import window as window_module

    fit_height = window_module.fit_height
    measured: list[int] = []

    def spy(page: Any, width: int, document: Any = None) -> int:
        height: int = fit_height(page, width, document)
        measured.append(height)
        return height

    monkeypatch.setattr(window_module, "fit_height", spy)
    window = open_window()
    monkeypatch.setattr(window_module, "fit_height", fit_height)
    ids = [calc.id for calc in window.registry]
    assert len(measured) == len(ids)
    window.show()
    for calc_id, height in zip(ids, measured, strict=True):
        window.select_calculator(calc_id)
        _settle(window)
        view = window.page_scroll.viewport()
        shown = fit_height(window.page_scroll.widget(), view.width(), window.output)
        assert shown == height, calc_id
    window.close()


@pytest.mark.usefixtures("qt")
def test_no_plugin_page_opens_until_it_is_chosen(monkeypatch: pytest.MonkeyPatch) -> None:
    """Building the window opens built-in pages only, and opens on a built-in one.

    A plugin's page runs the plugin's code, so a broken plugin fails only when chosen,
    though its family sorts first ("Acme Tools") and the launch size is measured
    (ADR-0019, ADR-0021 §3).
    """
    from caddcalc.calculators import default_registry
    from caddcalc.core import Context
    from caddcalc.gui.window import MainWindow, builtin_ids
    from tests.test_domains import ACME, _AcmeWidget

    class Failing(_AcmeWidget):
        id = "acme.failing"
        name = "Failing"

        @override
        def compute(self, ctx: Context) -> None:
            raise ZeroDivisionError("the plugin's own error")

    registry = default_registry(load_plugins=False)
    registry.register_domain(ACME)
    registry.register(Failing)
    opened: list[str] = []
    select_calculator = MainWindow.select_calculator

    def spy(window: MainWindow, calc_id: str) -> None:
        opened.append(calc_id)
        select_calculator(window, calc_id)

    monkeypatch.setattr(MainWindow, "select_calculator", spy)
    window = open_window(registry)
    assert opened and set(opened) <= builtin_ids(), opened
    assert window.calculator is not None and window.calculator.id in builtin_ids()
    with pytest.raises(ZeroDivisionError):
        window.select_calculator("acme.failing")  # only once it's chosen
    window.select_calculator("sheet_metal.bend_allowance")
    window.show()
    _settle(window)
    assert window.results.fields["bend_allowance"].value.text() not in ("", "—")
    window.close()


@pytest.mark.usefixtures("qt")
def test_a_page_that_fails_to_measure_leaves_the_window_working(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The measure's isolation boundary: a page whose code raises is left out of it."""
    from caddcalc.calculators.sheet_metal import VDieOpening
    from caddcalc.core import Context

    def failing(_self: Any, _ctx: Context) -> None:
        raise ZeroDivisionError("a calculator's own error")

    monkeypatch.setattr(VDieOpening, "compute", failing)
    with pytest.warns(UserWarning, match=r"leaves out .*\(sheet_metal\.v_die_opening\)"):
        window = open_window()
    window.select_calculator("sheet_metal.bend_allowance")
    window.show()
    _settle(window)
    assert window.results.fields["bend_allowance"].value.text() not in ("", "—")
    window.close()


@pytest.mark.parametrize("shorter", [False, True], ids=["platform-font", "shorter-lines"])
@pytest.mark.parametrize("calc_id", CALCULATORS)
def test_no_calculator_page_scrolls_at_the_launch_size(
    qt: Any, calc_id: str, shorter: bool
) -> None:
    """Every calculator page fits the launch size, whatever the font's lines (KI-024).

    The fields' heights are in pixels, so with lines shorter than the design's,
    ``launch_lines`` alone would give a window shorter than the pages need. The launch
    height covers the tallest calculator page instead.
    """
    from caddcalc.gui.text_units import line_spacing

    app = qt.QApplication.instance()
    base = app.font()
    if shorter:
        font = qt.QApplication.font()
        font.setPointSizeF(base.pointSizeF() * 0.75)
        app.setFont(font)
    try:
        window = open_window()
        if shorter:
            assert line_spacing(window.font()) < DESIGN_LINE
        window.select_calculator(calc_id)
        window.show()
        _settle(window)
        assert window.page_scroll.verticalScrollBar().maximum() == 0
        assert not window.output.full
        window.close()
    finally:
        app.setFont(base)
