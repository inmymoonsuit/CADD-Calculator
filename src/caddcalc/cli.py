"""Command-line front end.

caddcalc list
caddcalc show sheet_metal.bend_allowance
caddcalc run sheet_metal.bend_allowance T=0.1046 R=0.156 A=90 --method course
caddcalc run sheet_metal.bend_allowance T=3mm R=4mm A=120 --units mm --json
caddcalc gui
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import traceback
from collections.abc import Mapping, Sequence

from caddcalc import __version__
from caddcalc.calculators import default_registry
from caddcalc.core import CaddCalcError, Calculator, InputError, Param, Result, i18n
from caddcalc.core.formatting import (
    DISCLAIMER,
    DisplayPrefs,
    ShownUnits,
    describe_error,
    describe_note,
    describe_source,
    format_input,
    format_output,
    method_notes,
    render_step,
)
from caddcalc.core.i18n import _
from caddcalc.core.units import parse_quantity

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
    args = parser.parse_args(argv)
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
        help="input by key or symbol, e.g. T=0.1046 or thickness=3mm",
    )
    p_run.add_argument("--method", help="method key (default: the calculator's first method)")
    p_run.add_argument(
        "--units",
        default="in",
        choices=["in", "mm"],
        help="units for unitless inputs and for display (default: in)",
    )
    p_run.add_argument("--decimals", type=int, default=4)
    p_run.add_argument(
        "--fraction",
        type=int,
        metavar="DENOM",
        help="also show inch results as the nearest 1/DENOM fraction",
    )
    p_run.add_argument("--json", action="store_true", help="machine-readable output (base units)")
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
        if p.help:
            print(f"         {p.help}")
    print("\nOutputs")
    for o in calc.outputs:
        print(f"  {o.symbol:<6} {o.key:<20} {o.label}")
    print("\nMethods")
    for m in calc.methods:
        print(f"  {m.key:<14} {m.label}  [{m.status}]")
        print(f"         {m.summary}")
        for note in method_notes(m, ShownUnits.generated(), DisplayPrefs()):
            print(f"         Note: {note}")
        for ref in m.references:
            print(f"         Ref: {ref}")
    return 0


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
    calc: Calculator, items: Sequence[str], length_unit: str, method: str | None = None
) -> dict[str, float]:
    """Parse ``NAME=VALUE`` arguments into base-unit values keyed by parameter key.

    Args:
        calc: The calculator the inputs belong to.
        items: Arguments such as ``T=0.1046`` or ``thickness=3mm``.
        length_unit: The output set whose units values typed without one are read in.
        method: The method the inputs are for; ``None`` for the calculator's first.

    Raises:
        InputError: An argument is malformed, names an unknown input, has a bad value, or
            gives an input twice or one the method doesn't use, which would be lost.
    """
    chosen = calc.get_method(method)
    used = calc.params_for(chosen.key)
    units = ShownUnits.generated(length_unit)
    values: dict[str, float] = {}
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
        values[p.key] = parse_quantity(text, p.dimension, units.unit(p.dimension).symbol)
    unused = [given[key] for key in values if key not in {p.key for p in used}]
    if unused:
        inputs = ", ".join(f"{p.symbol}/{p.key}" for p in used)
        raise InputError(
            f"Method {chosen.key!r} of {calc.id} doesn't use {', '.join(unused)}; "
            f"its inputs are {inputs}"
        )
    return values


def _cmd_run(args: argparse.Namespace) -> int:
    calc = default_registry().get(args.calculator)
    units = ShownUnits.generated(args.units)
    prefs = DisplayPrefs(decimals=args.decimals, fraction_denominator=args.fraction)
    try:
        inputs = parse_inputs(calc, args.inputs, args.units, args.method)
        result = calc.run(inputs, method=args.method)
    except CaddCalcError as exc:
        _write_cause(exc)
        return _fail(describe_error(exc, units, prefs))
    if args.json:
        print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
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
