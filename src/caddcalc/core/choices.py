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
    """The option key selected until the user chooses, or ``None`` for no selection."""


@dataclass(frozen=True)
class DerivedValue:
    """A value a selection gives one domain setting.

    Raises:
        SpecError: The source isn't a derived one, or ``stated`` doesn't equal ``value``.
            A resolver that builds such a value has a bug.
    """

    value: float
    """The value, in base units."""
    source: InputSource
    """Where it came from, e.g. ``"12 ga, Manufacturers' Standard (nominal)"`` and the table."""
    stated: TypedValue | None = None
    """The value as its source states it, when it does."""
    note: Note | None = None
    """A note that results carry whenever this value is used, such as a nominal caution."""

    def __post_init__(self) -> None:
        if self.source.kind is not SourceKind.DERIVED:
            raise SpecError(f"A derived value needs a derived source, not {self.source.kind}")
        if self.stated is not None and self.stated.value != self.value:
            raise SpecError(f"Stated value {self.stated.text!r} doesn't equal {self.value!r}")


class ChoiceResolver(Protocol):
    """Supplies a domain's options and turns selections into derived values."""

    def options(self, choice: str) -> Sequence[Option]:
        """Return the options of ``choice``, in display order."""

    def derive(self, selections: Mapping[str, str]) -> Mapping[str, DerivedValue]:
        """Return the values ``selections`` give, by setting key.

        Args:
            selections: The selected option key for each choice that has a selection.
        """
