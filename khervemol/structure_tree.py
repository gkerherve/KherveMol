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

from PyQt5.QtCore import QMimeData, Qt, pyqtSignal
from PyQt5.QtWidgets import QAbstractItemView, QTreeWidget, QTreeWidgetItem

from . import dnd, elements, icons, model

_ORDER_DASH = {1: "–", 2: "=", 3: "≡"}
_ORDER_NAME = {1: "single", 2: "double", 3: "triple"}
_ATOM_ROLE = Qt.UserRole                # the atom index a row stands for
_RING_ROLE = Qt.UserRole + 1            # True on a ring-closure leaf


def _heavy_adjacency(atoms, bonds):
    adj = {i: [] for i, a in enumerate(atoms) if a[0] != "H"}
    for i, j, _o in bonds:
        if i in adj and j in adj:
            adj[i].append(j)
            adj[j].append(i)
    return adj


def _farthest(adj, start):
    """BFS: the most distant atom from *start* (lowest index on a tie)."""
    seen = {start: 0}
    queue = [start]
    while queue:
        cur = queue.pop(0)
        for k in adj[cur]:
            if k not in seen:
                seen[k] = seen[cur] + 1
                queue.append(k)
    return max(sorted(seen), key=lambda i: seen[i])


def _root_atom(atoms, bonds):
    """Root the tree at one end of the molecule's longest chain.

    Taking an endpoint of the heavy-atom "diameter" means an unbranched
    molecule is walked straight through, end to end — so it renders as a
    list, not a staircase. Falls back to the best-connected heavy atom when
    there are no heavy bonds at all (methane, water)."""
    if not atoms:
        return None
    adj = _heavy_adjacency(atoms, bonds)
    if not adj:
        return 0
    seed = max(sorted(adj), key=lambda i: len(adj[i]))
    return _farthest(adj, _farthest(adj, seed))


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


def _continuations(atoms, rows):
    """Pick, for each atom, the child that carries on its chain.

    That child renders at the *same* indent as its parent, so a backbone runs
    straight down the panel; everything else (hydrogens, side groups, ring
    closures) nests underneath. The chain follows the heaviest branch — the
    child with the biggest subtree — so a phenyl never steals the backbone."""
    children = {}
    for atom, parent, _g, _o, ring in rows:
        if not ring and parent is not None:
            children.setdefault(parent, []).append(atom)
    size = {}
    for atom, _p, _g, _o, ring in reversed(rows):        # children come first
        if not ring:
            size[atom] = 1 + sum(size[c] for c in children.get(atom, ()))
    out = {}
    for parent, kids in children.items():
        heavy = [k for k in kids if atoms[k][0] != "H"]
        if heavy:
            out[parent] = max(heavy, key=lambda k: (size[k], -k))
    return out


class StructureTree(QTreeWidget):
    """Live connectivity outline of one molecule, with per-bond geometry."""

    atom_selected = pyqtSignal(int)
    reattach_requested = pyqtSignal(int, int)   # move atom → onto anchor

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setColumnCount(4)
        self.setHeaderLabels(["Atom", "Bond", "Length", "Angle"])
        self.setRootIsDecorated(True)
        self.setAlternatingRowColors(True)
        self.setUniformRowHeights(True)
        self.setIndentation(14)         # chains stay readable in a narrow dock
        self.header().setStretchLastSection(False)
        self.setColumnWidth(0, 140)
        for col, width in ((1, 44), (2, 62), (3, 60)):
            self.setColumnWidth(col, width)
        # Drag an atom onto another to re-bond it (with everything hanging
        # off it). Qt must never move rows itself — the molecule decides.
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDragDropMode(QAbstractItemView.DragDrop)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self._mol = None
        self._rows = {}                 # atom index → its (non-ring) row
        self._parent = {}               # atom index → its tree parent
        self._quiet = False
        self.itemSelectionChanged.connect(self._on_row_selected)

    # ----------------------------------------------------------- drag & drop
    def _atom_of(self, item):
        if item is None or item.data(0, _RING_ROLE):
            return None
        atom = item.data(0, _ATOM_ROLE)
        return None if atom is None else int(atom)

    def parent_of(self, atom):
        """The atom this one hangs off in the outline (None at a root)."""
        return self._parent.get(atom)

    def mimeData(self, items):
        md = QMimeData()
        atom = self._atom_of(items[0]) if items else None
        if atom is not None:
            md.setData(dnd.MIME_ATOM, str(atom).encode("ascii"))
        return md

    def startDrag(self, actions):
        super().startDrag(Qt.CopyAction)     # never let Qt delete the row

    def can_drop(self, source, target):
        """Whether dragging atom *source* onto *target* would re-bond it.

        Checked while the drag is still moving, so an impossible drop shows a
        "no" cursor instead of failing on release: the target must be a real
        atom outside the fragment that would travel with *source*, and it must
        have the valence to take it."""
        mol = self._mol
        if mol is None or mol.crystal or target is None or source == target:
            return False
        parent = self._parent.get(source)
        old = (None if parent is None
               else model.bond_between(mol.bonds, source, parent))
        return model.can_reattach(mol.atoms, mol.bonds, source, old, target)

    def _drag_atoms(self, event):
        if not event.mimeData().hasFormat(dnd.MIME_ATOM):
            return None, None
        source = int(bytes(event.mimeData().data(dnd.MIME_ATOM)))
        return source, self._atom_of(self.itemAt(event.pos()))

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat(dnd.MIME_ATOM):
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        source, target = self._drag_atoms(event)
        if source is None or not self.can_drop(source, target):
            event.ignore()
            return
        event.acceptProposedAction()

    def dropEvent(self, event):
        source, target = self._drag_atoms(event)
        if source is None or not self.can_drop(source, target):
            return
        event.acceptProposedAction()
        self.reattach_requested.emit(source, target)

    # ------------------------------------------------------------- building
    def set_molecule(self, mol):
        self._mol = mol
        self.rebuild()

    def rebuild(self):
        self.clear()
        self._rows = {}
        self._parent = {}
        mol = self._mol
        if mol is None or not mol.atoms:
            return
        root_row = QTreeWidgetItem([mol.label or mol.name, "", "", ""])
        font = root_row.font(0)
        font.setBold(True)
        root_row.setFont(0, font)
        root_row.setFlags(Qt.ItemIsEnabled)          # not a drag/drop target
        root_row.setToolTip(0, f"{mol.formula()} — {len(mol.atoms)} atoms, "
                               f"{len(mol.bonds)} bonds")
        self.addTopLevelItem(root_row)

        rows = list(walk(mol.atoms, mol.bonds))
        keep_going = _continuations(mol.atoms, rows)
        holder = {}                     # atom → the item its chain hangs under
        for atom, parent, grand, order, ring in rows:
            if ring:
                self._rows.get(parent, root_row).addChild(
                    self._make_row(atom, parent, grand, order, True))
                continue
            self._parent[atom] = parent
            if parent is None:
                under = root_row
            elif keep_going.get(parent) == atom:
                under = holder[parent]      # same chain → same indent level
            else:
                under = self._rows[parent]  # a real branch → nest it
            row = self._make_row(atom, parent, grand, order, False)
            under.addChild(row)
            self._rows[atom] = row
            holder[atom] = under
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
        # An atom may carry a 5th slot (its colour / lattice-site tint), so
        # take the first four rather than unpacking the whole row.
        el, x, y, z = mol.atoms[atom][:4]
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
