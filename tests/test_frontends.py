"""CLI behavior and a GUI smoke test (skipped when PySide6 is not installed)."""

from __future__ import annotations

import json
import os

import pytest

from caddcalc.cli import main


def test_cli_list(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["list"]) == 0
    assert "sheet_metal.bend_allowance" in capsys.readouterr().out


def test_cli_run_shows_work(capsys: pytest.CaptureFixture[str]) -> None:
    assert (
        main(
            [
                "run",
                "sheet_metal.bend_allowance",
                "T=0.1046",
                "R=0.156",
                "A=90",
                "--method",
                "course",
            ]
        )
        == 0
    )
    out = capsys.readouterr().out
    assert "BA = (0.64·T + 1.57·R)·A/90" in out
    assert "0.3119 in" in out
    assert "unverified · reproduces legacy" in out


def test_cli_run_json_and_metric(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["run", "sheet_metal.v_die_opening", "R=1.5", "--units", "mm", "--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["outputs"]["die_opening"]["unit"] == "mm"
    assert data["outputs"]["die_opening"]["value"] == pytest.approx(1.5 / 0.156)


def test_cli_reports_input_errors(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["run", "sheet_metal.bend_allowance", "T=-1"]) == 2
    assert "must be greater than 0" in capsys.readouterr().err
    assert main(["run", "sheet_metal.bend_allowance", "Q=1"]) == 2
    assert main(["run", "no.such_calc"]) == 2


@pytest.mark.gui
def test_gui_window_computes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("QT_QPA_PLATFORM", os.environ.get("QT_QPA_PLATFORM", "offscreen"))
    widgets = pytest.importorskip("PySide6.QtWidgets")
    from caddcalc.gui.window import MainWindow

    app = widgets.QApplication.instance() or widgets.QApplication([])
    window = MainWindow()
    window.select_calculator("sheet_metal.bend_allowance")
    window.method_box.setCurrentIndex(0)  # course
    assert "0.3119 in" in window.output.toPlainText()

    window.units_box.setCurrentText("mm")
    _param, thickness = window.fields["thickness"]
    assert thickness.text() == "2.65684"  # 0.1046 in, re-expressed

    thickness.setText("-1")
    window.recompute()
    assert "Check the inputs" in window.output.toPlainText() or "greater than" in (
        window.output.toPlainText()
    )
    window.close()
    app.processEvents()
