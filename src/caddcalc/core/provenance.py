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
    """Computed from a built-in table. Reserved for materials (ADR-0013, phase 2)."""
    DEFAULT = "default"
    """The calculator parameter's own default."""


@dataclass(frozen=True)
class InputSource:
    """The provenance of one input value."""

    kind: SourceKind
    label: str = ""
    """Who supplied the value, e.g. ``"Sheet Metal settings"``. Empty for explicit and default."""
    domain: str | None = None
    """The domain id, when ``kind`` is ``DOMAIN``."""
    reference: Reference | None = None
    """The table and version a derived value came from (phase 2)."""

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
