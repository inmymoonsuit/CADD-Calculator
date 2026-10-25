"""The Windows installer, the winget manifests, and the signing gate (slice d3).

The installer itself is built and run in CI (release.yml: install, start, uninstall);
these check the rules that don't need Inno Setup: the script's stable AppId and the
defines it insists on, the build's defines, the winget renderer's checks, and that the
signing job is gated on tags and settings and never fails for missing ones.
"""

from __future__ import annotations

import importlib.util
import os
import re
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).parents[1]
ISS = ROOT / "packaging" / "windows" / "CADDCalculator.iss"
WORKFLOW = ROOT / ".github" / "workflows" / "release.yml"
APP_ID = "{{B2EF94B1-E799-438B-AEF3-A34EFB0048A2}"
"""The installer's AppId. It must never change: Windows matches upgrades by it."""


def _load(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def winget() -> ModuleType:
    return _load("winget", ROOT / "packaging" / "windows" / "winget.py")


def test_the_installer_keeps_its_app_id_and_installs_per_user() -> None:
    script = ISS.read_text(encoding="utf-8")
    assert f"AppId={APP_ID}" in script
    assert "PrivilegesRequired=lowest" in script, "a per-user install needs no admin rights"
    assert "PrivilegesRequiredOverridesAllowed=dialog commandline" in script
    assert "DefaultDirName={autopf}" in script
    assert "LicenseFile=" in script
    assert "[Icons]" in script and "{autoprograms}" in script, "a Start-menu shortcut"


def test_the_installer_script_refuses_to_compile_without_the_builds_defines() -> None:
    script = ISS.read_text(encoding="utf-8")
    for name in (
        "SourceDir",
        "AppVersion",
        "NumericVersion",
        "LicenseFile",
        "IconFile",
        "OutputDir",
        "OutputBase",
    ):
        assert re.search(rf"#ifndef {name}\s+#error", script), name


@pytest.mark.gui
def test_the_build_passes_the_version_and_folder_to_the_installer(tmp_path: Path) -> None:
    pytest.importorskip("PySide6.QtGui")
    import sys

    sys.path.insert(0, str(ROOT / "packaging"))
    try:
        build = importlib.import_module("build")
    finally:
        sys.path.remove(str(ROOT / "packaging"))
    from caddcalc import __version__

    output = tmp_path / "CADDCalculator-1.2.3-generic-windows-x64"
    output.mkdir()
    (output / "LICENSE.md").write_text("Apache License\n", encoding="utf-8")
    page = build.installer_license(output, tmp_path)
    text = page.read_text(encoding="utf-8")
    assert text.startswith("Apache License")
    assert "Microsoft-Visual-C++-runtime.txt" in text, "Low 5: the runtime's terms"
    assert "GNU LGPL v3" in text
    defines = build.installer_defines(output, tmp_path / "app.ico", page)
    assert defines["LicenseFile"] == str(page)
    assert defines["SourceDir"] == str(output)
    assert defines["AppVersion"] == __version__
    assert re.fullmatch(r"\d+\.\d+\.\d+\.\d+", defines["NumericVersion"])
    assert defines["OutputDir"] == str(tmp_path)
    assert defines["OutputBase"] == f"{output.name}-setup"
    script = ISS.read_text(encoding="utf-8")
    for name in defines:
        assert f"#ifndef {name}" in script, f"the script takes {name}"


def test_winget_render_fills_every_template(winget: ModuleType, tmp_path: Path) -> None:
    url = "https://github.com/inmymoonsuit/CADD-Calculator/releases/download/v0.3.0/x-setup.exe"
    written = winget.render("0.3.0", url, "ab" * 32, tmp_path)
    assert sorted(p.name for p in written) == [
        "inmymoonsuit.CADDCalculator.installer.yaml",
        "inmymoonsuit.CADDCalculator.locale.en-US.yaml",
        "inmymoonsuit.CADDCalculator.yaml",
    ]
    installer = (tmp_path / "inmymoonsuit.CADDCalculator.installer.yaml").read_text()
    assert f"InstallerUrl: {url}" in installer
    assert "InstallerSha256: " + "AB" * 32 in installer
    assert "InstallerType: inno" in installer
    assert all("{{" not in p.read_text() for p in written)


@pytest.mark.parametrize(
    ("version", "url", "sha256", "message"),
    [
        ("v0.3", "https://example.org/x-setup.exe", "a" * 64, "not a version"),
        ("0.3.0", "http://example.org/x-setup.exe", "a" * 64, "HTTPS .exe"),
        ("0.3.0", "https://example.org/x.zip", "a" * 64, "HTTPS .exe"),
        ("0.3.0", "https://example.org/x-setup.exe", "a" * 63, "not a SHA-256"),
    ],
)
def test_winget_render_refuses_bad_values(
    winget: ModuleType, tmp_path: Path, version: str, url: str, sha256: str, message: str
) -> None:
    with pytest.raises(winget.WingetError, match=message):
        winget.render(version, url, sha256, tmp_path)


def test_signing_runs_only_on_tags_and_is_gated_on_its_settings() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")
    job = workflow[workflow.index("  sign-windows:") : workflow.index("  draft-release:")]
    assert "if: startsWith(github.ref, 'refs/tags/v')" in job
    assert "vars.SIGNING_PROVIDER" in job
    assert "::notice title=Signing is switched off::" in job
    assert "exit 0" in job, "missing settings leave a notice, never a failure"
    for step in ("Sign through SignPath Foundation", "Sign through Microsoft Artifact Signing"):
        block = job[job.index(step) :]
        assert block.splitlines()[1].strip().startswith("if: steps.gate.outputs.provider =="), step
    assert "secrets." not in job.replace("secrets.SIGNPATH_API_TOKEN", ""), "one secret only"


def test_every_signing_waits_for_the_maintainers_approval() -> None:
    """M2: each signing waits in the release-signing environment for its reviewer.

    The docs bind Artifact Signing's Azure login to that environment.
    """
    workflow = WORKFLOW.read_text(encoding="utf-8")
    job = workflow[
        workflow.index("  sign-windows:") : workflow.index(
            "  steps:", workflow.index("  sign-windows:")
        )
    ]
    assert "environment: release-signing" in job
    guide = (ROOT / "docs" / "dev" / "packaging.md").read_text(encoding="utf-8")
    assert "repo:inmymoonsuit/CADD-Calculator:environment:release-signing" in guide
    assert "required reviewer" in guide
    assert "tag ruleset" in guide, "Low 6: only the maintainer creates v* tags"


def test_the_dry_run_builds_and_tests_the_installer() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")
    assert '--installer"' in workflow
    assert "packaging/windows/test_installer.py" in workflow
    assert "packaging/windows/winget.py validate" in workflow
    assert "builds/generic/*-setup.exe" in workflow


@pytest.mark.skipif(os.name != "nt", reason="the installer test is Windows-only")
def test_the_installer_test_refuses_a_missing_installer(tmp_path: Path) -> None:
    tester = _load("test_installer", ROOT / "packaging" / "windows" / "test_installer.py")
    with pytest.raises((tester.InstallerTestError, FileNotFoundError, OSError)):
        tester.test_installer(tmp_path / "missing-setup.exe", tmp_path)
