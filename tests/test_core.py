"""Units, the formula evaluator, formatting, and the calculator framework."""

from __future__ import annotations

import math

import pytest

from caddcalc.calculators import default_registry
from caddcalc.core import (
    CalculationError,
    Calculator,
    Context,
    Dimension,
    Domain,
    DomainValues,
    InputError,
    Method,
    Note,
    NoteKind,
    Output,
    Param,
    Reference,
    Registry,
    SpecError,
    UnknownCalculatorError,
    Verification,
    expr,
    parse_quantity,
)
from caddcalc.core.formatting import (
    DisplayPrefs,
    describe_note,
    display_unit,
    format_value,
    render_step,
    to_fraction,
)
from caddcalc.core.units import BASE_UNITS, get_unit, units_for

L, A, R = Dimension.LENGTH, Dimension.ANGLE, Dimension.RATIO


# --- units --------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "dim", "default", "expected"),
    [
        ("0.1046 in", L, None, 0.1046 * 25.4),
        ("0.1046", L, "in", 0.1046 * 25.4),
        ("3mm", L, "in", 3.0),
        ("1/8in", L, None, 3.175),
        ('1-1/2"', L, None, 38.1),
        ("1 1/2 in", L, None, 38.1),
        ("-3/4 in", L, None, -19.05),
        ("2'", L, None, 609.6),
        ("2.5e-3 m", L, None, 2.5),
        ("90°", A, None, 90.0),
        ("90", A, None, 90.0),
        ("44%", R, None, 0.44),
    ],
)
def test_parse_quantity(text: str, dim: Dimension, default: str | None, expected: float) -> None:
    assert parse_quantity(text, dim, default) == pytest.approx(expected)


@pytest.mark.parametrize("text", ["", "in", "abc", "1/0", "3 parsecs", "3 deg", "nan"])
def test_parse_quantity_rejects(text: str) -> None:
    with pytest.raises(InputError):
        parse_quantity(text, L, "in")


@pytest.mark.parametrize("dimension", list(Dimension))
def test_every_dimension_has_its_units_and_wording(dimension: Dimension) -> None:
    """A new Dimension needs an entry in every unit table, or display fails at run time."""
    assert get_unit(BASE_UNITS[dimension]).dimension is dimension
    assert units_for(dimension)
    for unit in ("in", "mm"):
        assert display_unit(dimension, DisplayPrefs(length_unit=unit)).dimension is dimension
    assert dimension.with_article.endswith(dimension.value)


def test_fraction_display() -> None:
    assert to_fraction(1.015625) == "1-1/64"
    assert to_fraction(0.5) == "1/2"
    assert to_fraction(2.0) == "2"
    assert to_fraction(-0.25) == "-1/4"


def test_format_value_converts_and_rounds_only_for_display() -> None:
    prefs = DisplayPrefs(length_unit="in", decimals=3, fraction_denominator=64)
    assert format_value(25.4, L, prefs) == '1.000 in  (≈ 1")'
    assert format_value(25.4, L, DisplayPrefs(length_unit="mm", decimals=1)) == "25.4 mm"


# --- expressions --------------------------------------------------------------------------


def test_expr_evaluates_and_renders() -> None:
    e = "pi/180*A*(R + K*T)"
    assert expr.evaluate(e, {"A": 180, "R": 1, "K": 0.5, "T": 2}) == pytest.approx(2 * 3.14159265)
    assert expr.render_symbolic(e) == "π/180·A·(R + K·T)"
    assert expr.names(e) == {"A", "R", "K", "T"}
    assert expr.render_symbolic("sqrt(x**2)") == "√(x^2)"


@pytest.mark.parametrize(
    "bad",
    ["__import__('os')", "x.real", "x[0]", "open('f')", "lambda: 1", "'s'", "x if y else z", "1 <"],
)
def test_expr_rejects_unsafe_or_invalid(bad: str) -> None:
    with pytest.raises(SpecError):
        expr.parse(bad)


def test_expr_math_errors_become_calculation_errors() -> None:
    with pytest.raises(CalculationError):
        expr.evaluate("1/x", {"x": 0})
    with pytest.raises(CalculationError):
        expr.evaluate("sqrt(x)", {"x": -1})


# --- framework ----------------------------------------------------------------------------


class _Demo(Calculator):
    id = "demo.double"
    name = "Double"
    domain = "demo"
    summary = "Doubles a length."
    params = (Param("length", "X", "Length", L, default="1 in", minimum=0.0),)
    outputs = (Output("doubled", "Y", "Doubled", L),)
    methods = (Method("only", "Only", "Y = 2·X", Verification.UNVERIFIED),)

    def compute(self, ctx: Context) -> None:
        ctx.calc("Y", "2*X", label="Doubled", dimension=L, output="doubled")


def test_run_uses_defaults_and_records_steps() -> None:
    result = _Demo().run()
    assert result.outputs["doubled"] == pytest.approx(50.8)
    assert render_step(result.steps[0], result, DisplayPrefs()) == ("2·X", "2·1.0000", "2.0000 in")
    assert result.to_dict()["outputs"]["doubled"] == {
        "value": pytest.approx(50.8),
        "unit": "mm",
        "dimension": "length",
    }


def test_notes_carry_a_kind_and_an_optional_reference() -> None:
    limit = Note(
        NoteKind.LIMIT_EXCEEDED,
        "Past the bench limit.",
        Reference("Shop handbook", "Table 4", "https://example.org/t4"),
    )
    assert limit.to_dict() == {
        "kind": "limit_exceeded",
        "text": "Past the bench limit.",
        "reference": {
            "title": "Shop handbook",
            "detail": "Table 4",
            "url": "https://example.org/t4",
        },
    }
    plain = Note(NoteKind.WARNING, "Check this.")
    assert plain.to_dict() == {"kind": "warning", "text": "Check this.", "reference": None}
    assert describe_note(plain) == "Check this."
    assert describe_note(limit) == "Limit exceeded: Past the bench limit. (Shop handbook, Table 4)"
    gap = Note(NoteKind.NO_APPLICABLE_VALUE, "No table covers 0.3 in.")
    assert describe_note(gap) == "No applicable value: No table covers 0.3 in."


def test_ctx_warn_makes_a_warning_note_unless_told_otherwise() -> None:
    class Noting(_Demo):
        def compute(self, ctx: Context) -> None:
            super().compute(ctx)
            ctx.warn("Plain.")
            ctx.warn("No data.", NoteKind.NO_APPLICABLE_VALUE, Reference("Table"))

    result = Noting().run()
    assert result.warnings == (
        Note(NoteKind.WARNING, "Plain."),
        Note(NoteKind.NO_APPLICABLE_VALUE, "No data.", Reference("Table")),
    )
    assert result.to_dict()["warnings"][1]["kind"] == "no_applicable_value"


def test_run_rejects_out_of_range_and_unknown_inputs() -> None:
    with pytest.raises(InputError, match="at least 0"):
        _Demo().run({"length": -1})
    with pytest.raises(InputError, match="no input"):
        _Demo().run({"width": 1})
    with pytest.raises(InputError, match="no method"):
        _Demo().run(method="nope")


DEMO = Domain("demo", "Demo", "Calculators for framework tests.")


def demo_registry() -> Registry:
    registry = Registry()
    registry.register_domain(DEMO)
    return registry


def test_registry_rejects_duplicates_and_bad_specs() -> None:
    reg = demo_registry()
    reg.register(_Demo)
    with pytest.raises(SpecError, match="twice"):
        reg.register(_Demo)

    class BadId(_Demo):
        id = "NoDomain"

    with pytest.raises(SpecError, match="at least two parts"):
        demo_registry().register(BadId)


@pytest.mark.parametrize("symbol", ["sqrt", "pi", "in", "2X", "T-1"])
def test_parameter_symbols_must_be_usable_in_formulas(symbol: str) -> None:
    class BadSymbol(_Demo):
        params = (Param("length", symbol, "Length", L, default="1 in"),)

    with pytest.raises(SpecError, match="not usable in formulas"):
        demo_registry().register(BadSymbol)


@pytest.mark.parametrize(
    ("default", "message"),
    [
        (
            "5 in",
            "'length' has a bad default '5 in' (= 127 mm), which must be at most 10 mm. "
            "Minimum and maximum are in base units (mm, deg, ratio).",
        ),
        ("-1 in", "bad default '-1 in' (= -25.4 mm), which must be at least 0 mm."),
        ("abc", "bad default 'abc': Cannot read a value from 'abc'"),
    ],
)
def test_a_bad_default_is_a_definition_error(default: str, message: str) -> None:
    class BadDefault(_Demo):
        params = (Param("length", "X", "Length", L, default=default, minimum=0.0, maximum=10.0),)

    with pytest.raises(SpecError) as caught:
        demo_registry().register(BadDefault)
    assert message in str(caught.value)


def test_a_registry_is_filled_only_by_registering() -> None:
    with pytest.raises(TypeError):
        Registry(_items={"demo.double": _Demo()})  # type: ignore[call-arg]


def test_registry_suggests_close_ids() -> None:
    with pytest.raises(UnknownCalculatorError, match=r"sheet_metal\.bend_allowance"):
        default_registry(load_plugins=False).get("sheet_metal.bend_alowance")


# --- every built-in calculator ------------------------------------------------------------

BUILTINS = list(default_registry(load_plugins=False))


@pytest.mark.parametrize("calc", BUILTINS, ids=lambda c: c.id)
def test_every_method_runs_on_defaults_and_renders(calc: Calculator) -> None:
    for method in calc.methods:
        result = calc.run(method=method.key)
        for step in result.steps:
            render_step(step, result, DisplayPrefs())
        for key, value in result.outputs.items():
            assert math.isfinite(value), f"{calc.id}/{method.key}: {key} is not finite"


@pytest.mark.parametrize("calc", BUILTINS, ids=lambda c: c.id)
def test_every_method_gives_the_same_result_with_no_settings_set(calc: Calculator) -> None:
    """ADR-0013: unset domain settings must never change a result."""
    unset = DomainValues(calc.domain, "Domain settings", {})
    for method in calc.methods:
        plain = calc.run(method=method.key)
        with_unset = calc.run(method=method.key, settings=unset)
        assert with_unset.outputs == plain.outputs
        assert with_unset.input_sources == plain.input_sources


@pytest.mark.parametrize("calc", BUILTINS, ids=lambda c: c.id)
def test_methods_are_documented(calc: Calculator) -> None:
    for method in calc.methods:
        assert method.summary
        if method.verification is not Verification.UNVERIFIED or method.legacy:
            assert method.references, f"{calc.id}/{method.key} claims a status without a source"
        if not method.references:
            assert any("citation" in n.lower() or "KI-" in n for n in method.notes) or (
                method.verification is Verification.UNVERIFIED
            )


# --- architecture -------------------------------------------------------------------------


def test_core_and_calculators_use_only_the_standard_library() -> None:
    """ADR-0003: the core and calculator layers import nothing outside the stdlib."""
    import ast
    import sys
    from pathlib import Path

    import caddcalc

    package = Path(caddcalc.__file__).parent
    offenders = []
    for layer in ("core", "calculators"):
        for path in (package / layer).rglob("*.py"):
            for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
                if isinstance(node, ast.Import):
                    modules = [alias.name for alias in node.names]
                elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                    modules = [node.module]
                else:
                    continue
                for module in modules:
                    top = module.split(".")[0]
                    if top == "caddcalc":
                        if module.startswith(("caddcalc.gui", "caddcalc.cli")):
                            offenders.append(f"{path.name}: {module}")
                    elif top not in sys.stdlib_module_names and top != "__future__":
                        offenders.append(f"{path.name}: {module}")
    assert not offenders, offenders


# --- evaluator hardening (review findings) ------------------------------------------------


@pytest.mark.parametrize(
    "bad",
    ["min()", "min(1)", "sqrt(1, 2)", "atan2d(1)", "True + 1", "x" + "+x" * 600, "-" * 250 + "1"],
)
def test_expr_rejects_bad_arity_bools_and_oversized_formulas(bad: str) -> None:
    with pytest.raises(SpecError):
        expr.parse(bad)


@pytest.mark.parametrize(
    ("formula", "values"),
    [("x**0.5", {"x": -4.0}), ("10.0**x", {"x": 1000.0}), ("x*1e308*10", {"x": 1.0})],
)
def test_expr_complex_and_non_finite_results_are_calculation_errors(
    formula: str, values: dict[str, float]
) -> None:
    with pytest.raises(CalculationError):
        expr.evaluate(formula, values)


def test_run_rejects_nan_and_infinite_inputs() -> None:
    for bad in (float("nan"), float("inf")):
        with pytest.raises(InputError, match="finite"):
            _Demo().run({"length": bad})


def test_expr_allows_long_flat_sums() -> None:
    """A whole-part flat length can be a long flat sum; it must not trip the depth limit."""
    terms = [f"L{i}" for i in range(150)]
    assert expr.evaluate(" + ".join(terms), dict.fromkeys(terms, 1.0)) == 150.0


def test_expr_tan_at_90_degrees_is_an_error_not_a_huge_number() -> None:
    with pytest.raises(CalculationError, match="undefined"):
        expr.evaluate("tand(x)", {"x": 90.0})
