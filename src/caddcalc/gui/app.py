"""Entry point for the desktop app (``caddcalc-gui`` or ``caddcalc gui``)."""

from __future__ import annotations

import json
import sys
import time
import traceback
from collections.abc import Callable, Sequence
from pathlib import Path
from types import TracebackType
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PySide6.QtWidgets import QApplication

    from caddcalc.gui.actions import AppActions
    from caddcalc.gui.branding import Branding
    from caddcalc.gui.welcome import WelcomeScreen
    from caddcalc.gui.window import MainWindow

SMOKE_TEST_FLAG = "--smoke-test"
"""``--smoke-test[=DIR]``: start, show the welcome screen and the window, then quit with 0.

Packaged builds are checked with it (``packaging/build.py --smoke-test``). With a DIR it
also writes ``smoke-test.json`` and a ``window.png`` screenshot there.
"""


def main(argv: Sequence[str] | None = None) -> int:
    """Start the desktop app and return its exit status.

    Args:
        argv: Command-line arguments without the program name; ``None`` reads
            ``sys.argv``, as the ``caddcalc-gui`` entry point calls it.
            ``--smoke-test[=DIR]`` is handled here (see ``SMOKE_TEST_FLAG``); the rest go
            to Qt.
    """
    started = time.perf_counter()
    try:
        from PySide6.QtGui import QIcon
        from PySide6.QtWidgets import QApplication
    except ImportError:
        print(
            "The desktop app needs PySide6. Install it with:\n"
            "  uv sync --extra gui        (from a source checkout)\n"
            "  pip install 'cadd-calculator[gui]'",
            file=sys.stderr,
        )
        return 1

    from PySide6.QtCore import QTimer
    from shiboken6 import isValid

    from caddcalc import __version__
    from caddcalc.gui.actions import AppActions
    from caddcalc.gui.branding import PRODUCT_NAME, active_branding
    from caddcalc.gui.regional import install_translations
    from caddcalc.gui.text_units import scaled_font
    from caddcalc.gui.welcome import WelcomeScreen
    from caddcalc.gui.window_layout import system_text_scale

    args, smoke_test, report_dir = _split_smoke_test(list(sys.argv[1:] if argv is None else argv))
    branding = active_branding()

    app = QApplication.instance() or QApplication([sys.argv[0], *args])
    if not isinstance(app, QApplication):
        raise TypeError("a non-widget Qt application already exists; the GUI needs QApplication")
    # One name in every edition (ADR-0016, S4), so they share their settings, too.
    app.setApplicationName(PRODUCT_NAME)
    app.setApplicationDisplayName(PRODUCT_NAME)
    app.setApplicationVersion(__version__)
    app.setOrganizationName("CADD Calculator")
    if branding.icon is not None:
        app.setWindowIcon(QIcon(str(branding.icon)))
    # Before any widget: our words and Qt's, in the user's language (ADR-0020 §3).
    translator = install_translations(app)
    # And the user's text size, so every text-unit size follows it (ADR-0021 §2). It's
    # put back on the way out, as main() found it, however it ends.
    base_font = app.font()
    app.setFont(scaled_font(base_font, system_text_scale()))
    # An error nothing caught is shown, not lost; a smoke test just writes it out.
    restore_hook = None if smoke_test else install_error_hook(app)
    try:
        # The welcome screen shows first and paints, so startup is never blank; the main
        # window is built after it (ADR-0015 §1, amendments).
        actions = AppActions(branding, app)
        welcome = WelcomeScreen(branding, actions)
        startup = _Startup(app, branding, actions, welcome, smoke_test=smoke_test)
        if startup.failed:  # not even the main window's shell; it has said so
            status = 1
        elif smoke_test:
            welcome.show()
            app.processEvents()
            startup.build_main_window()
            if startup.failed:
                status = 1
            else:
                ready = time.perf_counter() - started
                window = startup.main_window()
                _write_smoke_report(report_dir, app, window, branding, welcome, ready)
                status = 0
        else:
            welcome.show()
            app.processEvents()
            QTimer.singleShot(0, startup.build_main_window)
            status = int(app.exec())
        _dispose(app, welcome, startup.window, actions, translator)
    finally:
        if restore_hook is not None:
            restore_hook()
        app.setFont(base_font)
        if isValid(translator):  # _dispose deletes it, which takes it off the app too
            app.removeTranslator(translator)  # as main() found the app, however it ends
    return status


def install_error_hook(
    app: QApplication, show: Callable[[str, str], None] | None = None
) -> Callable[[], None]:
    """Show an error nothing caught, rather than lose it; return what undoes the hook.

    An error raised in a Qt slot goes to ``sys.excepthook``, past every isolation
    boundary, and the default hook writes it only to stderr, which a packaged app hasn't
    got. This one still writes it there, and then shows it, with its traceback in the
    details, while the application runs: not once it's about to quit or closing down,
    when its windows are going (KI-019), and never a second box while one shows.

    Args:
        app: The application.
        show: Shows a message and its details; a message box when ``None``.
    """
    previous = sys.excepthook
    showing = quitting = False

    def on_quit() -> None:
        nonlocal quitting
        quitting = True

    def hook(kind: type[BaseException], error: BaseException, tb: TracebackType | None) -> None:
        nonlocal showing
        previous(kind, error, tb)
        if showing or quitting or app.closingDown() or not issubclass(kind, Exception):
            return
        showing = True
        try:
            details = "".join(traceback.format_exception(kind, error, tb))
            (show or _error_box)(f"{kind.__name__}: {error}", details)
        finally:
            showing = False

    sys.excepthook = hook
    app.aboutToQuit.connect(on_quit)

    def restore() -> None:
        sys.excepthook = previous
        app.aboutToQuit.disconnect(on_quit)

    return restore


def _error_box(message: str, details: str) -> None:
    """Show an unexpected error in a message box, over the active window."""
    from PySide6.QtWidgets import QApplication, QMessageBox

    from caddcalc.gui.branding import PRODUCT_NAME

    box = QMessageBox(QApplication.activeWindow())
    box.setIcon(QMessageBox.Icon.Critical)
    box.setWindowTitle(PRODUCT_NAME)
    box.setText(f"Something went wrong: {message}")
    box.setInformativeText(
        "What you last did may not have finished. The details can be copied into a report."
    )
    box.setDetailedText(details)
    box.exec()


class _Startup:
    """Prepares the main window behind the welcome screen, and reveals it once.

    Every window shows once, final, in a stable order (ADR-0015 §1, amendments):

    1. The main window's shell is made, hidden, and the card given to it as a window it
       owns, before the card shows: Qt gives a window its owner only as it shows.
    2. The welcome card shows first, at its final place and size, and stays.
    3. The main window is built into its shell, fitted to the card's screen, hidden.
    4. It's revealed once it's ready and the card has been on screen alone for
       ``hold_ms`` from its first paint, or as soon as it's ready once the card is
       closed. It's revealed behind the card, which it owns, so the system keeps the
       card above it, and it doesn't take focus: the card keeps it until it closes, and
       then the main window takes it.

    Until the main window shows, the welcome screen is the app's only window, so closing
    it early mustn't end the app. If building the main window fails, the app says so and
    ends with status 1, rather than running on with no window.

    Attributes:
        hold_ms: How long the card is alone before the reveal; 0 reveals as soon as the
            main window is ready, as a smoke test does, which has no event loop to wait in.
    """

    def __init__(
        self,
        app: QApplication,
        branding: Branding,
        actions: AppActions,
        welcome: WelcomeScreen,
        *,
        smoke_test: bool = False,
        hold_ms: int | None = None,
    ) -> None:
        self.app = app
        self.branding = branding
        self.actions = actions
        self.welcome = welcome
        self.smoke_test = smoke_test
        self.window: MainWindow | None = None
        """The main window: its shell from the start, built once the card has painted."""
        self.failed = False
        """Whether building the main window failed."""
        self.revealed = False
        """Whether the main window has been shown."""
        hold = branding.welcome_tokens.startup.hold_ms if hold_ms is None else hold_ms
        self.hold_ms = 0 if smoke_test else hold
        self._held = self.hold_ms <= 0
        self._card_open = True
        self.ready = False
        """Whether the main window is built and fitted, ready to be revealed."""
        app.setQuitOnLastWindowClosed(False)
        welcome.painted.connect(self._on_card_painted)
        welcome.closed.connect(self._on_card_closed)
        # The same isolation boundary as the build's: the shell is the main window too.
        try:
            self._own_the_card()
        except Exception as exc:  # noqa: BLE001
            self._fail(exc)

    def _own_the_card(self) -> None:
        """Make the main window's shell, and the card a window it owns, before the card shows.

        Qt gives a window its owner only as it shows, so this comes first; the shell is a
        bare window, with no calculator loaded yet, and what it costs the card's first
        paint is in ADR-0015's amendments. The system then keeps the card above the main
        window, with no raise.
        """
        from PySide6.QtCore import Qt

        from caddcalc.gui.window import MainWindow

        window = MainWindow(branding=self.branding, actions=self.actions, build=False)
        self.window = window
        # It mustn't take the card's focus when it shows. Qt reads this as it makes the
        # native window, here, and again after the show, so it stays set until the card
        # closes.
        window.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        # On the card's screen: made unplaced, Windows puts a window on the pointer's
        # screen, and an owner on a screen of another scale rescales the card it owns.
        screen = self.welcome.screen()
        if screen is not None:
            window.setScreen(screen)
            window.move(screen.availableGeometry().topLeft())
        window.winId()  # the native window, which the card's owner must be
        self.welcome.winId()
        card = self.welcome.windowHandle()
        if card is not None:
            card.setTransientParent(window.windowHandle())

    def build_main_window(self) -> None:
        """Build the main window into its shell, hidden, fitted to the card's screen."""
        from shiboken6 import isValid

        window = self.window
        if self.failed or window is None:
            return
        try:
            window.build()
        # An isolation boundary: a packaged app has no console, so an error here would
        # otherwise leave a process with no window once the welcome screen closes.
        except Exception as exc:  # noqa: BLE001
            self._fail(exc)
            return
        # On the welcome card's screen, so the two stay together (ADR-0021 §3).
        window.fit_to_screen(self.welcome.screen() if isValid(self.welcome) else None)
        self.ready = True
        self._reveal_when_due()

    def _on_card_painted(self) -> None:
        from PySide6.QtCore import QTimer

        # Tied to the card: a card deleted first takes its pending hold with it.
        QTimer.singleShot(self.hold_ms, self.welcome, self._on_hold_passed)

    def _on_hold_passed(self) -> None:
        self._held = True
        self._reveal_when_due()

    def _on_card_closed(self) -> None:
        self._card_open = False
        if self.revealed:
            self._take_focus()
        self._reveal_when_due()

    def _take_focus(self) -> None:
        """Give the main window the focus the card had, and let it take focus from now on."""
        from PySide6.QtCore import Qt

        if self.window is not None:
            self.window.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, False)
            self.window.activateWindow()

    def _reveal_when_due(self) -> None:
        """Reveal the main window once it's ready, and the hold is over or the card closed."""
        from shiboken6 import isValid

        if not self.ready or self.revealed or not (self._held or not self._card_open):
            return
        window = self.window
        if window is None or not isValid(window):  # deleted already, as on the way out
            return
        window.show()  # below the card it owns, and without taking the card's focus
        self.revealed = True
        self.app.setQuitOnLastWindowClosed(True)
        if not self._card_open:
            self._take_focus()

    def _fail(self, exc: Exception) -> None:
        """Report a failed startup, and end the app with status 1."""
        from shiboken6 import isValid

        from caddcalc.gui.branding import PRODUCT_NAME

        self.failed = True
        traceback.print_exception(exc, file=sys.stderr)
        self.app.setQuitOnLastWindowClosed(True)
        message = f"{PRODUCT_NAME} couldn't start: building its main window failed."
        if self.smoke_test:
            print(f"{message}\n{exc}", file=sys.stderr)
        else:
            from PySide6.QtWidgets import QMessageBox

            parent = self.welcome if isValid(self.welcome) else None
            QMessageBox.critical(parent, PRODUCT_NAME, f"{message}\n\n{exc}")
            self.app.exit(1)

    def main_window(self) -> MainWindow:
        """Return the main window, once built."""
        if not self.ready or self.window is None:
            raise RuntimeError("the main window hasn't been built yet")
        return self.window


def _dispose(app: QApplication, *objects: object) -> None:
    """Close and delete the app's windows and commands while the application still runs.

    Left to interpreter exit, they would be torn down after or during Qt's own teardown,
    in no set order (KI-019). A window the user closed is already deleted.
    """
    from PySide6.QtCore import QEvent, QObject
    from PySide6.QtWidgets import QWidget
    from shiboken6 import isValid

    for item in objects:
        if isinstance(item, QObject) and isValid(item):
            if isinstance(item, QWidget):
                item.close()
            item.deleteLater()
    app.sendPostedEvents(None, QEvent.Type.DeferredDelete)


def _split_smoke_test(args: list[str]) -> tuple[list[str], bool, Path | None]:
    """Remove ``--smoke-test[=DIR]`` from ``args``. Qt gets the rest."""
    rest: list[str] = []
    smoke_test = False
    report_dir: Path | None = None
    for arg in args:
        flag, sep, value = arg.partition("=")
        if flag == SMOKE_TEST_FLAG:
            smoke_test = True
            report_dir = Path(value) if sep and value else None
        else:
            rest.append(arg)
    return rest, smoke_test, report_dir


def _write_smoke_report(
    report_dir: Path | None,
    app: QApplication,
    window: MainWindow,
    branding: Branding,
    welcome: WelcomeScreen,
    ready_seconds: float,
) -> None:
    from caddcalc import __version__
    from caddcalc.core import i18n
    from caddcalc.gui.branding import PRODUCT_NAME, packaged_app_dir

    app.processEvents()
    if report_dir is None:
        return
    report_dir.mkdir(parents=True, exist_ok=True)
    window.grab().save(str(report_dir / "window.png"))
    report = {
        "name": PRODUCT_NAME,
        "edition": branding.edition,
        "version": __version__,
        "window_title": window.windowTitle(),
        "icon_loaded": not app.windowIcon().isNull(),
        "welcome_shown": welcome.isVisible(),
        "welcome_art": welcome.art_source,
        "welcome_logo": welcome.logo_source,
        "display_font": welcome.display_face,
        "about_custom": branding.about_html is not None,
        "calculators": len(window.registry),
        "reference_tables": _load_reference_tables(),
        "catalogs": list(i18n.shipped_languages()),
        "qt_catalog": _loads_qt_catalog(),
        "packaged": packaged_app_dir() is not None,
        "main_to_ready_s": round(ready_seconds, 3),
    }
    (report_dir / "smoke-test.json").write_text(json.dumps(report, indent=2), encoding="utf-8")


def _loads_qt_catalog() -> bool:
    """Return whether Qt finds its own catalogs where this app keeps them.

    German stands for them all: Qt ships it, and the window would load a language's
    Qt catalog the same way, once we have a catalog of our own for it (ADR-0020 §1).
    """
    from PySide6.QtCore import QLibraryInfo, QLocale, QTranslator

    folder = QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)
    return bool(QTranslator().load(QLocale("de"), "qtbase", "_", folder))


def _load_reference_tables() -> int:
    """Load every shipped reference table and build its values; return how many loaded.

    A table missing from a packaged build, or one that fails its checks, raises here, so
    the smoke test fails instead of the first user who picks a gauge (ADR-0014).
    """
    from caddcalc.calculators import REFERENCE_TABLES

    for spec in REFERENCE_TABLES:
        list(spec.values(spec.load()))
    return len(REFERENCE_TABLES)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
