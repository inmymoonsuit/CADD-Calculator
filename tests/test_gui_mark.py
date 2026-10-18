"""A test marked ``gui`` runs with the ``qt`` fixture, so none touches Qt without an app."""

from __future__ import annotations

import pytest


@pytest.mark.gui
def test_a_gui_test_runs_with_the_qt_fixture(request: pytest.FixtureRequest) -> None:
    """Marked ``gui`` alone, it gets the fixture and its application (conftest.py)."""
    from PySide6.QtWidgets import QApplication

    assert "qt" in request.fixturenames
    assert QApplication.instance() is not None


def test_a_test_not_marked_gui_doesnt_get_it(request: pytest.FixtureRequest) -> None:
    """The rest don't start Qt."""
    assert "qt" not in request.fixturenames
