"""Domains: definitions, registration, lookup, and plugins (ADR-0013)."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, override

import pytest

from caddcalc.calculators import BUILTIN_CALCULATORS, BUILTIN_DOMAINS, default_registry
from caddcalc.calculators.sheet_metal.common import THICKNESS
from caddcalc.core import (
    Calculator,
    Context,
    Dimension,
    Domain,
    Method,
    Output,
    Param,
    Registry,
    SpecError,
    UnknownCalculatorError,
    UnknownDomainError,
    UsageError,
    Verification,
)
from caddcalc.core.formatting import describe_setting_uses
from caddcalc.core.registry import DOMAIN_ENTRY_POINT_GROUP, ENTRY_POINT_GROUP

L = Dimension.LENGTH
ACME = Domain("acme", "Acme Tools", "A plugin domain for tests.")


class _AcmeWidget(Calculator):
    id = "acme.widget"
    name = "Widget"
    domain = "acme"
    summary = "Copies a length."
    params = (Param("length", "X", "Length", L, default="1 in"),)
    outputs = (Output("copy", "Y", "Copy", L),)
    methods = (Method("only", "Only", "Y = X", Verification.UNVERIFIED),)

    @override
    def compute(self, ctx: Context) -> None:
        ctx.calc("Y", "X", label="Copy", dimension=L, output="copy")


@pytest.mark.parametrize(
    ("domain", "message"),
    [
        (Domain("Sheet-Metal", "Sheet Metal", "x"), "lowercase"),
        (Domain("blank", " ", "x"), "needs a name"),
        (
            Domain("dup", "Dup", "x", settings=(Param("t", "T", "T", L), Param("t", "U", "U", L))),
            "duplicate setting",
        ),
        (
            Domain("dflt", "Dflt", "x", settings=(Param("t", "T", "T", L, default="1 in"),)),
            "default",
        ),
        (
            Domain("meth", "Meth", "x", settings=(Param("t", "T", "T", L, methods=("a",)),)),
            "methods",
        ),
        (Domain("fn", "Fn", "x", settings=(Param("t", "sqrt", "T", L),)), "not usable"),
        (Domain("kw", "Kw", "x", settings=(Param("t", "in", "T", L),)), "not usable"),
        (
            Domain("sym", "Sym", "x", settings=(Param("t", "T", "T", L), Param("u", "T", "U", L))),
            "duplicate setting symbol",
        ),
    ],
)
def test_domain_definitions_are_validated(domain: Domain, message: str) -> None:
    with pytest.raises(SpecError, match=message):
        Registry().register_domain(domain)


def test_a_domain_registers_once() -> None:
    registry = Registry()
    registry.register_domain(ACME)
    with pytest.raises(SpecError, match="twice"):
        registry.register_domain(ACME)


def test_a_calculator_naming_an_unknown_domain_fails_with_a_hint() -> None:
    class Misnamed(_AcmeWidget):
        domain = "acmee"

    registry = Registry()
    registry.register_domain(ACME)
    with pytest.raises(SpecError, match=r"unknown domain 'acmee'\. Did you mean: acme\?"):
        registry.register(Misnamed)


def test_domain_lookup_suggests_close_ids() -> None:
    with pytest.raises(UnknownDomainError, match="sheet_metal"):
        default_registry(load_plugins=False).domain("sheet_metl")


def test_domain_hints_also_match_display_names() -> None:
    class Vague(_AcmeWidget):
        domain = "Metal"

    registry = default_registry(load_plugins=False)
    with pytest.raises(SpecError, match=r"Did you mean: sheet_metal\?"):
        registry.register(Vague)
    with pytest.raises(UnknownDomainError, match=r"Did you mean: sheet_metal\?"):
        registry.domain("Sheet Metal")


def test_lookup_errors_print_their_message_without_quotes() -> None:
    with pytest.raises(UnknownDomainError) as domain_error:
        Registry().domain("nope")
    assert str(domain_error.value) == "No domain 'nope'."
    with pytest.raises(UnknownCalculatorError) as calc_error:
        Registry().get("no.such")
    assert str(calc_error.value) == "No calculator 'no.such'."
    assert isinstance(calc_error.value, KeyError)


def test_calculators_are_grouped_by_domain_and_sorted_by_name() -> None:
    registry = default_registry(load_plugins=False)
    registry.register_domain(ACME)
    registry.register(_AcmeWidget)
    grouped = registry.by_domain()
    assert [d.name for d in grouped] == ["Geometry", "Conversions", "Sheet Metal", "Acme Tools"]
    assert [c.id for c in grouped[ACME]] == ["acme.widget"]
    for domain_id in ("geometry", "conversions", "sheet_metal"):
        names = [c.name for c in grouped[registry.domain(domain_id)]]
        assert names == sorted(names)
    assert [d.id for d in registry.domains()] == ["geometry", "conversions", "sheet_metal", "acme"]


def test_the_built_in_families_are_listed_general_tools_first() -> None:
    """ADR-0018 §1: the order is BUILTIN_DOMAINS', never the names' alphabetical order."""
    registry = default_registry(load_plugins=False)
    assert [d.id for d in registry.domains()] == [d.id for d in BUILTIN_DOMAINS]
    assert BUILTIN_DOMAINS[0].id == "geometry" and BUILTIN_DOMAINS[-1].id == "sheet_metal"
    assert next(c.domain for c in registry) == "geometry", "iteration follows it too"


@pytest.mark.parametrize(
    ("key", "users"),
    [
        (
            "thickness",
            [
                "Bend allowance & deduction",
                "Flat length of a formed segment",
                "Truncated cone flat pattern",
                "V-die opening (air bending): 8 × thickness rule of thumb",
            ],
        ),
        (
            "inside_radius",
            [
                "Bend allowance & deduction",
                "Flat length of a formed segment",
                "V-die opening (air bending): Inside-radius percentage rule",
            ],
        ),
        (
            "k_factor",
            [
                "Bend allowance & deduction: K-factor (neutral axis)",
                "Flat length of a formed segment: K-factor (neutral axis)",
            ],
        ),
    ],
)
def test_each_sheet_metal_setting_lists_the_calculators_that_use_it(
    key: str, users: list[str]
) -> None:
    registry = default_registry(load_plugins=False)
    assert describe_setting_uses(registry.setting_uses("sheet_metal", key)) == users


def test_the_family_settings_doc_lists_who_uses_each_setting() -> None:
    """The user guide's table is written by hand; this keeps it from drifting."""
    doc = Path(__file__).parents[1] / "docs" / "user" / "calculators" / "sheet-metal.md"
    section = doc.read_text(encoding="utf-8").split("## Family settings", 1)[1]
    section = section.split("\n## ", 1)[0].split("\n### ", 1)[0]  # the settings table only
    rows = {}
    for line in section.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if line.startswith("|") and cells[0] not in ("Setting", "---"):
            rows[cells[0]] = cells[1]
    registry = default_registry(load_plugins=False)
    assert rows == {
        f"{s.label} ({s.symbol})": "; ".join(
            describe_setting_uses(registry.setting_uses("sheet_metal", s.key))
        )
        for s in default_registry(load_plugins=False).domain("sheet_metal").settings
    }


def test_setting_uses_need_a_known_domain_and_setting() -> None:
    registry = default_registry(load_plugins=False)
    with pytest.raises(UnknownDomainError, match="sheet_metal"):
        registry.setting_uses("sheet_metl", "thickness")
    with pytest.raises(UsageError, match="no setting 'gauge'"):
        registry.setting_uses("sheet_metal", "gauge")
    assert _registry_with(GAUGED).setting_uses("gauged", "length") == [], "no calculators"


def test_builtin_calculator_ids_start_with_their_domain_id() -> None:
    domain_ids = {d.id for d in BUILTIN_DOMAINS}
    for calc in BUILTIN_CALCULATORS:
        assert calc.domain in domain_ids, calc.id
        assert calc.id.startswith(f"{calc.domain}."), calc.id


# --- plugins ------------------------------------------------------------------------------


@dataclass
class _FakeEntryPoint:
    name: str
    value: str
    target: Any

    def load(self) -> Any:
        if isinstance(self.target, Exception):
            raise self.target
        return self.target


def _with_plugins(
    domains: Sequence[_FakeEntryPoint] = (), calculators: Sequence[_FakeEntryPoint] = ()
) -> Registry:
    """The default registry, with these entry points as the installed plugins."""
    groups = {DOMAIN_ENTRY_POINT_GROUP: domains, ENTRY_POINT_GROUP: calculators}

    def entry_points(*, group: str) -> Sequence[_FakeEntryPoint]:
        return groups.get(group, ())

    return default_registry(entry_points=entry_points)


def test_plugin_domains_load_before_plugin_calculators() -> None:
    registry = _with_plugins(
        domains=[_FakeEntryPoint("acme", "acme:DOMAIN", ACME)],
        calculators=[_FakeEntryPoint("widget", "acme:Widget", _AcmeWidget)],
    )
    assert registry.plugin_errors == []
    assert registry.domain("acme") is ACME
    assert registry.get("acme.widget").domain == "acme"


def test_broken_plugins_are_recorded_and_never_crash() -> None:
    class Orphan(_AcmeWidget):
        id = "orphan.widget"
        domain = "orphan"

    registry = _with_plugins(
        domains=[
            _FakeEntryPoint("broken", "broken:DOMAIN", ImportError("no module")),
            _FakeEntryPoint("wrong", "wrong:DOMAIN", 42),
        ],
        calculators=[_FakeEntryPoint("orphan", "orphan:Widget", Orphan)],
    )
    errors = [(e.source, e.message) for e in registry.plugin_errors]
    assert [source for source, _ in errors] == [
        "broken = broken:DOMAIN",
        "wrong = wrong:DOMAIN",
        "orphan = orphan:Widget",
    ]
    assert "no module" in errors[0][1]
    assert "not iterable" in errors[1][1]
    assert "unknown domain 'orphan'" in errors[2][1]
    assert len(registry) == len(BUILTIN_CALCULATORS)


def test_one_bad_item_does_not_drop_the_rest_of_a_plugin() -> None:
    extra = Domain("acme_extra", "Acme Extra", "A second plugin domain.")

    class Lost(_AcmeWidget):
        id = "acme.lost"
        domain = "nowhere"

    class Gadget(_AcmeWidget):
        id = "acme.gadget"
        name = "Gadget"

    registry = _with_plugins(
        domains=[_FakeEntryPoint("pack", "acme:DOMAINS", [ACME, "junk", extra])],
        calculators=[_FakeEntryPoint("pack", "acme:CALCULATORS", [_AcmeWidget, Lost, Gadget])],
    )
    errors = {e.source: e.message for e in registry.plugin_errors}
    assert set(errors) == {"pack[1] = acme:DOMAINS", "pack[1] = acme:CALCULATORS"}
    assert "'junk' is not a Domain" in errors["pack[1] = acme:DOMAINS"]
    assert "unknown domain 'nowhere'" in errors["pack[1] = acme:CALCULATORS"]
    assert registry.domain("acme_extra") is extra
    assert [c.id for c in registry.by_domain()[ACME]] == ["acme.gadget", "acme.widget"]


def test_a_plugin_cannot_redefine_a_builtin_domain() -> None:
    impostor = Domain("sheet_metal", "Sheet Metal", "Not the built-in one.")
    registry = _with_plugins(domains=[_FakeEntryPoint("impostor", "x:DOMAIN", impostor)])
    assert [e.message for e in registry.plugin_errors] == [
        "a plugin can't redefine built-in domain 'sheet_metal'"
    ]
    assert registry.domain("sheet_metal") is next(
        d for d in BUILTIN_DOMAINS if d.id == "sheet_metal"
    )

    twice = _with_plugins(
        domains=[_FakeEntryPoint("a", "a:DOMAIN", ACME), _FakeEntryPoint("b", "b:DOMAIN", ACME)]
    )
    assert [(e.source, e.message) for e in twice.plugin_errors] == [
        ("b = b:DOMAIN", "Domain id 'acme' is registered twice")
    ]


def test_a_vendor_prefixed_plugin_calculator_can_join_a_builtin_domain() -> None:
    class FlangeCheck(Calculator):
        id = "acme.flange_check"
        name = "Flange Check"
        domain = "sheet_metal"
        summary = "Copies the material thickness."
        params = (THICKNESS,)
        outputs = (Output("copy", "Y", "Copy", L),)
        methods = (Method("only", "Only", "Y = T", Verification.UNVERIFIED),)

        @override
        def compute(self, ctx: Context) -> None:
            ctx.calc("Y", "T", label="Copy", dimension=L, output="copy")

    registry = _with_plugins(
        calculators=[_FakeEntryPoint("flange", "acme:FlangeCheck", FlangeCheck)]
    )
    assert registry.plugin_errors == []
    sheet_metal = registry.domain("sheet_metal")
    assert "acme.flange_check" in [c.id for c in registry.by_domain()[sheet_metal]]
    settings = sheet_metal.values(thickness=2.0)
    assert registry.get("acme.flange_check").run(settings=settings).outputs["copy"] == 2.0


# --- shared parameters --------------------------------------------------------------------

GAUGED = Domain(
    "gauged",
    "Gauged",
    "A domain with one length setting.",
    settings=(Param("length", "X", "Length", L),),
)


def _registry_with(domain: Domain) -> Registry:
    registry = Registry()
    registry.register_domain(domain)
    return registry


def test_a_shared_parameter_must_match_a_setting_key() -> None:
    class Unmatched(_AcmeWidget):
        id = "gauged.unmatched"
        domain = "gauged"
        params = (Param("width", "X", "Width", L, default="1 in", shared=True),)

    with pytest.raises(SpecError, match="no setting with that key"):
        _registry_with(GAUGED).register(Unmatched)


def test_a_shared_parameter_must_match_the_setting_dimension() -> None:
    class WrongKind(_AcmeWidget):
        id = "gauged.wrong_kind"
        domain = "gauged"
        params = (Param("length", "X", "Length", Dimension.ANGLE, default="1 deg", shared=True),)

    with pytest.raises(SpecError, match="measures angle, but the 'gauged' setting measures length"):
        _registry_with(GAUGED).register(WrongKind)


def test_a_matching_shared_parameter_registers_and_may_narrow_its_range() -> None:
    class Narrow(_AcmeWidget):
        id = "gauged.narrow"
        domain = "gauged"
        params = (Param("length", "X", "Length", L, default="1 in", minimum=5.0, shared=True),)

    assert _registry_with(GAUGED).register(Narrow).id == "gauged.narrow"
