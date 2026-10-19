"""S&R's CLI corpus as a correctness baseline for E-4's syntax (ADR-0024 E8, E-4).

``data/cli_corpus.json`` holds 448 sheet-metal invocations in the syntax before E-4,
each with its exit status and, for a run, every base value, captured with c7b1772's CLI
(``tooling/capture_cli_corpus.py``). Each call is rewritten keeping its meaning, as S&R's
M1 says: ``--units in`` becomes ``--output-set in``, and ``--units mm`` becomes
``--output-set mm`` with "mm" on each bare length, since it also read bare lengths in
mm. Every rewritten call must exit as it did, and read every input bit for bit.

The outputs and steps go through the platform's maths library, whose sine and tangent
can differ in their last bits: macOS's do from Linux's, where the corpus was captured.
A step that subtracts can then differ by more of its own last places than of its terms'
(the segment's flat length, 18.9 mm from terms of 324 mm, was 8 of its own, half of
theirs). So each output and step is held to ``ULPS`` units in the last place of the
largest value in its run, and the inputs, which only the reading decides, bit for bit.
"""

from __future__ import annotations

import contextlib
import io
import json
import math
from pathlib import Path
from typing import Any

import pytest

from caddcalc.calculators import default_registry
from caddcalc.cli import main
from caddcalc.core import Dimension, InputError, TypedValue

ULPS = 4
"""Units in the last place of a run's largest value its outputs and steps may differ by:
every difference macOS's maths library made, in CI's logs, is at most 2."""

CORPUS = json.loads((Path(__file__).parent / "data" / "cli_corpus.json").read_text("utf-8"))


def rewrite(argv: list[str]) -> list[str]:
    """Return an old call in E-4's syntax, keeping its meaning."""
    calc = default_registry(load_plugins=False).get(argv[1])
    dimensions = {p.symbol: p.dimension for p in calc.params}
    metric = False
    out: list[str] = []
    rest = iter(argv)
    for arg in rest:
        if arg == "--units":
            unit = next(rest)
            metric = unit == "mm"
            out += ["--output-set", unit]
        else:
            out.append(arg)
    if not metric:
        return out
    return [_in_mm(arg, dimensions) for arg in out]


def _in_mm(arg: str, dimensions: dict[str, Dimension]) -> str:
    """Return ``NAME=VALUE`` with "mm" on its value if it's a bare length."""
    name, sep, text = arg.partition("=")
    if not sep or dimensions.get(name) is not Dimension.LENGTH:
        return arg
    try:
        named = TypedValue.parse(text, Dimension.LENGTH, "in").explicit_unit
    except InputError:
        return arg  # refused either way
    return arg if named else f"{arg} mm"


def _run(argv: list[str]) -> tuple[int, dict[str, Any] | None]:
    stdout = io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(io.StringIO()):
        status = main([*argv, "--json"])
    if status:
        return status, None
    data = json.loads(stdout.getvalue())
    return status, {
        "inputs": {k: v["base"]["value"] for k, v in data["inputs"].items()},
        "outputs": {k: v["base"]["value"] for k, v in data["outputs"].items()},
        "steps": [s["base"]["value"] for s in data["steps"]],
    }


def _scale(base: dict[str, Any]) -> float:
    """The largest magnitude among a run's values, which its last places are counted in."""
    values = [*base["inputs"].values(), *base["outputs"].values(), *base["steps"]]
    return max((abs(v) for v in values), default=0.0)


def _within(got: float, want: float, scale: float) -> bool:
    """Whether two values agree to ``ULPS`` units in the last place of ``scale``."""
    return got == want or abs(got - want) <= ULPS * math.ulp(scale)


def test_the_bound_is_a_few_last_places_of_the_run() -> None:
    """Pinned: 4 of the scale's last places pass, 8 fail, and so does any input."""
    scale = 323.7609432604796
    assert _within(18.918888629956797, 18.918888629956825, scale), "macOS's, half a place"
    assert _within(1.0, 1.0 + ULPS * math.ulp(scale), scale)
    assert not _within(1.0, 1.0 + 2 * ULPS * math.ulp(scale), scale)
    assert not _within(18.9188886299568, 18.9188886299578, scale), "a change in the 14th digit"


def test_the_corpus_is_s_and_r_s_size() -> None:
    assert len(CORPUS) == 448
    assert sum("--json" in row["argv"] for row in CORPUS) == 112
    assert sum("mm" in row["argv"] for row in CORPUS) > 100, "--units mm, rewritten"
    assert sum(row["exit"] == 0 for row in CORPUS) > 200


@pytest.mark.parametrize("row", CORPUS, ids=lambda row: " ".join(row["argv"][1:]))
def test_every_call_rewritten_gives_c7b1772_s_base_values(row: dict[str, Any]) -> None:
    status, base = _run(rewrite(row["argv"]))
    assert status == row["exit"]
    if base is not None:
        want = row["base"]
        assert base["inputs"] == want["inputs"], "read bit for bit"
        scale = _scale(want)
        assert base["outputs"].keys() == want["outputs"].keys()
        far = {
            k: (v, want["outputs"][k])
            for k, v in base["outputs"].items()
            if not _within(v, want["outputs"][k], scale)
        }
        assert len(base["steps"]) == len(want["steps"])
        far |= {
            f"step {i}": (v, w)
            for i, (v, w) in enumerate(zip(base["steps"], want["steps"], strict=True))
            if not _within(v, w, scale)
        }
        assert far == {}, f"more than {ULPS} last places of {scale}"


def test_the_rewrite_reads_a_bare_length_in_mm_and_leaves_a_named_one() -> None:
    old = ["run", "sheet_metal.bend_allowance", "T=3/16", "R=4mm", "A=90", "--units", "mm"]
    assert rewrite(old) == [
        "run",
        "sheet_metal.bend_allowance",
        "T=3/16 mm",
        "R=4mm",
        "A=90",
        "--output-set",
        "mm",
    ]
