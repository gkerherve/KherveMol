"""Reaction animation: atom mapping, the film, and the viewer controls.

Copyright (C) 2026 Gwilherm Kerherve

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
"""

import math

import pytest

from khervemol import document, reactions


def _film(eq):
    m, rx = reactions.reaction_model(eq)
    return m, m.anim


def test_mapping_is_a_bijection_that_keeps_elements():
    m, a = _film("CH4 + 2 O2 -> CO2 + 2 H2O")
    assert sorted(a.pi) == list(range(len(a.pi)))
    for i, p in enumerate(a.pi):
        assert a.reac.elements[i] == a.prod.elements[p]


def test_mapping_keeps_bonds_that_survive():
    # ethene + H2 -> ethane: the C-C and four C-H bonds are all kept
    _m, a = _film("ethene + H2 -> ethane")
    rb = {frozenset(b[:2]) for b in a.rbonds}
    pb = {frozenset(b[:2]) for b in a.pbonds}
    assert len(rb & pb) == 5
    # N2 + 3 H2 -> 2 NH3: every H2 splits, each NH3 takes three H
    _m, a = _film("N2 + 3 H2 -> 2 NH3")
    assert len(a.pbonds) == 6 and len(a.rbonds) == 4


def test_no_film_when_drawn_atoms_differ():
    m, rx = reactions.reaction_model("1/2 O2 + H2 -> H2O")
    assert m.anim is None


def test_every_example_has_a_film():
    for name, eq in reactions.EXAMPLES.items():
        m, _rx = reactions.reaction_model(eq)
        assert m.anim is not None, name


def test_film_keyframes_and_bond_switch():
    m, a = _film("H2 + Cl2 -> HCl")
    n = len(a.reac.elements)
    for i in range(n):
        assert a.position(i, 0.0) == pytest.approx(a.reac.spread[i])
        assert a.position(i, 1.0) == pytest.approx(
            a.prod.spread[a.pi[i]])
    assert a.bonds_at(0.1) == [list(b) for b in a.rbonds]
    assert a.bonds_at(0.9) == [list(b) for b in a.pbonds]
    # between BREAK and FORM only the bonds both sides share remain: H2 + Cl2
    # -> 2 HCl shares none, so no bond is drawn while the atoms rearrange
    assert a.bonds_at(0.5) == []
    # reactants start left of the products' final place
    xr = sum(a.position(i, 0.0)[0] for i in range(n)) / n
    xp = sum(a.position(i, 1.0)[0] for i in range(n)) / n
    assert xr < 0 < xp


def test_apply_and_restore_the_static_scene():
    m, a = _film("2 H2 + O2 -> 2 H2O")
    static_atoms = [list(x) for x in m.atoms]
    static_notes = len(m.notes)
    a.apply(m, 0.5)
    assert len(m.atoms) == 6                 # reactant atoms only
    assert any(n.get("text") == "Atoms rearrange" for n in m.notes)
    a.restore(m)
    assert m.atoms == static_atoms and len(m.notes) == static_notes


def test_reaction_persists_and_refilms(tmp_path):
    m, _ = reactions.reaction_model("N2 + 3 H2 <=> 2 NH3")
    path = str(tmp_path / "r.kmol")
    document.save(path, m, [], [])
    back, _a, _b = document.load(path)
    assert back.reaction == m.reaction and back.anim is None
    assert reactions.attach_animation(back)
    assert back.anim is not None and len(back.anim.pi) == len(m.anim.pi)


def test_viewer_plays_scrubs_and_stops(qapp):
    from khervemol.viewer3d import Viewer3D
    v = Viewer3D()
    m, _ = reactions.reaction_model("CH4 + 2 O2 -> CO2 + 2 H2O")
    v.set_molecule(m)
    assert v.has_animation and not v.animating
    static = len(v.mol.atoms)
    v.set_progress(0.6)
    assert v.animating and len(v.mol.atoms) < static
    v.play()
    assert v.playing
    v._anim_tick()
    assert v._anim_p > 0.0
    v.pause()
    assert not v.playing
    v.anim_slider.setValue(1000)
    assert v._anim_p == pytest.approx(1.0)
    v.stop_animation()
    assert not v.animating and len(v.mol.atoms) == static
    # a plain molecule shows no controls
    from khervemol import library
    v.set_molecule(library.make("water"))
    assert not v.has_animation


def test_run_to_the_end_stops_unless_looping(qapp):
    from khervemol.viewer3d import Viewer3D
    v = Viewer3D()
    v.set_molecule(reactions.reaction_model("H2 + Cl2 -> HCl")[0])
    v.play()
    v._anim_p = 0.9999
    v._anim_tick()
    assert not v.playing and v._anim_p == pytest.approx(1.0)
    v.loop_btn.setChecked(True)
    v.play()
    v._anim_p = 0.9999
    v._anim_tick()
    assert v.playing and v._anim_p == 0.0
    v.pause()


def test_broken_bonds_vanish_before_new_ones_form():
    _m, a = _film("ethene + H2 -> ethane")
    mid = a.bonds_at(0.5)
    common = {frozenset(b[:2]) for b in a.rbonds} & \
        {frozenset(b[:2]) for b in a.pbonds}
    assert {frozenset(b[:2]) for b in mid} == common
    assert 0 < len(mid) < len(a.rbonds) + 1


def test_loading_a_reaction_plays_it_once(qapp):
    from khervemol.mainwindow import MainWindow
    w = MainWindow()
    w.load_entry("reaction", "H2 + Cl2 -> HCl")
    w.viewer.play(True)                      # what the delayed call does
    assert w.viewer.playing
    w.viewer._anim_p = 0.9999
    w.viewer._anim_tick()
    assert not w.viewer.playing and not w.viewer.animating   # back to equation
