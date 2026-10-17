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
import sys
from collections.abc import Sequence

from caddcalc import __version__
from caddcalc.calculators import default_registry
from caddcalc.core import CaddCalcError, Calculator, InputError, Param, Result
from caddcalc.core.formatting import DISCLAIMER, DisplayPrefs, format_value, render_step
from caddcalc.core.units import Dimension, parse_quantity


def main(argv: Sequence[str] | None = None) -> int:
    """Run the ``caddcalc`` command line and return the exit status."""
    _ensure_unicode_output()
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 0
    try:
        return int(args.handler(args))
    except CaddCalcError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="caddcalc", description="CADD drafting calculators.")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
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
        print(domain.name)
        for c in calcs:
            print(f"  {c.id:<40} {c.name}")
    for err in registry.plugin_errors:
        print(f"warning: plugin {err.source} failed to load: {err.message}", file=sys.stderr)
    return 0


def _cmd_show(args: argparse.Namespace) -> int:
    registry = default_registry()
    calc = registry.get(args.calculator)
    print(f"{calc.name}  [{calc.id}]")
    print(f"  {calc.summary}")
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
        for note in m.notes:
            print(f"         Note: {note}")
        for ref in m.references:
            print(f"         Ref: {ref}")
    return 0


def _resolve_param(calc: Calculator, name: str) -> Param:
    matches = [p for p in calc.params if name.lower() in (p.key.lower(), p.symbol.lower())]
    if len(matches) != 1:
        options = ", ".join(f"{p.symbol}/{p.key}" for p in calc.params)
        raise InputError(f"Unknown input {name!r} for {calc.id}. Inputs: {options}")
    return matches[0]


def parse_inputs(calc: Calculator, items: Sequence[str], length_unit: str) -> dict[str, float]:
    """Parse ``NAME=VALUE`` arguments into base-unit values keyed by parameter key.

    Args:
        calc: The calculator the inputs belong to.
        items: Arguments such as ``T=0.1046`` or ``thickness=3mm``.
        length_unit: The unit for lengths typed without one.

    Raises:
        InputError: An argument is malformed, names an unknown input, or has a bad value.
    """
    values: dict[str, float] = {}
    for item in items:
        name, sep, text = item.partition("=")
        if not sep:
            raise InputError(f"Expected NAME=VALUE, got {item!r}")
        p = _resolve_param(calc, name.strip())
        default_unit = length_unit if p.dimension is Dimension.LENGTH else None
        values[p.key] = parse_quantity(text, p.dimension, default_unit)
    return values


def _cmd_run(args: argparse.Namespace) -> int:
    calc = default_registry().get(args.calculator)
    result = calc.run(parse_inputs(calc, args.inputs, args.units), method=args.method)
    if args.json:
        print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
        return 0
    prefs = DisplayPrefs(
        length_unit=args.units, decimals=args.decimals, fraction_denominator=args.fraction
    )
    print(format_result(calc, result, prefs, show_work=not args.no_work))
    return 0


def format_result(
    calc: Calculator, result: Result, prefs: DisplayPrefs, *, show_work: bool = True
) -> str:
    """Render a result as plain text: inputs, work, results, warnings, and status."""
    method = calc.get_method(result.method)
    lines = [f"{calc.name} - {method.label}", "", "Inputs"]
    for p in calc.params_for(result.method):
        value = format_value(result.inputs[p.key], p.dimension, prefs)
        lines.append(f"  {p.symbol:<6} {p.label:<32} {value}")
    if show_work:
        lines += ["", "Work"]
        for step in result.steps:
            symbolic, numeric, value = render_step(step, result, prefs)
            lines.append(f"  {step.symbol} = {symbolic}")
            pad = " " * (len(step.symbol) + 3)
            if numeric:
                lines.append(f"  {pad[:-2]}= {numeric}")
            lines.append(f"  {pad[:-2]}= {value}")
    lines += ["", "Results"]
    for o in calc.outputs:
        value = format_value(result.outputs[o.key], o.dimension, prefs)
        lines.append(f"  {o.symbol:<6} {o.label:<32} {value}")
    if result.warnings:
        lines += ["", "Warnings"]
        lines += [f"  ! {w}" for w in result.warnings]
    lines += ["", f"Method status: {method.status}. {DISCLAIMER}"]
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
