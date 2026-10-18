"""Translation: one gettext catalog per language, for core, calculators, CLI and GUI (ADR-0020).

Standard library only (ADR-0003). Text is translated where it's shown, never where it's
declared: a declaration marks its text with ``N_()``, which only lets the extraction tool
find it, and the front end or ``core.formatting`` passes it through ``_()`` as it shows
it. So a calculator module can be imported before the language is chosen.

* ``use(languages)`` chooses the languages, most wanted first, as ``posix_language`` tags
  such as ``en_GB``; a front end calls it once at startup. Until then, and for a language
  with no catalog, text stays in the source language, US English (L2).
* Catalogs are compiled ``.mo`` files in this package's ``locale`` folder, read through
  ``importlib.resources``, so they load from a wheel or a frozen build alike.
* Translatable text is one template per sentence, with named placeholders, so a
  translation can reorder its words.
* ``install()`` is never called: nothing is put into Python's builtins (Python's guidance
  for libraries).
"""

from __future__ import annotations

import gettext as _gettext
import re
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from functools import lru_cache
from importlib import resources
from importlib.resources.abc import Traversable
from pathlib import Path

from caddcalc.core.errors import UsageError

DOMAIN = "caddcalc"
"""The gettext domain: every catalog is ``<language>/LC_MESSAGES/caddcalc.mo``."""
LOCALE_PACKAGE = "caddcalc"
LOCALE_FOLDER = "locale"
"""Where the shipped catalogs are, inside the ``caddcalc`` package."""


@dataclass(frozen=True, eq=False)
class _Chosen:
    """What ``use()`` chose: the languages, and any catalog folders searched first.

    It's replaced whole, never changed, and the catalogs are cached by it, by identity
    (its folders needn't be hashable). So a lookup that began before a ``use()`` caches
    what it read under the old choice, and can never answer for the new one.
    """

    languages: tuple[str, ...] = ()
    directories: tuple[Traversable | Path, ...] = ()


_chosen = _Chosen()


def N_(message: str) -> str:  # noqa: N802 (gettext's name for a deferred marker)
    """Mark ``message`` for translation where it's declared, and return it unchanged.

    It's translated later, where it's shown, with ``_()``.
    """
    return message


def NP_(context: str, singular: str, plural: str) -> tuple[str, str]:  # noqa: N802, ARG001 (the context is for the extractor)
    """Mark a ``singular`` and ``plural`` pair, in ``context``, where it's declared.

    It returns the pair unchanged, for a declaration such as a unit's names, and is
    translated where it's shown, with ``npgettext_shown`` in the same ``context``. The
    pair is one message, so a language with more plural forms than two can give each.
    """
    return singular, plural


def use(languages: Iterable[str], *, directories: Sequence[Traversable | Path] = ()) -> None:
    """Choose the languages text is shown in, most wanted first; ``()`` is the source.

    Args:
        languages: Language tags such as ``"en_GB"`` or ``"en-GB"``.
        directories: Catalog folders searched before the shipped ones, for tests and the
            pseudo-locale.
    """
    global _chosen  # noqa: PLW0603 (one statement replaces the choice; see _Chosen)
    named = (posix_language(tag) for tag in languages)
    _chosen = _Chosen(tuple(dict.fromkeys(name for name in named if name)), tuple(directories))


def languages() -> tuple[str, ...]:
    """Return the languages chosen, most wanted first; empty for the source language."""
    return _chosen.languages


def clear() -> None:
    """Forget the loaded catalogs, so the next lookup reads them again; for tests."""
    _loaded.cache_clear()


@lru_cache(maxsize=1)
def _loaded(chosen: _Chosen) -> tuple[tuple[str, ...], _gettext.NullTranslations]:
    """Return the catalogs ``chosen`` reads, by name, most wanted first, and their chain.

    Each choice reads its own catalogs, which its chain links, so two never share one.
    """
    wanted = dict.fromkeys(name for tag in chosen.languages for name in lineage(tag))
    found = [
        (name, catalog)
        for name in wanted
        if (catalog := _catalog(name, chosen.directories)) is not None
    ]
    chain: _gettext.NullTranslations = _gettext.NullTranslations()
    for _name, catalog in reversed(found):
        catalog.add_fallback(chain)
        chain = catalog
    return tuple(name for name, _catalog_ in found), chain


def translator() -> _gettext.NullTranslations:
    """Return the chosen languages' catalogs, chained most wanted first.

    Each language falls back through its ``lineage`` (``en_AU``, ``en_001``, ``en``)
    before the next one, and a language with no catalog to the source text, never to an
    error.
    """
    return _loaded(_chosen)[1]


SOURCE_LANGUAGE = "en"
"""The language text is written in: US English (ADR-0020 §2)."""


def text_language() -> str:
    """Return the language text is shown in: the first chosen one with a catalog.

    It's the source language when no chosen language has a catalog.
    """
    found = _loaded(_chosen)[0]
    return found[0] if found else SOURCE_LANGUAGE


_CLDR_PARENTS = {
    "en_001": (
        "150 AG AI AU BB BM BS BW BZ CC CK CM CX CY DG DM ER FJ FK FM GB GD GG GH GI GM GS GY "
        "HK ID IE IL IM IN IO JE JM KE KI KN KY LC LR LS MG MO MS MT MU MV MW MY NA NF NG NR "
        "NU NZ PG PK PN PW RW SB SC SD SG SH SL SS SX SZ TC TK TO TT TV TZ UG VC VG VU WS ZA "
        "ZM ZW"
    ),
    "en_150": "AT BE CH CZ DE DK ES FI FR HU IT NL NO PL PT RO SE SI SK",
}
"""English's parent locales, by region, from Unicode CLDR 47 (``supplementalData.xml``,
``parentLocales``): these regions' English inherits from en_001, and Europe's en_150 from
en_001 in turn. The rest, the US among them, inherit from en, the source language."""
_PARENTS = {
    f"en_{region}": parent
    for parent, regions in _CLDR_PARENTS.items()
    for region in regions.split()
} | {"en_CA": "en_001"}
"""Each locale's parent. en_CA is ours: CLDR keeps it under en, but Canada writes "metre" and
"colour" (ADR-0020 §2)."""


def lineage(language: str) -> tuple[str, ...]:
    """Return the catalogs ``language`` reads, nearest first, e.g. en_AT, en_150, en_001, en.

    A locale falls back to its parents, then to its base language. The British catalog is
    en_001's, so the English locales outside the US read it (ADR-0020 §2). A locale with
    a script, such as zh_Hant_TW, falls back to its language in that script, zh_Hant, but
    not to its language alone, which is written in another: CLDR's zh_Hant and sr_Latn
    inherit from root, the source.
    """
    name = posix_language(language)
    parts = name.split("_")
    if len(parts) > 1 and len(parts[1]) == 4:  # a script that isn't the language's usual one
        return tuple(dict.fromkeys([name, "_".join(parts[:2])]))
    chain = [name]
    while chain[-1] in _PARENTS:
        chain.append(_PARENTS[chain[-1]])
    base = chain[0].split("_", 1)[0]
    return tuple(chain if base in chain else [*chain, base])


def shipped_languages(folder: Traversable | Path | None = None) -> tuple[str, ...]:
    """Return the languages with a compiled catalog shipped in ``folder``, sorted.

    Args:
        folder: The catalogs' folder; the package's own when ``None``. A packaged build
            reports these, so a build that left them out fails its smoke test (ADR-0009).
    """
    folder = resources.files(LOCALE_PACKAGE) / LOCALE_FOLDER if folder is None else folder
    if not folder.is_dir():
        return ()
    return tuple(
        sorted(
            entry.name
            for entry in folder.iterdir()
            if (entry / "LC_MESSAGES" / f"{DOMAIN}.mo").is_file()
        )
    )


def _catalog(
    language: str, directories: Sequence[Traversable | Path]
) -> _gettext.GNUTranslations | None:
    """Return ``language``'s catalog, from a given folder or the shipped ones, if any."""
    shipped = resources.files(LOCALE_PACKAGE) / LOCALE_FOLDER
    for folder in (*directories, shipped):
        path = folder / language / "LC_MESSAGES" / f"{DOMAIN}.mo"
        if path.is_file():
            with path.open("rb") as stream:
                return _gettext.GNUTranslations(stream)
    return None


def _(message: str) -> str:
    """Return ``message`` in the chosen language.

    The empty string stays empty: gettext would return the catalog's header for it.
    """
    return translator().gettext(message) if message else message


def pgettext(context: str, message: str) -> str:
    """Return ``message`` in the chosen language, in ``context``, such as ``"unit"``."""
    return translator().pgettext(context, message) if message else message


def ngettext(singular: str, plural: str, count: int) -> str:
    """Return the form of ``singular`` or ``plural`` for a whole ``count``.

    gettext's plural rules take whole counts only, and Python warns on a float; a number
    shown with decimals chooses its form by ``plural_category`` instead (ADR-0020 §5).

    Raises:
        UsageError: ``count`` isn't an ``int``.
    """
    return translator().ngettext(singular, plural, _whole(count))


def npgettext(context: str, singular: str, plural: str, count: int) -> str:
    """Return the form for a whole ``count``, in ``context`` (``ngettext``)."""
    return translator().npgettext(context, singular, plural, _whole(count))


def _whole(count: int) -> int:
    if not isinstance(count, int) or isinstance(count, bool):
        raise UsageError(f"A plural form needs a whole count, not {count!r} (ADR-0020 §5)")
    return count


_TAG_PART = re.compile(r"[A-Za-z0-9]+")
_SCRIPTS = {
    "az": "Latn", "bal": "Arab", "bm": "Latn", "bs": "Latn", "en": "Latn", "ff": "Latn",
    "ha": "Latn", "hi": "Deva", "hnj": "Hmnp", "iu": "Cans", "kaa": "Cyrl", "kk": "Cyrl",
    "kok": "Deva", "ks": "Arab", "kxv": "Latn", "mn": "Cyrl", "mni": "Beng", "ms": "Latn",
    "pa": "Guru", "rhg": "Rohg", "sat": "Olck", "sd": "Arab", "shi": "Tfng", "sr": "Cyrl",
    "su": "Latn", "uz": "Latn", "vai": "Vaii", "yue": "Hant", "zh": "Hans",
}  # fmt: skip
"""The languages CLDR has locales for in more than one script, each with its usual one,
from Unicode CLDR's likely subtags (``likelySubtags.xml``); a test checks them against the
CLDR data Babel ships. A script is kept only where it isn't the usual one."""
_MODIFIERS = {"latin": "Latn", "cyrillic": "Cyrl"}
"""The POSIX locale modifiers that name a script, as in ``sr_RS@latin``."""
_NO_LANGUAGE = frozenset({"c", "posix"})
"""POSIX's names for no locale at all: text stays in the source language."""


def posix_language(tag: str) -> str:
    """Return a language tag as gettext names catalogs: ``en-Latn-GB`` gives ``en_GB``.

    The language is lower case and the region upper case. A script is kept only where it
    isn't the language's usual one, so ``zh-Hant-TW`` gives ``zh_Hant_TW`` and ``sr@latin``
    gives ``sr_Latn``, while ``zh-Hans-CN`` gives ``zh_CN``. ``C``, ``POSIX`` and a
    private-use tag, such as ``x-pseudo``, give ``""``: no language, so the source.
    """
    head, _at, modifier = tag.partition("@")
    parts = _TAG_PART.findall(head.split(".", 1)[0])
    if not parts or parts[0].lower() in _NO_LANGUAGE or len(parts[0]) == 1:
        return ""  # a single letter is private use, "x-", or grandfathered, "i-"
    language, rest = parts[0].lower(), parts[1:]
    script = next((p.title() for p in rest if len(p) == 4 and p.isalpha()), "")
    script = script or _MODIFIERS.get(modifier.lower(), "")
    if script == _SCRIPTS.get(language, script):
        script = ""  # the usual one, or a language written in one script
    region = next((p.upper() for p in rest if len(p) == 2 or p.isdigit()), "")
    return "_".join(part for part in (language, script, region) if part)


def plural_category(shown: str, language: str = "") -> str:
    """Return the CLDR plural category of a number as shown, such as ``"one"``.

    The category comes from the number's text, not its value: English says "1 inch" but
    "1.0000 inches", since CLDR's English rule makes "one" only a whole 1 with no
    visible decimals (i = 1 and v = 0). A language without a rule of its own here takes
    English's, the source language's.

    Args:
        shown: The number as shown, e.g. ``"1"``, ``"-1"``, ``"0.3119"`` or ``"0,3119"``.
        language: A language tag; the language text is shown in (``text_language``) when
            empty.
    """
    return _rule(language or text_language()).category(*_digits(shown))


def npgettext_shown(context: str, singular: str, plural: str, shown: str) -> str:
    """Return the form of ``singular`` or ``plural``, in ``context``, for a number as shown.

    The form follows the number's plural category in the language the text is shown in
    (ADR-0020 §5): "1" takes "inch", and "1.0000" and "0.5" take "inches". gettext picks a
    catalog's form by a whole count, so the category is passed as a count in it.
    """
    rule = _rule(text_language())
    count = rule.samples[rule.category(*_digits(shown))]
    return translator().npgettext(context, singular, plural, count)


_NUMBER = re.compile(r"[+\-−]?(\d*)(?:[.,](\d*))?")
"""A shown number's sign, integer part, and decimals; U+2212 is the minus sign."""


def _digits(shown: str) -> tuple[int, int]:
    """Return a shown number's integer part, i, and how many decimals it shows, v.

    Either "." or "," is its decimal mark: a shown number has no digit grouping
    (ADR-0020 §4).
    """
    match = _NUMBER.match(shown.strip())
    whole, fraction = (match.group(1), match.group(2)) if match else ("", None)
    return int(whole or "0"), len(fraction or "")


def _english(i: int, v: int) -> str:
    """CLDR's English cardinal rule: "one" for i = 1 and v = 0, "other" otherwise."""
    return "one" if i == 1 and v == 0 else "other"


@dataclass(frozen=True)
class _PluralRule:
    """A language's CLDR cardinal rule, and a whole count in each of its categories."""

    category: Callable[[int, int], str]
    """The rule, as (i, v) -> category: i is the integer part, and v the number of
    visible fraction digits."""
    samples: Mapping[str, int]
    """A whole count the language's catalogs put in each category, so a category can
    choose a catalog's form: gettext chooses forms by count."""


_PLURAL_RULES = {"en": _PluralRule(_english, {"one": 1, "other": 2})}
"""Each shipped language's rule, by language."""


def _rule(language: str) -> _PluralRule:
    """Return ``language``'s plural rule, or English's when it has none of its own."""
    return _PLURAL_RULES.get(posix_language(language).split("_", 1)[0], _PLURAL_RULES["en"])
