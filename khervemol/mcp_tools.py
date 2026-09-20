"""Runs an MCP tool against the live KherveMol window.

`mcp_schema.py` is the contract; this is the implementation.  Every
method here touches the real `MainWindow` and its `Viewer3D`, so it MUST
run on the GUI thread -- `mcp_bridge.McpBridge` is what guarantees that
(its ``QTcpServer`` delivers requests on the GUI thread).

Nothing here re-implements an editing operation.  Structures come from
`entries` / `chem` / `reactions`, edits go through the viewer's own
methods (which own the change signals, the 2D-sketch mirror and the
structure tree) and `model`, so an MCP edit and a mouse edit are the
same edit.  The library lookups live in `mcp_library` and never touch
the window.

Nothing here may raise a modal dialog: a tool call arrives with nobody
at the keyboard, so a `QMessageBox` would freeze the app.  Builds are
therefore done off-window and only shown once they succeeded.

Copyright (C) 2026 Gwilherm Kerherve

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
"""

from __future__ import annotations

import base64
import math
import os
from contextlib import contextmanager
from urllib.parse import urlencode

from PyQt5.QtCore import QBuffer, QByteArray, QIODevice

from . import (__version__, chem, document, elements, entries,
               library, mcp_library, model, polymers, properties, reactions,
               rdkit_io, shelf, svgexport)
from .crystal import BuildError
from .mcp_schema import (DEFAULT_IMAGE_SIZE, NANO_PARAMS, check_args,
                         tool_schema)
from .mcp_server import IMAGE_KEY
from .smiles import SmilesError
from .viewer3d import STANDARD_VIEWS

#: elements `fill_hydrogens` caps when no atoms are named (a metal or a
#: noble gas is not "missing" a hydrogen)
_HYDROGENATE = frozenset("B C N O F Si P S Cl Br I Se As Ge Sn Te".split())

#: cap on the atoms `get_structure` returns unless the client raises it
_DEFAULT_MAX_ATOMS = 300


class ToolError(Exception):
    """A tool failed for a reason the client should read and act on."""


def _r(value, digits=4):
    return round(float(value), digits)


class McpToolExecutor:
    """Executes one named tool against a `MainWindow`."""

    def __init__(self, window):
        self._w = window

    # -- Plumbing -----------------------------------------------------

    @property
    def _v(self):
        return self._w.viewer

    @property
    def _mol(self):
        return self._w.viewer.mol

    def execute(self, name: str, tool_input: dict) -> dict:
        """Run *name*; never raises -- a failure comes back as {"error"}."""
        handler = getattr(self, f"_t_{name}", None)
        schema = tool_schema(name)
        if handler is None or schema is None:
            return {"error": f"Unknown tool: {name}. tools/list names "
                             "every tool."}
        try:
            args = check_args(schema["input_schema"], tool_input or {})
            return handler(args)
        except (ToolError, BuildError, SmilesError, polymers.PolymerError,
                ValueError) as exc:
            return {"error": _message(exc)}
        except KeyError as exc:
            return {"error": _message(exc)}
        except Exception as exc:              # pragma: no cover - defensive
            return {"error": f"{type(exc).__name__}: {exc}"}

    # -- Shared helpers -----------------------------------------------

    def _need_editable(self):
        if not self._v.editable:
            kind = mcp_library.molecule_kind(self._mol)
            raise ToolError(
                f"The {kind} on screen is fixed -- crystals, surfaces, "
                "nanostructures and reaction scenes cannot be edited atom "
                "by atom. Build a molecule (build_molecule) or new_document "
                "first.")

    def _atom(self, index, name="atom"):
        n = len(self._mol.atoms)
        if not 0 <= index < n:
            raise ToolError(f"{name} {index} does not exist: this structure "
                            f"has {n} atoms (indices 0-{n - 1}). Call "
                            "get_structure for the current numbering.")
        return index

    def _redraw(self, structure=True):
        """Repaint after a direct change and tell every listener (the 2D
        sketch, the structure tree, the title)."""
        v = self._v
        v.view.rebuild()
        update = getattr(v, "_update_status", None)
        if update:
            update()
        (v.structure_changed if structure else v.view_changed).emit()

    def _show(self, mol, label=None):
        """Put a built structure on screen (what `MainWindow.load_entry`
        does, minus its modal error box)."""
        w = self._w
        w.viewer.set_molecule(mol)
        sync = getattr(w, "_sync_sketch", None)
        if sync:
            sync(force=True)
        w.tabs.setCurrentIndex(0)
        retitle = getattr(w, "_retitle", None)
        if retitle:
            retitle()
        w.statusBar().showMessage(f"MCP: showing {label or mol.label}")

    def _summary(self):
        mol = self._mol
        return {
            "label": mol.label,
            "formula": mol.formula(),
            "kind": mcp_library.molecule_kind(mol),
            "atoms": len(mol.atoms),
            "bonds": len(mol.bonds),
            "editable": bool(self._v.editable),
        }

    def _built(self, **extra):
        out = {"ok": True, **self._summary()}
        out.update(extra)
        return out

    def _view_state(self):
        v, mol = self._v, self._mol
        out = {
            "az": _r(math.degrees(mol.az), 2),
            "el": _r(math.degrees(mol.el), 2),
            "bond_spread": _r(mol.bond, 2),
            "renderer": v.renderer,
            "style": v.style,
            "labels": bool(v.labels_btn.isChecked()),
        }
        if hasattr(mol, "cell_visible"):
            out["cell_outline"] = bool(mol.cell_visible)
        if v.renderer != "gl" and v.style != "ball_and_stick":
            out["note"] = ("space_filling and sticks are drawn only by the "
                           "gl renderer; the classic renderer shows ball "
                           "and stick.")
        return out

    def _resolve_molecule(self, name=None, smiles=None, label=None):
        """A viewer `Molecule` from a library name / key / formula or a
        SMILES string."""
        if smiles:
            return entries.build("smiles", smiles, label)
        if str(name).startswith("@"):          # a kept molecule
            if mcp_library.shelf_name(name) is None:
                raise BuildError(
                    f"No molecule '{name}' on the My molecules shelf "
                    "(list_molecules shows what is kept; keep_molecule "
                    "adds the one on screen).")
            return entries.build("mine", name.lstrip("@"))
        key = mcp_library.compound_key(name)
        if key is not None:
            return entries.build("compound", key)
        kept = mcp_library.shelf_name(name)
        low = str(name).strip().lower().replace(" ", "_")
        for k in library.names():
            if low == k or low == library.label(k).lower():
                return entries.build("model", k)
        if kept is not None:
            return entries.build("mine", kept)
        try:                                   # C60 and the other cages
            return chem.compound_model(name)
        except KeyError:
            raise BuildError(mcp_library._no_compound(name))

    # -- Looking ------------------------------------------------------

    def _t_get_document_info(self, args):
        v, w, mol = self._v, self._w, self._mol
        out = {"app": "KherveMol", "version": __version__,
               **self._summary(), "name": mol.name,
               "view": self._view_state(),
               "selection": list(v.selection),
               "path": getattr(w, "_path", None),
               "tab": "3d" if w.tabs.currentIndex() == 0 else "2d",
               "sketch": {"atoms": len(w.sketch.atoms),
                          "bonds": len(w.sketch.bonds)},
               "rdkit": bool(rdkit_io.available()),
               "window_title": w.windowTitle()}
        if mol.crystal:
            out["cells"] = list(mol.cells)
            out["polyhedra"] = bool(mol.poly)
        if mol.reaction or v.has_animation:
            out["reaction"] = mol.reaction
            anim = {"available": bool(v.has_animation),
                    "active": bool(v.animating),
                    "playing": bool(v.playing)}
            p = getattr(v, "_anim_p", None)
            if p is not None and v.has_animation:
                anim["progress"] = _r(p, 3)
                anim["stage"] = mol.anim.stage(p)
            out["animation"] = anim
        return out

    def _t_search_library(self, args):
        return mcp_library.search(args["text"], args.get("kind"),
                                  args.get("limit"))

    def _t_list_molecules(self, args):
        return mcp_library.list_molecules(
            args.get("category"), args.get("search"), args.get("compound"),
            args.get("limit"), args.get("offset"))

    def _t_list_crystals(self, args):
        return mcp_library.list_crystals(
            args.get("key"), args.get("category"), args.get("search"),
            args.get("limit"), args.get("offset"))

    def _t_list_polymers(self, args):
        return mcp_library.list_polymers(args.get("search"),
                                         args.get("category"))

    def _t_list_reactions(self, args):
        return mcp_library.list_reactions(args.get("search"),
                                          args.get("equation"))

    def _t_get_structure(self, args):
        mol = self._mol
        cap = args.get("max_atoms", _DEFAULT_MAX_ATOMS)
        atoms = mol.atoms
        shown = atoms[:cap]
        out = {**self._summary(), "unit": "angstrom",
               "atoms": [[a[0], _r(a[1]), _r(a[2]), _r(a[3])]
                         for a in shown],
               "bonds": [[i, j, o, _r(model.distance(atoms, i, j), 3)]
                         for i, j, o in mol.bonds
                         if i < len(shown) and j < len(shown)]}
        if len(atoms) > cap:
            out["truncated"] = True
            out["note"] = (f"Only the first {cap} of {len(atoms)} atoms "
                           "are listed; raise max_atoms for more.")
        if mol.crystal and mol.edges:
            out["cell_edges"] = [[[_r(c, 3) for c in p], [_r(c, 3) for c in q]]
                                 for p, q, *_s in mol.edges[:48]]
        if args.get("geometry") and len(atoms) <= 60:
            out["angles"] = self._angles()
        return out

    def _angles(self):
        mol = self._mol
        nbrs = {}
        for i, j, _o in mol.bonds:
            nbrs.setdefault(i, []).append(j)
            nbrs.setdefault(j, []).append(i)
        rows = []
        for j, ring in nbrs.items():
            for a in range(len(ring)):
                for b in range(a + 1, len(ring)):
                    rows.append([ring[a], j, ring[b], _r(
                        model.angle(mol.atoms, ring[a], j, ring[b]), 1)])
        return rows

    def _t_properties(self, args):
        rows = properties.compute(self._mol)
        return {**self._summary(),
                "properties": {label: value for label, value in rows},
                "rows": [{"label": a, "value": b} for a, b in rows]}

    @contextmanager
    def _looking(self, az=None, el=None, style=None, labels=None,
                 spread=None):
        """Aim the viewer somewhere for one picture, then put the user's
        view back exactly as it was."""
        v, mol = self._v, self._mol
        saved = (mol.az, mol.el, mol.bond, v.style,
                 v.labels_btn.isChecked())
        try:
            if az is not None:
                mol.az = az
            if el is not None:
                mol.el = el
            if spread is not None:
                mol.bond = spread
            if labels is not None and labels != saved[4]:
                v.labels_btn.setChecked(labels)
            if style is not None and style != saved[3]:
                v.set_style(style)
            v.view.rebuild()
            yield
        finally:
            mol.az, mol.el, mol.bond = saved[:3]
            if v.labels_btn.isChecked() != saved[4]:
                v.labels_btn.setChecked(saved[4])
            if v.style != saved[3]:
                v.set_style(saved[3])
            v.view.rebuild()

    def _camera(self, args):
        """(az, el) radians from render_view / set_view arguments."""
        az = el = None
        if "orientation" in args:
            for title, vaz, vel in STANDARD_VIEWS:
                if title.lower() == args["orientation"]:
                    az, el = vaz, vel
        if "az" in args:
            az = math.radians(args["az"])
        if "el" in args:
            el = math.radians(args["el"])
        return az, el

    @staticmethod
    def _png_b64(img):
        if img is None or img.isNull():
            raise ToolError("The view could not be rendered (empty image).")
        buf = QBuffer()
        buf.open(QIODevice.WriteOnly)
        if not img.save(buf, "PNG"):
            raise ToolError("Could not encode the picture as PNG.")
        return base64.b64encode(bytes(QByteArray(buf.data()))).decode("ascii")

    def _t_render_view(self, args):
        w = args.get("width", DEFAULT_IMAGE_SIZE[0])
        h = args.get("height", DEFAULT_IMAGE_SIZE[1])
        if args.get("view") == "2d":
            if not self._w.sketch.atoms:
                raise ToolError("The 2D sketch is empty (a crystal, surface "
                                "or reaction scene has no skeletal form).")
            img = self._w.sketch.image(w, h)
            return {IMAGE_KEY: self._png_b64(img), "width": w, "height": h,
                    "view": "2d", "atoms": len(self._w.sketch.atoms)}
        az, el = self._camera(args)
        spread = args.get("bond_spread")
        with self._looking(az, el, args.get("style"), args.get("labels"),
                           spread):
            camera = self._view_state()
            img = self._v.render_image(w, h)
        out = {IMAGE_KEY: self._png_b64(img), "width": img.width(),
               "height": img.height(), "view": "3d", "camera": camera,
               **self._summary()}
        return out

    def _t_select_atoms(self, args):
        v = self._v
        wanted = []
        for i in args["atoms"]:
            self._atom(i)
            if i not in wanted:
                wanted.append(i)
        v.cancel_pick()
        if not wanted:
            v.select_atom(None)
        for k, i in enumerate(wanted):
            v.select_atom(i, toggle=k > 0)
        return {"ok": True, "selection": list(v.selection)}

    # -- Building -----------------------------------------------------

    def _t_build_molecule(self, args):
        name, smi = args.get("name"), args.get("smiles")
        if bool(name) == bool(smi):
            raise ToolError("Give exactly one of `name` (library key, name "
                            "or formula) or `smiles`.")
        mode = args.get("mode", "replace")
        mol = self._resolve_molecule(name, smi, args.get("label"))
        if mode == "add":
            if self._mol.crystal or mol.crystal or not self._mol.atoms:
                raise ToolError(
                    "mode 'add' merges a molecule into another molecule; "
                    "the current structure is a lattice or scene (or empty). "
                    "Use mode 'replace'.")
            before = len(self._mol.atoms)
            self._v.add_molecule(mol)
            retitle = getattr(self._w, "_retitle", None)
            if retitle:
                retitle()
            return self._built(added=mol.label, atoms_added=len(mol.atoms),
                               first_new_atom=before)
        self._show(mol, args.get("label"))
        return self._built()

    def _t_build_crystal(self, args):
        crystal = mcp_library.crystal_by_name(args["crystal"])
        cells = tuple(args.get("cells", (1, 1, 1)))
        mol = chem.crystal_model(crystal, cells,
                                 boundary=args.get("boundary", True))
        self._show(mol)
        return self._built(crystal=mcp_library.crystal_row(crystal),
                           cells=list(cells))

    def _adsorbate(self, spec):
        given = [k for k in ("smiles", "compound") if spec.get(k)]
        if spec.get("current"):
            given.append("current")
        if len(given) != 1:
            raise ToolError("adsorbate needs exactly one of `smiles`, "
                            "`compound` or `current: true`.")
        if "current" in given:
            mol = self._mol
            if mol.crystal or not mol.atoms:
                raise ToolError("adsorbate `current` needs a molecule on "
                                "screen (the view shows a lattice or is "
                                "empty). Build the molecule first.")
            return mol
        return self._resolve_molecule(spec.get("compound"),
                                      spec.get("smiles"))

    def _t_build_surface(self, args):
        crystal = mcp_library.crystal_by_name(args["crystal"])
        spec = args.get("adsorbate")
        molecule = self._adsorbate(spec) if spec is not None else None
        base = chem.surface_model(
            crystal, args["miller"], args.get("repeat"),
            args.get("layers", 3), args.get("termination"))
        slab_atoms = len(base.atoms)
        mol = base
        if molecule is not None:
            mode = spec.get("mode", "flat")
            if mode == "upright" and len(molecule.atoms) == 2:
                molecule, mode = _stand_diatomic(molecule), "as drawn"
            mol = chem.add_adsorbate(
                base, molecule, height=spec.get("height", 2.4),
                dx=spec.get("dx", 0.0), dy=spec.get("dy", 0.0),
                mode=mode, spin=spec.get("spin", 0.0))
        self._show(mol)
        extra = {"crystal": crystal.key, "slab_atoms": slab_atoms}
        if molecule is not None:
            extra["adsorbate"] = {"label": molecule.label,
                                  "formula": molecule.formula(),
                                  "atoms": len(molecule.atoms)}
        return self._built(**extra)

    def _t_build_nano(self, args):
        structure = args["structure"]
        allowed = NANO_PARAMS[structure]
        extra = [k for k in args if k != "structure" and k not in allowed]
        if extra:
            raise ToolError(
                f"'{structure}' does not take {', '.join(extra)}. It "
                f"accepts: {', '.join(allowed)}.")
        kw = {k: args[k] for k in allowed if k in args}
        if structure == "fullerene":
            kw.setdefault("kind", "c60")
            kw["kind"] = str(kw["kind"]).lower()
        if structure == "defect":
            kw["kind"] = str(kw.get("kind", "vacancy")).lower()
        mol = chem.nano_model(structure, **kw)
        self._show(mol)
        return self._built(structure=structure, parameters=kw)

    def _t_build_polymer(self, args):
        preset, unit = args.get("preset"), args.get("unit")
        if bool(preset) == bool(unit):
            raise ToolError("Give exactly one of `preset` (see "
                            "list_polymers) or `unit` (a repeat-unit "
                            "SMILES).")
        if preset:
            if args.get("head") or args.get("tail"):
                raise ToolError("head / tail caps apply to a custom `unit`; "
                                "a preset carries its own.")
            key = mcp_library.polymer_by_key(preset)
            query = {"n": args["n"]} if "n" in args else {}
            value = key + ("?" + urlencode(query) if query else "")
        else:
            query = {"unit": unit, "n": args.get("n", 4),
                     "head": args.get("head", ""),
                     "tail": args.get("tail", "")}
            value = "custom?" + urlencode(query)
        mol = entries.build_polymer(value)
        self._show(mol)
        return self._built(unit=unit or polymers.PRESETS[key][1])

    def _t_build_reaction(self, args):
        try:
            mol, rx = reactions.reaction_model(
                args["equation"], args.get("balance", True))
        except (BuildError, KeyError, ValueError) as exc:
            raise BuildError(_message(exc))
        self._show(mol, args["equation"])
        v = self._v
        if args.get("play") and v.has_animation:
            v.play(False)
        report = mcp_library.reaction_report(rx)
        return self._built(reaction=report, animation=bool(v.has_animation),
                           playing=bool(v.playing))

    def _need_film(self):
        if not self._v.has_animation:
            raise ToolError("The scene on screen is not a reaction: call "
                            "build_reaction first.")

    def _film_state(self):
        v = self._v
        p = getattr(v, "_anim_p", None)
        out = {"ok": True, "playing": bool(v.playing),
               "active": bool(v.animating)}
        if p is not None and v.has_animation:
            out["progress"] = _r(p, 3)
            out["stage"] = self._mol.anim.stage(p)
        return out

    def _t_play_reaction(self, args):
        self._need_film()
        v = self._v
        action = args.get("action", "play")
        if action == "play":
            v.play(args.get("restore_at_end", False))
        elif action == "pause":
            v.pause()
        else:
            v.stop_animation()
        return self._film_state()

    def _t_set_reaction_progress(self, args):
        self._need_film()
        v = self._v
        if v.playing:
            v.pause()
        v.set_progress(args["progress"])
        return self._film_state()

    # -- Editing ------------------------------------------------------

    def _t_add_atom(self, args):
        self._need_editable()
        v, mol = self._v, self._mol
        symbol = args["element"].strip()
        symbol = symbol[:1].upper() + symbol[1:].lower()
        if symbol not in elements.SYMBOLS:
            raise ToolError(f"'{args['element']}' is not an element symbol "
                            "(H, C, N, O, Cl, Fe ...).")
        order = args.get("order", 1)
        if "anchor" in args:
            anchor = self._atom(args["anchor"], "anchor")
        elif v.selected is not None and v.selected < len(mol.atoms):
            anchor = v.selected
        else:
            anchor = len(mol.atoms) - 1 if mol.atoms else None
        bonded = False
        if anchor is not None:
            free = model.free_valence(mol.atoms, mol.bonds, anchor)
            bonded = free >= order and elements.valence(symbol) >= order
        if anchor is not None:
            v.selected = anchor
        previous, v.order = v.order, order
        try:
            v.add_element(symbol)
        finally:
            v.order = previous
        index = len(mol.atoms) - 1
        out = {"ok": True, "index": index, "element": symbol,
               "anchor": anchor, "bonded": bonded, "order": order,
               "formula": mol.formula(), "atoms": len(mol.atoms)}
        if bonded:
            out["bond_length"] = _r(model.distance(mol.atoms, anchor, index),
                                    3)
        else:
            out["note"] = (
                f"Atom {anchor} has no free valence for a "
                f"{['single', 'double', 'triple'][order - 1]} {symbol} "
                "bond, so the new atom was placed unbonded. Delete a "
                "hydrogen from it first, or choose another anchor."
                if anchor is not None else "Placed as the first atom.")
        return out

    def _t_fill_hydrogens(self, args):
        self._need_editable()
        mol = self._mol
        if "atoms" in args:
            targets = [self._atom(i) for i in args["atoms"]]
        else:
            targets = [i for i, a in enumerate(mol.atoms)
                       if a[0] in _HYDROGENATE]
        added = 0
        for i in targets:
            if mol.atoms[i][0] == "H":
                continue
            while model.free_valence(mol.atoms, mol.bonds, i) > 0 \
                    and elements.valence(mol.atoms[i][0]) > 0:
                model.add_bonded_atom(mol.atoms, mol.bonds, i, "H", 1)
                added += 1
        if added:
            self._redraw()
        return self._built(hydrogens_added=added)

    def _t_delete_atom(self, args):
        self._need_editable()
        wanted = sorted({self._atom(i) for i in args["atoms"]}, reverse=True)
        if len(wanted) >= len(self._mol.atoms):
            raise ToolError("At least one atom must remain; use "
                            "new_document to start over.")
        v = self._v
        for i in wanted:
            v.selected = i
            v.delete_selected()
        return self._built(deleted=sorted(wanted),
                           note="Atom indices above a deleted atom shifted "
                                "down: call get_structure before editing "
                                "again.")

    def _why_not_bond(self, i, j, order):
        mol = self._mol
        if i == j:
            return "Pick two different atoms to bond."
        if model.bond_between(mol.bonds, i, j) is not None:
            return (f"Atoms {i} and {j} are already bonded -- use "
                    "set_bond_order to change the order.")
        short = [f"{mol.atoms[k][0]} (atom {k})" for k in (i, j)
                 if model.free_valence(mol.atoms, mol.bonds, k) < order]
        return (f"No free valence on {' and '.join(short)} for a bond of "
                f"order {order} -- delete_atom a hydrogen from it first.")

    def _t_bond_atoms(self, args):
        self._need_editable()
        i, j = self._atom(args["i"], "i"), self._atom(args["j"], "j")
        order = args.get("order", 1)
        mol = self._mol
        if not model.can_bond(mol.atoms, mol.bonds, i, j, order):
            raise ToolError(self._why_not_bond(i, j, order))
        self._v.bond_atoms(i, j, order)
        return self._built(bond=[i, j, order],
                           length=_r(model.distance(mol.atoms, i, j), 3))

    def _bond_index(self, i, j):
        i, j = self._atom(i, "i"), self._atom(j, "j")
        idx = model.bond_between(self._mol.bonds, i, j)
        if idx is None:
            raise ToolError(f"Atoms {i} and {j} are not bonded. "
                            "bond_atoms joins them.")
        return idx

    def _t_set_bond_order(self, args):
        self._need_editable()
        idx = self._bond_index(args["i"], args["j"])
        order = args["order"]
        if self._mol.bonds[idx][2] != order:
            if not self._v.can_set_order(idx, order):
                raise ToolError(
                    f"Cannot make that bond order {order}: one of its "
                    "atoms has no free valence. delete_atom a hydrogen "
                    "from it first.")
            self._v.set_bond_order(idx, order)
        i, j, o = self._mol.bonds[idx]
        return self._built(bond=[i, j, o],
                           length=_r(model.distance(self._mol.atoms, i, j),
                                     3))

    def _t_delete_bond(self, args):
        self._need_editable()
        idx = self._bond_index(args["i"], args["j"])
        self._v.delete_bond(idx)
        return self._built(removed=[args["i"], args["j"]])

    def _t_move_atom(self, args):
        self._need_editable()
        if ("position" in args) == ("delta" in args):
            raise ToolError("Give exactly one of `position` [x,y,z] or "
                            "`delta` [dx,dy,dz].")
        i = self._atom(args["atom"])
        mol = self._mol
        atom = mol.atoms[i]
        target = (args["position"] if "position" in args
                  else [atom[1 + k] + args["delta"][k] for k in range(3)])
        atom[1:4] = [float(c) for c in target]
        if args.get("keep_bond_lengths", True):
            model.constrain_atom(mol.atoms, mol.bonds, i)
        self._redraw()
        lengths = [[b if a == i else a, _r(model.distance(mol.atoms, a, b), 3)]
                   for a, b, _o in mol.bonds if i in (a, b)]
        return self._built(atom=i, position=[_r(c) for c in atom[1:4]],
                           bond_lengths=lengths)

    def _t_keep_molecule(self, args):
        """Put the molecule on screen on the 'My molecules' shelf."""
        w = self._w
        box = getattr(w, "shelf", None) or shelf.default()
        used = box.add(self._mol, args.get("name"))
        panel = getattr(w, "shelf_panel", None)
        if panel is not None:
            panel.refresh(select=used)
        return {"ok": True, "name": used, "token": shelf.token(used),
                "formula": box.formula(used), "shelf": box.names(),
                "note": "Use it as a species in build_reaction with "
                        f"{shelf.token(used)}, or load it with "
                        f"build_molecule(name='{shelf.token(used)}')."}

    # -- View ---------------------------------------------------------

    def _t_set_view(self, args):
        if not args:
            raise ToolError("Pass at least one of orientation, az, el, "
                            "style, renderer, labels, bond_spread, "
                            "polyhedra, cell_outline, tab.")
        v, mol = self._v, self._mol
        az, el = self._camera(args)
        if az is not None:
            mol.az = az
        if el is not None:
            mol.el = el
        if az is not None or el is not None:
            self._redraw(structure=False)
        if "style" in args:
            v.set_style(args["style"])
        if "renderer" in args:
            v.set_renderer(args["renderer"])
        if "labels" in args:
            v.labels_btn.setChecked(args["labels"])
        if "bond_spread" in args:
            v.bond_slider.setValue(int(round(args["bond_spread"] * 100)))
        if "polyhedra" in args:
            if args["polyhedra"] and not v.poly_btn.isEnabled():
                raise ToolError("No atom has four or more bonded "
                                "neighbours, so there are no coordination "
                                "polyhedra to draw.")
            v.poly_btn.setChecked(args["polyhedra"])
        if "cell_outline" in args:
            setter = getattr(v, "set_cell_visible", None)
            if setter is None or not mol.crystal:
                raise ToolError("cell_outline applies to crystals and "
                                "surfaces only.")
            setter(args["cell_outline"])
        if "tab" in args:
            self._w.tabs.setCurrentIndex(0 if args["tab"] == "3d" else 1)
        return {"ok": True, "view": self._view_state(),
                "tab": "3d" if self._w.tabs.currentIndex() == 0 else "2d"}

    # -- Files --------------------------------------------------------

    @staticmethod
    def _file(path, suffix, must_exist=False, overwrite=True, same=None):
        """A cleaned absolute path with the right suffix."""
        p = os.path.abspath(os.path.expanduser(str(path)))
        if os.path.splitext(p)[1] == "":
            p += suffix
        elif not p.lower().endswith(suffix):
            raise ToolError(f"The path must end in {suffix}, not "
                            f"'{os.path.splitext(p)[1]}'.")
        if must_exist:
            if not os.path.isfile(p):
                raise ToolError(f"No such file: {p}")
            return p
        folder = os.path.dirname(p)
        if not os.path.isdir(folder):
            raise ToolError(f"The folder {folder} does not exist. Create it "
                            "or choose another path.")
        if os.path.exists(p) and not overwrite \
                and not (same and os.path.abspath(same) == p):
            raise ToolError(f"{p} already exists. Pass overwrite: true to "
                            "replace it, or choose another name.")
        return p

    def _t_new_document(self, args):
        self._w.new_document()
        return self._built()

    def _t_open_document(self, args):
        path = self._file(args["path"], ".kmol", must_exist=True)
        try:
            document.load(path)               # parse first: no dialog later
        except Exception as exc:              # noqa: BLE001
            raise ToolError(f"Cannot open {path}: {exc}")
        self._w.open_path(path)
        return self._built(path=path)

    def _t_save_document(self, args):
        w = self._w
        if args.get("path"):
            path = self._file(args["path"], ".kmol",
                              overwrite=args.get("overwrite", False),
                              same=getattr(w, "_path", None))
        else:
            path = getattr(w, "_path", None)
            if not path:
                raise ToolError("This document has no file yet: pass "
                                "`path` (ending in .kmol).")
        try:
            document.save(path, self._mol, w.sketch.atoms, w.sketch.bonds)
        except Exception as exc:              # noqa: BLE001
            raise ToolError(f"Cannot save {path}: {exc}")
        w._path = path
        retitle = getattr(w, "_retitle", None)
        if retitle:
            retitle()
        w.statusBar().showMessage(f"MCP: saved {os.path.basename(path)}")
        return {"ok": True, "path": path, "bytes": os.path.getsize(path)}

    def _t_export_image(self, args):
        path = self._file(args["path"], ".png",
                          overwrite=args.get("overwrite", False))
        w = args.get("width", 1600)
        h = args.get("height", 1200)
        if args.get("view") == "2d":
            if not self._w.sketch.atoms:
                raise ToolError("The 2D sketch is empty.")
            img = self._w.sketch.image(w, h)
        else:
            img = self._v.render_image(w, h)
        if img is None or img.isNull() or not img.save(path, "PNG"):
            raise ToolError(f"Could not write {path}.")
        return {"ok": True, "path": path, "width": img.width(),
                "height": img.height(), "bytes": os.path.getsize(path)}

    def _t_export_svg(self, args):
        path = self._file(args["path"], ".svg",
                          overwrite=args.get("overwrite", False))
        w = self._w
        if args.get("view") == "2d":
            if not w.sketch.atoms:
                raise ToolError("The 2D sketch is empty.")
            specs = svgexport.sketch_specs(w.sketch.atoms, w.sketch.bonds,
                                           w.sketch.show_labels,
                                           w.sketch.mode)
        else:
            specs = self._v.export_specs(1000, 800)
        specs, width, height = svgexport.normalize(specs)
        svgexport.save_specs(path, specs, width, height)
        return {"ok": True, "path": path, "width": width, "height": height,
                "bytes": os.path.getsize(path),
                "note": "Opens in KhervePaint as editable shapes."}


def _stand_diatomic(molecule):
    """A copy of a two-atom molecule with its axis along z, the first atom
    at the bottom (so the first atom of the SMILES faces the surface).
    `chem.add_adsorbate` has no principal axes to work with for fewer than
    three atoms, so it cannot stand one up itself."""
    (_a, x0, y0, z0), (_b, x1, y1, z1) = [a[:4] for a in molecule.atoms]
    d = math.dist((x0, y0, z0), (x1, y1, z1)) or 1.0
    out = molecule.clone()
    out.atoms = [[molecule.atoms[0][0], 0.0, 0.0, -d / 2],
                 [molecule.atoms[1][0], 0.0, 0.0, d / 2]]
    return out


def _message(exc) -> str:
    """The readable text of an exception (a KeyError wraps its message in
    quotes)."""
    if isinstance(exc, KeyError) and exc.args:
        return str(exc.args[0])
    return str(exc.args[0]) if exc.args else str(exc)
