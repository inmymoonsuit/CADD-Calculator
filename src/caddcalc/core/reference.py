"""Citations for methods, domains, and derived values."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Reference:
    """A citation. Cite edition, section, and page. Do not copy copyrighted text or tables."""

    title: str
    detail: str = ""
    url: str = ""

    def __str__(self) -> str:
        return f"{self.title}, {self.detail}" if self.detail else self.title

    def to_dict(self) -> dict[str, str]:
        """Return a JSON-serialisable form."""
        return {"title": self.title, "detail": self.detail, "url": self.url}
