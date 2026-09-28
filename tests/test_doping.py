"""Space-group expansion, CIF import, random doping and whole polyhedra
at a slab cut — scheelite LaNb(1-x)Mo(x)O4 (001) as the worked example.

Copyright (C) 2026 Gwilherm Kerherve

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
"""

import builtins
import math
from collections import Counter

import pytest

from khervemol import chem, crystal, crystal_library, entries, symmetry
from khervemol.crystal import BuildError
from khervemol.mcp_schema import check_args, tool_schema

CELL = {"name": "LaNbO4 scheelite", "formula": "LaNbO4", "a": 5.40,
        "c": 11.66,
        "polyhedra": {"centre": "Nb", "ligand": "O", "cutoff": 2.1}}
BASIS = [["La", 0, 0.25, 0.625], ["Nb", 0, 0.25, 0.125],
         ["O", 0.1504, 0.0085, 0.2111]]
#: the same cell written out atom by atom (I 41/a, origin choice 2)
ATOMS = [["La", 0.0, 0.25, 0.625], ["La", 0.5, 0.75, 0.125],
         ["La", 0.5, 0.25, 0.875], ["La", 0.0, 0.75, 0.375],
         ["Nb", 0.0, 0.25, 0.125], ["Nb", 0.5, 0.75, 0.625],
         ["Nb", 0.5, 0.25, 0.375], ["Nb", 0.0, 0.75, 0.875],
         ["O", 0.1504, 0.0085, 0.2111], ["O", 0.3496, 0.9915, 0.7111],
         ["O", 0.7415, 0.4004, 0.4611], ["O", 0.7585, 0.5996, 0.9611],
         ["O", 0.6504, 0.5085, 0.7111], ["O", 0.8496, 0.4915, 0.2111],
         ["O", 0.2415, 0.9004, 0.9611], ["O", 0.2585, 0.0996, 0.4611],
         ["O", 0.8496, 0.9915, 0.7889], ["O", 0.6504, 0.0085, 0.2889],
         ["O", 0.7585, 0.0996, 0.0389], ["O", 0.7415, 0.9004, 0.5389],
         ["O", 0.3496, 0.4915, 0.2889], ["O", 0.1504, 0.5085, 0.7889],
         ["O", 0.2585, 0.5996, 0.5389], ["O", 0.2415, 0.4004, 0.0389]]


def scheelite():
    return crystal.custom({**CELL, "atoms": ATOMS})


def degrees(mol):
    deg = Counter()
    for i, j, _o in mol.bonds:
        deg[i] += 1
        deg[j] += 1
    return deg


# ------------------------------------------------------ space groups (ASE)
def test_space_group_88_expands_to_the_full_scheelite_cell():
    pytest.importorskip("ase")
    c = crystal.custom({**CELL, "space_group": 88, "setting": 2,
                        "basis": BASIS})
    assert c.composition() == {"La": 4, "Nb": 4, "O": 16}
    assert c.space_group == "88"
    assert c.nearest("Nb", "O") == pytest.approx(1.835, abs=1e-3)
    (_i, _p, ligands), *_rest = c.polyhedra_sites()
    assert len(ligands) == 4
    for el, *f in ATOMS:
        assert any(e == el and all(abs((a - b + 0.5) % 1.0 - 0.5) < 1e-3
                                   for a, b in zip(f, g))
                   for e, *g in c.atoms)


def test_a_symbol_works_like_the_number():
    pytest.importorskip("ase")
    c = crystal.custom({"a": 4.05, "space_group": "F m -3 m",
                        "basis": [["Al", 0, 0, 0]]})
    assert c.composition() == {"Al": 4}
    assert c.bonds and c.bonds[0][:2] == ("Al", "Al")


def test_without_ase_a_basis_asks_for_it(monkeypatch):
    real = builtins.__import__

    def no_ase(name, *a, **kw):
        if name == "ase" or name.startswith("ase."):
            raise ImportError(name)
        return real(name, *a, **kw)
    monkeypatch.setattr(builtins, "__import__", no_ase)
    with pytest.raises(ValueError, match="pip install ase"):
        crystal.custom({**CELL, "space_group": 88, "basis": BASIS})
    assert not symmetry.available()


def test_a_basis_needs_a_space_group():
    with pytest.raises(ValueError, match="space_group"):
        crystal.custom({**CELL, "basis": BASIS})


def test_cif_round_trip(tmp_path):
    pytest.importorskip("ase")
    import ase.io
    from ase.spacegroup import crystal as ase_crystal
    path = tmp_path / "scheelite.cif"
    ase.io.write(str(path), ase_crystal(
        [r[0] for r in BASIS], basis=[r[1:] for r in BASIS], spacegroup=88,
        setting=2, cellpar=[5.40, 5.40, 11.66, 90, 90, 90]))
    c = symmetry.read_cif(str(path))
    assert c.composition() == {"La": 4, "Nb": 4, "O": 16}
    assert c.a == pytest.approx(5.40) and c.c == pytest.approx(11.66)
    assert any({e1, e2} == {"Nb", "O"} for e1, e2, _d in c.bonds)
    mol = chem.crystal_model(c)           # not a library key: fixed block
    assert len(mol.atoms) == 24 and mol.bonds


# --------------------------------------------------- pure Python: no ASE
def test_custom_atoms_give_polyhedra_bonds():
    c = scheelite()
    assert c.cutoffs == {("Nb", "O"): 2.1}
    mol = chem.crystal_model(c, (1, 1, 1))
    assert Counter(a[0] for a in mol.atoms) == {"La": 4, "Nb": 4, "O": 16}


def test_whole_polyhedra_keep_the_slab_stoichiometric():
    mol = chem.surface_model(scheelite(), "001", (5, 5), 2, complete=True)
    assert Counter(a[0] for a in mol.atoms) == {"La": 100, "Nb": 100,
                                                "O": 400}
    deg = degrees(mol)
    assert {deg[i] for i, a in enumerate(mol.atoms) if a[0] == "Nb"} == {4}
    assert {deg[i] for i, a in enumerate(mol.atoms) if a[0] == "O"} == {1}
    for i, j, _o in mol.bonds:
        d = math.dist(mol.atoms[i][1:], mol.atoms[j][1:])
        assert d == pytest.approx(1.835, abs=2e-3)


def test_doping_is_exact_and_reproducible():
    kw = dict(complete=True, dope=[("Nb", "Mo", 0.1)], seed=7)
    one = chem.surface_model(scheelite(), "001", (5, 5), 2, **kw)
    two = chem.surface_model(scheelite(), "001", (5, 5), 2, **kw)
    comp = Counter(a[0] for a in one.atoms)
    assert comp == {"La": 100, "Nb": 90, "Mo": 10, "O": 400}
    assert one.atoms == two.atoms
    deg = degrees(one)
    assert {deg[i] for i, a in enumerate(one.atoms)
            if a[0] in ("Nb", "Mo")} == {4}
    other = chem.surface_model(scheelite(), "001", (5, 5), 2,
                               complete=True, dope="Nb:Mo:0.1", seed=8)
    assert other.atoms != one.atoms
    assert "0.1 Mo for Nb" in one.label


def test_substitute_and_parse_dope():
    els = ["Ti"] * 20 + ["O"] * 40
    chem.substitute(els, "Ti:Zr:0.25", seed=1)
    assert els.count("Zr") == 5 and els.count("Ti") == 15
    with pytest.raises(BuildError):
        chem.parse_dope("Ti:Qq:0.1")
    with pytest.raises(BuildError):
        chem.parse_dope([("Ti", "Zr", 2)])


def test_doped_library_crystal_block():
    mol = chem.crystal_model("rutile", (3, 3, 3), dope=[("Ti", "Zr", 0.5)])
    comp = Counter(a[0] for a in mol.atoms)
    assert comp["Zr"] == 27 and comp["Ti"] == 27
    zr = {i for i, a in enumerate(mol.atoms) if a[0] == "Zr"}
    assert any(i in zr or j in zr for i, j, _o in mol.bonds)


def test_complete_needs_polyhedra():
    with pytest.raises(BuildError, match="polyhedra"):
        chem.surface_model("cu", "111", (2, 2), 2, complete=True)


def test_library_polyhedra_complete_through_entries():
    rutile = crystal_library.get("rutile")
    assert rutile.polyhedra
    mol = entries.build("surface", "rutile:110?repeat=3,3&layers=2"
                        "&complete=1&dope=Ti:V:0.2&seed=3")
    comp = Counter(a[0] for a in mol.atoms)
    assert comp["V"] == round(0.2 * (comp["Ti"] + comp["V"]))
    deg = degrees(mol)
    # shared-corner octahedra: every centre whole (O is shared, so the
    # slab is not stoichiometric the way isolated tetrahedra are)
    assert {deg[i] for i, a in enumerate(mol.atoms)
            if a[0] in ("Ti", "V")} == {6}


def test_slab_keeps_bulk_bond_lengths():
    """Regression: slabs whose step vector leans (Si(111), I-centred
    cells) kept every atom's in-plane offset wrongly."""
    mol = chem.surface_model("si", "111", (3, 3), 3)
    lengths = {round(math.dist(mol.atoms[i][1:], mol.atoms[j][1:]), 3)
               for i, j, _o in mol.bonds}
    assert lengths == {2.352}


# ------------------------------------------------------------ MCP schema
def test_mcp_schema_takes_custom_dope_and_complete():
    args = check_args(tool_schema("build_surface")["input_schema"], {
        "custom": {**CELL, "atoms": ATOMS}, "miller": "001",
        "repeat": [5, 5], "layers": 2, "complete": True,
        "dope": [["Nb", "Mo", 0.1]], "seed": 7})
    assert args["complete"] is True and args["custom"]["a"] == 5.40
    check_args(tool_schema("build_crystal")["input_schema"],
               {"cif": "/tmp/x.cif", "dope": [["Nb", "Mo", 0.1]]})
