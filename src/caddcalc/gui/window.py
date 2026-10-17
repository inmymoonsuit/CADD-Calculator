"""Main window: a calculator browser on the left and a generated form with results on the right."""

from __future__ import annotations

from html import escape

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QSplitter,
    QTextBrowser,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from caddcalc import __version__
from caddcalc.core import CaddCalcError, Calculator, Param, Registry, Result, default_registry
from caddcalc.core.formatting import (
    DISCLAIMER,
    DisplayPrefs,
    display_value,
    format_number,
    format_value,
    render_step,
    unit_suffix,
)
from caddcalc.core.units import Dimension, parse_quantity

ID_ROLE = Qt.ItemDataRole.UserRole
ERROR_STYLE = "QLineEdit { border: 1px solid #c0392b; }"


class MainWindow(QMainWindow):
    def __init__(self, registry: Registry | None = None) -> None:
        super().__init__()
        self.registry = registry or default_registry()
        self.prefs = DisplayPrefs()
        self.calculator: Calculator | None = None
        self.values: dict[str, dict[str, float]] = {}
        """Last good input values per calculator id, by parameter key, in base units."""
        self.fields: dict[str, tuple[Param, QLineEdit]] = {}

        self.setWindowTitle("CADD Calculator")
        self.resize(1100, 720)
        self._build_ui()
        self._build_menu()
        self.statusBar().showMessage(DISCLAIMER)

        first = self.tree.topLevelItem(0)
        child = first.child(0) if first is not None else None
        if child is not None:
            self.tree.setCurrentItem(child)

    # --- layout ---------------------------------------------------------------------------

    def _build_ui(self) -> None:
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        for domain, calcs in self.registry.by_domain().items():
            parent = QTreeWidgetItem([domain])
            parent.setFlags(parent.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            for calc in calcs:
                child = QTreeWidgetItem([calc.name])
                child.setData(0, ID_ROLE, calc.id)
                child.setToolTip(0, calc.summary)
                parent.addChild(child)
            self.tree.addTopLevelItem(parent)
        self.tree.expandAll()
        self.tree.currentItemChanged.connect(self._on_tree_changed)

        self.title = QLabel()
        self.title.setStyleSheet("font-size: 16pt; font-weight: 600;")
        self.summary = QLabel()
        self.summary.setWordWrap(True)

        self.method_box = QComboBox()
        self.method_box.currentIndexChanged.connect(self._on_method_changed)
        self.units_box = QComboBox()
        self.units_box.addItems(["in", "mm"])
        self.units_box.currentTextChanged.connect(self._on_units_changed)
        options = QHBoxLayout()
        options.addWidget(QLabel("Method:"))
        options.addWidget(self.method_box, 1)
        options.addSpacing(16)
        options.addWidget(QLabel("Units:"))
        options.addWidget(self.units_box)

        self.form_box = QGroupBox("Inputs")
        self.form = QFormLayout(self.form_box)

        self.output = QTextBrowser()
        self.output.setOpenExternalLinks(True)

        right = QWidget()
        col = QVBoxLayout(right)
        col.addWidget(self.title)
        col.addWidget(self.summary)
        col.addLayout(options)
        col.addWidget(self.form_box)
        col.addWidget(self.output, 1)

        splitter = QSplitter()
        splitter.addWidget(self.tree)
        splitter.addWidget(right)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([280, 820])
        self.setCentralWidget(splitter)

    def _build_menu(self) -> None:
        help_menu = self.menuBar().addMenu("&Help")
        about = help_menu.addAction("&About CADD Calculator")
        about.triggered.connect(self._show_about)

    def _show_about(self) -> None:
        QMessageBox.about(
            self,
            "About CADD Calculator",
            f"<h3>CADD Calculator {escape(__version__)}</h3>"
            "<p>Open-source calculators for computer-aided drafting and design.</p>"
            f"<p>{escape(DISCLAIMER)}</p>"
            '<p><a href="https://github.com/inmymoonsuit/CADD-Calculator">'
            "github.com/inmymoonsuit/CADD-Calculator</a></p>",
        )

    # --- selection ------------------------------------------------------------------------

    def _on_tree_changed(self, current: QTreeWidgetItem | None, _previous: object) -> None:
        calc_id = current.data(0, ID_ROLE) if current is not None else None
        if calc_id:
            self.select_calculator(str(calc_id))

    def select_calculator(self, calc_id: str) -> None:
        calc = self.registry.get(calc_id)
        self.calculator = calc
        self.title.setText(calc.name)
        self.summary.setText(calc.summary)
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

    @property
    def method_key(self) -> str:
        return str(self.method_box.currentData())

    def _on_method_changed(self, _index: int) -> None:
        if self.calculator is not None:
            self._rebuild_form()

    def _on_units_changed(self, unit: str) -> None:
        self._read_fields()  # keep any valid edits made in the old unit
        self.prefs = DisplayPrefs(length_unit=unit)
        self._rebuild_form()

    # --- form -----------------------------------------------------------------------------

    def _rebuild_form(self) -> None:
        assert self.calculator is not None
        while self.form.rowCount():
            self.form.removeRow(0)
        self.fields.clear()
        stored = self.values[self.calculator.id]
        for p in self.calculator.params_for(self.method_key):
            edit = QLineEdit()
            if p.key in stored:
                edit.setText(self._field_text(p, stored[p.key]))
            edit.setToolTip(p.help)
            edit.textEdited.connect(self.recompute)
            row = QHBoxLayout()
            row.addWidget(edit, 1)
            row.addWidget(QLabel(unit_suffix(p.dimension, self.prefs).strip()))
            self.form.addRow(f"{p.label} ({p.symbol})", row)
            self.fields[p.key] = (p, edit)
        self.recompute()

    def _field_text(self, p: Param, base_value: float) -> str:
        shown = display_value(base_value, p.dimension, self.prefs)
        return format_number(shown, 6).rstrip("0").rstrip(".")

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
        calc = self.calculator
        if calc is None:
            return
        errors = self._read_fields()
        if errors:
            self.output.setHtml(_error_html(errors))
            return
        try:
            inputs = {k: self.values[calc.id][k] for k in self.fields}
            result = calc.run(inputs, method=self.method_key)
        except CaddCalcError as exc:
            self.output.setHtml(_error_html([str(exc)]))
            return
        self.output.setHtml(result_html(calc, result, self.prefs))


def _error_html(errors: list[str]) -> str:
    items = "".join(f"<li>{escape(e)}</li>" for e in errors)
    return f"<p style='color:#c0392b'><b>Check the inputs:</b></p><ul>{items}</ul>"


def result_html(calc: Calculator, result: Result, prefs: DisplayPrefs) -> str:
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
        parts.append(f"<h3 style='color:#b9770e'>Warnings</h3><ul>{warn}</ul>")
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
