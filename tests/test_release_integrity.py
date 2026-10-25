"""Checksums, attestations, PyPI Trusted Publishing, and pinned actions (slice d6).

CI runs the dry-run half (the wheel and sdist, the release files and SHA256SUMS); a tag
runs the rest. These check what a dry run can't: that only a tag attests, drafts, or
publishes, that each OIDC grant is in the one job that needs it, that nothing stores a
token, and what ``packaging/release_files.py`` does with a tag's files.
"""

from __future__ import annotations

import hashlib
import importlib.util
import re
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"
RELEASE = WORKFLOWS / "release.yml"
TAGS_ONLY = "if: startsWith(github.ref, 'refs/tags/v')"
VERSION = "0.1.0a1"


def _jobs() -> dict[str, str]:
    """Each job of release.yml by name, as its text."""
    text = RELEASE.read_text(encoding="utf-8")
    body = text[text.index("\njobs:\n") :]
    starts = [(m.group(1), m.start()) for m in re.finditer(r"^  ([a-z-]+):$", body, re.M)]
    ends = [start for _, start in starts[1:]] + [len(body)]
    return {name: body[start:end] for (name, start), end in zip(starts, ends, strict=True)}


@pytest.fixture(scope="module")
def release_files() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "release_files", ROOT / "packaging" / "release_files.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _downloads(folder: Path, version: str = VERSION) -> Path:
    """Fake build artifacts for every platform, named as the builds name them."""
    folder.mkdir()
    for name in (
        f"CADDCalculator-{version}-generic-windows-x64.zip",
        f"CADDCalculator-{version}-generic-windows-x64-setup.exe",
        f"CADDCalculator-{version}-generic-windows-x64.build.json",
        f"CADDCalculator-{version}-generic-linux-x64.tar.gz",
        f"CADDCalculator-{version}-generic-linux-x64.AppImage",
        f"CADDCalculator-{version}-generic-macos-arm64.zip",
        f"CADDCalculator-{version}-generic-macos-arm64.dmg",
        f"cadd_calculator-{version}-py3-none-any.whl",
        f"cadd_calculator-{version}.tar.gz",
    ):
        (folder / name).write_bytes(name.encode())
    return folder


def test_every_action_is_pinned_to_a_commit() -> None:
    for workflow in WORKFLOWS.glob("*.yml"):
        for line in workflow.read_text(encoding="utf-8").splitlines():
            if "uses:" in line:
                assert re.search(r"uses: [\w./-]+@[0-9a-f]{40}  # v\d", line), (workflow.name, line)
    dependabot = (ROOT / ".github" / "dependabot.yml").read_text(encoding="utf-8")
    assert "package-ecosystem: github-actions" in dependabot


def test_only_the_jobs_that_need_it_get_an_oidc_token() -> None:
    """S&R's d6 Low 2: dry runs hold no id-token or attestations write."""
    text = RELEASE.read_text(encoding="utf-8")
    assert "\npermissions:\n  contents: read\n" in text, "read-only by default"
    jobs = _jobs()
    with_oidc = {name for name, job in jobs.items() if "id-token: write" in job}
    assert with_oidc == {"sign-windows", "attest", "testpypi", "pypi"}
    assert all(TAGS_ONLY in jobs[name] for name in with_oidc)
    assert {name for name, job in jobs.items() if "attestations: write" in job} == {"attest"}
    assert "permissions:" not in jobs["release-files"]


def test_a_tags_run_is_never_cancelled() -> None:
    """S&R's mutant Y9: a newer push cancels a dry run, never a tag's run."""
    text = RELEASE.read_text(encoding="utf-8")
    assert "cancel-in-progress: ${{ !startsWith(github.ref, 'refs/tags/') }}" in text


def test_the_wheel_and_sdist_are_built_and_checked_on_every_run() -> None:
    job = _jobs()["python-dist"]
    assert "\n    if:" not in job, "a dry run builds them too"
    assert "uv build" in job
    assert "scripts/i18n.py check-wheel dist/*.whl" in job
    check = job[job.index("- name: Check the tag matches the version") :]
    assert check.splitlines()[1].strip() == TAGS_ONLY
    assert 'release_files.py check-tag "$GITHUB_REF_NAME" "$version"' in check


def test_the_release_carries_windows_and_linux_and_checks_its_sums() -> None:
    text = RELEASE.read_text(encoding="utf-8")
    assert "\nenv:\n" in text and "\n  RELEASE_PLATFORMS: Windows Linux\n" in text
    job = _jobs()["release-files"]
    assert "needs: [build, python-dist, linux-metadata, appimage-x11, sign-windows]" in job
    assert "needs.linux-metadata.result == 'success'" in job, "S&R Low 3"
    assert "needs.appimage-x11.result == 'success'" in job
    assert "\n    if: >-" in job and "refs/tags" not in job, "dry runs too"
    assert "release_files.py collect downloads release" in job
    assert '--platforms $RELEASE_PLATFORMS --signed signed --provider "$PROVIDER"' in job
    assert "PROVIDER: ${{ needs.sign-windows.outputs.provider }}" in job
    assert "sha256sum --check --strict SHA256SUMS" in job


def test_the_signed_installer_is_required_when_a_provider_signed() -> None:
    """S&R's d6 M2 and mutant Y10: no silent fallback to the unsigned installer."""
    jobs = _jobs()
    assert (
        "    outputs:\n      provider: ${{ steps.gate.outputs.provider }}" in jobs["sign-windows"]
    )
    job = jobs["release-files"]
    download = job[: job.index("name: CADDCalculator-signed-installer")]
    download = download[download.rindex("- uses: actions/download-artifact@") :]
    assert "if: needs.sign-windows.outputs.provider != ''" in download
    assert "continue-on-error" not in job


def test_only_a_tag_attests_and_drafts_a_pre_release() -> None:
    jobs = _jobs()
    attest = jobs["attest"]
    assert TAGS_ONLY in attest and "needs: release-files" in attest
    assert "uses: actions/attest@" in attest
    assert "subject-checksums: release/SHA256SUMS" in attest
    draft = jobs["draft-release"]
    assert TAGS_ONLY in draft
    assert "needs: [release-files, attest]" in draft
    assert "--draft $prerelease" in draft and "release/*" in draft
    assert 'release_files.py prerelease "$GITHUB_REF_NAME"' in draft


def test_pypi_publishing_is_off_tags_only_testpypi_first_and_tokenless() -> None:
    jobs = _jobs()
    test, real = jobs["testpypi"], jobs["pypi"]
    gate = "if: startsWith(github.ref, 'refs/tags/v') && vars.PUBLISH_PYPI == 'true'"
    for job, environment in ((test, "testpypi"), (real, "pypi")):
        assert gate in job, "switched off until the maintainer sets PUBLISH_PYPI"
        assert f"    environment:\n      name: {environment}\n" in job
        assert "uses: pypa/gh-action-pypi-publish@" in job
        assert "permissions:\n      id-token: write\n" in job
        assert "password" not in job and "secrets." not in job, "Trusted Publishing: no token"
    assert "repository-url: https://test.pypi.org/legacy/" in test
    assert "repository-url" not in real
    assert "needs: testpypi" in real, "PyPI only after TestPyPI succeeds"


def test_collect_takes_the_chosen_platforms_and_writes_sha256sums(
    release_files: ModuleType, tmp_path: Path
) -> None:
    downloads = _downloads(tmp_path / "downloads")
    files = release_files.collect(downloads, tmp_path / "release", VERSION, ["Windows", "Linux"])
    names = sorted(p.name for p in files)
    assert names == [
        f"CADDCalculator-{VERSION}-generic-linux-x64.AppImage",
        f"CADDCalculator-{VERSION}-generic-linux-x64.tar.gz",
        f"CADDCalculator-{VERSION}-generic-windows-x64-setup.exe",
        f"CADDCalculator-{VERSION}-generic-windows-x64.zip",
    ], "no macOS, no Python files, no build reports"
    sums = (tmp_path / "release" / "SHA256SUMS").read_text(encoding="utf-8").splitlines()
    assert sums == [f"{hashlib.sha256(n.encode()).hexdigest()}  {n}" for n in names]


def test_collect_fails_on_a_missing_file_or_another_version(
    release_files: ModuleType, tmp_path: Path
) -> None:
    """S&R's mutant Y8: a missing kind fails the release."""
    downloads = _downloads(tmp_path / "downloads")
    (downloads / f"CADDCalculator-{VERSION}-generic-linux-x64.AppImage").unlink()
    with pytest.raises(release_files.ReleaseError, match=r"Linux: expected one .*AppImage"):
        release_files.collect(downloads, tmp_path / "r1", VERSION, ["Windows", "Linux"])
    with pytest.raises(release_files.ReleaseError, match=r"isn't version 0.1.0a10"):
        release_files.collect(downloads, tmp_path / "r2", "0.1.0a10", ["Windows"])
    with pytest.raises(release_files.ReleaseError, match="unknown platforms"):
        release_files.collect(downloads, tmp_path / "r3", VERSION, ["Android"])
    assert (
        release_files.main(
            [
                "collect",
                str(downloads),
                str(tmp_path / "r4"),
                "--version",
                VERSION,
                "--platforms",
                "Linux",
            ]
        )
        == 1
    )


def test_collect_requires_the_signed_installer_when_a_provider_signed(
    release_files: ModuleType, tmp_path: Path
) -> None:
    """S&R's d6 M2: signing ran, so the signed installer must replace the unsigned one."""
    downloads = _downloads(tmp_path / "downloads")
    signed = tmp_path / "signed"
    signed.mkdir()
    with pytest.raises(release_files.ReleaseError, match="signpath signed the installer"):
        release_files.collect(downloads, tmp_path / "r1", VERSION, ["Windows"], signed, "signpath")
    installer = f"CADDCalculator-{VERSION}-generic-windows-x64-setup.exe"
    (signed / installer).write_bytes(b"signed")
    release_files.collect(downloads, tmp_path / "r2", VERSION, ["Windows"], signed, "signpath")
    assert (tmp_path / "r2" / installer).read_bytes() == b"signed"
    assert hashlib.sha256(b"signed").hexdigest() in (tmp_path / "r2" / "SHA256SUMS").read_text()
    # Switched off: the unsigned installer, and a stray signed folder is ignored.
    release_files.collect(downloads, tmp_path / "r3", VERSION, ["Windows"], signed, "")
    assert (tmp_path / "r3" / installer).read_bytes() == installer.encode()


def test_the_tag_must_match_the_version_and_pre_releases_are_marked(
    release_files: ModuleType,
) -> None:
    release_files.check_tag("v0.1.0a1", "0.1.0a1")
    with pytest.raises(release_files.ReleaseError, match="doesn't match"):
        release_files.check_tag("v0.1.0", "0.1.0a1")
    for tag in ("v0.1.0a1", "v1.0b2", "v2.0.0rc1", "v0.2.dev3"):
        assert release_files.is_prerelease(tag), tag
    for tag in ("v0.1.0", "v1.2", "v1.0.post1", "latest"):
        assert not release_files.is_prerelease(tag), tag


def test_the_version_has_one_source_that_a_tag_must_match(release_files: ModuleType) -> None:
    """The app, its builds, and the wheel all take caddcalc.__version__; a tag must match it."""
    import caddcalc

    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert '[tool.hatch.version]\npath = "src/caddcalc/__init__.py"' in pyproject
    release_files.check_tag(f"v{caddcalc.__version__}", caddcalc.__version__)


def test_the_docs_give_the_one_time_setup_and_no_longer_promise() -> None:
    guide = (ROOT / "docs" / "dev" / "packaging.md").read_text(encoding="utf-8")
    pypi = guide[guide.index("## PyPI\n") : guide.index("## winget\n")]
    assert "pending publisher" in pypi
    assert "workflow `release.yml`, environment `pypi` (on TestPyPI,\n   `testpypi`)" in pypi
    assert "required reviewer" in pypi
    assert "`PUBLISH_PYPI`" in pypi
    policy = (ROOT / "docs" / "user" / "code-signing.md").read_text(encoding="utf-8")
    assert "being added" not in policy and "will attach" not in policy
    assert "each release attaches a `SHA256SUMS` file" in policy
