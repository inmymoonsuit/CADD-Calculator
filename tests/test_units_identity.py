"""The units registry reads and shows every value as the old units module did (ADR-0019 §7).

``tests/units_as_it_was.py`` keeps the old module and display rules. Each test here runs
a corpus through both and wants the same answer: the same value and unit, or the same
error, word for word. The one allowed difference is psi's factor, now its exact
definition rounded once, one unit in the last place from before.

Dimensions and units added since (the area and its squares, ADR-0018 §3, and the minute
and second of arc) are new, so the corpus is the old dimensions and units. A text the
old module refused may now name a new unit, as ``3 sq in`` and ``30′`` in an angle do,
or be a compound form, as ``1'4"`` is; each is held to its new reading instead.
"""

from __future__ import annotations

import math
from collections.abc import Iterator
from itertools import product
from typing import Any

import pytest

import tests.units_as_it_was as old
from caddcalc.calculators import REFERENCE_TABLES, default_registry
from caddcalc.calculators.sheet_metal.materials import MATERIAL_TABLE, load_materials
from caddcalc.core import formatting
from caddcalc.core.errors import CaddCalcError
from caddcalc.core.units import (
    BASE_UNITS,
    UNITS,
    Dimension,
    TypedValue,
    base_unit_names,
    get_unit,
    parse_quantity_detailed,
    units_for,
)

NUMBERS = ("3", "0.1046", "1/8", "1-1/2", "1 1/2", "-2", "+2.5", "1e3", ".5", "0", "12")
"""Number forms the parser has always read."""
INVALID = (
    "",
    "  ",
    "abc",
    "3 xyz",
    "3 x%",
    "3mmm",
    "in",
    "mm",
    "3 in.",
    "3 m2",
    "1'4\"",
    "3 sq in",
    "1/0",
    "inf",
    "nan",
    "3 ñ",
    "--3",
    "3 mm mm",
    "°",
    "3 e",
    "1e",
    "3 m m",
    "abc xyz",
    "1-1/2-",
    "3,5 mm",
)
"""Text the parser has always refused, each with its own message."""
NEW_DIMENSIONS = {Dimension.AREA, Dimension.COUNT}
"""The dimensions added since: the area (ADR-0018 §3) and the count (KI-025)."""
OLD_DIMENSIONS = {d: old.Dimension(d.value) for d in Dimension if d not in NEW_DIMENSIONS}
"""The dimensions the old module had, by the new ones."""
OLD_UNITS = tuple(
    u
    for u in UNITS
    if u.dimension not in NEW_DIMENSIONS and u.symbol in {was.symbol for was in old.UNITS}
)
"""The units the old module had: every unit but the squares, the minute and second, and
the count."""
ARC_MARKS = {"'": "arcmin", "′": "arcmin", '"': "arcsec", "″": "arcsec"}
"""The foot's and inch's marks, which in an angle are the minute's and second's (SP 811
Table 6): an angle the old module refused as a length reads in them now."""
COMPOUND_TEXTS = {
    ("1'4\"", Dimension.LENGTH): 16 * 25.4,
    ("1'4\"", Dimension.ANGLE): 1 / 60 + 4 / 3600,
}
"""Texts the old module refused that are compound forms now: 1 foot 4 inches, and in an
angle 1 minute 4 seconds (ADR-0019 U3)."""
AREA_TEXTS = {"3 m2": "m²", "3 sq in": "in²"}
"""Texts the old module refused that name a square now: each reads as that area, and in
any other dimension is refused for measuring an area."""
NEW_SPELLINGS = {"millimetre": "mm", "centimetre": "cm", "metre": "m", "per cent": "%"}
"""Spellings units gained after the registry (ADR-0019 U5: every spelling reads in every
locale). The old module didn't know them, so they're held to their units instead."""


def _reads(parse: Any, text: str, dimension: Any, default: str | None) -> tuple[Any, ...]:
    """What a parser makes of ``text``.

    That's its value, unit, and whether it was named, or its error's type and message.
    """
    try:
        got = parse(text, dimension, default)
    except CaddCalcError as exc:
        return (type(exc).__name__, str(exc))
    return (got.value, got.unit.symbol, got.explicit_unit)


def _corpus() -> Iterator[tuple[str, Dimension, str | None]]:
    """Every text the identity test reads.

    That's every built-in name in every case and spacing, the invalid texts, every
    default, and every value a shipped table states.
    """
    for unit, number, space, dimension in product(
        OLD_UNITS, NUMBERS, ("", " ", "  "), OLD_DIMENSIONS
    ):
        for key in (k for k in unit.keys if k not in NEW_SPELLINGS):
            for name in {key, key.upper(), key.title()}:
                yield f"{number}{space}{name}", dimension, None
    defaults = (None, *(u.symbol for u in OLD_UNITS))
    for number, dimension, unit in product(NUMBERS, OLD_DIMENSIONS, defaults):
        yield number, dimension, unit
        yield f"  {number}  ", dimension, unit
    for text, dimension in product(INVALID, OLD_DIMENSIONS):
        yield text, dimension, None
    for calc in default_registry(load_plugins=False):
        for param in calc.params:
            if param.default is not None and param.dimension in OLD_DIMENSIONS:
                yield param.default, param.dimension, None
    for spec in REFERENCE_TABLES:
        for value in spec.values(spec.load()):
            if value.stated is not None:
                yield from _typed(value.stated)
    materials = load_materials(MATERIAL_TABLE.load())
    for radius in materials.radii:
        for band in radius.values:
            if isinstance(band.value, TypedValue):
                yield from _typed(band.value)
    for start in materials.k_starts:
        yield from _typed(start.value)
    for strength in materials.strengths:
        for typed in (*strength.ultimate, *strength.tensile_yield):
            yield from _typed(typed)


def _typed(value: TypedValue) -> Iterator[tuple[str, Dimension, str | None]]:
    yield value.text, value.dimension, value.unit.symbol
    yield value.text, value.dimension, None


def _same(new: tuple[Any, ...], was: tuple[Any, ...]) -> bool:
    """Whether two readings agree, allowing psi's one unit in the last place."""
    if len(new) == 3 and len(was) == 3 and new[1:] == was[1:] and new[1] == "psi":
        return abs(new[0] - was[0]) <= math.ulp(was[0])
    return new == was


def _reads_arc(text: str, dimension: Dimension, new: tuple[Any, ...], was: tuple[Any, ...]) -> bool:
    """Whether ``text`` is an angle in minutes or seconds the old module refused as a length.

    If it is, it must read as that many minutes or seconds now.
    """
    mark = text.rstrip()[-1:]
    if dimension is not Dimension.ANGLE or mark not in ARC_MARKS:
        return False
    if was != ("InputError", f"{text!r} is a length, but an angle is expected"):
        return False
    length, unit, _named = old.parse_quantity_detailed(text, old.Dimension.LENGTH, None)
    arc = get_unit(ARC_MARKS[mark])
    assert new == (pytest.approx(length / unit.factor * arc.factor), arc.symbol, True), text
    return True


def test_every_text_reads_as_it_always_has() -> None:
    differ = []
    count = 0
    for text, dimension, default in _corpus():
        count += 1
        new = _reads(parse_quantity_detailed, text, dimension, default)
        was = _reads(old.parse_quantity_detailed, text, OLD_DIMENSIONS[dimension], default)
        if "," in text:  # still refused, now saying why (ADR-0020 §4)
            assert new[0] == was[0] == "InputError" and "has a comma" in new[1], (new, was)
            continue
        if (text, dimension) in COMPOUND_TEXTS:
            assert was[0] == "InputError" and new[2] is True, (new, was)
            assert new[0] == pytest.approx(COMPOUND_TEXTS[text, dimension]), (text, new)
            continue
        if _reads_arc(text, dimension, new, was):
            continue
        if text in AREA_TEXTS:  # refused still, now because it names an area
            assert was[0] == "InputError" and new == (
                "InputError",
                f"{text!r} is an area, but {dimension.with_article} is expected",
            ), (new, was)
            continue
        if not _same(new, was):
            differ.append((text, dimension.value, default, new, was))
    assert count > 10_000, count
    assert differ == [], differ[:10]


@pytest.mark.parametrize(("text", "symbol"), AREA_TEXTS.items())
def test_a_text_that_names_a_square_now_reads_as_that_area(text: str, symbol: str) -> None:
    got = parse_quantity_detailed(text, Dimension.AREA, None)
    assert (got.unit.symbol, got.explicit_unit) == (symbol, True)
    assert got.value == pytest.approx(3 * get_unit(symbol).factor)


def test_every_name_finds_the_unit_it_always_has() -> None:
    """Names are now US English, the source language, each one an old alias (ADR-0020 §2)."""
    for unit in OLD_UNITS:
        for key in (*(k for k in unit.keys if k not in NEW_SPELLINGS), unit.symbol):
            new, was = get_unit(key, unit.dimension), old.get_unit(key)
            assert (new.symbol, new.dimension.value) == (was.symbol, was.dimension.value)
            assert new.name in (was.name, *was.aliases), new.name
            assert new.spoken_plural in (was.spoken_plural, *was.aliases), new.spoken_plural
            assert set(new.aliases) - set(was.aliases) <= set(NEW_SPELLINGS), new.aliases
            assert set(was.aliases) <= set(new.aliases), "every old spelling still reads"
    with pytest.raises(CaddCalcError, match="Unknown unit 'furlong'"):
        get_unit("furlong")


@pytest.mark.parametrize(("spelling", "symbol"), NEW_SPELLINGS.items())
def test_the_new_spellings_read_as_their_units(spelling: str, symbol: str) -> None:
    """British "millimetre" and "per cent" were unknown before; now they're their units."""
    with pytest.raises(CaddCalcError):  # an unknown unit, or "'3 per' is not a number"
        old.parse_quantity_detailed(f"3 {spelling}", old.Dimension.LENGTH, None)
    unit = get_unit(symbol)
    for name, space in product({spelling, spelling.upper(), spelling.title()}, ("", " ")):
        got = parse_quantity_detailed(f"3{space}{name}", unit.dimension, None)
        assert (got.unit.symbol, got.explicit_unit) == (symbol, True), name
        assert got.value == pytest.approx(3 * unit.factor)


def test_every_factor_is_as_it_was_but_psis_one_unit_in_the_last_place() -> None:
    changed = {}
    for new, was in zip(OLD_UNITS, old.UNITS, strict=True):
        assert new.symbol == was.symbol
        if new.factor != was.factor:
            changed[new.symbol] = (new.factor - was.factor) / math.ulp(was.factor)
    assert changed == {"psi": 1.0}, "recorded in ADR-0019's amendment and the CHANGELOG"


def test_dimensions_and_base_units_are_as_they_were() -> None:
    """The old dimensions keep their order, base units, and articles; the new ones follow."""
    assert {d.value: u for d, u in BASE_UNITS.items() if d in OLD_DIMENSIONS} == {
        d.value: u for d, u in old.BASE_UNITS.items()
    }
    assert list(Dimension)[: len(OLD_DIMENSIONS)] == list(OLD_DIMENSIONS)
    assert base_unit_names() == f"{old.base_unit_names()}, mm², count"
    for dimension in OLD_DIMENSIONS:
        assert dimension.with_article == OLD_DIMENSIONS[dimension].with_article
        was = [u.symbol for u in old.units_for(OLD_DIMENSIONS[dimension])]
        now = [u.symbol for u in units_for(dimension)]
        assert now[: len(was)] == was, "the old units first, in their order"
        assert set(now[len(was) :]) <= {"arcmin", "arcsec"}, "then only the new ones"


LENGTH_CHOICES = tuple(
    k for u in UNITS if u.dimension is Dimension.LENGTH for k in u.keys if k not in NEW_SPELLINGS
)


@pytest.mark.parametrize("length", LENGTH_CHOICES)
def test_every_dimension_shows_as_it_did_for_every_length_choice(length: str) -> None:
    for dimension in OLD_DIMENSIONS:
        # The preference took any of a length's names; a set is keyed by its symbol.
        units = formatting.ShownUnits.generated(get_unit(length, Dimension.LENGTH).symbol)
        prefs = formatting.DisplayPrefs()
        was = OLD_DIMENSIONS[dimension]
        assert units.unit(dimension).symbol == old.display_unit(was, length).symbol
        suffix = formatting.unit_suffix(units.unit(dimension))
        assert suffix == old.suffix(old.shown_symbol(was, length))
        parts = formatting.value_parts(7.9375, dimension, units, prefs)
        assert parts.unit == old.shown_symbol(was, length)
        decimals = {"angle": 2, "stress": 1}.get(dimension.value, 4)
        assert prefs.decimals_for(dimension) == decimals
