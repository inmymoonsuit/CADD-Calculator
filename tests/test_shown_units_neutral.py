"""The output sets show what the length preference showed (ADR-0024 E-3).

``data/e3_neutrality.json`` holds every built-in calculator's text, run on its defaults,
with each input out of range, and with each input scaled, in inches and millimetres, as
the app wrote it with the length preference before E-3: each output shown, said and
copied, the tab-separated rows, the work, the notes, the method's notes, the inputs, the
CLI's report and each error. The generated ``in`` and ``mm`` sets must write it all
again, character for character. A scaled run is held by the SHA-256 of its text as
canonical JSON, to keep the file small.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from caddcalc.calculators import default_registry
from caddcalc.cli import format_result
from caddcalc.core import Calculator, InputError
from caddcalc.core.formatting import (
    CopyForm,
    DisplayPrefs,
    NumberSymbols,
    ShownUnits,
    copy_output,
    describe_error,
    describe_note,
    format_output,
    method_notes,
    output_parts,
    render_step,
    results_tsv,
    spoken_value,
    value_parts,
)

GOLDEN = Path(__file__).parent / "data" / "e3_neutrality.json"


def _runs(calc: Calculator, method: str) -> Iterator[tuple[str, dict[str, float]]]:
    yield "defaults", {}
    for p in calc.params_for(method):  # each input out of range, for its error message
        yield f"low {p.key}", {p.key: -1e9}
    defaults = calc.run({}, method).inputs
    for p in calc.params_for(method):  # each input scaled, for the notes it raises
        for scale in (0.01, 0.1, 10.0, 100.0):
            yield f"x{scale} {p.key}", {p.key: defaults[p.key] * scale}


def _texts() -> dict[str, Any]:
    """Write what the golden holds, with the generated sets."""
    texts: dict[str, Any] = {}
    for calc in default_registry(load_plugins=False):
        for m in calc.methods:
            for length, mark in (("in", "."), ("in", ","), ("mm", ".")):
                units = ShownUnits.generated(length)
                prefs = DisplayPrefs(symbols=NumberSymbols(mark))
                for name, inputs in _runs(calc, m.key):
                    key = f"{calc.id}|{m.key}|{length}|{mark}|{name}"
                    try:
                        r = calc.run(inputs, m.key)
                    except InputError as exc:
                        texts[key] = {"error": describe_error(exc, units, prefs)}
                        continue
                    outputs = {}
                    for o in calc.outputs:
                        v = r.outputs[o.key]
                        copies = {
                            form.value: copy_output(o, v, units, prefs, form) for form in CopyForm
                        }
                        outputs[o.key] = {
                            "shown": format_output(o, v, units, prefs),
                            "spoken": spoken_value(output_parts(o, v, units, prefs)),
                            "copies": copies,
                        }
                    entry: dict[str, Any] = {
                        "outputs": outputs,
                        "tsv": results_tsv(calc, r, units, prefs),
                        "steps": [list(render_step(s, r, units, prefs)) for s in r.steps],
                        "notes": [list(describe_note(n, units, prefs).lines) for n in r.notes],
                        "method_notes": list(method_notes(m, units, prefs)),
                        "inputs": {
                            p.key: value_parts(r.inputs[p.key], p.dimension, units, prefs).with_unit
                            for p in calc.params_for(m.key)
                        },
                    }
                    if mark == ".":
                        entry["cli"] = format_result(calc, r, units, prefs)
                    texts[key] = entry
    return texts


def _held(entry: dict[str, Any]) -> dict[str, Any]:
    """Return a scaled run's entry as the golden holds it: its text's digest."""
    canon = json.dumps(entry, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return {"sha256": hashlib.sha256(canon.encode()).hexdigest()}


@pytest.fixture(scope="module")
def texts() -> dict[str, Any]:
    return _texts()


def test_the_golden_covers_every_built_in_calculator(texts: dict[str, Any]) -> None:
    golden = json.loads(GOLDEN.read_text(encoding="utf-8"))
    assert set(texts) == set(golden)
    assert {key.split("|")[0] for key in golden} == {
        calc.id for calc in default_registry(load_plugins=False)
    }
    assert any("error" in entry for entry in golden.values())
    assert sum(bool(entry.get("notes")) for entry in texts.values()) >= 50, "notes are covered"


def test_the_generated_sets_write_what_the_length_preference_wrote(
    texts: dict[str, Any],
) -> None:
    golden = json.loads(GOLDEN.read_text(encoding="utf-8"))

    def held(key: str) -> Any:
        entry = texts.get(key)
        return _held(entry) if entry is not None and "sha256" in golden[key] else entry

    differ = sorted(key for key in golden if held(key) != golden[key])
    assert differ == [], f"{len(differ)} of {len(golden)} differ, first {differ[:3]}"
