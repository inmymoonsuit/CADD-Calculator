"""The en_XA pseudo-locale, for tests only and never shipped (ADR-0020 §6).

It's made from the template, so every marked string has a translation that looks foreign
but stays readable: its letters accented (from Latin-1 and Latin Extended-A only), about
40% longer, and wrapped in ``⟦…⟧``. Text shown plain was never marked; text only partly
bracketed was translated too early, or pieced together from fragments. Placeholders,
numbers, unit symbols after a number, the product name, markup, and ``&`` mnemonics are
left as they are, so the text still works.
"""

from __future__ import annotations

import math
import re
from functools import cache
from pathlib import Path

from babel.messages.catalog import Catalog
from babel.messages.mofile import write_mo
from babel.messages.pofile import read_po

from caddcalc.core.units import registry
from caddcalc.gui.branding import PRODUCT_NAME

LANGUAGE = "en_XA"
TEMPLATE = Path(__file__).parents[1] / "src" / "caddcalc" / "locale" / "caddcalc.pot"
OPEN, CLOSE = "⟦", "⟧"
PADDING = 0.4
"""How much longer each string gets: translations run 30–40% longer than English."""

_ACCENTED = str.maketrans(
    "acdeghijklnorstuwyzACDEGHIJKLNORSTUWYZ",
    "åçðéĝĥîĵķļñöŕšţüŵýžÅÇÐÉĜĤÎĴĶĻÑÖŔŠŢÛŴÝŽ",
)
"""Each letter with an accented form in Latin-1 or Latin Extended-A; b, f, m, p, q, v and x
have none there, so they stay."""
_FILLER = "lorem ipsum dolor sit amet consectetur adipiscing elit sed do eiusmod tempor "


@cache
def _protected() -> re.Pattern[str]:
    """What a pseudo-translation never changes, longest alternatives first."""
    symbols = sorted(
        {re.escape(key) for unit in registry().units for key in unit.keys if key.isalpha()},
        key=len,
        reverse=True,
    )
    return re.compile(
        "|".join(
            (
                r"\{\{|\}\}|\{[^{}]*\}",  # placeholders, and escaped braces
                r"<[^<>]*>",  # markup
                r"&(?:#\d+|#x[0-9A-Fa-f]+|[A-Za-z][A-Za-z0-9]*);",  # character references
                r"&&|&\S",  # a literal &, or a mnemonic and its letter
                re.escape(PRODUCT_NAME),
                # a number, or a word with a digit such as 6061-T6, and a unit symbol after it
                rf"[A-Za-z]*\d[\w.,/-]*(?:\s?(?:{'|'.join(symbols)})(?![A-Za-z]))?",
            )
        )
    )


def pseudo(text: str) -> str:
    """Return ``text`` in en_XA: accented, about 40% longer, and wrapped in ``⟦…⟧``."""
    parts: list[str] = []
    end = 0
    for match in _protected().finditer(text):
        parts += [text[end : match.start()].translate(_ACCENTED), match.group()]
        end = match.end()
    parts.append(text[end:].translate(_ACCENTED))
    filler = (_FILLER * (1 + len(text) // len(_FILLER)))[: math.ceil(len(text) * PADDING)]
    padding = filler.strip().translate(_ACCENTED)
    return f"{OPEN}{''.join(parts)}{' ' + padding if padding else ''}{CLOSE}"


def catalog(template: Path = TEMPLATE) -> Catalog:
    """Return en_XA's catalog: every message in ``template``, every plural form filled."""
    with template.open("rb") as stream:
        source = read_po(stream)
    # Babel has no en_XA; English's plural rule is the one wanted.
    made = Catalog(locale="en", domain="caddcalc")
    for message in source:
        if not message.id:
            continue
        if isinstance(message.id, tuple | list):
            forms = [pseudo(message.id[min(n, 1)]) for n in range(made.num_plurals)]
            made.add(tuple(message.id), tuple(forms), context=message.context)
        else:
            made.add(message.id, pseudo(message.id), context=message.context)
    return made


def write(folder: Path, template: Path = TEMPLATE) -> Path:
    """Compile en_XA's catalog under ``folder``, for ``i18n.use(..., directories=[folder])``.

    Returns:
        ``folder``.
    """
    path = folder / LANGUAGE / "LC_MESSAGES" / "caddcalc.mo"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as stream:
        write_mo(stream, catalog(template))
    return folder
