"""Geometry engine + builder tests.

Copyright (C) 2026 Gwilherm Kerherve

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
"""

import pytest

from khervemol import elements, model


def test_bond_lengths_are_chemical():
    assert elements.bond_length("C", "O", 1) == 1.43
    assert elements.bond_length("O", "C", 2) == 1.23      # symmetric
    assert elements.bond_length("C", "C", 3) == 1.20
    # unlisted pair → covalent-radius sum, shortened by order
    assert elements.bond_length("Se", "Se", 1) == 2.40
    assert elements.bond_length("Se", "Se", 2) < 2.40


def test_added_atom_sits_at_the_ideal_length():
    atoms, bonds = model.single_atom("C")
    i = model.add_bonded_atom(atoms, bonds, 0, "O", 2)
    assert model.distance(atoms, 0, i) == pytest.approx(1.23, abs=1e-6)


def test_drag_swings_a_bond_without_stretching_it():
    atoms, bonds = model.single_atom("C")
    i = model.add_bonded_atom(atoms, bonds, 0, "O", 1)
    # yank the O far away; the constraint pulls it back onto the C–O sphere
    model.drag_atom(atoms, i, 200.0, 90.0, 0.0, 0.0, 1.0, 1.0, bonds=bonds)
    assert model.distance(atoms, 0, i) == pytest.approx(1.43, abs=1e-3)
    # without the bond list the drag is free
    model.drag_atom(atoms, i, 200.0, 90.0, 0.0, 0.0, 1.0, 1.0)
    assert model.distance(atoms, 0, i) > 2.0


def test_constrain_atom_balances_several_bonds():
    # formaldehyde: nudge the central C off its ideal spot, then constrain —
    # all three bonds must come back to length at once.
    atoms, bonds = model.single_atom("C")
    model.add_bonded_atom(atoms, bonds, 0, "H", 1)
    model.add_bonded_atom(atoms, bonds, 0, "H", 1)
    model.add_bonded_atom(atoms, bonds, 0, "O", 2)
    atoms[0][1] += 0.30
    atoms[0][2] -= 0.20
    atoms[0][3] += 0.15
    model.constrain_atom(atoms, bonds, 0)
    for k, target in ((1, 1.09), (2, 1.09), (3, 1.23)):
        assert model.distance(atoms, 0, k) == pytest.approx(target, abs=1e-3)


def test_set_bond_order_relengthens_and_respects_valence():
    atoms, bonds = model.single_atom("C")
    i = model.add_bonded_atom(atoms, bonds, 0, "O", 1)
    assert model.distance(atoms, 0, i) == pytest.approx(1.43, abs=1e-6)
    assert model.set_bond_order(atoms, bonds, 0, 2)
    assert bonds[0][2] == 2
    assert model.distance(atoms, 0, i) == pytest.approx(1.23, abs=1e-6)
    # O has valence 2 — a triple C≡O will not fit
    assert not model.can_set_bond_order(atoms, bonds, 0, 3)
    assert not model.set_bond_order(atoms, bonds, 0, 3)
    assert bonds[0][2] == 2


def test_relax_bond_moves_the_smaller_side_only():
    atoms, bonds = model.single_atom("C")
    model.add_bonded_atom(atoms, bonds, 0, "H", 1)
    model.add_bonded_atom(atoms, bonds, 0, "H", 1)
    o = model.add_bonded_atom(atoms, bonds, 0, "O", 1)
    before = [list(a) for a in atoms]
    model.set_bond_order(atoms, bonds, 2, 2)         # the C–O bond
    assert atoms[:3] == before[:3]                   # C and both H stay put
    assert atoms[o] != before[o]                     # the lone O slides in


def test_relax_bond_leaves_a_ring_alone():
    atoms = [["C", 0.0, 0.0, 0.0], ["C", 1.5, 0.0, 0.0], ["C", 0.75, 1.3, 0.0]]
    bonds = [[0, 1, 1], [1, 2, 1], [2, 0, 1]]
    before = [list(a) for a in atoms]
    model.relax_bond(atoms, bonds, 0)
    assert atoms == before


def test_fragment_splits_at_a_bond():
    atoms, bonds = model.single_atom("C")
    model.add_bonded_atom(atoms, bonds, 0, "H", 1)
    c2 = model.add_bonded_atom(atoms, bonds, 0, "C", 1)
    model.add_bonded_atom(atoms, bonds, c2, "H", 1)
    assert model.fragment(bonds, c2, 1) == {2, 3}     # across the C–C bond
    assert model.fragment(bonds, 0, 1) == {0, 1}


def test_angle_and_bond_between():
    atoms = [["O", 0.0, 0.0, 0.0], ["H", 1.0, 0.0, 0.0], ["H", 0.0, 1.0, 0.0]]
    bonds = [[0, 1, 1], [0, 2, 1]]
    assert model.angle(atoms, 1, 0, 2) == pytest.approx(90.0)
    assert model.angle(atoms, 2, 0, 1) == pytest.approx(90.0)   # symmetric
    assert model.bond_between(bonds, 2, 0) == 1
    assert model.bond_between(bonds, 1, 2) is None


def test_add_bond_joins_two_fragments_at_the_right_length():
    # two methyl-ish fragments, far apart and unbonded
    atoms = [["C", 0.0, 0.0, 0.0], ["H", 1.09, 0.0, 0.0],
             ["C", 9.0, 0.0, 0.0], ["H", 10.09, 0.0, 0.0]]
    bonds = [[0, 1, 1], [2, 3, 1]]
    assert model.can_bond(atoms, bonds, 0, 2, 1)
    assert model.add_bond(atoms, bonds, 0, 2, 1)
    assert model.distance(atoms, 0, 2) == pytest.approx(1.54, abs=1e-6)
    # the moved fragment kept its own geometry
    assert model.distance(atoms, 2, 3) == pytest.approx(1.09, abs=1e-6)
    # …and cannot be bonded twice
    assert not model.can_bond(atoms, bonds, 0, 2, 1)
    assert not model.add_bond(atoms, bonds, 2, 0, 1)


def test_add_bond_refuses_without_free_valence():
    atoms, bonds = model.single_atom("O")
    a = model.add_bonded_atom(atoms, bonds, 0, "H", 1)
    b = model.add_bonded_atom(atoms, bonds, 0, "H", 1)
    assert not model.can_bond(atoms, bonds, a, b, 1)     # both H are full
    assert not model.add_bond(atoms, bonds, a, b, 1)
    assert len(bonds) == 2


def test_add_bond_closing_a_ring_leaves_geometry_alone():
    atoms = [["C", 0.0, 0.0, 0.0], ["C", 1.5, 0.0, 0.0], ["C", 0.75, 1.3, 0.0]]
    bonds = [[0, 1, 1], [1, 2, 1]]
    before = [list(a) for a in atoms]
    assert model.add_bond(atoms, bonds, 2, 0, 1)         # closes the ring
    assert atoms == before
    assert len(bonds) == 3


def test_merge_appends_a_clear_fragment():
    atoms = [["C", 0.0, 0.0, 0.0], ["H", 1.09, 0.0, 0.0]]
    bonds = [[0, 1, 1]]
    base = model.merge(atoms, bonds, [["O", 0.0, 0.0, 0.0],
                                      ["H", 0.96, 0.0, 0.0]], [[0, 1, 1]])
    assert base == 2 and len(atoms) == 4
    assert bonds == [[0, 1, 1], [2, 3, 1]]          # re-indexed
    # the incoming fragment keeps its shape and is clear of the first
    assert model.distance(atoms, 2, 3) == pytest.approx(0.96)
    assert min(a[1] for a in atoms[2:]) > max(a[1] for a in atoms[:2])


def test_reattach_moves_an_atom_and_its_fragment():
    # propane-ish: C0–C1–C2, with an H on C2
    atoms, bonds = model.single_atom("C")
    c1 = model.add_bonded_atom(atoms, bonds, 0, "C", 1)
    c2 = model.add_bonded_atom(atoms, bonds, c1, "C", 1)
    h = model.add_bonded_atom(atoms, bonds, c2, "H", 1)
    old = model.bond_between(bonds, c2, c1)
    assert model.can_reattach(atoms, bonds, c2, old, 0)
    assert model.reattach(atoms, bonds, c2, old, 0)
    assert model.bond_between(bonds, c2, c1) is None
    assert model.bond_between(bonds, c2, 0) is not None
    assert model.distance(atoms, 0, c2) == pytest.approx(1.54, abs=1e-6)
    # the H came along, still bonded and still at the right length
    assert model.bond_between(bonds, c2, h) is not None
    assert model.distance(atoms, c2, h) == pytest.approx(1.09, abs=1e-6)


def test_reattach_refuses_to_bond_a_fragment_to_itself():
    atoms, bonds = model.single_atom("C")
    c1 = model.add_bonded_atom(atoms, bonds, 0, "C", 1)
    c2 = model.add_bonded_atom(atoms, bonds, c1, "C", 1)
    old = model.bond_between(bonds, c1, 0)
    # dropping C1 onto C2 — but C2 hangs off C1, so it would travel with it
    assert not model.can_reattach(atoms, bonds, c1, old, c2)
    assert not model.reattach(atoms, bonds, c1, old, c2)
    assert len(bonds) == 2                          # nothing was broken


def test_reattach_refuses_without_free_valence():
    atoms, bonds = model.single_atom("C")
    o = model.add_bonded_atom(atoms, bonds, 0, "O", 1)
    model.add_bonded_atom(atoms, bonds, o, "H", 1)  # the O is now full
    h = model.add_bonded_atom(atoms, bonds, 0, "H", 1)
    old = model.bond_between(bonds, h, 0)
    assert not model.reattach(atoms, bonds, h, old, o)
    assert model.bond_between(bonds, h, 0) is not None   # still where it was


def test_reattach_without_a_parent_just_bonds():
    atoms = [["C", 0.0, 0.0, 0.0], ["C", 9.0, 0.0, 0.0]]
    bonds = []
    assert model.reattach(atoms, bonds, 1, None, 0)
    assert bonds == [[0, 1, 1]]
    assert model.distance(atoms, 0, 1) == pytest.approx(1.54, abs=1e-6)


def test_delete_bond_keeps_atoms():
    atoms, bonds = model.single_atom("C")
    model.add_bonded_atom(atoms, bonds, 0, "O", 1)
    model.delete_bond(bonds, 0)
    assert bonds == []
    assert len(atoms) == 2


def test_single_atom():
    atoms, bonds = model.single_atom("C")
    assert atoms == [["C", 0.0, 0.0, 0.0]]
    assert bonds == []


def test_valence_tracking():
    atoms, bonds = model.single_atom("C")
    assert model.free_valence(atoms, bonds, 0) == 4
    model.add_bonded_atom(atoms, bonds, 0, "H", 1)
    assert model.free_valence(atoms, bonds, 0) == 3
    model.add_bonded_atom(atoms, bonds, 0, "O", 2)
    assert model.free_valence(atoms, bonds, 0) == 1


def test_delete_atom_reindexes_bonds():
    atoms, bonds = model.single_atom("C")
    i1 = model.add_bonded_atom(atoms, bonds, 0, "H", 1)
    i2 = model.add_bonded_atom(atoms, bonds, 0, "O", 1)
    assert (i1, i2) == (1, 2)
    model.delete_atom(atoms, bonds, 1)          # remove the H
    # only the C-O bond survives, re-indexed
    assert len(atoms) == 2
    assert bonds == [[0, 1, 1]]


def test_formula_hill_order():
    m = model.Molecule(
        atoms=[["C", 0, 0, 0], ["O", 1, 0, 0], ["H", 2, 0, 0],
               ["H", 3, 0, 0]])
    assert m.formula() == "C H2 O".replace(" ", "")


def test_specs_are_generated(qapp):
    atoms, bonds = model.single_atom("C")
    model.add_bonded_atom(atoms, bonds, 0, "O", 2)
    m = model.Molecule(atoms=atoms, bonds=bonds)
    specs = m.specs(400, 400)
    circles = [s for s in specs if s["shape"] == "circle"]
    lines = [s for s in specs if s["shape"] == "line"]
    assert len(circles) == 2           # two atoms
    assert len(lines) == 2             # a double bond = two sticks
