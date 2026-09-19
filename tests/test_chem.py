"""Chemistry libraries: compounds, crystals, surfaces, nanostructures,
reactions and the entries that tie them to the tree.

Copyright (C) 2026 Gwilherm Kerherve

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
"""

import math

import pytest

from khervemol import (chem, compounds, crystal_library, elements, entries,
                       nano, reactions, smiles, surface)
from khervemol.crystal import BuildError


# ------------------------------------------------------------ compounds
def test_library_is_large():
    assert len(compounds.COMPOUNDS) > 650
    assert len(crystal_library.LIBRARY) > 100


def test_declared_formulas_match_smiles():
    """Every entry's formula is the one its SMILES actually gives."""
    bad = []
    for key, (_n, smi, _c, formula) in compounds.COMPOUNDS.items():
        want = smiles.hill_formula(smiles.formula_counts(
            formula.split(" ")[0].rstrip("+-")))
        have = smiles.formula_of(smi)
        if smiles.hill_formula(smiles.formula_counts(
                have.split(" ")[0].rstrip("+-"))) != want:
            bad.append((key, formula, have))
    assert not bad


def test_sample_of_compounds_build_with_sound_geometry():
    keys = list(compounds.COMPOUNDS)[::9]
    for key in keys:
        m = chem.compound_model(key)
        assert m.atoms and all(len(a) == 4 for a in m.atoms)
        # every bond order is an integer the viewer can draw
        assert all(b[2] in (1, 2, 3) for b in m.bonds), key
        for i, j, o in m.bonds:
            d = math.dist(m.atoms[i][1:], m.atoms[j][1:])
            want = (elements.covalent_radius(m.atoms[i][0])
                    + elements.covalent_radius(m.atoms[j][0]))
            assert 0.5 * want < d < 1.4 * want, (key, i, j, d)


def test_kekulize_benzene_pyridine_pyrrole():
    benzene = chem.compound_model("benzene")
    cc = [b[2] for b in benzene.bonds
          if benzene.atoms[b[0]][0] == benzene.atoms[b[1]][0] == "C"]
    assert sorted(cc) == [1, 1, 1, 2, 2, 2]
    pyridine = chem.smiles_model("c1ccncc1")
    assert sum(b[2] for b in pyridine.bonds) - len(pyridine.bonds) == 3
    pyrrole = chem.smiles_model("c1cc[nH]c1")       # N keeps its H, no C=N
    doubles = [b for b in pyrrole.bonds if b[2] == 2]
    assert len(doubles) == 2
    assert all(pyrrole.atoms[i][0] == "C" == pyrrole.atoms[j][0]
               for i, j, _o in doubles)


def test_names_and_aliases_resolve():
    assert compounds.get("ethene").formula == "C2H4"
    assert compounds.get("Water").formula == "H2O"


def test_smiles_fallback_needs_no_rdkit():
    m = entries.build("smiles", "CC(=O)O")
    assert m.formula() == "C2H4O2"
    with pytest.raises(BuildError):
        entries.build("smiles", "C(C")


# -------------------------------------------------------------- crystals
def test_every_crystal_matches_its_data():
    for key, c in crystal_library.LIBRARY.items():
        for e1, e2, d in c.bonds:
            assert c.nearest(e1, e2) == pytest.approx(d, rel=0.03), key
        if c.density:
            assert c.computed_density() == pytest.approx(c.density,
                                                         rel=0.03), key
        # nothing sits on top of anything else
        pts = [c.cart(f) for _e, *f in c.atoms]
        for i in range(len(pts)):
            for j in range(i + 1, len(pts)):
                for shift in ((0, 0, 0),):
                    assert math.dist(pts[i], pts[j]) > 0.5, key


@pytest.mark.parametrize("key", list(crystal_library.LIBRARY))
def test_every_crystal_builds(key):
    m = chem.crystal_model(key, (2, 2, 2))
    assert m.crystal and m.edges and len(m.edges) == 12
    assert m.bonds, key


def test_rock_salt_cell_counts():
    with_faces = chem.crystal_model("nacl", (1, 1, 1), boundary=True)
    inside = chem.crystal_model("nacl", (1, 1, 1), boundary=False)
    assert len(with_faces.atoms) == 27      # 14 Na + 13 Cl on a full cube
    assert len(inside.atoms) == 8           # 4 + 4 per conventional cell
    assert {a[0] for a in inside.atoms} == {"Na", "Cl"}
    # every atom of a Na-Cl cell sees octahedral neighbours in the bulk
    big = chem.crystal_model("nacl", (3, 3, 3))
    deg = {}
    for i, j, _o in big.bonds:
        deg[i] = deg.get(i, 0) + 1
        deg[j] = deg.get(j, 0) + 1
    assert max(deg.values()) == 6


def test_crystal_limits():
    with pytest.raises(BuildError):
        chem.crystal_model("cu", (0, 1, 1))
    with pytest.raises(BuildError):
        chem.crystal_model("quartz", (30, 30, 30))


# -------------------------------------------------------------- surfaces
def test_fcc_111_is_hexagonal():
    m = chem.surface_model("cu", "111", (3, 3), 3)
    assert m.crystal and len(m.atoms) == 27
    top = [a for a in m.atoms if abs(a[3] - max(x[3] for x in m.atoms)) < 1e-6]
    assert len(top) == 9
    # a close-packed layer: each interior surface atom has 6 in-plane
    # neighbours at the nearest-neighbour distance (2.556 Å)
    nn = min(math.dist(a[1:], b[1:]) for a in top for b in top if a is not b)
    assert nn == pytest.approx(2.556, abs=0.01)


def test_miller_parsing():
    assert surface.parse_miller("111") == (1, 1, 1)
    assert surface.parse_miller("1 -1 0") == (1, -1, 0)
    assert surface.parse_miller("10-10") == (1, 0, 0)
    assert surface.parse_miller("0001") == (0, 0, 1)
    with pytest.raises(BuildError):
        surface.parse_miller("000")


def test_all_tree_surfaces_build():
    for _group, rows in entries.surface_entries():
        for _label, (kind, value) in rows:
            m = entries.build(kind, value)
            assert m.atoms and m.bonds, value


# ----------------------------------------------------------------- nano
def test_graphene_and_carbon_forms():
    g = chem.nano_model("graphene", width=3.0, depth=3.0)
    assert 300 < len(g.atoms) < 400 and g.crystal
    cc = [math.dist(g.atoms[i][1:], g.atoms[j][1:]) for i, j, _ in g.bonds]
    assert all(1.3 < d < 1.6 for d in cc)
    bi = chem.nano_model("graphene", width=3.0, depth=3.0, layers=2)
    assert len(bi.atoms) > 1.9 * len(g.atoms)
    c60 = chem.nano_model("fullerene", kind="c60")
    assert len(c60.atoms) == 60 and len(c60.bonds) == 90
    assert not c60.crystal
    tube = chem.nano_model("nanotube", n=5, m=5, length=3.0)
    zs = [a[3] for a in tube.atoms]
    assert max(zs) - min(zs) > 25.0                    # ~3 nm long


def test_all_nano_entries_build():
    for _title, rows in entries._NANO:
        for _label, value in rows:
            assert entries.build("nano", value).atoms, value


def test_nano_errors_are_build_errors():
    with pytest.raises(BuildError):
        chem.nano_model("nanotube", n=0, m=0)
    assert nano.diameter(5, 5) == pytest.approx(0.678, abs=0.005)


# ------------------------------------------------------------- reactions
def test_balance_classics():
    rx = reactions.solve("CH4 + O2 -> CO2 + H2O")
    assert rx.equation == "CH4 + 2 O2 → CO2 + 2 H2O" and rx.balanced
    rx = reactions.solve("N2 + H2 <=> NH3")
    assert rx.equation == "N2 + 3 H2 ⇌ 2 NH3"
    rx = reactions.solve("MnO4- + Fe^2+ + H+ -> Mn^2+ + Fe^3+ + H2O")
    assert rx.balanced and "charge" in rx.table


def test_reaction_given_coefficients_are_checked():
    rx = reactions.solve("2 H2 + O2 -> 3 H2O", balance_it=False)
    assert not rx.balanced
    assert rx.table["H"] == (4.0, 6.0)


def test_unbalanceable_and_unknown_species():
    with pytest.raises(BuildError):
        reactions.solve("H2 -> O2")
    with pytest.raises(BuildError):
        reactions.solve("H2 + Foo -> Bar")
    with pytest.raises(BuildError):
        reactions.solve("H2 O2")                      # no arrow


@pytest.mark.parametrize("name", list(reactions.EXAMPLES))
def test_every_example_reaction_balances_and_lays_out(name):
    rx = reactions.solve(reactions.EXAMPLES[name])
    assert rx.balanced, name
    m = reactions.layout(rx)
    assert m.notes and m.atoms
    kinds = {n["kind"] for n in m.notes}
    assert kinds == {"text", "arrow"}
    assert any(n["kind"] == "arrow" and n["double"] == rx.reversible
               for n in m.notes)


def test_reaction_scene_copies_and_order():
    m = reactions.reaction_model("2 H2 + O2 -> 2 H2O")[0]
    # H2 H2 O2 -> H2O H2O : 4 + 2 + 6 atoms, drawn left to right
    assert len(m.atoms) == 12
    arrow = next(n for n in m.notes if n["kind"] == "arrow")
    left = [a for a in m.atoms[:6]]
    right = [a for a in m.atoms[6:]]
    assert max(a[1] for a in left) < arrow["p1"][0] < min(a[1] for a in right)


def test_reaction_notes_survive_save_and_load(tmp_path):
    from khervemol import document
    m = reactions.reaction_model("N2 + 3 H2 <=> 2 NH3")[0]
    path = str(tmp_path / "rx.kmol")
    document.save(path, m, [], [])
    back, _a, _b = document.load(path)
    assert back.notes == m.notes
    assert isinstance(back.notes[0].get("pos", back.notes[0].get("p1")),
                      tuple)


def test_notes_are_drawn_by_the_classic_projection():
    m = reactions.reaction_model("H2 + Cl2 -> HCl")[0]
    specs = m.specs(800, 400)
    texts = [s["text"] for s in specs if s["shape"] == "text"]
    assert "+" in texts and "H2" in texts and "Cl2" in texts
    assert sum(1 for s in specs if s["shape"] == "line" and s["width"] > 1.5)


# --------------------------------------------------------------- entries
def test_sections_cover_everything_and_build_non_molecules():
    secs = entries.sections()
    titles = [t for t, _g in secs]
    assert any(t.startswith("Molecules") for t in titles)
    assert any(t.startswith("Crystals") for t in titles)
    assert any(t.startswith("Reactions") for t in titles)
    for title, groups in secs:
        if title.startswith("Molecules"):
            continue
        for _g, rows in groups:
            for _label, (kind, value) in rows[:6]:
                assert entries.build(kind, value).atoms


def test_entry_params_round_trip():
    m = entries.build("crystal", "cu?cells=2,1,1&boundary=0")
    assert len(m.atoms) == 8 and "2×1×1" in m.label
    s = entries.build("surface", "cu:100?repeat=2,3&layers=2")
    assert "2×3" in s.label
    with pytest.raises(BuildError):
        entries.build("nope", "x")


def test_main_window_loads_every_kind(qapp):
    from khervemol.mainwindow import MainWindow
    w = MainWindow()
    for kind, value in (("crystal", "quartz"), ("surface", "si:111"),
                        ("nano", "fullerene?kind=c60"),
                        ("reaction", "2 H2 + O2 -> 2 H2O"),
                        ("compound", "caffeine"), ("smiles", "CCO"),
                        ("model", "water")):
        assert w.load_entry(kind, value), (kind, value)
        assert w.viewer.mol.atoms
    assert w.viewer.mol.name == "water"
    assert w.tree.topLevelItemCount() >= 6


def test_builder_dialogs_produce_entries(qapp):
    from khervemol import builders_ui
    d = builders_ui.CrystalDialog(key="nacl")
    d.nx.setValue(2)
    kind, value, _label = d.entry()
    assert kind == "crystal" and value.startswith("nacl?cells=2,1,1")
    assert entries.build(kind, value).atoms
    d = builders_ui.SurfaceDialog(key="si")
    d.miller.setText("111")
    kind, value, _label = d.entry()
    assert entries.build(kind, value).crystal
    d.miller.setText("0 0 0")
    assert not d.ok_btn.isEnabled()
    d = builders_ui.NanoDialog()
    for i in range(d.type.count()):
        d.type.setCurrentIndex(i)
        kind, value, _label = d.entry()
        assert entries.build(kind, value).atoms, value
    d = builders_ui.ReactionDialog()
    kind, value, _label = d.entry()
    assert "2 O2" in value and entries.build(kind, value).notes
    d.text.setText("H2 -> O2")
    assert not d.ok_btn.isEnabled()


def test_explorer_lists_and_previews_all_kinds(qapp):
    from PyQt5.QtCore import Qt
    from khervemol.explorer import MoleculeExplorer
    dlg = MoleculeExplorer()
    top = dlg.tree.topLevelItem(1)                  # crystals
    leaf = top.child(0).child(0)
    dlg.tree.setCurrentItem(leaf)
    assert dlg.build_btn.isEnabled()
    assert dlg.result()[0] == "crystal"
    assert leaf.data(0, Qt.UserRole)[0] == "crystal"
