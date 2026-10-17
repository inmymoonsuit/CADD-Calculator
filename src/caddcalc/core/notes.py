"""Notes a result carries beside its numbers: warnings, exceeded limits, missing values."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from caddcalc.core.reference import Reference


class NoteKind(Enum):
    """What a note tells the user. Front ends word and style each kind the same way."""

    WARNING = "warning"
    """Something to check before using the result."""
    LIMIT_EXCEEDED = "limit_exceeded"
    """An input or result is past a limit that a rule or a reference gives."""
    NO_APPLICABLE_VALUE = "no_applicable_value"
    """No reference value covers this case, so a check couldn't be made (ADR-0014)."""


@dataclass(frozen=True)
class Note:
    """One note on a result."""

    kind: NoteKind
    text: str
    """One or two sentences for users, in plain text."""
    reference: Reference | None = None
    """The source of the limit or rule behind the note, if it has one."""

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serialisable form. ``reference`` is ``None`` or its fields."""
        return {
            "kind": self.kind.value,
            "text": self.text,
            "reference": None if self.reference is None else self.reference.to_dict(),
        }
