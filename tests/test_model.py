"""Geometry engine + builder tests.

Copyright (C) 2026 Gwilherm Kerherve

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
"""

from khervemol import model


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
