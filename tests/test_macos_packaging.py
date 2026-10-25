"""The macOS .dmg, the notarization stub, and the installing guide (slice d5).

CI builds the .dmg on macos-latest, mounts it, and starts the app from it; these check
what doesn't need a Mac: the workflow's steps and gates, and what the guide tells users.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "release.yml"
GUIDE = ROOT / "docs" / "user" / "installing.md"


def test_the_dmg_links_applications_and_is_smoke_tested_from_the_image() -> None:
    spec = importlib.util.spec_from_file_location(
        "make_dmg", ROOT / "packaging" / "macos" / "make_dmg.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    source = (ROOT / "packaging" / "macos" / "make_dmg.py").read_text(encoding="utf-8")
    assert 'symlink_to("/Applications")' in source
    assert '"-readonly"' in source and '"hdiutil", "detach"' in source.replace("\n", " ")
    assert module.VOLUME_NAME == "CADD Calculator"
    workflow = WORKFLOW.read_text(encoding="utf-8")
    assert "packaging/macos/make_dmg.py builds/generic/*-macos-*.app --smoke-test" in workflow
    assert "builds/generic/*.dmg" in workflow and "dist/*.dmg" in workflow


def test_notarization_is_a_stub_gated_off_on_tags_only() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")
    job = workflow[workflow.index("  notarize-macos:") : workflow.index("  linux-metadata:")]
    assert "if: startsWith(github.ref, 'refs/tags/v')" in job
    assert "environment: release-signing" in job
    assert "vars.MACOS_NOTARIZE" in job
    assert "::notice title=Notarization is switched off::" in job
    assert job.count("exit 0") == 2, "switched off, or missing a secret: a notice, not a failure"
    assert "Notarization isn't written yet" in job, "switched on, it fails until it's written"


def test_the_guide_says_the_app_is_unsigned_and_how_to_open_it() -> None:
    text = GUIDE.read_text(encoding="utf-8")
    assert "**The downloads aren't signed yet.**" in text
    assert "https://support.apple.com/en-us/102445" in text
    assert "click **Privacy & Security**, scroll down, and click\n   **Open Anyway**" in text
    assert "**Run anyway**" in text
    assert "smartscreen-reputation" in text
    assert "(docs/user/installing.md)" in (ROOT / "README.md").read_text(encoding="utf-8")
    assert "(installing.md)" in (ROOT / "docs" / "user" / "index.md").read_text(encoding="utf-8")
