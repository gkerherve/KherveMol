"""Interactive 3D ball-and-stick viewer / builder.

A `Viewer3D` shows a `model.Molecule` as a depth-sorted ball-and-stick
model and lets you:

* **orbit** by dragging the background (azimuth / elevation);
* **zoom** with the mouse wheel;
* snap to standard views with the cube toolbar;
* **spread** the bonds with the length slider;
* **build**: click an atom to select it, then click an element in the
  palette to bond a new atom on (valence-checked), drag an atom to bend
  a bond, or delete the selected atom.

Crystals are fixed lattices — rotatable and zoomable but not atom-editable.

Copyright (C) 2026 Gwilherm Kerherve

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
"""

import math

from PyQt5.QtCore import QEvent, QRectF, QSize, Qt, pyqtSignal
from PyQt5.QtGui import QColor, QPainter, QPen
from PyQt5.QtWidgets import (QComboBox, QGraphicsEllipseItem, QGraphicsScene,
                             QGraphicsView, QHBoxLayout, QLabel, QPushButton,
                             QSlider, QToolButton, QVBoxLayout, QWidget)

from . import elements, icons, model, render

_HALF = math.pi / 2.0
_W = 400.0                               # preview model-box size (scene units)
STANDARD_VIEWS = [
    ("Front", 0.0, 0.0), ("Back", math.pi, 0.0),
    ("Left", -_HALF, 0.0), ("Right", _HALF, 0.0),
    ("Top", 0.0, _HALF), ("Bottom", 0.0, -_HALF),
    ("Isometric", model.DEFAULT_AZ, model.DEFAULT_EL),
]


_SEL_COLOR = "#159c74"                   # the primary (last-clicked) atom
_CO_SEL_COLOR = "#7fbf3f"                # other Ctrl-selected atoms


class _View(QGraphicsView):
    """Renders the model. Drag empty space to orbit; drag a sphere to move
    that atom; click a sphere to select it (Ctrl+click to add it to the
    selection); Tab steps through the atoms; wheel to zoom."""

    atom_clicked = pyqtSignal(int, bool)    # atom index (-1 = empty), toggle?
    rotated = pyqtSignal()
    atom_moved = pyqtSignal()

    def __init__(self, owner, parent=None):
        super().__init__(parent)
        self._o = owner
        self.setScene(QGraphicsScene(self))
        self.setRenderHint(QPainter.Antialiasing)
        self.setBackgroundBrush(QColor("#ffffff"))
        self.setMinimumSize(360, 320)
        self.setFrameShape(QGraphicsView.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setFocusPolicy(Qt.StrongFocus)     # so Tab reaches keyPressEvent
        self._press = None
        self._press_atom = None
        self._mode = None               # None | "orbit" | "drag"
        self._frozen = None
        self._zoom = 1.0

    def rebuild(self):
        o = self._o
        scene = self.scene()
        scene.clear()
        specs = o.render_specs(_W, _W, frozen=self._frozen)
        sel_items = {}
        for spec in specs:
            item = render.spec_to_item(spec)
            if item is None:
                continue
            scene.addItem(item)
            if "_atom" in spec:
                item.setData(0, spec["_atom"])
                if spec["_atom"] in o.selection:
                    sel_items[spec["_atom"]] = item
            elif "_bond" in spec:
                item.setData(1, spec["_bond"])
        for idx, item in sel_items.items():
            primary = idx == o.selected
            r = item.sceneBoundingRect().adjusted(-3, -3, 3, 3)
            ring = QGraphicsEllipseItem(r)
            ring.setPen(QPen(QColor(_SEL_COLOR if primary else _CO_SEL_COLOR),
                             3 if primary else 2))
            scene.addItem(ring)
        if self._frozen is None:
            src = scene.itemsBoundingRect().adjusted(-10, -10, 10, 10)
            if src.isEmpty():
                src = QRectF(0, 0, _W, _W)
            scene.setSceneRect(src)
            self._apply_fit()

    def _apply_fit(self):
        src = self.scene().sceneRect()
        if src.isEmpty():
            return
        self.fitInView(src, Qt.KeepAspectRatio)
        if self._zoom != 1.0:
            self.scale(self._zoom, self._zoom)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._apply_fit()

    def wheelEvent(self, event):
        factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
        self._zoom = max(0.2, min(8.0, self._zoom * factor))
        self.scale(factor, factor)
        event.accept()

    def _atom_at(self, pos):
        for item in self.items(pos):
            data = item.data(0)
            if data is not None:
                return int(data)
        return None

    def _bond_at(self, pos):
        for item in self.items(pos):
            if item.data(0) is not None:
                return None                 # an atom sits on top of the stick
            data = item.data(1)
            if data is not None:
                return int(data)
        return None

    def contextMenuEvent(self, event):
        """Note what was right-clicked (atom, bond or background), then let
        the window build the matching menu."""
        o = self._o
        atom = self._atom_at(event.pos())
        if atom is not None:
            o.hit = ("atom", atom)
            # Right-clicking an already-selected atom keeps the rest of the
            # selection (so "bond to the other selected atom" stays on the
            # menu); right-clicking a fresh one selects just it.
            o.make_primary(atom) if atom in o.selection else o.select_atom(atom)
        else:
            bond = self._bond_at(event.pos())
            o.hit = ("bond", bond) if bond is not None else (None, -1)
        o.context.emit(event.globalPos())

    def event(self, e):
        """Tab normally moves focus out of the view — claim it instead, so it
        can step the selection from atom to atom."""
        if e.type() == QEvent.KeyPress and e.key() in (Qt.Key_Tab,
                                                       Qt.Key_Backtab):
            back = (e.key() == Qt.Key_Backtab
                    or e.modifiers() & Qt.ShiftModifier)
            self._o.step_selection(-1 if back else 1)
            return True
        return super().event(e)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self._o.cancel_pick()
        else:
            super().keyPressEvent(event)

    def mousePressEvent(self, event):
        if event.button() != Qt.LeftButton:
            return
        self.setFocus(Qt.MouseFocusReason)
        self._press = event.pos()
        self._press_atom = self._atom_at(event.pos())
        self._mode = None

    def mouseMoveEvent(self, event):
        if self._press is None:
            return
        delta = event.pos() - self._press
        o = self._o
        if self._mode is None:
            if abs(delta.x()) + abs(delta.y()) < 4:
                return
            if self._press_atom is not None and o.editable:
                self._mode = "drag"
                self._frozen = model.fit_params(
                    o.mol.atoms, o.mol.bonds, _W, _W, o.mol.az, o.mol.el,
                    o.mol.bond, o.mol.rscale)
            else:
                self._mode = "orbit"
        self._press = event.pos()
        if self._mode == "orbit":
            o.mol.az = (o.mol.az + delta.x() * 0.012) % (2 * math.pi)
            o.mol.el = max(-_HALF, min(_HALF, o.mol.el - delta.y() * 0.012))
            self.rebuild()
            self.rotated.emit()
        else:
            d = self.mapToScene(event.pos()) - self.mapToScene(
                event.pos() - delta)
            model.drag_atom(o.mol.atoms, self._press_atom, d.x(), d.y(),
                            o.mol.az, o.mol.el, o.mol.bond,
                            self._frozen["scale"],
                            bonds=o.mol.bonds if o.lock_lengths else None)
            self.rebuild()
            o.show_geometry(self._press_atom)

    def mouseReleaseEvent(self, event):
        if self._mode == "drag":
            self._frozen = None
            self.rebuild()
            self.atom_moved.emit()
        elif self._mode is None and self._press is not None:
            index = self._press_atom if self._press_atom is not None else -1
            toggle = bool(event.modifiers() & Qt.ControlModifier)
            self.atom_clicked.emit(index, toggle)
        self._press = None
        self._mode = None

    def reset_zoom(self):
        self._zoom = 1.0
        self._apply_fit()


class Viewer3D(QWidget):
    """3D ball-and-stick viewer / builder for one `model.Molecule`."""

    structure_changed = pyqtSignal()        # atoms/bonds edited
    view_changed = pyqtSignal()             # orientation/bond-length changed
    context = pyqtSignal(object)            # global QPoint of a right-click
    selection_changed = pyqtSignal()        # the selected atom(s) changed
    molecule_changed = pyqtSignal()         # a different structure was loaded

    def __init__(self, parent=None):
        super().__init__(parent)
        self.mol = model.Molecule(name="empty")
        #: Ordered atom indices; the last one is the "primary" selection.
        #: Ctrl+click adds to it, Tab steps it, two atoms can be bonded.
        self.selection = []
        self.order = 1
        self.hit = (None, -1)           # what the last right-click landed on
        self._pick = None               # (anchor, order) while picking on screen

        self.view = _View(self)
        self.view.atom_clicked.connect(self._on_atom_clicked)
        self.view.atom_moved.connect(self._on_atom_moved)
        self.view.rotated.connect(self.view_changed)

        root = QVBoxLayout(self)
        root.setContentsMargins(4, 4, 4, 4)
        root.addLayout(self._view_toolbar())
        root.addWidget(self.view, 1)

        self.status = QLabel("")
        self.status.setStyleSheet("color:#666; padding:2px 4px;")
        root.addWidget(self.status)

        root.addLayout(self._bond_row())
        root.addLayout(self._palette_row())

    # ------------------------------------------------------------------ UI
    def _view_toolbar(self):
        row = QHBoxLayout()
        row.addWidget(QLabel("View:"))
        for title, vaz, vel in STANDARD_VIEWS:
            btn = QToolButton()
            btn.setIcon(icons.view_cube_icon(title.lower()))
            btn.setIconSize(QSize(24, 24))
            btn.setText(title)
            btn.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
            btn.setAutoRaise(True)
            btn.setToolTip(f"View from {title.lower()}")
            btn.clicked.connect(
                lambda _=False, a=vaz, e=vel: self._set_view(a, e))
            row.addWidget(btn)
        row.addStretch(1)
        reset = QToolButton()
        reset.setText("Reset zoom")
        reset.setAutoRaise(True)
        reset.clicked.connect(self.view.reset_zoom)
        row.addWidget(reset)
        return row

    def _bond_row(self):
        row = QHBoxLayout()
        self._bond_label = QLabel("Bond length:")
        row.addWidget(self._bond_label)
        self.bond_slider = QSlider(Qt.Horizontal)
        self.bond_slider.setRange(80, 300)          # 0.8 .. 3.0
        self.bond_slider.valueChanged.connect(self._on_bond)
        row.addWidget(self.bond_slider, 1)
        self.labels_btn = QToolButton()
        self.labels_btn.setText("Labels")
        self.labels_btn.setCheckable(True)
        self.labels_btn.toggled.connect(lambda _=False: self.view.rebuild())
        row.addWidget(self.labels_btn)
        self.lock_btn = QToolButton()
        self.lock_btn.setText("Lock lengths")
        self.lock_btn.setCheckable(True)
        self.lock_btn.setChecked(True)
        self.lock_btn.setToolTip(
            "Hold every bond at its real length (C–O 1.43 Å, C=O 1.23 Å …) "
            "while you drag an atom — the bond swings instead of stretching")
        row.addWidget(self.lock_btn)
        return row

    @property
    def lock_lengths(self):
        return self.lock_btn.isChecked()

    def _palette_row(self):
        row = QHBoxLayout()
        row.addWidget(QLabel("Add atom:"))
        self._palette_btns = []
        for el in elements.PALETTE:
            btn = QPushButton(el)
            btn.setFixedWidth(32)
            color = elements.color(el)
            btn.setStyleSheet(f"background:{color}; color:{elements.text_color(el)}; "
                              "font-weight:bold; border:1px solid #888;")
            btn.setToolTip(f"Bond a {elements.name(el)} atom onto the "
                           "selected atom")
            btn.clicked.connect(lambda _=False, e=el: self.add_element(e))
            row.addWidget(btn)
            self._palette_btns.append(btn)
        # "add the active periodic-table element" — the whole table, not just
        # the 10 quick buttons (the active element is set in the table dock).
        self.add_active_btn = QPushButton("＋C")
        self.add_active_btn.setFixedWidth(40)
        self.add_active_btn.clicked.connect(self.add_active)
        row.addWidget(self.add_active_btn)
        self.set_active_element("C")
        row.addSpacing(8)
        row.addWidget(QLabel("Bond:"))
        self.order_combo = QComboBox()
        self.order_combo.addItems(["single", "double", "triple"])
        self.order_combo.currentIndexChanged.connect(
            lambda i: setattr(self, "order", i + 1))
        row.addWidget(self.order_combo)
        # Bond two atoms that already exist: Ctrl+click both, then this.
        self.join_btn = QPushButton("Bond selected")
        self.join_btn.setToolTip(
            "Bond the two selected atoms (Ctrl+click a second atom, or Tab "
            "to step the selection)")
        self.join_btn.clicked.connect(lambda: self.bond_selected(self.order))
        row.addWidget(self.join_btn)
        self.del_btn = QPushButton("Delete atom")
        self.del_btn.clicked.connect(self.delete_selected)
        row.addWidget(self.del_btn)
        row.addStretch(1)
        return row

    # ------------------------------------------------------------- molecule
    def set_molecule(self, mol):
        self.mol = mol
        self.selected = None
        self.view._zoom = 1.0
        self.bond_slider.blockSignals(True)
        self.bond_slider.setValue(int(self.mol.bond * 100))
        self.bond_slider.blockSignals(False)
        editable = self.editable
        for w in (self._bond_label, self.bond_slider):
            w.setEnabled(True)
        for btn in self._palette_btns:
            btn.setEnabled(editable)
        self.add_active_btn.setEnabled(editable)
        self.order_combo.setEnabled(editable)
        self.join_btn.setEnabled(editable)
        self.del_btn.setEnabled(editable)
        self._update_status()
        self.view.rebuild()
        self.molecule_changed.emit()
        self.selection_changed.emit()

    def set_active_element(self, el):
        """Set the element the ＋ button / right-click 'Add' adds (driven by
        the periodic-table dock), so any element can be built, not just the
        10 quick buttons."""
        self.active_element = el
        color = elements.color(el)
        self.add_active_btn.setText(f"＋{el}")
        self.add_active_btn.setStyleSheet(
            f"background:{color}; color:{elements.text_color(el)}; "
            "font-weight:bold; border:1px solid #666;")
        self.add_active_btn.setToolTip(
            f"Bond a {elements.name(el)} atom onto the selected atom")

    def add_active(self):
        self.add_element(self.active_element)

    @property
    def editable(self):
        return not self.mol.crystal

    def render_specs(self, w, h, frozen=None):
        return self.mol.specs(w, h, tag_atoms=self.editable, frozen=frozen,
                              labels=self.labels_btn.isChecked())

    def export_specs(self, w=1200, h=1000):
        """Untagged specs for PNG export at the current orientation."""
        return self.mol.specs(w, h, labels=self.labels_btn.isChecked())

    # -------------------------------------------------------------- actions
    def _set_view(self, az, el):
        self.mol.az, self.mol.el = az, el
        self.view.rebuild()
        self.view_changed.emit()

    def _on_bond(self, value):
        self.mol.bond = value / 100.0
        self.view.rebuild()
        self.view_changed.emit()

    # ------------------------------------------------------------- selection
    @property
    def selected(self):
        """The primary selected atom (the last one clicked), or None."""
        return self.selection[-1] if self.selection else None

    @selected.setter
    def selected(self, index):
        self.selection = [] if index is None else [int(index)]

    def _on_atom_clicked(self, index, toggle=False):
        if index >= 0 and self._pick is not None:
            anchor, order = self._pick
            self.cancel_pick()
            self.bond_atoms(anchor, index, order)
            return
        if index < 0:
            self.cancel_pick()
            self.selection = []
        elif not toggle:
            self.selection = [index]
        elif index in self.selection:               # Ctrl+click again → drop
            self.selection.remove(index)
        else:
            self.selection.append(index)
        self._update_status()
        self.view.rebuild()
        self.selection_changed.emit()

    def select_atom(self, index, toggle=False):
        self._on_atom_clicked(-1 if index is None else index, toggle)

    def make_primary(self, index):
        """Move an already-selected atom to the end (the primary slot)."""
        if index not in self.selection:
            return
        self.selection.remove(index)
        self.selection.append(index)
        self._update_status()
        self.view.rebuild()
        self.selection_changed.emit()

    def step_selection(self, delta):
        """Tab / Shift+Tab: walk the primary selection through the atoms."""
        if not self.mol.atoms:
            return
        n = len(self.mol.atoms)
        start = self.selected
        nxt = 0 if start is None else (start + delta) % n
        self.selection = [nxt]
        self._update_status()
        self.view.rebuild()
        self.selection_changed.emit()

    # ------------------------------------------------- bond two chosen atoms
    def can_bond_selected(self, order=1):
        return (self.editable and len(self.selection) >= 2
                and model.can_bond(self.mol.atoms, self.mol.bonds,
                                   self.selection[-2], self.selection[-1],
                                   order))

    def bond_selected(self, order=1):
        """Join the last two selected atoms — the Ctrl+click path."""
        if len(self.selection) < 2:
            return
        self.bond_atoms(self.selection[-2], self.selection[-1], order)

    def bond_atoms(self, i, j, order=1):
        """Bond two existing atoms, reporting why not if it can't be done."""
        if not self.editable:
            return
        if not model.add_bond(self.mol.atoms, self.mol.bonds, i, j, order):
            self.status.setText(self._why_not(i, j, order))
            return
        self.selection = [j]
        self.view.rebuild()
        self._update_status()
        self.structure_changed.emit()
        self.selection_changed.emit()

    def _why_not(self, i, j, order):
        atoms = self.mol.atoms
        if i == j:
            return "Pick two different atoms to bond."
        if model.bond_between(self.mol.bonds, i, j) is not None:
            return (f"{atoms[i][0]} and {atoms[j][0]} are already bonded — "
                    "right-click the bond to change its order.")
        short = [f"{atoms[k][0]} (atom {k})" for k in (i, j)
                 if model.free_valence(atoms, self.mol.bonds, k) < order]
        return (f"No free valence on {' and '.join(short)} — delete an atom "
                "from it first.")

    def start_pick(self, anchor, order=1):
        """Enter 'click the other atom' mode, bonding it to *anchor*."""
        if not self.editable:
            return
        self._pick = (anchor, order)
        self.view.setCursor(Qt.CrossCursor)
        kind = {1: "bond", 2: "double bond", 3: "triple bond"}[order]
        self.status.setText(
            f"Click the atom to {kind} to {self.mol.atoms[anchor][0]} "
            f"(atom {anchor}) — Esc to cancel.")

    def cancel_pick(self):
        if self._pick is None:
            return
        self._pick = None
        self.view.unsetCursor()
        self._update_status()

    @property
    def picking(self):
        return self._pick is not None

    def _on_atom_moved(self):
        self._update_status()
        self.structure_changed.emit()

    def show_geometry(self, index):
        """Report the dragged atom's bond lengths live in the status line."""
        parts = []
        for bi, (i, j, order) in enumerate(self.mol.bonds):
            if index not in (i, j):
                continue
            k = j if i == index else i
            dash = {1: "–", 2: "=", 3: "≡"}[order]
            d = model.distance(self.mol.atoms, i, j)
            parts.append(f"{self.mol.atoms[index][0]}{dash}"
                         f"{self.mol.atoms[k][0]} {d:.2f} Å")
        if not parts:
            return
        held = " (locked)" if self.lock_lengths else ""
        self.status.setText("   ".join(parts) + held)

    # ------------------------------------------------------------ bond edits
    def bond_label(self, bond_index):
        """``C=O 1.23 Å`` for the bond at *bond_index*."""
        i, j, order = self.mol.bonds[bond_index]
        dash = {1: "–", 2: "=", 3: "≡"}[order]
        d = model.distance(self.mol.atoms, i, j)
        return (f"{self.mol.atoms[i][0]}{dash}{self.mol.atoms[j][0]} "
                f"{d:.2f} Å")

    def can_set_order(self, bond_index, order):
        return model.can_set_bond_order(self.mol.atoms, self.mol.bonds,
                                        bond_index, order)

    def set_bond_order(self, bond_index, order):
        """Make a bond single / double / triple, re-lengthening it to match."""
        if not self.editable or bond_index >= len(self.mol.bonds):
            return
        if not model.set_bond_order(self.mol.atoms, self.mol.bonds,
                                    bond_index, order):
            self.status.setText(
                "Cannot make that bond "
                f"{('single', 'double', 'triple')[order - 1]} — one of its "
                "atoms has no free valence.")
            return
        self.view.rebuild()
        self._update_status()
        self.structure_changed.emit()

    def delete_bond(self, bond_index):
        if not self.editable or bond_index >= len(self.mol.bonds):
            return
        model.delete_bond(self.mol.bonds, bond_index)
        self.view.rebuild()
        self._update_status()
        self.structure_changed.emit()

    def bond_element(self, anchor, element, order=1):
        """Bond an *element* onto atom *anchor* (used by the right-click
        'Bond on' submenu, which offers the obvious elements)."""
        self.selected = anchor
        previous, self.order = self.order, order
        try:
            self.add_element(element)
        finally:
            self.order = previous

    def bondable(self, anchor, order=1):
        """Elements that can actually bond onto *anchor* right now."""
        if not self.editable or anchor is None:
            return []
        free = model.free_valence(self.mol.atoms, self.mol.bonds, anchor)
        if free < order:
            return []
        return [el for el in elements.PALETTE if elements.valence(el) >= order]

    def add_element(self, element):
        if not self.editable:
            return
        anchor = self.selected if self.selected is not None else \
            (len(self.mol.atoms) - 1 if self.mol.atoms else None)
        placed_free = False
        if anchor is None:
            self.mol.atoms.append([element, 0.0, 0.0, 0.0])
            self.selected = 0
        else:
            free = model.free_valence(self.mol.atoms, self.mol.bonds, anchor)
            can_bond = (free >= self.order
                        and elements.valence(element) >= self.order)
            if can_bond:
                self.selected = model.add_bonded_atom(
                    self.mol.atoms, self.mol.bonds, anchor, element, self.order)
            else:
                # Any element can still be added — as a free (unbonded) atom.
                # Covers noble gases and adding onto an already-full atom, so
                # the whole periodic table is usable.
                self.selected = self._place_free(element)
                placed_free = True
        self._update_status()
        if placed_free:
            self.status.setText(
                f"Placed a free {element} atom (no room to bond it to the "
                "selection — drag it, or select another atom to bond).")
        self.view.rebuild()
        self.structure_changed.emit()

    def _place_free(self, element):
        """Append an unbonded atom offset from the model, so it's visible."""
        atoms = self.mol.atoms
        if atoms:
            n = len(atoms)
            cx = sum(a[1] for a in atoms) / n + 3.0
            cy = sum(a[2] for a in atoms) / n
            cz = sum(a[3] for a in atoms) / n
            atoms.append([element, cx, cy, cz])
        else:
            atoms.append([element, 0.0, 0.0, 0.0])
        return len(atoms) - 1

    def delete_selected(self):
        if not self.editable or self.selected is None \
                or len(self.mol.atoms) <= 1:
            return
        model.delete_atom(self.mol.atoms, self.mol.bonds, self.selected)
        self.selected = None            # the other indices have shifted
        self._update_status()
        self.view.rebuild()
        self.structure_changed.emit()
        self.selection_changed.emit()

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Delete, Qt.Key_Backspace):
            self.delete_selected()
        elif event.key() == Qt.Key_Escape:
            self.cancel_pick()
        else:
            super().keyPressEvent(event)

    def _update_status(self):
        formula = self.mol.formula()
        head = f"{self.mol.label}   [{formula}]" if formula else self.mol.label
        if hasattr(self, "join_btn"):
            self.join_btn.setEnabled(self.can_bond_selected(self.order))
        if not self.editable:
            self.status.setText(f"{head} — drag to rotate, wheel to zoom "
                                "(fixed lattice).")
            return
        if len(self.selection) >= 2:
            i, j = self.selection[-2], self.selection[-1]
            a, b = self.mol.atoms[i][0], self.mol.atoms[j][0]
            n = len(self.selection)
            extra = f" ({n} atoms selected)" if n > 2 else ""
            if self.can_bond_selected(self.order):
                d = model.distance(self.mol.atoms, i, j)
                self.status.setText(
                    f"{head} — {a} (atom {i}) + {b} (atom {j}){extra}: "
                    f"{d:.2f} Å apart. Bond selected to join them.")
            else:
                self.status.setText(f"{head} — {self._why_not(i, j, self.order)}")
            return
        if self.selected is not None and self.selected < len(self.mol.atoms):
            el = self.mol.atoms[self.selected][0]
            free = model.free_valence(self.mol.atoms, self.mol.bonds,
                                      self.selected)
            total = elements.valence(el)
            avail = (f"{free} of {total} bonds free — click an element to add"
                     if free > 0 else f"full ({total} bonds)")
            self.status.setText(f"{head} — selected {el} (atom "
                                f"{self.selected}): {avail}. Ctrl+click "
                                "another atom to bond the two.")
        else:
            self.status.setText(f"{head} — click an atom to select (Tab steps "
                                "through them), drag it to bend, drag "
                                "background to rotate.")
