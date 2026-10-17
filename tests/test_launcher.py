"""The work-in-progress launcher, scripts/launch_app.py (docs/dev/launching.md)."""

from __future__ import annotations

import importlib.util
from collections.abc import Sequence
from pathlib import Path
from types import ModuleType

import pytest

from caddcalc.gui.branding import ENV_VAR

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "launch_app.py"


@pytest.fixture
def launcher(monkeypatch: pytest.MonkeyPatch) -> tuple[ModuleType, list[list[str]]]:
    """The launcher module, with the app replaced by a recorder of its arguments."""
    spec = importlib.util.spec_from_file_location("launch_app", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    calls: list[list[str]] = []

    def fake_app(argv: Sequence[str] | None = None) -> int:
        calls.append(list(argv or []))
        return 0

    monkeypatch.setattr(module, "app_main", fake_app)
    monkeypatch.setattr(module.faulthandler, "enable", lambda: None)
    return module, calls


def test_runs_unbranded_and_passes_other_arguments_to_the_app(
    launcher: tuple[ModuleType, list[list[str]]], monkeypatch: pytest.MonkeyPatch
) -> None:
    module, calls = launcher
    monkeypatch.setenv(ENV_VAR, "somewhere/else")
    assert module.main(["--smoke-test", "-style", "fusion"]) == 0
    assert calls == [["--smoke-test", "-style", "fusion"]]
    assert ENV_VAR not in module.os.environ, "an inherited pack must not brand the app"


def test_branding_pack_is_checked_and_handed_to_the_app(
    launcher: tuple[ModuleType, list[list[str]]], monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    module, calls = launcher
    monkeypatch.delenv(ENV_VAR, raising=False)
    (tmp_path / "branding.toml").write_text(
        'edition = "example"\nname = "CADD Calculator: Example Edition"\n', encoding="utf-8"
    )
    assert module.main(["--branding", str(tmp_path)]) == 0
    assert calls == [[]]
    assert module.os.environ[ENV_VAR] == str(tmp_path.resolve())


def test_invalid_branding_pack_stops_before_the_app_starts(
    launcher: tuple[ModuleType, list[list[str]]],
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    module, calls = launcher
    assert module.main(["--branding", str(tmp_path / "missing")]) == 2
    assert calls == []
    assert "branding.toml" in capsys.readouterr().err
