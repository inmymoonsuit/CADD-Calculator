"""A calculator's unexpected error is reported everywhere, never a stale result.

The core wraps a compute's error that isn't caddcalc's own as a SpecError, the window's
recalculation is an isolation boundary, and the app shows an error nothing caught
(S&R's review of f97d230; ADR-0006 and ADR-0017 §4, amendments).
"""

from __future__ import annotations

import sys
from typing import Any, override

import pytest

from caddcalc.calculators import default_registry
from caddcalc.core import (
    Calculator,
    Context,
    InputError,
    Method,
    Output,
    Param,
    Registry,
    SpecError,
    Verification,
)
from caddcalc.core.units import Dimension
from tests.qt_helpers import open_window, settle, type_into
from tests.test_domains import ACME

L = Dimension.LENGTH


class _Flaky(Calculator):
    """A plugin calculator whose second method's compute has a bug."""

    id = "acme.flaky"
    name = "Flaky"
    domain = "acme"
    summary = "Copies a length, or fails."
    params = (Param("length", "X", "Length", L, default="1 in"),)
    outputs = (Output("copy", "Y", "Copy", L),)
    methods = (
        Method("good", "Good", "Y = X", Verification.UNVERIFIED),
        Method("failing", "Failing", "Y = X", Verification.UNVERIFIED),
    )

    @override
    def compute(self, ctx: Context) -> None:
        if ctx.method == "failing":
            raise ZeroDivisionError("the plugin's own error")
        ctx.calc("Y", "X", label="Copy", dimension=L, output="copy")


def _registry() -> Registry:
    registry = default_registry(load_plugins=False)
    registry.register_domain(ACME)
    registry.register(_Flaky)
    return registry


def test_the_core_wraps_a_computes_unexpected_error() -> None:
    """As a check's is: a SpecError naming the method, caused by the original."""
    expected = r"acme\.flaky \(failing\): compute failed: ZeroDivisionError: the plugin's own"
    with pytest.raises(SpecError, match=expected) as caught:
        _Flaky().run(method="failing")
    assert isinstance(caught.value.__cause__, ZeroDivisionError)
    assert _Flaky().run(method="good").outputs["copy"] == pytest.approx(25.4), "1 in, in mm"


def test_caddcalcs_own_errors_pass_through() -> None:
    """An input error is worded for users already, so it isn't wrapped."""

    class _Picky(_Flaky):
        id = "acme.picky"

        @override
        def compute(self, ctx: Context) -> None:
            raise InputError("a value the user can fix")

    with pytest.raises(InputError, match="a value the user can fix"):
        _Picky().run()


def test_the_cli_exits_with_the_error(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """It says what failed and exits non-zero, with or without --json."""
    from caddcalc import cli

    monkeypatch.setattr(cli, "default_registry", _registry)
    for extra in ([], ["--json"]):
        assert cli.main(["run", "acme.flaky", "X=2", "--method", "failing", *extra]) == 2
        assert "compute failed: ZeroDivisionError: the plugin's own error" in (
            capsys.readouterr().err
        )
    assert cli.main(["run", "acme.flaky", "X=2", "--method", "good", "--json"]) == 0


@pytest.mark.gui
def test_the_window_blanks_the_results_and_shows_the_error_then_recovers() -> None:
    """Choosing the failing method never leaves the good one's results on screen."""
    window = open_window(_registry())
    window.select_calculator("acme.flaky")
    window.show()
    settle(window)
    value = window.results.fields["copy"].value
    assert value.text() not in ("", "—")
    window.method_box.setCurrentIndex(1)  # through the box's signal, as a user's choice is
    settle(window)
    assert window.result is None
    assert value.text() in ("", "—")
    assert "compute failed: ZeroDivisionError" in window.output.toPlainText()
    window.method_box.setCurrentIndex(0)
    settle(window)
    assert window.result is not None
    assert value.text() not in ("", "—")
    assert "ZeroDivisionError" not in window.output.toPlainText()
    window.close()


@pytest.mark.gui
def test_any_error_showing_a_result_blanks_it(monkeypatch: pytest.MonkeyPatch) -> None:
    """The window's boundary covers showing the result too, not only running it."""
    from caddcalc.gui import window as window_module

    window = open_window(_registry())
    window.select_calculator("acme.flaky")
    settle(window)

    def broken(*_args: Any, **_kwargs: Any) -> str:
        raise RuntimeError("the work couldn't be written")

    monkeypatch.setattr(window_module, "result_html", broken)
    type_into(window.fields["length"][1], "3")
    settle(window)
    assert window.result is None
    assert window.results.fields["copy"].value.text() in ("", "—")
    assert "Unexpected error: RuntimeError: the work couldn't be written" in (
        window.output.toPlainText()
    )
    window.close()


@pytest.mark.gui
def test_an_error_nothing_caught_is_shown_once(monkeypatch: pytest.MonkeyPatch) -> None:
    """An error in a Qt slot is still written out, then shown, never a box on a box."""
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication

    from caddcalc.gui.app import install_error_hook

    written: list[BaseException] = []
    monkeypatch.setattr(sys, "excepthook", lambda _kind, error, _tb: written.append(error))
    before = sys.excepthook
    shown: list[tuple[str, str]] = []

    def show(message: str, details: str) -> None:
        shown.append((message, details))
        sys.excepthook(RuntimeError, RuntimeError("while showing"), None)

    app = QApplication.instance()
    assert isinstance(app, QApplication)
    restore = install_error_hook(app, show)
    try:

        def slot() -> None:
            raise ZeroDivisionError("in a slot")

        QTimer.singleShot(0, slot)
        for _ in range(5):
            QApplication.processEvents()
    finally:
        restore()
    assert sys.excepthook is before
    assert [str(e) for e in written] == ["in a slot", "while showing"], "both written out"
    assert len(shown) == 1, "no second box while one shows"
    message, details = shown[0]
    assert message == "ZeroDivisionError: in a slot"
    assert "Traceback" in details and "in a slot" in details
