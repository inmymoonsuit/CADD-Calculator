"""The units registry reads and shows every value as the old units module did (ADR-0019 §7).

``tests/units_as_it_was.py`` keeps the old module and display rules. Each test here runs
a corpus through both and wants the same answer: the same value and unit, or the same
error, word for word. The one allowed difference is psi's factor, now its exact
definition rounded once, one unit in the last place from before.
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
OLD_DIMENSIONS = {d: old.Dimension(d.value) for d in Dimension}


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
    for unit, number, space, dimension in product(UNITS, NUMBERS, ("", " ", "  "), Dimension):
        for key in unit.keys:
            for name in {key, key.upper(), key.title()}:
                yield f"{number}{space}{name}", dimension, None
    for number, dimension, unit in product(NUMBERS, Dimension, (None, *(u.symbol for u in UNITS))):
        yield number, dimension, unit
        yield f"  {number}  ", dimension, unit
    for text, dimension in product(INVALID, Dimension):
        yield text, dimension, None
    for calc in default_registry(load_plugins=False):
        for param in calc.params:
            if param.default is not None:
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


def test_every_text_reads_as_it_always_has() -> None:
    differ = []
    count = 0
    for text, dimension, default in _corpus():
        count += 1
        new = _reads(parse_quantity_detailed, text, dimension, default)
        was = _reads(old.parse_quantity_detailed, text, OLD_DIMENSIONS[dimension], default)
        if not _same(new, was):
            differ.append((text, dimension.value, default, new, was))
    assert count > 10_000, count
    assert differ == [], differ[:10]


def test_every_name_finds_the_unit_it_always_has() -> None:
    for unit in UNITS:
        for key in (*unit.keys, unit.symbol, f" {unit.symbol} "):
            new, was = get_unit(key), old.get_unit(key)
            assert (new.symbol, new.name, new.dimension.value) == (
                was.symbol,
                was.name,
                was.dimension.value,
            )
            assert (new.aliases, new.spoken_plural) == (was.aliases, was.spoken_plural)
    with pytest.raises(CaddCalcError, match="Unknown unit 'furlong'"):
        get_unit("furlong")


def test_every_factor_is_as_it_was_but_psis_one_unit_in_the_last_place() -> None:
    changed = {}
    for new, was in zip(UNITS, old.UNITS, strict=True):
        assert new.symbol == was.symbol
        if new.factor != was.factor:
            changed[new.symbol] = (new.factor - was.factor) / math.ulp(was.factor)
    assert changed == {"psi": 1.0}, "recorded in ADR-0019's amendment and the CHANGELOG"


def test_dimensions_and_base_units_are_as_they_were() -> None:
    assert {d.value: u for d, u in BASE_UNITS.items()} == {
        d.value: u for d, u in old.BASE_UNITS.items()
    }
    assert base_unit_names() == old.base_unit_names()
    for dimension in Dimension:
        assert dimension.with_article == OLD_DIMENSIONS[dimension].with_article
        assert [u.symbol for u in units_for(dimension)] == [
            u.symbol for u in old.units_for(OLD_DIMENSIONS[dimension])
        ]


LENGTH_CHOICES = tuple(k for u in UNITS if u.dimension is Dimension.LENGTH for k in u.keys)


@pytest.mark.parametrize("length", LENGTH_CHOICES)
def test_every_dimension_shows_as_it_did_for_every_length_choice(length: str) -> None:
    for dimension, fraction in product(Dimension, (None, 64)):
        prefs = formatting.DisplayPrefs(length_unit=length, fraction_denominator=fraction)
        was = OLD_DIMENSIONS[dimension]
        assert formatting.display_unit(dimension, prefs).symbol == (
            old.display_unit(was, length).symbol
        )
        assert formatting.unit_suffix(dimension, prefs) == old.suffix(old.shown_symbol(was, length))
        parts = formatting.value_parts(7.9375, dimension, prefs)
        assert parts.unit == old.shown_symbol(was, length)
        shows = fraction is not None and old.shows_fraction(was, length)
        assert (parts.fraction is not None) == shows, (dimension, length, fraction)
        decimals = {"angle": 2, "stress": 1}.get(dimension.value, 4)
        assert prefs.decimals_for(dimension) == decimals
