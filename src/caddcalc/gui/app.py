"""Entry point for the desktop app (``caddcalc-gui`` or ``caddcalc gui``)."""

from __future__ import annotations

import sys
from collections.abc import Sequence


def main(argv: Sequence[str] | None = None) -> int:
    try:
        from PySide6.QtWidgets import QApplication
    except ImportError:
        print(
            "The desktop app needs PySide6. Install it with:\n"
            "  uv sync --extra gui        (from a source checkout)\n"
            "  pip install 'cadd-calculator[gui]'",
            file=sys.stderr,
        )
        return 1

    from caddcalc import __version__
    from caddcalc.gui.window import MainWindow

    app = QApplication.instance() or QApplication([sys.argv[0], *(argv or [])])
    app.setApplicationName("CADD Calculator")
    app.setApplicationVersion(__version__)
    app.setOrganizationName("CADD Calculator")
    window = MainWindow()
    window.show()
    return int(app.exec())


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
