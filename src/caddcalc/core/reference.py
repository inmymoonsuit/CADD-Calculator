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

    def __str__(self) -> str:
        return ", ".join(
            part for part in (self.title, self.edition, self.detail, self.locator) if part
        )

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
        }
