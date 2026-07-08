"""Connectivity-outline tests.

Copyright (C) 2026 Gwilherm Kerherve

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
"""

from khervemol import library, model
from khervemol.structure_tree import (_ATOM_ROLE, _RING_ROLE, StructureTree,
                                      walk)


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
    assert len(t._rows) == 9                    # every atom got a row
    c1 = t._rows[1]                             # the CH2, one along the chain
    assert c1.text(1) == "–"                    # single bond
    assert c1.text(2) == "1.43 Å"               # C–O, the real length
    c0 = t._rows[0]                             # the methyl carbon
    assert c0.text(2) == "1.54 Å"
    assert c0.text(3) == "109.5°"               # a real bond angle


def _depths(t):
    """atom index → how deep its row sits under the molecule row."""
    out = {}

    def rec(item, depth):
        atom = item.data(0, _ATOM_ROLE)
        if atom is not None and not item.data(0, _RING_ROLE):
            out[int(atom)] = depth
        for k in range(item.childCount()):
            rec(item.child(k), depth + 1)

    rec(t.topLevelItem(0), 0)
    return out


def test_an_unbranched_chain_renders_as_a_flat_list(qapp):
    """A straight chain must not stair-step one indent per atom."""
    atoms, bonds = model.single_atom("C")
    for _ in range(8):
        model.add_bonded_atom(atoms, bonds, len(atoms) - 1, "C", 1)
    t = StructureTree()
    t.set_molecule(model.Molecule(atoms=atoms, bonds=bonds, name="chain"))
    depths = _depths(t)
    assert len(depths) == 9
    assert set(depths.values()) == {1}          # every carbon at one indent
    assert t.topLevelItem(0).childCount() == 9


def test_branches_nest_but_the_backbone_stays_flat(qapp):
    t = StructureTree()
    t.set_molecule(library.make("butane"))
    depths = _depths(t)
    carbons = [i for i in range(4)]
    assert {depths[c] for c in carbons} == {1}  # the four backbone carbons
    hydrogens = [i for i in depths if i not in carbons]
    assert {depths[h] for h in hydrogens} == {2}    # their H nest one deeper


def test_tree_roots_on_a_chain_end(qapp):
    t = StructureTree()
    t.set_molecule(library.make("butane"))
    root_atom = t.topLevelItem(0).child(0).data(0, _ATOM_ROLE)
    assert root_atom in (0, 3)                  # a terminal carbon, not a middle


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


def test_can_drop_rejects_impossible_rebonds(qapp):
    atoms, bonds = model.single_atom("C")
    c1 = model.add_bonded_atom(atoms, bonds, 0, "C", 1)
    c2 = model.add_bonded_atom(atoms, bonds, c1, "C", 1)
    t = StructureTree()
    t.set_molecule(model.Molecule(atoms=atoms, bonds=bonds, name="c3"))
    moving = next(a for a in (0, c2) if t.parent_of(a) is not None)
    anchor = c2 if moving == 0 else 0
    assert t.can_drop(moving, anchor)               # across the chain: fine
    assert not t.can_drop(moving, moving)           # onto itself
    assert not t.can_drop(moving, None)             # onto blank space
    assert not t.can_drop(c1, moving)               # onto its own subtree


def test_can_drop_rejects_a_full_anchor_and_a_crystal(qapp):
    t = StructureTree()
    t.set_molecule(library.make("methane"))
    hs = [i for i, a in enumerate(t._mol.atoms) if a[0] == "H"]
    assert not t.can_drop(hs[0], hs[1])             # H has no free valence
    assert not t.can_drop(hs[0], 0)                 # that is its current bond
    t.set_molecule(library.make("nacl"))
    assert not t.can_drop(0, 1)                     # a lattice is not editable


def test_tree_widget_survives_an_empty_molecule(qapp):
    t = StructureTree()
    t.set_molecule(model.Molecule(name="empty"))
    assert t.topLevelItemCount() == 0
    t.show_atom(0)                              # no row: must not raise
