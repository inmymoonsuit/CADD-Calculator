"""Choices a domain offers, such as a gauge, and the values they derive (ADR-0014 §2).

A choice never enters a formula. The domain's resolver turns the user's selections into
derived numeric values for its settings, which calculators take as their **derived**
inputs (ADR-0013 §4), so calculators, formulas, and the CLI stay numeric.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Protocol

from caddcalc.core.errors import SpecError
from caddcalc.core.notes import Note
from caddcalc.core.provenance import InputSource, SourceKind
from caddcalc.core.steps import Step
from caddcalc.core.units import TypedValue

OPTION_KEY = re.compile(r"[a-z][a-z0-9_]*:[a-z0-9_]+")
"""The grammar of option keys, e.g. ``"msg:12"``: a group id, a colon, and an item id."""


@dataclass(frozen=True)
class Option:
    """One option of a choice.

    Its ``key`` is public and stable: saved sessions, scripts, and tests name an option by
    it. A compound key, such as ``"msg:12"`` for 12 gauge in Manufacturers' Standard, keeps
    a bare item (a gauge number without its system) unrepresentable.
    """

    key: str
    label: str
    """How the option reads, e.g. ``"12 ga"``."""
    group: str = ""
    """The group it belongs to, e.g. ``"Manufacturers' Standard"``, so a front end can show
    two levels."""


@dataclass(frozen=True)
class Choice:
    """A selection a domain offers its users, such as a gauge."""

    key: str
    """Stable identifier, e.g. ``"gauge"``."""
    label: str
    help: str = ""
    default: str | None = None
    """The option key selected until the user chooses, or ``None`` for no selection.

    For a dependent choice it applies only where the parents' selections offer it.
    """
    depends_on: tuple[str, ...] = ()
    """Keys of the choices whose selections decide this one's options, e.g. a temper
    depends on the material. A parent change clears a selection it no longer offers.
    """


@dataclass(frozen=True)
class DerivedValue:
    """A value a selection gives one domain setting.

    Raises:
        SpecError: The source isn't a derived one or doesn't name its table (a
            ``reference``), ``stated`` or ``work`` doesn't equal ``value``, or the note
            already has subjects. A resolver that builds such a value has a bug.
    """

    value: float
    """The value, in base units."""
    source: InputSource
    """Where it came from, e.g. ``"12 ga, Manufacturers' Standard (nominal)"`` and the table."""
    stated: TypedValue | None = None
    """The value as its source states it, when it does."""
    note: Note | None = None
    """A note that results carry whenever this value is used, such as a nominal caution.

    It has no subjects: ``Calculator.run`` names the inputs that took the value.
    """
    work: Step | None = None
    """How the value was derived, shown ahead of the calculator's work whenever the value
    is used. ``Calculator.run`` gives it the symbol of the input that took the value."""

    def __post_init__(self) -> None:
        if self.source.kind is not SourceKind.DERIVED:
            raise SpecError(f"A derived value needs a derived source, not {self.source.kind}")
        if self.source.reference is None:
            raise SpecError(
                f"Derived value {self.source.label!r} must name its table and version (ADR-0014 §1)"
            )
        if self.stated is not None and self.stated.value != self.value:
            raise SpecError(f"Stated value {self.stated.text!r} doesn't equal {self.value!r}")
        if self.work is not None and self.work.value != self.value:
            raise SpecError(
                f"The work of derived value {self.source.label!r} gives {self.work.value!r}, "
                f"not {self.value!r}"
            )
        if self.note is not None and self.note.subjects:
            raise SpecError(
                f"The note of derived value {self.source.label!r} has subjects; run() names "
                "the inputs that take the value"
            )


class ChoiceResolver(Protocol):
    """Supplies a domain's options and turns selections into derived values.

    A result carries a derived value's note only when one of its inputs uses that value,
    so every ``DerivedValue`` a caution applies to must carry the note itself.
    """

    def options(self, choice: str, selections: Mapping[str, str]) -> Sequence[Option]:
        """Return the options of ``choice``, in display order.

        Args:
            choice: The choice key.
            selections: The selections of the choices it depends on
                (``Choice.depends_on``) and no others. A parent without a selection is
                absent.
        """

    def derive(self, selections: Mapping[str, str]) -> Mapping[str, DerivedValue]:
        """Return the values ``selections`` give, by setting key.

        Args:
            selections: The selected option key for each choice that has a selection.
        """
