"""Entry point for the desktop app (``caddcalc-gui`` or ``caddcalc gui``)."""

from __future__ import annotations

import json
import sys
import time
from collections.abc import Sequence
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PySide6.QtWidgets import QApplication, QSplashScreen

    from caddcalc.gui.branding import Branding
    from caddcalc.gui.window import MainWindow

SMOKE_TEST_FLAG = "--smoke-test"
"""``--smoke-test[=DIR]``: start, show the window, then quit with status 0.

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
        from PySide6.QtGui import QIcon, QPixmap
        from PySide6.QtWidgets import QApplication, QSplashScreen
    except ImportError:
        print(
            "The desktop app needs PySide6. Install it with:\n"
            "  uv sync --extra gui        (from a source checkout)\n"
            "  pip install 'cadd-calculator[gui]'",
            file=sys.stderr,
        )
        return 1

    from caddcalc import __version__
    from caddcalc.gui.branding import active_branding
    from caddcalc.gui.window import MainWindow

    args, smoke_test, report_dir = _split_smoke_test(list(sys.argv[1:] if argv is None else argv))
    branding = active_branding()

    app = QApplication.instance() or QApplication([sys.argv[0], *args])
    if not isinstance(app, QApplication):
        raise TypeError("a non-widget Qt application already exists; the GUI needs QApplication")
    # The application name stays fixed so settings are shared by every edition;
    # the display name is what the user sees in window titles.
    app.setApplicationName("CADD Calculator")
    app.setApplicationDisplayName(branding.name)
    app.setApplicationVersion(__version__)
    app.setOrganizationName("CADD Calculator")
    if branding.icon is not None:
        app.setWindowIcon(QIcon(str(branding.icon)))

    splash = None
    if branding.splash is not None:
        pixmap = QPixmap(str(branding.splash))
        if not pixmap.isNull():
            splash = QSplashScreen(pixmap)
            splash.show()
            app.processEvents()

    window = MainWindow(branding=branding)
    window.show()
    if splash is not None:
        splash.finish(window)

    if smoke_test:
        ready = time.perf_counter() - started
        _write_smoke_report(report_dir, app, window, branding, splash, ready)
        status = 0
    else:
        status = int(app.exec())
    _dispose(app, window)
    return status


def _dispose(app: QApplication, window: MainWindow) -> None:
    """Close and delete the window while the application still runs.

    Left to interpreter exit, the window would be torn down after or during Qt's own
    teardown, in no set order (KI-019).
    """
    from PySide6.QtCore import QEvent

    window.close()
    window.deleteLater()
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
    splash: QSplashScreen | None,
    ready_seconds: float,
) -> None:
    from caddcalc import __version__
    from caddcalc.gui.branding import packaged_app_dir

    app.processEvents()
    if report_dir is None:
        return
    report_dir.mkdir(parents=True, exist_ok=True)
    window.grab().save(str(report_dir / "window.png"))
    report = {
        "name": branding.name,
        "edition": branding.edition,
        "version": __version__,
        "window_title": window.windowTitle(),
        "icon_loaded": not app.windowIcon().isNull(),
        "splash_shown": splash is not None,
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
