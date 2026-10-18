"""The app's design tokens beyond the welcome screen (ADR-0017 §7), and the note outlines."""

from __future__ import annotations

import tomllib
from dataclasses import fields
from pathlib import Path
from typing import Any

import pytest

from caddcalc.core import Note, NoteKind, Reference
from caddcalc.core.units import UNITS
from caddcalc.gui.outlines import error_outline, note_outline, strongest
from caddcalc.gui.style_tokens import StyleError
from caddcalc.gui.ui_style import STYLE_FILE, UiStyle, parse_ui_style, ui_style

ROOT = Path(__file__).parents[1]
SPEC = ROOT / "docs" / "dev" / "design" / "result-fields.md"


def shipped() -> dict[str, Any]:
    data: dict[str, Any] = tomllib.loads(STYLE_FILE.read_text(encoding="utf-8"))
    return data


def edited(table: str, key: str, value: Any) -> dict[str, Any]:
    data = shipped()
    data[table] = {**data[table], key: value}
    return data


def test_the_shipped_tokens_load() -> None:
    tokens = ui_style()
    assert tokens.result_field.border_role == "field_border"
    assert tokens.result_field.focus_role == "focus_ring"
    assert tokens.note_outline.width == 2, "inputs and results share it (ADR-0017 §3)"


def test_every_token_table_has_its_typed_class() -> None:
    assert {f.name for f in fields(UiStyle)} == set(shipped()) - {"schema"}


@pytest.mark.parametrize(
    ("data", "message"),
    [
        (edited("result_field", "shadow", 2), r"\[result_field\] has unknown \['shadow'\]"),
        ({**shipped(), "schema": 2}, "schema must be 1"),
        (edited("result_field", "gap", 10), r"result_field\.gap must be on the spacing scale"),
        (edited("result_field", "padding", [6, 5]), "on the spacing scale.*not 5"),
        (edited("result_field", "border_role", "ink"), "'ink' isn't a palette role"),
        (edited("result_field", "tabular_figures", 1), "tabular_figures must be true or false"),
        (edited("result_field", "copy_icon", "clipboard"), "'clipboard' isn't a vendored icon"),
        (edited("result_field", "min_height", 20), "min_height 20 is less than its button_size"),
        (edited("result_field", "icon_size", 32), "icon_size 32 is larger than its button_size"),
        (edited("note_outline", "width", 1), "note_outline.width 1 must be heavier"),
        (edited("note_outline", "limit_style", "dotted"), "must be one of dashed, solid"),
    ],
)
def test_the_loader_refuses_a_bad_token(data: dict[str, Any], message: str) -> None:
    with pytest.raises(StyleError, match=message):
        parse_ui_style(data)


def _quote(value: Any) -> str:
    """How the doc writes a token's value: a pair as ``a × b``, a flag as true or false."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, list):
        return f"{value[0]} × {value[1]}"
    return str(value)


def test_the_doc_quotes_every_token() -> None:
    """docs/dev/design/result-fields.md is written by hand; this keeps it in step."""
    doc = SPEC.read_text(encoding="utf-8")
    missing = [
        f"| `{table}.{key}` | {_quote(value)} |"
        for table, tokens in shipped().items()
        if isinstance(tokens, dict)
        for key, value in tokens.items()
        if f"| `{table}.{key}` | {_quote(value)} |" not in doc
    ]
    assert missing == [], missing


def _note(kind: NoteKind, *subjects: str) -> Note:
    cited = (Reference("Shop handbook", "Table 4"),) if kind is NoteKind.LIMIT_EXCEEDED else ()
    return Note(kind, "A note.", cited, subjects)


def test_a_field_takes_the_strongest_of_its_notes_outlines() -> None:
    """A cited limit over a warning over a check that couldn't be made."""
    notes = [
        _note(NoteKind.NO_APPLICABLE_VALUE, "thickness", "inside_radius"),
        _note(NoteKind.WARNING, "thickness", "flat_length"),
        _note(NoteKind.LIMIT_EXCEEDED, "inside_radius"),
        _note(NoteKind.INFEASIBLE, "elsewhere"),
    ]
    outlines = strongest(notes, {"thickness", "inside_radius", "flat_length"})
    assert {key: (o.role, o.style) for key, o in outlines.items()} == {
        "thickness": ("outline_note", "solid"),
        "inside_radius": ("outline_limit", "solid"),
        "flat_length": ("outline_note", "solid"),
    }
    assert "elsewhere" not in outlines, "only the fields that can show it"


def test_every_outline_is_heavier_than_a_fields_border() -> None:
    border = ui_style().result_field.border_width
    for kind in NoteKind:
        assert note_outline(kind).width > border
    unchecked = note_outline(NoteKind.NO_APPLICABLE_VALUE)
    assert (unchecked.role, unchecked.style) == ("outline_no_value", "dashed")
    assert error_outline().role == "outline_error"


def test_every_unit_is_spoken_in_the_singular_and_the_plural() -> None:
    """ADR-0017 §5: "0.3119 inches" for a screen reader; a ratio speaks only its number."""
    for unit in UNITS:
        if unit.symbol:
            assert unit.spoken_plural and unit.spoken(1) == unit.name, unit.symbol
            assert unit.spoken(2) == unit.spoken(0.5) == unit.spoken_plural
        else:
            assert unit.spoken(2) == unit.spoken(1) == ""
    inch = next(u for u in UNITS if u.symbol == "in")
    assert (inch.spoken(1), inch.spoken(0.3119)) == ("inch", "inches")
