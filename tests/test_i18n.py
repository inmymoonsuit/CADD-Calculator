"""Translation: the deferred API, catalogs, plural categories, and the catalog checks (ADR-0020)."""

from __future__ import annotations

import builtins
import gettext
import importlib.util
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
