"""Molecular-properties tests.

Basic properties (formula, weight) always run; RDKit descriptors run only
when RDKit is installed.

Copyright (C) 2026 Gwilherm Kerherve

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
"""

import pytest

from khervemol import elements, library, properties, rdkit_io


def test_weight_table_complete():
    assert len(elements._WEIGHTS) == len(elements.SYMBOLS) == 118
    assert abs(elements.weight("C") - 12.011) < 1e-6
    assert abs(elements.weight("O") - 15.999) < 1e-6


def test_molecular_weight():
    assert abs(properties.molecular_weight(library.make("water")) - 18.015) < 0.1
    assert abs(properties.molecular_weight(library.make("ethanol")) - 46.07) < 0.1


def test_compute_basic_rows(qapp):
    rows = dict(properties.compute(library.make("ethanol")))
    assert rows["Formula"] == "C2H6O"
    assert "g/mol" in rows["Molecular weight"]
    assert rows["Heavy atoms"] == "3"


def test_compute_crystal_note(qapp):
    rows = dict(properties.compute(library.make("nacl")))
    assert "lattice" in rows["Descriptors"].lower()


@pytest.mark.skipif(not rdkit_io.available(), reason="RDKit not installed")
def test_descriptors_present(qapp):
    d = rdkit_io.descriptors_from_smiles("CCO")
    assert d and "MolWt" in d and "LogP" in d and "TPSA" in d
    rows = dict(properties.compute(library.make("ethanol")))
    assert "LogP (Crippen)" in rows and "H-bond donors" in rows


def test_a_crystal_reports_its_lattice_not_molecular_descriptors():
    from khervemol import library, properties
    mol = library.make("perovskite")
    mol.cells = (2, 2, 1)
    mol.tilts = {"1,0,0": [10, 0, 0]}
    mol.rebuild()
    rows = dict(properties.compute(mol))
    assert rows["Type"] == "Crystal lattice"
    assert "4 unit cells" in rows["Supercell"]
    assert "Ti 6" in rows["Coordination"]
    assert "(1, 0, 0)" in rows["Tilted cells"]
    assert "Molecular weight" not in rows        # a lattice has no molar mass
    assert "Mass drawn" in rows


def test_a_lattice_system_reports_its_parameters():
    from khervemol import library, properties
    rows = dict(properties.compute(library.make("monoclinic")))
    assert "β=70°" in rows["Lattice parameters"]
    assert rows["Supercell"] == "single unit cell"


def test_a_molecule_still_reports_a_molecular_weight():
    from khervemol import library, properties
    rows = dict(properties.compute(library.make("ethanol")))
    assert "Molecular weight" in rows
    assert "Type" not in rows
