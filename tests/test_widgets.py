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
    bonds_before = len(v.mol.bonds)
    v._on_atom_clicked(0)                      # select the carbon (full)
    v.add_element("O")                         # can't bond a full C…
    assert len(v.mol.bonds) == bonds_before    # …so no new bond is made
    # a fresh carbon has free valence: adding an O bonds it
    v.set_molecule(model.Molecule(atoms=[["C", 0.0, 0.0, 0.0]], name="c"))
    v._on_atom_clicked(0)
    v.order = 1
    v.add_element("O")
    assert len(v.mol.atoms) == 2 and len(v.mol.bonds) == 1


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


def _methanol_ish(v):
    from khervemol import model
    v.set_molecule(model.Molecule(atoms=[["C", 0.0, 0.0, 0.0]], name="c"))
    v._on_atom_clicked(0)
    v.order = 1
    v.add_element("O")                         # C–O, atom 1


def test_viewer_bond_order_menu_ops(qapp):
    from khervemol import model
    v = Viewer3D()
    _methanol_ish(v)
    assert v.bond_label(0).startswith("C–O")
    assert v.can_set_order(0, 2)
    v.set_bond_order(0, 2)                     # C=O, and it shortens
    assert v.mol.bonds[0][2] == 2
    assert v.bond_label(0).startswith("C=O")
    assert model.distance(v.mol.atoms, 0, 1) == 1.23
    # O has valence 2 — the triple is offered but disabled, and refused
    assert not v.can_set_order(0, 3)
    v.set_bond_order(0, 3)
    assert v.mol.bonds[0][2] == 2
    v.delete_bond(0)
    assert v.mol.bonds == [] and len(v.mol.atoms) == 2


def test_viewer_bond_element_from_context_menu(qapp):
    v = Viewer3D()
    _methanol_ish(v)
    # the O is full at order 2 but has one free valence for a single bond
    assert "H" in v.bondable(1, 1)
    assert v.bondable(1, 2) == []
    v.bond_element(1, "H", 1)
    assert v.mol.atoms[-1][0] == "H"
    assert [1, 2, 1] in v.mol.bonds
    assert v.order == 1                        # the combo's order is restored


def test_drag_holds_bond_lengths_when_locked(qapp):
    from khervemol import model
    v = Viewer3D()
    _methanol_ish(v)
    assert v.lock_lengths                      # on by default
    model.drag_atom(v.mol.atoms, 1, 300.0, 120.0, v.mol.az, v.mol.el,
                    v.mol.bond, 1.0, bonds=v.mol.bonds)
    assert abs(model.distance(v.mol.atoms, 0, 1) - 1.43) < 1e-3


def _two_fragments(v):
    """Ethanol with its C–C bond cut — two loose pieces, as on screen."""
    from khervemol import model
    v.set_molecule(library.make("ethanol"))
    cs = [i for i, a in enumerate(v.mol.atoms) if a[0] == "C"]
    v.delete_bond(model.bond_between(v.mol.bonds, *cs))
    return cs


def test_ctrl_select_then_bond_the_two_carbons(qapp):
    from khervemol import model
    v = Viewer3D()
    c1, c2 = _two_fragments(v)
    v.select_atom(c1)
    v.select_atom(c2, toggle=True)             # Ctrl+click
    assert v.selection == [c1, c2]
    assert v.selected == c2                    # last clicked is primary
    assert v.can_bond_selected(1) and v.join_btn.isEnabled()
    v.bond_selected(1)
    assert model.bond_between(v.mol.bonds, c1, c2) is not None
    assert abs(model.distance(v.mol.atoms, c1, c2) - 1.54) < 1e-9
    # ctrl+clicking a selected atom again drops it
    v.select_atom(c1)
    v.select_atom(c2, toggle=True)
    v.select_atom(c2, toggle=True)
    assert v.selection == [c1]


def test_bond_selected_refuses_and_explains(qapp):
    v = Viewer3D()
    v.set_molecule(library.make("methane"))    # C is full, H are full
    v.select_atom(1)
    v.select_atom(2, toggle=True)
    assert not v.can_bond_selected(1)
    v.bond_selected(1)
    assert len(v.mol.bonds) == 4               # nothing added
    assert "No free valence" in v.status.text()


def test_tab_steps_the_selection(qapp):
    v = Viewer3D()
    v.set_molecule(library.make("methane"))
    v.selected = None
    v.step_selection(1)
    assert v.selected == 0
    v.step_selection(1)
    assert v.selected == 1
    v.step_selection(-1)
    assert v.selected == 0
    v.step_selection(-1)                       # wraps around
    assert v.selected == len(v.mol.atoms) - 1
    assert len(v.selection) == 1               # Tab replaces, never extends


def test_pick_an_atom_on_screen_to_bond_it(qapp):
    from khervemol import model
    v = Viewer3D()
    c1, c2 = _two_fragments(v)
    v.start_pick(c1, 1)
    assert v.picking and "Esc to cancel" in v.status.text()
    v.select_atom(c2)                          # the pick click
    assert not v.picking
    assert model.bond_between(v.mol.bonds, c1, c2) is not None
    # Esc leaves pick mode without bonding
    c1, c2 = _two_fragments(v)
    v.start_pick(c1, 1)
    v.cancel_pick()
    assert not v.picking
    v.select_atom(c2)
    assert model.bond_between(v.mol.bonds, c1, c2) is None


def _drop(widget, mime, payload, pos=None):
    """Deliver a real drag-enter + drop through the widget's viewport."""
    from PyQt5.QtCore import QMimeData, QPoint, Qt
    from PyQt5.QtGui import QDragEnterEvent, QDropEvent
    from PyQt5.QtWidgets import QApplication
    md = QMimeData()
    md.setData(mime, payload)
    pos = pos or QPoint(60, 60)
    target = widget.viewport() if hasattr(widget, "viewport") else widget
    enter = QDragEnterEvent(pos, Qt.CopyAction, md, Qt.LeftButton, Qt.NoModifier)
    QApplication.sendEvent(target, enter)
    drop = QDropEvent(pos, Qt.CopyAction, md, Qt.LeftButton, Qt.NoModifier)
    QApplication.sendEvent(target, drop)
    return enter.isAccepted(), drop.isAccepted()


def test_library_leaf_offers_a_draggable_payload(qapp):
    from PyQt5.QtCore import Qt
    from khervemol import dnd
    from khervemol.mainwindow import MainWindow
    w = MainWindow()

    def first_leaf(item):
        for k in range(item.childCount()):
            child = item.child(k)
            if child.data(0, Qt.UserRole):
                return child
            found = first_leaf(child)
            if found:
                return found
    leaf = first_leaf(w.tree.topLevelItem(0))
    assert leaf.flags() & Qt.ItemIsDragEnabled
    md = w.tree.mimeData([leaf])
    assert md.formats() == [dnd.MIME_COMPOUND]
    assert dnd.decode(md.data(dnd.MIME_COMPOUND))[0] == "model"


def test_drop_a_library_compound_on_the_3d_view(qapp):
    from khervemol import dnd, model
    from khervemol.mainwindow import MainWindow
    w = MainWindow()
    w.viewer.set_molecule(library.make("methane"))
    before = len(w.viewer.mol.atoms)
    enter, drop = _drop(w.viewer.view, dnd.MIME_COMPOUND,
                        dnd.encode("model", "water"))
    assert enter and drop
    # water merged in as a second, unbonded fragment
    assert len(w.viewer.mol.atoms) == before + 3
    assert w.viewer.mol.formula() == "CH6O"
    frag = model.fragment(w.viewer.mol.bonds, before, -1)
    assert len(frag) == 3 and not frag & set(range(before))


def test_drop_on_an_empty_3d_view_loads_the_compound(qapp):
    from khervemol import dnd, model
    from khervemol.mainwindow import MainWindow
    w = MainWindow()
    w.viewer.set_molecule(model.Molecule(name="empty"))
    _drop(w.viewer.view, dnd.MIME_COMPOUND, dnd.encode("model", "benzene"))
    assert w.viewer.mol.name == "benzene"
    # a crystal is replaced, never merged — a lattice has no room for a guest
    w.viewer.set_molecule(library.make("nacl"))
    _drop(w.viewer.view, dnd.MIME_COMPOUND, dnd.encode("model", "water"))
    assert w.viewer.mol.name == "water" and not w.viewer.mol.crystal


def test_drop_a_library_compound_on_the_2d_canvas(qapp):
    from khervemol import dnd
    from khervemol.mainwindow import MainWindow
    w = MainWindow()
    before = len(w.sketch.atoms)
    enter, drop = _drop(w.sketch.canvas, dnd.MIME_COMPOUND,
                        dnd.encode("model", "water"))
    assert enter and drop
    assert len(w.sketch.atoms) == before + 1        # the O (H are implicit)
    assert w.tabs.currentIndex() == 1               # and it shows you the tab


def test_drag_a_tree_row_onto_another_rebonds_it(qapp):
    from khervemol import model
    from khervemol.mainwindow import MainWindow
    w = MainWindow()
    atoms, bonds = model.single_atom("C")
    c1 = model.add_bonded_atom(atoms, bonds, 0, "C", 1)
    c2 = model.add_bonded_atom(atoms, bonds, c1, "C", 1)
    w.viewer.set_molecule(model.Molecule(atoms=atoms, bonds=bonds, name="c3"))
    # the outline roots on one end of the chain; drag the *other* end across
    moving = next(a for a in (0, c2) if w.structure.parent_of(a) is not None)
    anchor = c2 if moving == 0 else 0
    assert w.structure.parent_of(moving) == c1
    w.structure.reattach_requested.emit(moving, anchor)
    assert model.bond_between(w.viewer.mol.bonds, moving, c1) is None
    assert model.bond_between(w.viewer.mol.bonds, moving, anchor) is not None
    assert abs(model.distance(w.viewer.mol.atoms, moving, anchor) - 1.54) < 1e-9
    assert w.viewer.selected == moving


def test_tree_drag_refuses_an_impossible_drop(qapp):
    from khervemol import model
    from khervemol.mainwindow import MainWindow
    w = MainWindow()
    w.viewer.set_molecule(library.make("methane"))
    hs = [i for i, a in enumerate(w.viewer.mol.atoms) if a[0] == "H"]
    before = [list(b) for b in w.viewer.mol.bonds]
    w.structure.reattach_requested.emit(hs[0], hs[1])   # H has no free valence
    assert w.viewer.mol.bonds == before
    assert "No free valence" in w.viewer.status.text()


def test_bond_specs_are_tagged_for_hit_testing(qapp):
    v = Viewer3D()
    _methanol_ish(v)
    specs = v.render_specs(400, 400)
    assert any(s.get("_bond") == 0 for s in specs)
    assert any(s.get("_atom") == 1 for s in specs)
    # export specs stay untagged
    assert not any("_bond" in s for s in v.export_specs())


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
