"""Multi-molecule 2D construction: drag-drop, fragments, geometry, sync.

Copyright (C) 2026 Gwilherm Kerherve

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
"""

import math

from PyQt5.QtCore import QPointF, Qt
from PyQt5.QtWidgets import QTreeWidgetItem

from khervemol.editor2d import _DND_MIME, _BOND_LEN, Editor2D


def _fragments(sketch):
    c = sketch.canvas
    seen, n = set(), 0
    for i in range(len(sketch.atoms)):
        if i not in seen:
            n += 1
            seen |= c._component(i)
    return n


def test_library_tree_mimedata(qapp):
    from khervemol.mainwindow import _LibraryTree
    t = _LibraryTree()
    it = QTreeWidgetItem(["Ethanol"])
    it.setData(0, Qt.UserRole, ("model", "ethanol"))
    t.addTopLevelItem(it)
    md = t.mimeData([it])
    assert md.hasFormat(_DND_MIME)
    assert bytes(md.data(_DND_MIME)).decode() == "model|ethanol"


def test_drop_adds_fragment(qapp):
    from khervemol.mainwindow import MainWindow
    w = MainWindow()
    w.load_entry("model", "ethanol", "Ethanol")   # off the start screen
    before = len(w.sketch.atoms)
    w._on_drop_molecule("model", "benzene", 300, 100)
    assert len(w.sketch.atoms) > before
    assert w._sketch_dirty
    assert _fragments(w.sketch) >= 2         # original + dropped molecule


def test_dirty_guard_protects_sketch(qapp):
    from khervemol.mainwindow import MainWindow
    w = MainWindow()
    w._on_drop_molecule("model", "benzene", 200, 100)
    n = len(w.sketch.atoms)
    w._sync_sketch(force=False)              # skipped: sketch is dirty
    assert len(w.sketch.atoms) == n
    w._sync_sketch(force=True)               # explicit resync clears dirty
    assert not w._sketch_dirty


def test_bond_geometry_snaps(qapp):
    e = Editor2D()
    e.set_structure([["C", 0, 0]], [])
    idx = e.canvas._new_bonded_atom(0, QPointF(40, 5))
    a = e.atoms[idx]
    assert abs(math.hypot(a[1], a[2]) - _BOND_LEN) < 1e-6      # fixed length
    assert round(math.degrees(math.atan2(a[2], a[1]))) % 30 == 0   # 30° step


def test_move_selects_whole_fragment(qapp):
    e = Editor2D()
    e.set_structure([["C", 0, 0], ["C", 46, 0], ["O", 300, 0]], [[0, 1, 1]])
    assert e.canvas._component(0) == {0, 1}   # the C–C fragment, not the O


def test_bond_two_fragments(qapp):
    e = Editor2D()
    e.set_structure([["C", 0, 0], ["C", 300, 0]], [])   # two lone carbons
    assert _fragments(e) == 2
    e.canvas._add_or_cycle_bond(0, 1)                    # Draw across fragments
    assert e.bonds == [[0, 1, 1]]
    assert _fragments(e) == 1                            # now one molecule
