"""Tests for the OpenGL viewer: the GL-free parts (projection, hit-testing,
vertex arrays, drag units), the renderer switching / fallback logic, the
render styles and image export. Real-GL checks skip on the offscreen
platform, where `Viewer3D` uses the classic renderer.

Copyright (C) 2026 Gwilherm Kerherve

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
"""

import math

import pytest
from PyQt5.QtCore import QPoint
from PyQt5.QtGui import QImage

from khervemol import glview, library, model
from khervemol.viewer3d import Viewer3D


@pytest.fixture
def viewer(qapp):
    Viewer3D._gl_error = None
    v = Viewer3D()
    yield v
    Viewer3D._gl_error = None


def _scene(name="ethanol", style="ball_and_stick"):
    return glview.Scene(library.make(name), style)


# ----------------------------------------------------------- projection
@pytest.mark.parametrize("az,el", [(0.0, 0.0), (0.49, 0.35), (2.1, -0.8),
                                   (math.pi, math.pi / 2)])
def test_view_basis_matches_model_projection(az, el):
    """The GL camera projects exactly like model._proj (screen y flipped)."""
    r, u, f = glview.view_basis(az, el)
    for p in [(1.0, 2.0, 3.0), (-0.4, 0.9, 1.7), (0.0, 0.0, 0.0)]:
        sx, sy, depth = model._proj(*p, az, el)
        dot = lambda a: sum(a[k] * p[k] for k in range(3))
        assert dot(r) == pytest.approx(sx)
        assert -dot(u) == pytest.approx(sy)
        assert dot(f) == pytest.approx(depth)


def test_basis_is_orthonormal():
    r, u, f = glview.view_basis(1.1, 0.4)
    for a in (r, u, f):
        assert sum(c * c for c in a) == pytest.approx(1.0)
    assert sum(r[k] * u[k] for k in range(3)) == pytest.approx(0.0)
    assert sum(r[k] * f[k] for k in range(3)) == pytest.approx(0.0)


def test_fit_scale_does_not_depend_on_orientation():
    sc = _scene()
    assert sc.fit_ppa(600, 400) == pytest.approx(sc.fit_ppa(600, 400))
    # the fitted model always fits the box whatever the view
    ppa = sc.fit_ppa(600, 400)
    for az, el in [(0, 0), (1.0, 0.7), (2.5, -1.2)]:
        for x, y, _z in sc.screen(az, el, ppa, 600, 400):
            assert 0 <= x <= 600 and 0 <= y <= 400


def test_scene_spreads_bonds_like_the_classic_model():
    mol = library.make("ethanol")
    sc = glview.Scene(mol, "ball_and_stick")
    assert sc.factor == mol.bond
    d = math.dist(sc.pos[0], sc.pos[1])
    assert d == pytest.approx(model.distance(mol.atoms, 0, 1) * mol.bond)
    # space filling shows the true geometry
    assert glview.Scene(mol, "space_filling").factor == 1.0


# ------------------------------------------------------------- hit-testing
def test_pick_atom_hits_centres_and_misses_background():
    sc = _scene()
    az, el, w, h = 0.5, 0.3, 500, 400
    ppa = sc.fit_ppa(w, h)
    for i, (x, y, _z) in enumerate(sc.screen(az, el, ppa, w, h)):
        got = sc.pick_atom(x, y, az, el, ppa, w, h)
        assert got is not None
    assert sc.pick_atom(2, 2, az, el, ppa, w, h) is None


def test_pick_atom_prefers_the_nearer_sphere():
    # looking along +y (az = el = 0) depth == y, so O (y = 0.5) is nearer
    # the viewer and covers the centre of the overlapping C
    mol = model.Molecule([["C", 0, 0, 0], ["O", 0, 0.5, 0]], [], bond=1.0)
    sc = glview.Scene(mol)
    az, el, w, h = 0.0, 0.0, 300, 300
    ppa = sc.fit_ppa(w, h)
    assert sc.view_coords(az, el)[1][2] > sc.view_coords(az, el)[0][2]
    x, y, _ = sc.screen(az, el, ppa, w, h)[0]
    assert sc.pick_atom(x, y, az, el, ppa, w, h) == 1


def test_pick_bond_on_the_stick_between_atoms():
    sc = _scene()
    az, el, w, h = 0.5, 0.3, 500, 400
    ppa = sc.fit_ppa(w, h)
    pts = sc.screen(az, el, ppa, w, h)
    i, j, _ = sc.bonds[0]
    mx = (pts[i][0] + pts[j][0]) / 2
    my = (pts[i][1] + pts[j][1]) / 2
    assert sc.pick_bond(mx, my, az, el, ppa, w, h) is not None
    assert sc.pick_bond(2, 2, az, el, ppa, w, h) is None


def test_glview_bond_hit_ignores_points_on_an_atom(viewer):
    viewer.set_molecule(library.make("ethanol"))
    gl = glview.GLView(viewer)
    gl.resize(500, 400)
    ppa = gl._ppa()
    sc = gl.scene
    pts = sc.screen(viewer.mol.az, viewer.mol.el, ppa, 500, 400)
    on_atom = QPoint(int(pts[0][0]), int(pts[0][1]))
    assert gl._atom_at(on_atom) is not None
    assert gl._bond_at(on_atom) is None
    i, j, _ = sc.bonds[0]
    mid = QPoint(int((pts[i][0] + pts[j][0]) / 2),
                 int((pts[i][1] + pts[j][1]) / 2))
    if gl._atom_at(mid) is None:
        assert gl._bond_at(mid) is not None


def test_crystal_atoms_are_hit_testable_but_not_movable(viewer):
    """A click on a crystal atom picks a cell / recolour target, like the
    classic view (which tags crystal atoms too)."""
    viewer.set_molecule(library.make("fcc"))
    gl = glview.GLView(viewer)
    gl.resize(500, 400)
    assert not viewer.editable
    pts = gl.scene.screen(viewer.mol.az, viewer.mol.el, gl._ppa(), 500, 400)
    front = max(range(len(pts)), key=lambda i: pts[i][2])
    hit = gl._atom_at(QPoint(int(pts[front][0]), int(pts[front][1])))
    assert hit == front


# --------------------------------------------------------------- drag units
def test_drag_moves_the_atom_by_the_pixel_delta():
    """model.drag_atom with the scene's ppa shifts the projected atom by
    exactly the mouse delta (spread factor included)."""
    mol = library.make("ethanol")
    sc = glview.Scene(mol)
    frozen = sc.freeze()
    w, h = 500, 400
    ppa = sc.fit_ppa(w, h)
    az, el = mol.az, mol.el
    before = sc.screen(az, el, ppa, w, h)[3]
    model.drag_atom(mol.atoms, 3, 12.0, -7.0, az, el, sc.factor, ppa)
    sc2 = glview.Scene(mol, frozen=frozen)
    after = sc2.screen(az, el, ppa, w, h)[3]
    assert after[0] - before[0] == pytest.approx(12.0, abs=1e-6)
    assert after[1] - before[1] == pytest.approx(-7.0, abs=1e-6)


# ------------------------------------------------------------ vertex arrays
def test_sphere_data_is_a_quad_per_atom():
    sc = _scene()
    assert len(sc.sphere_data()) == len(sc.pos) * 6 * 9


def test_cylinder_data_counts():
    # C-O: two colours -> two half sticks; C-C: one; double -> two tubes
    mol = model.Molecule([["C", 0, 0, 0], ["O", 1.4, 0, 0], ["C", 0, 1.5, 0]],
                         [[0, 1, 2], [0, 2, 1]])
    sc = glview.Scene(mol)
    n = len(sc.cylinder_data()) // 13 // 6
    assert n == 2 * 2 + 1                   # double C=O halves + single C-C
    assert len(glview.Scene(mol, "space_filling").cylinder_data()) == 0


def test_cell_edges_become_cylinders():
    sc = _scene("fcc")
    edges = len(sc.edges)
    assert edges > 0
    assert len(sc.cylinder_data()) // 13 // 6 >= edges


def test_halo_data_colours_primary_and_co_selection():
    sc = _scene()
    data = sc.halo_data([0, 2], 2)
    assert len(data) == 2 * 6 * 9
    first = tuple(data[6:9])
    last = tuple(data[54 + 6:54 + 9])
    assert first == pytest.approx(glview.rgb(glview.CO_SEL_COLOR))
    assert last == pytest.approx(glview.rgb(glview.SEL_COLOR))
    assert len(sc.halo_data([99], None)) == 0


def test_styles_change_radii():
    ball = _scene("ethanol", "ball_and_stick")
    fill = _scene("ethanol", "space_filling")
    stick = _scene("ethanol", "sticks")
    assert all(f > b for f, b in zip(fill.radii, ball.radii))
    assert max(stick.radii) < min(ball.radii)
    assert stick.stick > ball.stick > fill.stick == 0


# ------------------------------------------------------ renderer / fallback
def test_offscreen_uses_the_classic_renderer(viewer):
    if Viewer3D.gl_available():
        pytest.skip("only meaningful on the offscreen platform")
    assert not Viewer3D.gl_available()
    assert viewer.renderer == "classic"
    assert viewer.set_renderer("gl") == "classic"      # quietly stays classic
    assert not viewer.style_combo.isEnabled()


def test_env_var_forces_classic(monkeypatch, qapp):
    monkeypatch.setattr(glview.QGuiApplication, "platformName",
                        staticmethod(lambda: "cocoa"))
    monkeypatch.delenv("KHERVEMOL_RENDERER", raising=False)
    assert glview.gl_available()
    monkeypatch.setenv("KHERVEMOL_RENDERER", "classic")
    assert not glview.gl_available()


def test_style_property_and_combo(viewer):
    assert viewer.style == "ball_and_stick"
    viewer.style = "space_filling"
    assert viewer.style == "space_filling"
    assert viewer.style_combo.currentData() == "space_filling"
    viewer.style_combo.setCurrentIndex(
        viewer.style_combo.findData("sticks"))
    assert viewer.style == "sticks"
    viewer.set_style("nonsense")
    assert viewer.style == "sticks"


def test_render_image_classic(viewer):
    viewer.set_molecule(library.make("water"))
    img = viewer.render_image(300, 200)
    assert isinstance(img, QImage)
    assert (img.width(), img.height()) == (300, 200)


def test_set_background_is_accepted_by_classic(viewer):
    viewer.set_background("#101820", "#203040")
    assert viewer._background == ("#101820", "#203040")
    viewer.set_background("#ffffff")
    assert viewer._background == ("#ffffff", "#ffffff")


def _force_gl(monkeypatch):
    monkeypatch.setattr(Viewer3D, "gl_available", staticmethod(lambda: True))


def test_swapping_renderers_keeps_molecule_selection_and_zoom(
        viewer, monkeypatch, qapp):
    _force_gl(monkeypatch)
    viewer.set_molecule(library.make("ethanol"))
    viewer.selection = [1, 3]
    viewer.view._zoom = 1.7
    assert viewer.set_renderer("gl") == "gl"
    assert isinstance(viewer.view, glview.GLView)
    assert viewer.view._zoom == 1.7
    assert viewer.selection == [1, 3]
    assert viewer.mol.name == "ethanol"
    assert viewer.set_renderer("classic") == "classic"
    assert viewer.view._zoom == 1.7
    assert viewer.selection == [1, 3]


def test_gl_failure_falls_back_to_classic_with_a_note(viewer, monkeypatch,
                                                      qapp):
    _force_gl(monkeypatch)
    viewer.set_renderer("gl")
    assert viewer.renderer == "gl"
    seen = []
    viewer.renderer_changed.connect(seen.append)
    viewer.view.failed.emit("shader link: boom")
    qapp.processEvents()
    qapp.processEvents()
    assert viewer.renderer == "classic"
    assert seen == ["classic"]
    assert "boom" in viewer.status.text()
    assert "classic" in viewer.renderer_note
    # GL stays off for later viewers in this process
    monkeypatch.undo()
    assert Viewer3D._gl_error is not None
    assert not Viewer3D.gl_available()


def test_glview_signals_and_interface(viewer):
    viewer.set_molecule(library.make("water"))
    gl = glview.GLView(viewer)
    for name in ("atom_clicked", "rotated", "atom_moved", "failed"):
        assert hasattr(gl, name)
    assert gl._zoom == 1.0
    gl.reset_zoom()
    gl.rebuild()                            # no context needed to lay out
    assert gl.scene.pos


def test_glview_offscreen_render_image_is_none_without_context(viewer):
    gl = glview.GLView(viewer)
    assert gl.render_image(100, 100) is None


# ------------------------------------------------------------ real GL only
def test_gl_render_image_draws_the_molecule(viewer, qapp):
    if not Viewer3D.gl_available():      # needs a real (non-offscreen) platform
        pytest.skip("needs a real (non-offscreen) OpenGL platform")
    viewer.resize(700, 600)
    viewer.show()
    viewer.set_molecule(library.make("benzene"))
    for _ in range(30):
        qapp.processEvents()
    img = viewer.render_image(400, 300)
    assert (img.width(), img.height()) == (400, 300)
    corner = img.pixelColor(2, 2)
    centre = img.pixelColor(200, 150)
    assert corner != centre


# ------------------------------------------------------------ annotations
def _annotated(factor=1.0):
    mol = model.Molecule(
        [["O", 0, 0, 0], ["H", 0.96, 0, 0]], [[0, 1, 1]], name="reaction",
        crystal=True, bond=factor,
        notes=[{"kind": "text", "text": "H2O", "pos": (-20.0, 0.0, -2.0),
                "size": 1.0, "color": "#4a5560", "bold": False},
               {"kind": "arrow", "p1": (5.0, 0, 0), "p2": (15.0, 0, 0),
                "color": "#1c2b36", "double": True, "size": 1.0}])
    return mol


def test_notes_are_in_the_scene_and_the_fit_bounds():
    sc = glview.Scene(_annotated())
    assert len(sc.notes) == 2 and sc.tight
    assert sc.bound >= 17.0                 # text at x = -20 is inside
    w, h = 800, 300
    az, el = 0.0, 0.0
    ppa = sc.fit_ppa(w, h, az, el)
    for n in sc.notes:
        for x, y in sc.note_box(n, az, el):
            pan = sc._view(az, el)[1]
            sx = w / 2 + (x - pan[0]) * ppa
            sy = h / 2 - (y - pan[1]) * ppa
            assert 0 <= sx <= w and 0 <= sy <= h


def test_wide_scene_fits_tighter_than_the_bounding_sphere():
    sc = glview.Scene(_annotated())
    tight = sc.fit_ppa(800, 300, 0.0, 0.0)
    sphere = sc.fit_ppa(800, 300)
    assert tight > sphere


def test_notes_spread_with_the_bond_factor():
    a = glview.Scene(_annotated(1.0))
    b = glview.Scene(_annotated(2.0))
    assert b.notes[1]["p2"][0] > a.notes[1]["p2"][0]


def test_screen_point_matches_atom_projection():
    mol = _annotated()
    sc = glview.Scene(mol)
    az, el, w, h = 0.6, 0.3, 500, 400
    ppa = sc.fit_ppa(w, h, az, el)
    ax, ay, _ = sc.screen(az, el, ppa, w, h)[1]
    px, py = sc.screen_point(tuple(sc.pos[1]), az, el, ppa, w, h)
    assert (px, py) == pytest.approx((ax, ay))


def test_plain_structures_have_no_notes():
    sc = _scene()
    assert sc.notes == [] and not sc.tight


def test_status_wording_for_fixed_structures(viewer):
    viewer.set_molecule(_annotated())
    assert "read-only scene" in viewer.status.text()
    assert viewer._fixed_kind() == "read-only scene"
    viewer.set_molecule(library.make("fcc"))
    assert viewer._fixed_kind() == "fixed lattice"
    mol = library.make("fcc")
    mol.name = "crystal:custom"
    viewer.set_molecule(mol)
    assert viewer._fixed_kind() == "fixed lattice"
    assert "drag to rotate" in viewer.status.text()
    viewer.set_molecule(model.Molecule([["Ar", 0, 0, 0]], [], name="x",
                                       crystal=True))
    assert viewer._fixed_kind() == "fixed structure"


def test_gl_render_image_draws_notes(viewer, qapp):
    if not Viewer3D.gl_available():
        pytest.skip("needs a real (non-offscreen) OpenGL platform")
    viewer.resize(900, 500)
    viewer.show()
    viewer.set_molecule(_annotated())
    for _ in range(30):
        qapp.processEvents()
    img = viewer.render_image(800, 300)
    # the arrow is dark on the light gradient somewhere along the centre row
    dark = [x for x in range(800) if img.pixelColor(x, 150).lightness() < 90]
    assert dark


# ------------------------------------------------- colours / polyhedra / cells
def test_per_atom_colour_override_reaches_the_vertex_data():
    mol = model.Molecule([["C", 0, 0, 0], ["C", 1.5, 0, 0, "#ff00aa"]],
                         [[0, 1, 1]], bond=1.0)
    sc = glview.Scene(mol)
    assert sc.colors[0] == pytest.approx(glview.rgb(glview.elements.color("C")))
    assert sc.colors[1] == pytest.approx(glview.rgb("#ff00aa"))
    data = sc.sphere_data()
    assert tuple(data[54 + 6:54 + 9]) == pytest.approx(glview.rgb("#ff00aa"))
    # the recoloured atom's half of the stick takes its colour too
    cyl = sc.cylinder_data()
    assert len(cyl) // 13 // 6 == 2


def test_crystal_colour_map_is_applied():
    mol = library.make("fcc")
    key = "Al@" + [a[4] for a in mol.atoms if len(a) > 4][0]
    mol.colors[key] = "#00aa44"
    sc = glview.Scene(mol)
    assert glview.rgb("#00aa44") in sc.colors
    assert len(set(sc.colors)) >= 2          # corners and face centres differ


def test_site_tints_colour_the_spheres():
    sc = glview.Scene(library.make("fcc"))
    assert len(set(sc.colors)) == 2


def test_polyhedra_faces_and_buffers():
    mol = library.make("perovskite")
    assert glview.Scene(mol).faces() == []
    assert len(glview.Scene(mol).poly_data()) == 0
    mol.poly = True
    sc = glview.Scene(mol)
    faces = sc.faces()
    assert len(faces) == 8                   # the TiO6 octahedron
    data = sc.poly_data()
    assert len(data) == 8 * 3 * 9            # 8 triangles
    # outlines join the cylinder buffer
    assert len(sc.cylinder_data()) > len(glview.Scene(
        library.make("perovskite")).cylinder_data())
    # the normal of a triangle is a unit vector
    nx, ny, nz = data[3:6]
    assert math.sqrt(nx * nx + ny * ny + nz * nz) == pytest.approx(1.0, abs=1e-5)


def test_polyhedra_use_the_centre_atoms_colour():
    mol = library.make("perovskite")
    mol.poly = True
    mol.colors["Ti"] = "#123456"
    sc = glview.Scene(mol)
    assert sc.faces()[0][1] == pytest.approx(glview.rgb("#123456"))


def test_legend_layout_reserves_room_and_lists_each_colour(viewer):
    viewer.set_molecule(library.make("fcc"))
    gl = glview.GLView(viewer)
    gl.resize(600, 400)
    assert gl._legend(600, 400) is None
    assert gl._box(600, 400) == (600, 400)
    viewer.legend_btn.setChecked(True)
    entries, r, fpx, lw = gl._legend(600, 400)
    assert len(entries) == 2                 # corner + face-centre tints
    assert 0 < lw <= 600 * 0.45
    assert gl._box(600, 400)[0] == pytest.approx(600 - lw)
    # the fit shrinks to make room, so the model never sits under the key
    assert gl._ppa(600, 400) <= gl.scene.fit_ppa(600, 400, viewer.mol.az,
                                                 viewer.mol.el) * gl._zoom


def test_legend_follows_recolouring(viewer):
    viewer.set_molecule(library.make("fcc"))
    gl = glview.GLView(viewer)
    viewer.legend_btn.setChecked(True)
    gl.rebuild()
    before = [c for _e, _l, c in gl.legend_entries()]
    viewer.selection = [0]
    viewer.mol.colors["Al"] = "#00aa44"
    gl.rebuild()
    after = [c for _e, _l, c in gl.legend_entries()]
    assert before != after and "#00aa44" in after


def test_rebuild_reuses_the_scene_until_the_geometry_changes(viewer):
    viewer.set_molecule(library.make("ethanol"))
    gl = glview.GLView(viewer)
    gl.rebuild()
    first = gl.scene
    viewer.selection = [1]
    gl.rebuild()                              # selection only: same scene
    assert gl.scene is first
    viewer.mol.atoms[3][1] += 0.2
    gl.rebuild()
    assert gl.scene is not first
    viewer.style = "sticks"
    gl.rebuild()
    assert gl.scene.style == "sticks"


def test_tilt_cell_ring_atoms_use_the_cell_colour(viewer):
    viewer.set_molecule(library.make("perovskite"))
    viewer.set_cells(2, 2, 2)
    viewer.select_atom(5)
    cell = viewer.tilt_cell_atoms()
    assert cell and viewer.mol.stacked
    sc = glview.Scene(viewer.mol)
    ring = sc.halo_data([i for i in cell if i != 5], None, glview.CELL_COLOR)
    assert len(ring) == (len(cell) - (5 in cell)) * 6 * 9
    assert tuple(ring[6:9]) == pytest.approx(glview.rgb(glview.CELL_COLOR))


def test_tilting_one_cell_keeps_the_fit_and_the_selection(viewer):
    viewer.set_molecule(library.make("perovskite"))
    viewer.set_cells(2, 2, 2)
    viewer.select_atom(5)
    before = glview.Scene(viewer.mol)
    viewer.set_tilt(viewer.mol.cell_of(5), [0, 0, 35])
    assert viewer.mol.tilts
    assert viewer.selection == [5]
    after = glview.Scene(viewer.mol)
    assert after.center == pytest.approx(before.center)
    assert after.bound == pytest.approx(before.bound)
    assert after.fit_ppa(600, 400) == pytest.approx(before.fit_ppa(600, 400))
    # ...while the atoms themselves did move
    assert after.pos != before.pos


def test_tilt_and_recolour_rebuild_through_the_gl_view(viewer):
    viewer.set_molecule(library.make("perovskite"))
    gl = glview.GLView(viewer)
    gl.rebuild()
    viewer.set_cells(2, 2, 2)
    gl.rebuild()
    assert len(gl.scene.pos) == len(viewer.mol.atoms)
    viewer.select_atom(3)
    viewer.pick_color("#abcdef")
    gl.rebuild()
    assert glview.rgb("#abcdef") in gl.scene.colors


def test_gl_render_image_with_polyhedra_and_legend(viewer, qapp):
    if not Viewer3D.gl_available():
        pytest.skip("needs a real (non-offscreen) OpenGL platform")
    viewer.resize(900, 600)
    viewer.show()
    mol = library.make("perovskite")
    mol.poly = True
    viewer.set_molecule(mol)
    viewer.legend_btn.setChecked(True)
    for _ in range(30):
        qapp.processEvents()
    img = viewer.render_image(800, 500)
    assert (img.width(), img.height()) == (800, 500)
    # the legend strip on the right carries dark text on the light gradient
    assert any(img.pixelColor(x, y).lightness() < 90
               for x in range(600, 800, 3) for y in range(20, 120, 3))
    viewer.set_cells(2, 2, 2)
    viewer.select_atom(5)
    viewer.set_tilt(viewer.mol.cell_of(5), [0, 0, 20])
    for _ in range(20):
        qapp.processEvents()
    assert viewer.render_image(400, 300) is not None
