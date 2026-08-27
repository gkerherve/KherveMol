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


#: What each built-in molecule's formula must be (Hill notation, as
#: `Molecule.formula` reports it). A model that draws the right shape but
#: the wrong number of atoms is still the wrong molecule — cyclopentane
#: once had no hydrogens at all, glucose only five carbons, and PTFE one
#: fluorine per carbon instead of two.
_FORMULAS = {
    "water": "H2O", "ammonia": "H3N", "ammonium": "H4N", "methane": "CH4",
    "carbon_dioxide": "CO2", "formaldehyde": "CH2O", "methanol": "CH4O",
    "ethanol": "C2H6O", "acetic_acid": "C2H4O2", "glucose": "C6H12O6",
    "ethane": "C2H6", "propane": "C3H8", "butane": "C4H10",
    "ethene": "C2H4", "ethyne": "C2H2", "benzene": "C6H6",
    "cyclopentane": "C5H10", "cyclohexane": "C6H12",
    # six-carbon oligomers of each repeat unit, capped with hydrogen
    "polyethylene": "C6H14", "polypropylene": "C9H20", "pvc": "C6H11Cl3",
    "ptfe": "C6H2F12", "polystyrene": "C24H26", "pet": "C10H8O4",
}


@pytest.mark.parametrize("name,formula", sorted(_FORMULAS.items()))
def test_a_built_in_molecule_has_the_formula_its_name_promises(name, formula):
    assert library.make(name).formula() == formula


def test_every_non_crystal_model_is_formula_checked():
    """A new molecule must declare its formula, or this table stops being
    a guard."""
    molecules = {n for n in library.names() if not library.is_crystal(n)}
    assert molecules == set(_FORMULAS)
