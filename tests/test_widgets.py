"""Smoke tests for the interactive widgets and main window.

Copyright (C) 2026 Gwilherm Kerherve

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
"""

from khervemol import library
from khervemol.editor2d import Editor2D
from khervemol.viewer3d import Viewer3D


def test_viewer_builds_atom(qapp):
    from khervemol import model
    v = Viewer3D()
    v.set_molecule(library.make("methane"))
    before = len(v.mol.atoms)
    v._on_atom_clicked(0)                      # select the carbon (full)
    v.add_element("O")                         # blocked by valence
    assert len(v.mol.atoms) == before
    # a fresh carbon has free valence: adding an O succeeds
    v.set_molecule(model.Molecule(atoms=[["C", 0.0, 0.0, 0.0]], name="c"))
    v._on_atom_clicked(0)
    v.order = 1
    v.add_element("O")
    assert len(v.mol.atoms) == 2


def test_any_element_can_be_added(qapp):
    from khervemol import model
    v = Viewer3D()
    # metals, lanthanides/actinides, and noble gases are all placeable —
    # bonded where chemistry allows, else as a free atom
    for el in ("Fe", "Ce", "U", "Au", "Na", "Xe", "Kr", "He", "Ne"):
        v.set_molecule(model.Molecule(atoms=[["C", 0.0, 0.0, 0.0]], name="c"))
        v._on_atom_clicked(0)
        v.order = 1
        before = len(v.mol.atoms)
        v.add_element(el)
        assert len(v.mol.atoms) == before + 1, el
    # Xe/Kr form bonds; He is inert (placed unbonded)
    v.set_molecule(model.Molecule(atoms=[["C", 0.0, 0.0, 0.0]], name="c"))
    v._on_atom_clicked(0)
    v.add_element("Xe")
    assert v.mol.bonds


def test_viewer_crystal_not_editable(qapp):
    v = Viewer3D()
    v.set_molecule(library.make("nacl"))
    assert not v.editable


def test_editor2d_draw_and_bond(qapp):
    e = Editor2D()
    e.set_structure([["C", 0, 0], ["O", 50, 0]], [])
    e.canvas._add_or_cycle_bond(0, 1)
    assert e.bonds == [[0, 1, 1]]
    e.canvas._add_or_cycle_bond(0, 1)          # cycles order
    assert e.bonds == [[0, 1, 2]]
    assert e.formula() == "CO"


def test_mainwindow_loads_and_syncs_2d(qapp):
    from khervemol.mainwindow import MainWindow
    w = MainWindow()
    w.load_model("benzene")
    assert w.viewer.mol.name == "benzene"
    # loading a 3D model auto-mirrors it into the 2D sketch as a skeletal
    # structure — heavy atoms only (hydrogens implicit)
    heavy = sum(1 for a in w.viewer.mol.atoms if a[0] != "H")
    assert len(w.sketch.atoms) == heavy
    assert all(a[0] != "H" for a in w.sketch.atoms)
    assert w.sketch.bonds


def test_sketch_tool_switch(qapp):
    from khervemol.editor2d import Editor2D
    e = Editor2D()
    e.set_tool("erase")
    assert e.tool == "erase"


def test_library_tree_includes_catalog(qapp):
    from PyQt5.QtCore import Qt
    from khervemol.mainwindow import MainWindow
    w = MainWindow()

    def leaves(it):
        n = 1 if it.data(0, Qt.UserRole) is not None else 0
        for i in range(it.childCount()):
            n += leaves(it.child(i))
        return n
    total = sum(leaves(w.tree.topLevelItem(i))
                for i in range(w.tree.topLevelItemCount()))
    assert total > 300                              # models + 328 catalog


def test_sketch_valence_enforced(qapp):
    from khervemol.editor2d import Editor2D
    e = Editor2D()
    # oxygen (valence 2) already has a double bond → no extra bond allowed
    e.set_structure([["O", 0, 0], ["C", 50, 0], ["C", 0, 50]], [[0, 1, 2]])
    e.canvas._add_or_cycle_bond(0, 2)
    assert e.bonds == [[0, 1, 2]]
    # cycling a C–O bond maxes at double (O can't take a triple), then wraps
    e.set_structure([["C", 0, 0], ["O", 50, 0]], [[0, 1, 1]])
    e.canvas._cycle_order(0)
    assert e.bonds == [[0, 1, 2]]
    e.canvas._cycle_order(0)
    assert e.bonds == [[0, 1, 1]]


def test_perovskite_and_new_crystals(qapp):
    for key in ("perovskite", "zincblende", "fluorite"):
        mol = library.make(key)
        assert mol.crystal and mol.edges, key
    # perovskite has the central TiO6 octahedron bonds
    assert library.make("perovskite").bonds
