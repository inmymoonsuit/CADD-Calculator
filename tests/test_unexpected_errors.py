"""A calculator's or a family's unexpected error is reported everywhere, never stale.

The core wraps an error that isn't caddcalc's own, from a compute or from a domain's
resolver or details, as a SpecError. The window's recalculation, its form and its
settings page are isolation boundaries, and the app shows an error nothing caught
(S&R's reviews of f97d230 and a1f0735; ADR-0006 and ADR-0017 §4, amendments).
"""

from __future__ import annotations

import sys
from collections.abc import Mapping, Sequence
from html import unescape
from typing import Any, override

import pytest

from caddcalc.calculators import default_registry
from caddcalc.core import (
    Calculator,
    Choice,
    Context,
    DerivedValue,
    Domain,
    Fact,
    InputError,
    Method,
    Output,
    Param,
    Registry,
    SpecError,
    StartingValue,
    Verification,
)
from caddcalc.core.choices import Option
from caddcalc.core.units import Dimension
from tests.qt_helpers import open_window, settle, type_into
from tests.test_choices import SETTINGS, _Bend, _Plates
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


class _Picky(_Flaky):
    """A plugin calculator whose compute refuses its input, as an input error."""

    id = "acme.picky"

    @override
    def compute(self, ctx: Context) -> None:
        raise InputError("a value the user can fix")


def test_caddcalcs_own_errors_pass_through() -> None:
    """An input error is worded for users already, so it isn't wrapped."""
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
        err = capsys.readouterr().err
        assert "compute failed: ZeroDivisionError: the plugin's own error" in err
        assert "Traceback" in err, "the plugin's author gets where it failed (S&R's note)"
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
    assert "The calculation failed:" in window.output.toPlainText()
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


class _FaultyPlates(_Plates):
    """The test plates' resolver, with a bug to switch on in either of its calls."""

    def __init__(self) -> None:
        super().__init__(domain="faulty")
        self.failing: set[str] = set()

    @override
    def options(self, choice: str, _selections: Mapping[str, str]) -> Sequence[Option]:
        if "options" in self.failing:
            raise ZeroDivisionError("options' own error")
        return super().options(choice, _selections)

    @override
    def derive(self, selections: Mapping[str, str]) -> Mapping[str, DerivedValue]:
        if "derive" in self.failing:
            raise ZeroDivisionError("derive's own error")
        if "derive with an input error" in self.failing:
            raise InputError("a plate the user can fix")
        return super().derive(selections)


class _FaultyDetails:
    """Details with a bug to switch on in either call."""

    def __init__(self) -> None:
        self.failing: set[str] = set()

    def facts(self, _selections: Mapping[str, str]) -> Sequence[Fact]:
        if "facts" in self.failing:
            raise ZeroDivisionError("facts' own error")
        return ()

    def starting_values(self, _selections: Mapping[str, str]) -> Sequence[StartingValue]:
        if "starting_values" in self.failing:
            raise ZeroDivisionError("starting values' own error")
        return ()


class _FaultyBend(_Bend):
    id = "faulty.bend"
    domain = "faulty"


def _faulty() -> tuple[Domain, _FaultyPlates, _FaultyDetails]:
    resolver, details = _FaultyPlates(), _FaultyDetails()
    domain = Domain(
        "faulty",
        "Faulty",
        "A plugin family whose code can fail.",
        settings=SETTINGS,
        choices=(Choice("plate", "Plate"),),
        resolver=resolver,
        details=details,
    )
    return domain, resolver, details


@pytest.mark.parametrize(
    ("call", "what"),
    [
        ("options", "its resolver's options for 'plate'"),
        ("derive", "its resolver's derive"),
        ("facts", "its details' facts"),
        ("starting_values", "its details' starting values"),
    ],
)
def test_the_core_wraps_a_domains_unexpected_error(call: str, what: str) -> None:
    """S&R's review of a1f0735: a family's own code, as a compute's (ADR-0006)."""
    domain, resolver, details = _faulty()
    resolver.failing.add(call)
    details.failing.add(call)
    calls = {
        "options": lambda: domain.options("plate"),
        "derive": lambda: domain.derived({"plate": "std:1"}),
        "facts": lambda: domain.facts({}),
        "starting_values": lambda: domain.starting_values({}),
    }
    with pytest.raises(SpecError, match=rf"Domain 'faulty': {what} failed: ZeroDivisionError") as e:
        calls[call]()
    assert isinstance(e.value.__cause__, ZeroDivisionError)


def _faulty_window() -> tuple[Any, Domain, _FaultyPlates]:
    domain, resolver, _details = _faulty()
    registry = default_registry(load_plugins=False)
    registry.register_domain(domain)
    registry.register(_FaultyBend)
    window = open_window(registry)
    window.domain_settings = window.domain_settings.set_choice(domain, "plate", "std:1")
    return window, domain, resolver


@pytest.mark.gui
def test_a_family_that_fails_to_derive_blanks_the_calculator(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Its fields are read inside the window's boundary, and its form is one too."""
    window, _domain, resolver = _faulty_window()
    window.select_calculator("faulty.bend")
    settle(window)
    value = window.results.fields["total"].value
    assert value.text() not in ("", "—")
    resolver.failing.add("derive")
    window.recompute()
    settle(window)
    assert window.result is None and value.text() in ("", "—"), "never the value from before"
    work = window.output.toPlainText()
    assert "The calculation failed:" in work
    assert "its resolver's derive failed: ZeroDivisionError: derive's own error" in work
    assert "The above exception was the direct cause" in capsys.readouterr().err
    window.method_box.setCurrentIndex(1)  # the form asks what its fields inherit
    settle(window)
    assert window.form.rowCount() == 0, "never a half-built form"
    assert "its resolver's derive failed" in window.output.toPlainText()
    resolver.failing.clear()
    window.method_box.setCurrentIndex(0)
    settle(window)
    assert window.form.rowCount() > 0 and value.text() not in ("", "—")
    window.close()


@pytest.mark.gui
def test_a_family_that_fails_shows_its_error_in_place_of_its_settings() -> None:
    """The settings page is a boundary: its error, never a half-built form."""
    window, _domain, resolver = _faulty_window()
    resolver.failing.add("options")
    window.select_domain("faulty")
    settle(window)
    note = unescape(window.domain_note.text())
    assert "The settings couldn't be shown:" in note
    assert "its resolver's options for 'plate' failed: ZeroDivisionError" in note
    assert window.settings_form.rowCount() == 0 and window.settings_box.isHidden()
    resolver.failing.clear()
    window.select_domain("faulty")
    settle(window)
    assert window.settings_form.rowCount() > 0 and not window.settings_box.isHidden()
    assert "couldn't be shown" not in unescape(window.domain_note.text())

    resolver.failing.add("derive")
    box = window.choice_rows["plate"][1]
    box.setCurrentIndex(box.findData("std:2"))  # through the box's signal, as a user's pick
    settle(window)
    assert window.settings_form.rowCount() == 0
    assert "its resolver's derive failed" in unescape(window.domain_note.text())
    window.close()


@pytest.mark.gui
def test_an_input_to_fix_and_a_failed_calculation_are_headed_apart() -> None:
    """S&R's L1: "Check the inputs:" only where the user can fix an input."""
    window = open_window(_registry())
    window.select_calculator("acme.flaky")
    type_into(window.fields["length"][1], "abc")
    settle(window)
    work = window.output.toPlainText()
    assert "Check the inputs:" in work and "The calculation failed:" not in work
    window.close()


@pytest.mark.gui
@pytest.mark.parametrize("guard", ["about to quit", "closing down", "not an Exception"])
def test_the_hook_only_writes_out_when_a_box_cant_or_shouldnt_show(
    guard: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """S&R's notes 2 and 3: from aboutToQuit on, while closing down, and for KeyboardInterrupt."""
    from PySide6.QtWidgets import QApplication

    from caddcalc.gui.app import install_error_hook

    written: list[BaseException] = []
    monkeypatch.setattr(sys, "excepthook", lambda _kind, error, _tb: written.append(error))
    shown: list[str] = []
    app = QApplication.instance()
    assert isinstance(app, QApplication)
    restore = install_error_hook(app, lambda message, _details: shown.append(message))
    try:
        error: BaseException = ZeroDivisionError("late")
        if guard == "about to quit":
            app.aboutToQuit.emit()
        elif guard == "closing down":
            monkeypatch.setattr(QApplication, "closingDown", staticmethod(lambda: True))
        else:
            error = KeyboardInterrupt()
        sys.excepthook(type(error), error, None)
    finally:
        monkeypatch.undo()
        restore()
    assert written == [error], "still written out"
    assert shown == []


def test_a_domains_own_input_error_passes_through() -> None:
    """Worded for users already, a family's input error isn't wrapped (S&R's K2)."""
    domain, resolver, _details = _faulty()
    resolver.failing.add("derive with an input error")
    with pytest.raises(InputError, match="a plate the user can fix"):
        domain.derived({"plate": "std:1"})


@pytest.mark.gui
def test_a_setting_applied_while_the_family_fails_shows_its_error() -> None:
    """S&R's L1: applying a typed setting is a settings-page boundary too."""
    window, _domain, resolver = _faulty_window()
    window.select_domain("faulty")
    settle(window)
    resolver.failing.add("derive")
    _setting, edit = window.setting_fields["thickness"]
    type_into(edit, "1")  # Enter: the field's editingFinished applies it
    settle(window)
    assert window.settings_failed and window.settings_box.isHidden()
    assert window.settings_form.rowCount() == 0
    assert "its resolver's derive failed" in unescape(window.domain_note.text())
    window.close()


@pytest.mark.gui
def test_opening_the_familys_calculator_while_it_fails_builds_no_form() -> None:
    """S&R's K4: building the form is a boundary, opening it from another calculator."""
    window, _domain, resolver = _faulty_window()
    window.select_calculator("sheet_metal.bend_allowance")
    settle(window)
    resolver.failing.add("derive")
    window.select_calculator("faulty.bend")  # the form asks what its fields inherit
    settle(window)
    assert window.form.rowCount() == 0 and window.result is None
    assert window.results.fields["total"].value.text() in ("", "—")
    assert "its resolver's derive failed" in window.output.toPlainText()
    window.close()


@pytest.mark.gui
def test_a_page_built_again_before_the_deferred_clear_keeps_its_form() -> None:
    """S&R's K7: the failed page's clear, deferred to the event loop, skips a rebuilt page."""
    window, _domain, resolver = _faulty_window()
    window.select_domain("faulty")
    settle(window)
    resolver.failing.add("derive")
    box = window.choice_rows["plate"][1]
    box.setCurrentIndex(box.findData("std:2"))  # fails; the form's clear waits for the loop
    assert window.settings_failed
    resolver.failing.clear()
    window.select_domain("faulty")  # built again before the loop runs
    rows = window.settings_form.rowCount()
    assert rows > 0 and not window.settings_failed
    settle(window)
    assert window.settings_form.rowCount() == rows and not window.settings_box.isHidden()
    window.close()


@pytest.mark.gui
def test_an_input_error_from_the_run_is_headed_check_the_inputs() -> None:
    """S&R's K9: a run's input error is the user's to fix, so it's headed so."""
    registry = _registry()
    registry.register(_Picky)
    window = open_window(registry)
    window.select_calculator("acme.picky")
    settle(window)
    work = window.output.toPlainText()
    assert "Check the inputs:" in work and "a value the user can fix" in work
    assert "The calculation failed:" not in work
    window.close()
