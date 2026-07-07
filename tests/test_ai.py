"""AI assistant tests — parsing and crash-safety (no network).

Copyright (C) 2026 Gwilherm Kerherve

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
"""

import pytest

from khervemol import ai_assistant


@pytest.mark.parametrize("reply,expected", [
    ("Sure! SMILES: CCO", "CCO"),
    ("Benzene:\nSMILES: c1ccccc1\ndone", "c1ccccc1"),
    ("SMILES: `CC(=O)O`", "CC(=O)O"),
    ("```smiles\nCC(=O)O\n```", "CC(=O)O"),
    ("just prose, no molecule", None),
    ("SMILES: CCO.", "CCO"),
])
def test_extract_smiles(reply, expected):
    assert ai_assistant.extract_smiles(reply) == expected


def test_dock_builds_and_survives_no_key(qapp):
    from khervemol.mainwindow import MainWindow
    from PyQt5.QtCore import QSettings
    w = MainWindow()
    assert hasattr(w, "ai_dock")
    s = QSettings("Kherve", "KherveMol")
    s.setValue("ai/provider", "Claude")
    s.remove("ai/key/Claude")
    # sending with no API key must warn in-chat, never raise / crash
    w.ai_dock._input.setPlainText("hello")
    w.ai_dock._send()
    assert w.ai_dock._worker is None            # never started a request


def test_dock_reply_and_error_are_safe(qapp):
    from khervemol.mainwindow import MainWindow
    w = MainWindow()
    # a reply carrying a SMILES must not raise (renders if RDKit present,
    # otherwise notes that it's needed)
    w.ai_dock._on_reply("Ethanol.\nSMILES: CCO")
    # a network error must not raise
    w.ai_dock._on_error("HTTP 401: bad key")
