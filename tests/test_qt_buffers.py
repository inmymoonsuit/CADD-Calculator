"""Qt buffers outlive their reads: no pixels are read from a temporary image."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEMPORARY_BITS = re.compile(r"\)\s*\.(?:const)?[Bb]its\(")
"""``constBits()`` or ``bits()`` straight on a call's result, such as a copy."""


def test_pixels_are_never_read_from_a_temporary_image() -> None:
    """A temporary QImage can be freed, and its buffer reused, before its bytes are copied.

    That failed only on Linux, so the image must be held in a name first:
    ``under = image.copy(rect)``, then ``bytes(under.constBits())`` (ADR-0016, amendments).
    """
    found = [
        f"{path.relative_to(ROOT)}:{number}"
        for folder in ("src", "tests")
        for path in sorted((ROOT / folder).rglob("*.py"))
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1)
        if TEMPORARY_BITS.search(line)
    ]
    assert found == [], found
