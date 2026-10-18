"""Citations and their terms: the works the app cites, and on what basis it may ship values.

Reference tables (``core.refdata``) and the units registry (``core.units``) both cite
works through these types, so there's one citation model and no import cycle between them
(ADR-0019 §4). The checks here are the parts of ADR-0014's §5 release checklist that hold
for a publication anywhere it's cited.
"""

from __future__ import annotations

import datetime
import re
import unicodedata
from dataclasses import dataclass
from enum import Enum
from urllib.parse import urlsplit

from caddcalc.core.errors import SpecError
from caddcalc.core.reference import Reference

MAX_CITE_ONLY_PER_PUBLICATION = 1
"""The most values one cite-only publication may define, in any table (ADR-0014 §5.1).

It counts reference-data values, not the coefficients in a method's formula, which are
cited and rated with their method (ADR-0014, amendments). Raising it takes a code change
and an ADR-0014 amendment, so an isolated cited fact can't quietly grow into a value set
drawn from one cite-only publication.
"""


class License(Enum):
    """The terms a value ships under (ADR-0014 §5.1). There is deliberately no vendor value."""

    PUBLIC_DOMAIN = "public_domain"
    CITE_ONLY_FACT = "cite_only_fact"
    """An isolated fact cited from a book or standard consulted in a legitimate copy."""
    OWN_MEASUREMENT = "own_measurement"
    """A value the project measured itself; only an own-measurement publication has it."""


class PublicationKind(Enum):
    """What a publication is. It decides which licenses and checks the publication needs."""

    BOOK = "book"
    STANDARD = "standard"
    STATUTE = "statute"
    GOVERNMENT_DOCUMENT = "government_document"
    ARTICLE = "article"
    WEBSITE = "website"
    OWN_MEASUREMENT = "own_measurement"
    """The project's own measurements, such as a test log; its license is ``OWN_MEASUREMENT``."""


EDITIONED = frozenset({PublicationKind.BOOK, PublicationKind.STANDARD})
"""The kinds that must name their edition."""
ONLINE = frozenset({PublicationKind.ARTICLE, PublicationKind.WEBSITE})
"""The kinds whose terms of use must have been read and permit reuse (ADR-0014 §5.2)."""
_LEADING_NUMBER = re.compile(r"[0-9]+")

PUBLIC_DOMAIN_HOSTS = (".gov", ".mil")
"""Host suffixes a public-domain publication's url may have.

US federal and military sites publish works that 17 U.S.C. §105 places in the public
domain. A url anywhere else fails the allowlist until someone adds its host on purpose, so
a vendor page can't pass as a government document. It is a tripwire for review, not a
ruling: ``public_domain_basis`` states the claim, and a state .gov work needs its own,
since §105 covers federal works only.
"""
PUBLIC_DOMAIN_MIRRORS = frozenset({"everyspec.com"})
"""Named mirrors: everyspec.com republishes DoD specifications and handbooks, which are
public domain at their source."""


@dataclass(frozen=True)
class Publication:
    """One work the app cites, with the terms its values ship under (ADR-0014 §5).

    The kind, license, terms, and cite-only cap belong to the publication, not to the
    places in it that are cited, so citing a book in several places can't raise its cap.
    """

    id: str
    kind: PublicationKind
    title: str
    license: License
    edition: str = ""
    url: str = ""
    third_party: bool = False
    """Whether the publication credits the content to someone else (ADR-0014 §5.3)."""
    public_domain_basis: str = ""
    """Why it is public domain, e.g. ``"17 U.S.C. §105"`` or ``"published before 1930"``."""
    cite_only_cap: int = 0
    """How many values this cite-only publication may define, through any of its sources
    (at most ``MAX_CITE_ONLY_PER_PUBLICATION``)."""
    terms_url: str = ""
    """Where an online publication's terms of use were read (ADR-0014 §5.2)."""
    terms_checked: datetime.date | None = None
    short_title: str = ""
    """How labels and note texts name it, e.g. ``"FAA-H-8083-31B"``; empty for the title."""

    @property
    def work(self) -> tuple[str, str]:
        """The title and edition, compared loosely, so one work can't be declared twice.

        The title is casefolded, without spaces or punctuation. An edition that starts
        with a number is that number, so "29", "29th", and "29th ed." are one edition.
        """
        edition = unicodedata.normalize("NFKC", self.edition).strip()
        number = _LEADING_NUMBER.match(edition)
        return loosely(self.title), number.group() if number else loosely(edition)

    @property
    def on_allowlist(self) -> bool:
        """Whether its url's host is a federal or military one, or a named mirror.

        Only a public-domain publication needs to be; one without a url never is, so a
        printed work passes only where it's named on purpose.
        """
        host = (urlsplit(self.url).hostname or "").removeprefix("www.")
        return bool(host) and (host.endswith(PUBLIC_DOMAIN_HOSTS) or host in PUBLIC_DOMAIN_MIRRORS)


@dataclass(frozen=True)
class Source:
    """One place in a publication that is cited, such as a table on a page."""

    id: str
    publication: Publication
    reference: Reference
    """The citation: the publication's title, edition, and url, with this place's locator."""
    remark: str = ""
    """A note for reviewers, such as where an earlier edition has the same values. It is
    never rendered: ``detail`` is for a sub-locator, which is part of the citation."""


def cite(
    source_id: str,
    publication: Publication,
    locator: str,
    *,
    accessed: datetime.date | None = None,
    scope: str = "",
    detail: str = "",
    remark: str = "",
) -> Source:
    """Return a place in ``publication``, with its citation built from the publication."""
    reference = Reference(
        publication.title,
        detail=detail,
        url=publication.url,
        edition=publication.edition,
        locator=locator,
        accessed=accessed,
        scope=scope,
        short_title=publication.short_title,
    )
    return Source(source_id, publication, reference, remark)


def loosely(text: str) -> str:
    """Return ``text`` for comparing titles: casefolded, without spaces or punctuation."""
    return "".join(ch for ch in unicodedata.normalize("NFKC", text).casefold() if ch.isalnum())


def check_license(
    where: str,
    kind: PublicationKind,
    license_: License,
    *,
    third_party: bool,
    edition: str,
    basis: str,
) -> None:
    """Hold a publication's license to what its kind allows (ADR-0014 §5.1, §5.3).

    Raises:
        SpecError: The license doesn't fit the kind, or a claim lacks its basis.
    """
    if kind in EDITIONED and not edition.strip():
        raise SpecError(f"{where} is a {kind.value}, so it needs an edition")
    if license_ is License.PUBLIC_DOMAIN and not basis.strip():
        raise SpecError(
            f"{where}: a public-domain {kind.value} needs a public_domain_basis, "
            'e.g. "17 U.S.C. §105" or "published before 1930"'
        )
    if basis.strip() and license_ is not License.PUBLIC_DOMAIN:
        raise SpecError(f"{where}: only a public-domain publication has a public_domain_basis")
    if (kind is PublicationKind.OWN_MEASUREMENT) != (license_ is License.OWN_MEASUREMENT):
        raise SpecError(
            f"{where}: the own_measurement license goes with the own_measurement kind, and "
            "only with it"
        )
    if third_party and license_ is not License.CITE_ONLY_FACT:
        raise SpecError(
            f"{where} credits its content to a third party, so it is cite-only (ADR-0014 §5.3)"
        )


def check_publication(publication: Publication) -> None:
    """Check a publication declared in code, as a table's are when loaded.

    Raises:
        SpecError: Its license doesn't fit its kind (``check_license``).
    """
    check_license(
        f"publication {publication.id!r}",
        publication.kind,
        publication.license,
        third_party=publication.third_party,
        edition=publication.edition,
        basis=publication.public_domain_basis,
    )
