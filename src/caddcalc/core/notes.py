"""Notes a result carries beside its numbers: warnings, cited limits, gaps, impossibilities."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from enum import Enum
from string import Formatter
from types import MappingProxyType
from typing import Any

from caddcalc.core.errors import SpecError
from caddcalc.core.reference import Reference
from caddcalc.core.units import BASE_UNITS, Dimension, base_text

Quantity = tuple[float, Dimension]
"""A value in base units, and what it measures."""


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


def _field_names(template: str) -> list[str | None]:
    """Return the replacement fields of ``template``; ``""`` for a positional one."""
    return [name for _text, name, _spec, _conv in Formatter().parse(template) if name is not None]


@dataclass(frozen=True)
class Note:
    """One note on a result: a lead, an optional detail, and its sources (ADR-0017 F1).

    A note that names values or data phrases writes them as named fields, such as
    ``"inside radius {R} is below {minimum}"``, filled when it's shown: ``quantities``
    in the front end's display units, ``phrases`` as they are. The note's text never
    holds a formatted number, so it reads in the user's units, and a translation can
    reorder the fields. A note with neither is plain text, braces and all.

    Raises:
        SpecError: A ``LIMIT_EXCEEDED`` note cites no reference, so "limit" would not mean a
            cited limit; or a field is positional, unnamed by ``quantities`` or
            ``phrases``, or named by both. The code that makes such a note is a calculator
            or domain bug.
    """

    kind: NoteKind
    text: str
    """The lead: one sentence for users that leads with the verdict, in plain text."""
    references: tuple[Reference, ...] = ()
    """The sources of the limit or rule behind the note; every one, when they disagree."""
    subjects: tuple[str, ...] = ()
    """The parameter or output keys the note concerns."""
    detail: str = ""
    """What follows the lead, if anything: what each source gives, and how a check decided."""
    quantities: Mapping[str, Quantity] = field(default_factory=dict, hash=False)
    """The values the text's fields name, in base units, e.g. ``{"R": (1.27, LENGTH)}``."""
    phrases: Mapping[str, str] = field(default_factory=dict, hash=False)
    """The data phrases the text's fields name, as written, e.g. ``{"material": ...}``."""

    def __post_init__(self) -> None:
        if self.kind is NoteKind.LIMIT_EXCEEDED and not self.references:
            raise SpecError(f"A limit-exceeded note must cite its limit: {self.text!r}")
        object.__setattr__(self, "quantities", MappingProxyType(dict(self.quantities)))
        object.__setattr__(self, "phrases", MappingProxyType(dict(self.phrases)))
        both = self.quantities.keys() & self.phrases.keys()
        if both:
            raise SpecError(f"Note fields {sorted(both)} are both quantities and phrases")
        if not self.has_fields:
            return
        known = self.quantities.keys() | self.phrases.keys()
        for template in (self.text, self.detail):
            try:
                names = _field_names(template)
            except ValueError as exc:
                raise SpecError(f"Note text {template!r} isn't a template: {exc}") from None
            for name in names:
                if not name:
                    raise SpecError(f"Note text {template!r} has an unnamed field")
                if name not in known:
                    raise SpecError(f"Note text {template!r} names {name!r}, which isn't given")

    @property
    def has_fields(self) -> bool:
        """Whether the text and detail are templates with fields to fill."""
        return bool(self.quantities or self.phrases)

    def fill(self, template: str, show: Callable[[float, Dimension], str]) -> str:
        """Return ``template``, the note's text or detail, with its fields filled.

        Args:
            template: ``text`` or ``detail``.
            show: Writes a base-unit value as text, e.g. in the display units.
        """
        if not self.has_fields:
            return template
        values = {name: show(*quantity) for name, quantity in self.quantities.items()}
        return template.format_map({**values, **self.phrases})

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serialisable form, with ``references`` and ``subjects`` as lists.

        ``text`` and ``detail`` are filled in base units, as the rest of the JSON is, and
        ``quantities`` gives each named value in base units with its unit.
        """
        return {
            "kind": self.kind.value,
            "text": self.fill(self.text, base_text),
            "detail": self.fill(self.detail, base_text),
            "quantities": {
                name: {"value": value, "unit": BASE_UNITS[dim], "dimension": dim.value}
                for name, (value, dim) in self.quantities.items()
            },
            "references": [reference.to_dict() for reference in self.references],
            "subjects": list(self.subjects),
        }
