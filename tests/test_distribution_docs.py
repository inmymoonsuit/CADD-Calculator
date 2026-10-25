"""The distribution docs say what ADR-0022 and SignPath's conditions ask of them (slice d1).

The code-signing policy page states who builds, the roles, the review before a release,
MFA, how to check a download, and privacy; the README and the user guide link it; and
every research claim behind ADR-0022 names a source and the date it was checked.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).parents[1]
POLICY = ROOT / "docs" / "user" / "code-signing.md"
RESEARCH = ROOT / "docs" / "dev" / "research" / "distribution.md"
ADR = ROOT / "docs" / "dev" / "decisions" / "0022-distribution-and-signing.md"


def _sections(path: Path) -> set[str]:
    return {
        line.lstrip("#").strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.startswith("## ")
    }


def test_the_policy_page_is_titled_as_signpath_asks() -> None:
    """SignPath's condition 15: the term "Code signing policy" names the page."""
    assert POLICY.read_text(encoding="utf-8").splitlines()[0] == "# Code signing policy"


def test_the_policy_page_states_each_thing_signpath_asks_for() -> None:
    sections = _sections(POLICY)
    for wanted in (
        "Who builds",
        "Who does what",
        "The review before a release",
        "Accounts",
        "Checking a download",
        "Privacy",
        "Removing the app",
    ):
        assert wanted in sections, wanted
    text = POLICY.read_text(encoding="utf-8")
    for role in ("Authors", "Reviewers", "Approvers"):
        assert f"| {role} |" in text, role
    assert "GitHub-hosted runners" in text
    assert "multi-factor authentication" in text
    assert "gh attestation verify" in text
    assert "makes no network calls" in text


def test_the_readme_and_the_user_guide_link_the_policy() -> None:
    assert "(docs/user/code-signing.md)" in (ROOT / "README.md").read_text(encoding="utf-8")
    index = (ROOT / "docs" / "user" / "index.md").read_text(encoding="utf-8")
    assert "(code-signing.md)" in index


def test_every_research_claim_names_a_source() -> None:
    """Each row of the claims table links at least one HTTPS source."""
    rows = [
        line
        for line in RESEARCH.read_text(encoding="utf-8").splitlines()
        if re.match(r"\| [A-Z]\d \|", line)
    ]
    assert len(rows) >= 14, "every claim in ADR-0022 has a row"
    for row in rows:
        assert "](https://" in row, row[:40]


def test_the_research_says_when_it_was_checked_and_the_adr_points_to_it() -> None:
    assert re.search(r"checked on \*\*\d{4}-\d{2}-\d{2}\*\*", RESEARCH.read_text(encoding="utf-8"))
    adr = ADR.read_text(encoding="utf-8")
    assert "(../research/distribution.md)" in adr
    assert "## Amendment (2026-10-25)" in adr
