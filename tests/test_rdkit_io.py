"""RDKit bridge tests — skipped entirely when RDKit is not installed.

Copyright (C) 2026 Gwilherm Kerherve

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
"""

import pytest

from khervemol import rdkit_io

pytestmark = pytest.mark.skipif(not rdkit_io.available(),
                                reason="RDKit not installed")


def test_smiles_to_3d(qapp):
    mol = rdkit_io.molecule_from_smiles("CCO")     # ethanol
    assert mol.formula() == "C2H6O"
    assert all(len(a) == 4 for a in mol.atoms)     # x, y, z present
    assert mol.bonds


def test_smiles_to_2d(qapp):
    atoms, bonds = rdkit_io.sketch_from_smiles("c1ccccc1")   # benzene
    assert len(atoms) == 6                          # heavy atoms only
    assert all(len(a) == 3 for a in atoms)          # el, x, y


def test_structure_to_smiles(qapp):
    mol = rdkit_io.molecule_from_smiles("CO")       # methanol
    smi = rdkit_io.smiles_from_structure(mol.atoms, mol.bonds)
    assert smi and "C" in smi and "O" in smi


def test_bad_smiles_raises():
    with pytest.raises(ValueError):
        rdkit_io.molecule_from_smiles("this is not smiles!!!")
