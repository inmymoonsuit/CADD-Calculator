"""Shared test fixtures."""

from __future__ import annotations

import os
from collections.abc import Iterator
from typing import Any

import pytest


@pytest.fixture
def qt(monkeypatch: pytest.MonkeyPatch) -> Iterator[Any]:
    """The Qt widgets module, with an application running offscreen; skips without PySide6."""
    monkeypatch.setenv("QT_QPA_PLATFORM", os.environ.get("QT_QPA_PLATFORM", "offscreen"))
    widgets = pytest.importorskip("PySide6.QtWidgets")
    app = widgets.QApplication.instance() or widgets.QApplication([])
    yield widgets
    app.processEvents()
