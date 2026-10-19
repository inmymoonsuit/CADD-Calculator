"""Capture the CLI corpus's base values with an old commit's CLI (ADR-0024 E-4).

The corpus is sheet-metal invocations in the CLI's syntax before E-4, with ``--units``.
This runs each one, with ``--json``, in a checkout of the old commit and records its exit
status and, for a run, every input, output and step value in base units. The test
(``tests/test_cli_corpus.py``) rewrites each call into E-4's syntax, keeping its
meaning, and wants the same values.

Run it with the old commit's own interpreter and package::

    git worktree add /tmp/old c7b1772
    uv run --project /tmp/old python tests/tooling/capture_cli_corpus.py out.json

It's run once, by hand: the old CLI's API isn't this checkout's.
"""

from __future__ import annotations

import contextlib
import io
import json
import random
import sys
from pathlib import Path

LENGTHS = (
    "0.25", "0.1046", "3/16", "1-1/2", "2", "0.0747", "10", "1/32",
    "3mm", "6.35 mm", "0.25in", "1/4\"", "2'", "1'-4 3/16\"", "0.5 cm", "0.01 m", "4mm",
)  # fmt: skip
ANGLES = ("90", "45", "120", "30", "90°", "90 deg", "1.5708 rad", "40°30'", "135", "0")
RATIOS = ("0.44", "44%", "0.33", "0.5", "0.4")
CALCULATORS = {
    "sheet_metal.bend_allowance": (
        ("course", "k_factor"),
        {"T": "length", "R": "length", "A": "angle", "K": "ratio"},
    ),
    "sheet_metal.segment_flat_length": (
        ("course", "k_factor"),
        {"T": "length", "R": "length", "FVD": "length", "A1": "angle", "A2": "angle", "K": "ratio"},
    ),
    "sheet_metal.truncated_cone_layout": (
        ("course", "mean_diameter"),
        {"Dt": "length", "Db": "length", "H": "length", "T": "length"},
    ),
    "sheet_metal.v_die_opening": (
        ("radius_ratio", "eight_t"),
        {"R": "length", "P": "ratio", "T": "length"},
    ),
}
TEXTS = {"length": LENGTHS, "angle": ANGLES, "ratio": RATIOS}


def corpus(seed: int = 24, per_method: int = 56) -> list[list[str]]:
    """Return the invocations, the same for a seed: each a list of arguments."""
    rng = random.Random(seed)
    calls = []
    for calc_id, (methods, symbols) in CALCULATORS.items():
        for method in methods:
            for i in range(per_method):
                argv = ["run", calc_id, "--method", method]
                names = [s for s in symbols if rng.random() < 0.7]
                argv += [f"{s}={rng.choice(TEXTS[symbols[s]])}" for s in names]
                units = rng.choice((None, "in", "mm", "mm"))
                if units is not None:
                    argv += ["--units", units]
                if i % 4 == 0:
                    argv.append("--json")
                calls.append(argv)
    return calls


def values(data: dict) -> dict:
    """Return a run's base values, from the old JSON's shape."""
    return {
        "inputs": {k: v["value"] for k, v in data["inputs"].items()},
        "outputs": {k: v["value"] for k, v in data["outputs"].items()},
        "steps": [s["value"] for s in data["steps"]],
    }


def main(out: str) -> None:
    from caddcalc.cli import main as cli

    rows = []
    for argv in corpus():
        args = argv if "--json" in argv else [*argv, "--json"]
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            status = cli(args)
        row: dict = {"argv": argv, "exit": status}
        if status == 0:
            row["base"] = values(json.loads(stdout.getvalue()))
        rows.append(row)
    Path(out).write_text(json.dumps(rows, indent=0, ensure_ascii=False) + "\n", encoding="utf-8")
    print(len(rows), sum(r["exit"] == 0 for r in rows), sum("--json" in r["argv"] for r in rows))


if __name__ == "__main__":
    main(sys.argv[1])
