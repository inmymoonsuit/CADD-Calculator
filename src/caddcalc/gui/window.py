"""Main window: calculators and their families on the left; their pages on the right."""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from functools import partial
from html import escape
from typing import Any, cast, override

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QGuiApplication, QTextDocument
from PySide6.QtWidgets import (
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
    InputError,
    Method,
    OutOfRangeError,
    Param,
    Registry,
    Result,
)
from caddcalc.core.formatting import (
    DISCLAIMER,
    DisplayPrefs,
    describe_error,
    describe_setting_uses,
    entry_text,
    field_text,
    format_value,
    render_step,
    unit_suffix,
)
from caddcalc.core.units import Dimension, parse_quantity
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
ERROR_STYLE = "QLineEdit { border: 1px solid #c0392b; }"
ICON_URL_SCHEME = "icon"
ICON_PX = 32
"""Pixel size icons are rendered at for the results pane; shown at 16 px, so sharp on HiDPI."""


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
        self.values: dict[str, dict[str, float]] = {}
        """Last good input values per calculator id, by parameter key, in base units."""
        self.fields: dict[str, tuple[Param, QLineEdit]] = {}
        self.domain_settings = DomainSettings()
        """The domain settings the user has set; kept for the life of the window (§7)."""
        self.setting_fields: dict[str, tuple[Param, QLineEdit]] = {}
        self.setting_errors: dict[str, str] = {}
        """Why each setting field's text was refused, by setting key."""

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
        self.output = ResultsBrowser()
        self.output.setOpenExternalLinks(True)
        self.calculator_page = QWidget()
        calc_col = QVBoxLayout(self.calculator_page)
        calc_col.setContentsMargins(0, 0, 0, 0)
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
        if calc.id not in self.values:
            self.values[calc.id] = {
                p.key: v for p in calc.params if (v := p.default_value()) is not None
            }
        self._rebuild_form()

    def select_domain(self, domain_id: str) -> None:
        """Show the settings page of the domain with ``domain_id``."""
        domain = self.registry.domain(domain_id)
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
            self._rebuild_form()

    def _on_units_changed(self, unit: str) -> None:
        self._read_fields()  # keep any valid edits made in the old unit
        self.prefs = DisplayPrefs(length_unit=unit)
        if self.domain is not None:
            self._rebuild_domain_form()
        else:
            self._rebuild_form()

    # --- calculator form ------------------------------------------------------------------

    def _rebuild_form(self) -> None:
        if self.calculator is None:
            return
        while self.form.rowCount():
            self.form.removeRow(0)
        self.fields.clear()
        stored = self.values[self.calculator.id]
        for p in self.calculator.params_for(self.method_key):
            edit = QLineEdit()
            if p.key in stored:
                edit.setText(field_text(stored[p.key], p.dimension, self.prefs))
            edit.setToolTip(p.help)
            edit.textEdited.connect(self.recompute)
            row = QHBoxLayout()
            row.addWidget(edit, 1)
            row.addWidget(QLabel(unit_suffix(p.dimension, self.prefs).strip()))
            self.form.addRow(f"{p.label} ({p.symbol})", row)
            self.fields[p.key] = (p, edit)
        self.recompute()

    def _read_fields(self) -> list[str]:
        """Parse every field into ``self.values``. Return error messages for bad fields."""
        if self.calculator is None:
            return []
        errors: list[str] = []
        stored = self.values[self.calculator.id]
        for key, (p, edit) in self.fields.items():
            default_unit = self.prefs.length_unit if p.dimension is Dimension.LENGTH else None
            try:
                stored[key] = parse_quantity(edit.text(), p.dimension, default_unit)
                edit.setStyleSheet("")
            except CaddCalcError as exc:
                edit.setStyleSheet(ERROR_STYLE)
                errors.append(f"{p.label}: {exc}")
        return errors

    def recompute(self) -> None:
        """Read the inputs, run the calculator, and show the result or the input errors."""
        calc = self.calculator
        if calc is None:
            return
        errors = self._read_fields()
        scheme = current_scheme()
        if errors:
            self.output.setHtml(_error_html(errors, scheme))
            return
        try:
            inputs = {k: self.values[calc.id][k] for k in self.fields}
            result = calc.run(inputs, method=self.method_key)
        except CaddCalcError as exc:
            self.output.setHtml(_error_html([describe_error(exc, self.prefs)], scheme))
            return
        self.output.setHtml(result_html(calc, result, self.prefs, scheme))

    # --- domain settings page -------------------------------------------------------------

    def _rebuild_domain_form(self) -> None:
        """Build one field per setting of ``self.domain``, showing what the user has set."""
        domain = self.domain
        if domain is None:
            return
        while self.settings_form.rowCount():
            self.settings_form.removeRow(0)
        self.setting_fields.clear()
        self.setting_errors.clear()
        for setting in domain.settings:
            edit = QLineEdit()
            edit.setPlaceholderText("not set")
            entry = self.domain_settings.get(domain, setting.key)
            if entry is not None:
                edit.setText(entry_text(entry, self.prefs))
            edit.setToolTip(setting.help)
            edit.textEdited.connect(partial(self._on_setting_edited, setting.key))
            field = QHBoxLayout()
            field.addWidget(edit, 1)
            field.addWidget(QLabel(unit_suffix(setting.dimension, self.prefs).strip()))
            about = QLabel(
                _setting_about_html(setting, self.registry.setting_uses(domain.id, setting.key))
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
        self._show_domain_note()

    def _on_setting_edited(self, key: str, text: str) -> None:
        """Set, or with empty text unset, one domain setting from what the user typed."""
        domain = self.domain
        if domain is None:
            return
        setting, edit = self.setting_fields[key]
        default_unit = self.prefs.length_unit if setting.dimension is Dimension.LENGTH else None
        try:
            if text.strip():
                updated = self.domain_settings.set_text(domain, key, text, default_unit)
            else:
                updated = self.domain_settings.clear(domain, key)
        except InputError as exc:
            edit.setStyleSheet(ERROR_STYLE)
            message = describe_error(exc, self.prefs)
            if not isinstance(exc, OutOfRangeError):  # a range error already names the setting
                message = f"{setting.label} ({setting.symbol}): {message}"
            self.setting_errors[key] = message
        else:
            self.domain_settings = updated
            edit.setStyleSheet("")
            self.setting_errors.pop(key, None)
        self._show_domain_note()

    def _clear_domain_settings(self) -> None:
        if self.domain is not None:
            self.domain_settings = self.domain_settings.clear_domain(self.domain)
            self._rebuild_domain_form()

    def _show_domain_note(self) -> None:
        """Show whether the family has calculators, and why any field's text was refused."""
        domain = self.domain
        if domain is None:
            return
        self.domain_note.setText(
            _domain_note_html(
                domain,
                has_calculators=bool(self.registry.by_domain().get(domain)),
                errors=list(self.setting_errors.values()),
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


def _error_html(errors: list[str], scheme: Scheme = "light") -> str:
    items = "".join(f"<li>{escape(e)}</li>" for e in errors)
    return (
        f"<p style='color:#c0392b'>{_img('alert-circle', 'icon_error', scheme)}"
        f"<b>Check the inputs:</b></p><ul>{items}</ul>"
    )


def _setting_about_html(setting: Param, uses: Sequence[tuple[Calculator, Sequence[Method]]]) -> str:
    """Return a setting's help, and the calculators that use it, for its settings-page row."""
    lines = describe_setting_uses(uses)
    used = "".join(f"<br>&nbsp;&nbsp;• {escape(line)}" for line in lines)
    return (
        f"<small>{escape(setting.help)}<br><b>Used by:</b>{used or ' no loaded calculator'}</small>"
    )


def _domain_note_html(domain: Domain, *, has_calculators: bool, errors: Sequence[str]) -> str:
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
            "<p style='color:#c0392b'><b>Check these settings.</b> Each keeps its last "
            f"valid value until it is fixed:</p><ul>{items}</ul>"
        )
    return "".join(parts)


def result_html(
    calc: Calculator, result: Result, prefs: DisplayPrefs, scheme: Scheme = "light"
) -> str:
    """Return the results pane as rich text: results, warnings, work, and method."""
    method = calc.get_method(result.method)
    rows = "".join(
        f"<tr><td><b>{escape(o.symbol)}</b></td><td>{escape(o.label)}</td>"
        f"<td align='right'><b>{escape(format_value(result.outputs[o.key], o.dimension, prefs))}"
        "</b></td></tr>"
        for o in calc.outputs
    )
    parts = [f"<h3>Results</h3><table cellpadding='4'>{rows}</table>"]
    if result.warnings:
        warn = "".join(f"<li>{escape(w)}</li>" for w in result.warnings)
        parts.append(
            f"<h3 style='color:#b9770e'>{_img('alert-triangle', 'icon_warning', scheme)}"
            f"Warnings</h3><ul>{warn}</ul>"
        )
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
