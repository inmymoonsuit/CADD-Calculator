"""Each failing test as a GitHub Actions annotation, on the line that failed.

A job's log can be read only by a signed-in user, but a check run's annotations are
public through GitHub's API. So under GitHub Actions each failure is also printed as a
workflow command, ``::error file=…,line=…::…``, which GitHub makes an annotation of
(GitHub Docs, "Workflow commands for GitHub Actions": "Setting an error message").
``conftest.py`` registers the hook; it prints nothing elsewhere. GitHub keeps at most ten
annotations of a kind per step; the log has every failure.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest


def _data(text: str) -> str:
    """Escape a workflow command's message, as GitHub's toolkit does."""
    return text.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


def _property(text: str) -> str:
    """Escape a workflow command's property, such as its file."""
    return _data(text).replace(":", "%3A").replace(",", "%2C")


def _where(report: pytest.TestReport | pytest.CollectReport, root: Path) -> tuple[str, int]:
    """Return the project file and line a failure is at, relative to ``root``.

    That's the deepest frame of its traceback inside the project: the test's own line for
    a failed assert, or the project's line that raised. Without one, the test itself.
    """
    traceback = getattr(report.longrepr, "reprtraceback", None)
    for entry in reversed(getattr(traceback, "reprentries", [])):
        location = getattr(entry, "reprfileloc", None)
        if location is None:
            continue
        path = Path(location.path)
        path = (path if path.is_absolute() else Path.cwd() / path).resolve()
        if path.is_relative_to(root):
            return path.relative_to(root).as_posix(), location.lineno
    file, line, _name = report.location
    return Path(file).as_posix(), (line or 0) + 1


def annotation(report: pytest.TestReport | pytest.CollectReport, root: Path) -> str:
    """Return the ``::error`` workflow command for a failed test's report.

    The message is the exception's first line. A report with no exception, such as a
    fixture that isn't found at setup, gives its error on the first line marked "E ".
    """
    crash = getattr(report.longrepr, "reprcrash", None)
    if crash is not None:
        message = crash.message
    else:
        text = str(report.longrepr)
        marked = [line[1:].strip() for line in text.splitlines() if line.startswith("E ")]
        message = marked[0] if marked else text
    first = message.strip().splitlines()[0] if message.strip() else "failed"
    file, line = _where(report, root.resolve())
    return f"::error file={_property(file)},line={line}::{_data(f'{report.nodeid}: {first}')}"


def pytest_terminal_summary(terminalreporter: pytest.TerminalReporter) -> None:
    """Under GitHub Actions, annotate each failed test and each error."""
    if os.environ.get("GITHUB_ACTIONS") != "true":
        return
    root = terminalreporter.config.rootpath
    for kind in ("failed", "error"):
        for report in terminalreporter.stats.get(kind, []):
            if isinstance(report, pytest.TestReport | pytest.CollectReport):
                terminalreporter.write_line(annotation(report, root))
