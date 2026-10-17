"""Where each input value of a run came from (ADR-0013 §5)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from caddcalc.core.reference import Reference


class SourceKind(Enum):
    """Where an input value came from, in precedence order (ADR-0013 §4)."""

    EXPLICIT = "explicit"
    """Given for this run: a form field set to override, a CLI argument, or the API."""
    DOMAIN = "domain"
    """A domain setting the user has set."""
    DERIVED = "derived"
    """Computed from a built-in table, such as a gauge's thickness (ADR-0014)."""
    DEFAULT = "default"
    """The calculator parameter's own default."""


@dataclass(frozen=True)
class InputSource:
    """The provenance of one input value."""

    kind: SourceKind
    label: str = ""
    """Who supplied the value, e.g. ``"Sheet Metal settings"``.

    An explicit value may have one too, e.g. ``"course example"``; empty means typed or
    given plainly. A default has none.
    """
    domain: str | None = None
    """The domain id, when ``kind`` is ``DOMAIN`` or ``DERIVED``."""
    reference: Reference | None = None
    """The table and version a derived value came from; for a domain value, the citation
    of a starting value the user applied rather than typed (ADR-0014 M2)."""

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serialisable form. ``reference`` is ``None`` or its fields."""
        return {
            "kind": self.kind.value,
            "label": self.label,
            "domain": self.domain,
            "reference": None if self.reference is None else self.reference.to_dict(),
        }


EXPLICIT = InputSource(SourceKind.EXPLICIT)
"""The source of a value given for the run."""
DEFAULT = InputSource(SourceKind.DEFAULT)
"""The source of a parameter's own default."""
