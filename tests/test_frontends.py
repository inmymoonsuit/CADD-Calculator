"""CLI behavior and a GUI smoke test (skipped when PySide6 is not installed)."""

from __future__ import annotations

import json
from typing import Any

import pytest

from caddcalc.cli import main


def test_cli_list(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["list"]) == 0
    assert "sheet_metal.bend_allowance" in capsys.readouterr().out


def test_cli_list_json_names_each_domain(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["list", "--json"]) == 0
    rows = json.loads(capsys.readouterr().out)
    bend = next(r for r in rows if r["id"] == "sheet_metal.bend_allowance")
    assert (bend["domain"], bend["domain_name"]) == ("sheet_metal", "Sheet Metal")


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
    assert "0.1046 in  (entered)" in out


def test_cli_run_json_and_metric(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["run", "sheet_metal.v_die_opening", "R=1.5", "--units", "mm", "--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["outputs"]["die_opening"]["unit"] == "mm"
    assert data["outputs"]["die_opening"]["value"] == pytest.approx(1.5 / 0.156)


def test_cli_reports_notes_with_their_kind(capsys: pytest.CaptureFixture[str]) -> None:
    args = ["run", "sheet_metal.bend_allowance", "T=0.25", "R=0.1"]
    assert main([*args, "--json"]) == 0
    notes = json.loads(capsys.readouterr().out)["notes"]
    assert [(n["kind"], n["references"], n["subjects"]) for n in notes] == [
        ("warning", [], ["inside_radius", "thickness"])
    ]
    assert "minimum bend radius" in notes[0]["text"]
    assert main(args) == 0
    assert "Notes\n  ! Inside radius is smaller" in capsys.readouterr().out

    short = ["run", "sheet_metal.segment_flat_length", "FVD=0.2", "A1=90", "A2=90"]
    assert main(short) == 0
    assert "  ! Not makeable: The flat length is zero or negative" in capsys.readouterr().out


def test_cli_reports_input_errors(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["run", "sheet_metal.bend_allowance", "T=-1"]) == 2
    assert "Material thickness (T) must be greater than 0 in" in capsys.readouterr().err
    assert main(["run", "sheet_metal.bend_allowance", "T=-1", "--units", "mm"]) == 2
    assert "must be greater than 0 mm" in capsys.readouterr().err
    assert main(["run", "sheet_metal.bend_allowance", "Q=1"]) == 2
    assert main(["run", "no.such_calc"]) == 2
    last = capsys.readouterr().err.splitlines()[-1]
    assert last.startswith("error: No calculator 'no.such_calc'."), "printed without quotes"


@pytest.mark.gui
def test_gui_results_mark_each_kind_of_note() -> None:
    pytest.importorskip("PySide6.QtWidgets")
    from caddcalc.calculators.sheet_metal import FormedSegmentFlatLength
    from caddcalc.core.formatting import DisplayPrefs
    from caddcalc.gui.window import result_html

    calc = FormedSegmentFlatLength()
    result = calc.run({"formed_dimension": 1.0, "bend_angle_1": 120.0, "bend_angle_2": 90.0})
    html = result_html(calc, result, DisplayPrefs())
    assert "icon:light/icon_error/alert-circle" in html, "an impossibility is marked as an error"
    assert "icon:light/icon_warning/alert-triangle" in html, "a warning is marked as one"
    assert "Not makeable: The flat length" in html
    assert "Notes</h3>" in html


@pytest.mark.gui
def test_gui_window_computes(qt: Any) -> None:
    from caddcalc.gui.window import MainWindow
    from tests.qt_helpers import results_text

    app = qt.QApplication.instance()
    window = MainWindow()
    window.select_calculator("sheet_metal.bend_allowance")
    window.method_box.setCurrentIndex(0)  # course
    assert "BA Bend allowance 0.3119 in" in results_text(window)

    window.units_box.setCurrentText("mm")
    _param, thickness = window.fields["thickness"]
    assert thickness.text() == "2.65684"  # 0.1046 in, re-expressed

    from PySide6.QtTest import QTest

    thickness.selectAll()
    QTest.keyClicks(thickness, "-1")  # typed, so it is the user's intent (ADR-0013 §9)
    assert "must be greater than 0 mm" in results_text(window)
    window.close()
    app.processEvents()


@pytest.mark.gui
@pytest.mark.usefixtures("qt")
def test_a_window_is_freed_when_the_last_reference_goes() -> None:
    """KI-019: no slot may hold the window, or it outlives its code and crashes at exit."""
    import gc
    import weakref

    from caddcalc.gui.window import MainWindow

    window = MainWindow()
    window.select_calculator("sheet_metal.bend_allowance")
    window.select_domain("sheet_metal")
    window.select_calculator("sheet_metal.v_die_opening")
    alive = weakref.ref(window)
    window.close()
    del window
    gc.collect()
    assert alive() is None, "a cycle through the window's connections keeps it alive"


@pytest.mark.gui
@pytest.mark.usefixtures("qt")
def test_an_explicit_registry_is_kept_even_with_no_calculators() -> None:
    """A Registry has a length, so an empty one is falsy; it's still the one given."""
    from caddcalc.core import Domain, Registry
    from caddcalc.gui.window import MainWindow

    registry = Registry()
    registry.register_domain(Domain("acme", "Acme Tools", "A domain with no calculators yet."))
    assert len(registry) == 0
    window = MainWindow(registry=registry)
    assert window.registry is registry
    assert [
        window.tree.topLevelItem(i).text(0) for i in range(window.tree.topLevelItemCount())
    ] == ["Acme Tools"]
    window.close()
