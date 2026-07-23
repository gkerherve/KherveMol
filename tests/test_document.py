"""Document round-trip + PNG export tests.

Copyright (C) 2026 Gwilherm Kerherve

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
"""

from khervemol import document, library


def test_roundtrip_molecule(qapp, tmp_path):
    mol = library.make("ethanol")
    sketch_atoms = [["C", 0, 0], ["O", 40, 0]]
    sketch_bonds = [[0, 1, 1]]
    path = tmp_path / "eth.kmol"
    document.save(str(path), mol, sketch_atoms, sketch_bonds)
    back, sa, sb = document.load(str(path))
    assert len(back.atoms) == len(mol.atoms)
    assert back.bonds == [list(b) for b in mol.bonds]
    assert abs(back.az - mol.az) < 1e-9
    assert back.formula() == mol.formula()
    assert sa == sketch_atoms
    assert sb == sketch_bonds


def test_roundtrip_crystal_keeps_edges(qapp, tmp_path):
    mol = library.make("fcc")
    path = tmp_path / "fcc.kmol"
    document.save(str(path), mol, [], [])
    back, _sa, _sb = document.load(str(path))
    assert back.crystal
    assert back.edges and len(back.edges) == len(mol.edges)


def test_export_png(qapp, tmp_path):
    mol = library.make("benzene")
    path = tmp_path / "benzene.png"
    document.export_png(str(path), mol.specs(300, 300), 300, 300)
    assert path.exists() and path.stat().st_size > 0
