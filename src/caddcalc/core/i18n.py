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
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from functools import cache
from importlib import resources
from importlib.resources.abc import Traversable
from pathlib import Path

from caddcalc.core.errors import UsageError

DOMAIN = "caddcalc"
"""The gettext domain: every catalog is ``<language>/LC_MESSAGES/caddcalc.mo``."""
LOCALE_PACKAGE = "caddcalc"
LOCALE_FOLDER = "locale"
"""Where the shipped catalogs are, inside the ``caddcalc`` package."""


@dataclass
class _Chosen:
    """What ``use()`` chose: the languages, and any catalog folders searched first."""

    languages: tuple[str, ...] = ()
    directories: tuple[Traversable | Path, ...] = ()


_chosen = _Chosen()


def N_(message: str) -> str:  # noqa: N802 (gettext's name for a deferred marker)
    """Mark ``message`` for translation where it's declared, and return it unchanged.

    It's translated later, where it's shown, with ``_()``.
    """
    return message


def use(languages: Iterable[str], *, directories: Sequence[Traversable | Path] = ()) -> None:
    """Choose the languages text is shown in, most wanted first; ``()`` is the source.

    Args:
        languages: Language tags such as ``"en_GB"`` or ``"en-GB"``.
        directories: Catalog folders searched before the shipped ones, for tests and the
            pseudo-locale.
    """
    _chosen.languages = tuple(dict.fromkeys(posix_language(tag) for tag in languages))
    _chosen.directories = tuple(directories)
    clear()


def languages() -> tuple[str, ...]:
    """Return the languages chosen, most wanted first; empty for the source language."""
    return _chosen.languages


def clear() -> None:
    """Forget the loaded catalogs, so the next lookup reads them again; for tests."""
    translator.cache_clear()


@cache
def translator() -> _gettext.NullTranslations:
    """Return the chosen languages' catalogs, chained most wanted first.

    Each language falls back to its base language (``en_GB`` to ``en``) before the next
    one, and a language with no catalog to the source text, never to an error.
    """
    chain: _gettext.NullTranslations = _gettext.NullTranslations()
    wanted = dict.fromkeys(name for tag in _chosen.languages for name in _with_base(tag))
    found = [catalog for name in wanted if (catalog := _catalog(name)) is not None]
    for catalog in reversed(found):
        catalog.add_fallback(chain)
        chain = catalog
    return chain


def _with_base(language: str) -> list[str]:
    """Return ``language`` and its base: ``en_GB`` and ``en``."""
    base = language.split("_", 1)[0]
    return [language] if base == language else [language, base]


def _catalog(language: str) -> _gettext.GNUTranslations | None:
    """Return ``language``'s catalog, from a given folder or the shipped ones, if any."""
    shipped = resources.files(LOCALE_PACKAGE) / LOCALE_FOLDER
    for folder in (*_chosen.directories, shipped):
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


def posix_language(tag: str) -> str:
    """Return a language tag as gettext names catalogs: ``en-Latn-GB`` gives ``en_GB``.

    The language is lower case and the region upper case. A script, such as Latn, is
    dropped: the catalogs are by language and region.
    """
    parts = _TAG_PART.findall(tag.split(".", 1)[0].split("@", 1)[0])
    if not parts:
        return ""
    language, rest = parts[0].lower(), parts[1:]
    region = next((p.upper() for p in rest if len(p) == 2 or p.isdigit()), "")
    return f"{language}_{region}" if region else language


def plural_category(shown: str, language: str = "") -> str:
    """Return the CLDR plural category of a number as shown, such as ``"one"``.

    The category comes from the number's text, not its value: English says "1 inch" but
    "1.0000 inches", since CLDR's English rule makes "one" only a whole 1 with no
    visible decimals (i = 1 and v = 0). A language without a rule of its own here takes
    English's, the source language's.

    Args:
        shown: The number as shown, e.g. ``"1"``, ``"-1"`` or ``"0.3119"``.
        language: A language tag; the chosen language when empty.
    """
    tag = posix_language(language) if language else next(iter(_chosen.languages), "")
    rule = _PLURAL_RULES.get(tag.split("_", 1)[0], _english)
    whole, _point, fraction = shown.strip().lstrip("+-").partition(".")
    return rule(int(whole or "0"), len(fraction))


def _english(i: int, v: int) -> str:
    """CLDR's English cardinal rule: "one" for i = 1 and v = 0, "other" otherwise."""
    return "one" if i == 1 and v == 0 else "other"


_PLURAL_RULES = {"en": _english}
"""Each shipped language's CLDR cardinal rule, by language, as (i, v) -> category: i is
the integer digits, and v the number of visible fraction digits."""
