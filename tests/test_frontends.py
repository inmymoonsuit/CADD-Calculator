"""CLI behavior and a GUI smoke test (skipped when PySide6 is not installed)."""

from __future__ import annotations

import json
from typing import Any

import pytest

from caddcalc.cli import LANGUAGE_VARIABLES, cli_languages, main
from caddcalc.core import i18n
from caddcalc.core.formatting import POINT


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


@pytest.mark.parametrize(
    ("lang", "environ", "languages"),
    [
        ("en_GB", {"CADDCALC_LANG": "fr", "LANG": "de_DE.UTF-8"}, ["en_GB"]),
        (None, {"CADDCALC_LANG": "fr", "LANGUAGE": "de", "LANG": "de_DE.UTF-8"}, ["fr"]),
        (None, {"LANGUAGE": "fr:en_GB", "LC_ALL": "de_DE.UTF-8"}, ["fr", "en_GB"]),
        (None, {"LC_ALL": "de_DE.UTF-8", "LANG": "fr_FR"}, ["de_DE.UTF-8"]),
        (None, {"LC_MESSAGES": "pt_BR", "LANG": "fr_FR"}, ["pt_BR"]),
        (None, {"LANG": "en_AU.UTF-8"}, ["en_AU.UTF-8"]),
        (None, {"LANG": "C.UTF-8"}, []),
        (None, {"LANGUAGE": "fr:C:en_GB"}, ["fr"]),
        (None, {"LANG": "POSIX"}, []),
        (None, {}, []),
    ],
)
def test_the_cli_language_comes_from_lang_then_the_environment(
    lang: str | None, environ: dict[str, str], languages: list[str]
) -> None:
    """--lang, CADDCALC_LANG, then gettext's own variables in its order (ADR-0020 §3)."""
    assert cli_languages(lang, environ) == languages


def test_the_cli_writes_words_in_its_language_and_numbers_with_a_point(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Scripts read the CLI's numbers, so they keep "." whatever the language."""
    for name in LANGUAGE_VARIABLES:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("LANG", "de_DE.UTF-8")
    args = ["run", "sheet_metal.bend_allowance", "T=0.1046", "R=0.156", "A=90"]
    assert main([*args, "--method", "course"]) == 0
    assert i18n.languages() == ("de_DE",)
    assert main(["--lang", "en_GB", *args, "--method", "course"]) == 0
    assert i18n.languages() == ("en_GB",)
    assert "0.3119 in" in capsys.readouterr().out


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
    assert notes[0]["text"].startswith("Inside radius 2.54 mm is less than the thickness")
    assert "minimum bend radius" in notes[0]["detail"]
    assert notes[0]["quantities"]["T"] == {"value": 6.35, "unit": "mm", "dimension": "length"}
    assert main(args) == 0
    out = capsys.readouterr().out
    assert "Notes\n  ! Inside radius 0.1000 in is less than the thickness 0.2500 in." in out
    assert "\n      Check the material's minimum bend radius;" in out, "the detail, indented"

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
@pytest.mark.usefixtures("qt")
def test_gui_results_mark_each_kind_of_note() -> None:
    from caddcalc.calculators.sheet_metal import FormedSegmentFlatLength
    from caddcalc.core.formatting import DisplayPrefs
    from caddcalc.gui.window import result_html

    calc = FormedSegmentFlatLength()
    result = calc.run({"formed_dimension": 1.0, "bend_angle_1": 120.0, "bend_angle_2": 90.0})
    html = result_html(calc, result, DisplayPrefs())
    assert "icon:light/icon_error/alert-circle" in html, "an impossibility is marked as an error"
    assert "icon:light/icon_warning/alert-triangle" in html, "a warning is marked as one"
    assert "<b>Not makeable: </b>The flat length" in html
    assert "Notes</h3>" in html
    notes = html.split("Notes</h3>", 1)[1].split("<h3>", 1)[0]
    assert "<li" not in notes and "<ul" not in notes, "the icon marks each note; no bullet (F2)"


@pytest.mark.gui
def test_gui_window_computes(qt: Any) -> None:
    from caddcalc.gui.window import MainWindow
    from tests.qt_helpers import results_text

    app = qt.QApplication.instance()
    window = MainWindow(symbols=POINT)
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

    window = MainWindow(symbols=POINT)
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
    window = MainWindow(registry=registry, symbols=POINT)
    assert window.registry is registry
    assert [
        window.tree.topLevelItem(i).text(0) for i in range(window.tree.topLevelItemCount())
    ] == ["Acme Tools"]
    window.close()
