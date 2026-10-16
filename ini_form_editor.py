# -*- coding: utf-8 -*-
"""Form-style INI editor for the uSWID INI format.

Every INI section becomes a group box whose title is the section name
(e.g. ``uSWID``); every ``key = value`` pair becomes a row with the key as a
label and the value as an input box.

The widget deliberately mirrors the part of the QPlainTextEdit API that
MainWindow used (setPlaceholderText / setReadOnly / setPlainText /
toPlainText / modificationChanged), plus setModified() / isModified()
replacing ``document().setModified()`` / ``document().isModified()``.

A "Raw text" toggle switches to a plain-text view of the same data. Input
that cannot be parsed as INI (or non-INI formats / binary info) is shown in
that raw view automatically.

Note: comments and blank-line layout of the original file are not preserved
when saving from the form view (the content is re-serialized).
"""

from __future__ import annotations

import configparser

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFontDatabase
from PyQt6.QtWidgets import (
    QCheckBox, QGridLayout, QGroupBox, QHBoxLayout, QInputDialog, QLabel,
    QLineEdit, QMessageBox, QPlainTextEdit, QPushButton, QScrollArea,
    QStackedWidget, QToolButton, QVBoxLayout, QWidget,
)

IniData = list[tuple[str, list[tuple[str, str]]]]


# ---------------------------------------------------------------------- #
# INI <-> data helpers
# ---------------------------------------------------------------------- #
def parse_ini(text: str) -> IniData:
    """Parse INI text into [(section, [(key, value), ...]), ...] (order kept).

    Raises configparser.Error if the text is not valid INI.
    """
    parser = configparser.ConfigParser(
        interpolation=None,
        strict=False,
        delimiters=("=",),
        default_section="__no_default_section__",  # treat [DEFAULT] as a normal section
        empty_lines_in_values=False,
    )
    parser.optionxform = str  # type: ignore[assignment]  # keep key case
    parser.read_string(text)
    return [(name, list(parser[name].items())) for name in parser.sections()]


def dump_ini(data: IniData) -> str:
    """Serialize parsed data back to INI text (``key = value`` style)."""
    blocks: list[str] = []
    for name, items in data:
        lines = [f"[{name}]"]
        for key, value in items:
            value = value.replace("\r\n", "\n").replace("\r", "\n")
            value = value.replace("\n", "\n\t")  # continuation lines
            lines.append(f"{key} = {value}" if value else f"{key} =")
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks) + "\n" if blocks else ""


def _valid_key(key: str) -> bool:
    return bool(key) and key[0] not in "[#;" and not any(c in key for c in "=\r\n")


def _valid_section(name: str) -> bool:
    return bool(name) and not any(c in name for c in "[]\r\n")


# ---------------------------------------------------------------------- #
# One section = one group box
# ---------------------------------------------------------------------- #
class SectionBox(QGroupBox):
    changed = pyqtSignal()
    removeRequested = pyqtSignal(object)

    def __init__(self, name: str, items: list[tuple[str, str]],
                 read_only: bool = False, parent: QWidget | None = None):
        super().__init__(name, parent)
        self.section_name = name
        self._rows: list[dict] = []
        self._next_row = 0
        self._read_only = read_only

        outer = QVBoxLayout(self)
        header = QHBoxLayout()
        header.addStretch(1)
        self._add_btn = QPushButton("+ Field")
        self._add_btn.clicked.connect(self._on_add_field)
        self._del_btn = QPushButton("Remove section")
        self._del_btn.clicked.connect(lambda: self.removeRequested.emit(self))
        header.addWidget(self._add_btn)
        header.addWidget(self._del_btn)
        outer.addLayout(header)

        self._grid = QGridLayout()
        self._grid.setColumnMinimumWidth(0, 140)
        self._grid.setColumnStretch(1, 1)
        outer.addLayout(self._grid)

        for key, value in items:
            self._append_row(key, value)
        self.set_read_only(read_only)

    # -- rows ----------------------------------------------------------- #
    def _make_value_widget(self, value: str) -> QWidget:
        if "\n" in value:  # multi-line value (INI continuation lines)
            w = QPlainTextEdit(value)
            lines = min(value.count("\n") + 1, 6)
            w.setFixedHeight(w.fontMetrics().lineSpacing() * lines + 14)
            w.textChanged.connect(self.changed)
        else:
            w = QLineEdit(value)
            w.textChanged.connect(self.changed)
        return w

    @staticmethod
    def _value_of(widget: QWidget) -> str:
        if isinstance(widget, QPlainTextEdit):
            return widget.toPlainText()
        return widget.text()  # type: ignore[attr-defined]

    def _append_row(self, key: str, value: str) -> QWidget:
        row = self._next_row
        self._next_row += 1

        label = QLabel(key)
        label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        value_w = self._make_value_widget(value)
        btn = QToolButton()
        btn.setText("\u2715")
        btn.setToolTip("Remove field")

        rec = {"key": key, "label": label, "value": value_w, "btn": btn}
        btn.clicked.connect(lambda _=False, r=rec: self._remove_row(r))

        top = Qt.AlignmentFlag.AlignTop
        self._grid.addWidget(label, row, 0, top)
        self._grid.addWidget(value_w, row, 1)
        self._grid.addWidget(btn, row, 2, top)
        self._rows.append(rec)

        value_w.setReadOnly(self._read_only)  # type: ignore[attr-defined]
        btn.setEnabled(not self._read_only)
        return value_w

    def _remove_row(self, rec: dict) -> None:
        for w in (rec["label"], rec["value"], rec["btn"]):
            self._grid.removeWidget(w)
            w.deleteLater()
        self._rows.remove(rec)
        self.changed.emit()

    def _on_add_field(self) -> None:
        key, ok = QInputDialog.getText(
            self, "Add field", f"Key name for [{self.section_name}]:")
        key = key.strip()
        if not ok or not key:
            return
        if not _valid_key(key):
            QMessageBox.warning(
                self, "Invalid key",
                "A key cannot be empty, contain '=', or start with '[', '#' or ';'.")
            return
        if any(r["key"] == key for r in self._rows):
            QMessageBox.warning(self, "Duplicate key",
                                f"'{key}' already exists in [{self.section_name}].")
            return
        widget = self._append_row(key, "")
        widget.setFocus()
        self.changed.emit()

    # -- public --------------------------------------------------------- #
    def items(self) -> list[tuple[str, str]]:
        return [(r["key"], self._value_of(r["value"])) for r in self._rows]

    def set_read_only(self, read_only: bool) -> None:
        self._read_only = read_only
        self._add_btn.setEnabled(not read_only)
        self._del_btn.setEnabled(not read_only)
        for r in self._rows:
            r["value"].setReadOnly(read_only)
            r["btn"].setEnabled(not read_only)


# ---------------------------------------------------------------------- #
# The editor
# ---------------------------------------------------------------------- #
class IniFormEditor(QWidget):
    modificationChanged = pyqtSignal(bool)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._modified = False
        self._loading = False
        self._read_only = False
        self._raw_mode = False
        self._boxes: list[SectionBox] = []

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(6)

        # toolbar
        bar = QHBoxLayout()
        self._add_section_btn = QPushButton("+ Add section")
        self._add_section_btn.clicked.connect(self._on_add_section)
        self._raw_check = QCheckBox("Raw text")
        self._raw_check.toggled.connect(self._on_raw_toggled)
        bar.addWidget(self._add_section_btn)
        bar.addStretch(1)
        bar.addWidget(self._raw_check)
        root.addLayout(bar)

        # stacked pages: 0 = form, 1 = raw text
        self._stack = QStackedWidget()
        root.addWidget(self._stack, 1)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        content = QWidget()
        self._boxes_layout = QVBoxLayout(content)
        self._hint = QLabel()
        self._hint.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
        self._hint.setWordWrap(True)
        self._hint.setEnabled(False)  # greyed-out look
        self._boxes_layout.addWidget(self._hint)
        self._boxes_layout.addStretch(1)
        self._scroll.setWidget(content)
        self._stack.addWidget(self._scroll)

        self._raw = QPlainTextEdit()
        self._raw.setFont(QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont))
        self._raw.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self._raw.textChanged.connect(self._touch)
        self._stack.addWidget(self._raw)

        self._update_ui_state()

    # ------------------------------------------------------------------ #
    # QPlainTextEdit-like API used by MainWindow
    # ------------------------------------------------------------------ #
    def setPlaceholderText(self, text: str) -> None:
        self._hint.setText(text)
        self._raw.setPlaceholderText(text)

    def setReadOnly(self, read_only: bool) -> None:
        self._read_only = read_only
        self._update_ui_state()

    def setPlainText(self, text: str, structured: bool = True) -> bool:
        """Load text. Returns True if shown as a form, False if shown raw.

        structured=False forces the raw view (non-INI input / binary info).
        """
        data: IniData | None = None
        if structured:
            try:
                data = parse_ini(text)
            except configparser.Error:
                data = None

        self._loading = True
        try:
            self._rebuild(data or [])
            self._raw.setPlainText(text)
            self._raw_mode = data is None
            self._raw_check.blockSignals(True)
            self._raw_check.setChecked(self._raw_mode)
            self._raw_check.blockSignals(False)
            self._raw_check.setEnabled(structured)
        finally:
            self._loading = False
        self.setModified(False)
        self._update_ui_state()
        return data is not None

    def toPlainText(self) -> str:
        if self._raw_mode:
            return self._raw.toPlainText()
        return dump_ini(self._collect())

    def isModified(self) -> bool:
        return self._modified

    def setModified(self, modified: bool) -> None:
        if modified != self._modified:
            self._modified = modified
            self.modificationChanged.emit(modified)

    # ------------------------------------------------------------------ #
    # internals
    # ------------------------------------------------------------------ #
    def _collect(self) -> IniData:
        return [(b.section_name, b.items()) for b in self._boxes]

    def _touch(self) -> None:
        if not self._loading:
            self.setModified(True)

    def _update_ui_state(self) -> None:
        self._stack.setCurrentIndex(1 if self._raw_mode else 0)
        self._add_section_btn.setEnabled(not self._read_only and not self._raw_mode)
        self._raw.setReadOnly(self._read_only)
        for box in self._boxes:
            box.set_read_only(self._read_only)
        self._hint.setVisible(not self._boxes)

    def _insert_box(self, name: str, items: list[tuple[str, str]]) -> SectionBox:
        box = SectionBox(name, items, self._read_only)
        box.changed.connect(self._touch)
        box.removeRequested.connect(self._on_remove_section)
        self._boxes_layout.insertWidget(self._boxes_layout.count() - 1, box)
        self._boxes.append(box)
        return box

    def _rebuild(self, data: IniData) -> None:
        for box in self._boxes:
            self._boxes_layout.removeWidget(box)
            box.setParent(None)
            box.deleteLater()
        self._boxes.clear()
        for name, items in data:
            self._insert_box(name, items)

    # -- toolbar actions ------------------------------------------------ #
    def _on_add_section(self) -> None:
        name, ok = QInputDialog.getText(
            self, "Add section", "Section name (e.g. uSWID-Link:vcs):")
        name = name.strip()
        if not ok or not name:
            return
        if not _valid_section(name):
            QMessageBox.warning(self, "Invalid section name",
                                "A section name cannot contain '[', ']' or line breaks.")
            return
        if any(b.section_name == name for b in self._boxes):
            QMessageBox.warning(self, "Duplicate section", f"[{name}] already exists.")
            return
        box = self._insert_box(name, [])
        self._update_ui_state()
        self._touch()
        QTimer.singleShot(0, lambda: self._scroll.ensureWidgetVisible(box))

    def _on_remove_section(self, box: SectionBox) -> None:
        answer = QMessageBox.question(
            self, "Remove section", f"Remove section [{box.section_name}] and all its fields?")
        if answer != QMessageBox.StandardButton.Yes:
            return
        self._boxes.remove(box)
        self._boxes_layout.removeWidget(box)
        box.setParent(None)
        box.deleteLater()
        self._update_ui_state()
        self._touch()

    def _on_raw_toggled(self, checked: bool) -> None:
        if checked:  # form -> raw
            self._loading = True
            try:
                self._raw.setPlainText(dump_ini(self._collect()))
            finally:
                self._loading = False
            self._raw_mode = True
        else:  # raw -> form
            try:
                data = parse_ini(self._raw.toPlainText())
            except configparser.Error as error:
                QMessageBox.warning(self, "Invalid INI",
                                    f"Cannot switch to form view:\n{error}")
                self._raw_check.blockSignals(True)
                self._raw_check.setChecked(True)
                self._raw_check.blockSignals(False)
                return
            self._loading = True
            try:
                self._rebuild(data)
            finally:
                self._loading = False
            self._raw_mode = False
        self._update_ui_state()
