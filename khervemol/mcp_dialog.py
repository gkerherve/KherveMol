"""Control panel for the assistant connection (Help > Connect to Claude).

Shows whether the connection is open and wires Claude Desktop, Claude
Code and their relatives up to it.

Nothing here says "MCP" unless the user has to type it somewhere: the
protocol is our problem, not theirs.  What a person needs to know is
which application to connect, that it must be restarted afterwards, and
that they then say "KherveMol" in the chat -- that last step is
invisible, and skipping it makes a correctly connected assistant look
broken.

Editing ``claude_desktop_config.json`` by hand is the step that stops
people connecting at all, so the dialog detects the applications on
this machine and writes the entry itself (see ``mcp_hosts``).  The
snippet and its Copy button stay for the ones we refuse to rewrite and
for anyone configuring a machine by hand.

`install(window)` is the one hook the main window calls: it creates the
bridge (off until the user turns it on), adds the Help menu action and
re-opens the bridge when the user left it enabled last session.

Copyright (C) 2026 Gwilherm Kerherve

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
"""

from __future__ import annotations

import json
import sys

from PyQt5.QtCore import QSettings, Qt
from PyQt5.QtGui import QFont, QGuiApplication
from PyQt5.QtWidgets import (
    QAction, QApplication, QCheckBox, QComboBox, QDialog, QDialogButtonBox,
    QFileDialog, QGroupBox, QHBoxLayout, QLabel, QListWidget,
    QListWidgetItem, QMessageBox, QPlainTextEdit, QPushButton,
    QVBoxLayout,
)

from .mcp_bridge import ACCESS_LEVELS
from .mcp_hosts import HOSTS, Host, cli_command, host_config
from .mcp_server import endpoint_path
from .style import _SETTINGS as SETTINGS


#: A literal double quote cannot appear inside an f-string before
#: Python 3.12, and the messages below quote what to type in the chat.
DQ = '"'

#: Access level → (label, what it means).  Order matches ACCESS_LEVELS.
_ACCESS_LABELS = [
    ("Read only",
     "Search the library, inspect the molecule and look at the 3D "
     "view; no changes."),
    ("Edit",
     "Build molecules, crystals, surfaces and reactions, edit atoms "
     "and bonds, change the view — and save over the open file, but "
     "not open or export another one."),
    ("Full (recommended)",
     "Everything, including opening, saving and exporting files it "
     "names itself, so 'open my caffeine file and add a chlorine' "
     "works in one go."),
]


class McpServerDialog(QDialog):
    """Enable/disable the bridge and copy the host configuration."""

    def __init__(self, bridge, parent=None):
        super().__init__(parent)
        self._bridge = bridge
        self.setWindowTitle("Connect to Claude")
        self.setMinimumWidth(620)
        self._build_ui()
        self._refresh()
        # Bound methods, not lambdas: PyQt drops the connection when
        # this dialog is destroyed (it is WA_DeleteOnClose), whereas a
        # lambda would outlive it and fire on a deleted widget.
        bridge.started.connect(self._on_bridge_started)
        bridge.stopped.connect(self._refresh)
        bridge.tool_invoked.connect(self._on_tool_invoked)

    # ── UI ───────────────────────────────────────────────────────────

    def _build_ui(self):
        lay = QVBoxLayout(self)

        blurb = QLabel(
            "Let Claude drive this window directly — no API key, "
            "it uses the login you already have. Works with <b>Claude "
            "Desktop</b> and <b>Claude Code</b>, and with Cursor, "
            "Cline, VS Code and LM Studio.<br><br>"
            "Claude gets the whole app rather than a chat reply: the "
            "molecule, crystal, surface, nanostructure, polymer and "
            "reaction libraries, atom-by-atom editing, the view "
            "controls, file export, and a look at the 3D view to check "
            "its own work. It only listens on this computer (127.0.0.1) "
            "and is off until you tick the box below.")
        blurb.setWordWrap(True)
        lay.addWidget(blurb)

        self._enable = QCheckBox("Let assistants connect to KherveMol")
        self._enable.toggled.connect(self._on_toggled)
        lay.addWidget(self._enable)

        self._status = QLabel()
        self._status.setTextInteractionFlags(Qt.TextSelectableByMouse)
        lay.addWidget(self._status)

        acc_row = QHBoxLayout()
        acc_row.addWidget(QLabel("The assistant may:"))
        self._access = QComboBox()
        for label, tip in _ACCESS_LABELS:
            self._access.addItem(label)
            self._access.setItemData(self._access.count() - 1, tip,
                                     Qt.ToolTipRole)
        self._access.currentIndexChanged.connect(self._on_access_changed)
        acc_row.addWidget(self._access, 1)
        lay.addLayout(acc_row)

        self._access_hint = QLabel()
        self._access_hint.setWordWrap(True)
        lay.addWidget(self._access_hint)

        host_box = QGroupBox("Connect an application")
        host_lay = QVBoxLayout(host_box)
        host_lay.addWidget(QLabel(
            "Pick yours and press Connect — KherveMol writes itself "
            "into that application's own settings, so there is no "
            "config file to edit by hand."))
        self._hosts = QListWidget()
        self._hosts.setMaximumHeight(120)
        self._hosts.currentRowChanged.connect(self._refresh_host_buttons)
        host_lay.addWidget(self._hosts)
        hrow = QHBoxLayout()
        self._connect_btn = QPushButton("Connect")
        self._connect_btn.clicked.connect(self._on_connect)
        self._disconnect_btn = QPushButton("Disconnect")
        self._disconnect_btn.clicked.connect(self._on_disconnect)
        hrow.addWidget(self._connect_btn)
        hrow.addWidget(self._disconnect_btn)
        other = QPushButton("Other application…")
        other.setToolTip(
            "Point at another assistant's JSON config file and add "
            "KherveMol to it.")
        other.clicked.connect(self._on_other_host)
        hrow.addWidget(other)
        hrow.addStretch(1)
        host_lay.addLayout(hrow)
        self._host_hint = QLabel()
        self._host_hint.setWordWrap(True)
        self._host_hint.setTextInteractionFlags(Qt.TextSelectableByMouse)
        host_lay.addWidget(self._host_hint)
        lay.addWidget(host_box)

        row = QHBoxLayout()
        row.addWidget(QLabel("Or set it up by hand:"))
        self._flavour = QComboBox()
        self._flavour.addItems([
            "Claude Desktop / Cursor / Zed (JSON)",
            "Claude Code (command line)",
            "URL only (clients that take an HTTP endpoint)",
        ])
        self._flavour.currentIndexChanged.connect(self._refresh_snippet)
        row.addWidget(self._flavour, 1)
        lay.addLayout(row)

        self._snippet = QPlainTextEdit()
        self._snippet.setReadOnly(True)
        mono = QFont("Consolas" if sys.platform.startswith("win")
                     else "Monospace")
        mono.setStyleHint(QFont.TypeWriter)
        mono.setPointSize(9)
        self._snippet.setFont(mono)
        self._snippet.setMinimumHeight(110)
        lay.addWidget(self._snippet)

        hint = QLabel(
            "<b>Then say &quot;KherveMol&quot; in the chat.</b> Claude "
            "only reaches for this window when you point it here. "
            "Try asking:<ul>"
            "<li><i>&quot;In KherveMol, show caffeine and tell me its "
            "formula and weight.&quot;</i></li>"
            "<li><i>&quot;In KherveMol, build Pt(111) with CO standing "
            "on it and render the result.&quot;</i></li>"
            "<li><i>&quot;In KherveMol, draw a twisted bilayer "
            "graphene at 13 degrees.&quot;</i></li>"
            "<li><i>&quot;In KherveMol, balance the combustion of "
            "propane and play the reaction.&quot;</i></li>"
            "<li><i>&quot;In KherveMol, turn the OH of this ethanol "
            "into NH2.&quot;</i></li></ul>"
            "Restart the application after connecting &mdash; it reads "
            "its tool list once at startup &mdash; and leave KherveMol "
            "running with the box above ticked.")
        hint.setWordWrap(True)
        lay.addWidget(hint)

        act_box = QGroupBox("Recent activity")
        act_lay = QVBoxLayout(act_box)
        self._activity = QListWidget()
        self._activity.setMaximumHeight(110)
        act_lay.addWidget(self._activity)
        lay.addWidget(act_box)

        btns = QDialogButtonBox(QDialogButtonBox.Close)
        copy = QPushButton("Copy")
        copy.clicked.connect(self._copy)
        btns.addButton(copy, QDialogButtonBox.ActionRole)
        btns.rejected.connect(self.reject)
        lay.addWidget(btns)

    # ── Behaviour ────────────────────────────────────────────────────

    def _on_bridge_started(self, _port: int):
        self._refresh()

    def _on_tool_invoked(self, name: str, outcome: str):
        self._activity.insertItem(0, f"{name} — {outcome}")
        while self._activity.count() > 50:
            self._activity.takeItem(self._activity.count() - 1)

    def _on_access_changed(self, index: int):
        level = ACCESS_LEVELS[index]
        self._bridge.set_access(level)
        QSettings(*SETTINGS).setValue("mcp/access", level)
        self._refresh_access_hint()

    def _on_toggled(self, on: bool):
        if on:
            if not self._bridge.start():
                self._enable.setChecked(False)
                self._status.setText(
                    "<b>Could not open a local port.</b> Another "
                    "process may be holding it.")
                return
        else:
            self._bridge.stop()
        QSettings(*SETTINGS).setValue("mcp/enabled", bool(on))
        self._refresh()

    def _refresh_access_hint(self):
        idx = self._access.currentIndex()
        text = _ACCESS_LABELS[idx][1]
        if ACCESS_LEVELS[idx] == "full":
            text += (" It can read and overwrite files anywhere you can, "
                     "so connect only applications you trust.")
        self._access_hint.setText(text)

    def _refresh(self):
        running = self._bridge.is_running()
        self._enable.blockSignals(True)
        self._enable.setChecked(running)
        self._enable.blockSignals(False)
        self._access.blockSignals(True)
        self._access.setCurrentIndex(
            ACCESS_LEVELS.index(self._bridge.access()))
        self._access.blockSignals(False)
        self._refresh_access_hint()
        self._activity.clear()
        for entry in reversed(self._bridge.log):
            self._activity.addItem(
                f"{entry['time']}  {entry['tool']} — {entry['outcome']}")
        if running:
            http = self._bridge.http_url()
            extra = f" &nbsp; HTTP: {http}" if http else ""
            self._status.setText(
                f"<b style='color:#2e7d32'>Listening</b> on "
                f"127.0.0.1:{self._bridge.port()}{extra}<br>"
                f"endpoint file: {endpoint_path()}")
        else:
            self._status.setText(
                "<b style='color:#b71c1c'>Stopped</b> — no assistant "
                "can reach this window.")
        self._refresh_snippet()
        self._refresh_hosts()

    # ── Host wiring ──────────────────────────────────────────────────

    def _selected_host(self):
        row = self._hosts.currentRow()
        return HOSTS[row] if 0 <= row < len(HOSTS) else None

    def _refresh_hosts(self):
        """Rebuild the host list, keeping the current selection."""
        row = max(self._hosts.currentRow(), 0)
        self._hosts.blockSignals(True)
        self._hosts.clear()
        for host in HOSTS:
            status = host.status()
            item = QListWidgetItem(f"{host.label} — {status}")
            if status.startswith("connected"):
                item.setForeground(Qt.darkGreen)
            elif status == "not installed":
                item.setForeground(Qt.gray)
            self._hosts.addItem(item)
        self._hosts.setCurrentRow(min(row, len(HOSTS) - 1))
        self._hosts.blockSignals(False)
        self._refresh_host_buttons()

    def _refresh_host_buttons(self):
        host = self._selected_host()
        if host is None:
            self._connect_btn.setEnabled(False)
            self._disconnect_btn.setEnabled(False)
            self._host_hint.clear()
            return
        connected = host.connected()
        self._connect_btn.setEnabled(not host.manual)
        self._connect_btn.setText(
            "Update entry" if connected and not host.up_to_date()
            else "Connect")
        self._disconnect_btn.setEnabled(connected and not host.manual)
        bits = []
        if host.manual:
            bits.append("Cannot be edited automatically.")
        bits.append(host.note)
        path = host.path()
        if path:
            bits.append(f"<i>{path}</i>")
        self._host_hint.setText("  ".join(b for b in bits if b))

    def _report(self, result: dict):
        """Show what a connect/disconnect actually did."""
        host = result.get("host", "host")
        if not result.get("ok"):
            QMessageBox.warning(self, "Connect to Claude", result.get(
                "error", f"Could not configure {host}."))
            self._refresh_hosts()
            return
        lines = [f"{host}: KherveMol {result.get('action', 'updated')}.",
                 f"File: {result.get('path', '')}"]
        if result.get("backup"):
            lines.append(f"Previous version saved as {result['backup']}")
        if result.get("restart"):
            lines.append(f"\nRestart {host} for it to take effect.")
        if result.get("action") != "removed":
            # The step with no visible cue: a correctly connected
            # assistant sits there doing nothing until a chat names
            # this application.
            lines.append(
                f"\nThen mention KherveMol in your chat with {host} "
                f"— say {DQ}in KherveMol, show caffeine{DQ} — and it "
                f"will work in this window.")
        QMessageBox.information(self, "Connect to Claude",
                                "\n".join(lines))
        self._refresh_hosts()

    def _require_running(self) -> bool:
        if self._bridge.is_running():
            return True
        QMessageBox.information(
            self, "Connect to Claude",
            "Tick 'Let assistants connect to KherveMol' "
            "first — the entry is only useful while "
            "KherveMol is listening.")
        return False

    def _on_connect(self):
        host = self._selected_host()
        if host is None or not self._require_running():
            return
        self._report(host.connect())

    def _on_other_host(self):
        """Add KherveMol to a config file the user points us at.

        The named entries cannot cover every MCP client, and guessing a
        path wrongly is worse than asking.
        """
        if not self._require_running():
            return
        path, _ = QFileDialog.getOpenFileName(
            self, "Choose the client's MCP config file", "",
            "JSON config (*.json);;All files (*)")
        if not path:
            return
        # Match the file's own convention rather than imposing ours:
        # most clients copied Claude Desktop's "mcpServers", VS Code
        # and its relatives use "servers".
        shape = "mcpServers"
        try:
            with open(path, "r", encoding="utf-8") as fh:
                doc = json.load(fh)
            if isinstance(doc, dict) and "servers" in doc \
                    and "mcpServers" not in doc:
                shape = "servers"
        except Exception:
            pass          # empty or unreadable: connect() reports it
        host = Host.for_file(path, shape=shape)
        if shape == "servers":
            host.entry_extra = {"type": "stdio"}
        self._report(host.connect())

    def _on_disconnect(self):
        host = self._selected_host()
        if host is None:
            return
        if QMessageBox.question(
                self, "Connect to Claude",
                f"Remove KherveMol from {host.label}'s configuration?\n"
                "Other servers are left untouched.",
                QMessageBox.Yes | QMessageBox.No) != QMessageBox.Yes:
            return
        self._report(host.disconnect())

    def _refresh_snippet(self):
        idx = self._flavour.currentIndex()
        if idx == 0:
            self._snippet.setPlainText(host_config())
        elif idx == 1:
            self._snippet.setPlainText(cli_command())
        else:
            self._snippet.setPlainText(self._http_snippet())

    def _http_snippet(self) -> str:
        """Endpoint and token for a client that only takes a URL."""
        url = self._bridge.http_url()
        if not url:
            return ("The HTTP endpoint is not listening.\n"
                    "Tick the box above.")
        return (
            f"URL      {url}\n"
            f"Transport  Streamable HTTP (POST JSON-RPC)\n"
            f"Header   Authorization: Bearer {self._bridge.token()}\n"
            "\n"
            "For clients that take an endpoint rather than a command —\n"
            "Open WebUI, n8n, and some IDE setups. The token changes\n"
            "every time the server is switched on, so re-copy it after\n"
            "restarting KherveMol.\n"
            "\n"
            "127.0.0.1 only: this is not reachable from another machine,\n"
            "and cloud assistants (ChatGPT, Le Chat, Grok) cannot use it.")

    def _copy(self):
        QApplication.clipboard().setText(self._snippet.toPlainText())


# -- Hooking into the main window ------------------------------------------

def bridge_for(window):
    """The window's MCP bridge (created by `install`), or None."""
    return getattr(window, "_mcp_bridge", None)


def _help_menu(window):
    for act in window.menuBar().actions():
        if act.text().replace("&", "").strip().lower() == "help":
            return act.menu()
    return window.menuBar().addMenu("&Help")


def install(window):
    """Give *window* its 'Connect to Claude (MCP)...' Help-menu action and
    re-open the bridge when the user left it enabled last session.

    Call once at the end of ``MainWindow.__init__``.  The bridge itself is
    off until the user ticks the box in the dialog; the choice is kept in
    QSettings so it survives a restart.  Returns the bridge.
    """
    existing = bridge_for(window)
    if existing is not None:
        return existing
    from .mcp_bridge import ACCESS_LEVELS, DEFAULT_ACCESS, McpBridge

    bridge = McpBridge(window)
    settings = QSettings(*SETTINGS)
    level = settings.value("mcp/access", DEFAULT_ACCESS)
    bridge.set_access(level if level in ACCESS_LEVELS else DEFAULT_ACCESS)
    window._mcp_bridge = bridge

    dialogs = []

    def open_dialog():
        # One live dialog at a time; it deletes itself when closed.
        dialogs[:] = [d for d in dialogs if d is not None and _alive(d)]
        if dialogs:
            dialogs[0].raise_()
            dialogs[0].activateWindow()
            return
        dlg = McpServerDialog(bridge, window)
        dlg.setAttribute(Qt.WA_DeleteOnClose)
        dialogs.append(dlg)
        dlg.show()

    action = QAction("Connect to Claude (MCP)\u2026", window)
    action.setToolTip("Let Claude Desktop, Claude Code, Cursor and other "
                      "assistants build and edit in this window")
    try:
        from . import icons
        action.setIcon(icons.icon("mdi.lan-connect"))
    except Exception:                          # noqa: BLE001
        pass
    action.triggered.connect(lambda _=False: open_dialog())
    menu = _help_menu(window)
    before = None
    for act in menu.actions():
        if act.text().replace("&", "").strip().lower().startswith("about"):
            before = act
            break
    if before is not None:
        menu.insertAction(before, action)
    else:
        menu.addAction(action)
    window._mcp_action = action

    # A permanent "Claude connected" note while the bridge is listening, so
    # the user always knows something can drive the window.
    note = QLabel("Claude: connected")
    note.setStyleSheet("color:#2e7d32; padding:0 6px;")
    note.setToolTip("An assistant may drive this window (Help > Connect to "
                    "Claude). Local only: 127.0.0.1.")
    note.setVisible(False)
    window.statusBar().addPermanentWidget(note)
    bridge.started.connect(lambda _p: note.setVisible(True))
    bridge.stopped.connect(lambda: note.setVisible(False))
    bridge.tool_invoked.connect(
        lambda name, _s: window.statusBar().showMessage(
            f"Claude: {name}", 3000))

    # The endpoint file names this process; it must go with it.
    app = QApplication.instance()
    if app is not None:
        app.aboutToQuit.connect(bridge.stop)

    # Re-open the bridge if the user left it on.  Never in a headless
    # (offscreen) run -- the test suite builds many windows and must not
    # publish an endpoint file for a developer's real session to trip over.
    if (settings.value("mcp/enabled", False, type=bool)
            and QGuiApplication.platformName() != "offscreen"):
        bridge.start()
    return bridge


def _alive(widget) -> bool:
    """False once Qt has deleted the widget under a stale Python ref."""
    try:
        widget.objectName()
        return True
    except RuntimeError:
        return False
