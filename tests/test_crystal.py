"""Crystallography: lattice systems, supercells, tilts, polyhedra, colours.

Copyright (C) 2026 Gwilherm Kerherve

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
"""

import math

import pytest

from khervemol import lattices, library, molcolor, supercell


# ------------------------------------------------------------ lattice systems
def test_every_lattice_system_is_registered_as_a_crystal():
    for name in lattices.PARAMS:
        assert name in library.names()
        assert library.is_crystal(name)
        assert library.can_stack(name)


@pytest.mark.parametrize("name", list(lattices.PARAMS))
def test_a_lattice_cell_is_eight_corners_and_twelve_edges(name):
    atoms, bonds, edges, _rscale = library.model_data(name)
    assert len(atoms) == 8
    assert len(edges) == 12
    assert not bonds


def test_lattice_vectors_reproduce_the_requested_parameters():
    a, b, c, al, be, ga = 2.0, 3.0, 4.0, 80.0, 70.0, 100.0
    va, vb, vc = lattices.lattice_vectors(a, b, c, al, be, ga)

    def norm(v):
        return math.sqrt(sum(x * x for x in v))

    def ang(u, v):
        dot = sum(u[k] * v[k] for k in range(3))
        return math.degrees(math.acos(dot / (norm(u) * norm(v))))

    assert norm(va) == pytest.approx(a)
    assert norm(vb) == pytest.approx(b)
    assert norm(vc) == pytest.approx(c)
    assert ang(vb, vc) == pytest.approx(al)
    assert ang(va, vc) == pytest.approx(be)
    assert ang(va, vb) == pytest.approx(ga)


def test_a_skewed_cell_stacks_along_its_own_vectors():
    """A monoclinic supercell must lean, not sit on an orthogonal grid: the
    second cell along c is offset in x as well as z."""
    atoms, _b, _e, _r = library.model_data("monoclinic", (1, 1, 2))
    xs = [a[1] for a in atoms]
    zs = [a[3] for a in atoms]
    assert max(zs) > 0
    assert max(xs) > lattices.PARAMS["monoclinic"][1] + 1e-6


# ------------------------------------------------------------------ supercell
def test_stacking_de_duplicates_the_shared_corners():
    """Two simple-cubic cells side by side share a face: 8 + 8 corners must
    come back as 12, not 16."""
    atoms, _b, edges, _r = library.model_data("simple_cubic", (2, 1, 1))
    assert len(atoms) == 12
    coords = {(round(a[1], 3), round(a[2], 3), round(a[3], 3)) for a in atoms}
    assert len(coords) == len(atoms)
    seen = {frozenset((tuple(round(v, 3) for v in e[0]),
                       tuple(round(v, 3) for v in e[1]))) for e in edges}
    assert len(seen) == len(edges)


@pytest.mark.parametrize("name", ["simple_cubic", "bcc", "fcc", "diamond",
                                  "nacl", "cscl", "perovskite", "fluorite",
                                  "hexagonal", "triclinic"])
def test_a_supercell_has_more_atoms_but_no_duplicates(name):
    one = library.model_data(name)[0]
    many = library.model_data(name, (2, 2, 2))[0]
    assert len(many) > len(one)
    coords = {(round(a[1], 3), round(a[2], 3), round(a[3], 3)) for a in many}
    assert len(coords) == len(many)


def test_hcp_does_not_stack():
    assert not library.can_stack("hcp")
    assert len(library.model_data("hcp", (2, 2, 2))[0]) == \
        len(library.model_data("hcp")[0])


def test_owners_name_the_home_cell_of_every_atom():
    owners = []
    atoms, _b, _e, _r = library.model_data("simple_cubic", (2, 2, 1),
                                           owners=owners)
    assert len(owners) == len(atoms)
    assert set(owners) <= set(supercell.cell_keys((2, 2, 1)))
    assert owners[0] == "0,0,0"


def test_in_range_rejects_a_cell_outside_the_supercell():
    assert supercell.in_range("1,1,0", (2, 2, 1))
    assert not supercell.in_range("2,0,0", (2, 2, 1))
    assert not supercell.in_range("nonsense", (2, 2, 1))


# ---------------------------------------------------------------------- tilts
def test_a_tilt_moves_that_cell_without_adding_atoms():
    plain = library.model_data("simple_cubic", (2, 2, 2))[0]
    tilted = library.model_data("simple_cubic", (2, 2, 2),
                                tilts={"0,0,0": (25, 0, 0)})[0]
    assert len(tilted) == len(plain)
    moved = sum(1 for a, b in zip(plain, tilted)
                if abs(a[1] - b[1]) + abs(a[2] - b[2]) + abs(a[3] - b[3]) > 1e-6)
    assert moved > 0


def test_an_untilted_far_corner_stays_put():
    """A tilt is a defect, not a rigid grain: it drags the atoms it shares
    with its neighbours, but a corner no tilted cell owns must not move."""
    cells = (3, 1, 1)
    plain = library.model_data("simple_cubic", cells)[0]
    tilted = library.model_data("simple_cubic", cells,
                                tilts={"0,0,0": (30, 0, 0)})[0]
    far = max(range(len(plain)), key=lambda k: plain[k][1])
    assert plain[far][1] == pytest.approx(tilted[far][1])
    assert plain[far][2] == pytest.approx(tilted[far][2])
    assert plain[far][3] == pytest.approx(tilted[far][3])


def test_a_zero_tilt_is_the_same_as_no_tilt():
    plain = library.model_data("bcc", (2, 1, 1))[0]
    zero = library.model_data("bcc", (2, 1, 1), tilts={"0,0,0": (0, 0, 0)})[0]
    assert plain == zero


# ------------------------------------------------------------- site colouring
@pytest.mark.parametrize("name,site", [("bcc", "body"), ("fcc", "face"),
                                       ("hcp", "mid"), ("diamond", "inner")])
def test_hidden_lattice_sites_are_tinted(name, site):
    """A body/face centre of the same element as the corners would vanish
    against them, so the builder tints it."""
    atoms = library.model_data(name)[0]
    tints = {molcolor.tint(a) for a in atoms if molcolor.tint(a)}
    assert molcolor.SITE_COLORS[site] in tints


def test_the_site_tint_survives_stacking():
    atoms = library.model_data("bcc", (2, 2, 2))[0]
    body = [a for a in atoms if molcolor.tint(a) == molcolor.SITE_COLORS["body"]]
    assert len(body) == 8            # one body centre per cell, never shared


def test_a_colour_key_separates_element_from_site():
    corner = ["Fe", 0, 0, 0]
    centre = ["Fe", 1, 1, 1, molcolor.SITE_COLORS["body"]]
    assert molcolor.color_key(corner) == "Fe"
    assert molcolor.color_key(centre) != "Fe"
    colors = {molcolor.color_key(centre): "#ff0000"}
    assert molcolor.atom_color(centre, colors) == "#ff0000"
    assert molcolor.atom_color(corner, colors) != "#ff0000"


def test_apply_colors_repaints_a_regenerated_lattice():
    atoms = library.model_data("nacl")[0]
    painted = molcolor.apply_colors(atoms, {"Na": "#123456"})
    assert any(a[4] == "#123456" for a in painted if len(a) > 4)


def test_the_legend_lists_one_row_per_colour():
    atoms = library.model_data("perovskite")[0]
    entries = molcolor.legend_entries(atoms)
    assert {e[0] for e in entries} == {"Ca", "Ti", "O"}
    specs = molcolor.legend_specs(entries)
    assert sum(1 for s in specs if s["shape"] == "text") == len(entries)


# ----------------------------------------------------------------- polyhedra
def test_perovskite_draws_an_octahedron_per_b_site():
    atoms, bonds = library.model_data("perovskite")[:2]
    assert molcolor.has_polyhedra(atoms, bonds)
    faces = molcolor.coordination_polyhedra(atoms, bonds)
    assert len(faces) == 8                        # TiO6 → 8 triangles
    assert all(len(f) == 3 for f, _c in faces)


def test_diamond_draws_a_tetrahedron_per_interior_carbon():
    atoms, bonds = library.model_data("diamond")[:2]
    faces = molcolor.coordination_polyhedra(atoms, bonds)
    assert len(faces) == 4 * 4                    # 4 interior C × 4 faces


def test_a_lattice_with_no_bonds_has_no_polyhedra():
    atoms, bonds = library.model_data("simple_cubic")[:2]
    assert not molcolor.has_polyhedra(atoms, bonds)
    assert molcolor.coordination_polyhedra(atoms, bonds) == []


def test_coordination_faces_of_an_octahedron():
    pts = [(1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)]
    faces = lattices.coordination_faces(pts)
    assert len(faces) == 8
    assert all(len(f) == 3 for f in faces)


def test_coordination_faces_of_a_cube_are_squares():
    pts = [(x, y, z) for x in (-1, 1) for y in (-1, 1) for z in (-1, 1)]
    faces = lattices.coordination_faces(pts)
    assert len(faces) == 6
    assert all(len(f) == 4 for f in faces)


# ------------------------------------------------------------- Molecule glue
def test_molecule_rebuilds_itself_for_a_new_supercell():
    mol = library.make("fcc")
    one = len(mol.atoms)
    mol.cells = (2, 2, 2)
    mol.rebuild()
    assert len(mol.atoms) > one
    assert len(mol.owners) == len(mol.atoms)
    assert mol.cell_of(0) == "0,0,0"


def test_prune_tilts_drops_cells_that_left_the_supercell():
    mol = library.make("bcc")
    mol.cells = (3, 3, 3)
    mol.tilts = {"2,2,2": [10, 0, 0], "0,0,0": [5, 0, 0]}
    mol.cells = (2, 2, 2)
    mol.prune_tilts()
    assert set(mol.tilts) == {"0,0,0"}


def test_polyhedra_specs_are_translucent_polygons():
    mol = library.make("perovskite")
    mol.poly = True
    specs = mol.specs(400, 400)
    polys = [s for s in specs if s["shape"] == "polygon"]
    assert polys
    assert all(0 < s["opacity"] < 1 for s in polys)


def test_a_tilt_does_not_rescale_the_rest_of_the_supercell():
    """The layout is anchored to the untilted geometry, so tilting one cell
    must leave the other cells drawn where they were."""
    mol = library.make("simple_cubic")
    mol.cells = (3, 1, 1)
    mol.rebuild()
    before = mol.specs(400, 400)
    mol.tilts = {"0,0,0": [30, 0, 0]}
    mol.rebuild()
    after = mol.specs(400, 400)
    far_before = max(s["x"] for s in before if s["shape"] == "circle")
    far_after = max(s["x"] for s in after if s["shape"] == "circle")
    assert far_before == pytest.approx(far_after, abs=0.5)


# ------------------------------------------------------------- viewer wiring
def _viewer(qapp):
    from khervemol.viewer3d import Viewer3D
    return Viewer3D()


def test_the_stacking_row_is_crystals_only(qapp):
    v = _viewer(qapp)
    v.set_molecule(library.make("perovskite"))
    assert v.cell_spins[0].isVisibleTo(v)
    v.set_molecule(library.make("ethanol"))
    assert not v.cell_spins[0].isVisibleTo(v)


def test_setting_cells_from_the_viewer_tiles_the_crystal(qapp):
    v = _viewer(qapp)
    v.set_molecule(library.make("fcc"))
    one = len(v.mol.atoms)
    v.set_cells(2, 2, 2)
    assert len(v.mol.atoms) > one
    assert [sp.value() for sp in v.cell_spins] == [2, 2, 2]


def test_tilting_keeps_a_cell_of_the_same_atom_selected(qapp):
    """Re-tiling renumbers the atoms, so the viewer must re-select an atom
    of the tilted cell — otherwise the next spin tick hits another cell."""
    v = _viewer(qapp)
    v.set_molecule(library.make("simple_cubic"))
    v.set_cells(2, 1, 1)
    v.set_tilt("1,0,0", (15, 0, 0))
    assert v.mol.tilts == {"1,0,0": [15, 0, 0]}
    assert v.mol.cell_of(v.selected) == "1,0,0"
    v.reset_tilts()
    assert v.mol.tilts == {}


def test_recolouring_a_crystal_keys_on_element_and_site(qapp):
    v = _viewer(qapp)
    v.set_molecule(library.make("bcc"))
    body = next(i for i, a in enumerate(v.mol.atoms)
                if molcolor.tint(a) == molcolor.SITE_COLORS["body"])
    v.select_atom(body)
    key = v.pick_color("#ff00ff")
    assert v.mol.colors[key] == "#ff00ff"
    assert key != "Fe"                       # the corners keep their colour
    v.reset_colors()
    assert not v.mol.colors


def test_recolouring_a_molecule_rides_on_the_atom(qapp):
    v = _viewer(qapp)
    v.set_molecule(library.make("water"))
    v.select_atom(0)
    v.pick_color("#00ff00")
    assert v.mol.atoms[0][4] == "#00ff00"
    assert not v.mol.colors
    v.reset_colors()
    assert len(v.mol.atoms[0]) == 4


def test_the_legend_toggle_adds_specs_to_the_export(qapp):
    v = _viewer(qapp)
    v.set_molecule(library.make("nacl"))
    plain = len(v.export_specs())
    v.legend_btn.setChecked(True)
    assert len(v.export_specs()) > plain


def test_the_polyhedra_toggle_is_off_for_a_bondless_lattice(qapp):
    v = _viewer(qapp)
    v.set_molecule(library.make("simple_cubic"))
    assert not v.poly_btn.isEnabled()
    v.set_molecule(library.make("perovskite"))
    assert v.poly_btn.isEnabled()


def test_a_crystal_atom_can_be_clicked_even_though_it_cannot_be_dragged(qapp):
    v = _viewer(qapp)
    v.set_molecule(library.make("cscl"))
    assert not v.editable
    assert any("_atom" in s for s in v.render_specs(400, 400))


def test_the_lattice_state_round_trips_through_a_kmol_file(tmp_path):
    from khervemol import document
    mol = library.make("perovskite")
    mol.cells = (2, 1, 1)
    mol.tilts = {"1,0,0": [10, 0, 5]}
    mol.poly = True
    mol.rebuild()
    mol.colors = {"Ti": "#ff00ff"}
    path = tmp_path / "x.kmol"
    document.save(str(path), mol, [], [])
    back, _sa, _sb = document.load(str(path))
    assert back.cells == (2, 1, 1)
    assert back.tilts == {"1,0,0": [10, 0, 5]}
    assert back.colors == {"Ti": "#ff00ff"}
    assert back.poly is True
    assert len(back.atoms) == len(mol.atoms)
    assert len(back.owners) == len(back.atoms)


def test_a_version_1_file_still_loads(tmp_path):
    import json
    from khervemol import document
    path = tmp_path / "old.kmol"
    path.write_text(json.dumps({
        "format": "khervemol", "version": 1,
        "mol3d": {"name": "water", "label": "Water", "crystal": False,
                  "atoms": [["O", 0, 0, 0], ["H", 1, 0, 0]],
                  "bonds": [[0, 1, 1]], "edges": None},
        "sketch2d": {"atoms": [], "bonds": []}}), encoding="utf-8")
    mol, _sa, _sb = document.load(str(path))
    assert mol.cells == (1, 1, 1)
    assert mol.tilts == {} and mol.colors == {} and mol.poly is False


def test_polygons_survive_the_svg_export():
    from khervemol import svgexport
    mol = library.make("perovskite")
    mol.poly = True
    specs, w, h = svgexport.normalize(mol.specs(400, 400))
    root = svgexport.specs_to_svg(specs, w, h)
    tags = [el.tag.rsplit("}", 1)[-1] for el in root]
    assert "polygon" in tags


# ------------------------------------------------------------ atom labels
def test_the_labels_toggle_actually_emits_text():
    """The `label` flag used to set a key nothing rendered, so the viewer's
    Labels button did nothing."""
    mol = library.make("water")
    plain = mol.specs(300, 300)
    labelled = mol.specs(300, 300, labels=True)
    texts = [s for s in labelled if s["shape"] == "text"]
    assert len(texts) == len(mol.atoms)
    assert {s["text"] for s in texts} == {"H", "O"}
    assert all(s["anchor"] == "center" for s in texts)
    assert len(labelled) > len(plain)


def test_a_label_reads_against_its_sphere():
    from khervemol import model
    on_blue = model.atom_specs(0, 0, 10, "N", label=True)[1]["stroke"]
    on_white = model.atom_specs(0, 0, 10, "H", label=True)[1]["stroke"]
    on_yellow = model.atom_specs(0, 0, 10, "S", label=True)[1]["stroke"]
    assert on_blue == "#ffffff"        # nitrogen's blue is dark to the eye
    assert on_white == "#161616"
    assert on_yellow == "#161616"


def test_a_centred_label_is_placed_on_its_centre(qapp):
    from khervemol import render
    spec = {"shape": "text", "text": "Mg", "x": 100.0, "y": 50.0,
            "anchor": "center", "size": 20, "stroke": "#000000"}
    item = render.spec_to_item(spec)
    box = item.sceneBoundingRect()
    assert box.center().x() == pytest.approx(100.0, abs=1.0)
    assert box.center().y() == pytest.approx(50.0, abs=1.0)


def test_only_centred_svg_text_is_centred():
    from khervemol import svgexport
    specs = [{"shape": "text", "text": "a", "x": 0, "y": 0, "size": 10,
              "anchor": "center", "stroke": "#000000"},
             {"shape": "text", "text": "b", "x": 0, "y": 0, "size": 10,
              "stroke": "#000000"}]
    root = svgexport.specs_to_svg(specs, 100, 100)
    anchors = [el.get("text-anchor") for el in root
               if el.tag.endswith("text")]
    assert anchors == ["middle", "start"]


def test_the_cell_count_is_capped(qapp):
    from khervemol.viewer3d import Viewer3D
    v = Viewer3D()
    v.set_molecule(library.make("simple_cubic"))
    v.set_cells(99, 0, 3)
    assert v.mol.cells == (supercell.MAX_CELLS, 1, 3)
