"""Checksums, attestations, PyPI Trusted Publishing, and pinned actions (slice d6).

CI runs the dry-run half (the wheel and sdist, SHA256SUMS); a tag runs the rest. These
check what a dry run can't: that only a tag attests or publishes, that each OIDC grant is
in the one job that needs it, and that nothing stores a token.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"
RELEASE = WORKFLOWS / "release.yml"
TAGS_ONLY = "if: startsWith(github.ref, 'refs/tags/v')"


def _jobs() -> dict[str, str]:
    """Each job of release.yml by name, as its text."""
    text = RELEASE.read_text(encoding="utf-8")
    body = text[text.index("\njobs:\n") :]
    starts = [(m.group(1), m.start()) for m in re.finditer(r"^  ([a-z-]+):$", body, re.M)]
    ends = [start for _, start in starts[1:]] + [len(body)]
    return {name: body[start:end] for (name, start), end in zip(starts, ends, strict=True)}


def test_every_action_is_pinned_to_a_commit() -> None:
    for workflow in WORKFLOWS.glob("*.yml"):
        for line in workflow.read_text(encoding="utf-8").splitlines():
            if "uses:" in line:
                assert re.search(r"uses: [\w./-]+@[0-9a-f]{40}  # v\d", line), (workflow.name, line)
    dependabot = (ROOT / ".github" / "dependabot.yml").read_text(encoding="utf-8")
    assert "package-ecosystem: github-actions" in dependabot


def test_only_the_jobs_that_need_it_get_an_oidc_token() -> None:
    text = RELEASE.read_text(encoding="utf-8")
    assert "\npermissions:\n  contents: read\n" in text, "read-only by default"
    jobs = _jobs()
    with_oidc = {name for name, job in jobs.items() if "id-token: write" in job}
    assert with_oidc == {"sign-windows", "release-files", "testpypi", "pypi"}
    assert {name for name, job in jobs.items() if "attestations: write" in job} == {"release-files"}


def test_the_wheel_and_sdist_are_built_and_checked_on_every_run() -> None:
    job = _jobs()["python-dist"]
    assert "\n    if:" not in job, "a dry run builds them too"
    assert "uv build" in job
    assert "scripts/i18n.py check-wheel dist/*.whl" in job
    assert "name: python-dist" in job


def test_sha256sums_covers_every_release_file_and_only_a_tag_attests() -> None:
    job = _jobs()["release-files"]
    assert "needs: [build, python-dist, sign-windows]" in job
    assert "\n    if: >-" in job and "refs/tags" not in job.split("steps:")[0], "dry runs too"
    for kind in (".zip", ".tar.gz", "-setup.exe", ".AppImage", ".dmg", ".whl"):
        assert f"downloads/*{kind}" in job, kind
    assert "for kind in .zip .tar.gz -setup.exe .AppImage .dmg .whl; do" in job
    assert "signed/*-setup.exe" in job, "the signed installer replaces the unsigned one"
    assert "sha256sum -- * > SHA256SUMS" in job
    assert "sha256sum --check --strict SHA256SUMS" in job
    attest = job[job.index("- name: Attest every release file") :]
    assert attest.splitlines()[1].strip() == TAGS_ONLY
    assert "uses: actions/attest@" in attest
    assert "subject-checksums: release/SHA256SUMS" in attest


def test_the_draft_release_attaches_the_checksummed_files() -> None:
    job = _jobs()["draft-release"]
    assert TAGS_ONLY in job
    assert "needs: release-files" in job
    assert "--draft" in job and "release/*" in job


def test_pypi_publishing_is_tags_only_testpypi_first_and_tokenless() -> None:
    jobs = _jobs()
    test, real = jobs["testpypi"], jobs["pypi"]
    for job, environment in ((test, "testpypi"), (real, "pypi")):
        assert TAGS_ONLY in job
        assert f"    environment:\n      name: {environment}\n" in job
        assert "uses: pypa/gh-action-pypi-publish@" in job
        assert "permissions:\n      id-token: write\n" in job
        assert "password" not in job and "secrets." not in job, "Trusted Publishing: no token"
    assert "repository-url: https://test.pypi.org/legacy/" in test
    assert "repository-url" not in real
    assert "needs: testpypi" in real, "PyPI only after TestPyPI succeeds"


def test_the_docs_give_the_one_time_setup_and_no_longer_promise() -> None:
    guide = (ROOT / "docs" / "dev" / "packaging.md").read_text(encoding="utf-8")
    pypi = guide[guide.index("## PyPI\n") : guide.index("## winget\n")]
    assert "pending publisher" in pypi
    assert "workflow `release.yml`, environment `pypi` (on TestPyPI,\n   `testpypi`)" in pypi
    assert "required reviewer" in pypi
    policy = (ROOT / "docs" / "user" / "code-signing.md").read_text(encoding="utf-8")
    assert "being added" not in policy and "will attach" not in policy
    assert "each release attaches a `SHA256SUMS` file" in policy
