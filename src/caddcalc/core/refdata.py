"""Reference data: versioned, cited tables that ship inside the package (ADR-0014 §1).

A table is a TOML file with a ``[table]`` header, its ``[[source]]`` list, and content that
its domain module reads. This module loads and checks the parts every table shares: the
header, the sources, and the release-checklist rules that can be checked mechanically
(ADR-0014 §5).
"""

from __future__ import annotations

import datetime
import tomllib
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal
from enum import Enum
from importlib import resources
from types import MappingProxyType
from typing import Any

from caddcalc.core.errors import SpecError
from caddcalc.core.reference import Reference
from caddcalc.core.units import TypedValue, get_unit


class License(Enum):
    """The terms a value ships under (ADR-0014 §5.1). There is deliberately no vendor value."""

    PUBLIC_DOMAIN = "public_domain"
    CITE_ONLY_FACT = "cite_only_fact"
    """An isolated fact cited from a book or standard consulted in a legitimate copy."""
    OWN_MEASUREMENT = "own_measurement"


class PublicationKind(Enum):
    """What a source is. A book or a standard must name its edition."""

    BOOK = "book"
    STANDARD = "standard"
    STATUTE = "statute"
    GOVERNMENT_DOCUMENT = "government_document"
    ARTICLE = "article"
    WEBSITE = "website"


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


_NEEDS_EDITION = frozenset({PublicationKind.BOOK, PublicationKind.STANDARD})
_SOURCE_KEYS = frozenset(
    {"id", "kind", "title", "detail", "url", "edition", "locator", "accessed", "license"}
    | {"third_party", "scope"}
)
_TABLE_KEYS = frozenset({"name", "version", "cite_only_cap"})


@dataclass(frozen=True)
class TableSource:
    """One source a table cites, with the terms its values ship under."""

    id: str
    reference: Reference
    kind: PublicationKind
    license: License
    third_party: bool = False
    """Whether the publication credits the content to someone else (ADR-0014 §5.3)."""


@dataclass(frozen=True)
class ReferenceValue:
    """One value from a reference table, with its sources and how far to trust it.

    Raises:
        SpecError: It cites no source, or ``stated`` doesn't equal ``value``.
    """

    value: float
    """The value, in base units."""
    sources: tuple[str, ...]
    """Ids of the table's sources it rests on."""
    basis: Basis
    trust: TrustLevel
    stated: TypedValue | None = None
    """The value as the source states it, when the source states it literally."""

    def __post_init__(self) -> None:
        if not self.sources:
            raise SpecError("A reference value must cite at least one source")
        if self.stated is not None and self.stated.value != self.value:
            raise SpecError(f"Stated value {self.stated.text!r} doesn't equal {self.value!r}")


@dataclass(frozen=True)
class ReferenceTable:
    """A loaded reference table: its header, its sources, and its domain content."""

    name: str
    version: int
    sources: Mapping[str, TableSource]
    cite_only_cap: int
    """How many of its values may rest on cite-only sources alone (ADR-0014 §5.1)."""
    data: Mapping[str, Any] = field(default_factory=dict)
    """Everything but the header and sources, for the table's domain module to read."""

    @property
    def reference(self) -> Reference:
        """This table as a citation, e.g. ``"Gauge systems, version 1"``."""
        return Reference(self.name, f"version {self.version}")

    def check_values(self, values: Iterable[ReferenceValue]) -> None:
        """Check the values a domain module built from this table.

        Raises:
            SpecError: A value cites a source the table doesn't declare, or more values
                rest on cite-only sources alone than the table's cap allows.
        """
        cite_only = 0
        for value in values:
            unknown = [s for s in value.sources if s not in self.sources]
            if unknown:
                raise SpecError(f"{self.name}: a value cites unknown sources {unknown}")
            if all(self.sources[s].license is License.CITE_ONLY_FACT for s in value.sources):
                cite_only += 1
        if cite_only > self.cite_only_cap:
            raise SpecError(
                f"{self.name}: {cite_only} values rest on cite-only sources alone; "
                f"the cap is {self.cite_only_cap} (ADR-0014 §5.1)"
            )


def load_table(package: str, filename: str) -> ReferenceTable:
    """Load and check a reference table shipped in ``package``.

    Args:
        package: The package that holds the file, e.g. ``"caddcalc.calculators.sheet_metal"``.
        filename: The file's path inside the package, e.g. ``"data/gauges.toml"``.

    Raises:
        SpecError: The file is missing, isn't valid TOML, or breaks the table schema.
    """
    try:
        text = resources.files(package).joinpath(filename).read_text(encoding="utf-8")
    except (OSError, ModuleNotFoundError) as exc:
        raise SpecError(f"Reference table {package}/{filename} can't be read: {exc}") from exc
    return parse_table(text, f"{package}/{filename}")


def parse_table(text: str, origin: str) -> ReferenceTable:
    """Parse and check a reference table's TOML text.

    Args:
        text: The TOML.
        origin: Where the text came from, for error messages.

    Raises:
        SpecError: The text isn't valid TOML, or breaks the table schema.
    """
    try:
        raw = tomllib.loads(text)
    except tomllib.TOMLDecodeError as exc:
        raise SpecError(f"{origin}: not valid TOML: {exc}") from exc
    header = raw.pop("table", None)
    if not isinstance(header, dict):
        raise SpecError(f"{origin}: missing the [table] header")
    _check_keys(origin, "[table]", header, _TABLE_KEYS, required=_TABLE_KEYS)
    name, version, cap = header["name"], header["version"], header["cite_only_cap"]
    if not isinstance(name, str) or not name.strip():
        raise SpecError(f"{origin}: [table] name must be text")
    if not isinstance(version, int) or isinstance(version, bool) or version < 1:
        raise SpecError(f"{origin}: [table] version must be a whole number from 1")
    if not isinstance(cap, int) or isinstance(cap, bool) or cap < 0:
        raise SpecError(f"{origin}: [table] cite_only_cap must be a whole number from 0")
    sources: dict[str, TableSource] = {}
    for entry in raw.pop("source", []):
        source = _parse_source(origin, entry)
        if source.id in sources:
            raise SpecError(f"{origin}: source {source.id!r} is declared twice")
        sources[source.id] = source
    return ReferenceTable(name, version, MappingProxyType(sources), cap, MappingProxyType(raw))


def _parse_source(origin: str, entry: Any) -> TableSource:
    if not isinstance(entry, dict):
        raise SpecError(f"{origin}: each [[source]] must be a table")
    where = f"source {entry.get('id', '?')!r}"
    required = {"id", "kind", "title", "locator", "accessed", "license"}
    _check_keys(origin, where, entry, _SOURCE_KEYS, required=required)
    for key in ("id", "title", "locator"):
        if not isinstance(entry[key], str) or not entry[key].strip():
            raise SpecError(f"{origin}: {where} needs a {key}")
    accessed = entry["accessed"]
    if not isinstance(accessed, datetime.date) or isinstance(accessed, datetime.datetime):
        raise SpecError(f"{origin}: {where} accessed must be a date, e.g. 2026-10-17")
    kind = _enum(origin, where, PublicationKind, entry["kind"])
    license_ = _enum(origin, where, License, entry["license"])
    edition = entry.get("edition", "")
    if kind in _NEEDS_EDITION and not str(edition).strip():
        raise SpecError(f"{origin}: {where} is a {kind.value}, so it needs an edition")
    third_party = entry.get("third_party", False)
    if not isinstance(third_party, bool):
        raise SpecError(f"{origin}: {where} third_party must be true or false")
    if third_party and license_ is not License.CITE_ONLY_FACT:
        raise SpecError(
            f"{origin}: {where} credits its content to a third party, so it is cite-only "
            "(ADR-0014 §5.3)"
        )
    reference = Reference(
        entry["title"],
        detail=str(entry.get("detail", "")),
        url=str(entry.get("url", "")),
        edition=str(edition),
        locator=entry["locator"],
        accessed=accessed,
        scope=str(entry.get("scope", "")),
    )
    return TableSource(entry["id"], reference, kind, license_, third_party)


def _check_keys(
    origin: str,
    where: str,
    entry: Mapping[str, Any],
    allowed: frozenset[str],
    *,
    required: Iterable[str],
) -> None:
    unknown = sorted(set(entry) - allowed)
    if unknown:
        raise SpecError(f"{origin}: {where} has unknown keys {unknown}")
    missing = sorted(set(required) - set(entry))
    if missing:
        raise SpecError(f"{origin}: {where} is missing {missing}")


def _enum[E: Enum](origin: str, where: str, enum: type[E], value: Any) -> E:
    try:
        return enum(value)
    except ValueError:
        allowed = ", ".join(repr(member.value) for member in enum)
        raise SpecError(f"{origin}: {where} has {value!r}; allowed: {allowed}") from None


def nominal(value: float, unit: str, decimals: int, rounding: str = ROUND_HALF_UP) -> TypedValue:
    """Return a standard's stated value: ``value`` at the precision the standard publishes.

    This is the one place a value is rounded outside display: a gauge system's published
    thickness is part of its definition, not a display choice (guidelines §2.7,
    ADR-0014 amendments). The result is exact text, so it parses to the published value.

    Args:
        value: The value in ``unit``, e.g. inches computed from a gauge definition.
        unit: The unit the standard states it in, e.g. ``"in"``; ``""`` for a ratio.
        decimals: How many decimal places the standard publishes.
        rounding: A ``decimal`` rounding mode, e.g. ``ROUND_HALF_UP`` or ``ROUND_DOWN``.
    """
    exact = Decimal(value).quantize(Decimal(1).scaleb(-decimals), rounding=rounding)
    text = f"{exact} {unit}".rstrip()
    return TypedValue.parse(text, get_unit(unit).dimension)
