"""Molecules on a surface: place, move, turn, add another, remove.

Copyright (C) 2026 Gwilherm Kerherve

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
"""

import math

import pytest

from khervemol import adsorbates, chem, document, entries
from khervemol.crystal import BuildError


@pytest.fixture
def scene():
    base = chem.surface_model("cu", "111")
    return chem.add_adsorbate(base, entries.build("compound", "benzene"),
                              height=2.4, mode="flat")


def _pos(mol, gi):
    return [list(mol.atoms[i][1:4]) for i in adsorbates.members(mol, gi)]


def test_add_makes_a_group_above_the_top_layer(scene):
    assert len(scene.groups) == 1
    g = scene.groups[0]
    assert g["count"] == 12 and g["start"] == 108
    assert adsorbates.pose(scene, 0)["height"] == pytest.approx(2.4)
    assert adsorbates.group_of(scene, 110) == 0
    assert adsorbates.group_of(scene, 5) is None
    assert adsorbates.surface_indices(scene) == list(range(108))
    assert adsorbates.top_layer(scene) == pytest.approx(
        max(a[3] for a in scene.atoms[:108]))


def test_translate_and_place(scene):
    before = _pos(scene, 0)
    adsorbates.translate(scene, 0, 1.0, -2.0, 0.5)
    for b, a in zip(before, _pos(scene, 0)):
        assert (a[0] - b[0], a[1] - b[1], a[2] - b[2]) == pytest.approx(
            (1.0, -2.0, 0.5))
    adsorbates.place(scene, 0, height=3.0)
    assert adsorbates.pose(scene, 0)["height"] == pytest.approx(3.0)
    adsorbates.place(scene, 0, x=1.0, y=2.0)
    p = adsorbates.pose(scene, 0)
    assert (p["x"], p["y"]) == pytest.approx((1.0, 2.0))
    assert p["height"] == pytest.approx(3.0)            # untouched
    # the slab did not move
    assert scene.atoms[0][3] == chem.surface_model("cu", "111").atoms[0][3]


def test_rotate_is_rigid_about_the_centre(scene):
    c0 = adsorbates.centroid(scene, 0)
    pos = _pos(scene, 0)
    dists = [math.dist(pos[0], p) for p in pos]
    adsorbates.rotate(scene, 0, rz=90)
    assert adsorbates.centroid(scene, 0) == pytest.approx(c0, abs=1e-9)
    after = _pos(scene, 0)
    assert [math.dist(after[0], p) for p in after] == pytest.approx(dists)
    assert after != pos
    # a full turn returns it
    adsorbates.rotate(scene, 0, rz=90)
    adsorbates.rotate(scene, 0, rz=180)
    flat = lambda rows: [x for r in rows for x in r]
    assert flat(_pos(scene, 0)) == pytest.approx(flat(pos), abs=1e-8)
    # tilting a flat ring lifts part of it off the plane
    adsorbates.rotate(scene, 0, rx=60)
    zs = [p[2] for p in _pos(scene, 0)]
    assert max(zs) - min(zs) > 1.0


def test_drag_slides_in_the_plane_or_lifts():
    base = chem.surface_model("cu", "111")
    m = chem.add_adsorbate(base, entries.build("compound", "benzene"))
    az, el = math.radians(30), math.radians(40)
    p0 = adsorbates.centroid(m, 0)
    adsorbates.drag(m, 0, 20.0, 0.0, az, el, 1.0, 10.0)
    p1 = adsorbates.centroid(m, 0)
    assert p1[2] == pytest.approx(p0[2])                # stays in the plane
    assert math.dist(p0, p1) == pytest.approx(2.0, rel=1e-6)
    # dragging right on screen moves the molecule right on screen
    ca, sa = math.cos(az), math.sin(az)
    assert (p1[0] - p0[0]) * ca - (p1[1] - p0[1]) * sa > 0
    adsorbates.drag(m, 0, 0.0, -30.0, az, el, 1.0, 10.0, vertical=True)
    assert adsorbates.centroid(m, 0)[2] > p1[2] + 2.0   # up the screen = up


def test_add_a_second_molecule_at_a_free_spot(scene):
    water = entries.build("compound", "water")
    gi = adsorbates.add(scene, water, auto=True)
    assert gi == 1 and len(scene.groups) == 2
    # no atom of the new one is closer than the clearance to the first
    first = _pos(scene, 0)
    for p in _pos(scene, 1):
        assert min(math.dist(p, q) for q in first) >= adsorbates.CLEARANCE - 1e-6
    # names stay unique
    gi = adsorbates.add(scene, water, auto=True)
    names = [g["name"] for g in scene.groups]
    assert len(set(names)) == 3
    # not bonded to the surface or to each other
    n = len(scene.atoms)
    starts = [g["start"] for g in scene.groups] + [n]
    def owner(i):
        return next((k for k in range(len(starts) - 1)
                     if starts[k] <= i < starts[k + 1]), None)
    assert all(owner(i) == owner(j) for i, j, _o in scene.bonds
               if i >= 108 and j >= 108)


def test_remove_reindexes_everything(scene):
    water = entries.build("compound", "water")
    adsorbates.add(scene, water, auto=True)
    adsorbates.add(scene, water, auto=True)
    total = len(scene.atoms)
    nb = len(scene.bonds)
    adsorbates.remove(scene, 1)                      # the middle one
    assert len(scene.atoms) == total - 3 and len(scene.bonds) == nb - 2
    assert len(scene.groups) == 2
    assert scene.groups[1]["start"] == 108 + 12
    assert all(i < len(scene.atoms) and j < len(scene.atoms)
               for i, j, _o in scene.bonds)
    assert scene.atoms[scene.groups[1]["start"]][0] == "O"
    adsorbates.remove(scene, 0)
    adsorbates.remove(scene, 0)
    assert scene.groups == [] and len(scene.atoms) == 108


def test_errors(scene):
    with pytest.raises(BuildError):
        adsorbates.add(scene, entries.build("crystal", "cu"))
    with pytest.raises(BuildError):
        adsorbates.add(scene, entries.build("compound", "water"), mode="up")
    from khervemol.model import Molecule
    with pytest.raises(BuildError):
        adsorbates.top_layer(Molecule([], []))


def test_groups_survive_clone_and_file(scene, tmp_path):
    adsorbates.translate(scene, 0, 1.5, 0.0, 0.0)
    copy = scene.clone()
    assert copy.groups == scene.groups and copy.groups is not scene.groups
    path = str(tmp_path / "s.kmol")
    document.save(path, scene, [], [])
    back, _a, _b = document.load(path)
    assert back.groups == scene.groups
    assert adsorbates.pose(back, 0) == pytest.approx(adsorbates.pose(scene, 0))
    # an old file with no groups still loads
    scene.groups = []
    document.save(path, scene, [], [])
    assert document.load(path)[0].groups == []


# ------------------------------------------------------------------ viewer
def test_viewer_controls_move_turn_add_remove(qapp):
    from khervemol.mainwindow import MainWindow
    w = MainWindow()
    v = w.viewer
    w.load_entry("surface", "cu:111")
    assert v.is_surface
    assert all(wd.isVisibleTo(v) for wd in v._group_widgets)
    assert not v.group_combo.isEnabled() and v.group_add_btn.isEnabled()
    # add two molecules through the viewer (what the dialog does)
    v.add_group(entries.build("compound", "benzene"), mode="flat")
    v.add_group(entries.build("compound", "water"), auto=True)
    assert v.group_combo.count() == 2 and v.current_group() == 1
    before = adsorbates.centroid(v.mol, 1)
    v.group_step.setValue(1.0)
    v._group_btns[1].click()                             # X+
    after = adsorbates.centroid(v.mol, 1)
    assert after[0] - before[0] == pytest.approx(1.0)
    v._group_btns[5].click()                             # Z+
    assert adsorbates.centroid(v.mol, 1)[2] == pytest.approx(after[2] + 1.0)
    # the other molecule did not move
    assert adsorbates.pose(v.mol, 0)["height"] == pytest.approx(2.4)
    # turn mode
    v.group_mode.setCurrentIndex(v.group_mode.findData("turn"))
    assert v.group_step.value() == 15.0 and v._group_btns[5].text() == "Turn+"
    pos = [list(a) for a in v.mol.atoms[v.mol.groups[1]["start"]:]]
    v._group_btns[5].click()
    moved = [list(a) for a in v.mol.atoms[v.mol.groups[1]["start"]:]]
    assert moved != pos
    # clicking an atom of the first molecule picks it in the combo
    v.select_atom(v.mol.groups[0]["start"] + 1)
    assert v.current_group() == 0
    assert "above the surface" in v.status.text()
    v.remove_current_group()
    assert v.group_combo.count() == 1 and len(v.mol.groups) == 1
    # a molecule view has no such row
    w.load_entry("compound", "water")
    assert not v.is_surface
    assert not any(wd.isVisibleTo(v) for wd in v._group_widgets)


def test_add_molecule_dialog_and_menu(qapp, tmp_path, monkeypatch):
    from khervemol import builders_ui, library, shelf
    from khervemol.mainwindow import MainWindow
    monkeypatch.setattr(shelf, "_DEFAULT", shelf.Shelf(str(tmp_path / "s.json")))
    w = MainWindow()
    w.shelf.add(entries.build("compound", "methanol"), "Alcohol")
    d = builders_ui.AddMoleculeDialog(molecule=library.make("benzene"),
                                      shelf=w.shelf, crowded=True)
    assert d.adsorbate_source() == "drawn" and d.ads_auto.isChecked()
    assert d.adsorbate().formula() == "C6H6"
    d.ads_source.setCurrentIndex(d.ads_source.findData("kept"))
    assert d.adsorbate().formula() == "CH4O"
    d.ads_source.setCurrentIndex(d.ads_source.findData("smiles"))
    assert not d.ok_btn.isEnabled()
    d.ads_smiles.setText("CC")
    assert d.ok_btn.isEnabled() and d.adsorbate().formula() == "C2H6"
    assert not d.ads_dx.isEnabled()                       # automatic spot
    assert d.placement()["auto"] is True
    # the menu action exists
    titles = [a.text() for m in w.findChildren(type(w._menus["crystals"]))
              for a in m.actions()]
    assert any("Add molecule to surface" in t for t in titles)


def test_mcp_tools_add_move_remove(qapp, tmp_path, monkeypatch):
    from khervemol import mcp_tools, shelf
    from khervemol.mainwindow import MainWindow
    monkeypatch.setattr(shelf, "_DEFAULT", shelf.Shelf(str(tmp_path / "s.json")))
    w = MainWindow()
    ex = mcp_tools.McpToolExecutor(w)
    assert "build_surface" in ex.execute("add_to_surface",
                                         {"smiles": "O"})["error"]
    r = ex.execute("build_surface", {"crystal": "cu", "miller": "111",
                                     "adsorbate": {"smiles": "c1ccccc1"}})
    assert r["adsorbates"][0]["height"] == pytest.approx(2.4)
    shelf.default().add(entries.build("compound", "methanol"), "Alcohol")
    r = ex.execute("add_to_surface", {"kept": "Alcohol"})
    assert r["ok"] and r["adsorbate"]["index"] == 1
    r = ex.execute("add_to_surface", {"compound": "water", "dx": 4.0,
                                      "auto": False, "height": 3.0})
    assert r["adsorbate"]["index"] == 2 and len(r["adsorbates"]) == 3
    ex.execute("move_adsorbate", {"index": 2, "x": 1.0, "y": -1.0,
                                  "height": 3.5})
    p = ex.execute("get_document_info", {})["adsorbates"][2]
    assert (p["x"], p["y"], p["height"]) == pytest.approx((1.0, -1.0, 3.5))
    ex.execute("move_adsorbate", {"name": "Alcohol", "dx": 2.0, "turn": 90})
    assert "index" in ex.execute("move_adsorbate", {"dx": 1})["error"]
    assert "No adsorbate named" in ex.execute(
        "move_adsorbate", {"name": "zzz", "dx": 1})["error"]
    r = ex.execute("remove_adsorbate", {"index": 1})
    assert r["remaining"] == 2 and r["removed"] == "Alcohol"
    assert len(ex.execute("get_document_info", {})["adsorbates"]) == 2
