"""3D-model exports (STL, 3MF, OBJ, PLY, GLB) and chemistry files (XYZ, MOL,
SDF, PDB, CIF).

Copyright (C) 2026 Gwilherm Kerherve

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
"""

import json
import os
import struct
import xml.etree.ElementTree as ET
import zipfile

import pytest

from khervemol import chemexport, entries, meshexport
from khervemol.crystal import BuildError
from khervemol.model import Molecule


@pytest.fixture
def benzene():
    return entries.build("compound", "benzene")


def _signed_volume(mesh):
    v = 0.0
    for a, b, c in mesh.tris:
        A, B, C = mesh.verts[a], mesh.verts[b], mesh.verts[c]
        v += (A[0] * (B[1] * C[2] - B[2] * C[1])
              - A[1] * (B[0] * C[2] - B[2] * C[0])
              + A[2] * (B[0] * C[1] - B[1] * C[0])) / 6
    return v


# ------------------------------------------------------------------ mesh
def test_one_atom_is_a_closed_outward_sphere():
    m = Molecule([["C", 0, 0, 0]], [], name="atom")
    mesh = meshexport.build_mesh(m, quality="high", scale=10)
    # every edge is shared by exactly two triangles: watertight
    edges = {}
    for a, b, c in mesh.tris:
        for e in ((a, b), (b, c), (c, a)):
            edges[tuple(sorted(e))] = edges.get(tuple(sorted(e)), 0) + 1
    assert set(edges.values()) == {2}
    r = 10 * 0.58 * m.rscale                     # elements.radius("C") = 0.58
    import math
    assert _signed_volume(mesh) == pytest.approx(4 / 3 * math.pi * r ** 3,
                                                 rel=0.06)


def test_size_position_and_style(benzene):
    small = meshexport.build_mesh(benzene, scale=10)
    big = meshexport.build_mesh(benzene, scale=20)
    zs = [v[2] for v in small.verts]
    assert min(zs) == pytest.approx(0.0, abs=1e-6)        # stands on the bed
    xs = [v[0] for v in small.verts]
    assert abs(max(xs) + min(xs)) < 1.0                    # centred
    span = lambda mesh, d: (max(v[d] for v in mesh.verts)
                            - min(v[d] for v in mesh.verts))
    assert span(big, 0) == pytest.approx(2 * span(small, 0), rel=1e-6)
    assert 20 < span(small, 0) < 120                       # a ring, in mm
    one = Molecule([["C", 0, 0, 0]], [], name="atom")
    fill = meshexport.build_mesh(one, style="space_filling", scale=10)
    ball = meshexport.build_mesh(one, scale=10)
    assert span(fill, 0) > span(ball, 0)              # van der Waals > ball
    sticks = meshexport.build_mesh(benzene, style="sticks", scale=10)
    assert len(sticks.tris) > 0


def test_palette_keeps_element_colours_and_double_bonds(benzene):
    mesh = meshexport.build_mesh(benzene)
    assert "#f4f4f4" in mesh.palette                        # hydrogen
    assert len(mesh.palette) >= 2
    single = Molecule([["C", 0, 0, 0], ["C", 1.5, 0, 0]], [[0, 1, 1]])
    double = Molecule([["C", 0, 0, 0], ["C", 1.3, 0, 0]], [[0, 1, 2]])
    assert len(meshexport.build_mesh(double).tris) > \
        len(meshexport.build_mesh(single).tris)


def test_thinnest_bond_is_honoured():
    m = Molecule([["C", 0, 0, 0], ["C", 1.5, 0, 0]], [[0, 1, 1]])
    thin = meshexport.build_mesh(m, style="sticks", scale=1.0,
                                 min_stick_mm=0.1)
    thick = meshexport.build_mesh(m, style="sticks", scale=1.0,
                                  min_stick_mm=3.0)

    def rod_radius(mesh):
        # the middle of the bond, clear of the small end balls
        pts = [v for v in mesh.verts if 0.6 < v[0] + 1.2 < 1.8]
        return max(abs(v[1]) for v in pts) if pts else 0
    assert rod_radius(thick) > 3 * rod_radius(thin)


def test_cell_outline_option():
    m = entries.build("crystal", "cu")
    without = meshexport.build_mesh(m, cell=False)
    with_cell = meshexport.build_mesh(m, cell=True)
    assert len(with_cell.tris) > len(without.tris)
    assert "#3a3f46" in with_cell.palette


def test_mesh_errors():
    with pytest.raises(BuildError):
        meshexport.build_mesh(Molecule([], []))
    m = Molecule([["C", 0, 0, 0]], [])
    with pytest.raises(BuildError):
        meshexport.build_mesh(m, style="cubes")
    with pytest.raises(BuildError):
        meshexport.build_mesh(m, scale=0)
    with pytest.raises(BuildError):
        meshexport.export(m, "x.abc")
    big = entries.build("crystal", "cu?cells=10,10,10")
    with pytest.raises(BuildError) as err:
        meshexport.build_mesh(big, quality="high")
    assert "too many" in str(err.value).lower()


# --------------------------------------------------------------- writers
def test_binary_and_ascii_stl(benzene, tmp_path):
    p = str(tmp_path / "b.stl")
    r = meshexport.export(benzene, p)
    data = open(p, "rb").read()
    n = struct.unpack("<I", data[80:84])[0]
    assert n == r["triangles"] and len(data) == 84 + 50 * n
    t = str(tmp_path / "t.stl")
    meshexport.export(benzene, t, ascii=True)
    text = open(t).read()
    assert text.startswith("solid") and text.count("facet normal") == n
    assert text.strip().endswith("endsolid KherveMol")


def test_3mf_is_a_valid_package(benzene, tmp_path):
    p = str(tmp_path / "b.3mf")
    r = meshexport.export(benzene, p, scale=10)
    with zipfile.ZipFile(p) as z:
        assert set(z.namelist()) == {"[Content_Types].xml", "_rels/.rels",
                                     "3D/3dmodel.model"}
        root = ET.fromstring(z.read("3D/3dmodel.model"))
    ns = {"m": "http://schemas.microsoft.com/3dmanufacturing/core/2015/02"}
    assert root.get("unit") == "millimeter"
    verts = root.findall(".//m:vertex", ns)
    tris = root.findall(".//m:triangle", ns)
    mats = root.findall(".//m:base", ns)
    assert len(verts) == r["vertices"] and len(tris) == r["triangles"]
    assert len(mats) == r["colours"] >= 2
    assert all(0 <= int(t.get("p1")) < len(mats) for t in tris)
    assert all(int(t.get("v3")) < len(verts) for t in tris)


def test_obj_and_mtl(benzene, tmp_path):
    p = str(tmp_path / "b.obj")
    r = meshexport.export(benzene, p)
    lines = open(p).read().splitlines()
    assert sum(1 for x in lines if x.startswith("v ")) == r["vertices"]
    assert sum(1 for x in lines if x.startswith("f ")) == r["triangles"]
    mtl = open(str(tmp_path / "b.mtl")).read()
    assert mtl.count("newmtl") == r["colours"]
    assert "mtllib b.mtl" in lines[1]
    faces = [tuple(map(int, x.split()[1:])) for x in lines if x.startswith("f ")]
    assert max(max(f) for f in faces) == r["vertices"]


def test_ply_header_and_counts(benzene, tmp_path):
    p = str(tmp_path / "b.ply")
    r = meshexport.export(benzene, p)
    lines = open(p).read().splitlines()
    end = lines.index("end_header")
    assert f"element face {r['triangles']}" in lines
    nverts = int(next(x for x in lines if x.startswith("element vertex")
                      ).split()[-1])
    assert len(lines) - end - 1 == nverts + r["triangles"]
    assert len(lines[end + 1].split()) == 6            # x y z r g b


def test_glb_is_well_formed(benzene, tmp_path):
    p = str(tmp_path / "b.glb")
    r = meshexport.export(benzene, p)
    data = open(p, "rb").read()
    magic, version, length = struct.unpack("<4sII", data[:12])
    assert magic == b"glTF" and version == 2 and length == len(data)
    jlen, jtype = struct.unpack("<I4s", data[12:20])
    doc = json.loads(data[20:20 + jlen])
    assert jtype == b"JSON"
    blen, btype = struct.unpack("<I4s", data[20 + jlen:28 + jlen])
    assert btype == b"BIN\0" and blen == doc["buffers"][0]["byteLength"]
    assert doc["accessors"][0]["count"] == r["vertices"]
    n_idx = sum(a["count"] for a in doc["accessors"]
                if a["type"] == "SCALAR")
    assert n_idx == 3 * r["triangles"]
    assert len(doc["meshes"][0]["primitives"]) == r["colours"]
    for view in doc["bufferViews"]:
        assert view["byteOffset"] + view["byteLength"] <= blen


def test_extension_decides_and_is_added(benzene, tmp_path):
    r = meshexport.export(benzene, str(tmp_path / "noext"), fmt="stl")
    assert r["path"].endswith("noext.stl") and os.path.exists(r["path"])


# ------------------------------------------------------------ chemistry
def test_xyz_roundtrip(benzene, tmp_path):
    r = chemexport.export(benzene, str(tmp_path / "b.xyz"))
    lines = open(r["path"]).read().splitlines()
    assert int(lines[0]) == 12 and len(lines) == 14
    el, x, y, z = lines[2].split()
    a = benzene.atoms[0]
    assert el == a[0] and float(x) == pytest.approx(a[1], abs=1e-5)


def test_mol_and_sdf(benzene, tmp_path):
    text = chemexport.mol_text(benzene)
    lines = text.splitlines()
    assert lines[3].startswith(" 12 12") and lines[3].endswith("V2000")
    assert lines[-1] == "M  END"
    bonds = [l for l in lines[4 + 12:-1]]
    assert len(bonds) == 12
    assert sorted(int(b[6:9]) for b in bonds).count(2) == 3   # Kekulé doubles
    assert chemexport.sdf_text(benzene).endswith("$$$$\n")
    huge = entries.build("crystal", "cu?cells=6,6,6")
    with pytest.raises(BuildError):
        chemexport.mol_text(huge)


def test_pdb_has_hetatm_conect_and_cell(tmp_path):
    ethanol = entries.build("compound", "ethanol")
    text = chemexport.pdb_text(ethanol)
    assert text.count("HETATM") == 9 and "CONECT" in text and "CRYST1" not in text
    assert all(len(l) >= 78 for l in text.splitlines() if l.startswith("HETATM"))
    salt = chemexport.pdb_text(entries.build("crystal", "nacl"))
    assert salt.splitlines()[2].startswith("CRYST1")
    assert "5.640" in salt


def test_cif_of_crystals_slabs_and_errors():
    salt = chemexport.cif_text(entries.build("crystal", "nacl"))
    assert "_cell_length_a 5.64020" in salt and "_cell_angle_gamma 90" in salt
    # face atoms are wrapped and de-duplicated: 4 Na + 4 Cl in P1
    rows = [l for l in salt.splitlines() if l.startswith(" ") and "'" not in l]
    assert len(rows) == 8
    quartz = chemexport.cif_text(entries.build("crystal", "quartz"))
    assert "_cell_angle_gamma 120" in quartz
    two = chemexport.cif_text(entries.build("crystal", "nacl?cells=2,1,1"))
    assert "_cell_length_a 11.28040" in two
    slab = chemexport.cif_text(entries.build("surface", "cu:111"))
    assert "_cell_angle_gamma 120" in slab
    with pytest.raises(BuildError):
        chemexport.cif_text(entries.build("compound", "benzene"))
    with pytest.raises(BuildError):
        chemexport.export(entries.build("compound", "benzene"), "x.abc")


def test_chemistry_export_of_an_empty_structure_fails():
    for fn in (chemexport.xyz_text, chemexport.pdb_text,
               chemexport.mol_text):
        with pytest.raises(BuildError):
            fn(Molecule([], []))


# -------------------------------------------------------------------- UI
def test_dialog_and_menu_actions(qapp):
    from khervemol import exports_ui
    from khervemol.mainwindow import MainWindow
    w = MainWindow()
    titles = [a.text() for m in w.menuBar().findChildren(type(w.menuBar().addMenu("x")))
              for a in m.actions()]
    assert any("Export 3D model" in t for t in titles)
    assert any("Export chemistry file" in t for t in titles)
    d = exports_ui.MeshDialog(w.viewer.mol, "ball_and_stick")
    assert d.format() == "stl" and d.ascii.isEnabled()
    d.fmt.setCurrentIndex(d.fmt.findData("3mf"))
    assert not d.ascii.isEnabled()
    d.scale.setValue(20)
    assert " mm" in d.size.text()
    assert d.options()["scale"] == 20 and d.options()["style"] == "ball_and_stick"
    assert not d.cell.isEnabled()                      # ethanol has no cell
    w.load_entry("crystal", "cu")
    d2 = exports_ui.MeshDialog(w.viewer.mol)
    assert d2.cell.isEnabled() and d2.cell.isChecked()
    w.viewer.mol.cell_visible = False
    assert not exports_ui.MeshDialog(w.viewer.mol).cell.isChecked()


def test_mcp_export_model_tool(qapp, tmp_path):
    from khervemol import mcp_schema, mcp_tools
    from khervemol.mainwindow import MainWindow
    assert "export_model" in mcp_schema.TOOL_NAMES
    w = MainWindow()
    w.load_entry("model", "ethanol", "Ethanol")   # off the start screen
    ex = mcp_tools.McpToolExecutor(w)
    r = ex.execute("export_model", {"path": str(tmp_path / "e.stl"),
                                    "scale_mm_per_angstrom": 5})
    assert r["ok"] and r["format"] == "stl" and r["triangles"] > 100
    r = ex.execute("export_model", {"path": str(tmp_path / "e.xyz")})
    assert r["format"] == "xyz" and r["atoms"] == 9
    assert "not an export format" in ex.execute(
        "export_model", {"path": str(tmp_path / "e.docx")})["error"]
    assert "cell outline" in ex.execute(
        "export_model", {"path": str(tmp_path / "e.cif")})["error"]
