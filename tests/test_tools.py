"""Polymers, the menus in line with the library, and the toolbars.

Copyright (C) 2026 Gwilherm Kerherve

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
"""

import pytest

from khervemol import entries, polymers, smiles
from khervemol.crystal import BuildError


@pytest.mark.parametrize("key", list(polymers.PRESETS))
def test_every_polymer_preset_builds(key):
    name, unit, n, cat, (head, tail) = polymers.PRESETS[key]
    assert cat in polymers.CATEGORIES
    m = entries.build("polymer", f"{key}?n=2")
    assert len(m.atoms) >= 4 and m.bonds
    assert "2 repeat units" in m.label
    # no atom is left short of its valence: every implicit H became an atom
    assert m.formula() == smiles.formula_of(
        polymers.chain_smiles(unit, 2, head, tail))


def test_polymer_grows_with_n():
    a = entries.build("polymer", "pvc?n=2")
    b = entries.build("polymer", "pvc?n=6")
    assert len(b.atoms) - len(a.atoms) == 4 * 6      # C2H3Cl = 6 atoms per unit
    assert b.formula() == "C12H20Cl6"


def test_custom_polymer_and_errors():
    m = entries.build("polymer", "custom?unit=CC%28C%23N%29&n=3")
    assert m.formula() == "C9H11N3"
    with pytest.raises(BuildError):
        entries.build("polymer", "custom?unit=C%28C&n=3")
    with pytest.raises(BuildError):
        entries.build("polymer", "pvc?n=500")
    with pytest.raises(BuildError):
        entries.build("polymer", "nope?n=2")
    assert polymers.max_units("CC") > 50


def test_menus_list_what_the_tree_lists(qapp):
    from PyQt5.QtCore import Qt
    from khervemol.mainwindow import MainWindow
    w = MainWindow()

    def count(menu):
        n = 0
        for act in menu.actions():
            if act.menu() is not None:
                n += count(act.menu())
            elif not act.isSeparator() and not act.text().endswith("builder…"):
                n += 1
        return n

    def leaves(item):
        n = 1 if item.data(0, Qt.UserRole) is not None else 0
        return n + sum(leaves(item.child(i)) for i in range(item.childCount()))

    tree = {}
    for i in range(w.tree.topLevelItemCount()):
        top = w.tree.topLevelItem(i)
        tree[top.text(0).split(" —")[0]] = leaves(top)
    # every molecule / crystal / polymer in the tree is in its menu
    assert count(w._menus["molecules"]) >= tree["Molecules"]
    assert count(w._menus["polymers"]) >= tree["Polymers"]
    assert count(w._menus["reactions"]) >= tree["Reactions"]
    assert count(w._menus["surfaces"]) == tree["Surfaces"]
    assert count(w._menus["carbon"]) == tree[
        "Graphene, nanotubes & fullerenes"]
    assert tree["Molecules"] > 650 and tree["Polymers"] >= 40


def test_menu_action_loads_an_entry(qapp):
    from khervemol.mainwindow import MainWindow
    w = MainWindow()
    poly = w._menus["polymers"]
    sub = next(a.menu() for a in poly.actions() if a.menu())
    sub.actions()[0].trigger()
    assert w.viewer.mol.name.startswith("polymer:")


def test_toolbar_tools_drive_the_editors(qapp):
    from khervemol import library
    from khervemol.mainwindow import MainWindow
    w = MainWindow()
    # 2D tools switch tab and set the sketch tool
    w._tool_actions["erase"].trigger()
    assert w.sketch.tool == "erase" and w.tabs.currentIndex() == 1
    w._tool_actions["draw"].trigger()
    assert w.sketch.tool == "draw"
    # element combo drives both views
    w.tb_element.setCurrentText("N")
    assert w.viewer.active_element == "N" and w.sketch.element == "N"
    # bond order actions follow the viewer combo, both ways
    w._order_actions[2].trigger()
    assert w.viewer.order == 3
    w.viewer.order_combo.setCurrentIndex(1)
    assert w._order_actions[1].isChecked()
    # add an atom from the toolbar
    w.viewer.set_molecule(library.make("methane"))
    w.viewer.select_atom(0)
    before = len(w.viewer.mol.atoms)
    w._order_actions[0].trigger()
    w.tb_element.setCurrentText("H")
    w._edit_actions[0].trigger()
    assert w.tabs.currentIndex() == 0
    assert len(w.viewer.mol.atoms) in (before, before + 1)


def test_toolbar_disables_what_does_not_apply(qapp):
    from khervemol import library
    from khervemol.mainwindow import MainWindow
    w = MainWindow()
    w.load_entry("reaction", "H2 + Cl2 -> HCl")
    assert w._play_action.isEnabled() and not w._stop_action.isEnabled()
    assert not w._edit_actions[0].isEnabled()           # a read-only scene
    w.viewer.set_progress(0.4)
    assert w._stop_action.isEnabled()
    w.load_entry("model", "ethanol")
    assert not w._play_action.isEnabled()
    assert w._edit_actions[0].isEnabled()
    w.viewer.set_molecule(library.make("fcc"))
    assert not w._edit_actions[0].isEnabled()


def test_toolbar_labels_and_lock_stay_in_step(qapp):
    from khervemol.mainwindow import MainWindow
    w = MainWindow()
    w._labels_action.setChecked(True)
    assert w.viewer.labels_btn.isChecked()
    w.viewer.labels_btn.setChecked(False)
    assert not w._labels_action.isChecked()
    w._lock_action.setChecked(False)
    assert not w.viewer.lock_btn.isChecked()


def test_polymer_dialog(qapp):
    from khervemol import builders_ui
    d = builders_ui.PolymerDialog(key="pmma")
    assert "C" in d.summary.text() and d.ok_btn.isEnabled()
    k, v, _l = d.entry()
    assert k == "polymer" and v.startswith("pmma?n=")
    d.combo.setCurrentIndex(d.combo.findData("custom"))
    d.unit.setText("C(C")
    assert not d.ok_btn.isEnabled()
    d.unit.setText("CC(F)")
    d.n.setValue(3)
    k, v, _l = d.entry()
    assert entries.build(k, v).formula() == "C6H11F3"


def test_periodic_table_is_a_window_not_a_dock(qapp):
    from PyQt5.QtWidgets import QDockWidget
    from khervemol.mainwindow import MainWindow
    w = MainWindow()
    assert not any(d.windowTitle() == "Periodic table"
                   for d in w.findChildren(QDockWidget))
    assert w._ptable_window is None
    w.show_periodic_table()
    assert w._ptable_window.isVisible() and not w._ptable_window.isModal()
    w.picker.picked.emit("Fe")             # a click in the window
    assert w.viewer.active_element == "Fe" and w.sketch.element == "Fe"
    assert w.tb_element.currentText() == "Fe"   # added to the toolbar box
    w.show_periodic_table()                # reopening reuses the window
    assert w._ptable_window.isVisible()


def test_table_button_in_the_add_atom_row_opens_the_table(qapp):
    from khervemol.mainwindow import MainWindow
    w = MainWindow()
    row = w.viewer.table_btn.parentWidget()
    assert row is w.viewer
    w.viewer.table_btn.click()
    assert w._ptable_window is not None and w._ptable_window.isVisible()
    # the palette buttons have room for two-letter symbols (Cl, Br)
    for b in w.viewer._palette_btns + [w.viewer.table_btn]:
        assert b.minimumWidth() >= 38
        assert "padding" in b.styleSheet()


def test_there_is_no_duplicate_plus_element_button(qapp):
    from khervemol.mainwindow import MainWindow
    w = MainWindow()
    assert not hasattr(w.viewer, "add_active_btn")
    w.tb_element.setCurrentText("N")
    assert "N" in w.viewer.table_btn.text()
    w.viewer.select_atom(0)


def test_adsorbate_sits_above_the_top_layer_unbonded():
    from khervemol import chem
    base = chem.surface_model("cu", "111")
    ben = entries.build("compound", "benzene")
    top = max(a[3] for a in base.atoms)
    for mode in chem.ADSORB_MODES:
        m = chem.add_adsorbate(base, ben, height=3.0, mode=mode)
        ads = m.atoms[len(base.atoms):]
        assert len(ads) == len(ben.atoms)
        assert min(a[3] for a in ads) == pytest.approx(top + 3.0)
        # no bond between the surface and the molecule
        assert all((i < len(base.atoms)) == (j < len(base.atoms))
                   for i, j, _o in m.bonds)
        assert len(m.bonds) == len(base.bonds) + len(ben.bonds)
    flat = chem.add_adsorbate(base, ben, mode="flat")
    up = chem.add_adsorbate(base, ben, mode="upright")
    zs = [a[3] for a in flat.atoms[len(base.atoms):]]
    zu = [a[3] for a in up.atoms[len(base.atoms):]]
    assert max(zs) - min(zs) < 0.1 < max(zu) - min(zu)     # planar ring
    with pytest.raises(BuildError):
        chem.add_adsorbate(base, entries.build("crystal", "cu"))
    with pytest.raises(BuildError):
        chem.add_adsorbate(base, ben, mode="sideways")


def test_surface_dialog_offers_the_drawn_molecule(qapp):
    from khervemol import builders_ui, library
    none = builders_ui.SurfaceDialog(key="cu")
    assert none.adsorbate_source() == "none" and none.adsorbate() is None
    assert not none.ads_source.model().item(1).isEnabled()
    d = builders_ui.SurfaceDialog(key="cu", molecule=library.make("benzene"))
    assert d.adsorbate_source() == "drawn"      # pre-selected when there is one
    assert d.adsorbate().formula() == "C6H6"
    d.ads_source.setCurrentIndex(2)
    assert not d.ok_btn.isEnabled()             # needs a SMILES
    d.ads_smiles.setText("CO")
    assert d.ok_btn.isEnabled() and d.adsorbate().formula() == "CH4O"
    assert d.placement()["mode"] == "flat"


def test_main_window_remembers_the_molecule_through_a_surface(qapp):
    from khervemol import library
    from khervemol.mainwindow import MainWindow
    w = MainWindow()
    w.viewer.set_molecule(library.make("benzene"))
    assert w.drawn_molecule().formula() == "C6H6"
    w.load_entry("surface", "cu:111")
    assert not w.viewer.editable
    assert w.drawn_molecule().formula() == "C6H6"      # still available


def test_cell_outline_can_be_hidden_everywhere(qapp, tmp_path):
    from khervemol import document, library
    from khervemol.mainwindow import MainWindow
    w = MainWindow()
    v = w.viewer
    w.load_entry("crystal", "srtio3?cells=2,2,2")
    assert v.cell_btn.isEnabled() and v.cell_btn.isChecked()
    full = len(v.mol.specs(800, 600))
    v.cell_btn.setChecked(False)                     # the tick box
    assert v.mol.cell_visible is False and v.mol.shown_edges is None
    assert len(v.mol.specs(800, 600)) == full - len(v.mol.edges)
    # the scene of the GL renderer is built without the outline too
    from khervemol import glview
    assert glview.Scene(v.mol).edges == []
    v.mol.cell_visible = True
    assert len(glview.Scene(v.mol).edges) == len(v.mol.edges)
    v.mol.cell_visible = False
    # the View menu and the Crystal menu follow, and drive it back
    w._sync_crystal_menu()
    assert not w._view_cell.isChecked() and not w._xtal_cell.isChecked()
    w._view_cell.trigger()
    assert v.mol.cell_visible and v.cell_btn.isChecked()
    w._xtal_cell.trigger()
    assert not v.mol.cell_visible
    # persisted, and kept when the file is reopened
    path = str(tmp_path / "c.kmol")
    document.save(path, v.mol, [], [])
    back, _a, _b = document.load(path)
    assert back.cell_visible is False
    v.set_molecule(back)
    assert not v.cell_btn.isChecked()
    # nothing to hide on a molecule
    v.set_molecule(library.make("water"))
    assert not v.cell_btn.isEnabled()
    assert v.mol.clone().cell_visible


# ------------------------------------------------------- kept molecules
def _fresh_shelf(tmp_path):
    from khervemol import shelf
    return shelf.Shelf(str(tmp_path / "shelf.json"))


def test_shelf_keeps_names_and_persists(tmp_path):
    from khervemol import shelf
    sh = _fresh_shelf(tmp_path)
    m1 = entries.build("compound", "methane")
    assert sh.add(m1) == "Molecule 1"
    assert sh.add(entries.build("compound", "water")) == "Molecule 2"
    assert sh.add(m1, "Fuel") == "Fuel"
    assert sh.names() == ["Molecule 1", "Molecule 2", "Fuel"]
    assert sh.formula("Molecule 2") == "H2O"
    assert sh.next_name() == "Molecule 3"
    # replaced, not duplicated, when the same name is kept again
    sh.add(entries.build("compound", "ammonia"), "fuel")
    assert len(sh) == 3 and sh.formula("fuel") == "H3N"
    sh.rename("Molecule 2", "Product")
    sh.move("Product", -1)
    again = shelf.Shelf(sh.path)                     # a new session
    assert again.names() == ["Product", "Molecule 1", "fuel"]
    assert again.model("Molecule 1").formula() == "CH4"
    assert shelf.token("Molecule 1") == "@Molecule_1"
    assert "@molecule_1" in again and "Nope" not in again
    again.remove("fuel")
    assert len(shelf.Shelf(sh.path)) == 2


def test_shelf_refuses_what_is_not_a_molecule(tmp_path):
    sh = _fresh_shelf(tmp_path)
    with pytest.raises(BuildError):
        sh.add(entries.build("crystal", "cu"))
    with pytest.raises(BuildError):
        sh.add(entries.build("reaction", "H2 + Cl2 -> HCl"))
    with pytest.raises(BuildError):
        sh.add(entries.build("compound", "water"), "!!!")
    from khervemol.model import Molecule
    with pytest.raises(BuildError):
        sh.add(Molecule([], []))                      # nothing to keep
    sh.add(entries.build("compound", "water"), "A")
    sh.add(entries.build("compound", "water"), "B")
    with pytest.raises(BuildError):
        sh.rename("A", "b")                           # taken
    with pytest.raises(KeyError):
        sh.rename("Nothing", "x")


def test_reaction_from_kept_molecules(tmp_path, monkeypatch):
    from khervemol import reactions, shelf
    sh = _fresh_shelf(tmp_path)
    monkeypatch.setattr(shelf, "_DEFAULT", sh)
    for key in ("methane", "oxygen", "carbon_dioxide", "water"):
        sh.add(entries.build("compound", key))
    rx = reactions.solve("@Molecule_1 + @Molecule_2 -> @Molecule_3 + "
                         "@Molecule_4")
    assert rx.balanced and [str(c) for c in rx.coefs] == ["1", "2", "1", "2"]
    assert rx.equation == "Molecule 1 + 2 Molecule 2 → Molecule 3 + 2 Molecule 4"
    scene = reactions.layout(rx)
    assert scene.anim is not None and len(scene.atoms) == 18
    with pytest.raises(BuildError) as err:
        reactions.solve("@Nope -> @Molecule_1")
    assert "shelf" in str(err.value)
    assert entries.build("mine", "Molecule 3").formula() == "CO2"


def test_insert_species_builds_the_equation():
    from khervemol.builders_ui import insert_species
    assert insert_species(" -> ", "@A", 0) == "@A -> "
    assert insert_species("@A -> ", "@B", 0) == "@A + @B -> "
    assert insert_species("@A + @B -> ", "@C", 1) == "@A + @B -> @C"
    assert insert_species("@A -> @C", "@D", 1) == "@A -> @C + @D"
    assert insert_species("H2 + O2 <=> H2O", "@X", 1) == \
        "H2 + O2 <=> H2O + @X"
    assert insert_species("", "@A", 0) == "@A -> "


def test_keep_and_use_in_the_window(qapp, tmp_path, monkeypatch):
    from PyQt5.QtWidgets import QInputDialog
    from khervemol import builders_ui, library, shelf
    from khervemol.mainwindow import MainWindow
    monkeypatch.setattr(shelf, "_DEFAULT", _fresh_shelf(tmp_path))
    w = MainWindow()
    assert w.shelf is shelf.default() and len(w.shelf) == 0
    answers = iter(["Molecule 1", "Molecule 2", "Product"])
    monkeypatch.setattr(QInputDialog, "getText",
                        lambda *a, **k: (next(answers), True))
    for key in ("methane", "oxygen", "carbon_dioxide"):
        w.viewer.set_molecule(library.make(key)
                              if key in library.names()
                              else entries.build("compound", key))
        w.keep_molecule()
    assert w.shelf.names() == ["Molecule 1", "Molecule 2", "Product"]
    assert w.shelf_panel.list.count() == 3
    # load one back, delete one, reorder
    w.shelf_panel.load_requested.emit("Molecule 1")
    assert w.viewer.mol.formula() == "CH4"
    w.move_kept("Product", -1)
    assert w.shelf.names()[1] == "Product"
    w.delete_kept("Molecule 2")
    assert len(w.shelf) == 2
    # the reaction dialog offers them and writes the equation
    d = builders_ui.ReactionDialog(shelf=w.shelf)
    d.new_eq.click()
    d.mine.setCurrentIndex(d.mine.findData("Molecule 1"))
    d.add_reactant.click()
    d.mine.setCurrentIndex(d.mine.findData("Product"))
    d.add_product.click()
    assert d.text.text() == "@Molecule_1 -> @Product"
    # Molecule 1 (CH4) cannot become CO2 on its own: reported, not raised
    assert not d.ok_btn.isEnabled()
    assert "balanced" in d.report.toPlainText().lower() \
        or "solution" in d.report.toPlainText().lower()


def test_diatomic_stands_up_or_lies_flat_on_a_surface():
    from khervemol import chem
    base = chem.surface_model("cu", "111")
    co = entries.build("compound", "carbon_monoxide")
    top = max(a[3] for a in base.atoms)
    up = chem.add_adsorbate(base, co, mode="upright", height=2.0)
    z = sorted(a[3] for a in up.atoms[len(base.atoms):])
    assert z[0] == pytest.approx(top + 2.0) and z[1] - z[0] > 1.0
    flat = chem.add_adsorbate(base, co, mode="flat", height=2.0)
    z = [a[3] for a in flat.atoms[len(base.atoms):]]
    assert max(z) - min(z) < 0.05


def test_library_crystals_stack_and_tilt_a_cell_as_a_defect(qapp):
    """The KhervePaint 'tilt a cell as a defect' engine works on every
    library crystal: a tilt moves atoms without renumbering them, drags the
    atoms shared with the neighbours, and an untilted block is unchanged."""
    from khervemol.mainwindow import MainWindow
    w = MainWindow()
    v = w.viewer
    w.load_entry("crystal", "srtio3?cells=2,2,2")
    m = v.mol
    assert m.can_stack and m.stacked and m.name == "crystal:srtio3"
    assert all(wd.isVisibleTo(v) for wd in v._crystal_widgets)   # the panel
    before = [list(a) for a in m.atoms]
    nbonds = len(m.bonds)
    assert set(m.members) == {f"{i},{j},{k}" for i in (0, 1)
                              for j in (0, 1) for k in (0, 1)}
    v.set_tilt("0,0,0", (0, 0, 20))
    assert len(m.atoms) == len(before) and len(m.bonds) == nbonds
    moved = [i for i, (a, b) in enumerate(zip(before, m.atoms))
             if abs(a[1] - b[1]) + abs(a[2] - b[2]) > 1e-6]
    assert 0 < len(moved) < len(m.atoms)          # a defect, not the whole grain
    assert [a[0] for a in m.atoms] == [a[0] for a in before]
    v.reset_tilts()
    assert all(abs(a[i] - b[i]) < 1e-9 for a, b in zip(before, m.atoms)
               for i in (1, 2, 3))
    # the supercell spinners rebuild it, and it round-trips through a file
    v.set_cells(3, 1, 1)
    assert m.cells == (3, 1, 1) and "3×1×1" in m.label
    assert len(m.atoms) != len(before)


def test_stacked_library_crystal_persists_with_its_tilt(tmp_path):
    from khervemol import document
    m = entries.build("crystal", "cu?cells=2,2,1")
    m.tilts = {"1,0,0": (10.0, 0.0, 0.0)}
    m.rebuild()
    path = str(tmp_path / "t.kmol")
    document.save(path, m, [], [])
    back, _a, _b = document.load(path)
    assert back.cells == (2, 2, 1) and [float(x) for x in back.tilts["1,0,0"]] == [10.0, 0.0, 0.0]
    assert back.can_stack and len(back.atoms) == len(m.atoms)
    for a, b in zip(m.atoms, back.atoms):
        assert a[1:4] == pytest.approx(b[1:4], abs=1e-6)


def test_cell_contents_variant_is_a_fixed_block():
    from khervemol import chem
    m = chem.crystal_model("nacl", (1, 1, 1), boundary=False)
    assert m.name == "cell:nacl" and not m.can_stack and len(m.atoms) == 8
