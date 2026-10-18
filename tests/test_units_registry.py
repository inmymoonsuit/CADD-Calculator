"""The units registry: cited, exact declarations, and the guards on registering (ADR-0019)."""

from __future__ import annotations

import math
import subprocess
import sys
from decimal import Decimal, localcontext
from fractions import Fraction
from typing import Any

import pytest

from caddcalc.core.citations import (
    License,
    PublicationKind,
    check_publication,
)
from caddcalc.core.errors import InputError, SpecError, UsageError
from caddcalc.core.units import (
    UNITS,
    Dimension,
    Unit,
    UnitRegistry,
    UnitSystem,
    build_registry,
    builtin,
    clear_registry,
    get_unit,
    parse_quantity_detailed,
    parsing,
    registry,
)

L, A = Dimension.LENGTH, Dimension.ANGLE

PRINTED = frozenset({builtin.FR_1959.id})
"""Public-domain works the units cite with no url, named on purpose: the 1959 Federal
Register notice is cited as printed."""


def test_every_unit_cites_its_definition_and_its_exact_factor() -> None:
    """ADR-0019 §4: a cited source, an exact factor, rounded once."""
    for unit in UNITS:
        assert unit.sources and unit.reference is not None, unit.symbol
        assert unit.sources[0].publication is builtin.SP_811
        assert unit.reference.locator, unit.symbol
        assert isinstance(unit.exact, Fraction | Decimal), unit.symbol
        assert unit.factor == float(unit.exact), "the exact definition, rounded once"
        assert unit.system is not None, unit.symbol
        for source in unit.sources:
            check_publication(source.publication)
            work = source.publication
            assert (work.kind, work.license) == (
                PublicationKind.GOVERNMENT_DOCUMENT,
                License.PUBLIC_DOMAIN,
            )
            assert work.on_allowlist or work.id in PRINTED, work.id
    assert builtin.SP_811.on_allowlist, "nist.gov"
    inch, pound_force = get_unit("in"), get_unit("psi")
    assert builtin.FR_1959 in {s.publication for s in inch.sources}, "the inch's primary source"
    assert builtin.FR_1959 in {s.publication for s in pound_force.sources}, "and the pound's"


def test_derived_factors_equal_their_definitions() -> None:
    by = {u.symbol: u.exact for u in UNITS}
    assert by["ft"] == 12 * by["in"] == Fraction("304.8")
    assert by["in"] == Fraction(9144, 10_000) * 1000 / 36, "the yard is 0.9144 m"
    assert by["psi"] == builtin.POUND_KG * builtin.STANDARD_GRAVITY / builtin.INCH_MM**2
    assert by["ksi"] == 1000 * by["psi"]
    assert (by["mm"], by["cm"], by["m"]) == (1, 10, 1000)
    assert (by["kPa"], by["MPa"], by["GPa"]) == (Fraction(1, 1000), 1, 1000)
    assert by["%"] == Fraction(1, 100)
    radian = by["rad"]
    assert isinstance(radian, Decimal)
    with localcontext() as context:
        context.prec = 40
        assert +(radian * builtin._PI) == 180, "180/π to 50 digits"
    assert float(radian) == 180 / math.pi


def test_symbols_keep_their_case_and_the_degree_alone_is_close_up() -> None:
    """SP 811 §6.1.2 and §7.2: lower case but Pa's P and the M and G prefixes; ° close up."""
    assert {u.symbol for u in UNITS if u.symbol != u.symbol.lower()} == {"MPa", "kPa", "GPa"}
    assert {u.written for u in UNITS if u.close_up} == {"°"}
    assert get_unit("%").close_up is False, "the percent sign is spaced (§7.10.2)"
    assert {u.symbol for u in UNITS if u.fractions} == {"in"}


def _fresh() -> UnitRegistry:
    """A registry of the built-ins, not yet frozen, to register more into."""
    test = UnitRegistry(builtin.DIMENSIONS)
    for unit in UNITS:
        test.register(unit)
    return test


def _yard(**changes: Any) -> Unit:
    """A cited test unit, the yard; ``changes`` break it in one way."""
    fields: dict[str, Any] = {
        "symbol": "yd",
        "name": "yard",
        "dimension": L,
        "factor": 914.4,
        "aliases": ("yard", "yards"),
        "spoken_plural": "yards",
        "exact": Fraction("914.4"),
        "system": UnitSystem.US_CUSTOMARY,
        "sources": get_unit("ft").sources,
    }
    return Unit(**(fields | changes))


def test_a_cited_unit_registers_and_parses_at_once() -> None:
    test = _fresh()
    test.register(_yard(aliases=("yard", "yards", "sq yd")))
    assert test.find("YD").symbol == "yd"
    assert test.ending("3 yards", L) == (test.find("yd"), len("yards"))
    assert test.ending("3 sq yd", L) == (test.find("yd"), len("sq yd")), "a name with a space"


@pytest.mark.parametrize(
    ("changes", "problem"),
    [
        ({"aliases": ("2yd",)}, "can't be told from the number"),
        ({"aliases": ("-yd",)}, "can't be told from the number"),
        ({"aliases": ("/yd",)}, "can't be told from the number"),
        ({"aliases": (".yd",)}, "can't be told from the number"),
        ({"aliases": ("eyd",)}, "can't be told from the number"),
        ({"aliases": ("Eyd",)}, "can't be told from the number"),
        ({"aliases": (" yd",)}, "can't be told from the number"),
        ({"aliases": ("MM",)}, "'MM' is already 'mm', unit 'mm'"),
        ({"aliases": ('"',)}, "is already '\"', unit 'in'"),
        ({"symbol": "in"}, "the symbol 'in' is taken"),
        ({"system": None}, "needs a system"),
        ({"sources": ()}, "needs a citation"),
        ({"exact": None}, "needs an exact definition"),
        ({"factor": 914.4000000001}, "rounded once"),
        ({"spoken_plural": ""}, "needs a name and a plural"),
        ({"close_up": True}, "only °, ′, and ″"),
        ({"written": "yard-ish"}, "read back the symbol"),
    ],
)
def test_registration_refuses_a_unit_that_breaks_a_rule(
    changes: dict[str, Any], problem: str
) -> None:
    with pytest.raises(SpecError, match=problem):
        _fresh().register(_yard(**changes))


def test_case_sensitive_units_may_differ_only_in_case() -> None:
    """A future Mm beside mm: both must declare themselves case-sensitive."""
    test = UnitRegistry(builtin.DIMENSIONS)
    small = _yard(symbol="xy", aliases=(), case_sensitive=True)
    test.register(small)
    test.register(_yard(symbol="XY", aliases=(), case_sensitive=True))
    assert test.find("xy") is small and test.find("XY").symbol == "XY"
    with pytest.raises(InputError, match="Unknown unit"):
        test.find("Xy")
    with pytest.raises(SpecError, match="already"):
        test.register(_yard(symbol="xY", aliases=()))


def test_names_are_unique_within_a_dimension_and_the_parser_knows_which() -> None:
    """′ is the foot for a length and could be the minute for an angle (SP 811 Table 6)."""
    minute = Unit(
        "arcmin",
        "minute",
        A,
        float(Fraction(1, 60)),
        ("′", "'"),
        "minutes",
        exact=Fraction(1, 60),
        system=UnitSystem.ACCEPTED,
        sources=get_unit("deg").sources,
        written="′",
        close_up=True,
    )
    test = _fresh()
    test.register(minute)
    assert test.find("′", A) is minute and test.find("′", L).symbol == "ft"
    with pytest.raises(UsageError, match="several dimensions"):
        test.find("′")
    assert test.ending("30′", A) == (minute, 1) and test.ending("30′", L)[0].symbol == "ft"


def test_a_frozen_registry_takes_no_more() -> None:
    test = _fresh()
    test.freeze()
    with pytest.raises(UsageError, match="frozen"):
        test.register(_yard())
    assert registry().frozen


class _EntryPoint:
    def __init__(self, name: str, loaded: Any) -> None:
        self.name, self.value, self._loaded = name, f"tests:{name}", loaded

    def load(self) -> Any:
        return self._loaded


def test_plugin_units_register_and_a_bad_one_is_skipped_with_its_reason() -> None:
    """U2: built-ins win; a clash names both; the app still starts."""

    def entry_points(*, group: str) -> list[_EntryPoint]:
        assert group == "caddcalc.units"
        return [
            _EntryPoint("good", _yard()),
            _EntryPoint("clash", [_yard(symbol="inch2", aliases=("in",))]),
            _EntryPoint("junk", ["not a unit"]),
        ]

    built = build_registry(entry_points=entry_points)
    assert built.frozen and built.find("yd").name == "yard"
    assert [e.source for e in built.plugin_errors] == [
        "clash[0] = tests:clash",
        "junk[0] = tests:junk",
    ]
    assert "'in' is already 'in', unit 'in' (inch)" in built.plugin_errors[0].message
    assert built.find("in").name == "inch", "the built-in kept its name"


def test_the_registry_is_built_once_and_cleared_for_tests() -> None:
    first = registry()
    assert registry() is first
    clear_registry()
    assert registry() is not first and registry().find("mm").symbol == "mm"


def test_the_parser_reads_whatever_the_registry_holds(monkeypatch: pytest.MonkeyPatch) -> None:
    test = _fresh()
    test.register(_yard(aliases=("yard", "yards", "sq yd")))
    test.freeze()
    monkeypatch.setattr(parsing, "registry", lambda: test)
    parsed = parse_quantity_detailed("2 yards", L)
    assert (parsed.value, parsed.unit.symbol, parsed.explicit_unit) == (1828.8, "yd", True)
    with pytest.raises(InputError, match="Unknown unit 'yardz'"):
        parse_quantity_detailed("2 yardz", L)


def test_nothing_reads_units_at_import_time() -> None:
    """ADR-0019 §4: the registry is built on first use, never while modules import."""
    code = (
        "import caddcalc.calculators, caddcalc.cli\n"
        "from caddcalc.core.units import registry\n"
        "print(registry.cache_info().currsize)"
    )
    out = subprocess.run(  # noqa: S603  # this interpreter, on code the test wrote
        [sys.executable, "-c", code], capture_output=True, text=True, check=True
    )
    assert out.stdout.strip() == "0"
