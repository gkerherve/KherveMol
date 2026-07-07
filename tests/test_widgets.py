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


def test_mainwindow_loads(qapp):
    from khervemol.mainwindow import MainWindow
    w = MainWindow()
    w.load_model("benzene")
    assert w.viewer.mol.name == "benzene"
    w.flatten_to_2d()
    assert len(w.sketch.atoms) == len(w.viewer.mol.atoms)
