"""Shared test fixtures."""

from __future__ import annotations

import os
from collections.abc import Iterator
from typing import Any

import pytest

from caddcalc.core import i18n
from tests.ci_annotations import pytest_terminal_summary  # noqa: F401  # registers the hook


@pytest.fixture(autouse=True)
def _source_language() -> Iterator[None]:
    """Every test starts, and leaves, in the source language, whatever the machine's is.

    The app's ``main()`` chooses the system's languages (ADR-0020 §3), so a test that
    runs it would leave them chosen for the tests after it.
    """
    i18n.use(())
    yield
    i18n.use(())


@pytest.fixture(autouse=True)
def _gui_tests_run_with_qt(request: pytest.FixtureRequest) -> None:
    """A test marked ``gui`` runs with the ``qt`` fixture, as if it had asked for it.

    So no GUI test touches Qt before an application exists, which crashes. A
    ``usefixtures`` mark added in a collection hook wouldn't do: by then each test's
    fixtures are settled, and the mark is ignored.
    """
    if request.node.get_closest_marker("gui") is not None:
        request.getfixturevalue("qt")


@pytest.fixture
def qt(monkeypatch: pytest.MonkeyPatch) -> Iterator[Any]:
    """The Qt widgets module, with an application running offscreen; skips without PySide6.

    At teardown it closes and deletes every top-level widget the test left, then delivers
    the deferred deletes while the application still runs, as pytest-qt's ``qtbot`` does.
    A window left to interpreter exit is torn down in no set order (KI-019).

    The clipboard is the test's own, in memory: the system's is shared with every other
    program on the machine, so on a native platform a test would read another program's
    copy, or overwrite the user's. It's patched on the class, as an instance's patch is
    undone after its window is deleted, which crashes Linux.
    """
    monkeypatch.setenv("QT_QPA_PLATFORM", os.environ.get("QT_QPA_PLATFORM", "offscreen"))
    widgets = pytest.importorskip("PySide6.QtWidgets")
    from PySide6.QtCore import QEvent
    from PySide6.QtGui import QClipboard

    held = [""]

    def set_text(_clipboard: object, text: str, *_mode: object) -> None:
        held[0] = text

    def text(_clipboard: object, *_mode: object) -> str:
        return held[0]

    def clear(_clipboard: object, *_mode: object) -> None:
        held[0] = ""

    monkeypatch.setattr(QClipboard, "setText", set_text)
    monkeypatch.setattr(QClipboard, "text", text)
    monkeypatch.setattr(QClipboard, "clear", clear)
    app = widgets.QApplication.instance() or widgets.QApplication([])
    # The welcome card adds the vendored display face to the application's fonts, which
    # can change the fallback faces other text measures in (S&R's M1 at stop 2). Added
    # first, it's there for every test, so no test's widths depend on whether a card was
    # shown before it.
    from caddcalc.gui.fonts import display_family

    display_family()
    before = set(app.topLevelWidgets())
    yield widgets
    for widget in app.topLevelWidgets():
        if widget not in before:
            widget.close()
            widget.deleteLater()
    app.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    app.processEvents()
