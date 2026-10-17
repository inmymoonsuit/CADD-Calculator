"""Main window: calculators and their families on the left; their pages on the right."""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from enum import Enum
from functools import partial
from html import escape
from typing import Any, cast, override

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QGuiApplication, QTextDocument
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QStackedWidget,
    QTextBrowser,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from caddcalc import __version__
from caddcalc.calculators import default_registry
from caddcalc.core import (
    CaddCalcError,
    Calculator,
    Domain,
    DomainSettings,
    DomainValues,
    InputError,
    InputSource,
    Method,
    NoteKind,
    OutOfRangeError,
    Param,
    Registry,
    Result,
    SourceKind,
    TypedValue,
)
from caddcalc.core.formatting import (
    DISCLAIMER,
    DisplayPrefs,
    describe_error,
    describe_note,
    describe_override,
    describe_setting_uses,
    describe_source,
    display_unit,
    entry_text,
    field_text,
    format_value,
    render_step,
    unit_suffix,
)
from caddcalc.core.units import Dimension, parse_quantity_detailed
from caddcalc.gui.branding import GENERIC, Branding
from caddcalc.gui.icons import (
    TABLER_DIR,
    Scheme,
    clear_cache,
    current_scheme,
    icon,
    render,
    role_color,
)

ID_ROLE = Qt.ItemDataRole.UserRole
"""Tree item data holding a calculator row's calculator id."""
DOMAIN_ROLE = int(Qt.ItemDataRole.UserRole) + 1
"""Tree item data holding a family row's domain id."""
NO_CALCULATORS = "No calculators loaded"
"""Shown under a family with no calculator, e.g. when all its plugin calculators failed."""
ICON_URL_SCHEME = "icon"
ICON_PX = 32
"""Pixel size icons are rendered at for the results pane; shown at 16 px, so sharp on HiDPI."""


COURSE_EXAMPLE = "course example"
"""How results name a value set by Load course example."""


class EntryOrigin(Enum):
    """How a calculator field's own value got there; results name all but typed ones."""

    TYPED = "typed"
    COURSE_EXAMPLE = "course example"
    FAMILY_COPY = "family copy"
    """Copied from the family value when the user unticked "Use … value"."""


@dataclass(frozen=True)
class FieldEntry:
    """A calculator field's own value: text the user typed, or a base value set for them."""

    value: TypedValue | float
    origin: EntryOrigin = EntryOrigin.TYPED

    @property
    def base_value(self) -> float:
        """The value, in base units."""
        return self.value.value if isinstance(self.value, TypedValue) else self.value


@dataclass(frozen=True)
class _EditStart:
    """How a calculator field stood when the user began editing it."""

    entry: FieldEntry | None
    overridden: bool
    shown: str
    in_use: float | None


class ResultsBrowser(QTextBrowser):
    """A results pane that can show the vendored icons inline.

    It serves ``icon:<scheme>/<role>/<name>`` image URLs (written by ``_img``) by rendering
    the Tabler icon in the palette color for that role and scheme.
    """

    @override
    def loadResource(self, type: int, name: QUrl | str) -> Any:
        url = QUrl(name) if isinstance(name, str) else name
        kind = getattr(type, "value", type)
        if kind == QTextDocument.ResourceType.ImageResource.value and (
            url.scheme() == ICON_URL_SCHEME
        ):
            parts = url.path().split("/")
            if len(parts) == 3 and parts[0] in ("light", "dark"):
                scheme, role, icon_name = parts
                if (TABLER_DIR / f"{icon_name}.svg").is_file():
                    return render(icon_name, role_color(role, cast(Scheme, scheme)), ICON_PX)
        return super().loadResource(type, name)


class MainWindow(QMainWindow):
    """The main window: calculators and their families on the left; a page on the right.

    A calculator's page has its inputs, results, and work. A family's page has its shared
    settings (ADR-0013 §8).
    """

    def __init__(self, registry: Registry | None = None, branding: Branding = GENERIC) -> None:
        super().__init__()
        self.registry = registry or default_registry()
        self.branding = branding
        self.prefs = DisplayPrefs()
        self.calculator: Calculator | None = None
        """The calculator whose page is shown, if one is."""
        self.domain: Domain | None = None
        """The domain whose settings page is shown, if one is."""
        self.entries: dict[str, dict[str, FieldEntry]] = {}
        """Each calculator's own values, by calculator id and parameter key.

        An absent key means the calculator's default.
        """
        self.overrides: dict[str, set[str]] = {}
        """The shared parameters each calculator overrides; sticky for the session (C)."""
        self.fields: dict[str, tuple[Param, QLineEdit]] = {}
        self.pending_fields: dict[tuple[str, str], str] = {}
        """Text typed in a calculator field that can't be read, by (calculator id, key).

        It outlives the page, so the text and its explanation are still there when the
        user comes back.
        """
        self.edit_starts: dict[tuple[str, str], _EditStart] = {}
        """How each field being edited stood when its edit began, by (calculator id, key)."""
        self.field_notices: dict[tuple[str, str], str] = {}
        """One-time notes for calculator fields, shown until the user leaves the page."""
        self.result: Result | None = None
        """The shown calculator's last result, or ``None`` while its inputs have errors."""
        self.inherit_boxes: dict[str, QCheckBox] = {}
        self.override_notes: dict[str, QLabel] = {}
        self.domain_settings = DomainSettings()
        """The domain settings the user has set; kept for the life of the window (§7)."""
        self.setting_fields: dict[str, tuple[Param, QLineEdit]] = {}
        self.pending_settings: dict[tuple[str, str], str] = {}
        """Text typed in a settings field but not applied, by (domain id, setting key).

        It outlives the page, so refused text and its explanation are still there when the
        user comes back.
        """

        self.setWindowTitle(branding.name)
        self.resize(1100, 720)
        self._build_ui()
        self._build_menu()
        self._apply_icons()
        self.statusBar().showMessage(DISCLAIMER)
        QGuiApplication.styleHints().colorSchemeChanged.connect(self._on_color_scheme_changed)

        first = next(self._calculator_items(), None)
        if first is not None:
            self.tree.setCurrentItem(first)

    # --- layout ---------------------------------------------------------------------------

    def _build_ui(self) -> None:
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        grouped = self.registry.by_domain()
        for domain in self.registry.domains():
            parent = QTreeWidgetItem([domain.name])
            parent.setData(0, DOMAIN_ROLE, domain.id)
            parent.setToolTip(0, domain.summary)
            for calc in grouped.get(domain, []):
                child = QTreeWidgetItem([calc.name])
                child.setData(0, ID_ROLE, calc.id)
                child.setToolTip(0, calc.summary)
                parent.addChild(child)
            if not parent.childCount():
                placeholder = QTreeWidgetItem([NO_CALCULATORS])
                placeholder.setFlags(Qt.ItemFlag.NoItemFlags)
                parent.addChild(placeholder)
            self.tree.addTopLevelItem(parent)
        self.tree.expandAll()
        self.tree.currentItemChanged.connect(self._on_tree_changed)

        self.title = QLabel()
        self.title.setStyleSheet("font-size: 16pt; font-weight: 600;")
        self.summary = QLabel()
        self.summary.setWordWrap(True)

        self.method_box = QComboBox()
        self.method_box.currentIndexChanged.connect(self._on_method_changed)
        self.method_row = QWidget()
        method_layout = QHBoxLayout(self.method_row)
        method_layout.setContentsMargins(0, 0, 0, 0)
        method_layout.addWidget(QLabel("Method:"))
        method_layout.addWidget(self.method_box, 1)
        self.units_box = QComboBox()
        self.units_box.addItems(["in", "mm"])
        self.units_box.currentTextChanged.connect(self._on_units_changed)
        options = QHBoxLayout()
        options.addWidget(self.method_row, 1)
        options.addStretch(0)  # holds the units box right while a settings page hides the method
        options.addSpacing(16)
        options.addWidget(QLabel("Units:"))
        options.addWidget(self.units_box)

        self.form_box = QGroupBox("Inputs")
        self.form = QFormLayout(self.form_box)
        self.example_button = QPushButton("Load course example")
        self.example_button.setToolTip(
            "Fill every input with the course example, overriding the family settings."
        )
        self.example_button.clicked.connect(self.load_course_example)
        example_row = QHBoxLayout()
        example_row.addWidget(self.example_button)
        example_row.addStretch(1)
        self.output = ResultsBrowser()
        self.output.setOpenExternalLinks(True)
        self.calculator_page = QWidget()
        calc_col = QVBoxLayout(self.calculator_page)
        calc_col.setContentsMargins(0, 0, 0, 0)
        calc_col.addLayout(example_row)
        calc_col.addWidget(self.form_box)
        calc_col.addWidget(self.output, 1)

        self.settings_box = QGroupBox("Family settings")
        self.settings_form = QFormLayout(self.settings_box)
        self.clear_settings_button = QPushButton("Clear all")
        self.clear_settings_button.setToolTip("Unset every setting of this family.")
        self.clear_settings_button.clicked.connect(self._clear_domain_settings)
        self.domain_note = QLabel()
        self.domain_note.setWordWrap(True)
        self.domain_note.setTextFormat(Qt.TextFormat.RichText)
        buttons = QHBoxLayout()
        buttons.addWidget(self.clear_settings_button)
        buttons.addStretch(1)
        self.domain_page = QWidget()
        domain_col = QVBoxLayout(self.domain_page)
        domain_col.setContentsMargins(0, 0, 0, 0)
        domain_col.addWidget(self.settings_box)
        domain_col.addLayout(buttons)
        domain_col.addWidget(self.domain_note)
        domain_col.addStretch(1)

        self.pages = QStackedWidget()
        self.pages.addWidget(self.calculator_page)
        self.pages.addWidget(self.domain_page)

        right = QWidget()
        col = QVBoxLayout(right)
        col.addWidget(self.title)
        col.addWidget(self.summary)
        col.addLayout(options)
        col.addWidget(self.pages, 1)

        splitter = QSplitter()
        splitter.addWidget(self.tree)
        splitter.addWidget(right)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([280, 820])
        self.setCentralWidget(splitter)

    def _calculator_items(self) -> Iterator[QTreeWidgetItem]:
        """Yield the tree's calculator rows, in order."""
        for i in range(self.tree.topLevelItemCount()):
            domain = self.tree.topLevelItem(i)
            for j in range(domain.childCount() if domain is not None else 0):
                child = domain.child(j) if domain is not None else None
                if child is not None and child.data(0, ID_ROLE):
                    yield child

    def _build_menu(self) -> None:
        help_menu = self.menuBar().addMenu("&Help")
        self.about_action = help_menu.addAction(f"&About {self.branding.name.replace('&', '&&')}")
        self.about_action.triggered.connect(self._show_about)

    def _apply_icons(self) -> None:
        """(Re)color every icon for the current light or dark scheme."""
        for i in range(self.tree.topLevelItemCount()):
            domain = self.tree.topLevelItem(i)
            if domain is not None:
                domain.setIcon(0, icon("category"))
        for child in self._calculator_items():
            child.setIcon(0, icon("calculator"))
        self.about_action.setIcon(icon("info-circle"))

    def _on_color_scheme_changed(self, *_args: object) -> None:
        clear_cache()
        self._apply_icons()
        self.recompute()
        self._show_setting_problems()

    def _show_about(self) -> None:
        QMessageBox.about(self, f"About {self.branding.name}", about_html(self.branding))

    # --- selection ------------------------------------------------------------------------

    def _on_tree_changed(self, current: QTreeWidgetItem | None, _previous: object) -> None:
        if current is None:
            return
        if calc_id := current.data(0, ID_ROLE):
            self.select_calculator(str(calc_id))
        elif domain_id := current.data(0, DOMAIN_ROLE):
            self.select_domain(str(domain_id))

    def select_calculator(self, calc_id: str) -> None:
        """Show the calculator with ``calc_id`` and build its input form."""
        calc = self.registry.get(calc_id)
        self._apply_setting_edits()
        self._leave_calculator()
        self.calculator = calc
        self.domain = None
        self.title.setText(calc.name)
        self.summary.setText(calc.summary)
        self.method_row.show()
        self.pages.setCurrentWidget(self.calculator_page)
        self.method_box.blockSignals(True)
        self.method_box.clear()
        for m in calc.methods:
            self.method_box.addItem(f"{m.label}  [{m.status}]", m.key)
        self.method_box.blockSignals(False)
        self._rebuild_form()

    def select_domain(self, domain_id: str) -> None:
        """Show the settings page of the domain with ``domain_id``."""
        domain = self.registry.domain(domain_id)
        self._apply_setting_edits()
        self._leave_calculator()
        self.domain = domain
        self.calculator = None
        self.title.setText(domain.name)
        self.summary.setText(domain.summary)
        self.method_row.hide()
        self.pages.setCurrentWidget(self.domain_page)
        self._rebuild_domain_form()

    @property
    def method_key(self) -> str:
        """The key of the method selected in the method box."""
        return str(self.method_box.currentData())

    def _on_method_changed(self, _index: int) -> None:
        if self.calculator is not None:
            self._finish_field_edits()
            self._rebuild_form()

    def _on_units_changed(self, unit: str) -> None:
        self._apply_setting_edits()
        self._finish_field_edits()
        prefs = DisplayPrefs(length_unit=unit)
        self._name_pending_units(prefs)
        self.prefs = prefs
        if self.domain is not None:
            self._rebuild_domain_form()
        else:
            self._rebuild_form()

    # --- calculator form ------------------------------------------------------------------
    # Each field shows the value the run uses for it. Only the user's own typing creates
    # intent: a unit switch, an inherited value, and a loaded example keep their base value
    # and are never re-read from the field (ADR-0013 §9). Fields recompute as the user types,
    # but an edit is judged when it ends (Enter, focus leaving, or leaving the page or
    # switching units): keystrokes such as "0.1" on the way to "0.156" are provisional, so
    # retyping the value in use, or ending on unreadable text, records nothing (decision C).
    # A field inheriting a set family value is read-only; only unticking its box overrides.

    def _rebuild_form(self) -> None:
        calc = self.calculator
        if calc is None:
            return
        for _p, old in self.fields.values():
            old.blockSignals(True)  # removing a field mustn't edit it mid-rebuild
        while self.form.rowCount():
            self.form.removeRow(0)
        self.fields.clear()
        self.inherit_boxes.clear()
        self.override_notes.clear()
        domain = self.registry.domain(calc.domain)
        self.example_button.setVisible(any(m.legacy for m in calc.methods))
        for p in calc.params_for(self.method_key):
            edit = QLineEdit()
            if self._inherits_set_value(calc, p):
                dropped = self.pending_fields.pop((calc.id, p.key), None)
                if dropped is not None:  # it can't apply while the field inherits
                    self.field_notices[calc.id, p.key] = (
                        f"Your unapplied text {dropped!r} for {p.label.lower()} was "
                        f"discarded; it now uses the {domain.name} value."
                    )
            pending = self.pending_fields.get((calc.id, p.key))
            edit.setText(self._shown_text(calc, p) if pending is None else pending)
            default = p.default_value()
            if default is not None:
                edit.setPlaceholderText(f"default {field_text(default, p.dimension, self.prefs)}")
            edit.setToolTip(p.help)
            edit.textEdited.connect(partial(self._on_field_edited, p.key))
            edit.editingFinished.connect(partial(self._finish_field_edit, p.key))
            field = QHBoxLayout()
            field.addWidget(edit, 1)
            field.addWidget(QLabel(unit_suffix(p.dimension, self.prefs).strip()))
            row = QVBoxLayout()
            row.addLayout(field)
            if p.shared:
                box = QCheckBox(f"Use {domain.name} value")
                box.setToolTip(
                    f"Use the {domain.name} settings' value. Untick to give this calculator "
                    "its own value."
                )
                box.toggled.connect(partial(self._on_inherit_toggled, p.key))
                field.addWidget(box)
                note = QLabel()
                note.setWordWrap(True)
                row.addWidget(note)
                self.inherit_boxes[p.key] = box
                self.override_notes[p.key] = note
            self.form.addRow(f"{p.label} ({p.symbol})", row)
            self.fields[p.key] = (p, edit)
        self.recompute()

    def _inherits(self, calc: Calculator, p: Param) -> bool:
        """Whether ``p`` takes its domain's value in ``calc``, rather than overriding it."""
        return p.shared and p.key not in self.overrides.get(calc.id, set())

    def _family_value(self, calc: Calculator, p: Param) -> TypedValue | None:
        """The value set for ``p`` in ``calc``'s domain, if any."""
        if not p.shared:
            return None
        return self.domain_settings.get(self.registry.domain(calc.domain), p.key)

    def _inherits_set_value(self, calc: Calculator, p: Param) -> bool:
        return self._inherits(calc, p) and self._family_value(calc, p) is not None

    def _own_value(self, calc: Calculator, p: Param) -> float | None:
        """The value ``calc`` itself has for ``p``: what the user set, or else the default."""
        entry = self.entries.get(calc.id, {}).get(p.key)
        return p.default_value() if entry is None else entry.base_value

    def _value_in_use(self, calc: Calculator, p: Param) -> float | None:
        """The value the run uses for ``p``: the family's, or else the calculator's own."""
        inherited = self._family_value(calc, p)
        if self._inherits(calc, p):
            return p.default_value() if inherited is None else inherited.value
        return self._own_value(calc, p)

    def _shown_text(self, calc: Calculator, p: Param) -> str:
        """Return the text a field shows: the value the run uses for it."""
        if self._inherits(calc, p):
            inherited = self._family_value(calc, p)
            if inherited is not None:
                return entry_text(inherited, self.prefs)
        else:
            entry = self.entries.get(calc.id, {}).get(p.key)
            if entry is not None and isinstance(entry.value, TypedValue):
                return entry_text(entry.value, self.prefs)
        value = self._value_in_use(calc, p)
        return "" if value is None else field_text(value, p.dimension, self.prefs)

    def _field_problem(self, p: Param, text: str) -> str | None:
        """Return why ``text`` can't be read as a value of ``p``, or ``None`` if it can."""
        default_unit = self.prefs.length_unit if p.dimension is Dimension.LENGTH else None
        try:
            TypedValue.parse(text, p.dimension, default_unit)
        except InputError as exc:
            return f"{p.label}: {exc}"
        return None

    def _on_field_edited(self, key: str, text: str) -> None:
        """Apply a keystroke provisionally, so results follow the typing.

        The first keystroke of an edit records how the field stood, so the edit can be
        judged, and undone if it changes nothing, when it ends (``_finish_field_edit``).
        Empty text drops the field's own value; unreadable text is kept and applies nothing.
        """
        calc = self.calculator
        if calc is None:
            return
        p, _edit = self.fields[key]
        own = self.entries.setdefault(calc.id, {})
        overrides = self.overrides.setdefault(calc.id, set())
        if (calc.id, key) not in self.edit_starts:
            pending = self.pending_fields.get((calc.id, key))
            self.edit_starts[calc.id, key] = _EditStart(
                entry=own.get(key),
                overridden=key in overrides,
                shown=self._shown_text(calc, p) if pending is None else pending,
                in_use=self._value_in_use(calc, p),
            )
        if not text.strip():
            self.pending_fields.pop((calc.id, key), None)
            own.pop(key, None)
        elif self._field_problem(p, text) is not None:
            self.pending_fields[calc.id, key] = text
        else:
            self.pending_fields.pop((calc.id, key), None)
            default_unit = self.prefs.length_unit if p.dimension is Dimension.LENGTH else None
            own[key] = FieldEntry(TypedValue.parse(text, p.dimension, default_unit))
            if p.shared:
                overrides.add(key)
        self.recompute()

    def _finish_field_edit(self, key: str) -> None:
        """Judge an edit as it ends: keep it, or put the field back as it stood.

        An edit that ends on the text the field showed, or on the value already in use,
        changes nothing; nor does one that ends on unreadable text, which stays shown with
        its error. Anything else is kept, and in a shared field overrides for the session.
        """
        calc = self.calculator
        if calc is None or key not in self.fields:
            return
        # KI-018: focus leaving for another window (Alt+Tab) also ends an edit here.
        start = self.edit_starts.pop((calc.id, key), None)
        if start is None:
            return
        p, edit = self.fields[key]
        text = edit.text()
        if not text.strip():
            unchanged = self._value_in_use(calc, p) == start.in_use
        elif self._field_problem(p, text) is not None:
            unchanged = True
        else:
            default_unit = self.prefs.length_unit if p.dimension is Dimension.LENGTH else None
            value = TypedValue.parse(text, p.dimension, default_unit).value
            unchanged = text.strip() == start.shown or value == start.in_use
        if unchanged:
            own = self.entries.setdefault(calc.id, {})
            if start.entry is None:
                own.pop(key, None)
            else:
                own[key] = start.entry
            overrides = self.overrides.setdefault(calc.id, set())
            if start.overridden:
                overrides.add(key)
            else:
                overrides.discard(key)
        self.recompute()

    def _finish_field_edits(self) -> None:
        """End every edit in the shown calculator's fields, as leaving each field would."""
        for key in list(self.fields):
            self._finish_field_edit(key)

    def _leave_calculator(self) -> None:
        """End the shown calculator's edits, and forget notices it has already shown."""
        if self.calculator is not None:
            self._finish_field_edits()
            calc_id = self.calculator.id
            for key in [k for k in self.field_notices if k[0] == calc_id]:
                del self.field_notices[key]

    def _on_inherit_toggled(self, key: str, inherit: bool) -> None:
        """Tick to use the family value; untick to override it with an exact copy of it.

        The copy changes nothing until the user edits it (as CAD tools do), and results
        name it as copied from the family settings.
        """
        calc = self.calculator
        if calc is None:
            return
        self._finish_field_edit(key)
        p, edit = self.fields[key]
        overrides = self.overrides.setdefault(calc.id, set())
        if inherit:
            overrides.discard(key)
        else:
            inherited = self._family_value(calc, p)
            if inherited is not None:
                self.entries.setdefault(calc.id, {})[key] = FieldEntry(
                    inherited, EntryOrigin.FAMILY_COPY
                )
            overrides.add(key)
        self.pending_fields.pop((calc.id, key), None)
        self.field_notices.pop((calc.id, key), None)
        edit.setText(self._shown_text(calc, p))
        self.recompute()

    def load_course_example(self) -> None:
        """Fill the course method's inputs with the course example (decision D).

        The built-in defaults are the course examples (docs/user/calculators/sheet-metal.md),
        so each input the course method uses gets its default as an explicit value, and
        shared ones override the family settings. A method that isn't the course's is
        switched to the course method, so the example gives the lesson's answer. Inputs
        the course doesn't use, such as K, are left exactly as they were.
        """
        calc = self.calculator
        if calc is None:
            return
        course = next((m for m in calc.methods if m.legacy), None)
        if course is None:
            return
        self._finish_field_edits()  # a shortcut or script may load mid-edit
        if not calc.get_method(self.method_key).legacy:
            self.method_box.blockSignals(True)
            self.method_box.setCurrentIndex(self.method_box.findData(course.key))
            self.method_box.blockSignals(False)
        lesson = calc.params_for(course.key)
        self.entries.setdefault(calc.id, {}).update(
            {
                p.key: FieldEntry(value, EntryOrigin.COURSE_EXAMPLE)
                for p in lesson
                if (value := p.default_value()) is not None
            }
        )
        self.overrides.setdefault(calc.id, set()).update(p.key for p in lesson if p.shared)
        for p in lesson:
            self.pending_fields.pop((calc.id, p.key), None)
        self._rebuild_form()

    def _entry_label(self, calc: Calculator, p: Param, entry: FieldEntry) -> str:
        """Return how results name ``entry``'s value; empty for a value the user typed.

        A copy of the family value is credited to the family settings only while it still
        equals the family value.
        """
        if entry.origin is EntryOrigin.COURSE_EXAMPLE:
            return COURSE_EXAMPLE
        if entry.origin is EntryOrigin.FAMILY_COPY:
            settings_label = self.registry.domain(calc.domain).settings_label
            inherited = self._family_value(calc, p)
            if inherited is not None and inherited.value == entry.base_value:
                return f"copied from {settings_label}"
            return f"copied earlier from {settings_label}"
        return ""

    def _run_arguments(
        self, calc: Calculator
    ) -> tuple[dict[str, float], dict[str, InputSource], DomainValues]:
        """Return the explicit inputs, their labels, and the domain settings for ``calc``.

        An inheriting field passes nothing, so the run takes the family value or else the
        default. An overriding field passes its own value, or nothing for its default, and
        its key is left out of the settings so the family value can't take its place.
        """
        own = self.entries.get(calc.id, {})
        inputs: dict[str, float] = {}
        labels: dict[str, InputSource] = {}
        for p in calc.params_for(self.method_key):
            entry = own.get(p.key)
            if entry is not None and not self._inherits(calc, p):
                inputs[p.key] = entry.base_value
                if label := self._entry_label(calc, p, entry):
                    labels[p.key] = InputSource(SourceKind.EXPLICIT, label)
        domain = self.registry.domain(calc.domain)
        overridden = self.overrides.get(calc.id, set())
        set_values = self.domain_settings.for_domain(domain).values
        settings = domain.values(**{k: v for k, v in set_values.items() if k not in overridden})
        return inputs, labels, settings

    def _refresh_fields(self, calc: Calculator) -> list[str]:
        """Show each field's state, and return why any field's text can't be read.

        Shared fields show their box while a family value is set, are read-only while
        inheriting it, and show a note while overriding it or after unapplied text in them
        was discarded.
        """
        domain = self.registry.domain(calc.domain)
        problems = []
        for key, (p, edit) in self.fields.items():
            pending = self.pending_fields.get((calc.id, key))
            problem = None if pending is None else self._field_problem(p, pending)
            edit.setStyleSheet(_outline("outline_error") if problem else "")
            if problem:
                problems.append(problem)
            edit.setReadOnly(self._inherits_set_value(calc, p))
            box = self.inherit_boxes.get(key)
            note = self.override_notes.get(key)
            if box is None or note is None:
                continue
            inherited = self._family_value(calc, p)
            box.setVisible(inherited is not None)
            box.blockSignals(True)
            box.setChecked(self._inherits(calc, p))
            box.blockSignals(False)
            own = self._own_value(calc, p)
            text = self.field_notices.get((calc.id, key), "")
            if inherited is not None and not self._inherits(calc, p) and own is not None:
                text = describe_override(domain.name, inherited.value, own, p.dimension, self.prefs)
            note.setText(text)
            note.setVisible(bool(text))
        return problems

    def recompute(self) -> None:
        """Run the calculator on the form's values, and show the result or the input errors."""
        calc = self.calculator
        if calc is None:
            return
        problems = self._refresh_fields(calc)
        scheme = current_scheme()
        self.result = None
        if problems:
            self.output.setHtml(_error_html(problems, scheme))
            return
        try:
            inputs, labels, settings = self._run_arguments(calc)
            self.result = calc.run(
                inputs, method=self.method_key, settings=settings, explicit_sources=labels
            )
        except CaddCalcError as exc:
            self.output.setHtml(_error_html([describe_error(exc, self.prefs)], scheme))
            return
        for note in self.result.notes:
            for key in note.subjects:
                if key in self.fields:
                    self.fields[key][1].setStyleSheet(_outline("outline_note"))
        self.output.setHtml(result_html(calc, self.result, self.prefs, scheme))

    # --- domain settings page -------------------------------------------------------------
    # Fields apply on Enter or when focus leaves them, and are checked as the user types.
    # Applying every keystroke would store passing prefixes ("1" on the way to "15") in
    # values that calculators the user can't see from here will use.

    def _rebuild_domain_form(self) -> None:
        """Build one field per setting of ``self.domain``: unapplied text, or the set value."""
        domain = self.domain
        if domain is None:
            return
        for _setting, old in self.setting_fields.values():
            old.blockSignals(True)  # removing a focused field mustn't apply it mid-rebuild
        while self.settings_form.rowCount():
            self.settings_form.removeRow(0)
        self.setting_fields.clear()
        for setting in domain.settings:
            edit = QLineEdit()
            edit.setPlaceholderText("not set")
            pending = self.pending_settings.get((domain.id, setting.key))
            if pending is not None:
                edit.setText(pending)
                edit.setModified(True)
            elif (entry := self.domain_settings.get(domain, setting.key)) is not None:
                edit.setText(entry_text(entry, self.prefs))
            edit.setToolTip(setting.help)
            edit.textEdited.connect(partial(self._on_setting_edited, setting.key))
            edit.editingFinished.connect(partial(self._apply_setting, setting.key))
            field = QHBoxLayout()
            field.addWidget(edit, 1)
            field.addWidget(QLabel(unit_suffix(setting.dimension, self.prefs).strip()))
            about = QLabel(
                _setting_about_html(
                    setting,
                    self.registry.setting_uses(domain.id, setting.key),
                    overridden_in=[
                        calc.name
                        for calc, _methods in self.registry.setting_uses(domain.id, setting.key)
                        if setting.key in self.overrides.get(calc.id, set())
                    ],
                )
            )
            about.setTextFormat(Qt.TextFormat.RichText)
            about.setWordWrap(True)
            row = QVBoxLayout()
            row.addLayout(field)
            row.addWidget(about)
            self.settings_form.addRow(f"{setting.label} ({setting.symbol})", row)
            self.setting_fields[setting.key] = (setting, edit)
        self.settings_box.setVisible(bool(domain.settings))
        self.clear_settings_button.setEnabled(bool(domain.settings))
        self._show_setting_problems()

    def _setting_problem(self, setting: Param, text: str) -> str | None:
        """Return why ``text`` can't be applied to ``setting``, or ``None`` if it can."""
        domain = self.domain
        if domain is None or not text.strip():
            return None
        default_unit = self.prefs.length_unit if setting.dimension is Dimension.LENGTH else None
        try:
            self.domain_settings.set_text(domain, setting.key, text, default_unit)
        except InputError as exc:
            message = describe_error(exc, self.prefs)
            if isinstance(exc, OutOfRangeError):  # a range error already names the setting
                return message
            return f"{setting.label} ({setting.symbol}): {message}"
        return None

    def _on_setting_edited(self, key: str, text: str) -> None:
        """Check what the user is typing, without applying it."""
        if self.domain is not None:
            self.pending_settings[self.domain.id, key] = text
            self._show_setting_problems()

    def _apply_setting(self, key: str) -> None:
        """Apply a field's edited text; empty text unsets, and refused text applies nothing."""
        domain = self.domain
        if domain is None or key not in self.setting_fields:
            return
        setting, edit = self.setting_fields[key]
        if not edit.isModified():
            return  # shown text, never re-read as a value (ADR-0013 §9)
        text = edit.text()
        if self._setting_problem(setting, text) is None:
            if text.strip():
                default_unit = (
                    self.prefs.length_unit if setting.dimension is Dimension.LENGTH else None
                )
                updated = self.domain_settings.set_text(domain, key, text, default_unit)
            else:
                updated = self.domain_settings.clear(domain, key)
            self.domain_settings = updated
            self.pending_settings.pop((domain.id, key), None)
            edit.setModified(False)
        else:
            self.pending_settings[domain.id, key] = text
        self._show_setting_problems()

    def _apply_setting_edits(self) -> None:
        """Apply every field's unapplied text, as leaving each field would."""
        for key in list(self.setting_fields):
            self._apply_setting(key)

    def _name_pending_units(self, new_prefs: DisplayPrefs) -> None:
        """Before the display unit changes, give unapplied unitless text its unit.

        Unapplied text is read in the display unit when it is applied, so "5" typed in
        inches would mean 5 mm after a switch to mm. Writing it as "5 in" keeps the
        user's meaning, and the field shows exactly what will be applied (ADR-0013 §9).
        Text that names its unit, or that can't be read in any unit, is left as typed.
        This covers settings fields and calculator fields alike.
        """
        for (domain_id, key), text in list(self.pending_settings.items()):
            dimension = self.registry.domain(domain_id).setting(key).dimension
            self.pending_settings[domain_id, key] = _name_unit(
                text, dimension, self.prefs, new_prefs
            )
        for (calc_id, key), text in list(self.pending_fields.items()):
            param = next(p for p in self.registry.get(calc_id).params if p.key == key)
            self.pending_fields[calc_id, key] = _name_unit(
                text, param.dimension, self.prefs, new_prefs
            )

    def _clear_domain_settings(self) -> None:
        domain = self.domain
        if domain is not None:
            self.domain_settings = self.domain_settings.clear_domain(domain)
            for key in [k for k in self.pending_settings if k[0] == domain.id]:
                del self.pending_settings[key]
            self._rebuild_domain_form()

    def _show_setting_problems(self) -> None:
        """Outline each field whose text is refused, and explain why under the form."""
        domain = self.domain
        if domain is None:
            return
        problems = []
        for key, (setting, edit) in self.setting_fields.items():
            pending = self.pending_settings.get((domain.id, key))
            problem = None if pending is None else self._setting_problem(setting, pending)
            edit.setStyleSheet(_outline("outline_error") if problem else "")
            if problem:
                problems.append(problem)
        self.domain_note.setText(
            _domain_note_html(
                domain,
                has_calculators=bool(self.registry.by_domain().get(domain)),
                errors=problems,
                scheme=current_scheme(),
            )
        )


GENERIC_ABOUT = "<p>Open-source calculators for computer-aided drafting and design.</p>"


def about_html(branding: Branding) -> str:
    """Return the Help > About text.

    A branding pack replaces the description. The version, the disclaimer, the link to
    the source code, and the third-party credits are always shown.
    """
    return (
        f"<h3>{escape(branding.name)} {escape(__version__)}</h3>"
        + (branding.about_html if branding.about_html is not None else GENERIC_ABOUT)
        + f"<p>{escape(DISCLAIMER)}</p>"
        '<p><a href="https://github.com/inmymoonsuit/CADD-Calculator">'
        "github.com/inmymoonsuit/CADD-Calculator</a></p>"
        '<p>Icons: <a href="https://tabler.io/icons">Tabler Icons</a>, MIT License. '
        "Third-party notices are in THIRD_PARTY_NOTICES.md.</p>"
    )


def _img(name: str, role: str, scheme: Scheme) -> str:
    """Return an inline icon for the results pane, served by ``ResultsBrowser``."""
    return (
        f'<img src="{ICON_URL_SCHEME}:{scheme}/{role}/{name}" width="16" height="16" '
        'align="middle">&nbsp;'
    )


_NOTE_ICONS = {
    NoteKind.WARNING: ("alert-triangle", "icon_warning"),
    NoteKind.LIMIT_EXCEEDED: ("alert-circle", "icon_error"),
    NoteKind.NO_APPLICABLE_VALUE: ("info-circle", "icon"),
    NoteKind.INFEASIBLE: ("alert-circle", "icon_error"),
}
"""The icon and palette role that mark each kind of note in the results pane."""


def _outline(role: str) -> str:
    """Return a style sheet outlining a field in a palette role's colour for the scheme."""
    return f"QLineEdit {{ border: 1px solid {role_color(role, current_scheme())}; }}"


def _error_html(errors: list[str], scheme: Scheme = "light") -> str:
    items = "".join(f"<li>{escape(e)}</li>" for e in errors)
    return (
        f"<p style='color:{role_color('text_error', scheme)}'>"
        f"{_img('alert-circle', 'icon_error', scheme)}"
        f"<b>Check the inputs:</b></p><ul>{items}</ul>"
    )


def _name_unit(text: str, dimension: Dimension, old: DisplayPrefs, new: DisplayPrefs) -> str:
    """Return ``text`` with the unit it was typed in, if the switch would change its meaning.

    Only a bare number, in a dimension whose display unit changes, gains its unit.
    """
    typed_in = display_unit(dimension, old)
    if typed_in == display_unit(dimension, new):
        return text
    try:
        parsed = parse_quantity_detailed(text, dimension, typed_in.symbol)
    except InputError:
        return text
    return text if parsed.explicit_unit else f"{text.strip()} {typed_in.symbol}"


def _setting_about_html(
    setting: Param,
    uses: Sequence[tuple[Calculator, Sequence[Method]]],
    *,
    overridden_in: Sequence[str],
) -> str:
    """Return a setting's help, the calculators that use it, and those overriding it."""
    lines = describe_setting_uses(uses)
    used = "".join(f"<br>&nbsp;&nbsp;• {escape(line)}" for line in lines)
    overridden = (
        f"<br><b>Overridden in {len(overridden_in)}:</b> {escape('; '.join(overridden_in))}"
        if overridden_in
        else ""
    )
    return (
        f"<small>{escape(setting.help)}<br><b>Used by:</b>{used or ' no loaded calculator'}"
        f"{overridden}</small>"
    )


def _domain_note_html(
    domain: Domain, *, has_calculators: bool, errors: Sequence[str], scheme: Scheme = "light"
) -> str:
    """Return the note under a settings page: no calculators, and any refused values."""
    parts = []
    if not has_calculators:
        parts.append(
            f"<p><b>{NO_CALCULATORS}.</b> No calculator uses the {escape(domain.name)} "
            "settings in this session.</p>"
        )
    if errors:
        items = "".join(f"<li>{escape(e)}</li>" for e in errors)
        parts.append(
            f"<p style='color:{role_color('text_error', scheme)}'><b>Not applied.</b> Each of "
            "these settings keeps its "
            f"previous value until its text is fixed:</p><ul>{items}</ul>"
        )
    return "".join(parts)


def result_html(
    calc: Calculator, result: Result, prefs: DisplayPrefs, scheme: Scheme = "light"
) -> str:
    """Return the results pane as rich text: results, notes, inputs, work, and method."""
    method = calc.get_method(result.method)
    rows = "".join(
        f"<tr><td><b>{escape(o.symbol)}</b></td><td>{escape(o.label)}</td>"
        f"<td align='right'><b>{escape(format_value(result.outputs[o.key], o.dimension, prefs))}"
        "</b></td></tr>"
        for o in calc.outputs
    )
    parts = [f"<h3>Results</h3><table cellpadding='4'>{rows}</table>"]
    if result.notes:
        warn = "".join(
            f"<li>{_img(*_NOTE_ICONS[note.kind], scheme)}{escape(describe_note(note))}</li>"
            for note in result.notes
        )
        parts.append(
            f"<h3 style='color:{role_color('text_warning', scheme)}'>"
            f"{_img('alert-triangle', 'icon_warning', scheme)}"
            f"Notes</h3><ul>{warn}</ul>"
        )
    inputs = "".join(
        f"<tr><td><b>{escape(p.symbol)}</b></td><td>{escape(p.label)}</td>"
        f"<td align='right'>{escape(format_value(result.inputs[p.key], p.dimension, prefs))}</td>"
        f"<td>({escape(describe_source(result.source_of(p.key)))})</td></tr>"
        for p in calc.params_for(result.method)
    )
    parts.append(f"<h3>Inputs</h3><table cellpadding='4'>{inputs}</table>")
    work = []
    for step in result.steps:
        symbolic, numeric, value = render_step(step, result, prefs)
        lines = [f"{step.symbol} = {symbolic}"]
        if numeric:
            lines.append(f"= {numeric}")
        lines.append(f"= {value}")
        work.append("<br>&nbsp;&nbsp;&nbsp;&nbsp;".join(escape(x) for x in lines))
    parts.append("<h3>Work</h3><p style='font-family: monospace'>" + "<br><br>".join(work) + "</p>")
    refs = "".join(f"<li>{escape(str(r))}</li>" for r in method.references)
    notes = "".join(f"<li>{escape(n)}</li>" for n in method.notes)
    parts.append(
        f"<h3>Method</h3><p><b>{escape(method.label)}</b>: {escape(method.summary)}<br>"
        f"Status: <b>{escape(method.status)}</b></p>"
        + (f"<ul>{notes}</ul>" if notes else "")
        + (f"<p>References:</p><ul>{refs}</ul>" if refs else "<p>References: none yet.</p>")
    )
    return "".join(parts)
