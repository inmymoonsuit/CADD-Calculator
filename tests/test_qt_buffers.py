"""Qt buffers outlive their reads: no pixels are read from a temporary image."""

from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FOLDERS = ("src", "tests", "packaging", "scripts")
PIXEL_READS = frozenset({"bits", "constBits", "scanLine", "constScanLine"})
"""The QImage methods that return a view into the image's own buffer."""


def temporary_reads(source: str) -> list[int]:
    """Return the lines that read pixels straight from a call's result.

    That's ``image.copy(rect).constBits()``, or the unbound form
    ``QImage.constBits(image.copy(rect))``: nothing holds the temporary image, so its
    buffer can be freed, and reused, before the bytes are read.
    """
    lines = []
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr not in PIXEL_READS:
            continue
        receiver = node.func.value
        bound = isinstance(receiver, ast.Call)
        on_class = (isinstance(receiver, ast.Name) and receiver.id == "QImage") or (
            isinstance(receiver, ast.Attribute) and receiver.attr == "QImage"
        )
        unbound = on_class and bool(node.args) and isinstance(node.args[0], ast.Call)
        if bound or unbound:
            lines.append(node.lineno)
    return lines


def test_the_check_finds_both_forms_and_passes_a_held_image() -> None:
    assert temporary_reads("data = bytes(shown.copy(area).constBits())") == [1]
    assert temporary_reads("row = QImage.scanLine(image.copy(area), 0)") == [1]
    assert temporary_reads("row = QtGui.QImage.bits(image.copy(area))") == [1]
    assert temporary_reads("under = shown.copy(area)\ndata = bytes(under.constBits())") == []
    assert temporary_reads("line = image.constScanLine(height())") == []


def test_pixels_are_never_read_from_a_temporary_image() -> None:
    """A temporary QImage can be freed before its bytes are copied; it failed on Linux.

    So the image is held in a name first (ADR-0016, amendments).
    """
    found = [
        f"{path.relative_to(ROOT)}:{line}"
        for folder in FOLDERS
        for path in sorted((ROOT / folder).rglob("*.py"))
        for line in temporary_reads(path.read_text(encoding="utf-8"))
    ]
    assert found == [], found
