"""The MCP server: schemas, the tool layer, the bridge and the stdio server.

The tool layer is driven directly against a real (offscreen) `MainWindow`
-- no sockets.  A second group starts a real `McpBridge` on a free
loopback port and talks to it from a worker thread while the main thread
pumps the Qt event loop; those skip cleanly where sockets are unavailable.

Copyright (C) 2026 Gwilherm Kerherve

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
"""

import base64
import json
import math
import os
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request

import pytest

from khervemol import (mcp_bridge, mcp_hosts, mcp_schema, mcp_server,
                       mcp_tools)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PNG = b"\x89PNG\r\n\x1a\n"


# ---------------------------------------------------------------- fixtures
@pytest.fixture
def win(qapp):
    from khervemol.mainwindow import MainWindow
    w = MainWindow()
    yield w
    w.viewer.stop_animation()
    w.close()


@pytest.fixture
def ex(win):
    return mcp_tools.McpToolExecutor(win)


@pytest.fixture
def run(ex):
    """Call a tool and return its result dict."""
    def call(_tool, **args):
        return ex.execute(_tool, args)
    return call


def ok(result):
    assert "error" not in result, result.get("error")
    return result


def hydrogens_on(win, atom):
    mol = win.viewer.mol
    out = []
    for i, j, _o in mol.bonds:
        if atom in (i, j):
            other = j if i == atom else i
            if mol.atoms[other][0] == "H":
                out.append(other)
    return out


def elements_of(win, symbol):
    return [i for i, a in enumerate(win.viewer.mol.atoms) if a[0] == symbol]


def bond_of(win, i, j):
    from khervemol import model
    return model.bond_between(win.viewer.mol.bonds, i, j)


def png_bytes(result):
    raw = base64.b64decode(result[mcp_server.IMAGE_KEY], validate=True)
    assert raw[:8] == PNG
    return raw


# ----------------------------------------------------------------- schemas
def test_every_tool_has_a_valid_schema():
    seen = set()
    assert len(mcp_schema.TOOLS) >= 30
    for tool in mcp_schema.TOOLS:
        name = tool["name"]
        assert name not in seen and name.replace("_", "").isalnum()
        seen.add(name)
        assert len(tool["description"]) > 40, name
        schema = tool["input_schema"]
        assert schema["type"] == "object", name
        props = schema["properties"]
        assert isinstance(props, dict)
        assert set(schema["required"]) <= set(props), name
        assert schema["additionalProperties"] is False
        json.dumps(schema)                       # serialisable
        _check_props(name, props)


def _check_props(name, props):
    for key, spec in props.items():
        assert spec["type"] in ("string", "integer", "number", "boolean",
                                "array", "object"), (name, key)
        assert spec.get("description"), (name, key)
        if "enum" in spec:
            assert spec["enum"] and all(isinstance(e, str)
                                        for e in spec["enum"])
        if spec["type"] == "array":
            assert "items" in spec, (name, key)
        if spec["type"] == "object":
            assert set(spec.get("required", ())) <= set(spec["properties"])
            _check_props(name, spec["properties"])
        if "minimum" in spec and "maximum" in spec:
            assert spec["minimum"] <= spec["maximum"], (name, key)


def test_every_tool_is_implemented_and_documented(ex):
    names = set(mcp_schema.TOOL_NAMES)
    handlers = {n[3:] for n in dir(ex) if n.startswith("_t_")}
    assert handlers == names
    for name in names:                # the server tells the model about all
        assert name in mcp_server._INSTRUCTIONS, name
    assert mcp_bridge.READ_ONLY_TOOLS <= names
    assert mcp_bridge.FILE_TOOLS <= names
    assert set(mcp_schema.NANO_PARAMS) == set(mcp_schema.NANO_STRUCTURES)


def test_argument_validation():
    schema = mcp_schema.tool_schema("build_surface")["input_schema"]
    good = mcp_schema.check_args(schema, {
        "crystal": "cu", "miller": "111", "layers": "4",
        "adsorbate": {"smiles": "CO", "height": 2}})
    assert good["layers"] == 4 and good["adsorbate"]["height"] == 2.0
    bad = [
        ({"crystal": "cu"}, "Missing required"),
        ({"crystal": "cu", "miller": "111", "nope": 1}, "Unknown"),
        ({"crystal": "cu", "miller": "111", "layers": 0}, "at least 1"),
        ({"crystal": "cu", "miller": "111", "layers": 1.5}, "whole number"),
        ({"crystal": "cu", "miller": 111}, "string"),
        ({"crystal": "cu", "miller": "111", "repeat": [1]}, "exactly 2"),
        ({"crystal": "cu", "miller": "111",
          "adsorbate": {"mode": "sideways"}}, "one of"),
        ({"crystal": "cu", "miller": "111",
          "adsorbate": {"height": 99}}, "at most 15"),
        ({"crystal": "cu", "miller": "111", "adsorbate": {"colour": 1}},
         "Unknown"),
    ]
    for args, fragment in bad:
        with pytest.raises(mcp_schema.ArgError) as err:
            mcp_schema.check_args(schema, args)
        assert fragment in str(err.value)
    with pytest.raises(mcp_schema.ArgError):
        mcp_schema.check_args(schema, ["not", "a", "dict"])
    flag = mcp_schema.tool_schema("set_view")["input_schema"]
    assert mcp_schema.check_args(flag, {"labels": "true"}) == {"labels": True}
    with pytest.raises(mcp_schema.ArgError):
        mcp_schema.check_args(flag, {"labels": 1})


def test_the_stdio_side_imports_no_qt():
    code = ("import sys, khervemol.mcp_server, khervemol.mcp_schema\n"
            "bad = sorted(m for m in sys.modules "
            "if m.split('.')[0] in ('PyQt5', 'PyQt6', 'PySide2', 'PySide6'))\n"
            "assert not bad, bad\n")
    subprocess.run([sys.executable, "-c", code], cwd=ROOT, check=True,
                   timeout=60)


# --------------------------------------------------------- read-only tools
def test_get_document_info(run):
    info = ok(run("get_document_info"))
    assert info["formula"] == "C2H6O" and info["kind"] == "molecule"
    assert info["atoms"] == 9 and info["editable"] is True
    assert info["tab"] == "3d" and info["path"] is None
    assert info["view"]["renderer"] in ("gl", "classic")
    assert info["selection"] == []
    ok(run("build_reaction", equation="2 H2 + O2 -> 2 H2O"))
    info = ok(run("get_document_info"))
    assert info["kind"] == "reaction" and info["animation"]["available"]


def test_read_only_tools_do_not_touch_the_window(win, run):
    v = win.viewer
    ok(run("select_atoms", atoms=[2]))

    def state():
        m = v.mol
        return (json.dumps([m.atoms, m.bonds]), m.az, m.el, m.bond, v.style,
                v.labels_btn.isChecked(), list(v.selection), m.label,
                win._path, win.tabs.currentIndex(), v.renderer)

    before = state()
    calls = [
        ("get_document_info", {}),
        ("search_library", {"text": "caffeine"}),
        ("list_molecules", {"category": "alcohol", "limit": 5}),
        ("list_molecules", {"compound": "water"}),
        ("list_crystals", {"search": "cu"}),
        ("list_crystals", {"key": "nacl"}),
        ("list_polymers", {"search": "vinyl"}),
        ("list_reactions", {}),
        ("list_reactions", {"equation": "CH4 + O2 -> CO2 + H2O"}),
        ("get_structure", {"geometry": True}),
        ("properties", {}),
        ("render_view", {"width": 200, "height": 160, "az": 75, "el": -30,
                         "labels": True, "style": "space_filling",
                         "bond_spread": 2.5}),
        ("render_view", {"width": 200, "height": 160,
                         "orientation": "top"}),
        ("render_view", {"width": 200, "height": 160, "view": "2d"}),
    ]
    for name, args in calls:
        assert name in mcp_bridge.READ_ONLY_TOOLS
        ok(run(name, **args))
        assert state() == before, name


def test_search_library(run):
    hits = ok(run("search_library", text="caffeine"))["results"]
    assert hits[0]["kind"] == "compound" and hits[0]["value"] == "caffeine"
    assert hits[0]["build_with"] == "build_molecule"
    by_formula = ok(run("search_library", text="C6H12O6"))["results"]
    assert {h["value"] for h in by_formula} >= {"glucose", "fructose"}
    si = ok(run("search_library", text="silicon 111", kind="surface"))
    assert si["results"][0]["value"] == "si:111"
    assert si["results"][0]["build_with"] == "build_surface"
    assert ok(run("search_library", text="zzzznotathing"))["results"] == []
    assert "error" in run("search_library", text="  ")


def test_list_molecules_crystals_polymers_reactions(run):
    page = ok(run("list_molecules"))
    assert page["total"] > 300 and page["categories"] and page["molecules"]
    alc = ok(run("list_molecules", category="alcohol", limit=3, offset=1))
    assert alc["returned"] == 3 and "categories" not in alc
    full = ok(run("list_molecules", compound="ethanol"))
    assert full["formula"] == "C2H6O" and full["smiles"] == "CCO"
    assert len(full["atoms"]) == 9 and len(full["bonds"]) == 8
    assert math.isclose(full["molecular_weight"], 46.07, abs_tol=0.05)
    err = run("list_molecules", compound="etanol")
    assert "ethanol" in err["error"] and len(err["error"]) < 400

    rows = ok(run("list_crystals", category="Metals"))["crystals"]
    assert rows and all(r["cell"]["a"] > 0 and r["atoms_per_cell"] > 0
                        for r in rows)
    nacl = ok(run("list_crystals", key="NaCl rock salt"))
    assert nacl["space_group"].startswith("Fm-3m")
    assert nacl["atoms_per_cell"] == 8 == len(nacl["atoms"])
    assert nacl["surfaces"] == ["100"]
    assert math.isclose(nacl["density_g_cm3"], 2.16, abs_tol=0.05)
    err = run("list_crystals", key="copperr")
    assert "No library crystal" in err["error"] and len(err["error"]) < 400

    pol = ok(run("list_polymers", search="vinyl chloride"))
    assert pol["polymers"][0]["key"] == "pvc"
    assert ok(run("list_polymers"))["total"] > 20

    rx = ok(run("list_reactions"))
    assert rx["total"] > 20
    check = ok(run("list_reactions", equation="N2 + H2 <=> NH3"))
    assert check["balanced"] and check["coefficients"] == [1, 3, 2]
    assert check["reversible"]


def test_get_structure(run):
    s = ok(run("get_structure", geometry=True))
    assert len(s["atoms"]) == 9 and s["unit"] == "angstrom"
    assert s["atoms"][0][0] == "C" and len(s["atoms"][0]) == 4
    cc = [b for b in s["bonds"] if {b[0], b[1]} == {0, 1}][0]
    assert math.isclose(cc[3], 1.52, abs_tol=0.06)
    assert all(abs(a[3] - 109.5) < 6 for a in s["angles"])
    ok(run("build_crystal", crystal="cu", cells=[2, 2, 2]))
    small = ok(run("get_structure", max_atoms=10))
    assert small["truncated"] and len(small["atoms"]) == 10
    assert small["cell_edges"]


def test_properties_tool(run):
    p = ok(run("properties"))
    assert p["properties"]["Formula"] == "C2H6O"
    assert p["properties"]["Molecular weight"].startswith("46.0")
    assert {"label", "value"} == set(p["rows"][0])
    ok(run("build_crystal", crystal="nacl"))
    assert "Mass drawn" in ok(run("properties"))["properties"]


def test_render_view_returns_a_png(win, run):
    r = ok(run("render_view", width=320, height=240))
    raw = png_bytes(r)
    from PyQt5.QtGui import QImage
    img = QImage.fromData(raw, "PNG")
    assert (img.width(), img.height()) == (320, 240)
    assert r["formula"] == "C2H6O" and r["camera"]["az"] == 28.0
    default = ok(run("render_view"))
    assert (default["width"], default["height"]) == (1000, 800)
    # a different camera changes the picture but not the user's view
    az, el = win.viewer.mol.az, win.viewer.mol.el
    other = ok(run("render_view", width=320, height=240, az=140, el=55,
                   labels=True))
    assert other["camera"]["az"] == 140.0 and other["camera"]["labels"]
    assert png_bytes(other) != raw
    assert (win.viewer.mol.az, win.viewer.mol.el) == (az, el)
    assert not win.viewer.labels_btn.isChecked()
    two_d = ok(run("render_view", width=200, height=150, view="2d"))
    assert two_d["view"] == "2d"
    png_bytes(two_d)
    assert "error" in run("render_view", width=10)


# ------------------------------------------------------------------ builds
def test_build_molecule_by_name_formula_and_smiles(win, run):
    r = ok(run("build_molecule", name="caffeine"))
    assert r["formula"] == "C8H10N4O2" and r["atoms"] == 24
    assert win.viewer.mol.formula() == "C8H10N4O2"
    assert win.sketch.atoms                        # mirrored into the 2D tab
    r = ok(run("build_molecule", name="C2H6O"))    # by formula
    assert r["formula"] == "C2H6O"
    r = ok(run("build_molecule", smiles="CC(=O)O", label="Vinegar"))
    assert r["formula"] == "C2H4O2" and r["label"] == "Vinegar"
    assert ok(run("build_molecule", name="c60"))["formula"] == "C60"
    assert ok(run("build_molecule", name="water"))["atoms"] == 3
    # add merges a fragment next to the current molecule
    r = ok(run("build_molecule", name="methane", mode="add"))
    assert r["atoms"] == 3 + 5 and r["first_new_atom"] == 3
    assert r["formula"] == "CH6O" or "C" in r["formula"]


def test_build_molecule_errors(run):
    assert "exactly one" in run("build_molecule")["error"]
    assert "exactly one" in run("build_molecule", name="a",
                                smiles="C")["error"]
    err = run("build_molecule", name="etanol")["error"]
    assert "ethanol" in err and "search_library" in err
    err = run("build_molecule", smiles="C(C")["error"]
    assert "SMILES" in err
    assert "Unknown parameter" in run("build_molecule", nom="x")["error"]
    ok(run("build_crystal", crystal="nacl"))
    assert "mode 'add'" in run("build_molecule", name="water",
                               mode="add")["error"]


def test_build_crystal(win, run):
    r = ok(run("build_crystal", crystal="cu", cells=[2, 2, 1]))
    assert r["kind"] == "crystal" and r["editable"] is False
    assert r["cells"] == [2, 2, 1] and r["crystal"]["key"] == "cu"
    assert "2×2×1" in win.viewer.mol.label
    inside = ok(run("build_crystal", crystal="Copper", cells=[2, 2, 1],
                    boundary=False))
    assert inside["atoms"] < r["atoms"]
    for bad in ({"crystal": "nosuch"},
                {"crystal": "cu", "cells": [0, 1, 1]},
                {"crystal": "cu", "cells": [1, 1]}):
        assert "error" in run("build_crystal", **bad)


def test_build_surface_and_adsorbate(win, run):
    slab = ok(run("build_surface", crystal="cu", miller="111",
                  repeat=[3, 3], layers=3))
    assert slab["kind"] == "surface" and slab["atoms"] == 27
    assert "(111)" in win.viewer.mol.label
    co = ok(run("build_surface", crystal="cu", miller="111", repeat=[3, 3],
                layers=3, adsorbate={"smiles": "[C-]#[O+]", "height": 1.9,
                                     "mode": "upright"}))
    assert co["kind"] == "surface+adsorbate"
    assert co["atoms"] == 27 + 2 and co["slab_atoms"] == 27
    assert co["adsorbate"]["atoms"] == 2
    mol = win.viewer.mol
    top = max(a[3] for a in mol.atoms[:27])
    low = min(a[3] for a in mol.atoms[27:])
    assert math.isclose(low - top, 1.9, abs_tol=0.05)
    high = max(a[3] for a in mol.atoms[27:])
    assert high - low > 1.0                       # standing up
    water = ok(run("build_surface", crystal="cu", miller="111",
                   repeat=[3, 3], adsorbate={"compound": "water", "dx": 2.0}))
    assert water["atoms"] == 27 + 3
    # 'current' adsorbs the molecule on screen
    ok(run("build_molecule", name="ethanol"))
    cur = ok(run("build_surface", crystal="pt", miller="111", repeat=[3, 3],
                 layers=2, adsorbate={"current": True, "spin": 30}))
    assert cur["adsorbate"]["formula"] == "C2H6O"
    assert cur["atoms"] == 18 + 9
    # hexagonal Miller with four indices
    assert ok(run("build_surface", crystal="gan", miller="10-10",
                  repeat=[2, 2]))["kind"] == "surface"


def test_build_surface_errors(run):
    assert "exactly one" in run("build_surface", crystal="cu",
                                miller="111", adsorbate={})["error"]
    assert "exactly one" in run(
        "build_surface", crystal="cu", miller="111",
        adsorbate={"smiles": "C", "compound": "water"})["error"]
    ok(run("build_crystal", crystal="nacl"))
    assert "needs a molecule" in run(
        "build_surface", crystal="cu", miller="111",
        adsorbate={"current": True})["error"]
    assert "Miller" in run("build_surface", crystal="cu",
                           miller="abc")["error"]
    assert "No library crystal" in run("build_surface", crystal="zz",
                                       miller="111")["error"]
    assert "at most" in run("build_surface", crystal="cu", miller="111",
                            adsorbate={"smiles": "C", "height": 40})["error"]
    assert "SMILES" in run("build_surface", crystal="cu", miller="111",
                           adsorbate={"smiles": "C(C"})["error"]


def test_build_nano(win, run):
    g = ok(run("build_nano", structure="graphene", width=1.5, depth=1.5,
               layers=2, stacking="AB"))
    assert g["kind"] == "nanostructure" and set(g["formula"]) >= set("C")
    assert not g["editable"]
    tube = ok(run("build_nano", structure="nanotube", n=5, m=5, length=1))
    assert tube["formula"] == "C88"
    assert ok(run("build_nano", structure="fullerene", kind="C60"))[
        "formula"] == "C60"
    assert ok(run("build_nano", structure="fullerene"))["formula"] == "C60"
    assert "N" in ok(run("build_nano", structure="defect", kind="nitrogen",
                         width=1.5, depth=1.5))["formula"]
    assert ok(run("build_nano", structure="ribbon", edge="zigzag",
                  width=1.0, length=2.0))["atoms"] > 20
    assert ok(run("build_nano", structure="dot", diameter=1.0))["atoms"] > 10
    assert ok(run("build_nano", structure="graphite", layers=2, width=1.2,
                  depth=1.2))["atoms"] > 20
    err = run("build_nano", structure="graphene", n=5)["error"]
    assert "does not take n" in err and "width" in err
    assert "structure" in run("build_nano")["error"]
    assert "error" in run("build_nano", structure="nanotube", n=5, m=9)


def test_build_polymer(win, run):
    p = ok(run("build_polymer", preset="pvc", n=3))
    assert p["kind"] == "polymer" and p["formula"] == "C6H11Cl3"
    assert p["editable"] is True
    q = ok(run("build_polymer", unit="CC(C#N)", n=3))
    assert q["formula"] == "C9H11N3"
    assert ok(run("build_polymer", unit="CC", n=2, head="C",
                  tail="C"))["formula"] == "C6H14"
    assert "exactly one" in run("build_polymer")["error"]
    assert "exactly one" in run("build_polymer", preset="pvc",
                                unit="CC")["error"]
    assert "Did you mean" in run("build_polymer", preset="pvcc")["error"]
    assert "caps" in run("build_polymer", preset="pvc", head="C")["error"]
    assert "error" in run("build_polymer", unit="C(C", n=3)
    assert "at most 200" in run("build_polymer", preset="pvc", n=500)["error"]


def test_build_reaction_and_film(win, run):
    r = ok(run("build_reaction", equation="CH4 + O2 -> CO2 + H2O",
               play=True))
    rep = r["reaction"]
    assert rep["balanced"] and rep["coefficients"] == [1, 2, 1, 2]
    assert rep["equation"].startswith("CH4 + 2 O2")
    assert r["animation"] and r["playing"] and win.viewer.playing
    assert r["kind"] == "reaction"
    info = ok(run("get_document_info"))
    assert info["animation"]["playing"]
    paused = ok(run("play_reaction", action="pause"))
    assert not paused["playing"]
    seen = {}
    for p in (0.0, 0.3, 0.6, 0.85, 1.0):
        st = ok(run("set_reaction_progress", progress=p))
        assert math.isclose(st["progress"], p, abs_tol=1e-6)
        seen[p] = st["stage"]
    assert seen[0.0] == "Reactants approach" and seen[1.0] != seen[0.3]
    assert len(set(seen.values())) >= 3
    assert not ok(run("play_reaction", action="stop"))["active"]
    assert ok(run("play_reaction"))["playing"]
    # unbalanced input is reported, not hidden
    bad = ok(run("build_reaction", equation="2 H2 + 3 O2 -> H2O",
                 balance=False))["reaction"]
    assert bad["balanced"] is False and "O" in bad["warning"]
    quiet = ok(run("build_reaction", equation="N2 + 3 H2 <=> 2 NH3"))
    assert not quiet["playing"] and quiet["reaction"]["reversible"]
    err = run("build_reaction", equation="Xx + O2 -> H2O")["error"]
    assert err
    assert "error" in run("build_reaction", equation="H2 + O2")


def test_film_tools_need_a_reaction(run):
    assert "not a reaction" in run("play_reaction")["error"]
    assert "not a reaction" in run("set_reaction_progress",
                                   progress=0.5)["error"]
    assert "at most 1" in run("set_reaction_progress", progress=2)["error"]


# ----------------------------------------------------------------- editing
def test_add_atom_delete_atom_and_fill_hydrogens(win, run):
    ok(run("build_molecule", name="ethanol"))
    o = elements_of(win, "O")[0]
    full = ok(run("add_atom", element="Cl", anchor=o))       # O is saturated
    assert full["bonded"] is False and "no free valence" in full["note"]
    ok(run("delete_atom", atoms=[full["index"]]))
    # swap the hydroxyl hydrogen for a chlorine
    ok(run("delete_atom", atoms=hydrogens_on(win, o)))
    o = elements_of(win, "O")[0]
    added = ok(run("add_atom", element="cl", anchor=o))
    assert added["bonded"] and added["element"] == "Cl"
    assert added["index"] == len(win.viewer.mol.atoms) - 1
    assert 1.4 < added["bond_length"] < 1.9
    assert win.viewer.mol.formula() == "C2H5ClO"
    assert ok(run("add_atom", element="O", anchor=0, order=2))[
        "bonded"] is False                                   # C0 is saturated
    ok(run("delete_atom", atoms=[len(win.viewer.mol.atoms) - 1]))
    # strip two hydrogens and cap them back
    hs = elements_of(win, "H")
    ok(run("delete_atom", atoms=hs[:2]))
    n = len(win.viewer.mol.atoms)
    capped = ok(run("fill_hydrogens"))
    assert capped["hydrogens_added"] == 2 and capped["atoms"] == n + 2
    assert win.viewer.mol.formula() == "C2H5ClO"
    assert ok(run("fill_hydrogens"))["hydrogens_added"] == 0
    # only the atoms named
    ok(run("delete_atom", atoms=[elements_of(win, "H")[0]]))
    assert ok(run("fill_hydrogens", atoms=[elements_of(win, "O")[0]]))[
        "hydrogens_added"] == 0
    assert ok(run("fill_hydrogens", atoms=[0, 1]))["hydrogens_added"] == 1
    assert "at least one atom" in run(
        "delete_atom", atoms=list(range(len(win.viewer.mol.atoms))))[
        "error"].lower()
    assert "does not exist" in run("delete_atom", atoms=[99])["error"]
    assert "not an element" in run("add_atom", element="Zz")["error"]
    assert "does not exist" in run("add_atom", element="C", anchor=99)["error"]


def test_build_a_molecule_atom_by_atom(win, run):
    ok(run("new_document"))
    r = ok(run("add_atom", element="O", anchor=0, order=2))    # C=O
    assert r["bonded"] and math.isclose(r["bond_length"], 1.23, abs_tol=0.06)
    ok(run("fill_hydrogens"))
    assert win.viewer.mol.formula() == "CH2O"                   # formaldehyde
    assert ok(run("get_document_info"))["formula"] == "CH2O"


def test_bond_atoms_and_bond_order(win, run):
    ok(run("build_molecule", name="ethane"))
    c0, c1 = elements_of(win, "C")
    hs = elements_of(win, "H")
    assert "already bonded" in run("bond_atoms", i=c0, j=c1)["error"]
    assert "No free valence" in run("bond_atoms", i=hs[0], j=hs[-1])["error"]
    assert "different atoms" in run("bond_atoms", i=0, j=0)["error"]
    assert "does not exist" in run("bond_atoms", i=0, j=99)["error"]
    assert "no free valence" in run("set_bond_order", i=c0, j=c1,
                                    order=2)["error"]
    # make a C=C: a hydrogen has to come off each carbon first
    ok(run("delete_atom", atoms=[hydrogens_on(win, c0)[0],
                                 hydrogens_on(win, c1)[0]]))
    c0, c1 = elements_of(win, "C")
    r = ok(run("set_bond_order", i=c0, j=c1, order=2))
    assert r["bond"][2] == 2 and math.isclose(r["length"], 1.34, abs_tol=0.06)
    assert win.viewer.mol.formula() == "C2H4"
    r = ok(run("set_bond_order", i=c0, j=c1, order=1))
    assert math.isclose(r["length"], 1.53, abs_tol=0.06)
    # delete the bond, then join the two carbons again
    ok(run("delete_bond", i=c0, j=c1))
    assert bond_of(win, c0, c1) is None
    assert "not bonded" in run("delete_bond", i=c0, j=c1)["error"]
    assert "not bonded" in run("set_bond_order", i=c0, j=c1,
                               order=2)["error"]
    r = ok(run("bond_atoms", i=c0, j=c1, order=2))
    assert bond_of(win, c0, c1) is not None and r["bond"] == [c0, c1, 2]
    assert math.isclose(r["length"], 1.34, abs_tol=0.06)


def test_move_atom_keeps_bond_lengths(win, run):
    ok(run("build_molecule", name="ethanol"))
    o = [i for i, a in enumerate(win.viewer.mol.atoms) if a[0] == "O"][0]
    before = {b[1] if b[0] == o else b[0]: None
              for b in win.viewer.mol.bonds if o in b[:2]}
    r = ok(run("move_atom", atom=o, delta=[0.0, 0.0, 1.5]))
    for _j, length in r["bond_lengths"]:
        assert math.isclose(length, 1.42, abs_tol=0.08) or length < 1.1
    assert before
    free = ok(run("move_atom", atom=o, position=[5.0, 5.0, 5.0],
                  keep_bond_lengths=False))
    assert free["position"] == [5.0, 5.0, 5.0]
    assert any(length > 4 for _j, length in free["bond_lengths"])
    assert "exactly one" in run("move_atom", atom=0)["error"]
    assert "exactly one" in run("move_atom", atom=0, delta=[0, 0, 0],
                                position=[0, 0, 0])["error"]


def test_editing_a_fixed_structure_is_refused(run):
    ok(run("build_crystal", crystal="nacl"))
    for name, args in (("add_atom", {"element": "C"}),
                       ("delete_atom", {"atoms": [0]}),
                       ("bond_atoms", {"i": 0, "j": 1}),
                       ("set_bond_order", {"i": 0, "j": 1, "order": 2}),
                       ("delete_bond", {"i": 0, "j": 1}),
                       ("move_atom", {"atom": 0, "delta": [1, 0, 0]}),
                       ("fill_hydrogens", {})):
        err = run(name, **args)["error"]
        assert "fixed" in err and "crystal" in err, name


@pytest.fixture
def shelf_env(tmp_path, monkeypatch):
    from khervemol import shelf
    monkeypatch.setenv("KHERVEMOL_STATE_DIR", str(tmp_path / "shelfdir"))
    shelf.reset_default()
    yield
    shelf.reset_default()


def test_keep_molecule_and_the_shelf(shelf_env, win, run):
    ok(run("build_molecule", name="ethanol"))
    kept = ok(run("keep_molecule", name="My ethanol"))
    assert kept["name"] == "My ethanol" and kept["token"] == "@My_ethanol"
    assert kept["formula"] == "C2H6O" and kept["shelf"] == ["My ethanol"]
    assert win.shelf.names() == ["My ethanol"]      # the window's own shelf
    auto = ok(run("keep_molecule"))
    assert auto["name"] == "Molecule 1"
    listing = ok(run("list_molecules"))
    assert [m["name"] for m in listing["my_molecules"]] == [
        "My ethanol", "Molecule 1"]
    assert ok(run("list_molecules", search="ethanol"))["my_molecules"]
    hits = ok(run("search_library", text="ethanol", kind="mine"))["results"]
    assert not hits or hits[0]["build_with"] == "build_molecule"
    ok(run("build_molecule", name="water"))
    back = ok(run("build_molecule", name="@My_ethanol"))
    assert back["formula"] == "C2H6O"
    assert ok(run("build_molecule", name="my ethanol"))["formula"] == "C2H6O"
    assert "shelf" in run("build_molecule", name="@Nope")["error"]
    rx = ok(run("build_reaction",
                equation="@My_ethanol + O2 -> CO2 + H2O"))["reaction"]
    assert rx["balanced"] and rx["coefficients"] == [1, 3, 2, 3]
    ok(run("build_crystal", crystal="nacl"))
    assert "crystal" in run("keep_molecule")["error"]


def test_select_atoms(win, run):
    assert ok(run("select_atoms", atoms=[1, 3]))["selection"] == [1, 3]
    assert win.viewer.selection == [1, 3]
    a = ok(run("add_atom", element="H"))          # bonds onto the primary
    assert a["anchor"] == 3 or not a["bonded"]
    assert ok(run("select_atoms", atoms=[]))["selection"] == []
    assert "does not exist" in run("select_atoms", atoms=[500])["error"]


# --------------------------------------------------------------------- view
def test_set_view(win, run):
    v = win.viewer
    r = ok(run("set_view", orientation="top"))
    assert r["view"]["el"] == 90.0 and r["view"]["az"] == 0.0
    r = ok(run("set_view", az=45, el=-20, labels=True, bond_spread=2.0))
    assert (r["view"]["az"], r["view"]["el"]) == (45.0, -20.0)
    assert r["view"]["labels"] and v.labels_btn.isChecked()
    assert math.isclose(v.mol.bond, 2.0)
    r = ok(run("set_view", style="space_filling"))
    assert v.style == "space_filling" and r["view"]["style"] == "space_filling"
    assert ok(run("set_view", renderer="classic"))["view"][
        "renderer"] == "classic"
    assert ok(run("set_view", tab="2d"))["tab"] == "2d"
    assert win.tabs.currentIndex() == 1
    ok(run("set_view", tab="3d"))
    assert "Pass at least one" in run("set_view")["error"]
    assert "one of" in run("set_view", orientation="sideways")["error"]
    assert "at most 90" in run("set_view", el=120)["error"]
    ok(run("build_molecule", name="water"))
    assert "no coordination" in run("set_view", polyhedra=True)["error"]
    assert "crystals and surfaces only" in run(
        "set_view", cell_outline=False)["error"]
    ok(run("build_crystal", crystal="rutile"))
    ok(run("set_view", polyhedra=True))
    assert v.mol.poly is True
    ok(run("set_view", cell_outline=False))
    assert v.mol.cell_visible is False


# -------------------------------------------------------------------- files
def test_new_open_save_and_export(win, run, tmp_path):
    ok(run("build_molecule", name="ethanol"))
    assert "no file yet" in run("save_document")["error"]
    path = tmp_path / "eth.kmol"
    saved = ok(run("save_document", path=str(path)))
    assert saved["path"] == str(path) and path.stat().st_size > 100
    assert win._path == str(path)
    ok(run("save_document"))                       # over the open file
    other = tmp_path / "other.kmol"
    other.write_text("keep")
    assert "already exists" in run("save_document", path=str(other))["error"]
    assert other.read_text() == "keep"
    ok(run("save_document", path=str(other), overwrite=True))
    assert "must end in .kmol" in run(
        "save_document", path=str(tmp_path / "a.txt"))["error"]
    assert "does not exist" in run(
        "save_document", path=str(tmp_path / "no" / "a.kmol"))["error"]

    n = ok(run("new_document"))
    assert n["atoms"] == 1 and win._path is None
    opened = ok(run("open_document", path=str(path)))
    assert opened["formula"] == "C2H6O" and win._path == str(path)
    assert "No such file" in run("open_document",
                                 path=str(tmp_path / "nope.kmol"))["error"]
    bad = tmp_path / "bad.kmol"
    bad.write_text("{not json")
    assert "Cannot open" in run("open_document", path=str(bad))["error"]

    png = tmp_path / "eth.png"
    r = ok(run("export_image", path=str(png), width=400, height=300))
    assert (r["width"], r["height"]) == (400, 300)
    assert png.read_bytes()[:8] == PNG
    assert "already exists" in run("export_image", path=str(png))["error"]
    ok(run("export_image", path=str(png), width=200, height=100,
           overwrite=True))
    two = tmp_path / "sketch.png"
    ok(run("export_image", path=str(two), view="2d", width=300, height=200))
    assert two.read_bytes()[:8] == PNG
    svg = tmp_path / "eth.svg"
    r = ok(run("export_svg", path=str(svg)))
    text = svg.read_text()
    assert text.lstrip().startswith(("<?xml", "<svg")) and "<ellipse" in text
    assert "KhervePaint" in r["note"]
    ok(run("export_svg", path=str(tmp_path / "s2.svg"), view="2d"))
    assert "must end in .png" in run("export_image",
                                     path=str(tmp_path / "x.jpg"))["error"]


def test_an_unknown_tool_and_bad_arguments(run):
    assert "Unknown tool" in run("format_disk")["error"]
    assert "Unknown parameter" in run("get_document_info", x=1)["error"]
    assert "must be an integer" in run("get_structure",
                                       max_atoms="lots")["error"]


# ----------------------------------------------------------- hosts (no Qt)
def test_hosts_write_and_remove_the_entry(tmp_path):
    cfg = tmp_path / "cfg.json"
    cfg.write_text(json.dumps({"mcpServers": {"other": {"command": "x"}},
                               "theme": "dark"}))
    host = mcp_hosts.Host.for_file(str(cfg))
    assert not host.connected()
    rep = host.connect()
    assert rep["ok"] and rep["action"] == "added" and rep["backup"]
    doc = json.loads(cfg.read_text())
    assert doc["theme"] == "dark" and "other" in doc["mcpServers"]
    entry = doc["mcpServers"]["khervemol"]
    assert entry["command"] == sys.executable
    assert entry["args"] == ["-m", "khervemol.mcp_server"]
    assert os.path.isdir(os.path.join(entry["env"]["PYTHONPATH"], "khervemol"))
    assert host.connected() and host.up_to_date()
    assert host.connect()["action"] == "updated"
    assert os.path.exists(rep["backup"])
    assert host.disconnect()["action"] == "removed"
    doc = json.loads(cfg.read_text())
    assert "khervemol" not in doc["mcpServers"] and "other" in doc[
        "mcpServers"]
    assert host.disconnect()["action"] == "already absent"


def test_hosts_refuse_to_clobber_an_unreadable_file(tmp_path):
    cfg = tmp_path / "cfg.json"
    cfg.write_text("{ not json")
    rep = mcp_hosts.Host.for_file(str(cfg)).connect()
    assert not rep["ok"] and "not valid JSON" in rep["error"]
    assert cfg.read_text() == "{ not json"
    fresh = mcp_hosts.Host.for_file(str(tmp_path / "new.json"))
    assert fresh.connect()["ok"]
    assert "khervemol" in json.loads(
        (tmp_path / "new.json").read_text())["mcpServers"]
    vs = mcp_hosts.Host.for_file(str(tmp_path / "vs.json"), shape="servers")
    vs.entry_extra = {"type": "stdio"}
    assert vs.connect()["ok"]
    assert json.loads((tmp_path / "vs.json").read_text())["servers"][
        "khervemol"]["type"] == "stdio"


def test_host_snippets():
    snippet = json.loads(mcp_hosts.host_config())
    assert list(snippet["mcpServers"]) == ["khervemol"]
    assert "khervemol.mcp_server" in mcp_hosts.cli_command()
    assert mcp_hosts.cli_command().startswith("claude mcp add khervemol")
    assert mcp_hosts.host_by_key("claude-desktop").label == "Claude Desktop"
    assert mcp_hosts.host_by_key("nope") is None
    assert all(h.key for h in mcp_hosts.HOSTS)


# ------------------------------------------------------- bridge and server
@pytest.fixture
def state_dir(tmp_path, monkeypatch):
    monkeypatch.setenv(mcp_server.STATE_DIR_ENV, str(tmp_path / "state"))
    return tmp_path / "state"


@pytest.fixture
def bridge(win, state_dir):
    b = mcp_bridge.McpBridge(win)
    if not b.start():
        pytest.skip("cannot open a loopback socket here")
    yield b
    b.stop()


def pump(qapp, fn):
    """Run *fn* (blocking socket code) in a thread while the GUI thread
    keeps processing events; return its result or re-raise."""
    box = {}

    def target():
        try:
            box["value"] = fn()
        except BaseException as exc:            # noqa: BLE001
            box["error"] = exc

    t = threading.Thread(target=target, daemon=True)
    t.start()
    deadline = time.time() + 60
    while t.is_alive() and time.time() < deadline:
        qapp.processEvents()
        time.sleep(0.003)
    t.join(1)
    assert not t.is_alive(), "the client thread hung"
    if "error" in box:
        raise box["error"]
    return box.get("value")


def test_state_dir_and_endpoint_file(bridge, state_dir):
    assert mcp_server.state_dir() == str(state_dir)
    path = mcp_server.endpoint_path()
    info = mcp_server.read_endpoint()
    assert info["host"] == "127.0.0.1" and info["port"] == bridge.port()
    assert info["token"] == bridge.token() and len(info["token"]) >= 32
    assert info["pid"] == os.getpid()
    assert info["http_url"].startswith("http://127.0.0.1:")
    if not sys.platform.startswith("win"):
        assert (os.stat(path).st_mode & 0o777) == 0o600
    bridge.stop()
    assert not os.path.exists(path) and bridge.token() == ""
    assert mcp_server.read_endpoint() is None


def test_bridge_off_by_default_and_a_stale_file_is_left_alone(win, state_dir):
    b = mcp_bridge.McpBridge(win)
    assert not b.is_running() and b.port() == 0
    assert not os.path.exists(mcp_server.endpoint_path())
    os.makedirs(state_dir)
    with open(mcp_server.endpoint_path(), "w") as fh:
        json.dump({"port": 1, "token": "someone else's"}, fh)
    b.stop()                                      # was never started
    assert os.path.exists(mcp_server.endpoint_path())


def test_bridge_requires_the_token(qapp, bridge):
    def go():
        client = mcp_server.BridgeClient()
        client._connect()
        client._token = "wrong"
        try:
            client.request("get_status")
        except mcp_server.BridgeError as exc:
            return str(exc)
        finally:
            client.close()
    assert "Invalid bridge token" in pump(qapp, go)


def test_stdio_server_protocol_against_a_live_bridge(qapp, win, bridge):
    server = mcp_server.McpServer(mcp_server.BridgeClient())

    def conversation():
        out = {}
        out["init"] = server.handle({
            "jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {"protocolVersion": "2025-06-18",
                       "capabilities": {}, "clientInfo": {"name": "t"}}})
        out["notif"] = server.handle({"jsonrpc": "2.0",
                                      "method": "notifications/initialized"})
        out["ping"] = server.handle({"jsonrpc": "2.0", "id": 2,
                                     "method": "ping"})
        out["tools"] = server.handle({"jsonrpc": "2.0", "id": 3,
                                      "method": "tools/list"})
        out["info"] = server.handle({
            "jsonrpc": "2.0", "id": 4, "method": "tools/call",
            "params": {"name": "get_document_info", "arguments": {}}})
        out["build"] = server.handle({
            "jsonrpc": "2.0", "id": 5, "method": "tools/call",
            "params": {"name": "build_molecule",
                       "arguments": {"name": "caffeine"}}})
        out["render"] = server.handle({
            "jsonrpc": "2.0", "id": 6, "method": "tools/call",
            "params": {"name": "render_view",
                       "arguments": {"width": 200, "height": 150}}})
        out["bad"] = server.handle({
            "jsonrpc": "2.0", "id": 7, "method": "tools/call",
            "params": {"name": "build_molecule",
                       "arguments": {"name": "nosuchmolecule"}}})
        out["unknown"] = server.handle({"jsonrpc": "2.0", "id": 8,
                                        "method": "frobnicate"})
        return out

    out = pump(qapp, conversation)
    init = out["init"]["result"]
    assert init["protocolVersion"] == "2025-06-18"
    assert init["serverInfo"]["name"] == "khervemol"
    assert "LIVE KherveMol window" in init["instructions"]
    assert out["notif"] is None and out["ping"]["result"] == {}
    tools = out["tools"]["result"]["tools"]
    assert [t["name"] for t in tools] == mcp_schema.TOOL_NAMES
    assert all(t["inputSchema"]["type"] == "object" for t in tools)
    info = out["info"]["result"]
    assert info["isError"] is False
    assert json.loads(info["content"][0]["text"])["formula"] == "C2H6O"
    assert win.viewer.mol.formula() == "C8H10N4O2"    # the window changed
    blocks = out["render"]["result"]["content"]
    assert blocks[0]["type"] == "image" and blocks[0]["mimeType"] == "image/png"
    assert base64.b64decode(blocks[0]["data"])[:8] == PNG
    assert blocks[1]["type"] == "text"
    bad = out["bad"]["result"]
    assert bad["isError"] is True
    assert "No library compound" in json.loads(bad["content"][0]["text"])[
        "error"]
    assert out["unknown"]["error"]["code"] == -32601
    tools_run = [e["tool"] for e in bridge.log]
    assert "build_molecule" in tools_run and "render_view" in tools_run


def test_stdio_server_as_a_subprocess(qapp, win, bridge, state_dir):
    """The real thing: `python -m khervemol.mcp_server` speaking JSON lines
    on stdin / stdout, finding the window through the endpoint file."""
    requests = [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize",
         "params": {"protocolVersion": "2024-11-05"}},
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
        {"jsonrpc": "2.0", "id": 3, "method": "tools/call",
         "params": {"name": "build_reaction",
                    "arguments": {"equation": "2 H2 + O2 -> 2 H2O"}}},
    ]
    env = dict(os.environ, PYTHONPATH=ROOT,
               **{mcp_server.STATE_DIR_ENV: str(state_dir)})

    def go():
        proc = subprocess.run(
            [sys.executable, "-m", "khervemol.mcp_server"], cwd=ROOT, env=env,
            input="".join(json.dumps(r) + "\n" for r in requests).encode(),
            capture_output=True, timeout=90)
        return proc

    proc = pump(qapp, go)
    assert proc.returncode == 0, proc.stderr.decode()
    replies = [json.loads(line) for line in proc.stdout.splitlines()]
    assert [r["id"] for r in replies] == [1, 2, 3]
    assert replies[0]["result"]["protocolVersion"] == "2024-11-05"
    assert len(replies[1]["result"]["tools"]) == len(mcp_schema.TOOLS)
    call = replies[2]["result"]
    assert call["isError"] is False
    assert json.loads(call["content"][0]["text"])["reaction"]["balanced"]
    assert win.viewer.mol.reaction


def test_stdio_server_says_when_the_app_is_not_running(state_dir):
    server = mcp_server.McpServer(mcp_server.BridgeClient())
    init = server.handle({"jsonrpc": "2.0", "id": 1, "method": "initialize",
                          "params": {}})
    assert init["result"]["serverInfo"]["name"] == "khervemol"
    reply = server.handle({"jsonrpc": "2.0", "id": 2, "method": "tools/call",
                           "params": {"name": "get_document_info"}})
    assert "not reachable" in reply["error"]["message"]
    assert "Connect to Claude" in reply["error"]["message"]


def test_access_levels(qapp, win, bridge, tmp_path):
    def call(_tool, **args):
        return bridge._call_tool({"name": _tool, "input": args})

    assert bridge.access() == "full"
    bridge.set_access("read")
    refused = call("build_molecule", name="water")
    assert "Refused" in refused["error"] and "Read only" in refused["error"]
    assert win.viewer.mol.formula() == "C2H6O"
    assert "error" not in call("get_document_info")
    assert "error" not in call("render_view", width=100, height=80)
    assert {t["name"] for t in bridge.visible_tools()} == \
        mcp_bridge.READ_ONLY_TOOLS
    bridge.set_access("edit")
    assert "error" not in call("build_molecule", name="water")
    target = str(tmp_path / "w.kmol")
    refused = call("save_document", path=target)
    assert "Full" in refused["error"] and not os.path.exists(target)
    assert "Full" in call("open_document", path=target)["error"]
    assert "Full" in call("export_image", path=str(tmp_path / "a.png"))["error"]
    assert "no file yet" in call("save_document")["error"]   # no path: allowed
    bridge.set_access("full")
    assert "error" not in call("save_document", path=target)
    assert os.path.exists(target)
    with pytest.raises(ValueError):
        bridge.set_access("root")
    assert [e["outcome"] for e in bridge.log if e["tool"] == "build_molecule"
            ][0] == "refused"
    assert "Missing tool name" in bridge._call_tool({})["error"]


def test_bridge_status_and_busy_guard(win, bridge):
    st = bridge._status()
    assert st["app"] == "KherveMol" and st["formula"] == "C2H6O"
    bridge._busy = True
    assert "still running" in bridge._call_tool(
        {"name": "get_document_info"})["error"]
    bridge._busy = False


def test_http_transport(qapp, win, bridge):
    url = bridge.http_url()
    if not url:
        pytest.skip("HTTP listener unavailable")
    token = bridge.token()

    def post(body, headers=None):
        req = urllib.request.Request(
            url, data=json.dumps(body).encode(),
            headers={"Content-Type": "application/json", **(headers or {})})
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                raw = resp.read()
                return resp.status, json.loads(raw) if raw else None
        except urllib.error.HTTPError as exc:
            return exc.code, json.loads(exc.read() or b"null")

    def go():
        out = {}
        call = {"jsonrpc": "2.0", "id": 1, "method": "tools/list"}
        out["noauth"] = post(call)
        out["origin"] = post(call, {"Authorization": f"Bearer {token}",
                                    "Origin": "https://evil.example"})
        out["wrong"] = post(call, {"Authorization": "Bearer nope"})
        out["list"] = post(call, {"Authorization": f"Bearer {token}"})
        out["call"] = post(
            {"jsonrpc": "2.0", "id": 2, "method": "tools/call",
             "params": {"name": "build_molecule",
                        "arguments": {"name": "water"}}},
            {"Authorization": f"Bearer {token}",
             "Origin": "http://localhost:3000"})
        out["notif"] = post({"jsonrpc": "2.0",
                             "method": "notifications/initialized"},
                            {"Authorization": f"Bearer {token}"})
        return out

    out = pump(qapp, go)
    assert out["noauth"][0] == 401 and out["wrong"][0] == 401
    assert out["origin"][0] == 403
    status, body = out["list"]
    assert status == 200 and len(body["result"]["tools"]) == len(
        mcp_schema.TOOLS)
    assert out["call"][0] == 200 and not out["call"][1]["result"]["isError"]
    assert win.viewer.mol.formula() == "H2O"
    assert out["notif"][0] == 202


# ------------------------------------------------------------ dialog & menu
def test_install_adds_the_help_action_above_about(qapp, win, state_dir):
    from khervemol import mcp_dialog
    bridge = mcp_dialog.install(win)
    assert mcp_dialog.install(win) is bridge          # idempotent
    assert not bridge.is_running()                    # off until enabled
    help_menu = [a.menu() for a in win.menuBar().actions()
                 if a.text().replace("&", "") == "Help"][0]
    texts = [a.text() for a in help_menu.actions()]
    assert any("Connect to Claude" in t for t in texts)
    assert texts.index([t for t in texts if "Connect to Claude" in t][0]) \
        < texts.index([t for t in texts if t.startswith("About")][0])
    assert bridge.parent() is win


def test_dialog_turns_the_bridge_on_and_off(qapp, win, state_dir):
    from PyQt5.QtCore import QSettings
    from khervemol import mcp_dialog, style
    QSettings(*style._SETTINGS).remove("mcp/enabled")
    bridge = mcp_dialog.install(win)
    dlg = mcp_dialog.McpServerDialog(bridge, win)
    try:
        assert not dlg._enable.isChecked()
        assert "Stopped" in dlg._status.text()
        assert "khervemol.mcp_server" in dlg._snippet.toPlainText()
        assert dlg._hosts.count() == len(mcp_hosts.HOSTS)
        dlg._enable.setChecked(True)
        if not bridge.is_running():
            pytest.skip("cannot open a loopback socket here")
        assert "Listening" in dlg._status.text()
        assert os.path.exists(mcp_server.endpoint_path())
        assert QSettings(*style._SETTINGS).value(
            "mcp/enabled", False, type=bool) is True
        dlg._flavour.setCurrentIndex(2)
        assert bridge.token() in dlg._snippet.toPlainText()
        dlg._access.setCurrentIndex(0)
        assert bridge.access() == "read"
        bridge.set_access("full")
        dlg._enable.setChecked(False)
        assert not bridge.is_running()
        assert not os.path.exists(mcp_server.endpoint_path())
        assert QSettings(*style._SETTINGS).value(
            "mcp/enabled", False, type=bool) is False
    finally:
        QSettings(*style._SETTINGS).remove("mcp/enabled")
        QSettings(*style._SETTINGS).remove("mcp/access")
        bridge.stop()
        dlg.close()
