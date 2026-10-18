"""The window in a comma locale, and the language chosen at startup (ADR-0020 §§3–4)."""

from __future__ import annotations

import sys
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


def test_in_a_comma_locale_each_copy_item_says_what_it_copies() -> None:
    """UI/UX's i4 L1: "Copy 0.3119" beside "Copy 0,3119", so the menu explains itself."""
    window = _bend_window()
    menu = window.results.fields["bend_allowance"].context_menu()
    names = []
    for action in menu.actions():
        action.trigger()
        assert action.text() == f"Copy {_clipboard().text()}"
        names.append(action.text())
    assert names[:3] == ["Copy 0.3119", "Copy 0,3119", "Copy 0.3119 in"], names
    menu.deleteLater()
    window.close()


def test_a_methods_note_writes_its_values_in_the_locales_mark() -> None:
    """UI/UX's i4 L2: the cone's note gives the course example's angles as values."""
    window = open_window(symbols=COMMA)
    window.select_calculator("sheet_metal.truncated_cone_layout")
    window.method_box.setCurrentIndex(window.method_box.findData("course"))
    text = window.output.toPlainText()
    assert "132,70° against 133,70°" in text, text
    window.close()


def test_a_range_errors_decimal_bound_is_written_in_the_locales_mark() -> None:
    """UI/UX's i4 review: a bound the app writes, in a field's message, takes the mark."""
    from caddcalc.core import Registry
    from caddcalc.core.spec import Param
    from caddcalc.core.units import Dimension, parse_quantity
    from tests.test_domains import ACME, _AcmeWidget

    class Bounded(_AcmeWidget):
        params = (
            Param(
                "length",
                "X",
                "Length",
                Dimension.LENGTH,
                default="1 in",
                minimum=parse_quantity("0.25 in", Dimension.LENGTH),
            ),
        )

    registry = Registry()
    registry.register_domain(ACME)
    registry.register(Bounded)
    window = open_window(registry, symbols=COMMA)
    window.select_calculator("acme.widget")
    _param, edit = window.fields["length"]
    type_into(edit, "0,1 in")
    message = edit.toolTip() + window.output.toPlainText()
    assert "0,25 in" in message and "0.25" not in message, message
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


def _undo_text() -> str:
    """The first item of a field's own context menu, as Qt words it."""
    from PySide6.QtWidgets import QLineEdit

    field = QLineEdit()
    menu = field.createStandardContextMenu()
    text = str(menu.actions()[0].text()).split("	", 1)[0]  # the label, not its shortcut
    menu.deleteLater()
    field.deleteLater()
    return text


def test_with_no_catalog_for_the_language_the_whole_window_stays_english() -> None:
    """UI/UX's i4 M1: Qt's own text follows ours, so a window never mixes languages."""
    from PySide6.QtCore import QCoreApplication, QLocale

    from caddcalc.gui.regional import install_translations

    app = QCoreApplication.instance()
    translator = install_translations(app, QLocale("de_DE"))
    try:
        assert i18n.languages()[0] == "de_DE" and i18n.text_language() == "en"
        assert translator.isEmpty(), "no Qt catalog either"
        assert _undo_text() == "&Undo"
        assert QCoreApplication.translate("QPlatformTheme", "Cancel") == "Cancel"
    finally:
        app.removeTranslator(translator)
        translator.deleteLater()


def test_with_our_catalog_for_the_language_qts_text_is_in_it_too(tmp_path: Any) -> None:
    """Our German catalog brings Qt's German, its shortcut names included (UI/UX's L3)."""
    from babel.messages.catalog import Catalog
    from babel.messages.mofile import write_mo
    from PySide6.QtCore import QCoreApplication, QLocale
    from PySide6.QtGui import QKeySequence

    from caddcalc.gui.regional import install_translations
    from caddcalc.gui.result_fields import COPY_ALL_KEYS

    german = Catalog(locale="de", domain="caddcalc")
    german.add("About", "Über", context="button")
    path = tmp_path / "de" / "LC_MESSAGES" / "caddcalc.mo"
    path.parent.mkdir(parents=True)
    with path.open("wb") as stream:
        write_mo(stream, german)
    app = QCoreApplication.instance()
    translator = install_translations(app, QLocale("de_DE"), directories=[tmp_path])
    try:
        assert i18n.text_language() == "de"
        if translator.isEmpty():
            pytest.skip("this Qt has no qtbase_de catalog")
        assert QCoreApplication.translate("QPlatformTheme", "Cancel") == "Abbrechen"
        assert _undo_text() != "&Undo"
        window = open_window()
        tip = window.results.copy_all_button.toolTip()
        native = COPY_ALL_KEYS.toString(QKeySequence.SequenceFormat.NativeText)
        assert native in tip
        # macOS writes the modifiers as symbols in every language, "⇧⌘C"; elsewhere
        # they're words, which Qt's German names.
        if sys.platform != "darwin":
            assert "Strg" in native, tip
        window.close()
    finally:
        app.removeTranslator(translator)
        translator.deleteLater()
    assert QCoreApplication.translate("QPlatformTheme", "Cancel") == "Cancel"
