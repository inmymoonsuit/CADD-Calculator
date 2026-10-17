"""Reference data: cited tables, their schema, and the mechanical §5 checks (ADR-0014 §1)."""

from __future__ import annotations

import datetime
from decimal import ROUND_DOWN, ROUND_HALF_EVEN, ROUND_HALF_UP, Decimal
from fractions import Fraction

import pytest

from caddcalc.calculators import REFERENCE_TABLES
from caddcalc.core import (
    Basis,
    Dimension,
    License,
    Note,
    NoteKind,
    PublicationKind,
    Reference,
    ReferenceValue,
    SpecError,
    TrustLevel,
    TypedValue,
    UsageError,
    Verification,
    load_table,
    nominal,
    parse_table,
)
from caddcalc.core.formatting import describe_note
from caddcalc.core.refdata import MAX_CITE_ONLY_PER_SOURCE

ACCESSED = datetime.date(2026, 10, 17)
SAMPLE_KEYS = {"system"}

TABLE_DIGESTS: dict[tuple[str, int], str] = {}
"""The content hash of every shipped table, by (name, version). Changing a table's data
without bumping its version fails ``test_every_shipped_table_is_pinned_to_its_version``."""


def test_a_reference_keeps_its_old_shape_and_gains_structured_fields() -> None:
    assert str(Reference("EDD5", "Ch. 19")) == "EDD5, Ch. 19"
    handbook = Reference(
        "Machinery's Handbook",
        edition="29th ed.",
        locator="Table 2, printed p. 2608",
        accessed=ACCESSED,
        scope="shop practice",
    )
    assert str(handbook) == "Machinery's Handbook, 29th ed., Table 2, printed p. 2608"
    assert handbook.to_dict() == {
        "title": "Machinery's Handbook",
        "detail": "",
        "url": "",
        "edition": "29th ed.",
        "locator": "Table 2, printed p. 2608",
        "accessed": "2026-10-17",
        "scope": "shop practice",
    }
    assert Reference("Plain").to_dict()["accessed"] is None


def test_a_note_names_each_sources_scope() -> None:
    bench = Reference("AC 43.13-1B", locator="Table 4-6", scope="aerospace bench practice")
    note = Note(NoteKind.LIMIT_EXCEEDED, "Too tight.", (bench, Reference("TO 1-1A-9")))
    assert describe_note(note) == (
        "Limit exceeded: Too tight. (AC 43.13-1B, Table 4-6: aerospace bench practice; TO 1-1A-9)"
    )


def test_a_shipped_table_loads_through_importlib_resources() -> None:
    table = load_table("tests", "data/refdata_sample.toml", SAMPLE_KEYS)
    assert (table.name, table.version) == ("Sample table", 2)
    assert str(table.reference) == "Sample table, version 2"
    handbook = table.sources["handbook"]
    assert (handbook.kind, handbook.license, handbook.cite_only_cap) == (
        PublicationKind.BOOK,
        License.CITE_ONLY_FACT,
        1,
    )
    assert handbook.reference.edition == "3rd ed."
    assert handbook.reference.accessed == ACCESSED
    assert handbook.reference.scope == "bench practice"
    assert table.data["system"][0]["id"] == "sample", "domain content is kept for its module"
    assert len(table.digest) == 64


def test_a_missing_table_is_a_definition_error() -> None:
    with pytest.raises(SpecError, match="can't be read"):
        load_table("tests", "data/no_such_table.toml", SAMPLE_KEYS)


HEADER = '[table]\nschema = 1\nname = "T"\nversion = 1\n'


def source(**fields: object) -> str:
    """A [[source]] entry: a public-domain statute, with ``fields`` changed (None drops one)."""
    entry: dict[str, object] = {
        "id": '"s"',
        "kind": '"statute"',
        "title": '"S"',
        "locator": '"§1"',
        "accessed": "2026-10-17",
        "license": '"public_domain"',
    }
    entry.update(fields)
    lines = "".join(f"{key} = {value}\n" for key, value in entry.items() if value is not None)
    return "[[source]]\n" + lines


ONLINE = {
    "kind": '"article"',
    "url": '"https://example.org/a"',
    "license": '"cite_only_fact"',
    "terms_url": '"https://example.org/terms"',
    "terms_checked": "2026-10-17",
    "terms_outcome": '"permits_reuse"',
}


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("[table\n", "not valid TOML"),
        (source(), r"missing the \[table\] header"),
        ('[table]\nschema = 1\nname = "T"\n', "missing"),
        (HEADER.replace("schema = 1", "schema = 2"), "schema 2 isn't supported"),
        (HEADER.replace("version = 1", "version = 0"), "version must be"),
        (HEADER + "[[sytem]]\nid = 1\n", r"unknown top-level keys \['sytem'\]"),
        (HEADER + source(locator=None), "missing"),
        (HEADER + source(locator='" "'), "needs a locator"),
        (HEADER + source(license='"vendor"'), "has 'vendor'; allowed"),
        (HEADER + source(accessed='"2026-10-17"'), "must be a date"),
        (HEADER + source(third_party="true"), "cite-only"),
        (HEADER + source(lisence='"x"'), "unknown keys"),
        (HEADER + source() + source(), "declared twice"),
        (HEADER + source(kind='"book"', license='"cite_only_fact"'), "needs an edition"),
        (HEADER + source(kind='"book"', edition='"29th ed."'), "public domain only with"),
        (HEADER + source(kind='"standard"', edition='"2024"'), "public domain only with"),
        (HEADER + source(**{**ONLINE, "url": None}), "needs a url"),
        (HEADER + source(**{**ONLINE, "terms_checked": None}), "terms weren't read"),
        (HEADER + source(**{**ONLINE, "terms_outcome": '"unreadable"'}), "must permit reuse"),
        (HEADER + source(cite_only_cap="1"), "only a cite-only source"),
        (
            HEADER
            + source(license='"cite_only_fact"', cite_only_cap=str(MAX_CITE_ONLY_PER_SOURCE + 1)),
            "above the ceiling",
        ),
    ],
)
def test_a_table_that_breaks_the_schema_is_refused(text: str, message: str) -> None:
    with pytest.raises(SpecError, match=message):
        parse_table(text, "test", SAMPLE_KEYS)


def test_the_probed_sources_are_refused() -> None:
    """A handbook as public domain, and an article whose terms weren't read, can't be entered."""
    handbook = source(kind='"book"', title='"Machinery\'s Handbook"', edition='"29th ed."')
    with pytest.raises(SpecError, match="public domain only with"):
        parse_table(HEADER + handbook, "test", SAMPLE_KEYS)
    article = source(kind='"article"', url='"https://example.org/a"', license='"cite_only_fact"')
    with pytest.raises(SpecError, match="terms weren't read"):
        parse_table(HEADER + article, "test", SAMPLE_KEYS)
    website = source(kind='"website"', license='"cite_only_fact"')
    with pytest.raises(SpecError, match="needs a url"):
        parse_table(HEADER + website, "test", SAMPLE_KEYS)


def test_public_domain_needs_a_basis_unless_it_is_a_statute_or_government_document() -> None:
    old_book = source(
        kind='"book"', edition='"1st ed."', public_domain_basis='"published before 1930"'
    )
    assert (
        parse_table(HEADER + old_book, "test", SAMPLE_KEYS).sources["s"].license
        is License.PUBLIC_DOMAIN
    )
    report = source(kind='"government_document"')
    assert (
        parse_table(HEADER + report, "test", SAMPLE_KEYS).sources["s"].kind
        is PublicationKind.GOVERNMENT_DOCUMENT
    )
    article = source(**ONLINE)
    assert parse_table(HEADER + article, "test", SAMPLE_KEYS).sources["s"].terms_checked == ACCESSED


def test_a_cite_only_source_may_define_only_its_capped_number_of_values() -> None:
    table = load_table("tests", "data/refdata_sample.toml", SAMPLE_KEYS)
    computed = ReferenceValue(
        2.657, "statute", Basis.NOMINAL_DEFINITION, TrustLevel.VERIFIED_DERIVATION, ("handbook",)
    )
    basis = ReferenceValue(41.82, "handbook", Basis.TYPICAL, TrustLevel.HANDBOOK_RULE)
    table.check_values([computed, computed, basis])

    with pytest.raises(SpecError, match="'handbook' defines 2 values; its cap is 1"):
        table.check_values([computed, basis, basis])
    stray = ReferenceValue(1.0, "vendor_page", Basis.TYPICAL, TrustLevel.RULE_OF_THUMB)
    with pytest.raises(SpecError, match="unknown sources"):
        table.check_values([stray])
    hidden = ReferenceValue(1.0, "statute", Basis.TYPICAL, TrustLevel.RULE_OF_THUMB, ("nowhere",))
    with pytest.raises(SpecError, match="unknown sources"):
        table.check_values([hidden])


def test_a_reference_value_agrees_with_its_stated_text() -> None:
    stated = TypedValue.parse("0.1046 in", Dimension.LENGTH)
    value = ReferenceValue(
        stated.value, "s", Basis.NOMINAL_DEFINITION, TrustLevel.VERIFIED_DERIVATION, stated=stated
    )
    assert value.stated == stated
    with pytest.raises(SpecError, match="doesn't equal"):
        ReferenceValue(2.0, "s", Basis.TYPICAL, TrustLevel.RULE_OF_THUMB, stated=stated)


def test_every_shipped_table_loads_within_the_ceiling_and_is_pinned_to_its_version() -> None:
    digests = {}
    for spec in REFERENCE_TABLES:
        table = spec.load()
        assert all(s.cite_only_cap <= MAX_CITE_ONLY_PER_SOURCE for s in table.sources.values())
        digests[table.name, table.version] = table.digest
    assert digests == TABLE_DIGESTS, (
        "a table's data changed without a version bump, or it isn't pinned"
    )


def test_the_digest_follows_the_content() -> None:
    first = parse_table(HEADER + source(), "test", SAMPLE_KEYS).digest
    assert parse_table(HEADER + source(), "test", SAMPLE_KEYS).digest == first
    assert parse_table(HEADER + source(locator='"§2"'), "test", SAMPLE_KEYS).digest != first


def test_nominal_states_a_value_at_its_published_precision() -> None:
    """Manufacturers' Standard 12 ga: 70 oz/ft² ÷ 16 ÷ 41.82 = 0.104615…, published 0.1046."""
    twelve = nominal(Fraction(70, 16) / Fraction("41.82"), "in", 4)
    assert twelve == TypedValue.parse("0.1046 in", Dimension.LENGTH)
    assert twelve.value == TypedValue.parse("0.1046", Dimension.LENGTH, "in").value
    assert nominal(Fraction(7, 64), "in", 4, ROUND_HALF_UP).text == "0.1094 in"
    assert nominal(Fraction(7, 64), "in", 4, ROUND_DOWN).text == "0.1093 in"
    assert nominal(Decimal("0.4471"), "", 2).text == "0.45"


@pytest.mark.parametrize(
    ("gauge", "exact", "stated"),
    [(26, Fraction(3, 160), "0.0188 in"), (17, Fraction(9, 160), "0.0563 in")],
)
def test_nominal_rounds_exact_us_standard_ties_up(gauge: int, exact: Fraction, stated: str) -> None:
    """US Standard 26 ga is exactly 0.01875 in; as a float it sits just below the tie."""
    assert nominal(exact, "in", 4, ROUND_HALF_UP).text == stated, gauge


def test_nominal_refuses_inexact_input_and_unknown_modes() -> None:
    with pytest.raises(UsageError, match="exact Fraction or Decimal"):
        nominal(0.01875, "in", 4)  # type: ignore[arg-type]
    with pytest.raises(UsageError, match="exact Fraction or Decimal"):
        nominal(Decimal("NaN"), "in", 4)
    with pytest.raises(UsageError, match="rounding mode"):
        nominal(Fraction(1), "in", 2, "ROUND_CEILING")
    assert nominal(Fraction(1, 20000), "in", 4, ROUND_HALF_EVEN).text == "0.0000 in"
    assert nominal(Fraction(-7, 64), "in", 4).text == "-0.1094 in"


def test_trust_levels_are_named_apart_from_method_verification() -> None:
    assert {t.value for t in TrustLevel}.isdisjoint({v.value for v in Verification})
    assert "vendor" not in {member.value for member in License}
