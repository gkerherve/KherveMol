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
    assert "lattice" in rows["Note"].lower()


@pytest.mark.skipif(not rdkit_io.available(), reason="RDKit not installed")
def test_descriptors_present(qapp):
    d = rdkit_io.descriptors_from_smiles("CCO")
    assert d and "MolWt" in d and "LogP" in d and "TPSA" in d
    rows = dict(properties.compute(library.make("ethanol")))
    assert "LogP (Crippen)" in rows and "H-bond donors" in rows
