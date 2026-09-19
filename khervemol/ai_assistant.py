"""AI Assistant dock — chat with an LLM about chemistry.

The assistant answers chemistry questions and, when you ask it to draw a
molecule, replies with a ``SMILES:`` line that KherveMol renders into the
3D view and 2D sketch (via the RDKit bridge). It talks to any provider in
`ai_providers`. All network runs on a background `QThread`, so a slow or
failing request never blocks or crashes the UI — errors show up as a red
line in the chat.

Copyright (C) 2026 Gwilherm Kerherve

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
"""

import html
import re

from PyQt5.QtCore import QSettings, Qt, QThread, pyqtSignal
from PyQt5.QtGui import QTextCursor
from PyQt5.QtWidgets import (QComboBox, QDialog, QDialogButtonBox, QDockWidget,
                             QFormLayout, QGroupBox, QHBoxLayout, QLabel,
                             QLineEdit, QMessageBox, QPlainTextEdit,
                             QPushButton, QTextBrowser, QToolButton,
                             QVBoxLayout, QWidget)

from . import ai_providers as providers
from . import icons

_SETTINGS = ("Kherve", "KherveMol")

SYSTEM_PROMPT = """You are a chemistry assistant inside KherveMol, a desktop \
app that draws molecules and crystal structures in 3D and 2D.

Answer chemistry questions clearly and concisely.

When the user asks you to draw, build, show or load a MOLECULE, put its \
SMILES string on its own line in the exact form:
    SMILES: <smiles>
For example, for ethanol write `SMILES: CCO`. The app then renders it in \
3D and 2D automatically. Give one short sentence of context, then the \
SMILES line. Only include a SMILES line when a molecule should be drawn.

Crystal unit cells (NaCl, diamond, perovskite, BCC/FCC, …) are not SMILES; \
if asked for one, tell the user to pick it from the Crystal menu."""

_SMILES_RE = re.compile(r"SMILES\s*[:=]\s*`?([^\s`]+)", re.IGNORECASE)
_FENCE_RE = re.compile(r"```(?:smiles)?\s*([^\n`]+?)\s*```", re.IGNORECASE)


def extract_smiles(reply):
    """Pull a SMILES string out of an assistant reply, or None."""
    m = _SMILES_RE.search(reply)
    if m:
        return m.group(1).strip().strip(".,;")
    m = _FENCE_RE.search(reply)
    if m:
        cand = m.group(1).strip()
        if cand and " " not in cand:
            return cand
    return None


def _fmt(text):
    return html.escape(text).replace("\n", "<br>")


# ------------------------------------------------------------------ worker
class _Worker(QThread):
    done = pyqtSignal(object)
    failed = pyqtSignal(str)

    def __init__(self, fn, parent=None):
        super().__init__(parent)
        self._fn = fn

    def run(self):
        try:
            self.done.emit(self._fn())
        except Exception as exc:                  # pragma: no cover - network
            self.failed.emit(str(exc))


# ---------------------------------------------------------------- settings
class AiSettingsDialog(QDialog):
    """Provider / model / API-key settings, like the rest of the family."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("AI Chat Settings")
        self.setMinimumWidth(440)
        self._settings = QSettings(*_SETTINGS)
        self._worker = None

        layout = QVBoxLayout(self)
        form = QFormLayout()
        layout.addLayout(form)

        self.provider_combo = QComboBox()
        for key in providers.PROVIDERS:
            self.provider_combo.addItem(providers.DISPLAY_NAMES[key], key)
        form.addRow("Provider:", self.provider_combo)

        model_row = QHBoxLayout()
        self.model_combo = QComboBox()
        self.model_combo.setEditable(True)
        self.refresh_btn = QToolButton()
        self.refresh_btn.setIcon(icons.icon("mdi.refresh"))
        self.refresh_btn.setToolTip("Refresh the model list from the provider")
        model_row.addWidget(self.model_combo, 1)
        model_row.addWidget(self.refresh_btn)
        form.addRow("Model:", model_row)

        self.key_edit = QLineEdit()
        self.key_edit.setEchoMode(QLineEdit.Password)
        form.addRow("API Key:", self.key_edit)

        self.base_label = QLabel("Base URL:")
        self.base_edit = QLineEdit()
        form.addRow(self.base_label, self.base_edit)

        self.help_box = QGroupBox("How to get an API key")
        help_layout = QVBoxLayout(self.help_box)
        self.help_label = QLabel()
        self.help_label.setWordWrap(True)
        help_layout.addWidget(self.help_label)
        layout.addWidget(self.help_box)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok
                                   | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.provider_combo.currentIndexChanged.connect(self._load_provider)
        self.refresh_btn.clicked.connect(self._refresh)

        saved = self._settings.value("ai/provider", "Claude")
        idx = self.provider_combo.findData(saved)
        if idx >= 0:
            self.provider_combo.setCurrentIndex(idx)
        self._load_provider()

    def _provider(self):
        return self.provider_combo.currentData()

    def _load_provider(self, *_):
        provider = self._provider()
        self.key_edit.setText(self._settings.value(f"ai/key/{provider}", ""))
        self.base_edit.setText(self._settings.value(f"ai/base/{provider}", ""))
        self.key_edit.setEnabled(provider in providers.NEEDS_KEY)
        show_base = provider in ("Local", "Ollama")
        self.base_label.setVisible(show_base)
        self.base_edit.setVisible(show_base)
        self.model_combo.blockSignals(True)
        self.model_combo.clear()
        self.model_combo.addItems(providers.DEFAULT_MODELS.get(provider, []))
        saved = self._settings.value(f"ai/model/{provider}", "")
        if saved:
            self.model_combo.setCurrentText(saved)
        self.model_combo.blockSignals(False)
        self.help_label.setText(providers.PROVIDER_HELP.get(provider, ""))

    def _refresh(self):
        provider = self._provider()
        key, base = self.key_edit.text(), self.base_edit.text()
        self.refresh_btn.setEnabled(False)
        self._worker = _Worker(
            lambda: providers.list_models(provider, key, base), self)
        self._worker.done.connect(self._models_ready)
        self._worker.failed.connect(self._refresh_failed)
        self._worker.start()

    def _models_ready(self, models):
        self.refresh_btn.setEnabled(True)
        if not models:
            QMessageBox.information(self, "AI Chat", "No models returned.")
            return
        current = self.model_combo.currentText()
        self.model_combo.clear()
        self.model_combo.addItems(models)
        self.model_combo.setCurrentText(current if current in models
                                        else models[0])

    def _refresh_failed(self, message):
        self.refresh_btn.setEnabled(True)
        QMessageBox.warning(self, "AI Chat",
                            f"Could not list models:\n{message}")

    def _accept(self):
        provider = self._provider()
        self._settings.setValue("ai/provider", provider)
        self._settings.setValue(f"ai/key/{provider}", self.key_edit.text())
        self._settings.setValue(f"ai/base/{provider}", self.base_edit.text())
        if self.model_combo.currentText():
            self._settings.setValue(f"ai/model/{provider}",
                                    self.model_combo.currentText())
        self.accept()


# -------------------------------------------------------------------- input
class _ChatInput(QPlainTextEdit):
    """Multi-line input that sends on Enter (Shift+Enter = newline)."""

    submitted = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setPlaceholderText("Ask a question, or “draw aspirin”…  "
                                "(Enter to send, Shift+Enter for a newline)")
        self.setFixedHeight(66)

    def keyPressEvent(self, event):
        if (event.key() in (Qt.Key_Return, Qt.Key_Enter)
                and not (event.modifiers() & Qt.ShiftModifier)):
            self.submitted.emit()
            event.accept()
            return
        super().keyPressEvent(event)


# --------------------------------------------------------------------- dock
class AiDock(QDockWidget):
    """Chat panel that answers chemistry and can draw molecules."""

    def __init__(self, window):
        super().__init__("AI Chat", window)
        self._window = window
        self._settings = QSettings(*_SETTINGS)
        self._history = []
        self._worker = None
        self.setAllowedAreas(Qt.RightDockWidgetArea | Qt.LeftDockWidgetArea)

        panel = QWidget()
        v = QVBoxLayout(panel)
        v.setContentsMargins(6, 6, 6, 6)

        head = QHBoxLayout()
        self._provider_label = QLabel()
        self._provider_label.setWordWrap(True)
        head.addWidget(self._provider_label, 1)
        gear = QToolButton()
        gear.setIcon(icons.icon("mdi.cog"))
        gear.setText("⚙")
        gear.setToolTip("AI provider / model / key settings")
        gear.clicked.connect(self._open_settings)
        head.addWidget(gear)
        clear = QToolButton()
        clear.setIcon(icons.icon("mdi.broom"))
        clear.setText("Clear")
        clear.setToolTip("Clear the conversation")
        clear.clicked.connect(self._clear)
        head.addWidget(clear)
        v.addLayout(head)

        self._log = QTextBrowser()
        self._log.setOpenExternalLinks(True)
        v.addWidget(self._log, 1)

        row = QHBoxLayout()
        self._input = _ChatInput()
        self._input.submitted.connect(self._send)
        row.addWidget(self._input, 1)
        self._send_btn = QPushButton("Send")
        self._send_btn.clicked.connect(self._send)
        row.addWidget(self._send_btn)
        v.addLayout(row)

        self.setWidget(panel)
        self._refresh_provider_label()
        self._append("system", "Ask a chemistry question, or say “draw "
                     "caffeine”. Set your provider, model and API key with "
                     "the ⚙ button first.")

    # ------------------------------------------------------------ helpers
    def _refresh_provider_label(self):
        p = self._settings.value("ai/provider", "Claude")
        m = self._settings.value(f"ai/model/{p}", "") or "(no model set)"
        self._provider_label.setText(
            f"<b>{providers.DISPLAY_NAMES.get(p, p)}</b> · {html.escape(m)}")

    def _open_settings(self):
        if AiSettingsDialog(self).exec_():
            self._refresh_provider_label()

    def _clear(self):
        self._history = []
        self._log.clear()

    def _append(self, role, text):
        colors = {"user": "#0e6f52", "assistant": "#123529",
                  "system": "#8a8a8a", "error": "#b00020"}
        who = {"user": "You", "assistant": "AI", "error": "Error"}.get(role, "")
        prefix = (f"<b style='color:{colors[role]}'>{who}:</b> "
                  if who else "")
        self._log.append(
            f"<div style='margin:5px 0; color:{colors.get(role, '#333')}'>"
            f"{prefix}{_fmt(text)}</div>")
        self._log.moveCursor(QTextCursor.End)

    def _set_busy(self, busy):
        self._send_btn.setEnabled(not busy)
        self._send_btn.setText("…" if busy else "Send")
        self._input.setReadOnly(busy)

    # -------------------------------------------------------------- send
    def _send(self):
        if self._worker is not None:
            return
        text = self._input.toPlainText().strip()
        if not text:
            return
        provider = self._settings.value("ai/provider", "Claude")
        model = self._settings.value(f"ai/model/{provider}", "")
        key = self._settings.value(f"ai/key/{provider}", "")
        base = self._settings.value(f"ai/base/{provider}", "")
        if provider in providers.NEEDS_KEY and not (key or "").strip():
            self._append("error", "No API key set — click ⚙ to add one.")
            return
        if not model:
            self._append("error", "No model selected — click ⚙ to choose one.")
            return

        self._input.clear()
        self._append("user", text)
        self._history.append({"role": "user", "content": text})
        messages = ([{"role": "system", "content": SYSTEM_PROMPT}]
                    + self._history)
        self._set_busy(True)

        worker = _Worker(
            lambda: providers.chat(provider, model, messages, key, base), self)
        worker.done.connect(self._on_reply)
        worker.failed.connect(self._on_error)
        worker.finished.connect(lambda: self._finish(worker))
        self._worker = worker
        worker.start()

    def _on_reply(self, reply):
        self._history.append({"role": "assistant", "content": reply})
        self._append("assistant", reply)
        smiles = extract_smiles(reply)
        if not smiles:
            return
        try:
            if self._window.build_smiles(smiles, label=smiles):
                self._append("system", f"✓ Built {smiles} in the 3D view + "
                             "2D sketch.")
            else:
                self._append("error", f"Could not build {smiles}.")
        except Exception as exc:                  # noqa: BLE001
            self._append("error", f"Could not build {smiles}: {exc}")

    def _on_error(self, message):
        self._append("error", message)

    def _finish(self, worker):
        self._worker = None
        self._set_busy(False)
