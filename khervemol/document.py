"""Document persistence: the ``.kmol`` JSON format and PNG export.

A ``.kmol`` file stores both the 3D model (atoms/bonds/edges + view) and
the 2D sketch, so a document round-trips completely:

    {"format": "khervemol", "version": 1,
     "mol3d": {"name","label","az","el","bond","rscale","crystal",
               "atoms": [[el,x,y,z]...], "bonds": [[i,j,order]...],
               "edges": [[[x,y,z],[x,y,z],style]...] | null},
     "sketch2d": {"atoms": [[el,x,y]...], "bonds": [[i,j,order]...]}}

Copyright (C) 2026 Gwilherm Kerherve

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
"""

import json

from . import model, render

FORMAT_VERSION = 1


def mol_to_dict(mol):
    edges = None
    if mol.edges:
        edges = [[list(e[0]), list(e[1]), (e[2] if len(e) > 2 else "solid")]
                 for e in mol.edges]
    return {
        "name": mol.name, "label": mol.label,
        "az": mol.az, "el": mol.el, "bond": mol.bond,
        "rscale": mol.rscale, "crystal": mol.crystal,
        "atoms": [list(a) for a in mol.atoms],
        "bonds": [list(b) for b in mol.bonds],
        "edges": edges,
    }


def mol_from_dict(d):
    edges = None
    if d.get("edges"):
        edges = [(tuple(e[0]), tuple(e[1]), e[2]) for e in d["edges"]]
    return model.Molecule(
        atoms=d.get("atoms", []), bonds=d.get("bonds", []),
        name=d.get("name", "custom"), label=d.get("label"),
        az=d.get("az"), el=d.get("el"), bond=d.get("bond"),
        rscale=d.get("rscale", 0.92), crystal=d.get("crystal", False),
        edges=edges)


def save(path, mol, sketch_atoms, sketch_bonds):
    data = {
        "format": "khervemol", "version": FORMAT_VERSION,
        "mol3d": mol_to_dict(mol),
        "sketch2d": {"atoms": [list(a) for a in sketch_atoms],
                     "bonds": [list(b) for b in sketch_bonds]},
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1)


def load(path):
    """Return ``(Molecule, sketch_atoms, sketch_bonds)``."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    mol = mol_from_dict(data.get("mol3d", {}))
    sk = data.get("sketch2d", {})
    return mol, sk.get("atoms", []), sk.get("bonds", [])


def export_png(path, specs, width=1200, height=1000, transparent=False):
    img = render.render_image(specs, width, height, transparent=transparent)
    img.save(path, "PNG")
