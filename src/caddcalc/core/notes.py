"""Notes a result carries beside its numbers: warnings, cited limits, gaps, impossibilities."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from caddcalc.core.errors import SpecError
from caddcalc.core.reference import Reference


class NoteKind(Enum):
    """What a note tells the user. Front ends word and style each kind the same way."""

    WARNING = "warning"
    """Something to check before using the result, such as a rule of thumb."""
    LIMIT_EXCEEDED = "limit_exceeded"
    """An input or result is past a limit a cited source states; it always has a reference."""
    NO_APPLICABLE_VALUE = "no_applicable_value"
    """No reference value covers this case, so a check couldn't be made (ADR-0014)."""
    INFEASIBLE = "infeasible"
    """The inputs describe something that can't be made. The numbers are still shown."""


@dataclass(frozen=True)
class Note:
    """One note on a result.

    Raises:
        SpecError: A ``LIMIT_EXCEEDED`` note cites no reference, so "limit" would not mean a
            cited limit. The code that makes such a note is a calculator or domain bug.
    """

    kind: NoteKind
    text: str
    """One or two sentences for users, in plain text."""
    references: tuple[Reference, ...] = ()
    """The sources of the limit or rule behind the note; every one, when they disagree."""
    subjects: tuple[str, ...] = ()
    """The parameter or output keys the note concerns."""

    def __post_init__(self) -> None:
        if self.kind is NoteKind.LIMIT_EXCEEDED and not self.references:
            raise SpecError(f"A limit-exceeded note must cite its limit: {self.text!r}")

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serialisable form, with ``references`` and ``subjects`` as lists."""
        return {
            "kind": self.kind.value,
            "text": self.text,
            "references": [reference.to_dict() for reference in self.references],
            "subjects": list(self.subjects),
        }
