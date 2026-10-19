"""The startup order: the card once, then the main window, revealed once behind it.

ADR-0015 §1, amendments. Every window is recorded as the app shows, hides, moves,
resizes and activates it, from the card's show until the startup is done.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import pytest

pytestmark = [pytest.mark.gui, pytest.mark.usefixtures("qt")]


class _Launch:
    """A startup as ``main()`` runs it, with every top-level window event recorded."""

    def __init__(self, monkeypatch: pytest.MonkeyPatch, hold_ms: int) -> None:
        from PySide6.QtCore import QEvent, QObject
        from PySide6.QtWidgets import QApplication, QWidget

        from caddcalc.gui.actions import AppActions
        from caddcalc.gui.app import _Startup
        from caddcalc.gui.branding import GENERIC
        from caddcalc.gui.welcome import WelcomeScreen
        from caddcalc.gui.window import MainWindow

        kinds = {
            QEvent.Type.Show: "show",
            QEvent.Type.Hide: "hide",
            QEvent.Type.Move: "move",
            QEvent.Type.Resize: "resize",
            QEvent.Type.WindowActivate: "activate",
        }
        self.events: list[tuple[float, str, str]] = []
        """(when, which window, what), in order."""
        self.calls: list[tuple[float, str, str]] = []
        """(when, which window, which call) for ``raise_`` and ``activateWindow``."""
        self.painted = 0.0

        def name(widget: object) -> str:
            return "card" if isinstance(widget, WelcomeScreen) else "window"

        launch = self

        class Recorder(QObject):
            def eventFilter(self, watched: QObject, event: QEvent) -> bool:  # noqa: N802
                if isinstance(watched, WelcomeScreen | MainWindow) and event.type() in kinds:
                    launch.events.append((time.perf_counter(), name(watched), kinds[event.type()]))
                return False

        for call in ("raise_", "activateWindow"):
            original = getattr(QWidget, call)

            def spy(widget: QWidget, original: Any = original, call: str = call) -> None:
                if widget.isWindow():
                    self.calls.append((time.perf_counter(), name(widget), call))
                original(widget)

            monkeypatch.setattr(QWidget, call, spy)
        self.app = QApplication.instance()
        self.recorder = Recorder()
        self.app.installEventFilter(self.recorder)
        actions = AppActions(GENERIC, self.app)
        self.welcome = WelcomeScreen(GENERIC, actions)
        self.welcome.painted.connect(self._on_painted)
        self.startup = _Startup(self.app, GENERIC, actions, self.welcome, hold_ms=hold_ms)
        self.actions = actions

    def _on_painted(self) -> None:
        self.painted = time.perf_counter()

    def run_until(self, done: Any, timeout: float = 10) -> None:
        from PySide6.QtWidgets import QApplication

        end = time.perf_counter() + timeout
        while not done():
            assert time.perf_counter() < end, "the startup never finished"
            QApplication.processEvents()
            time.sleep(0.005)

    def changes_after(self, window: str, what: str) -> list[str]:
        """Each show, hide, move or resize of ``window`` after its first ``what``."""
        first = next(i for i, e in enumerate(self.events) if e[1:] == (window, what))
        later = self.events[first + 1 :]
        return [e[2] for e in later if e[1] == window and e[2] != "activate"]

    def when(self, window: str, what: str) -> float:
        return next(e[0] for e in self.events if e[1:] == (window, what))

    def close(self) -> None:
        from shiboken6 import isValid

        self.app.removeEventFilter(self.recorder)
        for widget in (self.welcome, self.startup.window):
            if widget is not None and isValid(widget):
                widget.close()
        self.app.setQuitOnLastWindowClosed(True)


def test_the_card_shows_once_and_the_window_once_behind_it_after_the_hold(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The maintainer saw the card, then the window over it, then the card again."""
    from PySide6.QtCore import Qt, QTimer
    from PySide6.QtGui import QGuiApplication

    hold = 300
    launch = _Launch(monkeypatch, hold)
    launch.welcome.show()
    QTimer.singleShot(0, launch.startup.build_main_window)
    launch.run_until(lambda: launch.startup.revealed)
    launch.run_until(lambda: time.perf_counter() > launch.when("window", "show") + 0.2)
    window = launch.startup.main_window()

    shows = [e[1] for e in launch.events if e[2] == "show"]
    assert shows == ["card", "window"], "each shows once, the card first"
    assert launch.changes_after("card", "show") == [], "the card never moves or hides"
    assert launch.changes_after("window", "show") == [], "nor does the window"
    assert launch.painted > 0
    assert launch.when("window", "show") - launch.painted >= 0.95 * hold / 1000, "the hold"
    assert [c for c in launch.calls if c[2] == "raise_"] == [], "nothing is raised"
    # The card keeps the focus: the window is shown without activating, and nothing
    # activates it. Offscreen, Qt activates every window it shows, whatever is asked.
    assert window.testAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
    assert [c for c in launch.calls if c[1] == "window"] == []
    if QGuiApplication.platformName() != "offscreen":
        assert ("window", "activate") not in [e[1:] for e in launch.events]
    card = launch.welcome.windowHandle()
    assert card is not None and card.transientParent() is window.windowHandle(), "it owns it"
    assert launch.welcome.isVisible() and window.isVisible()

    closed = time.perf_counter()
    launch.welcome.close()
    launch.run_until(lambda: any(c[1:] == ("window", "activateWindow") for c in launch.calls))
    assert all(c[0] >= closed for c in launch.calls if c[1] == "window"), "once it closes"
    launch.close()


def test_closing_the_card_early_reveals_the_window_at_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The hold is for a calm start; a user who closes the card doesn't wait for it."""
    launch = _Launch(monkeypatch, 10_000)
    launch.welcome.show()
    launch.run_until(lambda: launch.painted > 0)
    launch.startup.build_main_window()
    assert not launch.startup.revealed, "ready, but held"
    launch.welcome.close()
    launch.run_until(lambda: launch.startup.revealed, timeout=2)
    assert [c[1:] for c in launch.calls] == [("window", "activateWindow")]
    launch.close()


def test_a_card_closed_before_the_window_is_ready_reveals_it_when_it_is(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    launch = _Launch(monkeypatch, 10_000)
    launch.welcome.show()
    launch.run_until(lambda: launch.painted > 0)
    launch.welcome.close()
    assert not launch.startup.revealed
    launch.startup.build_main_window()
    assert launch.startup.revealed
    assert [c[1:] for c in launch.calls] == [("window", "activateWindow")]
    launch.close()


def test_the_card_is_owned_by_the_window_and_stays_above_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Natively, the system keeps the card above the window that owns it.

    Qt gives a window its owner only as it shows, so the window's shell is made, and the
    card given to it, before the card shows. Given later, the card has no owner, and the
    window, shown on top of it, hides it for good.
    """
    import ctypes
    import sys

    from PySide6.QtCore import QTimer
    from PySide6.QtGui import QGuiApplication

    if sys.platform != "win32" or QGuiApplication.platformName() != "windows":
        pytest.skip("the windows' owner and z-order are the Windows platform's")
    from ctypes import wintypes

    user32 = ctypes.windll.user32  # type: ignore[attr-defined]
    user32.GetWindow.restype = user32.GetTopWindow.restype = ctypes.c_void_p
    user32.GetWindow.argtypes = [ctypes.c_void_p, ctypes.c_uint]
    user32.GetTopWindow.argtypes = [ctypes.c_void_p]
    user32.WindowFromPoint.argtypes = [wintypes.POINT]
    user32.WindowFromPoint.restype = user32.GetAncestor.restype = ctypes.c_void_p
    user32.GetAncestor.argtypes = [ctypes.c_void_p, ctypes.c_uint]
    next_window, owner, root = 2, 4, 2  # GW_HWNDNEXT, GW_OWNER, GA_ROOT

    launch = _Launch(monkeypatch, 100)
    launch.welcome.show()
    QTimer.singleShot(0, launch.startup.build_main_window)
    launch.run_until(lambda: launch.startup.revealed)
    launch.run_until(lambda: time.perf_counter() > launch.when("window", "show") + 0.3)
    card, window = int(launch.welcome.winId()), int(launch.startup.window.winId())
    assert user32.GetWindow(card, owner) == window
    order = []
    hwnd = user32.GetTopWindow(None)
    while hwnd and len(order) < 10_000:
        order.append(hwnd)
        hwnd = user32.GetWindow(hwnd, next_window)
    assert order.index(card) < order.index(window), "the card is above the window"
    frame, ratio = launch.welcome.frameGeometry(), launch.welcome.devicePixelRatioF()
    centre = wintypes.POINT(round(frame.center().x() * ratio), round(frame.center().y() * ratio))
    shown = user32.GetAncestor(user32.WindowFromPoint(centre), root)
    assert shown == card, "on screen, the card is what's at its centre"
    launch.close()


SHELL_THEN_BUILD = """
import json, sys
from PySide6.QtWidgets import QApplication

app = QApplication([])
from caddcalc.gui.actions import AppActions
from caddcalc.gui.branding import GENERIC
from caddcalc.gui.window import MainWindow


def calculators():
    return sorted(name for name in sys.modules if name.startswith("caddcalc.calculators"))


window = MainWindow(branding=GENERIC, actions=AppActions(GENERIC), build=False)
window.winId()
shell = calculators()
window.build()
print(json.dumps([shell, len(calculators())]))
"""


def test_the_shell_loads_no_calculator_until_it_is_built(tmp_path: Path) -> None:
    """The shell comes before the card's first paint, the calculators only with the build.

    Startup imports the window's module and makes its shell before the card shows, so
    neither loads a calculator; ``build`` does, after the first paint (ADR-0015,
    amendments). Tests import the calculators already, so this runs in its own process.
    """
    import json
    import os
    import subprocess
    import sys

    script = tmp_path / "shell_then_build.py"
    script.write_text(SHELL_THEN_BUILD, encoding="utf-8")
    env = {**os.environ, "QT_QPA_PLATFORM": os.environ.get("QT_QPA_PLATFORM", "offscreen")}
    done = subprocess.run(  # noqa: S603  # this interpreter, on a script the test wrote
        [sys.executable, str(script)],
        capture_output=True,
        text=True,
        timeout=60,
        env=env,
        check=False,
    )
    assert done.returncode == 0, done.stderr
    shell, built = json.loads(done.stdout.splitlines()[-1])
    assert shell == [], "the shell loaded calculators before the card's first paint"
    assert built > 0, "the build loads them"
