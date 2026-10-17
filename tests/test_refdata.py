"""Reference data: cited tables, their schema, and the mechanical §5 checks (ADR-0014 §1)."""

from __future__ import annotations

import datetime
from decimal import ROUND_DOWN, ROUND_HALF_UP

import pytest

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
    Verification,
    load_table,
    nominal,
    parse_table,
)
from caddcalc.core.formatting import describe_note

ACCESSED = datetime.date(2026, 10, 17)


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
    table = load_table("tests", "data/refdata_sample.toml")
    assert (table.name, table.version, table.cite_only_cap) == ("Sample table", 2, 1)
    assert str(table.reference) == "Sample table, version 2"
    handbook = table.sources["handbook"]
    assert (handbook.kind, handbook.license, handbook.third_party) == (
        PublicationKind.BOOK,
        License.CITE_ONLY_FACT,
        False,
    )
    assert handbook.reference.edition == "3rd ed."
    assert handbook.reference.accessed == ACCESSED
    assert handbook.reference.scope == "bench practice"
    assert table.data["system"][0]["id"] == "sample", "domain content is kept for its module"


def test_a_missing_table_is_a_definition_error() -> None:
    with pytest.raises(SpecError, match="can't be read"):
        load_table("tests", "data/no_such_table.toml")


HEADER = '[table]\nname = "T"\nversion = 1\ncite_only_cap = 0\n'
SOURCE = (
    '[[source]]\nid = "s"\nkind = "statute"\ntitle = "S"\nlocator = "§1"\n'
    'accessed = 2026-10-17\nlicense = "public_domain"\n'
)


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("[table\n", "not valid TOML"),
        (SOURCE, r"missing the \[table\] header"),
        ('[table]\nname = "T"\nversion = 1\n', "missing"),
        (HEADER.replace("version = 1", "version = 0"), "version must be"),
        (HEADER + SOURCE.replace('locator = "§1"\n', ""), "missing"),
        (HEADER + SOURCE.replace('locator = "§1"', 'locator = " "'), "needs a locator"),
        (HEADER + SOURCE.replace("public_domain", "vendor"), "has 'vendor'; allowed"),
        (HEADER + SOURCE.replace('"statute"', '"book"'), "needs an edition"),
        (HEADER + SOURCE.replace("2026-10-17", '"2026-10-17"'), "must be a date"),
        (HEADER + SOURCE + "third_party = true\n", "cite-only"),
        (HEADER + SOURCE + 'lisence = "x"\n', "unknown keys"),
        (HEADER + SOURCE + SOURCE, "declared twice"),
    ],
)
def test_a_table_that_breaks_the_schema_is_refused(text: str, message: str) -> None:
    with pytest.raises(SpecError, match=message):
        parse_table(text, "test")


def test_values_must_cite_declared_sources_within_the_cite_only_cap() -> None:
    table = load_table("tests", "data/refdata_sample.toml")
    computed = ReferenceValue(
        2.657, ("statute", "handbook"), Basis.NOMINAL_DEFINITION, TrustLevel.VERIFIED_DERIVATION
    )
    basis = ReferenceValue(41.82, ("handbook",), Basis.TYPICAL, TrustLevel.HANDBOOK_RULE)
    table.check_values([computed, basis])

    with pytest.raises(SpecError, match="cap is 1"):
        table.check_values([computed, basis, basis])
    stray = ReferenceValue(1.0, ("vendor_page",), Basis.TYPICAL, TrustLevel.RULE_OF_THUMB)
    with pytest.raises(SpecError, match="unknown sources"):
        table.check_values([stray])


def test_a_reference_value_cites_a_source_and_agrees_with_its_stated_text() -> None:
    stated = TypedValue.parse("0.1046 in", Dimension.LENGTH)
    assert ReferenceValue(
        stated.value, ("s",), Basis.NOMINAL_DEFINITION, TrustLevel.VERIFIED_DERIVATION, stated
    )
    with pytest.raises(SpecError, match="at least one source"):
        ReferenceValue(1.0, (), Basis.TYPICAL, TrustLevel.RULE_OF_THUMB)
    with pytest.raises(SpecError, match="doesn't equal"):
        ReferenceValue(2.0, ("s",), Basis.TYPICAL, TrustLevel.RULE_OF_THUMB, stated)


def test_nominal_states_a_value_at_its_published_precision() -> None:
    """Manufacturers' Standard 12 ga: 4.375 ÷ 41.82 = 0.104615…, published as 0.1046 in."""
    twelve = nominal(4.375 / 41.82, "in", 4)
    assert twelve == TypedValue.parse("0.1046 in", Dimension.LENGTH)
    assert twelve.value == TypedValue.parse("0.1046", Dimension.LENGTH, "in").value
    exact = 4.375 / 40  # US Standard 1893: 7/64 in exactly
    assert nominal(exact, "in", 4, ROUND_HALF_UP).text == "0.1094 in"
    assert nominal(exact, "in", 4, ROUND_DOWN).text == "0.1093 in"
    assert nominal(0.4471, "", 2).text == "0.45"


def test_trust_levels_are_named_apart_from_method_verification() -> None:
    assert {t.value for t in TrustLevel}.isdisjoint({v.value for v in Verification})
    assert License("public_domain") is License.PUBLIC_DOMAIN
    assert "vendor" not in {member.value for member in License}
