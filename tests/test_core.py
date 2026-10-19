"""Units, the formula evaluator, formatting, and the calculator framework."""

from __future__ import annotations

import math
import time
from collections.abc import Callable, Mapping
from dataclasses import replace
from decimal import Decimal
from fractions import Fraction

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
    Result,
    SpecError,
    UnknownCalculatorError,
    UsageError,
    Verification,
    expr,
    parse_quantity,
)
from caddcalc.core.formatting import (
    DisplayPrefs,
    describe_note,
    display_unit,
    entry_unit,
    format_value,
    render_step,
    to_fraction,
    unit_suffix,
)
from caddcalc.core.units import BASE_UNITS, get_unit, to_base, units_for

L, A, R, S = Dimension.LENGTH, Dimension.ANGLE, Dimension.RATIO, Dimension.STRESS
KSI_IN_MPA = 6.894757293168361
"""1 ksi in MPa: 1000 lbf (0.45359237 kg × 9.80665 m/s², exact) over 0.0254² m² (exact)."""


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
        ("36 ksi", S, None, 36 * KSI_IN_MPA),
        ("36000 psi", S, None, 36 * KSI_IN_MPA),
        ("250", S, None, 250.0),
        ("250 MPa", S, "ksi", 250.0),
        ("0.2 GPa", S, None, 200.0),
        ("500 kPa", S, None, 0.5),
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
    assert get_unit(BASE_UNITS[dimension], dimension).dimension is dimension
    assert units_for(dimension)
    for unit in ("in", "mm"):
        assert display_unit(dimension, DisplayPrefs(length_unit=unit)).dimension is dimension
    assert dimension.with_article.endswith(dimension.value)
    for unit in ("in", "mm"):
        prefs = DisplayPrefs(length_unit=unit)
        assert entry_unit(dimension, prefs) == display_unit(dimension, prefs).symbol


def test_stress_units_come_from_the_exact_pound_and_inch() -> None:
    assert to_base(1, "ksi") == pytest.approx(KSI_IN_MPA, rel=1e-15)
    # In exact arithmetic: each double is its definition rounded once (ADR-0019 §2), so
    # 1000 times psi's double is a second rounding away from ksi's.
    assert get_unit("ksi").exact == 1000 * get_unit("psi").exact
    assert get_unit("megapascals").symbol == "MPa"


@pytest.mark.parametrize(
    ("length_unit", "shown", "suffix"),
    [("in", "42.0 ksi", " ksi"), ("ft", "42.0 ksi", " ksi"), ("mm", "289.6 MPa", " MPa")],
)
def test_stress_follows_the_length_preference(length_unit: str, shown: str, suffix: str) -> None:
    """One choice sets both: inch-pound lengths show ksi, metric lengths MPa."""
    prefs = DisplayPrefs(length_unit=length_unit)
    assert format_value(to_base(42, "ksi"), S, prefs) == shown
    assert unit_suffix(S, prefs) == suffix


def test_a_bare_number_is_read_in_the_display_unit() -> None:
    """A field labelled ksi reads "36" as 36 ksi, not 36 of the base unit (MPa)."""
    prefs = DisplayPrefs(length_unit="in")
    assert parse_quantity("36", S, entry_unit(S, prefs)) == pytest.approx(36 * KSI_IN_MPA)
    assert parse_quantity("0.5", L, entry_unit(L, prefs)) == pytest.approx(12.7)
    assert parse_quantity("90", A, entry_unit(A, prefs)) == 90.0


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


def test_notes_carry_a_kind_references_and_subjects() -> None:
    handbook = Reference("Shop handbook", "Table 4", "https://example.org/t4")
    limit = Note(
        NoteKind.LIMIT_EXCEEDED,
        "Past the bench limit.",
        (handbook, Reference("Second source")),
        ("length",),
    )
    assert limit.to_dict() == {
        "kind": "limit_exceeded",
        "text": "Past the bench limit.",
        "detail": "",
        "quantities": {},
        "references": [
            {
                "title": "Shop handbook",
                "detail": "Table 4",
                "url": "https://example.org/t4",
                "edition": "",
                "locator": "",
                "accessed": None,
                "scope": "",
                "short_title": "",
            },
            {
                "title": "Second source",
                "detail": "",
                "url": "",
                "edition": "",
                "locator": "",
                "accessed": None,
                "scope": "",
                "short_title": "",
            },
        ],
        "subjects": ["length"],
    }
    plain = Note(NoteKind.WARNING, "Check this.")
    assert plain.to_dict() == {
        "kind": "warning",
        "text": "Check this.",
        "detail": "",
        "quantities": {},
        "references": [],
        "subjects": [],
    }


@pytest.mark.parametrize(
    ("note", "wording"),
    [
        (Note(NoteKind.WARNING, "Check this."), ("Check this.",)),
        (
            Note(NoteKind.LIMIT_EXCEEDED, "Too tight.", (Reference("A", "p. 1"), Reference("B"))),
            ("Limit exceeded: Too tight.", "Sources: A, p. 1 · B"),
        ),
        (
            Note(NoteKind.NO_APPLICABLE_VALUE, "No table covers it.", detail="Why not."),
            ("No applicable value: No table covers it.", "Why not."),
        ),
        (Note(NoteKind.INFEASIBLE, "Too short."), ("Not makeable: Too short.",)),
    ],
)
def test_notes_are_worded_once_for_every_front_end(note: Note, wording: tuple[str, ...]) -> None:
    """ADR-0017 F1: the lead, then the detail, then the sources, each its own part."""
    assert describe_note(note, DisplayPrefs()).lines == wording


def test_a_notes_fields_are_filled_in_the_display_units_and_in_base_units_in_json() -> None:
    note = Note(
        NoteKind.WARNING,
        "Radius {R} is under {T} for {material}.",
        detail="Nothing joined: {material} {{as}} written.",
        quantities={"R": (25.4, Dimension.LENGTH), "T": (50.8, Dimension.LENGTH)},
        phrases={"material": "brass {not a field}"},
    )
    text = describe_note(note, DisplayPrefs())
    assert text.lead == "Radius 1.0000 in is under 2.0000 in for brass {not a field}."
    assert text.detail == "Nothing joined: brass {not a field} {as} written."
    metric = describe_note(note, DisplayPrefs(length_unit="mm"))
    assert metric.lead.startswith("Radius 25.4000 mm is under 50.8000 mm")
    data = note.to_dict()
    assert data["text"] == "Radius 25.4 mm is under 50.8 mm for brass {not a field}."
    assert data["quantities"]["T"] == {"value": 50.8, "unit": "mm", "dimension": "length"}
    assert hash(note) == hash(Note(NoteKind.WARNING, note.text, detail=note.detail))
    assert Note(NoteKind.WARNING, "A {plain} note.").to_dict()["text"] == "A {plain} note."


@pytest.mark.parametrize(
    ("text", "fields", "problem"),
    [
        ("Radius {} is tight.", {"R": (1.0, Dimension.LENGTH)}, "unnamed field"),
        ("Radius {0} is tight.", {"R": (1.0, Dimension.LENGTH)}, "names '0'"),
        ("Radius {S} is tight.", {"R": (1.0, Dimension.LENGTH)}, "names 'S'"),
        ("Radius {R is tight.", {"R": (1.0, Dimension.LENGTH)}, "isn't a template"),
        ("Radius {R:.2f} is tight.", {"R": (1.0, Dimension.LENGTH)}, "must be a name alone"),
        ("Radius {R!r} is tight.", {"R": (1.0, Dimension.LENGTH)}, "must be a name alone"),
    ],
)
def test_a_notes_fields_must_be_named_and_given(
    text: str, fields: dict[str, tuple[float, Dimension]], problem: str
) -> None:
    """Named fields only, so a translation can reorder them (ADR-0017, amendments)."""
    with pytest.raises(SpecError, match=problem):
        Note(NoteKind.WARNING, text, quantities=fields)
    with pytest.raises(SpecError, match="both quantities and phrases"):
        Note(NoteKind.WARNING, "{R}", quantities={"R": (1.0, Dimension.LENGTH)}, phrases={"R": "x"})


def test_a_limit_exceeded_note_must_cite_its_limit() -> None:
    with pytest.raises(SpecError, match="must cite its limit"):
        Note(NoteKind.LIMIT_EXCEEDED, "Too tight.")


def test_ctx_note_records_kinds_references_and_subjects() -> None:
    class Noting(_Demo):
        def compute(self, ctx: Context) -> None:
            super().compute(ctx)
            ctx.warn("Plain.", subjects=("length",))
            ctx.note(
                "No data.",
                NoteKind.NO_APPLICABLE_VALUE,
                references=[Reference("Table")],
                subjects=["doubled"],
            )

    result = Noting().run()
    assert result.notes == (
        Note(NoteKind.WARNING, "Plain.", (), ("length",)),
        Note(NoteKind.NO_APPLICABLE_VALUE, "No data.", (Reference("Table"),), ("doubled",)),
    )
    assert result.to_dict()["notes"][1] == {
        "kind": "no_applicable_value",
        "text": "No data.",
        "detail": "",
        "quantities": {},
        "references": [
            {
                "title": "Table",
                "detail": "",
                "url": "",
                "edition": "",
                "locator": "",
                "accessed": None,
                "scope": "",
                "short_title": "",
            }
        ],
        "subjects": ["doubled"],
    }


def _note_material(ctx: Context, selections: Mapping[str, str]) -> None:
    """A result check that names the chosen material, or says none was chosen."""
    material = selections.get("material")
    if material is None:
        ctx.note("No material chosen.", NoteKind.NO_APPLICABLE_VALUE, subjects=("length",))
    else:
        ctx.warn(f"Checked for {material}.", subjects=("doubled",))


class _Checked(_Demo):
    checks = (_note_material,)

    def compute(self, ctx: Context) -> None:
        super().compute(ctx)
        ctx.warn("From compute.")


def test_result_checks_run_after_compute_and_see_the_selections() -> None:
    settings = DomainValues("demo", "Demo settings", {}, selections={"material": "al:6061"})
    result = _Checked().run(settings=settings)
    assert [n.text for n in result.notes] == ["From compute.", "Checked for al:6061."]
    assert result.notes[1].subjects == ("doubled",)
    assert _Checked().run().notes[1] == Note(
        NoteKind.NO_APPLICABLE_VALUE, "No material chosen.", (), ("length",)
    )


CARRIED = Note(NoteKind.WARNING, "Carried with the input.")


def _checked_by(check: Callable[[Context, Mapping[str, str]], None]) -> Result:
    """Run the demo with one result check, and a note carried by its explicit input."""

    class Checked(_Demo):
        checks = (check,)

    return Checked().run({"length": 25.4}, explicit_notes={"length": CARRIED})


def _recompute(ctx: Context, _selections: Mapping[str, str]) -> None:
    ctx.calc("Z", "X", label="Again", dimension=L)


def _replace_step(ctx: Context, _selections: Mapping[str, str]) -> None:
    ctx.steps[0] = replace(ctx.steps[0], value=0.0)


def _clear_notes(ctx: Context, _selections: Mapping[str, str]) -> None:
    ctx.notes.clear()


def _add_symbol(ctx: Context, _selections: Mapping[str, str]) -> None:
    ctx.symbols["Q"] = (1.0, L)


def _change_output(ctx: Context, _selections: Mapping[str, str]) -> None:
    ctx.outputs["doubled"] = 0.0


@pytest.mark.parametrize(
    "check", [_recompute, _replace_step, _clear_notes, _add_symbol, _change_output]
)
def test_a_result_check_changes_nothing_in_place(
    check: Callable[[Context, Mapping[str, str]], None],
) -> None:
    """Steps, symbols, outputs, and earlier notes, the carried caution among them."""
    with pytest.raises(SpecError, match=f"check {check.__name__} changed the run"):
        _checked_by(check)


def test_a_result_check_may_not_repeat_a_note() -> None:
    def twice(ctx: Context, _selections: Mapping[str, str]) -> None:
        ctx.warn("Once is enough.")
        ctx.warn("Once is enough.")

    def again(ctx: Context, _selections: Mapping[str, str]) -> None:
        ctx.notes.append(replace(CARRIED, subjects=("length",)))

    with pytest.raises(SpecError, match=r"check twice repeated the note 'Once is enough\.'"):
        _checked_by(twice)
    with pytest.raises(SpecError, match="check again repeated the note"):
        _checked_by(again)


def test_a_failing_check_is_a_definition_error() -> None:
    def lookup(_ctx: Context, selections: Mapping[str, str]) -> None:
        if selections["material"]:
            return

    def stray(ctx: Context, _selections: Mapping[str, str]) -> None:
        ctx.warn("Odd.", subjects=("width",))

    with pytest.raises(SpecError, match=r"demo\.double: check lookup failed") as raised:
        _checked_by(lookup)
    assert isinstance(raised.value.__cause__, KeyError)
    with pytest.raises(SpecError, match=r"check stray failed: .*note subjects \['width'\]"):
        _checked_by(stray)


def test_a_check_sees_each_inputs_source_read_only() -> None:
    """Review L2: a check tells a derived thickness from a typed one by its source."""
    seen: dict[str, str] = {}

    def sources(ctx: Context, _selections: Mapping[str, str]) -> None:
        seen.update({k: s.kind.value for k, s in ctx.sources.items()})
        with pytest.raises(TypeError):
            ctx.sources["length"] = ctx.sources["length"]  # type: ignore[index]

    _checked_by(sources)
    assert seen == {"length": "explicit"}


def test_notes_are_carried_then_computed_then_checked() -> None:
    def checked(ctx: Context, _selections: Mapping[str, str]) -> None:
        ctx.warn("From the check.")

    class Ordered(_Demo):
        checks = (checked,)

        def compute(self, ctx: Context) -> None:
            super().compute(ctx)
            ctx.warn("From compute.")

    result = Ordered().run({"length": 25.4}, explicit_notes={"length": CARRIED})
    assert [n.text for n in result.notes] == [CARRIED.text, "From compute.", "From the check."]


def test_checks_are_a_tuple_of_callables() -> None:
    class Listed(_Demo):
        # A mutable list is the mistake under test.
        checks = [_note_material]  # type: ignore[assignment]  # noqa: RUF012

    with pytest.raises(SpecError, match="checks must be a tuple"):
        Listed.validate_spec()


def test_note_subjects_must_be_parameters_or_outputs() -> None:
    class Stray(_Demo):
        def compute(self, ctx: Context) -> None:
            super().compute(ctx)
            ctx.warn("Odd.", subjects=("width",))

    with pytest.raises(SpecError, match=r"note subjects \['width'\]"):
        Stray().run()


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
            "Minimum and maximum are in base units (mm, deg, ratio, MPa, mm², count).",
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


def test_expr_sine_and_cosine_are_exactly_0_where_they_are_0() -> None:
    """π/180 is rounded, so sin(radians(180)) is 1.2e-16; sind(180) is 0, as sinPi(1) is."""
    for k in range(-8, 9):
        assert expr.evaluate("sind(x)", {"x": 180.0 * k}) == 0.0, k
        assert expr.evaluate("cosd(x)", {"x": 90.0 + 180.0 * k}) == 0.0, k
    assert math.sin(math.radians(180)) != 0, "the case it's for"
    for deg in (0.5, 30.0, 45.0, 89.99999999, 179.99999999, 1e6 + 0.5):
        assert expr.evaluate("sind(x)", {"x": deg}) == math.sin(math.radians(deg)), deg
        assert expr.evaluate("cosd(x)", {"x": deg}) == math.cos(math.radians(deg)), deg
    assert (
        expr.evaluate("sind(x)", {"x": 90.0}) == 1.0
        and expr.evaluate("cosd(x)", {"x": 180.0}) == -1.0
    )


def test_expr_evaluates_exactly_with_exact_inputs() -> None:
    """The same expression, evaluated as rationals; 0.1 + 0.2 is 3/10, not 0.30000000000000004."""
    assert expr.evaluate_exact("a + b", {"a": Decimal("0.1"), "b": Fraction(1, 5)}, digits=10) == (
        Fraction(3, 10)
    )
    assert expr.evaluate_exact(
        "(w + c) / 16 / B", {"w": 70, "c": 0, "B": Decimal("41.82")}, digits=10
    ) == (Fraction(70, 16) / Fraction("41.82"))
    assert expr.evaluate_exact("x ** 3 - -x", {"x": Fraction(1, 2)}, digits=10) == Fraction(5, 8)
    assert expr.evaluate_exact("0.005 * 2", {}, digits=10) == Fraction(1, 100), "literal as written"


def test_expr_evaluates_a_non_integer_power_to_the_stated_digits() -> None:
    root = expr.evaluate_exact("x ** (1 / 2)", {"x": 2}, digits=30)
    assert abs(root - Fraction("1.41421356237309504880168872421")) < Fraction(1, 10**28)
    assert expr.evaluate_exact("x ** (1 / 2)", {"x": 2}, digits=5) == Fraction("1.4142")
    assert expr.evaluate_exact("0 ** (1 / 2)", {}, digits=5) == 0


@pytest.mark.parametrize(
    ("symbols", "message"),
    [
        ({"x": 0.5}, "needs exact values; x is float 0.5"),
        ({"x": True}, "needs exact values; x is bool"),
        ({"x": Decimal("NaN")}, "needs finite values"),
    ],
)
def test_a_float_cant_reach_the_exact_evaluator(symbols: dict[str, object], message: str) -> None:
    with pytest.raises(UsageError, match=message):
        expr.evaluate_exact("x + 1", symbols, digits=10)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("formula", "error", "message"),
    [
        ("sqrt(x)", SpecError, "functions have no exact value"),
        ("pi * x", SpecError, "pi has no exact value"),
        ("y + 1", SpecError, "unknown symbol 'y'"),
        ("1 / (x - 4)", CalculationError, "Division by zero"),
        ("(0 - x) ** (1 / 2)", CalculationError, "not a real number"),
        ("x ** 100000", CalculationError, "exceed 100000 bits"),
        ("0 ** (0 - 1 / 2)", CalculationError, "Division by zero"),
        ("0 ** (0 - 1)", CalculationError, "Division by zero"),
    ],
)
def test_the_exact_evaluator_refuses_what_has_no_exact_value(
    formula: str, error: type[Exception], message: str
) -> None:
    with pytest.raises(error, match=message):
        expr.evaluate_exact(formula, {"x": 4}, digits=10)
    with pytest.raises(UsageError, match="digits from 1 to 1000"):
        expr.evaluate_exact("x", {"x": 4}, digits=0)


def test_zero_to_a_power_follows_evaluate() -> None:
    assert expr.evaluate_exact("0 ** 0", {}, digits=10) == 1 == expr.evaluate("0 ** 0", {})
    assert expr.evaluate_exact("0 ** (1 / 2)", {}, digits=10) == 0
    assert expr.evaluate_exact("(0 - 1) ** 100001", {}, digits=10) == -1, "a unit base is cheap"


@pytest.mark.parametrize(
    "formula",
    [
        "((10 ** 1000) ** 1000) ** 1000",
        "(10 ** 3000) * (10 ** 3000) * (10 ** 3000) * (10 ** 3000) * (10 ** 3000) * (10 ** 3000)"
        " * (10 ** 3000) * (10 ** 3000) * (10 ** 3000) * (10 ** 3000) * (10 ** 3000)",
        "1 / (10 ** 30000) / (10 ** 30000) / (10 ** 30000) / (10 ** 30000)",
        "2 ** (10 ** 9 / 3)",
        "2 ** (0 - 10 ** 9 / 3)",
    ],
)
def test_the_exact_evaluator_refuses_runaway_values_promptly(formula: str) -> None:
    """The reviewer's probe hung before the size bound; nesting compounded the exponents."""
    started = time.perf_counter()
    with pytest.raises(CalculationError, match="exceed 100000 bits"):
        expr.evaluate_exact(formula, {}, digits=40)
    assert time.perf_counter() - started < 2.0


def test_a_steps_expression_unit_must_measure_its_dimension() -> None:
    from caddcalc.core import Step

    with pytest.raises(SpecError, match="only a formula step"):
        Step("T", "Thickness", Dimension.LENGTH, 1.0, expression_unit="in")
    with pytest.raises(SpecError, match="Unknown unit 'furlong'"):
        Step("T", "Thickness", Dimension.LENGTH, 1.0, "t", expression_unit="furlong")
    with pytest.raises(SpecError, match="'deg' doesn't measure a length"):
        Step("T", "Thickness", Dimension.LENGTH, 1.0, "t", expression_unit="deg")


def test_work_in_its_own_unit_is_shown_in_it_then_in_the_display_unit() -> None:
    """KI-005: "(70 + 0) / 16 / 41.82 = 2.6568 mm" would be false; the expression gives inches."""
    from caddcalc.core import Step
    from caddcalc.core.formatting import DisplayPrefs, render_step

    step = Step(
        "T",
        "Thickness",
        Dimension.LENGTH,
        0.1046 * 25.4,
        "(w + c) / 16 / B",
        substitution={"w": "70", "c": "0", "B": "41.82"},
        expression_unit="in",
    )
    inches = render_step(step, None, DisplayPrefs())
    assert inches == ("(w + c) / 16 / B", "(70 + 0) / 16 / 41.82", "0.1046 in")
    millimetres = render_step(step, None, DisplayPrefs(length_unit="mm"))
    assert millimetres[1:] == ("(70 + 0) / 16 / 41.82", "0.1046 in = 2.6568 mm")


def test_every_step_lists_its_substitution_and_expression_unit_in_json() -> None:
    result = default_registry(load_plugins=False).get("sheet_metal.bend_allowance").run()
    step = result.to_dict()["steps"][0]
    assert (step["substitution"], step["expression_unit"], step["stated"]) == (None, None, None)


@pytest.mark.parametrize(
    "value",
    [Decimal("1e-40000"), Decimal("1e40000"), Decimal("1e400000000"), 2**100001],
    ids=["tiny Decimal", "huge Decimal", "vast Decimal", "huge int"],
)
def test_an_oversized_input_is_a_calculation_error(value: Decimal | int) -> None:
    """The bound covers inputs too, before they are built, as the docstring promises."""
    started = time.perf_counter()
    with pytest.raises(CalculationError, match="exceed 100000 bits"):
        expr.evaluate_exact("x + 1", {"x": value}, digits=10)
    assert time.perf_counter() - started < 2.0
    assert expr.evaluate_exact("x", {"x": Decimal("1e20000")}, digits=10) == 10**20000


def test_the_exact_evaluators_digits_are_capped_before_any_work() -> None:
    started = time.perf_counter()
    with pytest.raises(UsageError, match="digits from 1 to 1000, not 20000"):
        expr.evaluate_exact("2 ** 0.5", {}, digits=20000)
    assert time.perf_counter() - started < 0.5
    assert abs(expr.evaluate_exact("2 ** 0.5", {}, digits=1000) ** 2 - 2) < Fraction(1, 10**990)


def test_a_stated_value_is_shown_as_stated_in_either_unit() -> None:
    """Review M3: rounding 0.109375 in to 0.1094 in made a third value for 12 ga."""
    from caddcalc.core import Step
    from caddcalc.core.formatting import DisplayPrefs, render_step

    step = Step(
        "T",
        "Thickness",
        Dimension.LENGTH,
        0.109375 * 25.4,
        "w / 16 / B",
        substitution={"w": "70", "B": "40"},
        expression_unit="in",
        stated="0.109375 in",
    )
    assert render_step(step, None, DisplayPrefs())[2] == "0.109375 in"
    assert render_step(step, None, DisplayPrefs(length_unit="mm"))[2] == ("0.109375 in = 2.7781 mm")
    with pytest.raises(SpecError, match="needs an expression_unit"):
        Step("T", "Thickness", Dimension.LENGTH, 2.778125, "t", stated="0.109375 in")
    with pytest.raises(SpecError, match="isn't its value in in"):
        Step("T", "T", Dimension.LENGTH, 2.778125, "t", expression_unit="in", stated="0.1094 in")
    with pytest.raises(SpecError, match="isn't its value in in"):
        Step("T", "T", Dimension.LENGTH, 2.778125, "t", expression_unit="in", stated="2.778125 mm")
    with pytest.raises(SpecError, match="stated value"):
        Step("T", "T", Dimension.LENGTH, 2.778125, "t", expression_unit="in", stated="thick")


def test_a_methods_notes_name_their_values_and_read_in_the_users_format() -> None:
    """UI/UX's i4 L2: the app's own numbers in a note are values, filled where shown."""
    from caddcalc.core.errors import SpecError
    from caddcalc.core.formatting import DisplayPrefs, NumberSymbols, method_notes
    from caddcalc.core.units import Dimension

    angle = (132.70, Dimension.ANGLE)
    method = Method(
        "m", "M", "S", Verification.UNVERIFIED, notes=("gives {a}",), quantities={"a": angle}
    )
    assert method_notes(method, DisplayPrefs()) == ("gives 132.70°",)
    assert method_notes(method, DisplayPrefs(symbols=NumberSymbols(","))) == ("gives 132,70°",)
    plain = Method("m", "M", "S", Verification.UNVERIFIED, notes=("braces {kept}",))
    assert method_notes(plain, DisplayPrefs()) == ("braces {kept}",), "no values: plain text"
    for notes in (("gives {b}",), ("gives {}",), ("gives {a:.2f}",)):
        with pytest.raises(SpecError):
            Method("m", "M", "S", Verification.UNVERIFIED, notes=notes, quantities={"a": angle})


def test_a_status_writes_its_scope_and_the_verification_note_follows_the_notes() -> None:
    """ADR-0010's amendments: "verified at 90°"; an unverified method has no scope."""
    verified = Method(
        "m",
        "M",
        "S",
        Verification.VERIFIED,
        notes=("a note",),
        legacy=True,
        scope="at 90°",
        verification_note="Verified at 90°, against an example.",
    )
    assert verified.status == "verified at 90° · reproduces legacy"
    assert verified.notes_shown(lambda v, _d: str(v)) == (
        "a note",
        "Verified at 90°, against an example.",
    )
    assert Method("m", "M", "S", Verification.VERIFIED).status == "verified"
    with pytest.raises(SpecError, match="has a scope, but isn't verified"):
        Method("m", "M", "S", Verification.UNVERIFIED, scope="at 90°")
