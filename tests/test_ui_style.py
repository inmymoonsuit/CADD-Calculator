"""The app's design tokens beyond the welcome screen (ADR-0017 §7), and the note outlines."""

from __future__ import annotations

import re
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
        (edited("layout", "list_min_chars", 52), "list_min_chars 52 is more than .*list_width"),
        (edited("layout", "panel_max_chars", 149), "panel_max_chars 149 is more than .*page_max"),
        (
            edited("layout", "right_pane_min_chars", 65),
            "right_pane_min_chars 65 is more than .*right_pane_default",
        ),
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


def test_the_doc_quotes_no_token_that_isnt_there() -> None:
    """The other way: a doc row for a removed or renamed token fails."""
    doc = SPEC.read_text(encoding="utf-8")
    quoted = re.findall(r"^\| `(\w+)\.(\w+)` \|", doc, flags=re.MULTILINE)
    tables = shipped()
    stale = [
        f"{t}.{k}" for t, k in quoted if not isinstance(tables.get(t), dict) or k not in tables[t]
    ]
    assert quoted and stale == [], stale


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


def test_notes_are_listed_strongest_first_in_the_calculators_order_within_a_rank() -> None:
    """A short document opens with the note that matters most (ADR-0017)."""
    from caddcalc.gui.outlines import strongest_first

    gap = _note(NoteKind.NO_APPLICABLE_VALUE, "a")
    warning, impossible = _note(NoteKind.WARNING, "b"), _note(NoteKind.INFEASIBLE, "c")
    limit = _note(NoteKind.LIMIT_EXCEEDED, "d")
    later_warning = _note(NoteKind.WARNING, "e")
    ordered = strongest_first([gap, warning, impossible, limit, later_warning])
    assert ordered == [limit, warning, impossible, later_warning, gap]
    assert [note_outline(n.kind).rank for n in ordered] == sorted(
        (note_outline(n.kind).rank for n in ordered), reverse=True
    ), "the same ranking as the outlines"


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
            assert unit.spoken_plural and unit.spoken("1") == unit.name, unit.symbol
            assert unit.spoken("-1") == unit.name, "the sign isn't counted"
            plurals = {unit.spoken(shown) for shown in ("2", "0.5", "1.0000", "0", "-2")}
            assert plurals == {unit.spoken_plural}, "a shown decimal takes the plural"
        else:
            assert unit.spoken("2") == unit.spoken("1") == ""
    inch = next(u for u in UNITS if u.symbol == "in")
    assert (inch.spoken("1"), inch.spoken("0.3119"), inch.spoken("1.0000")) == (
        "inch",
        "inches",
        "inches",
    )
