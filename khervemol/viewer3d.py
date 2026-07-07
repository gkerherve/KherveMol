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

from PyQt5.QtCore import QRectF, QSize, Qt, pyqtSignal
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


class _View(QGraphicsView):
    """Renders the model. Drag empty space to orbit; drag a sphere to move
    that atom; click a sphere to select it; wheel to zoom."""

    atom_clicked = pyqtSignal(int)          # atom index, or -1 for empty
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
        sel_item = None
        for spec in specs:
            item = render.spec_to_item(spec)
            if item is None:
                continue
            scene.addItem(item)
            if "_atom" in spec:
                item.setData(0, spec["_atom"])
                if spec["_atom"] == o.selected:
                    sel_item = item
        if sel_item is not None:
            r = sel_item.sceneBoundingRect().adjusted(-3, -3, 3, 3)
            ring = QGraphicsEllipseItem(r)
            ring.setPen(QPen(QColor("#159c74"), 3))
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

    def mousePressEvent(self, event):
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
                            self._frozen["scale"])
            self.rebuild()

    def mouseReleaseEvent(self, event):
        if self._mode == "drag":
            self._frozen = None
            self.rebuild()
            self.atom_moved.emit()
        elif self._mode is None and self._press is not None:
            self.atom_clicked.emit(self._press_atom if self._press_atom
                                   is not None else -1)
        self._press = None
        self._mode = None

    def reset_zoom(self):
        self._zoom = 1.0
        self._apply_fit()


class Viewer3D(QWidget):
    """3D ball-and-stick viewer / builder for one `model.Molecule`."""

    structure_changed = pyqtSignal()        # atoms/bonds edited
    view_changed = pyqtSignal()             # orientation/bond-length changed

    def __init__(self, parent=None):
        super().__init__(parent)
        self.mol = model.Molecule(name="empty")
        self.selected = None
        self.order = 1

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
        return row

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
        row.addSpacing(8)
        row.addWidget(QLabel("Bond:"))
        self.order_combo = QComboBox()
        self.order_combo.addItems(["single", "double", "triple"])
        self.order_combo.currentIndexChanged.connect(
            lambda i: setattr(self, "order", i + 1))
        row.addWidget(self.order_combo)
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
        self.order_combo.setEnabled(editable)
        self.del_btn.setEnabled(editable)
        self._update_status()
        self.view.rebuild()

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

    def _on_atom_clicked(self, index):
        self.selected = None if index < 0 else index
        self._update_status()
        self.view.rebuild()

    def _on_atom_moved(self):
        self._update_status()
        self.structure_changed.emit()

    def add_element(self, element):
        if not self.editable:
            return
        anchor = self.selected if self.selected is not None else \
            (len(self.mol.atoms) - 1 if self.mol.atoms else None)
        if anchor is None:
            self.mol.atoms.append([element, 0.0, 0.0, 0.0])
            self.selected = 0
        else:
            free = model.free_valence(self.mol.atoms, self.mol.bonds, anchor)
            if free < self.order:
                el = self.mol.atoms[anchor][0]
                self.status.setText(
                    f"{el} (atom {anchor}) has no room — "
                    f"{elements.valence(el)} bonds max, {free} free.")
                return
            if elements.valence(element) < self.order:
                names = ['', 'single', 'double', 'triple']
                self.status.setText(f"{element} can't take a "
                                    f"{names[self.order]} bond.")
                return
            self.selected = model.add_bonded_atom(
                self.mol.atoms, self.mol.bonds, anchor, element, self.order)
        self._update_status()
        self.view.rebuild()
        self.structure_changed.emit()

    def delete_selected(self):
        if not self.editable or self.selected is None \
                or len(self.mol.atoms) <= 1:
            return
        model.delete_atom(self.mol.atoms, self.mol.bonds, self.selected)
        self.selected = None
        self._update_status()
        self.view.rebuild()
        self.structure_changed.emit()

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Delete, Qt.Key_Backspace):
            self.delete_selected()
        else:
            super().keyPressEvent(event)

    def _update_status(self):
        formula = self.mol.formula()
        head = f"{self.mol.label}   [{formula}]" if formula else self.mol.label
        if not self.editable:
            self.status.setText(f"{head} — drag to rotate, wheel to zoom "
                                "(fixed lattice).")
            return
        if self.selected is not None and self.selected < len(self.mol.atoms):
            el = self.mol.atoms[self.selected][0]
            free = model.free_valence(self.mol.atoms, self.mol.bonds,
                                      self.selected)
            total = elements.valence(el)
            avail = (f"{free} of {total} bonds free — click an element to add"
                     if free > 0 else f"full ({total} bonds)")
            self.status.setText(f"{head} — selected {el} (atom "
                                f"{self.selected}): {avail}.")
        else:
            self.status.setText(f"{head} — click an atom to select, drag it "
                                "to bend, drag background to rotate.")
