"""2D structure sketcher — draw a flat skeletal/graph formula.

A lightweight molecular-graph editor: atoms are 2D points, bonds are
index pairs with an order. Tools:

* **Draw**   — press on an atom and drag to another (bond them) or to
  empty space (spawn a new atom of the active element, bonded); click
  empty space to drop a lone atom.
* **Move**   — drag atoms around.
* **Atom**   — click to set an atom's element to the active one.
* **Erase**  — click an atom (removes it + its bonds) or a bond.

Bond order cycles single → double → triple by clicking an existing bond
with the Draw tool. It renders as a proper **skeletal formula**: thin bond
lines (double/triple as parallels), carbons as implicit vertices and
heteroatoms as CPK-coloured element labels; hydrogens are implicit unless
"All labels" is on. Right-click for a context menu (Build 3D from sketch,
tools, export…).

Copyright (C) 2026 Gwilherm Kerherve

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
"""

import math

from PyQt5.QtCore import QLineF, QPointF, QRectF, Qt, pyqtSignal
from PyQt5.QtGui import QColor, QFont, QPainter, QPen
from PyQt5.QtWidgets import (QButtonGroup, QComboBox, QGraphicsScene,
                             QGraphicsView, QHBoxLayout, QLabel, QPushButton,
                             QToolButton, QVBoxLayout, QWidget)

from . import elements

_HIT = 15.0             # px pick radius for atoms
_BOND_LEN = 46.0        # default new-bond length
_BOND_LW = 2.3          # skeletal bond line width
_MULTI_GAP = 4.5        # perpendicular offset between double/triple lines
_LABEL_R = 10.0         # halo radius behind a drawn atom label


class _Canvas(QGraphicsView):
    changed = pyqtSignal()
    picked = pyqtSignal(str)      # status text

    def __init__(self, owner, parent=None):
        super().__init__(parent)
        self._o = owner
        self.setScene(QGraphicsScene(self))
        self.scene().setSceneRect(-2000, -2000, 4000, 4000)
        self.setRenderHint(QPainter.Antialiasing)
        self.setBackgroundBrush(QColor("#ffffff"))
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setDragMode(QGraphicsView.NoDrag)
        self._press = None
        self._drag_from = None
        self._moving = None
        self._preview = None
        self.redraw()

    # ----------------------------------------------------------- geometry
    def _atom_at(self, sp):
        best, bd = None, _HIT
        for i, a in enumerate(self._o.atoms):
            d = math.hypot(a[1] - sp.x(), a[2] - sp.y())
            if d < bd:
                best, bd = i, d
        return best

    def _bond_at(self, sp):
        best, bd = None, 8.0
        for bi, (i, j, _o) in enumerate(self._o.bonds):
            a, b = self._o.atoms[i], self._o.atoms[j]
            d = _point_seg_dist(sp.x(), sp.y(), a[1], a[2], b[1], b[2])
            if d < bd:
                best, bd = bi, d
        return best

    # -------------------------------------------------------------- events
    def contextMenuEvent(self, event):
        self._o.context_requested.emit(event.globalPos())

    def mousePressEvent(self, event):
        if event.button() != Qt.LeftButton:
            return
        sp = self.mapToScene(event.pos())
        tool = self._o.tool
        ai = self._atom_at(sp)
        self._press = sp
        if tool == "move":
            self._moving = ai
        elif tool == "atom":
            if ai is not None:
                self._o.atoms[ai][0] = self._o.element
            else:
                self._o.atoms.append([self._o.element, sp.x(), sp.y()])
            self.redraw()
            self.changed.emit()
        elif tool == "erase":
            self._erase_at(sp, ai)
        elif tool == "draw":
            self._drag_from = ai if ai is not None else self._new_atom(sp)

    def mouseMoveEvent(self, event):
        sp = self.mapToScene(event.pos())
        if self._moving is not None:
            self._o.atoms[self._moving][1] = sp.x()
            self._o.atoms[self._moving][2] = sp.y()
            self.redraw()
        elif self._drag_from is not None:
            self.redraw()
            a = self._o.atoms[self._drag_from]
            pen = QPen(QColor("#9aa0a6"), 2, Qt.DashLine)
            self._preview = self.scene().addLine(
                QLineF(a[1], a[2], sp.x(), sp.y()), pen)

    def mouseReleaseEvent(self, event):
        sp = self.mapToScene(event.pos())
        if self._moving is not None:
            self._moving = None
            self.changed.emit()
        elif self._drag_from is not None:
            src = self._drag_from
            tgt = self._atom_at(sp)
            moved = self._press is not None and \
                (abs(sp.x() - self._press.x()) + abs(sp.y() - self._press.y())) > 6
            if tgt is None and moved:
                tgt = self._new_atom(sp)
            if tgt is not None and tgt != src:
                self._add_or_cycle_bond(src, tgt)
            elif tgt == src and not moved:
                bi = self._bond_at(sp)
                if bi is not None:
                    self._cycle_order(bi)
            self._drag_from = None
            self.redraw()
            self.changed.emit()
        self._press = None

    def _new_atom(self, sp):
        self._o.atoms.append([self._o.element, sp.x(), sp.y()])
        return len(self._o.atoms) - 1

    def _add_or_cycle_bond(self, i, j):
        for b in self._o.bonds:
            if {b[0], b[1]} == {i, j}:
                b[2] = b[2] % 3 + 1
                return
        self._o.bonds.append([i, j, 1])

    def _cycle_order(self, bi):
        self._o.bonds[bi][2] = self._o.bonds[bi][2] % 3 + 1

    def _erase_at(self, sp, ai):
        if ai is not None:
            self._o.atoms.pop(ai)
            self._o.bonds[:] = [
                [i - (i > ai), j - (j > ai), o]
                for i, j, o in self._o.bonds if ai not in (i, j)]
            self.redraw()
            self.changed.emit()
            return
        bi = self._bond_at(sp)
        if bi is not None:
            self._o.bonds.pop(bi)
            self.redraw()
            self.changed.emit()

    # ------------------------------------------------------------- drawing
    def _degree(self, idx):
        return sum(1 for i, j, _o in self._o.bonds if idx in (i, j))

    def _labeled(self, idx, show_all):
        """Whether atom *idx* is drawn as a text label (vs an implicit
        vertex). Heteroatoms always; carbons/H only if forced or isolated."""
        el = self._o.atoms[idx][0]
        if show_all:
            return True
        if el in ("C", "H"):
            return self._degree(idx) == 0
        return True

    def redraw(self):
        """Draw the graph as a proper 2D skeletal formula: thin bond lines
        (double/triple as parallels), carbons as implicit vertices and
        heteroatoms as CPK-coloured element labels. Hydrogens are hidden
        (skeletal convention) unless 'All labels' is on."""
        sc = self.scene()
        sc.clear()
        self._preview = None
        atoms, bonds = self._o.atoms, self._o.bonds
        show_all = self._o.show_labels

        pen = QPen(QColor("#1b1b1b"), _BOND_LW)
        pen.setCapStyle(Qt.RoundCap)
        for i, j, order in bonds:
            if not show_all and (atoms[i][0] == "H" or atoms[j][0] == "H"):
                continue                       # hide bonds to implicit H
            a, b = atoms[i], atoms[j]
            gi = _LABEL_R + 3 if self._labeled(i, show_all) else 0.0
            gj = _LABEL_R + 3 if self._labeled(j, show_all) else 0.0
            self._draw_bond(a[1], a[2], b[1], b[2], order, gi, gj, pen)

        for idx, (el, x, y) in enumerate(atoms):
            if not show_all and el == "H" and self._degree(idx) > 0:
                continue
            if self._labeled(idx, show_all):
                self._draw_label(el, x, y)

    def _draw_bond(self, x1, y1, x2, y2, order, gi, gj, pen):
        dx, dy = x2 - x1, y2 - y1
        length = math.hypot(dx, dy) or 1.0
        ux, uy = dx / length, dy / length
        px, py = -uy, ux                       # unit perpendicular
        sx, sy = x1 + ux * gi, y1 + uy * gi    # shortened at labelled ends
        ex, ey = x2 - ux * gj, y2 - uy * gj
        offs = {1: [0.0], 2: [-1.0, 1.0], 3: [-1.0, 0.0, 1.0]}.get(order, [0.0])
        for o in offs:
            ox, oy = px * o * _MULTI_GAP, py * o * _MULTI_GAP
            sc = self.scene()
            sc.addLine(QLineF(sx + ox, sy + oy, ex + ox, ey + oy), pen)

    def _draw_label(self, el, x, y):
        sc = self.scene()
        color = QColor(elements.color(el))
        # opaque halo so bond lines don't run through the letter
        halo = sc.addEllipse(QRectF(x - _LABEL_R, y - _LABEL_R,
                                    2 * _LABEL_R, 2 * _LABEL_R),
                             QPen(Qt.NoPen), QColor("#ffffff"))
        halo.setZValue(5)
        txt = sc.addSimpleText(el)
        txt.setFont(QFont("Segoe UI", 12, QFont.Bold))
        ink = color if color.lightnessF() < 0.75 else color.darker(160)
        txt.setBrush(ink)
        br = txt.boundingRect()
        txt.setPos(x - br.width() / 2.0, y - br.height() / 2.0)
        txt.setZValue(6)

    def wheelEvent(self, event):
        factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
        self.scale(factor, factor)
        event.accept()


def _point_seg_dist(px, py, x1, y1, x2, y2):
    dx, dy = x2 - x1, y2 - y1
    if dx == 0 and dy == 0:
        return math.hypot(px - x1, py - y1)
    t = max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)))
    return math.hypot(px - (x1 + t * dx), py - (y1 + t * dy))


class Editor2D(QWidget):
    """2D structure sketcher widget."""

    changed = pyqtSignal()
    context_requested = pyqtSignal(object)      # global QPoint of right-click

    def __init__(self, parent=None):
        super().__init__(parent)
        self.atoms = []             # [element, x, y]
        self.bonds = []             # [i, j, order]
        self.tool = "draw"
        self.element = "C"
        self.show_labels = False

        root = QVBoxLayout(self)
        root.setContentsMargins(4, 4, 4, 4)
        root.addLayout(self._toolbar())
        self.canvas = _Canvas(self)
        self.canvas.changed.connect(self._on_changed)
        root.addWidget(self.canvas, 1)
        self.status = QLabel("Draw: drag from an atom to bond; click empty "
                             "to place. Click a bond to cycle its order.")
        self.status.setStyleSheet("color:#666; padding:2px 4px;")
        root.addWidget(self.status)

    def _toolbar(self):
        row = QHBoxLayout()
        self._tool_group = QButtonGroup(self)
        for key, text in (("draw", "Draw"), ("move", "Move"),
                          ("atom", "Atom"), ("erase", "Erase")):
            btn = QToolButton()
            btn.setText(text)
            btn.setCheckable(True)
            btn.setAutoRaise(True)
            btn.setToolButtonStyle(Qt.ToolButtonTextOnly)
            if key == "draw":
                btn.setChecked(True)
            btn.clicked.connect(lambda _=False, k=key: setattr(self, "tool", k))
            self._tool_group.addButton(btn)
            row.addWidget(btn)
        row.addSpacing(10)
        row.addWidget(QLabel("Element:"))
        self.el_combo = QComboBox()
        for el in elements.PALETTE:
            self.el_combo.addItem(icons_element(el), el)
        self.el_combo.currentTextChanged.connect(
            lambda t: setattr(self, "element", t))
        row.addWidget(self.el_combo)
        self.labels_btn = QToolButton()
        self.labels_btn.setText("All labels")
        self.labels_btn.setCheckable(True)
        self.labels_btn.toggled.connect(self._toggle_labels)
        row.addWidget(self.labels_btn)
        clear = QPushButton("Clear")
        clear.clicked.connect(self.clear)
        row.addWidget(clear)
        row.addStretch(1)
        return row

    def set_tool(self, key):
        """Set the active tool and sync the toolbar button state."""
        self.tool = key
        for btn in self._tool_group.buttons():
            btn.setChecked(btn.text().lower() == key)

    def _toggle_labels(self, on):
        self.show_labels = on
        self.canvas.redraw()

    def _on_changed(self):
        self.status.setText(f"{len(self.atoms)} atoms, {len(self.bonds)} "
                            f"bonds   [{self.formula()}]")
        self.changed.emit()

    def clear(self):
        self.atoms = []
        self.bonds = []
        self.canvas.redraw()
        self._on_changed()

    def set_structure(self, atoms, bonds):
        """Load a 2D graph: atoms [[el,x,y],...], bonds [[i,j,order],...]."""
        self.atoms = [list(a) for a in atoms]
        self.bonds = [list(b) for b in bonds]
        self.canvas.redraw()
        self._on_changed()

    def image(self, w=1200, h=1000, background="#ffffff"):
        """Rasterise the sketch scene to a QImage for PNG export."""
        from PyQt5.QtCore import QRectF
        from PyQt5.QtGui import QImage, QPainter
        sc = self.canvas.scene()
        box = sc.itemsBoundingRect()
        if box.isEmpty():
            box = QRectF(0, 0, 1, 1)
        img = QImage(w, h, QImage.Format_ARGB32)
        img.fill(QColor(background))
        p = QPainter(img)
        p.setRenderHint(QPainter.Antialiasing)
        sc.render(p, QRectF(24, 24, w - 48, h - 48), box, Qt.KeepAspectRatio)
        p.end()
        return img

    def formula(self):
        counts = {}
        for a in self.atoms:
            counts[a[0]] = counts.get(a[0], 0) + 1
        order = []
        if "C" in counts:
            order.append("C")
        if "H" in counts:
            order.append("H")
        order += sorted(e for e in counts if e not in ("C", "H"))
        out = ""
        for e in order:
            n = counts[e]
            out += e + (str(n) if n > 1 else "")
        return out


def icons_element(el):
    from . import icons
    return icons.element_icon(elements.color(el))
