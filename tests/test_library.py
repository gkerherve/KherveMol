"""Library tests — every model builds and projects to specs.

Copyright (C) 2026 Gwilherm Kerherve

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
"""

import pytest

from khervemol import library, model


@pytest.mark.parametrize("name", library.names())
def test_every_model_builds(name, qapp):
    mol = library.make(name)
    assert mol.atoms, name
    specs = mol.specs(400, 400)
    assert specs, name
    assert any(s["shape"] == "circle" for s in specs), name


def test_crystal_flag():
    assert library.make("diamond").crystal
    assert library.make("nacl").crystal
    assert not library.make("water").crystal


def test_crystals_carry_edges():
    mol = library.make("bcc")
    assert mol.edges, "crystal unit cell must have frame edges"


def test_labels_present():
    for name in library.names():
        assert library.label(name)


def _molecules():
    return [n for n in library.names() if not library.is_crystal(n)]


@pytest.mark.parametrize("name", _molecules())
def test_no_impossible_bond_angles(name):
    """Every built-in molecule must have sane geometry.

    Substituents have to be placed from the bonds an atom already carries;
    reusing a fixed tetrahedral basis on a *second* centre puts them at 70.5°
    — the supplement of 109.5° — instead. No real skeleton bends below ~95°."""
    mol = library.make(name)
    neighbours = {i: [] for i in range(len(mol.atoms))}
    for i, j, _o in mol.bonds:
        neighbours[i].append(j)
        neighbours[j].append(i)
    for centre, ns in neighbours.items():
        for a in range(len(ns)):
            for b in range(a + 1, len(ns)):
                deg = model.angle(mol.atoms, ns[a], centre, ns[b])
                assert deg >= 95.0, (
                    f"{name}: {mol.atoms[ns[a]][0]}{ns[a]}–"
                    f"{mol.atoms[centre][0]}{centre}–"
                    f"{mol.atoms[ns[b]][0]}{ns[b]} is {deg:.1f}°")


@pytest.mark.parametrize("name", _molecules())
def test_no_atom_exceeds_its_valence(name):
    mol = library.make(name)
    if name == "ammonium":
        return                              # NH4+ is a cation: N carries 4
    for i, atom in enumerate(mol.atoms):
        free = model.free_valence(mol.atoms, mol.bonds, i)
        assert free >= 0, f"{name}: {atom[0]}{i} is over-bonded by {-free}"


@pytest.mark.parametrize("name", _molecules())
def test_bonded_atoms_are_not_on_top_of_each_other(name):
    mol = library.make(name)
    for i, j, _o in mol.bonds:
        assert model.distance(mol.atoms, i, j) > 0.5, f"{name}: atoms {i}-{j}"
