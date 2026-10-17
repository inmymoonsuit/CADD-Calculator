"""Shared test fixtures."""

from __future__ import annotations

import os
from collections.abc import Iterator
from typing import Any

import pytest


@pytest.fixture
def qt(monkeypatch: pytest.MonkeyPatch) -> Iterator[Any]:
    """The Qt widgets module, with an application running offscreen; skips without PySide6.

    At teardown it closes and deletes every top-level widget the test left, then delivers
    the deferred deletes while the application still runs, as pytest-qt's ``qtbot`` does.
    A window left to interpreter exit is torn down in no set order (KI-019).
    """
    monkeypatch.setenv("QT_QPA_PLATFORM", os.environ.get("QT_QPA_PLATFORM", "offscreen"))
    widgets = pytest.importorskip("PySide6.QtWidgets")
    from PySide6.QtCore import QEvent

    app = widgets.QApplication.instance() or widgets.QApplication([])
    before = set(app.topLevelWidgets())
    yield widgets
    for widget in app.topLevelWidgets():
        if widget not in before:
            widget.close()
            widget.deleteLater()
    app.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    app.processEvents()
