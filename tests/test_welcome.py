"""welcome.WelcomeScreen and its wiring into MainWindow: the start screen
shown until a molecule is on screen, and the recent-files list on it.

Copyright (C) 2026 Gwilherm Kerherve

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
"""

import os
import tempfile

from PyQt5.QtCore import QSettings

from khervemol import recent, style
from khervemol.welcome import WelcomeScreen


def _snapshot():
    return QSettings(*style._SETTINGS).value(recent._KEY, [])


def _restore(saved):
    QSettings(*style._SETTINGS).setValue(recent._KEY, saved)


# ------------------------------------------------------------- WelcomeScreen
def test_empty_state_shows_placeholder(qapp):
    saved = _snapshot()
    try:
        recent.clear()
        w = WelcomeScreen()
        assert w._recent_box.count() == 1
        assert w._recent_box.itemAt(0).widget() is w._empty_label
    finally:
        _restore(saved)


def test_refresh_lists_recent_files_newest_first(qapp):
    saved = _snapshot()
    try:
        recent.clear()
        with tempfile.NamedTemporaryFile(suffix=".kmol") as f1, \
                tempfile.NamedTemporaryFile(suffix=".kmol") as f2:
            recent.add(f1.name)
            recent.add(f2.name)
            w = WelcomeScreen()
            rows = [w._recent_box.itemAt(i).widget()
                    for i in range(w._recent_box.count())]
            assert [r.path for r in rows] == [os.path.abspath(f2.name),
                                              os.path.abspath(f1.name)]
    finally:
        _restore(saved)


def test_row_click_emits_path_chosen(qapp):
    saved = _snapshot()
    try:
        recent.clear()
        with tempfile.NamedTemporaryFile(suffix=".kmol") as f1:
            recent.add(f1.name)
            w = WelcomeScreen()
            row = w._recent_box.itemAt(0).widget()
            got = []
            w.path_chosen.connect(got.append)
            row.chosen.emit(row.path)
            assert got == [os.path.abspath(f1.name)]
    finally:
        _restore(saved)


def test_forgetting_a_row_removes_it_and_persists(qapp):
    saved = _snapshot()
    try:
        recent.clear()
        with tempfile.NamedTemporaryFile(suffix=".kmol") as f1:
            recent.add(f1.name)
            w = WelcomeScreen()
            row = w._recent_box.itemAt(0).widget()
            row.forgotten.emit(row.path)
            assert recent.list_paths() == []
            assert w._recent_box.itemAt(0).widget() is w._empty_label
    finally:
        _restore(saved)


# ------------------------------------------------------------- MainWindow
def test_window_opens_on_the_start_screen(qapp):
    from khervemol.mainwindow import MainWindow
    w = MainWindow()
    assert w._central.currentWidget() is w.welcome
    assert w.viewer.mol.atoms == []


def test_loading_a_molecule_switches_to_the_workspace(qapp):
    from khervemol.mainwindow import MainWindow
    w = MainWindow()
    w.load_entry("model", "ethanol", "Ethanol")
    assert w._central.currentWidget() is w.tabs


def test_start_screen_action_returns_to_welcome(qapp):
    from khervemol.mainwindow import MainWindow
    w = MainWindow()
    w.load_entry("model", "ethanol", "Ethanol")
    assert w._central.currentWidget() is w.tabs
    w._show_welcome()
    assert w._central.currentWidget() is w.welcome


def test_recent_file_row_opens_through_the_window(qapp, tmp_path):
    from khervemol.mainwindow import MainWindow
    saved = _snapshot()
    try:
        recent.clear()
        w = MainWindow()
        w.load_entry("model", "ethanol", "Ethanol")
        path = str(tmp_path / "ethanol.kmol")
        w._write(path)
        w._show_welcome()
        row = w.welcome._recent_box.itemAt(0).widget()
        assert row.path == os.path.abspath(path)
        row.chosen.emit(row.path)
        assert w._central.currentWidget() is w.tabs
        assert w._path == path
    finally:
        _restore(saved)
