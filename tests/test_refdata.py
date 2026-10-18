"""Reference data: cited tables, their schema, and the mechanical §5 checks (ADR-0014 §1)."""

from __future__ import annotations

import datetime
import math
from collections import Counter
from collections.abc import Iterable
from dataclasses import replace
from decimal import ROUND_DOWN, ROUND_HALF_EVEN, ROUND_HALF_UP, Decimal
from fractions import Fraction
from urllib.parse import urlsplit

import pytest

from caddcalc.calculators import REFERENCE_TABLES
from caddcalc.core import (
    Band,
    Basis,
    Dimension,
    License,
    Note,
    NoteKind,
    PublicationKind,
    Reference,
    ReferenceTable,
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
from caddcalc.core.formatting import DisplayPrefs, describe_note
from caddcalc.core.refdata import MAX_CITE_ONLY_PER_PUBLICATION

ACCESSED = datetime.date(2026, 10, 17)
SAMPLE_KEYS = {"system"}
SAMPLE_QUANTITIES = frozenset({"constant", "min_radius", "f_tu"})


def sample_table() -> ReferenceTable:
    """The sample table, with the quantities these tests' values are."""
    return load_table("tests", "data/refdata_sample.toml", SAMPLE_KEYS, SAMPLE_QUANTITIES)


def constant(
    value: float,
    source: str,
    name: str,
    *,
    corroborating: tuple[str, ...] = (),
    basis: Basis = Basis.TYPICAL,
    trust: TrustLevel = TrustLevel.HANDBOOK_RULE,
) -> ReferenceValue:
    """A named, cited constant, as the gauge table holds them; the values are invented."""
    return ReferenceValue(
        value, source, basis, trust, corroborating, quantity="constant", conditions={"name": name}
    )


TABLE_DIGESTS: dict[tuple[str, int], str] = {
    ("Gauge systems", 3): "ae1da48bd0f688660b0d91169db074712b55f7ddb36f458938e15c04e4e7dfc6",
    ("Sheet-metal materials", 1): (
        "c064d35b8e642f87db09c96747918186f0ec3cfe0b5b284e89c715b34ce3672f"
    ),
}
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
        "short_title": "",
    }
    assert Reference("Plain").to_dict()["accessed"] is None


def test_a_citation_puts_its_locator_before_its_detail_and_never_shows_a_remark() -> None:
    """Review M1: a reviewer's remark read as part of the citation."""
    cited = Reference("AC 43.13-1B", edition="2024", locator="Table 4-6, p. 4-17", detail="Ch. 4")
    assert str(cited) == "AC 43.13-1B, 2024, Table 4-6, p. 4-17, Ch. 4"
    remarked = parse_table(
        table(publication(), source(remark='"p. 4-14 in an earlier file"')), "test", SAMPLE_KEYS
    )
    assert remarked.sources["s"].remark == "p. 4-14 in an earlier file"
    assert "p. 4-14" not in str(remarked.sources["s"].reference)
    assert "p. 4-14" not in str(remarked.sources["s"].reference.to_dict())


def test_a_short_title_names_a_reference_in_labels_and_falls_back_to_the_full_one() -> None:
    faa = Reference("FAA-H-8083-31B, Airframe", locator="p. 4-63", short_title="FAA-H-8083-31B")
    assert (faa.short, str(faa)) == ("FAA-H-8083-31B, p. 4-63", "FAA-H-8083-31B, Airframe, p. 4-63")
    assert Reference("Gauge systems", "version 1").short == "Gauge systems, version 1"
    with pytest.raises(SpecError, match="short_title must be text"):
        parse_table(table(publication(short_title='" "')), "test", SAMPLE_KEYS)
    named = parse_table(table(publication(short_title='"Short"'), source()), "test", SAMPLE_KEYS)
    assert (
        named.publications["p"].short_title == named.sources["s"].reference.short_title == "Short"
    )


def test_a_note_names_each_sources_scope() -> None:
    bench = Reference("AC 43.13-1B", locator="Table 4-6", scope="aerospace bench practice")
    note = Note(NoteKind.LIMIT_EXCEEDED, "Too tight.", (bench, Reference("TO 1-1A-9")))
    assert describe_note(note, DisplayPrefs()).lines == (
        "Limit exceeded: Too tight.",
        "Sources: AC 43.13-1B, Table 4-6: aerospace bench practice · TO 1-1A-9",
    )


def test_a_shipped_table_loads_through_importlib_resources() -> None:
    table = load_table("tests", "data/refdata_sample.toml", SAMPLE_KEYS)
    assert (table.name, table.version) == ("Sample table", 2)
    assert str(table.reference) == "Sample table, version 2"
    assert list(table.publications) == ["statute", "handbook"]
    handbook = table.sources["handbook"]
    assert handbook.publication is table.publications["handbook"]
    assert (handbook.publication.kind, handbook.publication.license) == (
        PublicationKind.BOOK,
        License.CITE_ONLY_FACT,
    )
    assert handbook.publication.cite_only_cap == 1
    assert str(handbook.reference) == "A handbook, 3rd ed., Table 7, p. 12"
    assert handbook.reference.accessed == ACCESSED
    assert handbook.reference.scope == "bench practice"
    assert table.sources["handbook_appendix"].publication is handbook.publication
    assert table.sources["statute"].reference.url == "https://uscode.house.gov/"
    assert table.data["system"][0]["id"] == "sample", "domain content is kept for its module"
    assert len(table.digest) == 64


def test_a_missing_table_is_a_definition_error() -> None:
    with pytest.raises(SpecError, match="can't be read"):
        load_table("tests", "data/no_such_table.toml", SAMPLE_KEYS)


HEADER = '[table]\nschema = 1\nname = "T"\nversion = 1\n'


def _entry(name: str, defaults: dict[str, object], fields: dict[str, object]) -> str:
    entry = {**defaults, **fields}
    lines = "".join(f"{key} = {value}\n" for key, value in entry.items() if value is not None)
    return f"[[{name}]]\n{lines}"


def publication(**fields: object) -> str:
    """A [[publication]] "p": a public-domain statute, with ``fields`` changed (None drops one)."""
    defaults: dict[str, object] = {
        "id": '"p"',
        "kind": '"statute"',
        "title": '"S"',
        "license": '"public_domain"',
        "public_domain_basis": '"17 U.S.C. §105"',
    }
    return _entry("publication", defaults, fields)


def source(**fields: object) -> str:
    """A [[source]] "s" citing publication "p", with ``fields`` changed (None drops one)."""
    defaults: dict[str, object] = {
        "id": '"s"',
        "publication": '"p"',
        "locator": '"§1"',
        "accessed": "2026-10-17",
    }
    return _entry("source", defaults, fields)


def table(*entries: str) -> str:
    return HEADER + "".join(entries)


CITED = {"license": '"cite_only_fact"', "public_domain_basis": None}
"""A publication's fields for a cite-only fact."""
BOOK = {"kind": '"book"', "edition": '"29th ed."', **CITED}
ONLINE = {
    "kind": '"article"',
    "url": '"https://example.org/a"',
    **CITED,
    "terms_url": '"https://example.org/terms"',
    "terms_checked": "2026-10-17",
    "terms_outcome": '"permits_reuse"',
}
OWN = {"kind": '"own_measurement"', "license": '"own_measurement"', "public_domain_basis": None}


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("[table\n", "not valid TOML"),
        (publication(), r"missing the \[table\] header"),
        ('[table]\nschema = 1\nname = "T"\n', "missing"),
        (HEADER.replace("schema = 1", "schema = 2"), "schema 2 isn't supported"),
        (HEADER.replace("version = 1", "version = 0"), "version must be"),
        (table("[[sytem]]\nid = 1\n"), r"unknown top-level keys \['sytem'\]"),
        (table("[publication]\nid = 1\n"), r"each \[\[publication\]\] must be a table"),
        (table(publication(title=None)), "missing"),
        (table(publication(title='" "')), "needs a title"),
        (table(publication(license='"vendor"')), "has 'vendor'; allowed"),
        (table(publication(lisence='"x"')), "unknown keys"),
        (table(publication(locator='"§1"')), r"unknown keys \['locator'\]"),
        (table(publication(), publication()), "publication 'p' is declared twice"),
        (table(publication(), source(locator=None)), "missing"),
        (table(publication(), source(locator='" "')), "needs a locator"),
        (table(publication(), source(accessed='"2026-10-17"')), "must be a date"),
        (table(publication(), source(kind='"book"')), r"unknown keys \['kind'\]"),
        (table(publication(), source(), source()), "source 's' is declared twice"),
        (table(publication(), source(publication='"q"')), "cites publication 'q', which isn't"),
        (table(publication(), source(publication="1")), "needs a publication"),
        (table(publication(third_party="true")), "cite-only"),
        (table(publication(**{**BOOK, "edition": None})), "needs an edition"),
        (table(publication(public_domain_basis=None)), "public-domain statute needs a public"),
        (
            table(publication(kind='"government_document"', public_domain_basis=None)),
            "public-domain government_document needs a public_domain_basis",
        ),
        (table(publication(kind='"book"', edition='"1st ed."', public_domain_basis=None)), "basis"),
        (table(publication(**{**CITED, "public_domain_basis": '"x"'})), "only a public-domain"),
        (table(publication(**{**ONLINE, "url": None})), "needs a url"),
        (table(publication(**{**ONLINE, "terms_checked": None})), "terms weren't read"),
        (table(publication(**{**ONLINE, "terms_outcome": '"unreadable"'})), "must permit reuse"),
        (table(publication(cite_only_cap="1")), "only a cite-only publication"),
        (
            table(publication(**CITED, cite_only_cap=str(MAX_CITE_ONLY_PER_PUBLICATION + 1))),
            "above the ceiling",
        ),
        (table(publication(**{**BOOK, "license": '"own_measurement"'})), "goes with the own_"),
        (table(publication(**{**OWN, "license": '"cite_only_fact"'})), "goes with the own_"),
        (
            table(publication(**BOOK), publication(**{**BOOK, "id": '"q"'})),
            "publications 'p' and 'q' have the same title and edition",
        ),
    ],
)
def test_a_table_that_breaks_the_schema_is_refused(text: str, message: str) -> None:
    with pytest.raises(SpecError, match=message):
        parse_table(text, "test", SAMPLE_KEYS)


def test_the_probed_sources_are_refused() -> None:
    """A handbook as public domain, and an article whose terms weren't read, can't be entered."""
    handbook = publication(
        kind='"book"',
        title='"Machinery\'s Handbook"',
        edition='"29th ed."',
        public_domain_basis=None,
    )
    with pytest.raises(SpecError, match="public-domain book needs a public_domain_basis"):
        parse_table(table(handbook), "test", SAMPLE_KEYS)
    article = publication(kind='"article"', url='"https://example.org/a"', **CITED)
    with pytest.raises(SpecError, match="terms weren't read"):
        parse_table(table(article), "test", SAMPLE_KEYS)
    website = publication(kind='"website"', **CITED)
    with pytest.raises(SpecError, match="needs a url"):
        parse_table(table(website), "test", SAMPLE_KEYS)


PUBLIC_DOMAIN_HOSTS = (".gov", ".mil")
"""Host suffixes a public-domain publication's url may have.

US federal and military sites publish works that 17 U.S.C. §105 places in the public
domain. A url anywhere else fails this test until someone adds its host on purpose, so a
vendor page can't pass as a government document. It is a tripwire for review, not a
ruling: ``public_domain_basis`` states the claim, and a state .gov work needs its own,
since §105 covers federal works only.
"""
PUBLIC_DOMAIN_MIRRORS = frozenset({"everyspec.com"})
"""Named mirrors: everyspec.com republishes DoD specifications and handbooks, which are
public domain at their source."""
PUBLIC_DOMAIN_PRINTED: frozenset[tuple[str, str]] = frozenset()
"""Public-domain publications with no url, by (table name, publication id).

A printed work, such as a book published before 1930, has no host to check, so it passes
only when named here on purpose, with a comment on why it is public domain. None ships.
"""


def off_allowlist(
    reference_table: ReferenceTable,
    printed: frozenset[tuple[str, str]] = PUBLIC_DOMAIN_PRINTED,
) -> list[str]:
    """Return the table's public-domain publications not on the allowlist, by host or id."""
    off = []
    for work in reference_table.publications.values():
        if work.license is not License.PUBLIC_DOMAIN:
            continue
        if not work.url:
            if (reference_table.name, work.id) not in printed:
                off.append(f"{work.id} (no url)")
            continue
        host = (urlsplit(work.url).hostname or "").removeprefix("www.")
        if not (host.endswith(PUBLIC_DOMAIN_HOSTS) or host in PUBLIC_DOMAIN_MIRRORS):
            off.append(host or work.url)
    return off


def test_every_shipped_public_domain_url_is_on_the_host_allowlist() -> None:
    for spec in REFERENCE_TABLES:
        assert off_allowlist(spec.load()) == [], spec.filename


def test_a_vendor_chart_cant_pass_as_a_government_document() -> None:
    """The reviewer's probe: a vendor page declared a government document, public domain."""
    probe = {
        "kind": '"government_document"',
        "title": '"Vendor gauge chart"',
        "url": '"https://vendor.example.com/gauge-chart"',
    }
    unclaimed = table(publication(**probe, public_domain_basis=None), source())
    with pytest.raises(SpecError, match="needs a public_domain_basis"):
        parse_table(unclaimed, "test", SAMPLE_KEYS)
    claimed = parse_table(table(publication(**probe), source()), "test", SAMPLE_KEYS)
    assert off_allowlist(claimed) == ["vendor.example.com"], "the basis is claimed, not checked"
    allowed = [
        publication(id=f'"p{n}"', title=f'"S{n}"', url=f'"{url}"')
        for n, url in enumerate(
            (
                "https://uscode.house.gov/view.xhtml",
                "https://nvlpubs.nist.gov/nistpubs/",
                "https://www.everyspec.com/MIL-HDBK/",
                "https://quicksearch.dla.mil/",
            )
        )
    ]
    assert off_allowlist(parse_table(table(*allowed), "test", SAMPLE_KEYS)) == []


def test_a_public_domain_publication_without_a_url_must_be_named_on_purpose() -> None:
    """The reviewer's probe: the vendor chart again, with a basis claimed and no url."""
    probe = publication(kind='"government_document"', title='"Vendor gauge chart"')
    unhosted = parse_table(table(probe, source()), "test", SAMPLE_KEYS)
    assert off_allowlist(unhosted) == ["p (no url)"]
    assert off_allowlist(unhosted, printed=frozenset({("T", "p")})) == []
    assert off_allowlist(unhosted, printed=frozenset({("Other table", "p")})) == ["p (no url)"]
    cited = parse_table(table(publication(**BOOK)), "test", SAMPLE_KEYS)
    assert off_allowlist(cited) == [], "only public-domain publications are held to it"


@pytest.mark.parametrize(
    ("first", "second", "same"),
    [
        ("29th ed.", "29", True),
        ("29th ed.", "29th", True),
        ("29th ed.", "29TH Edition", True),
        ("29th ed.", "30th ed.", False),
        ("A568/A568M-25a", "a568 a568m 25a", True),
        ("A568/A568M-25a", "A568/A568M-24", False),
        ("2024 ed.", "2024", True),
    ],
)
def test_editions_compare_by_their_leading_number(first: str, second: str, same: bool) -> None:
    pair = table(
        publication(**{**BOOK, "id": '"a"', "edition": f'"{first}"'}),
        publication(**{**BOOK, "id": '"b"', "edition": f'"{second}"'}),
    )
    if same:
        with pytest.raises(SpecError, match="same title and edition"):
            parse_table(pair, "test", SAMPLE_KEYS)
    else:
        assert set(parse_table(pair, "test", SAMPLE_KEYS).publications) == {"a", "b"}


def cite_only_totals(
    tables: Iterable[tuple[ReferenceTable, Iterable[ReferenceValue]]],
) -> Counter[tuple[str, str]]:
    """Count the values each cite-only work defines, across tables, by its loose identity."""
    totals: Counter[tuple[str, str]] = Counter()
    for reference_table, values in tables:
        for value in values:
            work = reference_table.sources[value.source].publication
            if work.license is License.CITE_ONLY_FACT:
                totals[work.work] += 1
    return totals


def test_no_cite_only_work_exceeds_the_ceiling_across_the_shipped_tables() -> None:
    totals = cite_only_totals(
        (t, spec.values(t)) for spec in REFERENCE_TABLES for t in [spec.load()]
    )
    assert totals, "the gauge table defines one cite-only value"
    assert max(totals.values()) <= MAX_CITE_ONLY_PER_PUBLICATION, totals


def test_a_work_split_across_tables_is_counted_once() -> None:
    """Two tables, each citing the 29th edition for one value, define two values from it."""
    value = ReferenceValue(1.0, "s", Basis.TYPICAL, TrustLevel.HANDBOOK_RULE)

    def handbook(edition: str) -> ReferenceTable:
        work = publication(**{**BOOK, "edition": f'"{edition}"'}, cite_only_cap="1")
        return parse_table(table(work, source()), "test", SAMPLE_KEYS)

    totals = cite_only_totals([(handbook("29th ed."), [value]), (handbook("29"), [value])])
    assert list(totals.values()) == [2]
    assert max(totals.values()) > MAX_CITE_ONLY_PER_PUBLICATION


def test_a_book_split_into_several_entries_stays_under_its_cap() -> None:
    """The reviewer's probe: one handbook cited five ways, each with its own cap of 1."""
    values = [constant(float(n), f"s{n}", f"c{n}") for n in range(5)]
    one_work = table(
        publication(**BOOK, title='"Machinery\'s Handbook"', cite_only_cap="1"),
        *(source(id=f'"s{n}"', locator=f'"p. {n}"') for n in range(5)),
    )
    with pytest.raises(SpecError, match="publication 'p' defines 5 values; its cap is 1"):
        parse_table(one_work, "test", SAMPLE_KEYS, SAMPLE_QUANTITIES).check_values(values)

    spellings = ("Machinery's Handbook", "MACHINERY’S  HANDBOOK", "Machinerys Handbook")
    editions = ("29th ed.", "29th Ed", "29TH ED.")

    def book(key: str, title: str, edition: str = "29th ed.") -> str:
        return publication(**{**BOOK, "id": f'"{key}"', "edition": f'"{edition}"'}, title=title)

    split = table(
        *(
            book(f"p{n}", f'"{title}"', edition)
            for n, (title, edition) in enumerate(zip(spellings, editions, strict=True))
        )
    )
    with pytest.raises(SpecError, match="'p0' and 'p1' have the same title and edition"):
        parse_table(split, "test", SAMPLE_KEYS)
    for title, edition in zip(spellings[1:], editions[1:], strict=True):
        pair = table(book("a", f'"{spellings[0]}"'), book("b", f'"{title}"', edition))
        with pytest.raises(SpecError, match="same title and edition"):
            parse_table(pair, "test", SAMPLE_KEYS)
    other_edition = table(
        book("a", f'"{spellings[0]}"'), book("b", f'"{spellings[0]}"', "30th ed.")
    )
    assert set(parse_table(other_edition, "test", SAMPLE_KEYS).publications) == {"a", "b"}


def test_public_domain_states_its_basis_and_own_measurements_are_their_own_kind() -> None:
    old_book = publication(
        kind='"book"', edition='"1st ed."', public_domain_basis='"published before 1930"'
    )
    parsed = parse_table(table(old_book), "test", SAMPLE_KEYS).publications["p"]
    assert (parsed.license, parsed.public_domain_basis) == (
        License.PUBLIC_DOMAIN,
        "published before 1930",
    )
    report = publication(kind='"government_document"')
    assert (
        parse_table(table(report), "test", SAMPLE_KEYS).publications["p"].kind
        is PublicationKind.GOVERNMENT_DOCUMENT
    )
    article = publication(**ONLINE)
    assert parse_table(table(article), "test", SAMPLE_KEYS).publications["p"].terms_checked == (
        ACCESSED
    )
    log = parse_table(table(publication(**OWN), source()), "test", SAMPLE_KEYS)
    assert log.sources["s"].publication.license is License.OWN_MEASUREMENT


def test_a_cite_only_publication_may_define_only_its_capped_number_of_values() -> None:
    sample = sample_table()

    def computed(name: str) -> ReferenceValue:
        return constant(
            2.657,
            "statute",
            name,
            corroborating=("handbook",),
            basis=Basis.NOMINAL_DEFINITION,
            trust=TrustLevel.VERIFIED_DERIVATION,
        )

    basis = constant(41.82, "handbook", "basis")
    # A corroborating source defines nothing, so the handbook defines only the basis.
    sample.check_values([computed("12"), computed("14"), basis])

    with pytest.raises(SpecError, match="'handbook' defines 2 values; its cap is 1"):
        sample.check_values([computed("12"), basis, constant(41.0, "handbook", "basis_2")])
    appendix = constant(9.0, "handbook_appendix", "appendix")
    with pytest.raises(SpecError, match="'handbook' defines 2 values; its cap is 1"):
        sample.check_values([basis, appendix])
    with pytest.raises(SpecError, match="unknown sources"):
        sample.check_values([constant(1.0, "vendor_page", "stray")])
    with pytest.raises(SpecError, match="unknown sources"):
        sample.check_values([constant(1.0, "statute", "hidden", corroborating=("nowhere",))])


def test_a_reference_value_agrees_with_its_stated_text() -> None:
    stated = TypedValue.parse("0.1046 in", Dimension.LENGTH)
    value = ReferenceValue(
        stated.value, "s", Basis.NOMINAL_DEFINITION, TrustLevel.VERIFIED_DERIVATION, stated=stated
    )
    assert value.stated == stated
    with pytest.raises(SpecError, match="doesn't equal"):
        ReferenceValue(2.0, "s", Basis.TYPICAL, TrustLevel.RULE_OF_THUMB, stated=stated)


IN = 25.4
"""Millimetres per inch."""


def band(low: float, high: float, *, low_in: bool = True, high_in: bool = True) -> Band:
    """A thickness band, its ends given in inches."""
    return Band(low * IN, high * IN, Dimension.LENGTH, low_in, high_in)


def test_a_band_holds_its_ends_as_it_says() -> None:
    closed = band(0.012, 0.051)
    above = band(0.051, 0.090, low_in=False)
    assert closed.contains(0.012 * IN) and closed.contains(0.051 * IN)
    assert not closed.contains(0.0119 * IN)
    assert not above.contains(0.051 * IN) and above.contains(0.090 * IN)
    assert not closed.overlaps(above) and not above.overlaps(closed)
    assert closed.overlaps(band(0.051, 0.090)), "two closed bands sharing an end overlap"
    assert closed.overlaps(band(0.020, 0.030)) and not closed.overlaps(band(0.06, 0.07))
    point = Band(1.0, 1.0, Dimension.LENGTH)
    assert point.contains(1.0) and point.overlaps(Band(0.0, 1.0, Dimension.LENGTH))
    assert str(above) == "(1.2954 mm, 2.286 mm]"


@pytest.mark.parametrize(
    ("ends", "message"),
    [
        ((2.0, 1.0, True, True), "holds no value"),
        ((1.0, 1.0, False, True), "holds no value"),
        ((math.inf, math.inf, True, True), "finite"),
        ((math.nan, 1.0, True, True), "finite"),
    ],
)
def test_a_band_must_hold_a_value(ends: tuple[float, float, bool, bool], message: str) -> None:
    low, high, low_in, high_in = ends
    with pytest.raises(SpecError, match=message):
        Band(low, high, Dimension.LENGTH, low_in, high_in)


def test_bands_of_different_dimensions_cant_be_compared() -> None:
    with pytest.raises(UsageError, match="different dimensions"):
        band(0, 1).overlaps(Band(0.0, 90.0, Dimension.ANGLE))


def test_a_values_conditions_are_checked_and_kept_read_only() -> None:
    value = ReferenceValue(
        1.0, "s", Basis.TYPICAL, TrustLevel.HANDBOOK_RULE, conditions={"temper": "temper:t6"}
    )
    assert dict(value.conditions) == {"temper": "temper:t6"}
    with pytest.raises(TypeError):
        value.conditions["temper"] = "temper:o"  # type: ignore[index]
    for bad in ({"Temper": "temper:t6"}, {"temper": " "}, {"temper": 6}):
        with pytest.raises(SpecError, match="Condition"):
            ReferenceValue(
                1.0,
                "s",
                Basis.TYPICAL,
                TrustLevel.HANDBOOK_RULE,
                conditions=bad,  # type: ignore[arg-type]
            )


def radius(source: str, thickness: Band | None, material: str = "al:6061") -> ReferenceValue:
    """A banded minimum-radius value for one material; the value itself is invented."""
    return ReferenceValue(
        2.0,
        source,
        Basis.RULE_OF_THUMB,
        TrustLevel.HANDBOOK_RULE,
        quantity="min_radius",
        band=thickness,
        conditions={"material": material},
    )


def test_bands_in_one_series_must_not_overlap() -> None:
    """A series is one quantity, from one source, under one set of conditions, at one basis."""
    sample = sample_table()
    low, high = band(0.012, 0.051), band(0.051, 0.090, low_in=False)
    sample.check_values([radius("statute", low), radius("statute", high)])
    with pytest.raises(SpecError, match="overlapping bands"):
        sample.check_values([radius("statute", low), radius("statute", band(0.051, 0.090))])
    with pytest.raises(SpecError, match="both with and without a band"):
        sample.check_values([radius("statute", low), radius("statute", None)])
    with pytest.raises(SpecError, match="twice without a band"):
        sample.check_values([radius("statute", None), radius("statute", None)])
    angle = Band(0.0, 90.0, Dimension.ANGLE)
    with pytest.raises(SpecError, match="bands of different dimensions"):
        sample.check_values([radius("statute", low), radius("statute", angle)])


def test_other_sources_quantities_and_conditions_are_other_series() -> None:
    """Sources may overlap: where they disagree, every one is shown (ADR-0014 M4)."""
    sample = sample_table()
    low = band(0.012, 0.051)
    sample.check_values(
        [
            radius("statute", low),
            radius("handbook", low),
            replace(radius("statute", low), quantity="f_tu"),
            radius("statute", low, material="al:5052"),
            replace(radius("statute", low), basis=Basis.A_BASIS),
        ]
    )
    sample.check_values([constant(1.0, "statute", "a"), constant(2.0, "statute", "b")])


def test_a_tables_values_are_its_declared_quantities_with_the_same_conditions() -> None:
    """Lookups match conditions exactly, so a quantity names the same keys throughout."""
    sample = sample_table()
    low, high = band(0.012, 0.051), band(0.051, 0.090, low_in=False)
    with pytest.raises(SpecError, match="quantity 'tonnage' isn't declared"):
        sample.check_values([replace(radius("statute", low), quantity="tonnage")])
    tempered = replace(
        radius("statute", high), conditions={"material": "al:6061", "temper": "temper:6061_t6"}
    )
    with pytest.raises(
        SpecError, match=r"name conditions \['material'\] and \['material', 'temper'\]"
    ):
        sample.check_values([radius("statute", low), tempered])


def test_a_values_key_is_its_series_and_band() -> None:
    value = radius("statute", band(0.012, 0.051))
    assert value.series == (
        "min_radius",
        "statute",
        (("material", "al:6061"),),
        Basis.RULE_OF_THUMB,
    )
    assert value.key == (*value.series, band(0.012, 0.051))
    assert replace(value, value=3.0).key == value.key, "the key names the entry, not its number"


def test_every_shipped_table_loads_within_the_ceiling_and_is_pinned_to_its_version() -> None:
    digests = {}
    for spec in REFERENCE_TABLES:
        loaded = spec.load()
        assert all(
            p.cite_only_cap <= MAX_CITE_ONLY_PER_PUBLICATION for p in loaded.publications.values()
        )
        digests[loaded.name, loaded.version] = loaded.digest
    assert digests == TABLE_DIGESTS, (
        "a table's data changed without a version bump, or it isn't pinned"
    )


def test_the_digest_follows_the_content() -> None:
    first = parse_table(table(publication()), "test", SAMPLE_KEYS).digest
    assert parse_table(table(publication()), "test", SAMPLE_KEYS).digest == first
    assert parse_table(table(publication(title='"T"')), "test", SAMPLE_KEYS).digest != first


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
