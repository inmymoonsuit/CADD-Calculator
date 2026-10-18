"""Translation: the deferred API, catalogs, plural categories, and the catalog checks (ADR-0020)."""

from __future__ import annotations

import builtins
import gettext
import re
from pathlib import Path
from typing import Any

import pytest
from babel.messages.catalog import Catalog

from caddcalc.core import i18n
from caddcalc.core.errors import UsageError
from tests.catalogs import shipped, tooling


def _british(folder: Path) -> Path:
    """Compile a small British catalog into ``folder``, as the build will."""
    catalog = Catalog(locale="en_GB", domain="caddcalc")
    catalog.add("millimeter", "millimetre")
    catalog.add("Copy", "Copy (verb)", context="button")
    catalog.add(("{count} field", "{count} fields"), ("{count} field (GB)", "{count} fields (GB)"))
    tooling().compile_to(catalog, folder / "en_GB" / "LC_MESSAGES" / "caddcalc.mo")
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


ABOUT = "About {product}: version, license, and terms"
BRITISH = "About {product}: version, licence, and terms"
"""A string the British catalog spells its own way."""


@pytest.mark.parametrize(
    "tag", ["en_GB", "en-AU", "en_NZ", "en_IE", "en_ZA", "en_IN", "en_CA", "en_AT", "en_001"]
)
def test_english_outside_the_us_reads_the_british_catalog(tmp_path: Path, tag: str) -> None:
    """CLDR's en_001 and its children, and en_CA, which ADR-0020 §2 adds."""
    i18n.use([tag], directories=[shipped(tmp_path, "en_001")])
    assert "en_001" in i18n.lineage(tag)
    assert i18n._("About {product}: version, license, and terms") == BRITISH


@pytest.mark.parametrize("tag", ["en_US", "en", "en_PR", "en_PH", "fr_FR"])
def test_us_english_and_other_languages_keep_the_source_spelling(tmp_path: Path, tag: str) -> None:
    i18n.use([tag], directories=[shipped(tmp_path, "en_001")])
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
    tools = tooling()
    monkeypatch.setattr(tools, "LOCALE", tmp_path)
    path = tools.init("de")
    catalog = tools.read(path)
    assert tools.keys(catalog) == tools.keys(tools.read(tools.TEMPLATE))
    forms = [m.string if isinstance(m.string, tuple) else (m.string,) for m in catalog if m.id]
    assert not catalog.fuzzy and not any(any(f) for f in forms), "nothing translated"
    with pytest.raises(FileExistsError, match="update"):
        tools.init("de")


def test_an_untranslated_message_is_left_out_so_the_next_catalog_answers() -> None:
    """Babel compiles an untranslated plural as the source text, which would hide en_001's."""
    tools = tooling()
    catalog = Catalog(locale="en_CA", domain="caddcalc")
    catalog.add(("meter", "meters"), ("", ""), context="unit")
    catalog.add("Sheet Metal", "")
    catalog.add(("percent", "percent"), ("percent", "percent"), context="unit")
    assert [m.id for m in tools.translated(catalog) if m.id] == [("percent", "percent")]


def test_a_plural_translated_in_part_is_caught(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    tools = tooling()
    monkeypatch.setattr(tools, "LOCALE", tmp_path)
    path = tools.init("de")
    catalog = tools.read(path)
    catalog.get(("inch", "inches"), context="unit").string = ("Zoll", "")
    path.write_bytes(tools.po_text(catalog))
    monkeypatch.setattr(tools, "TEMPLATE", tools.ROOT / "src/caddcalc/locale/caddcalc.pot")
    assert any("'inch' translates only some" in p for p in tools.check())


def test_a_fuzzy_translation_is_caught(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Babel's guess after a source change isn't compiled, so it waits to be confirmed."""
    tools = tooling()
    monkeypatch.setattr(tools, "LOCALE", tmp_path)
    path = tools.init("de")
    catalog = tools.read(path)
    message = catalog.get("Sheet Metal")
    message.string, message.flags = "Blech", {"fuzzy"}
    path.write_bytes(tools.po_text(catalog))
    monkeypatch.setattr(tools, "TEMPLATE", tools.ROOT / "src/caddcalc/locale/caddcalc.pot")
    assert any("'Sheet Metal' is fuzzy" in p for p in tools.check())


def test_every_unit_name_is_marked_as_a_plural_pair_in_the_unit_context() -> None:
    """ADR-0019 U5: names in US English, translated where they're shown."""
    from caddcalc.core.units import UNITS
    from caddcalc.core.units.model import NAME_CONTEXT

    tools = tooling()
    template = tools.read(tools.TEMPLATE)
    for unit in (u for u in UNITS if u.symbol):
        message = template.get((unit.name, unit.spoken_plural), context=NAME_CONTEXT)
        assert message is not None and message.id == (unit.name, unit.spoken_plural), unit.symbol


@pytest.mark.parametrize(
    ("symbol", "shown", "spoken"),
    [
        ("mm", "1", "millimeter"),
        ("mm", "-1", "millimeter"),
        ("mm", "1.0000", "millimeters"),
        ("mm", "0.5", "millimeters"),
        ("mm", "0", "millimeters"),
        ("in", "1", "inch"),
        ("in", "0.3119", "inches"),
        ("ft", "2", "feet"),
        ("%", "1", "percent"),
        ("%", "44", "percent"),
        ("", "0.44", ""),
    ],
)
def test_a_spoken_name_follows_the_number_as_shown(symbol: str, shown: str, spoken: str) -> None:
    """US English, the source: singular only after a shown 1 (ADR-0020 §5)."""
    from caddcalc.core.units import get_unit

    assert get_unit(symbol).spoken(shown) == spoken


@pytest.mark.parametrize(
    ("tag", "symbol", "shown", "spoken"),
    [
        ("en_GB", "mm", "1", "millimetre"),
        ("en_GB", "mm", "0.3119", "millimetres"),
        ("en_AU", "cm", "2", "centimetres"),
        ("en_IE", "m", "1", "metre"),
        ("en_GB", "%", "44", "per cent"),
        ("en_GB", "in", "1.0000", "inches"),
        ("en_CA", "mm", "2", "millimetres"),
        ("en_CA", "%", "44", "percent"),
        ("en_US", "mm", "2", "millimeters"),
    ],
)
def test_a_spoken_name_is_in_the_language_text_is_shown_in(
    tmp_path: Path, tag: str, symbol: str, shown: str, spoken: str
) -> None:
    """CLDR 47's names: en_001 writes "millimetre" and "per cent"; en_CA, "percent"."""
    from caddcalc.core.units import get_unit

    folder = shipped(shipped(tmp_path, "en_001"), "en_CA")
    i18n.use([tag], directories=[folder])
    assert get_unit(symbol).spoken(shown) == spoken


def test_the_plural_rule_is_the_language_the_text_is_in(tmp_path: Path) -> None:
    """A language with no catalog shows the source text, so it takes English's rule."""
    folder = shipped(tmp_path, "en_001")
    assert i18n.text_language() == "en"
    i18n.use(["fr_FR", "en_GB"], directories=[folder])
    assert i18n.text_language() == "en_001", "French has no catalog; British comes next"
    i18n.use(["fr_FR"], directories=[folder])
    assert i18n.text_language() == "en"
    assert i18n.npgettext_shown("unit", "inch", "inches", "1,0") == "inches", "a comma too"


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
        ("FR", "fr"),
        ("", ""),
        # A script is kept only where it isn't the language's usual one (S&R's i1 L4).
        ("zh-Hant-TW", "zh_Hant_TW"),
        ("sr-Latn-RS", "sr_Latn_RS"),
        ("sr-Cyrl-RS", "sr_RS"),
        ("sr@latin", "sr_Latn"),
        ("sr_RS@latin", "sr_Latn_RS"),
        ("de_DE@euro", "de_DE"),
        # No language at all: the source (S&R's i1 L5).
        ("C", ""),
        ("POSIX", ""),
        ("C.UTF-8", ""),
        ("x-pseudo", ""),
        ("i-klingon", ""),
        ("en-XA", "en_XA"),
    ],
)
def test_language_tags_are_named_as_gettext_names_catalogs(tag: str, posix: str) -> None:
    assert i18n.posix_language(tag) == posix


@pytest.mark.parametrize(
    ("tag", "lineage"),
    [
        ("zh-Hant-TW", ("zh_Hant_TW", "zh_Hant")),
        ("sr_RS@latin", ("sr_Latn_RS", "sr_Latn")),
        ("zh-Hans-CN", ("zh_CN", "zh")),
    ],
)
def test_a_locale_in_another_script_never_falls_back_to_its_usual_script(
    tag: str, lineage: tuple[str, ...]
) -> None:
    """Traditional Chinese never reads Simplified, nor Latin Serbian the Cyrillic."""
    assert i18n.lineage(tag) == lineage


def test_the_usual_scripts_are_cldrs() -> None:
    """Every language CLDR has locales for in more than one script, with its usual one."""
    babel = pytest.importorskip("babel")
    from babel.core import get_global, parse_locale

    multi = {
        parse_locale(name)[0]
        for name in babel.localedata.locale_identifiers()
        if parse_locale(name)[2]
    }
    likely = get_global("likely_subtags")
    usual = {language: parse_locale(likely[language])[2] for language in multi}
    assert usual == i18n._SCRIPTS


def test_a_lookup_begun_before_a_new_choice_never_answers_for_it(tmp_path: Path) -> None:
    """S&R's i1 L2: a catalog read under the old choice is cached under the old choice."""
    import threading

    folder = shipped(tmp_path, "en_001")
    i18n.use(["en_GB"], directories=[folder])
    reading, chosen = threading.Event(), threading.Event()
    catalog = i18n._catalog

    def slow(language: str, directories: Any) -> Any:
        if threading.current_thread() is not threading.main_thread():
            reading.set()
            assert chosen.wait(10)
        return catalog(language, directories)

    old: list[str] = []
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(i18n, "_catalog", slow)
        lookup = threading.Thread(target=lambda: old.append(i18n._(ABOUT)))
        lookup.start()
        assert reading.wait(10)
        i18n.use(["fr"], directories=[folder])
        chosen.set()
        lookup.join(10)
    assert old == [BRITISH], "the old choice's lookup answered for the old choice"
    assert i18n.languages() == ("fr",)
    assert i18n._(ABOUT) == ABOUT, "and the new one reads its own catalogs"


def test_nothing_is_translated_at_import_time() -> None:
    """S&R's i1: text is translated where it's shown, never where it's declared (§1).

    A call at module or class level would run as the module is imported, before a front
    end has chosen the language.
    """
    import ast

    calls = {"_", "gettext", "pgettext", "ngettext", "npgettext", "npgettext_shown", "use"}

    def run_on_import(body: list[ast.stmt]) -> list[ast.AST]:
        """What a module's or a class's body runs as it's defined: not functions' bodies."""
        found: list[ast.AST] = []
        for statement in body:
            if isinstance(statement, ast.FunctionDef | ast.AsyncFunctionDef):
                args = statement.args
                found += [*statement.decorator_list, *args.defaults, *args.kw_defaults]
            elif isinstance(statement, ast.ClassDef):
                found += [*statement.decorator_list, *statement.bases, *statement.keywords]
                found += run_on_import(statement.body)
            else:
                found.append(statement)
        return [node for node in found if node is not None]

    found = []
    for path in sorted((Path(i18n.__file__).parents[1]).rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for top in run_on_import(tree.body):
            for node in ast.walk(top):
                func = getattr(node, "func", None)
                name = getattr(func, "id", None) or getattr(func, "attr", None)
                if isinstance(node, ast.Call) and name in calls:
                    found.append(f"{path.name}:{node.lineno}")
    assert found == [], found


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
    tools = tooling()
    monkeypatch.setattr(tools, "SOURCE", tmp_path)
    catalog = tools.extract()
    wanted = {("Bend allowance", None), ("in", "unit"), ("{count} field", None)}
    assert tools.keys(catalog) == wanted
    assert catalog.get("in", context="unit").auto_comments == ['the unit, as in "3 in".']
    assert catalog.get(("{count} field", "{count} fields")).id[1] == "{count} fields"


def test_the_catalogs_are_current() -> None:
    """The template matches every marked string, and every language the template."""
    assert tooling().check() == []


def test_a_stale_template_or_language_is_caught(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    tools = tooling()
    stale = Catalog(domain="caddcalc")
    stale.add("A string no code marks")
    template = tmp_path / "caddcalc.pot"
    template.write_bytes(tools.po_text(stale))
    monkeypatch.setattr(tools, "TEMPLATE", template)
    assert any("out of date" in p for p in tools.check())


def test_every_translation_keeps_its_sources_placeholders() -> None:
    """A translation may reorder named fields, never drop, add, or rename one (§1)."""
    tools = tooling()
    catalog = Catalog(locale="en_GB", domain="caddcalc")
    catalog.add("{value} is below {limit}", "{limit} is above {value}")
    assert tools.placeholder_mismatches(catalog) == [], "reordered is fine"
    catalog.add("{value} is past {limit}", "{value} is past the limit")
    catalog.add(("{count} field", "{count} fields"), ("{count} field", "{number} fields"))
    problems = tools.placeholder_mismatches(catalog)
    assert len(problems) == 2 and "past the limit" in problems[0], problems
    for path in tools.languages():
        assert tools.placeholder_mismatches(tools.read(path)) == [], path


def test_a_plurals_forms_are_checked_one_by_one() -> None:
    """S&R's i1 L1: "one inch" may leave out the count; "inches" may not."""
    tools = tooling()
    catalog = Catalog(locale="en_GB", domain="caddcalc")
    catalog.add(("{n} inch", "{n} inches"), ("one inch", "{n} inches"))
    assert tools.placeholder_mismatches(catalog) == [], "the one form may leave it out"
    catalog.add(("{n} foot", "{n} feet"), ("{n} foot", "feet"))
    catalog.add(("{n} yard", "{n} yards"), ("{n} yard", "{n} yards {extra}"))
    assert len(tools.placeholder_mismatches(catalog)) == 2
    single = Catalog(locale="ja", domain="caddcalc")  # one form for every count
    single.add(("{n} inch", "{n} inches"), ("inch",))
    assert len(tools.placeholder_mismatches(single)) == 1, "its only form needs the count"


@pytest.mark.parametrize(
    ("text", "refused"),
    [
        ("{value} of {limit}", False),
        ("10% grade", False),
        ("{} of {}", True),
        ("Load %(name)s now", True),
        ("Load %s now", True),
        ("%d fields", True),
    ],
)
def test_marked_text_names_its_fields(text: str, refused: bool) -> None:
    """S&R's i1 L1: a positional or printf placeholder can't be checked or reordered."""
    tools = tooling()
    template = Catalog(domain="caddcalc")
    template.add(text)
    assert bool(tools.source_problems(template)) is refused


QUOTED = {
    "0.64": "Machinery's Handbook's formula, 0.64T + 1.57R, as published",
    "1.57": "the same formula",
    "0.55": "the Handbook's coefficient for soft brass and copper",
    "0.71": "the Handbook's coefficient for bronze and hard metals",
    "0.408": "K implied by the Handbook's formula, said beside it",
    "0.452": "K implied by the Handbook's Eq. (34), said beside it",
    "0.445": "FAA-H-8083-31B's K for aircraft aluminum",
    "0.4": "EDD5's instructional K",
    "0.5": "the limit K approaches, as the sources say",
    "0.156": "the course's hard-coded P",
    "0.1046": "the course example's thickness, 12 ga",
    "0.0747": "the course example's thickness, 14 ga",
}
"""Numbers typed into the calculators' prose, each quoted from a source, which stay as
published (ADR-0020 §4). Any other number the app writes is a value, formatted where it's
shown in the user's mark: a note names it as a field (``Method.quantities``)."""


def test_the_calculators_prose_holds_no_number_of_the_apps_own() -> None:
    """UI/UX's i4 L2: the string sweep, over method notes and summaries, and help texts."""
    from caddcalc.calculators import default_registry

    registry = default_registry(load_plugins=False)
    texts = [m.summary for c in registry for m in c.methods]
    texts += [note for c in registry for m in c.methods for note in m.notes]
    texts += [p.help for c in registry for p in c.params]
    texts += [s.help for d in registry.domains() for s in d.settings]
    typed = {number for text in texts for number in re.findall(r"\d+[.,]\d+", text or "")}
    assert typed <= QUOTED.keys(), sorted(typed - QUOTED.keys())


def test_the_shipped_languages_are_those_with_a_compiled_catalog(tmp_path: Path) -> None:
    """A packaged build reports them, so one that left a catalog out fails (i5)."""
    assert i18n.shipped_languages(tmp_path / "none") == ()
    assert i18n.shipped_languages(tmp_path) == ()
    written = tooling().compile_catalogs(tmp_path)
    assert {p.parents[1].name for p in written} == {"en_001", "en_CA"}
    assert i18n.shipped_languages(tmp_path) == ("en_001", "en_CA")
    (tmp_path / "fr" / "LC_MESSAGES").mkdir(parents=True)  # a .po alone isn't shipped
    assert i18n.shipped_languages(tmp_path) == ("en_001", "en_CA")
