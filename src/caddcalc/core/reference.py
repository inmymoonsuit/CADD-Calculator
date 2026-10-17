"""Citations for methods, domains, and derived values."""

from __future__ import annotations

import datetime
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Reference:
    """A citation. Cite edition, section, and page. Do not copy copyrighted text or tables.

    The structured fields after ``url`` are optional. Reference data requires them
    (ADR-0014 §1); a method's citation may keep its edition and page in ``title`` and
    ``detail``.
    """

    title: str
    detail: str = ""
    url: str = ""
    edition: str = ""
    """E.g. ``"29th ed."``."""
    locator: str = ""
    """Where in the work: a table, figure, or page, e.g. ``"Table 2, printed p. 2608"``."""
    accessed: datetime.date | None = None
    """When the source was consulted."""
    scope: str = ""
    """The practice the source describes, e.g. ``"aerospace bench practice"``."""
    short_title: str = ""
    """How a label or a note's text names the work, e.g. ``"FAA-H-8083-31B"``."""

    def __str__(self) -> str:
        # The locator comes before the detail, which narrows it, e.g. a chapter or a step.
        return ", ".join(
            part for part in (self.title, self.edition, self.locator, self.detail) if part
        )

    @property
    def short(self) -> str:
        """The citation as a label names it, e.g. ``"FAA-H-8083-31B, p. 4-63"``.

        That is the short title and the locator, or the full citation when there's no
        short title.
        """
        if not self.short_title:
            return str(self)
        return ", ".join(part for part in (self.short_title, self.locator) if part)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serialisable form; ``accessed`` is an ISO date or ``None``."""
        return {
            "title": self.title,
            "detail": self.detail,
            "url": self.url,
            "edition": self.edition,
            "locator": self.locator,
            "accessed": None if self.accessed is None else self.accessed.isoformat(),
            "scope": self.scope,
            "short_title": self.short_title,
        }
