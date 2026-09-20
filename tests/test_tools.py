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
            elif not act.isSeparator() and act.data() is None:
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
