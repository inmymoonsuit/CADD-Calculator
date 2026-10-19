"""The en_XA pseudo-locale's own rules (ADR-0020 §6): what it changes, and what it never does."""

from __future__ import annotations

import re
from pathlib import Path
from string import Formatter

import pytest
from babel.messages.catalog import Catalog
from babel.messages.pofile import write_po

from tests import pseudo_locale
from tests.catalogs import tooling
from tests.pseudo_locale import CLOSE, OPEN, pseudo


def _letters(text: str) -> str:
    return re.sub(r"[^\w]|\d|_", "", text)


def _fields(text: str) -> list[str]:
    return [name for _t, name, _s, _c in Formatter().parse(text) if name is not None]


@pytest.mark.parametrize(
    "text",
    [
        "Bend allowance & deduction",
        "About {product}: version, license, and terms",
        "{value} is below {limit:.4f}",
        "Close (Esc)",
    ],
)
def test_letters_are_accented_from_latin_1_and_extended_a_only(text: str) -> None:
    shown = pseudo(text)
    assert shown.startswith(OPEN) and shown.endswith(CLOSE)
    inner = shown[1:-1]
    assert all(ord(c) < 0x80 or 0xC0 <= ord(c) <= 0x17F for c in inner), inner
    assert any(ord(c) >= 0xC0 for c in inner), "accented"
    assert OPEN not in inner and CLOSE not in inner


def test_each_string_grows_by_about_40_percent() -> None:
    text = "Flat-pattern length of one segment, dimensioned to the outside"
    grown = len(pseudo(text)) - 2  # without the brackets
    assert 1.35 <= grown / len(text) <= 1.5


@pytest.mark.parametrize(
    ("text", "kept"),
    [
        ("{value} is below {limit:.4f}", ["{value}", "{limit:.4f}"]),
        ("for sheet over 0.051 to 0.090 in", ["0.051", "0.090 in"]),
        ("Aluminum 6061-T6, 2 mm thick", ["6061-T6", "2 mm"]),
        ("Welcome to CADD Calculator", ["CADD Calculator"]),
        ("&File and && more", ["&F", "&&"]),
        ("<b>Method</b>: see &amp; read", ["<b>", "</b>", "&amp;"]),
        ("Load %(name)s now, %s of %d", ["%(name)s", "%s", "%d"]),  # printf placeholders too
    ],
)
def test_what_makes_text_work_is_never_touched(text: str, kept: list[str]) -> None:
    """Placeholders, numbers, unit symbols, the product name, mnemonics, and markup."""
    shown = pseudo(text)
    for token in kept:
        assert token in shown, (token, shown)
    assert _fields(shown) == _fields(text), "the same fields, in order"


def test_a_word_that_is_only_a_unit_symbol_away_from_a_number_is_still_a_word() -> None:
    """After a number, "in" is the inch; in a sentence, it is a word."""
    shown = pseudo("2 in thick, cut in half")
    assert "2 in" in shown and "çüţ îñ" in shown


def test_every_message_and_every_plural_form_is_filled(tmp_path: Path) -> None:
    template = Catalog(domain="caddcalc")
    template.add("Sheet Metal")
    template.add("Copy", context="button")
    template.add(("{count} field", "{count} fields"))
    path = tmp_path / "caddcalc.pot"
    with path.open("wb") as stream:
        write_po(stream, template)
    made = pseudo_locale.catalog(path)
    assert made.get("Copy", context="button").string == pseudo("Copy")
    forms = made.get(("{count} field", "{count} fields")).string
    assert len(forms) == made.num_plurals == 2
    assert forms == (pseudo("{count} field"), pseudo("{count} fields"))


def test_the_shipped_template_makes_a_catalog_that_keeps_every_placeholder() -> None:
    tools = tooling()
    made = pseudo_locale.catalog()
    template = tools.read(pseudo_locale.TEMPLATE)
    assert tools.keys(made) == tools.keys(template), "every marked string"
    assert tools.placeholder_mismatches(made) == []
    forms = [
        f for m in made if m.id for f in (m.string if isinstance(m.string, tuple) else [m.string])
    ]
    assert all(_letters(f) for f in forms), "nothing left empty, in any plural form"
    assert any(isinstance(m.id, tuple) for m in made), "the units' names have plural forms"
