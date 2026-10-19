"""Failing tests read as GitHub Actions annotations, without the job's log (ci_annotations.py)."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

FAILING = """\
import json


def test_asserts():
    value = "a"
    assert value == "b", "100% wrong: on purpose"


def test_raises_outside():
    json.loads("{")


def test_passes():
    pass


def test_needs_a_missing_fixture(nowhere):
    pass
"""


def _run(tmp_path: Path, github: bool) -> list[str]:
    """Run pytest on ``FAILING`` with the hook, and return the lines it printed."""
    (tmp_path / "test_sample.py").write_text(FAILING, encoding="utf-8")
    env = {k: v for k, v in os.environ.items() if k != "GITHUB_ACTIONS"}
    if github:
        env["GITHUB_ACTIONS"] = "true"
    env["PYTHONPATH"] = os.pathsep.join([str(ROOT), env.get("PYTHONPATH", "")])
    done = subprocess.run(  # noqa: S603  # this interpreter, on a test the test wrote
        [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "-p",
            "no:cacheprovider",
            "-p",
            "tests.ci_annotations",
            "--rootdir",
            str(tmp_path),
            str(tmp_path / "test_sample.py"),
        ],
        capture_output=True,
        text=True,
        timeout=120,
        env=env,
        cwd=tmp_path,
        check=False,
    )
    assert done.returncode == 1, done.stdout + done.stderr
    return done.stdout.splitlines()


def test_each_failure_is_an_annotation_on_its_line(tmp_path: Path) -> None:
    """The failed assert's own line; for a raise outside the project, the test's line.

    A setup error with no exception, a missing fixture, gives its "E " line.
    """
    lines = [line for line in _run(tmp_path, github=True) if line.startswith("::error ")]
    assert lines == [
        "::error file=test_sample.py,line=6::test_sample.py::test_asserts: "
        "AssertionError: 100%25 wrong: on purpose",
        "::error file=test_sample.py,line=10::test_sample.py::test_raises_outside: "
        "json.decoder.JSONDecodeError: Expecting property name enclosed in double quotes: "
        "line 1 column 2 (char 1)",
        "::error file=test_sample.py,line=17::test_sample.py::test_needs_a_missing_fixture: "
        "fixture 'nowhere' not found",
    ]


def test_no_annotation_outside_github_actions(tmp_path: Path) -> None:
    """Elsewhere the hook prints nothing."""
    assert not [line for line in _run(tmp_path, github=False) if line.startswith("::")]
