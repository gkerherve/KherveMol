"""The molecule as a connectivity tree.

A `StructureTree` mirrors the current `model.Molecule` as a folder-like
outline: the molecule name at the root, then each atom nested under the atom
it hangs off. An atom with further neighbours reads like a folder, a terminal
hydrogen like a file — the shape of the tree *is* the shape of the molecule.

Every row carries the geometry of the bond that reached it: its order, its
length in ångström, and the bond angle at the parent atom. Bonds that close a
ring cannot nest (they would loop forever), so they appear as a leaf pointing
back at the atom they reach.

Selecting a row selects that atom in the 3D viewer, and vice versa.

Copyright (C) 2026 Gwilherm Kerherve

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
"""

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import QTreeWidget, QTreeWidgetItem

from . import elements, icons, model

_ORDER_DASH = {1: "–", 2: "=", 3: "≡"}
_ORDER_NAME = {1: "single", 2: "double", 3: "triple"}
_ATOM_ROLE = Qt.UserRole                # the atom index a row stands for
_RING_ROLE = Qt.UserRole + 1            # True on a ring-closure leaf


def _root_atom(atoms, bonds):
    """Start the tree at the best-connected heavy atom, counting only its
    heavy neighbours — otherwise a CH₂ (four bonds) would outrank a ring
    carbon (three), and the backbone would hang off a side group."""
    if not atoms:
        return None
    degree = [0] * len(atoms)
    for i, j, _o in bonds:
        if atoms[j][0] != "H":
            degree[i] += 1
        if atoms[i][0] != "H":
            degree[j] += 1
    heavy = [i for i, a in enumerate(atoms) if a[0] != "H"]
    return max(heavy or range(len(atoms)), key=lambda i: (degree[i], -i))


def walk(atoms, bonds, root=None):
    """Depth-first spanning tree of the molecule.

    Yields ``(atom, parent, grandparent, order, ring)`` in tree order, where
    *ring* marks a bond that closes a cycle — it becomes a leaf pointing back,
    since nesting it would loop forever. *parent* is None for the root, and
    for the first atom of each disconnected fragment."""
    if not atoms:
        return
    adjacency = {i: [] for i in range(len(atoms))}
    for bi, (i, j, o) in enumerate(bonds):
        adjacency[i].append((j, o, bi))
        adjacency[j].append((i, o, bi))

    first = _root_atom(atoms, bonds) if root is None else root
    seen, done_rings = set(), set()
    # every fragment gets walked, starting from the chosen root
    for start in [first] + [i for i in range(len(atoms)) if i != first]:
        if start in seen:
            continue
        seen.add(start)
        stack = [(start, None, None, 0)]
        while stack:
            atom, parent, grand, order = stack.pop()
            yield atom, parent, grand, order, False
            # heavy atoms before hydrogens, higher bond orders first, so a
            # backbone stays at the top of each branch
            kids = sorted(adjacency[atom],
                          key=lambda t: (atoms[t[0]][0] == "H", -t[1], t[0]))
            for k, o, bi in reversed(kids):
                if k in seen:
                    if bi not in done_rings and k != parent:
                        done_rings.add(bi)
                        yield k, atom, parent, o, True
                    continue
                seen.add(k)
                stack.append((k, atom, parent, o))


class StructureTree(QTreeWidget):
    """Live connectivity outline of one molecule, with per-bond geometry."""

    atom_selected = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setColumnCount(4)
        self.setHeaderLabels(["Atom", "Bond", "Length", "Angle"])
        self.setRootIsDecorated(True)
        self.setAlternatingRowColors(True)
        self.setUniformRowHeights(True)
        self.header().setStretchLastSection(False)
        self.setColumnWidth(0, 140)
        for col, width in ((1, 44), (2, 62), (3, 60)):
            self.setColumnWidth(col, width)
        self._mol = None
        self._rows = {}                 # atom index → its (non-ring) row
        self._quiet = False
        self.itemSelectionChanged.connect(self._on_row_selected)

    # ------------------------------------------------------------- building
    def set_molecule(self, mol):
        self._mol = mol
        self.rebuild()

    def rebuild(self):
        self.clear()
        self._rows = {}
        mol = self._mol
        if mol is None or not mol.atoms:
            return
        root_row = QTreeWidgetItem([mol.label or mol.name, "", "", ""])
        font = root_row.font(0)
        font.setBold(True)
        root_row.setFont(0, font)
        root_row.setToolTip(0, f"{mol.formula()} — {len(mol.atoms)} atoms, "
                               f"{len(mol.bonds)} bonds")
        self.addTopLevelItem(root_row)

        for atom, parent, grand, order, ring in walk(mol.atoms, mol.bonds):
            under = root_row if parent is None else self._rows.get(parent,
                                                                   root_row)
            row = self._make_row(atom, parent, grand, order, ring)
            under.addChild(row)
            if not ring:
                self._rows[atom] = row
        root_row.setExpanded(True)
        self.expandAll()

    def _make_row(self, atom, parent, grand, order, ring):
        mol = self._mol
        el = mol.atoms[atom][0]
        label = f"{el}{atom}" + ("" if ring else f"  {elements.name(el)}")
        if ring:
            label = f"↻ closes ring to {el}{atom}"
        row = QTreeWidgetItem([label, "", "", ""])
        row.setIcon(0, icons.element_icon(elements.color(el)))
        if parent is not None:
            row.setText(1, _ORDER_DASH[order])
            row.setText(2, f"{model.distance(mol.atoms, parent, atom):.2f} Å")
            if grand is not None:
                deg = model.angle(mol.atoms, grand, parent, atom)
                row.setText(3, f"{deg:.1f}°")
        for col in (1, 2, 3):
            row.setTextAlignment(col, Qt.AlignRight | Qt.AlignVCenter)
        if ring:
            row.setData(0, _RING_ROLE, True)
            row.setForeground(0, Qt.gray)
        row.setData(0, _ATOM_ROLE, atom)
        row.setToolTip(0, self._tip(atom, parent, order))
        return row

    def _tip(self, atom, parent, order):
        mol = self._mol
        el, x, y, z = mol.atoms[atom]
        free = model.free_valence(mol.atoms, mol.bonds, atom)
        lines = [f"<b>{elements.name(el)}</b> ({el}), atom {atom}",
                 f"Z = {elements.number(el)}, "
                 f"{elements.weight(el):.3f} g/mol",
                 f"Valence {elements.valence(el)} — {free} free",
                 f"x {x:.3f}, y {y:.3f}, z {z:.3f} Å"]
        if parent is not None:
            pel = mol.atoms[parent][0]
            ideal = elements.bond_length(pel, el, order)
            actual = model.distance(mol.atoms, parent, atom)
            lines.append(
                f"{_ORDER_NAME[order]} bond {pel}{_ORDER_DASH[order]}{el}: "
                f"{actual:.3f} Å (ideal {ideal:.2f} Å)")
        return "<br>".join(lines)

    # ------------------------------------------------------------ selection
    def _on_row_selected(self):
        if self._quiet:
            return
        rows = self.selectedItems()
        if not rows:
            return
        atom = rows[0].data(0, _ATOM_ROLE)
        if atom is not None:
            self.atom_selected.emit(int(atom))

    def show_atom(self, index):
        """Highlight the row for atom *index* (driven by the 3D viewer)."""
        row = self._rows.get(index)
        self._quiet = True
        try:
            self.clearSelection()
            if row is not None:
                self.setCurrentItem(row)
                self.scrollToItem(row)
        finally:
            self._quiet = False
