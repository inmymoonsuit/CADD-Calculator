"""The window in a comma locale, and the language chosen at startup (ADR-0020 §§3–4)."""

from __future__ import annotations

from typing import Any

import pytest

from caddcalc.core import i18n
from caddcalc.core.formatting import NumberSymbols
from tests.qt_helpers import open_window, type_into

pytestmark = [pytest.mark.gui, pytest.mark.usefixtures("qt")]

COMMA = NumberSymbols(",")
BEND = "sheet_metal.bend_allowance"


def _clipboard() -> Any:
    from PySide6.QtGui import QGuiApplication

    return QGuiApplication.clipboard()


def _bend_window(symbols: NumberSymbols = COMMA) -> Any:
    """Bend allowance with the course method: BA = 0.3119 in."""
    window = open_window(symbols=symbols)
    window.select_calculator(BEND)
    window.method_box.setCurrentIndex(window.method_box.findData("course"))
    _clipboard().clear()
    return window


def test_results_show_the_locales_mark_and_copy_writes_a_point() -> None:
    """ADR-0020 L4: Copy and Ctrl+C write "." in every locale, for CAD."""
    window = _bend_window()
    field = window.results.fields["bend_allowance"]
    assert field.parts.number == "0,3119"
    field.copy_button.click()
    assert _clipboard().text() == "0.3119"
    assert window.statusBar().currentMessage() == "Copied BA = 0.3119 to the clipboard"
    window.close()


def test_the_menu_offers_the_number_as_shown_in_a_comma_locale() -> None:
    """Named by its effect, "Copy 0,3119"; the status bar quotes what was copied."""
    window = _bend_window()
    field = window.results.fields["bend_allowance"]
    menu = field.context_menu()
    [shown] = [a for a in menu.actions() if a.text() == "Copy 0,3119"]
    shown.trigger()
    assert _clipboard().text() == "0,3119"
    assert window.statusBar().currentMessage() == "Copied BA = 0,3119 to the clipboard"
    menu.deleteLater()
    window.close()
    point = _bend_window(NumberSymbols("."))
    names = [a.text() for a in point.results.fields["bend_allowance"].context_menu().actions()]
    assert names == ["Copy value", "Copy with unit", "Copy full precision"], "no second value"
    point.close()


def test_copy_all_writes_the_locales_mark_for_a_spreadsheet() -> None:
    window = _bend_window()
    window.results.copy_all_button.click()
    assert _clipboard().text().splitlines()[0] == "BA\tBend allowance\t0,3119\tin"
    window.close()


@pytest.mark.parametrize("typed", ["0,125", "0.125"])
def test_a_field_takes_the_locales_mark_and_a_point(typed: str) -> None:
    window = _bend_window()
    _param, edit = window.fields["thickness"]
    type_into(edit, typed)
    assert window.results.fields["bend_allowance"].parts.number == "0,3249"
    assert edit.text() == typed, "kept as typed"
    window.close()


def test_a_field_refuses_two_decimal_marks_with_a_clear_message() -> None:
    window = _bend_window()
    _param, edit = window.fields["thickness"]
    type_into(edit, "1.234,5")
    assert "more than one decimal mark" in edit.toolTip() + window.output.toPlainText()
    window.close()


def test_the_course_example_is_written_in_the_locales_mark() -> None:
    """Text the app writes into a field follows the locale (ADR-0020 §4)."""
    window = _bend_window()
    window.load_course_example()
    texts = [edit.text() for _p, edit in window.fields.values()]
    assert "0,1046" in texts and not any("." in text for text in texts), texts
    window.close()


def test_the_work_is_typeset_in_the_locales_mark() -> None:
    window = _bend_window()
    text = window.output.toPlainText()
    assert "(0,64·T + 1,57·R)·A/90" in text and "0,3119 in" in text, text
    window.close()


def test_the_regional_format_gives_the_decimal_mark() -> None:
    from PySide6.QtCore import QLocale

    from caddcalc.gui.regional import number_symbols, ui_languages

    assert number_symbols(QLocale("de_DE")).decimal == ","
    assert number_symbols(QLocale("en_US")).decimal == "."
    tags = ui_languages(QLocale("en_GB"))
    assert all("-" not in tag for tag in tags), "the underscore form"
    assert i18n.posix_language(tags[0]) == "en_GB", tags


def test_startup_chooses_the_language_for_our_text_and_qts() -> None:
    """Qt's standard buttons read the same languages our catalogs do (ADR-0020 §1)."""
    from PySide6.QtCore import QCoreApplication, QLocale

    from caddcalc.gui.regional import install_translations

    app = QCoreApplication.instance()
    translator = install_translations(app, QLocale("de_DE"))
    try:
        assert i18n.languages()[0] == "de_DE"
        if translator.isEmpty():
            pytest.skip("this Qt has no qtbase_de catalog")
        assert QCoreApplication.translate("QPlatformTheme", "Cancel") == "Abbrechen"
    finally:
        app.removeTranslator(translator)
        translator.deleteLater()
    assert QCoreApplication.translate("QPlatformTheme", "Cancel") == "Cancel"
