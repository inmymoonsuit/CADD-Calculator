"""Translation: the deferred API, catalogs, plural categories, and the catalog checks (ADR-0020)."""

from __future__ import annotations

import builtins
import gettext
import importlib.util
import re
from collections.abc import Iterator
from pathlib import Path
from types import ModuleType

import pytest
from babel.messages.catalog import Catalog

from caddcalc.core import i18n
from caddcalc.core.errors import UsageError

SCRIPT = Path(__file__).parents[1] / "scripts" / "i18n.py"


def _tooling() -> ModuleType:
    """The catalog tooling script, loaded as a module."""
    spec = importlib.util.spec_from_file_location("i18n_tooling", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(autouse=True)
def _source_language() -> Iterator[None]:
    """Every test starts, and leaves, in the source language."""
    i18n.use(())
    yield
    i18n.use(())


def _british(folder: Path) -> Path:
    """Compile a small British catalog into ``folder``, as the build will."""
    catalog = Catalog(locale="en_GB", domain="caddcalc")
    catalog.add("millimeter", "millimetre")
    catalog.add("Copy", "Copy (verb)", context="button")
    catalog.add(("{count} field", "{count} fields"), ("{count} field (GB)", "{count} fields (GB)"))
    _tooling().compile_to(catalog, folder / "en_GB" / "LC_MESSAGES" / "caddcalc.mo")
    return folder


def test_text_is_in_the_source_language_until_a_language_is_chosen() -> None:
    assert i18n.languages() == ()
    assert i18n._("millimeter") == "millimeter"
    assert i18n.N_("millimeter") == "millimeter", "a marker only"
    assert i18n.ngettext("{count} field", "{count} fields", 1) == "{count} field"
    assert i18n.ngettext("{count} field", "{count} fields", 2) == "{count} fields"


def test_a_catalog_translates_where_text_is_shown(tmp_path: Path) -> None:
    i18n.use(["en-GB"], directories=[_british(tmp_path)])
    assert i18n.languages() == ("en_GB",)
    assert i18n._("millimeter") == "millimetre"
    assert i18n.pgettext("button", "Copy") == "Copy (verb)"
    assert i18n._("Copy") == "Copy", "a context keeps a short word apart"
    assert i18n.ngettext("{count} field", "{count} fields", 3) == "{count} fields (GB)"
    assert i18n._("not translated") == "not translated", "the source text, never an error"


def test_the_empty_string_stays_empty(tmp_path: Path) -> None:
    """For "", gettext returns a catalog's header (ADR-0020 §1)."""
    i18n.use(["en_GB"], directories=[_british(tmp_path)])
    assert i18n._("") == "" and i18n.pgettext("unit", "") == ""


def test_languages_fall_back_in_order_and_to_the_source(tmp_path: Path) -> None:
    folder = _british(tmp_path)
    i18n.use(["fr_FR", "en_GB"], directories=[folder])
    assert i18n._("millimeter") == "millimetre", "no French catalog: the next language"
    i18n.use(["de_DE"], directories=[folder])
    assert i18n._("millimeter") == "millimeter", "no catalog at all: the source"


def test_the_translator_is_cached_and_cleared() -> None:
    first = i18n.translator()
    assert i18n.translator() is first
    i18n.clear()
    assert i18n.translator() is not first


def test_nothing_is_installed_into_builtins_or_gettexts_globals(tmp_path: Path) -> None:
    """Python's guidance for libraries: no install(), no global domain."""
    before = getattr(builtins, "_", None)
    i18n.use(["en_GB"], directories=[_british(tmp_path)])
    i18n._("millimeter")
    assert getattr(builtins, "_", None) is before
    assert gettext.textdomain() == "messages"


BRITISH = "About {product}: version, licence, and terms"
"""A string the British catalog spells its own way."""


def _shipped(folder: Path, language: str) -> Path:
    """Compile the shipped ``language`` .po into ``folder``, as the build does."""
    tooling = _tooling()
    po = tooling.LOCALE / language / "LC_MESSAGES" / "caddcalc.po"
    tooling.compile_to(tooling.read(po), folder / language / "LC_MESSAGES" / "caddcalc.mo")
    return folder


@pytest.mark.parametrize(
    "tag", ["en_GB", "en-AU", "en_NZ", "en_IE", "en_ZA", "en_IN", "en_CA", "en_AT", "en_001"]
)
def test_english_outside_the_us_reads_the_british_catalog(tmp_path: Path, tag: str) -> None:
    """CLDR's en_001 and its children, and en_CA, which ADR-0020 §2 adds."""
    i18n.use([tag], directories=[_shipped(tmp_path, "en_001")])
    assert "en_001" in i18n.lineage(tag)
    assert i18n._("About {product}: version, license, and terms") == BRITISH


@pytest.mark.parametrize("tag", ["en_US", "en", "en_PR", "en_PH", "fr_FR"])
def test_us_english_and_other_languages_keep_the_source_spelling(tmp_path: Path, tag: str) -> None:
    i18n.use([tag], directories=[_shipped(tmp_path, "en_001")])
    assert "en_001" not in i18n.lineage(tag)
    assert i18n._("About {product}: version, license, and terms") == (
        "About {product}: version, license, and terms"
    )


@pytest.mark.parametrize(
    ("tag", "lineage"),
    [
        ("en_AT", ("en_AT", "en_150", "en_001", "en")),
        ("en-GB", ("en_GB", "en_001", "en")),
        ("en_US", ("en_US", "en")),
        ("de_AT", ("de_AT", "de")),
        ("en", ("en",)),
    ],
)
def test_a_locale_reads_its_parents_then_its_language(tag: str, lineage: tuple[str, ...]) -> None:
    assert i18n.lineage(tag) == lineage


def test_englishs_parent_locales_are_cldrs() -> None:
    """Every English locale CLDR has, as Babel ships it, has CLDR's parent, but en_CA.

    A Babel update with a newer CLDR fails here if CLDR moved a locale; the table in
    ``core.i18n`` names the version it's from.
    """
    from babel import localedata
    from babel.core import get_global

    exceptions = get_global("parent_exceptions")
    regional = [
        n for n in localedata.locale_identifiers() if re.fullmatch(r"en_([A-Z]{2}|\d{3})", n)
    ]
    assert len(regional) > 100, "Babel's CLDR data, not a stub"
    for name in regional:  # a script, such as en_Dsrt, has no region of its own
        cldr = exceptions.get(name, "en")
        expected = "en_001" if name == "en_CA" else cldr
        assert i18n.lineage(name)[1] == expected, name


def test_a_new_language_starts_from_the_template(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    tooling = _tooling()
    monkeypatch.setattr(tooling, "LOCALE", tmp_path)
    path = tooling.init("de")
    catalog = tooling.read(path)
    assert tooling.keys(catalog) == tooling.keys(tooling.read(tooling.TEMPLATE))
    assert not catalog.fuzzy and all(not m.string for m in catalog if m.id)
    with pytest.raises(FileExistsError, match="update"):
        tooling.init("de")


def test_a_fuzzy_translation_is_caught(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Babel's guess after a source change isn't compiled, so it waits to be confirmed."""
    tooling = _tooling()
    monkeypatch.setattr(tooling, "LOCALE", tmp_path)
    path = tooling.init("de")
    catalog = tooling.read(path)
    message = catalog.get("Sheet Metal")
    message.string, message.flags = "Blech", {"fuzzy"}
    path.write_bytes(tooling.po_text(catalog))
    monkeypatch.setattr(tooling, "TEMPLATE", tooling.ROOT / "src/caddcalc/locale/caddcalc.pot")
    assert any("'Sheet Metal' is fuzzy" in p for p in tooling.check())


@pytest.mark.parametrize("count", [1.0, 2.5, True])
def test_a_plural_form_needs_a_whole_count(count: object) -> None:
    """A shown decimal uses plural_category (§5): gettext's rules take whole counts."""
    with pytest.raises(UsageError, match="whole count"):
        i18n.ngettext("inch", "inches", count)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("tag", "posix"),
    [
        ("en-GB", "en_GB"),
        ("en_GB", "en_GB"),
        ("en-Latn-US", "en_US"),
        ("zh-Hans-CN", "zh_CN"),
        ("es-419", "es_419"),
        ("de_DE.UTF-8", "de_DE"),
        ("sr@latin", "sr"),
        ("FR", "fr"),
        ("", ""),
    ],
)
def test_language_tags_are_named_as_gettext_names_catalogs(tag: str, posix: str) -> None:
    assert i18n.posix_language(tag) == posix


@pytest.mark.parametrize(
    ("shown", "category"),
    [
        ("1", "one"),
        ("-1", "one"),
        ("+1", "one"),
        ("1.0", "other"),
        ("1.0000", "other"),
        ("0", "other"),
        ("0.5", "other"),
        ("2", "other"),
        ("21", "other"),
    ],
)
def test_the_plural_category_is_the_number_as_shown(shown: str, category: str) -> None:
    """CLDR's English rule: "one" only for i = 1 and v = 0 (ADR-0020 §5)."""
    assert i18n.plural_category(shown, "en") == category
    assert i18n.plural_category(shown, "fr_FR") == category, "no rule yet: English's"


def test_every_marked_string_is_extracted(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """``N_``, ``pgettext`` and the plural forms, with a translator's comment."""
    (tmp_path / "sample.py").write_text(
        "from caddcalc.core.i18n import N_, ngettext, pgettext\n"
        'NAME = N_("Bend allowance")\n'
        '# Translators: the unit, as in "3 in".\n'
        'UNIT = pgettext("unit", "in")\n'
        'FIELDS = ngettext("{count} field", "{count} fields", 2)\n',
        encoding="utf-8",
    )
    tooling = _tooling()
    monkeypatch.setattr(tooling, "SOURCE", tmp_path)
    catalog = tooling.extract()
    wanted = {("Bend allowance", None), ("in", "unit"), ("{count} field", None)}
    assert tooling.keys(catalog) == wanted
    assert catalog.get("in", context="unit").auto_comments == ['the unit, as in "3 in".']
    assert catalog.get(("{count} field", "{count} fields")).id[1] == "{count} fields"


def test_the_catalogs_are_current() -> None:
    """The template matches every marked string, and every language the template."""
    assert _tooling().check() == []


def test_a_stale_template_or_language_is_caught(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    tooling = _tooling()
    stale = Catalog(domain="caddcalc")
    stale.add("A string no code marks")
    template = tmp_path / "caddcalc.pot"
    template.write_bytes(tooling.po_text(stale))
    monkeypatch.setattr(tooling, "TEMPLATE", template)
    assert any("out of date" in p for p in tooling.check())


def test_every_translation_keeps_its_sources_placeholders() -> None:
    """A translation may reorder named fields, never drop, add, or rename one (§1)."""
    tooling = _tooling()
    catalog = Catalog(locale="en_GB", domain="caddcalc")
    catalog.add("{value} is below {limit}", "{limit} is above {value}")
    assert tooling.placeholder_mismatches(catalog) == [], "reordered is fine"
    catalog.add("{value} is past {limit}", "{value} is past the limit")
    catalog.add(("{count} field", "{count} fields"), ("{count} field", "{number} fields"))
    problems = tooling.placeholder_mismatches(catalog)
    assert len(problems) == 2 and "past the limit" in problems[0], problems
    for path in tooling.languages():
        assert tooling.placeholder_mismatches(tooling.read(path)) == [], path
