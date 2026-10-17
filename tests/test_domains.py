"""Domains: definitions, registration, lookup, and plugins (ADR-0013)."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, override

import pytest

from caddcalc.calculators import BUILTIN_CALCULATORS, BUILTIN_DOMAINS, default_registry
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
    UnknownDomainError,
    Verification,
)
from caddcalc.core import registry as registry_module

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


def test_calculators_are_grouped_by_domain_and_sorted_by_name() -> None:
    registry = default_registry(load_plugins=False)
    registry.register_domain(ACME)
    registry.register(_AcmeWidget)
    grouped = registry.by_domain()
    assert [d.name for d in grouped] == ["Acme Tools", "Sheet Metal"]
    assert [c.id for c in grouped[ACME]] == ["acme.widget"]
    names = [c.name for c in grouped[registry.domain("sheet_metal")]]
    assert names == sorted(names)
    assert [d.id for d in registry.domains()] == ["acme", "sheet_metal"]


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


def _fake_entry_points(groups: dict[str, list[_FakeEntryPoint]]) -> Callable[..., Any]:
    def entry_points(*, group: str) -> list[_FakeEntryPoint]:
        return groups.get(group, [])

    return entry_points


def test_plugin_domains_load_before_plugin_calculators(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        registry_module,
        "entry_points",
        _fake_entry_points(
            {
                "caddcalc.calculators": [_FakeEntryPoint("widget", "acme:Widget", _AcmeWidget)],
                "caddcalc.domains": [_FakeEntryPoint("acme", "acme:DOMAIN", ACME)],
            }
        ),
    )
    registry = default_registry()
    assert registry.plugin_errors == []
    assert registry.domain("acme") is ACME
    assert registry.get("acme.widget").domain == "acme"


def test_broken_plugins_are_recorded_and_never_crash(monkeypatch: pytest.MonkeyPatch) -> None:
    class Orphan(_AcmeWidget):
        id = "orphan.widget"
        domain = "orphan"

    monkeypatch.setattr(
        registry_module,
        "entry_points",
        _fake_entry_points(
            {
                "caddcalc.domains": [
                    _FakeEntryPoint("broken", "broken:DOMAIN", ImportError("no module")),
                    _FakeEntryPoint("wrong", "wrong:DOMAIN", ["not a domain"]),
                ],
                "caddcalc.calculators": [_FakeEntryPoint("orphan", "orphan:Widget", Orphan)],
            }
        ),
    )
    registry = default_registry()
    messages = [e.message for e in registry.plugin_errors]
    assert len(messages) == 3
    assert "no module" in messages[0]
    assert "not a Domain" in messages[1]
    assert "unknown domain 'orphan'" in messages[2]
    assert len(registry) == len(BUILTIN_CALCULATORS)
