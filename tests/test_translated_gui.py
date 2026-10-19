"""The GUI in another language: en_XA's longer, accented text, and what must fit (ADR-0020)."""

from __future__ import annotations

import math
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from caddcalc import __version__
from caddcalc.core import i18n
from tests import pseudo_locale
from tests.catalogs import shipped
from tests.pseudo_locale import LANGUAGE, pseudo
from tests.qt_helpers import open_window, settle, show_in

pytestmark = [pytest.mark.gui, pytest.mark.usefixtures("qt")]


def _in(language: str, folder: Path) -> None:
    """Choose ``language``: en_XA, made into ``folder``, or the source for ``""``."""
    i18n.use([language] if language else [], directories=[pseudo_locale.write(folder)])


def _rows(window: Any) -> Iterator[Any]:
    """Every row of the calculator list: each domain, then its calculators."""
    tree = window.tree
    for i in range(tree.topLevelItemCount()):
        domain = tree.topLevelItem(i)
        yield domain
        yield from (domain.child(j) for j in range(domain.childCount()))


def test_a_calculator_imported_before_the_language_is_chosen_shows_it(tmp_path: Path) -> None:
    """Text is translated where it's shown, never where it's declared (ADR-0020 §1)."""
    import caddcalc.calculators.sheet_metal  # noqa: F401 (declared, so marked, first)
    from caddcalc.gui.window import DOMAIN_ROLE, ID_ROLE

    assert i18n.languages() == (), "no language yet"
    _in(LANGUAGE, tmp_path)
    window = open_window()
    registry = window.registry
    for row in _rows(window):
        if calc_id := row.data(0, ID_ROLE):
            calc = registry.get(calc_id)
            assert (row.text(0), row.toolTip(0)) == (pseudo(calc.name), pseudo(calc.summary))
        elif domain_id := row.data(0, DOMAIN_ROLE):
            domain = registry.domain(domain_id)
            assert (row.text(0), row.toolTip(0)) == (pseudo(domain.name), pseudo(domain.summary))
    calc = next(iter(registry))
    window.select_calculator(calc.id)
    assert window.title.text() == pseudo(calc.name)
    assert window.summary.text() == pseudo(calc.summary)
    window.close()


@pytest.mark.parametrize(
    ("language", "spoken"),
    [
        ("", "millimeters"),
        ("en_GB", "millimetres"),
        (LANGUAGE, pseudo("millimeters")),
    ],
)
def test_a_result_says_its_unit_in_the_language_text_is_shown_in(
    tmp_path: Path, language: str, spoken: str
) -> None:
    """A screen reader hears the unit's name in the user's spelling (ADR-0019 U5)."""
    folder = pseudo_locale.write(shipped(tmp_path, "en_001"))
    i18n.use([language] if language else [], directories=[folder])
    window = open_window()
    window.select_calculator("sheet_metal.bend_allowance")
    window.method_box.setCurrentIndex(window.method_box.findData("course"))
    show_in(window, "mm")
    field = window.results.fields["bend_allowance"]
    # The pseudo-locale marks the measure's template too: "⟦7.9213 ⟦millimeters⟧ …⟧".
    assert f" {spoken}" in field.accessibleName(), field.accessibleName()
    window.close()


def _tooltip(tree: Any, item: Any) -> str:
    """The tooltip the list shows when the pointer rests on ``item``."""
    from PySide6.QtCore import QEvent
    from PySide6.QtGui import QHelpEvent
    from PySide6.QtWidgets import QApplication, QToolTip

    at = tree.visualItemRect(item).center()
    assert tree.itemAt(at) is item, "the pointer rests on the row itself"
    viewport = tree.viewport()
    QApplication.sendEvent(viewport, QHelpEvent(QEvent.Type.ToolTip, at, viewport.mapToGlobal(at)))
    text = QToolTip.text() if QToolTip.isVisible() else ""
    QToolTip.hideText()
    return str(text)


@pytest.mark.parametrize("language", ["", LANGUAGE])
def test_a_list_name_too_long_for_its_row_shows_whole_in_its_tooltip(
    tmp_path: Path, language: str
) -> None:
    """A row's tooltip is its summary; once its name elides, the name comes first."""
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication

    from caddcalc.gui.name_tips import tip_text

    _in(language, tmp_path)
    # A native platform animates a tooltip in, so it isn't visible yet when it's asked
    # for; without the animation it shows at once, as offscreen.
    animated = QApplication.isEffectEnabled(Qt.UIEffect.UI_AnimateTooltip)
    QApplication.setEffectEnabled(Qt.UIEffect.UI_AnimateTooltip, False)
    window = open_window()
    # Below the list's least width and size hint, and its column's least width, so every
    # name elides, a short one such as "Area" too.
    window.tree.setMinimumWidth(1)
    window.tree.header().setMinimumSectionSize(1)
    window.resize(2400, 800)
    window.show()
    splitter = window.centralWidget()
    try:
        for row in _rows(window):
            name, summary = row.text(0), row.toolTip(0)
            splitter.setSizes([1200, 1200])
            settle(window)
            # A family's rows are indented; 24 px past the indent leaves room for a few
            # letters, whatever the platform's indentation and font.
            indent = window.tree.visualItemRect(row).left()
            splitter.setSizes([indent + 24, 2400 - indent - 24])
            settle(window)
            # The stretched column keeps its width when the list narrows, so it's narrowed too.
            window.tree.header().resizeSection(0, window.tree.viewport().width())
            settle(window)
            assert _tooltip(window.tree, row) == tip_text(name, summary), name
            splitter.setSizes([1200, 1200])
            settle(window)
            assert _tooltip(window.tree, row) == summary, name
    finally:
        window.close()
        QApplication.setEffectEnabled(Qt.UIEffect.UI_AnimateTooltip, animated)


def _clipped(window: Any) -> list[Any]:
    """Every visible text widget smaller than it needs, or past the window's right edge."""
    from PySide6.QtCore import QPoint
    from PySide6.QtWidgets import (
        QAbstractButton,
        QComboBox,
        QGroupBox,
        QLabel,
        QStyle,
        QStyleOptionComboBox,
        QWidget,
    )

    found = []
    for widget in window.findChildren(QWidget):
        if not widget.isVisible() or not isinstance(
            widget, QLabel | QAbstractButton | QComboBox | QGroupBox
        ):
            continue
        least = widget.minimumSizeHint()
        short = least.isValid() and (
            widget.width() < least.width() or widget.height() < least.height()
        )
        if isinstance(widget, QLabel) and widget.wordWrap() and widget.hasHeightForWidth():
            short = short or widget.height() < widget.heightForWidth(widget.width())
        if isinstance(widget, QComboBox):
            option = QStyleOptionComboBox()
            widget.initStyleOption(option)
            field = widget.style().subControlRect(
                QStyle.ComplexControl.CC_ComboBox,
                option,
                QStyle.SubControl.SC_ComboBoxEditField,
                widget,
            )
            short = short or widget.fontMetrics().horizontalAdvance(option.currentText) > (
                field.width()
            )
        right = widget.mapTo(window, QPoint(widget.width(), 0)).x()
        if short or right > window.width():
            found.append(widget)
    return found


def _described(widget: Any, window: Any) -> str:
    """A clipped widget, named, with its size, its least size, and where it ends."""
    from PySide6.QtCore import QPoint

    least = widget.minimumSizeHint()
    right = widget.mapTo(window, QPoint(widget.width(), 0)).x()
    text_width = getattr(widget, "text_width", None)
    return (
        f"{type(widget).__name__} {widget.accessibleName() or widget.objectName()!r}: "
        f"{widget.width()}x{widget.height()}, least {least.width()}x{least.height()}, "
        f"ends at x={right} of the window's {window.width()}; "
        f"{widget.style().name()} style, {widget.font().pointSizeF()} pt"
        + ("" if text_width is None else f", text width {text_width}")
    )


@pytest.mark.parametrize("language", ["", LANGUAGE])
def test_nothing_clips_at_the_least_window_size(tmp_path: Path, language: str) -> None:
    """Every page, at the window's least size, in English and in en_XA's longer text.

    The page scrolls rather than squeezes, so this is about width, and about any label
    given less height than its wrapped text needs. The calculator list elides a long
    name instead, and gives it whole in its tooltip (the test above).
    """
    _in(language, tmp_path)
    window = open_window()
    window.show()
    found = []
    for row in _rows(window):
        if not row.flags():
            continue  # a placeholder row
        window.tree.setCurrentItem(row)
        # The page's least width reaches the window only once its layout has run; read
        # at once, the hint is the last page's.
        settle(window)
        window.resize(window.minimumSizeHint())
        settle(window)
        clipped = _clipped(window)
        found += [f"{row.text(0)}: {_described(w, window)}" for w in clipped]
        if clipped:
            # Whether the layout only held a size it wasn't told had changed.
            for widget in clipped:
                widget.updateGeometry()
            settle(window)
            told = len(_clipped(window))
            found.append(f"{row.text(0)}: {told} still clipped once told to update")
    assert not found, "\n".join(found)
    window.close()


@pytest.mark.parametrize("language", ["", LANGUAGE])
def test_the_welcome_cards_version_stays_inside_its_safe_area(
    tmp_path: Path, language: str
) -> None:
    """The art keeps that corner clear of detail; a longer translation must still fit it."""
    from caddcalc.gui.actions import AppActions
    from caddcalc.gui.branding import GENERIC
    from caddcalc.gui.welcome import WelcomeScreen
    from caddcalc.gui.welcome_layout import scaled
    from caddcalc.gui.welcome_style import style

    _in(language, tmp_path)
    welcome = WelcomeScreen(GENERIC, AppActions(GENERIC))
    welcome.show()  # placed once it has its size
    pane = welcome.art.version_pane
    shown = pseudo("Version {version}") if language else "Version {version}"
    assert pane.text == shown.format(version=__version__)
    tokens = style()
    area = scaled(
        tokens.safe_area(tokens.version_pane), welcome.art.width() / tokens.art.slot.width
    )
    box = pane.geometry()
    assert box.x() >= math.floor(area.x) and box.y() >= math.floor(area.y), (box, area)
    assert box.x() + box.width() <= math.ceil(area.x + area.width), (box, area)
    assert box.y() + box.height() <= math.ceil(area.y + area.height), (box, area)
    welcome.close()


def test_the_disclaimer_is_translated_everywhere_it_is_shown(tmp_path: Path) -> None:
    """Under the results, in About, and after the command line's results (ADR-0020)."""
    import html

    from caddcalc.calculators import default_registry
    from caddcalc.cli import format_result
    from caddcalc.core.formatting import DISCLAIMER, DisplayPrefs, ShownUnits
    from caddcalc.gui.actions import about_html
    from caddcalc.gui.branding import Branding

    _in(LANGUAGE, tmp_path)
    translated = pseudo(DISCLAIMER)
    assert translated != DISCLAIMER
    window = open_window()
    assert window.results.disclaimer.text() == translated
    window.close()
    assert html.escape(translated) in about_html(Branding())
    calc = default_registry(load_plugins=False).get("sheet_metal.bend_allowance")
    assert format_result(calc, calc.run(), ShownUnits.generated(), DisplayPrefs()).endswith(
        f". {translated}"
    )
