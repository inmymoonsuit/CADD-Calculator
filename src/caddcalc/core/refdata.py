"""Reference data: versioned, cited tables that ship inside the package (ADR-0014 §1).

A table is a TOML file with a ``[table]`` header, the ``[[publication]]`` list of works it
cites, the ``[[source]]`` list of places in them, and the content keys its domain module
declares. This module loads and checks the parts every table shares: the header, the
publications and sources, and the release-checklist rules that can be checked
mechanically (ADR-0014 §5).
"""

from __future__ import annotations

import datetime
import hashlib
import json
import re
import tomllib
import unicodedata
from collections import Counter
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from decimal import ROUND_DOWN, ROUND_HALF_EVEN, ROUND_HALF_UP, Decimal
from enum import Enum
from fractions import Fraction
from importlib import resources
from types import MappingProxyType
from typing import Any

from caddcalc.core.errors import SpecError, UsageError
from caddcalc.core.reference import Reference
from caddcalc.core.units import TypedValue, get_unit

SCHEMA_VERSION = 1
"""The table schema this module reads; ``[table] schema`` must equal it."""

MAX_CITE_ONLY_PER_PUBLICATION = 1
"""The most values one cite-only publication may define, in any table (ADR-0014 §5.1).

Raising it takes a code change and an ADR-0014 amendment, so an isolated cited fact can't
quietly grow into a value set drawn from one cite-only publication.
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


class Basis(Enum):
    """What a value represents."""

    SPEC_MINIMUM = "spec_minimum"
    TYPICAL = "typical"
    A_BASIS = "a_basis"
    """A statistical allowable, e.g. from MIL-HDBK-5J."""
    RULE_OF_THUMB = "rule_of_thumb"
    NOMINAL_DEFINITION = "nominal_definition"
    """A nominal value from a published definition, such as a gauge system's thickness."""


class TrustLevel(Enum):
    """How far a value can be trusted. It rates values; ``Verification`` rates methods."""

    VERIFIED_DERIVATION = "verified_derivation"
    HANDBOOK_RULE = "handbook_rule"
    SPEC_GUIDANCE = "spec_guidance"
    RULE_OF_THUMB = "rule_of_thumb"


_EDITIONED = frozenset({PublicationKind.BOOK, PublicationKind.STANDARD})
_ONLINE = frozenset({PublicationKind.ARTICLE, PublicationKind.WEBSITE})
_PERMITS_REUSE = "permits_reuse"
_TABLE_KEYS = frozenset({"schema", "name", "version"})
_PUBLICATION_KEYS = frozenset(
    {"id", "kind", "title", "edition", "url", "license", "public_domain_basis"}
    | {"third_party", "cite_only_cap", "terms_url", "terms_checked", "terms_outcome"}
)
_SOURCE_KEYS = frozenset({"id", "publication", "locator", "accessed", "scope", "detail"})
_LEADING_NUMBER = re.compile(r"[0-9]+")


@dataclass(frozen=True)
class TablePublication:
    """One work a table cites, with the terms its values ship under (ADR-0014 §5).

    The kind, license, terms, and cite-only cap belong to the publication, not to the
    places in it that a table cites, so citing a book in several places can't raise its cap.
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

    @property
    def work(self) -> tuple[str, str]:
        """The title and edition, compared loosely, so one work can't be declared twice.

        The title is casefolded, without spaces or punctuation. An edition that starts
        with a number is that number, so "29", "29th", and "29th ed." are one edition.
        """
        edition = unicodedata.normalize("NFKC", self.edition).strip()
        number = _LEADING_NUMBER.match(edition)
        return _loosely(self.title), number.group() if number else _loosely(edition)


@dataclass(frozen=True)
class TableSource:
    """One place in a publication that a table cites, such as a table on a page."""

    id: str
    publication: TablePublication
    reference: Reference
    """The citation: the publication's title, edition, and url, with this place's locator."""


@dataclass(frozen=True)
class ReferenceValue:
    """One value from a reference table, with its sources and how far to trust it.

    Raises:
        SpecError: ``stated`` doesn't equal ``value``.
    """

    value: float
    """The value, in base units."""
    source: str
    """The id of the source the number comes from. Its publication's license is the value's."""
    basis: Basis
    trust: TrustLevel
    corroborating: tuple[str, ...] = ()
    """Ids of sources that agree with it but don't define it, such as spot checks."""
    stated: TypedValue | None = None
    """The value as the source states it, when the source states it literally."""

    def __post_init__(self) -> None:
        if self.stated is not None and self.stated.value != self.value:
            raise SpecError(f"Stated value {self.stated.text!r} doesn't equal {self.value!r}")


@dataclass(frozen=True)
class ReferenceTable:
    """A loaded reference table: its header, what it cites, and its domain content."""

    name: str
    version: int
    publications: Mapping[str, TablePublication]
    sources: Mapping[str, TableSource]
    data: Mapping[str, Any] = field(default_factory=dict)
    """The content keys its domain module declared, for that module to read."""
    digest: str = ""
    """A hash of the table's parsed content, which tests pin to its name and version."""

    @property
    def reference(self) -> Reference:
        """This table as a citation, e.g. ``"Gauge systems, version 1"``."""
        return Reference(self.name, f"version {self.version}")

    def check_values(self, values: Iterable[ReferenceValue]) -> None:
        """Check the values a domain module built from this table.

        Whether a value's defining source really states it can't be checked here; the
        release checklist covers that (ADR-0014 §5).

        Raises:
            SpecError: A value cites a source the table doesn't declare, or a cite-only
                publication defines more values, through any of its sources, than its
                cap (ADR-0014 §5.1).
        """
        defined: Counter[str] = Counter()
        for value in values:
            unknown = [s for s in (value.source, *value.corroborating) if s not in self.sources]
            if unknown:
                raise SpecError(f"{self.name}: a value cites unknown sources {unknown}")
            defined[self.sources[value.source].publication.id] += 1
        for publication_id, count in defined.items():
            publication = self.publications[publication_id]
            if publication.license is License.CITE_ONLY_FACT and count > publication.cite_only_cap:
                raise SpecError(
                    f"{self.name}: cite-only publication {publication_id!r} defines {count} "
                    f"values; its cap is {publication.cite_only_cap} (ADR-0014 §5.1)"
                )


@dataclass(frozen=True)
class TableSpec:
    """Where a shipped reference table lives, and the content keys its domain module reads.

    The calculators layer lists its tables (``caddcalc.calculators.REFERENCE_TABLES``), so
    tests can check every shipped table and the packaged app can report what it loaded.
    """

    package: str
    filename: str
    content_keys: frozenset[str]
    values: Callable[[ReferenceTable], Iterable[ReferenceValue]]
    """Builds the table's values as its domain module does, so tests can hold the cite-only
    cap across every shipped table, not just within one."""

    def load(self) -> ReferenceTable:
        """Load and check the table."""
        return load_table(self.package, self.filename, self.content_keys)


def load_table(package: str, filename: str, content_keys: Iterable[str]) -> ReferenceTable:
    """Load and check a reference table shipped in ``package``.

    Args:
        package: The package that holds the file, e.g. ``"caddcalc.calculators.sheet_metal"``.
        filename: The file's path inside the package, e.g. ``"data/gauges.toml"``.
        content_keys: The top-level keys the domain module reads, besides the header,
            publications, and sources. Any other key is refused, so a misspelled key can't
            pass silently.

    Raises:
        SpecError: The file is missing, isn't valid TOML, or breaks the table schema.
    """
    try:
        text = resources.files(package).joinpath(filename).read_text(encoding="utf-8")
    except (OSError, ModuleNotFoundError) as exc:
        raise SpecError(f"Reference table {package}/{filename} can't be read: {exc}") from exc
    return parse_table(text, f"{package}/{filename}", content_keys)


def parse_table(text: str, origin: str, content_keys: Iterable[str]) -> ReferenceTable:
    """Parse and check a reference table's TOML text.

    Args:
        text: The TOML.
        origin: Where the text came from, for error messages.
        content_keys: The top-level keys allowed besides ``table``, ``publication``, and
            ``source``.

    Raises:
        SpecError: The text isn't valid TOML, or breaks the table schema.
    """
    try:
        raw = tomllib.loads(text)
    except tomllib.TOMLDecodeError as exc:
        raise SpecError(f"{origin}: not valid TOML: {exc}") from exc
    digest = hashlib.sha256(
        json.dumps(raw, sort_keys=True, default=_json_default).encode("utf-8")
    ).hexdigest()
    header = raw.pop("table", None)
    if not isinstance(header, dict):
        raise SpecError(f"{origin}: missing the [table] header")
    _check_keys(f"{origin}: [table]", header, _TABLE_KEYS, required=_TABLE_KEYS)
    if header["schema"] != SCHEMA_VERSION:
        raise SpecError(
            f"{origin}: [table] schema {header['schema']!r} isn't supported; this version "
            f"reads schema {SCHEMA_VERSION}"
        )
    name, version = header["name"], header["version"]
    if not isinstance(name, str) or not name.strip():
        raise SpecError(f"{origin}: [table] name must be text")
    if not isinstance(version, int) or isinstance(version, bool) or version < 1:
        raise SpecError(f"{origin}: [table] version must be a whole number from 1")
    publications = _parse_publications(origin, raw.pop("publication", []))
    sources: dict[str, TableSource] = {}
    for entry in raw.pop("source", []):
        source = _parse_source(origin, entry, publications)
        if source.id in sources:
            raise SpecError(f"{origin}: source {source.id!r} is declared twice")
        sources[source.id] = source
    stray = sorted(set(raw) - set(content_keys))
    if stray:
        raise SpecError(f"{origin}: unknown top-level keys {stray}")
    return ReferenceTable(
        name,
        version,
        MappingProxyType(publications),
        MappingProxyType(sources),
        MappingProxyType(raw),
        digest,
    )


def _parse_publications(origin: str, entries: Any) -> dict[str, TablePublication]:
    """Parse the publications, each declared once, however its title is spelt."""
    publications: dict[str, TablePublication] = {}
    by_work: dict[tuple[str, str], str] = {}
    for entry in entries:
        publication = _parse_publication(origin, entry)
        if publication.id in publications:
            raise SpecError(f"{origin}: publication {publication.id!r} is declared twice")
        work = publication.work
        if work in by_work:
            raise SpecError(
                f"{origin}: publications {by_work[work]!r} and {publication.id!r} have the same "
                "title and edition; declare it once and cite each place as a source"
            )
        by_work[work] = publication.id
        publications[publication.id] = publication
    return publications


def _loosely(text: str) -> str:
    """Return ``text`` for comparing titles: casefolded, without spaces or punctuation."""
    return "".join(ch for ch in unicodedata.normalize("NFKC", text).casefold() if ch.isalnum())


def _parse_publication(origin: str, entry: Any) -> TablePublication:
    if not isinstance(entry, dict):
        raise SpecError(f"{origin}: each [[publication]] must be a table")
    where = f"{origin}: publication {entry.get('id', '?')!r}"
    _check_keys(where, entry, _PUBLICATION_KEYS, required={"id", "kind", "title", "license"})
    for key in ("id", "title"):
        if not isinstance(entry[key], str) or not entry[key].strip():
            raise SpecError(f"{where} needs a {key}")
    kind = _enum(where, PublicationKind, entry["kind"])
    license_ = _enum(where, License, entry["license"])
    third_party = entry.get("third_party", False)
    if not isinstance(third_party, bool):
        raise SpecError(f"{where}: third_party must be true or false")
    edition = str(entry.get("edition", ""))
    basis = str(entry.get("public_domain_basis", ""))
    url = str(entry.get("url", ""))
    _check_license(where, kind, license_, third_party=third_party, edition=edition, basis=basis)
    terms_url, terms_checked = "", None
    if kind in _ONLINE:
        terms_url, terms_checked = _check_terms(where, entry, url)
    cap = entry.get("cite_only_cap", 0)
    if not isinstance(cap, int) or isinstance(cap, bool) or cap < 0:
        raise SpecError(f"{where}: cite_only_cap must be a whole number from 0")
    if cap and license_ is not License.CITE_ONLY_FACT:
        raise SpecError(f"{where}: only a cite-only publication has a cite_only_cap")
    if cap > MAX_CITE_ONLY_PER_PUBLICATION:
        raise SpecError(
            f"{where}: cite_only_cap {cap} is above the ceiling of "
            f"{MAX_CITE_ONLY_PER_PUBLICATION} (ADR-0014 §5.1)"
        )
    return TablePublication(
        entry["id"],
        kind,
        entry["title"],
        license_,
        edition=edition,
        url=url,
        third_party=third_party,
        public_domain_basis=basis,
        cite_only_cap=cap,
        terms_url=terms_url,
        terms_checked=terms_checked,
    )


def _parse_source(
    origin: str, entry: Any, publications: Mapping[str, TablePublication]
) -> TableSource:
    if not isinstance(entry, dict):
        raise SpecError(f"{origin}: each [[source]] must be a table")
    where = f"{origin}: source {entry.get('id', '?')!r}"
    required = {"id", "publication", "locator", "accessed"}
    _check_keys(where, entry, _SOURCE_KEYS, required=required)
    for key in ("id", "publication", "locator"):
        if not isinstance(entry[key], str) or not entry[key].strip():
            raise SpecError(f"{where} needs a {key}")
    publication = publications.get(entry["publication"])
    if publication is None:
        raise SpecError(f"{where} cites publication {entry['publication']!r}, which isn't declared")
    reference = Reference(
        publication.title,
        detail=str(entry.get("detail", "")),
        url=publication.url,
        edition=publication.edition,
        locator=entry["locator"],
        accessed=_date(where, "accessed", entry["accessed"]),
        scope=str(entry.get("scope", "")),
    )
    return TableSource(entry["id"], publication, reference)


def _check_license(
    where: str,
    kind: PublicationKind,
    license_: License,
    *,
    third_party: bool,
    edition: str,
    basis: str,
) -> None:
    """Hold a publication's license to what its kind allows (ADR-0014 §5.1, §5.3)."""
    if kind in _EDITIONED and not edition.strip():
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


def _check_terms(where: str, entry: Mapping[str, Any], url: str) -> tuple[str, datetime.date]:
    """An online publication needs terms that were read and permit reuse (ADR-0014 §5.2)."""
    if not url.strip():
        raise SpecError(f"{where} is online, so it needs a url")
    terms_url = str(entry.get("terms_url", ""))
    if not terms_url.strip() or "terms_checked" not in entry:
        raise SpecError(
            f"{where} is online, so it needs terms_url and terms_checked: nothing ships from "
            "a site whose terms weren't read (ADR-0014 §5.2)"
        )
    if entry.get("terms_outcome") != _PERMITS_REUSE:
        raise SpecError(
            f"{where}: its terms must permit reuse (terms_outcome = {_PERMITS_REUSE!r}); "
            f"found {entry.get('terms_outcome')!r} (ADR-0014 §5.2)"
        )
    return terms_url, _date(where, "terms_checked", entry["terms_checked"])


def _date(where: str, key: str, value: Any) -> datetime.date:
    if not isinstance(value, datetime.date) or isinstance(value, datetime.datetime):
        raise SpecError(f"{where}: {key} must be a date, e.g. 2026-10-17")
    return value


def _check_keys(
    where: str, entry: Mapping[str, Any], allowed: frozenset[str], *, required: Iterable[str]
) -> None:
    unknown = sorted(set(entry) - allowed)
    if unknown:
        raise SpecError(f"{where} has unknown keys {unknown}")
    missing = sorted(set(required) - set(entry))
    if missing:
        raise SpecError(f"{where} is missing {missing}")


def _enum[E: Enum](where: str, enum: type[E], value: Any) -> E:
    try:
        return enum(value)
    except ValueError:
        allowed = ", ".join(repr(member.value) for member in enum)
        raise SpecError(f"{where} has {value!r}; allowed: {allowed}") from None


def _json_default(value: Any) -> str:
    """Write TOML dates in the digest as ISO text."""
    if isinstance(value, datetime.date):
        return value.isoformat()
    raise TypeError(f"Can't hash {type(value).__name__}")


def nominal(
    value: Fraction | Decimal, unit: str, decimals: int, rounding: str = ROUND_HALF_UP
) -> TypedValue:
    """Return a standard's stated value: ``value`` at the precision the standard publishes.

    This is the one place a value is rounded outside display: a gauge system's published
    thickness is part of its definition, not a display choice (guidelines §2.7,
    ADR-0014 amendments). The rounding is exact rational arithmetic, so a value exactly
    halfway, such as 0.01875 in at four decimals, rounds as the standard says. A float is
    refused: 0.01875 as a float sits just below the tie. The result is exact text, so it
    parses to the published value.

    Args:
        value: The exact value in ``unit``: a ``Fraction``, or a ``Decimal`` computed at a
            stated working precision (for a value with no exact form, such as AWG's).
        unit: The unit the standard states it in, e.g. ``"in"``; ``""`` for a ratio.
        decimals: How many decimal places the standard publishes.
        rounding: ``decimal.ROUND_HALF_UP``, ``ROUND_HALF_EVEN``, or ``ROUND_DOWN``.

    Raises:
        UsageError: ``value`` isn't a finite ``Fraction`` or ``Decimal``, ``decimals`` is
            negative, or the rounding mode isn't one of those three.
    """
    if not isinstance(value, Fraction | Decimal) or (
        isinstance(value, Decimal) and not value.is_finite()
    ):
        raise UsageError(f"nominal() needs an exact Fraction or Decimal, not {value!r}")
    if decimals < 0:
        raise UsageError(f"nominal() needs decimals of 0 or more, not {decimals}")
    exact = Fraction(value)
    scaled = abs(exact) * 10**decimals
    whole, rest = divmod(scaled.numerator, scaled.denominator)
    remainder = Fraction(rest, scaled.denominator)
    half = Fraction(1, 2)
    if rounding == ROUND_DOWN:
        units = whole
    elif rounding == ROUND_HALF_UP:
        units = whole + (remainder >= half)
    elif rounding == ROUND_HALF_EVEN:
        units = whole + (remainder > half or (remainder == half and whole % 2 == 1))
    else:
        raise UsageError(f"nominal() doesn't support the rounding mode {rounding!r}")
    sign = "-" if exact < 0 and units else ""
    digits = str(units).rjust(decimals + 1, "0")
    number = f"{digits[:-decimals]}.{digits[-decimals:]}" if decimals else digits
    return TypedValue.parse(f"{sign}{number} {unit}".rstrip(), get_unit(unit).dimension)
