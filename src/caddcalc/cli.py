"""Command-line front end.

caddcalc list
caddcalc show sheet_metal.bend_allowance
caddcalc run sheet_metal.bend_allowance T=0.1046 R=0.156 A=90 --method course
caddcalc run sheet_metal.bend_allowance T=3mm R=4mm A=120 --output-set mm --json
caddcalc run geometry.circle --unit d=ft_in d=10-2 --output-set ft_in
caddcalc gui
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import traceback
from collections.abc import Mapping, Sequence
from dataclasses import replace

from caddcalc import __version__
from caddcalc.calculators import default_registry
from caddcalc.core import (
    CaddCalcError,
    Calculator,
    InputError,
    Output,
    Param,
    Result,
    TypedValue,
    i18n,
)
from caddcalc.core.formatting import (
    DISCLAIMER,
    DisplayPrefs,
    ShownUnits,
    choice_unit,
    describe_error,
    describe_note,
    describe_source,
    entered_form,
    format_input,
    format_output,
    method_notes,
    render_step,
    result_json,
)
from caddcalc.core.i18n import _
from caddcalc.core.units import UnitInTextError, registry

LANGUAGE_VARIABLES = ("CADDCALC_LANG", "LANGUAGE", "LC_ALL", "LC_MESSAGES", "LANG")
"""Where the CLI finds its language after ``--lang``: ours, then the variables Python's
gettext reads, in its order (ADR-0020 §3)."""


def cli_languages(lang: str | None, environ: Mapping[str, str]) -> list[str]:
    """Return the languages the CLI writes in, most wanted first; empty for the source.

    ``--lang`` wins, then the first of ``LANGUAGE_VARIABLES`` that's set. Each is a list
    of languages separated by colons, as ``LANGUAGE`` is, and ``C`` or ``POSIX`` in it
    means the source language from there on, as gettext reads it.
    """
    for value in (lang, *(environ.get(name) for name in LANGUAGE_VARIABLES)):
        if value:
            languages = []
            for name in value.split(":"):
                if name.split(".", 1)[0] in ("C", "POSIX"):
                    break
                if name:
                    languages.append(name)
            return languages
    return []


def main(argv: Sequence[str] | None = None) -> int:
    """Run the ``caddcalc`` command line and return the exit status."""
    _ensure_unicode_output()
    parser = _build_parser()
    args = _parse(parser, argv)
    # Words follow the language; numbers keep "." for scripts (ADR-0020 §§3-4).
    i18n.use(cli_languages(args.lang, os.environ))
    if args.command is None:
        parser.print_help()
        return 0
    try:
        return int(args.handler(args))
    except CaddCalcError as exc:
        # Only running a calculator raises range errors, and _cmd_run words them itself.
        _write_cause(exc)
        return _fail(str(exc))


def _parse(parser: argparse.ArgumentParser, argv: Sequence[str] | None) -> argparse.Namespace:
    """Parse the arguments, a run's ``NAME=VALUE`` inputs wherever they're given.

    Before Python 3.13, argparse gives a positional that takes any number of arguments
    only those before the first option, so ``run CALC --method course T=3`` left ``T=3``
    unrecognized. Each argument of a run left over that isn't an option joins its inputs,
    as Python 3.13 takes it, so a stray word is refused as an input in every version;
    an unknown option is refused as argparse refuses it.
    """
    args, extra = parser.parse_known_args(argv)
    inputs = [e for e in extra if not e.startswith("-")]
    if args.command == "run" and inputs:
        args.inputs = [*args.inputs, *inputs]
        extra = [e for e in extra if e not in inputs]
    if extra:
        parser.error(f"unrecognized arguments: {' '.join(extra)}")
    return args


def _write_cause(exc: CaddCalcError) -> None:
    """Write a wrapped bug's traceback, such as a plugin's error in a SpecError."""
    if exc.__cause__ is not None:
        traceback.print_exception(exc, file=sys.stderr)


def _fail(message: str) -> int:
    """Print an error and return the exit status for it."""
    print(f"error: {message}", file=sys.stderr)
    return 2


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="caddcalc", description="CADD drafting calculators.")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument(
        "--lang",
        metavar="LANG",
        help="the language to write in, e.g. en_GB (default: CADDCALC_LANG, then LANGUAGE, "
        "LC_ALL, LC_MESSAGES, LANG); numbers always use '.'",
    )
    sub = parser.add_subparsers(dest="command")

    p_list = sub.add_parser("list", help="list available calculators")
    p_list.add_argument("--json", action="store_true", help="machine-readable output")
    p_list.set_defaults(handler=_cmd_list)

    p_show = sub.add_parser("show", help="describe a calculator's inputs, outputs, and methods")
    p_show.add_argument("calculator")
    p_show.set_defaults(handler=_cmd_show)

    p_run = sub.add_parser("run", help="run a calculator")
    p_run.add_argument("calculator")
    p_run.add_argument(
        "inputs",
        nargs="*",
        metavar="NAME=VALUE",
        help="input by key or symbol, with its unit, e.g. T=3mm or A=90°; a bare number is "
        "in the input's default unit, which 'caddcalc show' lists",
    )
    p_run.add_argument("--method", help="method key (default: the calculator's first method)")
    p_run.add_argument(
        "--unit",
        action="append",
        default=[],
        metavar="NAME=ID",
        help="read input NAME in the unit or form ID, as a field picked in it reads it, "
        "e.g. --unit L=ft_in L=10-2; repeatable",
    )
    p_run.add_argument(
        "--output-set",
        action="append",
        default=[],
        metavar="SET",
        help="the units the results show in, e.g. mm or in_16 (default: the calculator's "
        "first; 'caddcalc show' lists them)",
    )
    p_run.add_argument(
        "--output-unit",
        action="append",
        default=[],
        metavar="KEY=ID",
        help="the unit an output with its own picker shows in; repeatable",
    )
    p_run.add_argument("--decimals", type=int, default=4)
    p_run.add_argument(
        "--json",
        action="store_true",
        help="machine-readable output: schema 1, each value in base units and as shown",
    )
    p_run.add_argument("--no-work", action="store_true", help="hide the step-by-step work")
    p_run.set_defaults(handler=_cmd_run)

    p_gui = sub.add_parser("gui", help="open the desktop app (needs the 'gui' extra)")
    p_gui.set_defaults(handler=_cmd_gui)
    return parser


def _cmd_list(args: argparse.Namespace) -> int:
    registry = default_registry()
    if args.json:
        rows = [
            {
                "id": c.id,
                "name": c.name,
                "domain": c.domain,
                "domain_name": registry.domain(c.domain).name,
                "summary": c.summary,
            }
            for c in registry
        ]
        print(json.dumps(rows, indent=2, ensure_ascii=False))
        return 0
    for domain, calcs in registry.by_domain().items():
        print(_(domain.name))
        for c in calcs:
            print(f"  {c.id:<40} {_(c.name)}")
    for err in registry.plugin_errors:
        print(f"warning: plugin {err.source} failed to load: {err.message}", file=sys.stderr)
    return 0


def _cmd_show(args: argparse.Namespace) -> int:
    registry = default_registry()
    calc = registry.get(args.calculator)
    print(f"{_(calc.name)}  [{calc.id}]")
    print(f"  {_(calc.summary)}")
    print(f"  Domain: {registry.domain(calc.domain).name}\n")
    print("Inputs")
    for p in calc.params:
        scope = f"  (methods: {', '.join(p.methods)})" if p.methods else ""
        default = f"  default {p.default}" if p.default else ""
        print(f"  {p.symbol:<6} {p.key:<20} {p.label}{default}{scope}")
        if any(p.choices):
            print(f"         Units (--unit): {_choices_text(p.choices, p.default_choice)}")
        if p.help:
            print(f"         {p.help}")
    print("\nOutputs")
    for o in calc.outputs:
        print(f"  {o.symbol:<6} {o.key:<20} {o.label}")
        if o.picks:
            print(f"         Units (--output-unit): {_choices_text(o.picks, o.picks[0])}")
        elif o.unit or o.form:
            print(f"         Always in {o.form or o.unit}")
    sets = calc.unit_sets()
    if sets:
        print("\nOutput sets (--output-set)")
        for i, unit_set in enumerate(sets):
            first = "  (default)" if i == 0 else ""
            print(f"  {unit_set.key:<10} {unit_set.label}{first}")
    print("\nMethods")
    for m in calc.methods:
        print(f"  {m.key:<14} {m.label}  [{m.status}]")
        print(f"         {m.summary}")
        for note in method_notes(m, ShownUnits.generated(), DisplayPrefs()):
            print(f"         Note: {note}")
        for ref in m.references:
            print(f"         Ref: {ref}")
    return 0


def _choices_text(choices: Sequence[str], default: str | None) -> str:
    """Return choices' ids as ``show`` lists them: ``in (default), ft_in, mm``."""
    return ", ".join(f"{c} (default)" if c == default else c for c in choices)


def _resolve_param(calc: Calculator, name: str, used: Sequence[Param]) -> Param:
    """Return the input ``name`` names: by its exact key or symbol, else in any case.

    An exact match comes first, so ``a`` and ``A`` can be a side and an angle. A name
    matched in any case must match one symbol only, among the results too: ``B`` for a
    triangle is its angle, a result, and never its side ``b``. Only the inputs in
    ``used``, the chosen method's, are offered in its place.

    Raises:
        InputError: No input has the name, or, in any case, several inputs or results do.
    """
    exact = [p for p in calc.params if name in (p.key, p.symbol)]
    if len(exact) == 1:
        return exact[0]
    folded = name.casefold()
    matches = [p for p in calc.params if folded in (p.key.casefold(), p.symbol.casefold())]
    symbols = {p.symbol for p in matches}
    results = [
        o
        for o in calc.outputs
        if folded in (o.key.casefold(), o.symbol.casefold()) and o.symbol not in symbols
    ]
    if len(matches) > 1:
        names = ", ".join(f"{p.symbol}/{p.key}" for p in matches)
        raise InputError(f"Input {name!r} for {calc.id} could be {names}; give one exactly")
    options = ", ".join(f"{p.symbol}/{p.key}" for p in used)
    if matches and results:
        # Only what can be given is offered: the result is named, not suggested, and
        # an input the method refuses isn't suggested either.
        (p,) = matches
        said = (
            f"Input {name!r} for {calc.id} isn't one: as written it's a result, {results[0].key}."
        )
        if p in used:
            raise InputError(f"{said} Did you mean {p.symbol}/{p.key}? Give it exactly")
        raise InputError(f"{said} Inputs: {options}")
    if not matches:
        raise InputError(f"Unknown input {name!r} for {calc.id}. Inputs: {options}")
    return matches[0]


def parse_inputs(
    calc: Calculator,
    items: Sequence[str],
    method: str | None = None,
    *,
    unit_items: Sequence[str] = (),
) -> dict[str, TypedValue]:
    """Read ``NAME=VALUE`` arguments into typed values keyed by parameter key.

    A value reads with its unit in its text, ``T=3mm``, and a bare number in its input's
    default choice (ADR-0024 E5). A ``--unit NAME=ID`` reads that input as a field picked
    in ``ID`` reads it, with the field's grammar, and refuses a unit in its text.

    Args:
        calc: The calculator the inputs belong to.
        items: Arguments such as ``T=0.1046`` or ``thickness=3mm``.
        method: The method the inputs are for; ``None`` for the calculator's first.
        unit_items: ``--unit`` arguments, such as ``L=ft_in``.

    Raises:
        InputError: An argument is malformed, names an unknown input, has a bad value, or
            gives an input twice or one the method doesn't use, which would be lost; or a
            ``--unit`` names a choice its input doesn't offer, an input twice, or an input
            with no value.
    """
    chosen = calc.get_method(method)
    used = calc.params_for(chosen.key)
    picked = _picked_choices(calc, unit_items, used)
    entries: dict[str, TypedValue] = {}
    given: dict[str, str] = {}
    for item in items:
        name, sep, text = item.partition("=")
        if not sep:
            raise InputError(f"Expected NAME=VALUE, got {item!r}")
        p = _resolve_param(calc, name.strip(), used)
        if p.key in given:
            raise InputError(
                f"Input {p.symbol}/{p.key} is given twice, as {given[p.key]!r} and {item!r}; "
                "give it once"
            )
        given[p.key] = item
        entries[p.key] = _read(p, text, picked.get(p.key))
    unused = [given[key] for key in entries if key not in {p.key for p in used}]
    if unused:
        inputs = ", ".join(f"{p.symbol}/{p.key}" for p in used)
        raise InputError(
            f"Method {chosen.key!r} of {calc.id} doesn't use {', '.join(unused)}; "
            f"its inputs are {inputs}"
        )
    for key, (choice, item) in picked.items():
        if key not in entries:
            p = next(p for p in calc.params if p.key == key)
            raise InputError(
                f"--unit {item} names {p.symbol}/{p.key}, which isn't given; "
                f"give it as {p.symbol}=VALUE, read in {choice}"
            )
    return entries


def _picked_choices(
    calc: Calculator, unit_items: Sequence[str], used: Sequence[Param]
) -> dict[str, tuple[str, str]]:
    """Return each ``--unit`` input's choice and argument, by parameter key.

    Raises:
        InputError: An argument is malformed, names an input twice, or names a choice
            its input doesn't offer.
    """
    picked: dict[str, tuple[str, str]] = {}
    for item in unit_items:
        name, sep, choice = item.partition("=")
        if not sep or not name.strip():
            raise InputError(f"Expected --unit NAME=ID, got {item!r}")
        p = _resolve_param(calc, name.strip(), used)
        choice = choice.strip()
        if not choice:
            raise InputError(f"--unit {item}: give the unit or form to read {p.key} in")
        if p not in used:
            inputs = ", ".join(f"{q.symbol}/{q.key}" for q in used)
            raise InputError(
                f"--unit {item}: {p.symbol}/{p.key} isn't an input of this method; "
                f"its inputs are {inputs}"
            )
        if p.key in picked:
            raise InputError(
                f"--unit names {p.symbol}/{p.key} twice, as {picked[p.key][1]!r} and "
                f"{item!r}; give it once"
            )
        if choice not in p.choices:
            offered = ", ".join(c for c in p.choices if c) or "none: it takes a plain number"
            raise InputError(
                f"--unit {item}: {choice!r} isn't a unit for {p.symbol}/{p.key}; "
                f"its units are {offered}"
            )
        picked[p.key] = (choice, item)
    return picked


def _read(p: Param, text: str, picked: tuple[str, str] | None) -> TypedValue:
    """Read one input's text: in its ``--unit`` choice, or with its unit in its text."""
    if picked is None:
        default = choice_unit(p.default_choice or "", p.dimension)
        return TypedValue.parse(text, p.dimension, default.symbol)
    choice, item = picked
    try:
        return TypedValue.read(text, choice, p.dimension)
    except UnitInTextError as exc:
        raise InputError(
            f"Input {p.symbol}/{p.key}: {text.strip()!r} names a unit, {exc.shown}, but "
            f"--unit {item} reads it in {choice}; give the number alone, or drop the --unit"
        ) from None


def _output_units(
    calc: Calculator,
    set_key: str | None,
    output_items: Sequence[str],
    entries: Mapping[str, TypedValue],
) -> ShownUnits:
    """Return the units a run is shown in: its set, each output's pick, each input's own.

    An input given is shown in the unit or form it was read in, and any other in its
    default choice.

    Raises:
        InputError: The set isn't one of the calculator's, or an ``--output-unit`` is
            malformed, names an output twice, or one without its own picker, or a choice
            it doesn't offer.
    """
    sets = calc.unit_sets()
    if set_key is not None and set_key not in {s.key for s in sets}:
        offered = ", ".join(s.key for s in sets) or "none: every result has its own unit"
        raise InputError(
            f"--output-set {set_key!r} isn't one of {calc.id}'s; its sets are {offered}"
        )
    picks: dict[str, str] = {}
    for item in output_items:
        name, sep, choice = item.partition("=")
        if not sep or not name.strip():
            raise InputError(f"Expected --output-unit KEY=ID, got {item!r}")
        output = _resolve_output(calc, name.strip(), item)
        if not output.picks:
            raise InputError(
                f"--output-unit {item}: {output.symbol}/{output.key} has no unit of its own "
                "to pick; --output-set sets its unit"
            )
        if output.key in picks:
            raise InputError(f"--output-unit names {output.symbol}/{output.key} twice")
        if choice.strip() not in output.picks:
            raise InputError(
                f"--output-unit {item}: {choice.strip()!r} isn't a unit for "
                f"{output.symbol}/{output.key}; its units are {', '.join(output.picks)}"
            )
        picks[output.key] = choice.strip()
    inputs = {p.key: _shown_choice(p, entries.get(p.key)) for p in calc.params}
    if not sets:
        # Its notes and messages need units, but it has no set to name (JSON's null).
        return replace(ShownUnits.generated(), picks=picks, inputs=inputs, key="")
    chosen = next((s for s in sets if s.key == set_key), sets[0])
    return ShownUnits.of(chosen, picks=picks, inputs=inputs)


def _resolve_output(calc: Calculator, name: str, item: str) -> Output:
    """Return the output ``name`` names: by its exact key or symbol, else in any case.

    As ``--unit`` resolves an input (``_resolve_param``), a name in any case must match
    one output only.

    Raises:
        InputError: No output has the name, or, in any case, several do.
    """
    exact = [o for o in calc.outputs if name in (o.key, o.symbol)]
    if len(exact) == 1:
        return exact[0]
    folded = name.casefold()
    matches = [o for o in calc.outputs if folded in (o.key.casefold(), o.symbol.casefold())]
    if len(matches) == 1:
        return matches[0]
    if matches:
        names = ", ".join(f"{o.symbol}/{o.key}" for o in matches)
        raise InputError(f"--output-unit {item}: {name!r} could be {names}; give one exactly")
    own = ", ".join(f"{o.symbol}/{o.key}" for o in calc.outputs if o.picks)
    raise InputError(
        f"--output-unit {item}: {calc.id} has no output {name!r}; "
        f"the outputs with their own unit to pick are {own or 'none'}"
    )


def _shown_choice(p: Param, entry: TypedValue | None) -> str:
    """Return the choice an input is shown in: the one it was read in, else its default.

    A unit typed that isn't one of the picker's, such as a yard, is shown in the default.
    """
    if entry is None:
        return p.default_choice or ""
    form = entered_form(entry)
    if form is not None:
        return form
    if entry.choice is not None:
        return entry.choice
    if entry.unit.symbol in registry().output_choices(p.dimension):
        return entry.unit.symbol
    return p.default_choice or ""


def _cmd_run(args: argparse.Namespace) -> int:
    calc = default_registry().get(args.calculator)
    prefs = DisplayPrefs(decimals=args.decimals)
    units = ShownUnits.generated()
    try:
        entries = parse_inputs(calc, args.inputs, args.method, unit_items=args.unit)
        if len(args.output_set) > 1:
            raise InputError(
                f"--output-set is given {len(args.output_set)} times, as "
                f"{', '.join(map(repr, args.output_set))}; give it once"
            )
        output_set = args.output_set[0] if args.output_set else None
        units = _output_units(calc, output_set, args.output_unit, entries)
        inputs = {key: entry.value for key, entry in entries.items()}
        result = calc.run(inputs, method=args.method)
    except CaddCalcError as exc:
        _write_cause(exc)
        return _fail(describe_error(exc, units, prefs))
    if args.json:
        data = result_json(calc, result, units, prefs, entries)
        print(json.dumps(data, indent=2, ensure_ascii=False))
        return 0
    print(format_result(calc, result, units, prefs, show_work=not args.no_work))
    return 0


LABEL_WIDTH = 32
"""The least width of the results' label column, in characters."""


def format_result(
    calc: Calculator,
    result: Result,
    units: ShownUnits,
    prefs: DisplayPrefs,
    *,
    show_work: bool = True,
) -> str:
    """Render a result as plain text, in ``units``: inputs, work, results, notes, status."""
    method = calc.get_method(result.method)
    params = calc.params_for(result.method)
    # The label column is as wide as its longest label, and at least LABEL_WIDTH.
    labels = [p.label for p in params] + [o.label for o in calc.outputs]
    width = max(LABEL_WIDTH, *(len(label) for label in labels))
    lines = [f"{calc.name} - {method.label}", "", "Inputs"]
    for p in params:
        value = format_input(p.key, result.inputs[p.key], p.dimension, units, prefs)
        source = describe_source(result.source_of(p.key))
        lines.append(f"  {p.symbol:<6} {p.label:<{width}} {value}  ({source})")
    if show_work:
        lines += ["", "Work"]
        for step in result.steps:
            symbolic, numeric, value = render_step(step, result, units, prefs)
            lines.append(f"  {step.symbol} = {symbolic}")
            pad = " " * (len(step.symbol) + 3)
            if numeric:
                lines.append(f"  {pad[:-2]}= {numeric}")
            lines.append(f"  {pad[:-2]}= {value}")
            if step.expression is not None and step.note:
                lines.append(f"  {pad}({step.note})")
    lines += ["", "Results"]
    for o in calc.outputs:
        value = format_output(o, result.outputs[o.key], units, prefs)
        lines.append(f"  {o.symbol:<6} {o.label:<{width}} {value}")
    if result.notes:
        lines += ["", "Notes"]
        for note in result.notes:
            first, *rest = describe_note(note, units, prefs).lines
            lines += [f"  ! {first}", *(f"      {line}" for line in rest)]
    lines += ["", f"Method status: {method.status}. {_(DISCLAIMER)}"]
    return "\n".join(lines)


def _cmd_gui(_args: argparse.Namespace) -> int:
    from caddcalc.gui.app import main as gui_main

    return gui_main([])


def _ensure_unicode_output() -> None:
    """Formulas print symbols like π and √, which legacy Windows code pages cannot encode."""
    for stream in (sys.stdout, sys.stderr):
        encoding = getattr(stream, "encoding", None) or "ascii"
        try:
            "π√·°−".encode(encoding)
        except (UnicodeEncodeError, LookupError):
            reconfigure = getattr(stream, "reconfigure", None)
            if reconfigure is not None:
                reconfigure(encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
