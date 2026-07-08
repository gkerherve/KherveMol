"""Connectivity-outline tests.

Copyright (C) 2026 Gwilherm Kerherve

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
"""

from khervemol import library, model
from khervemol.structure_tree import StructureTree, walk


def _rows(atoms, bonds):
    return list(walk(atoms, bonds))


def test_walk_covers_every_atom_exactly_once():
    m = library.make("ethanol")
    branches = [r for r in _rows(m.atoms, m.bonds) if not r[4]]
    assert sorted(r[0] for r in branches) == list(range(len(m.atoms)))


def test_walk_nests_children_under_their_parent():
    m = library.make("ethanol")
    seen = set()
    for atom, parent, _grand, _order, ring in _rows(m.atoms, m.bonds):
        if ring:
            continue
        if parent is not None:
            assert parent in seen               # parent always comes first
            assert model.bond_between(m.bonds, parent, atom) is not None
        seen.add(atom)


def test_walk_marks_ring_closures_once():
    m = library.make("benzene")
    rows = _rows(m.atoms, m.bonds)
    rings = [r for r in rows if r[4]]
    # a single six-ring closes exactly once; it is a leaf, not a branch
    assert len(rings) == 1
    branches = [r for r in rows if not r[4]]
    assert len(branches) == len(m.atoms)
    # every bond is accounted for: tree edges + ring closures
    tree_edges = sum(1 for r in branches if r[1] is not None)
    assert tree_edges + len(rings) == len(m.bonds)


def test_walk_reaches_disconnected_fragments():
    # ethanol with the C–C bond cut: both carbons become fragment roots
    m = library.make("ethanol")
    cs = [i for i, a in enumerate(m.atoms) if a[0] == "C"]
    m.bonds.pop(model.bond_between(m.bonds, *cs))
    rows = _rows(m.atoms, m.bonds)
    assert sorted(r[0] for r in rows if not r[4]) == list(range(len(m.atoms)))
    roots = [r[0] for r in rows if r[1] is None]
    assert sorted(roots) == sorted(cs)          # one root per fragment


def test_walk_records_bond_order_and_grandparent():
    m = library.make("formaldehyde")
    by_atom = {r[0]: r for r in _rows(m.atoms, m.bonds) if not r[4]}
    o = next(i for i, a in enumerate(m.atoms) if a[0] == "O")
    assert by_atom[o][3] == 2                   # C=O is a double bond
    hs = [i for i, a in enumerate(m.atoms) if a[0] == "H"]
    # the H rows hang off the carbon and have no grandparent (C is the root)
    assert all(by_atom[h][1] == by_atom[o][1] for h in hs)


def test_tree_widget_mirrors_the_molecule(qapp):
    t = StructureTree()
    t.set_molecule(library.make("ethanol"))
    root = t.topLevelItem(0)
    assert root.text(0) == "Ethanol"
    # every atom got a row, and lengths/angles are filled in below the root
    assert len(t._rows) == 9
    child = t._rows[1]                          # the second carbon
    assert child.text(1) == "–"                 # single bond
    assert child.text(2) == "1.54 Å"


def test_tree_widget_selection_round_trip(qapp):
    t = StructureTree()
    t.set_molecule(library.make("ethanol"))
    picked = []
    t.atom_selected.connect(picked.append)
    t.setCurrentItem(t._rows[3])
    assert picked == [3]
    # driving it from the viewer side must not echo back a signal
    t.show_atom(5)
    assert t.currentItem() is t._rows[5]
    assert picked == [3]


def test_tree_widget_survives_an_empty_molecule(qapp):
    t = StructureTree()
    t.set_molecule(model.Molecule(name="empty"))
    assert t.topLevelItemCount() == 0
    t.show_atom(0)                              # no row: must not raise
