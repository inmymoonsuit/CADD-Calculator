"""The user's language and regional format, read once at startup (ADR-0020 §§3–4).

Words follow the system's display languages, and numbers its regional format, which are
separate settings: "English words, German number format" is a normal setup. A change to
either applies at the next start.
"""

from __future__ import annotations

from PySide6.QtCore import QCoreApplication, QLibraryInfo, QLocale, QTranslator

from caddcalc.core import i18n
from caddcalc.core.errors import UsageError
from caddcalc.core.formatting import POINT, NumberSymbols


def number_symbols(locale: QLocale | None = None) -> NumberSymbols:
    """Return how the regional format writes numbers: its decimal mark.

    Args:
        locale: The locale to read; the system's, with the user's own changes to its
            regional format, when ``None``.
    """
    mark = (QLocale.system() if locale is None else locale).decimalPoint()
    try:
        return NumberSymbols(mark)
    except UsageError:
        return POINT  # a mark of more than one character, which input can't take


def ui_languages(locale: QLocale | None = None) -> list[str]:
    """Return the display languages, most wanted first, as gettext names catalogs."""
    chosen = QLocale.system() if locale is None else locale
    return chosen.uiLanguages(QLocale.TagSeparator.Underscore)


def install_translations(app: QCoreApplication, locale: QLocale | None = None) -> QTranslator:
    """Choose the app's language, and give Qt's own text the same one.

    Our text comes from our catalogs (``core.i18n``), and Qt's own, such as a dialog's
    standard buttons, from Qt's ``qtbase`` catalogs. Both read the same list of display
    languages, so they agree. Call it before any widget is made.

    Returns:
        Qt's translator, installed if Qt has a catalog for the language; ``app`` owns it.
    """
    chosen = QLocale.system() if locale is None else locale
    i18n.use(ui_languages(chosen))
    translator = QTranslator(app)
    folder = QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)
    if translator.load(chosen, "qtbase", "_", folder):
        app.installTranslator(translator)
    return translator
