"""Entry point for the desktop app (``caddcalc-gui`` or ``caddcalc gui``)."""

from __future__ import annotations

import json
import sys
import time
import traceback
from collections.abc import Sequence
from pathlib import Path
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

    from caddcalc import __version__
    from caddcalc.gui.actions import AppActions
    from caddcalc.gui.branding import PRODUCT_NAME, active_branding
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
    # Before any widget: the user's text size, so every text-unit size follows it
    # (ADR-0021 §2). It's put back on the way out, as main() found it, however it ends.
    base_font = app.font()
    app.setFont(scaled_font(base_font, system_text_scale()))
    try:
        # The welcome screen shows first and paints, so startup is never blank; the main
        # window is built after it (ADR-0015 §1, amendments).
        actions = AppActions(branding, app)
        welcome = WelcomeScreen(branding, actions)
        startup = _Startup(app, branding, actions, welcome, smoke_test=smoke_test)
        welcome.show()
        app.processEvents()

        if smoke_test:
            startup.build_main_window()
            if startup.failed:
                status = 1
            else:
                ready = time.perf_counter() - started
                window = startup.main_window()
                _write_smoke_report(report_dir, app, window, branding, welcome, ready)
                status = 0
        else:
            QTimer.singleShot(0, startup.build_main_window)
            status = int(app.exec())
        _dispose(app, welcome, startup.window, actions)
    finally:
        app.setFont(base_font)
    return status


class _Startup:
    """Builds the main window once the welcome screen has painted (ADR-0015 §1).

    Until the main window shows, the welcome screen is the app's only window, so closing
    it early mustn't end the app. If building the main window fails, the app says so and
    ends with status 1, rather than running on with no window.
    """

    def __init__(
        self,
        app: QApplication,
        branding: Branding,
        actions: AppActions,
        welcome: WelcomeScreen,
        *,
        smoke_test: bool = False,
    ) -> None:
        self.app = app
        self.branding = branding
        self.actions = actions
        self.welcome = welcome
        self.smoke_test = smoke_test
        self.window: MainWindow | None = None
        self.failed = False
        """Whether building the main window failed."""
        app.setQuitOnLastWindowClosed(False)

    def build_main_window(self) -> None:
        """Build and show the main window behind the welcome screen."""
        from shiboken6 import isValid

        from caddcalc.gui.window import MainWindow

        try:
            self.window = MainWindow(branding=self.branding, actions=self.actions)
        # An isolation boundary: a packaged app has no console, so an error here would
        # otherwise leave a process with no window once the welcome screen closes.
        except Exception as exc:  # noqa: BLE001
            self._fail(exc)
            return
        # On the welcome card's screen, so the two stay together (ADR-0021 §3).
        self.window.fit_to_screen(self.welcome.screen() if isValid(self.welcome) else None)
        self.window.show()
        if isValid(self.welcome) and self.welcome.isVisible():
            self.welcome.raise_()
            self.welcome.activateWindow()
        self.app.setQuitOnLastWindowClosed(True)

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
        if self.window is None:
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
        "packaged": packaged_app_dir() is not None,
        "main_to_ready_s": round(ready_seconds, 3),
    }
    (report_dir / "smoke-test.json").write_text(json.dumps(report, indent=2), encoding="utf-8")


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
