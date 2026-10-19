"""The user guides read as the app is: their links resolve, and no retired word is left.

ADR-0024's U4: no guide mentions the Units box, a unit typed into a field as a way to
give one, or the removed ``--units`` and ``--fraction`` options.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[1]
GUIDES = [*sorted((ROOT / "docs" / "user").rglob("*.md")), ROOT / "README.md"]
LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
RETIRED = (
    re.compile(r"units\W{0,4}box", re.IGNORECASE),
    re.compile(r"\*\*Units\*\*"),
    re.compile(r"--units\b"),
    re.compile(r"--fraction\b"),
    re.compile(r"display unit", re.IGNORECASE),
    re.compile(r"unit system", re.IGNORECASE),
)


def _anchors(text: str) -> set[str]:
    """Each heading's anchor, as GitHub writes it."""
    found = set()
    for line in text.splitlines():
        if line.startswith("#"):
            title = line.lstrip("#").strip().lower()
            found.add(re.sub(r"[^\w\- ]", "", title).replace(" ", "-"))
    return found


@pytest.mark.parametrize("guide", GUIDES, ids=lambda p: str(p.relative_to(ROOT)))
def test_every_link_resolves(guide: Path) -> None:
    for target in LINK.findall(guide.read_text(encoding="utf-8")):
        if target.startswith(("http://", "https://", "mailto:")):
            continue
        path, _hash, anchor = target.partition("#")
        linked = (guide.parent / path).resolve() if path else guide
        assert linked.exists(), f"{guide.name} links to {target}, which isn't there"
        if anchor and linked.suffix == ".md":
            assert anchor in _anchors(linked.read_text(encoding="utf-8")), (guide.name, target)


@pytest.mark.parametrize("guide", GUIDES, ids=lambda p: str(p.relative_to(ROOT)))
def test_no_guide_uses_a_retired_word(guide: Path) -> None:
    text = guide.read_text(encoding="utf-8")
    for word in RETIRED:
        assert not word.search(text), f"{guide.name}: {word.pattern}"
