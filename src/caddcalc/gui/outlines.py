"""How a field a note concerns is outlined: input and result fields alike (ADR-0017 §3).

A note names the inputs and outputs it concerns (``Note.subjects``). Each such field is
outlined by the strongest of its notes: a cited limit over a warning over a check that
couldn't be made, whose dashed outline reads as "unchecked". The roles, the styles, and
the one width every note outline shares are tokens (``ui_style``, ``note_outline``); the
ranking is here, so the input fields and the result fields can't disagree.

Standard library only.
"""

from __future__ import annotations

from collections.abc import Collection, Iterable
from dataclasses import dataclass

from caddcalc.core import Note, NoteKind
from caddcalc.gui.ui_style import NoteOutlineTokens, ui_style


@dataclass(frozen=True)
class Outline:
    """A field's outline: a palette role, a line style, and a width."""

    role: str
    style: str
    """``"solid"`` or ``"dashed"``."""
    width: float
    rank: int
    """How strong it is: a field several notes concern takes the strongest."""


def note_outline(kind: NoteKind, tokens: NoteOutlineTokens | None = None) -> Outline:
    """Return the outline for a field a note of ``kind`` concerns."""
    tokens = ui_style().note_outline if tokens is None else tokens
    if kind is NoteKind.LIMIT_EXCEEDED:
        return Outline(tokens.limit_role, tokens.limit_style, tokens.width, 3)
    if kind is NoteKind.NO_APPLICABLE_VALUE:
        return Outline(tokens.no_value_role, tokens.no_value_style, tokens.width, 1)
    return Outline(tokens.note_role, tokens.note_style, tokens.width, 2)  # warning, infeasible


def error_outline(tokens: NoteOutlineTokens | None = None) -> Outline:
    """Return the outline for an input whose text can't be read."""
    tokens = ui_style().note_outline if tokens is None else tokens
    return Outline(tokens.error_role, tokens.error_style, tokens.width, 4)


def strongest(
    notes: Iterable[Note], keys: Collection[str], tokens: NoteOutlineTokens | None = None
) -> dict[str, Outline]:
    """Return the strongest outline of each of ``keys`` that a note concerns.

    Args:
        notes: A result's notes.
        keys: The fields that can show an outline, by parameter or output key.
        tokens: The outline tokens; the shipped ones when ``None``.
    """
    outlines: dict[str, Outline] = {}
    for note in notes:
        outline = note_outline(note.kind, tokens)
        for key in note.subjects:
            if key in keys and (key not in outlines or outline.rank > outlines[key].rank):
                outlines[key] = outline
    return outlines
