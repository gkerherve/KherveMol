"""Molecule Explorer — a searchable browser of structures to build.

Open the Explorer (Molecule ▸ Explorer…) and pick a structure by name
from one categorised, searchable tree: ~700 molecules (solvents, drugs,
amino acids, sugars, aromatics, salts, oxides…), 120+ crystals, surfaces
cut along (hkl), graphene / nanotubes / fullerenes, and classic
reactions. The right pane previews the selection in 3D; **Build** loads
it into the 3D view (and 2D sketch). Everything builds without RDKit.

Copyright (C) 2026 Gwilherm Kerherve

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
"""

from PyQt5.QtCore import QRectF, Qt
from PyQt5.QtGui import QColor, QPainter
from PyQt5.QtWidgets import (QDialogButtonBox, QGraphicsScene, QGraphicsView,
                             QDialog, QHBoxLayout, QLabel, QLineEdit,
                             QPushButton, QTreeWidget, QTreeWidgetItem,
                             QVBoxLayout, QWidget)

from . import entries, render


class _Preview(QGraphicsView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setScene(QGraphicsScene(self))
        self.setRenderHint(QPainter.Antialiasing)
        self.setBackgroundBrush(QColor("#ffffff"))
        self.setMinimumSize(300, 260)
        self.setFrameShape(QGraphicsView.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

    def show_specs(self, specs):
        sc = self.scene()
        sc.clear()
        render.add_specs(sc, specs)
        box = sc.itemsBoundingRect()
        if not box.isEmpty():
            sc.setSceneRect(box.adjusted(-12, -12, 12, 12))
            self.fitInView(sc.sceneRect(), Qt.KeepAspectRatio)

    def show_text(self, text):
        sc = self.scene()
        sc.clear()
        item = sc.addText(text)
        item.setDefaultTextColor(QColor("#888"))
        self.setSceneRect(item.boundingRect())
        self.fitInView(item, Qt.KeepAspectRatio)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        r = self.scene().sceneRect()
        if not r.isEmpty():
            self.fitInView(r, Qt.KeepAspectRatio)


class MoleculeExplorer(QDialog):
    """Pick a structure to build. `result()` returns ``(kind, value, name)``
    — an `entries` pair plus its display name."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Molecule Explorer")
        self.setMinimumSize(780, 560)
        self._choice = None

        root = QVBoxLayout(self)
        body = QHBoxLayout()
        root.addLayout(body, 1)

        # ---- left: search + tree ----
        left = QVBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search…  (name, formula or family)")
        self.search.textChanged.connect(self._filter)
        self.search.setClearButtonEnabled(True)
        left.addWidget(self.search)
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.currentItemChanged.connect(self._on_select)
        self.tree.itemDoubleClicked.connect(self._on_double)
        left.addWidget(self.tree, 1)
        lwrap = QWidget()
        lwrap.setLayout(left)
        lwrap.setFixedWidth(320)
        body.addWidget(lwrap)

        # ---- right: preview + info ----
        right = QVBoxLayout()
        self.preview = _Preview()
        right.addWidget(self.preview, 1)
        self.info = QLabel("Select a compound to preview it.")
        self.info.setWordWrap(True)
        self.info.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.info.setStyleSheet("color:#333; padding:4px;")
        self.info.setMinimumHeight(64)
        right.addWidget(self.info)
        body.addLayout(right, 1)

        buttons = QDialogButtonBox()
        self.build_btn = buttons.addButton("Build in 3D",
                                           QDialogButtonBox.AcceptRole)
        buttons.addButton(QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._build)
        buttons.rejected.connect(self.reject)
        self.build_btn.setEnabled(False)
        root.addWidget(buttons)

        self._populate()

    # ------------------------------------------------------------- tree
    def _populate(self):
        for n, (title, groups) in enumerate(entries.sections()):
            top = QTreeWidgetItem([title])
            self._bold(top)
            self.tree.addTopLevelItem(top)
            for group, rows in groups:
                grp = QTreeWidgetItem([group])
                top.addChild(grp)
                for label, (kind, value) in rows:
                    it = QTreeWidgetItem([label])
                    it.setData(0, Qt.UserRole, (kind, value, label))
                    tip = entries.smiles_of(kind, value)
                    if tip:
                        it.setToolTip(0, tip)
                    grp.addChild(it)
            top.setExpanded(n == 0)

    def _bold(self, item):
        f = item.font(0)
        f.setBold(True)
        item.setFont(0, f)

    def _filter(self, text):
        text = text.strip().lower()

        def walk(item):
            data = item.data(0, Qt.UserRole)
            if data is not None:                       # leaf
                match = (not text or text in item.text(0).lower()
                         or text in str(data[1]).lower())
                item.setHidden(not match)
                return match
            any_child = False
            for i in range(item.childCount()):
                any_child = walk(item.child(i)) or any_child
            item.setHidden(not any_child)
            if text and any_child:
                item.setExpanded(True)
            return any_child

        for i in range(self.tree.topLevelItemCount()):
            walk(self.tree.topLevelItem(i))

    # ---------------------------------------------------------- preview
    def _on_select(self, current, _prev):
        data = current.data(0, Qt.UserRole) if current else None
        self._choice = data
        self.build_btn.setEnabled(data is not None)
        if data is None:
            self.preview.show_text("")
            self.info.setText("Select a structure to preview it.")
            return
        kind, value, name = data
        try:
            mol = entries.build(kind, value, name)
            self.preview.show_specs(mol.specs(300, 260))
            extra = ""
            smi = entries.smiles_of(kind, value)
            if smi:
                extra = f"<br>SMILES: <code>{smi}</code>"
            elif kind == "reaction":
                extra = f"<br><code>{value}</code>"
            formula = mol.formula() if not mol.notes else ""
            head = f" &nbsp; [{formula}]" if formula else ""
            self.info.setText(f"<b>{name}</b>{head}<br>"
                              f"{len(mol.atoms)} atoms, "
                              f"{len(mol.bonds)} bonds{extra}")
        except Exception as exc:                        # noqa: BLE001
            self.preview.show_text("Preview unavailable")
            self.info.setText(f"<b>{name}</b><br>"
                              f"<span style='color:#b00'>{exc}</span>")

    def _on_double(self, item, _col=0):
        if item.data(0, Qt.UserRole) is not None:
            self._build()

    def _build(self):
        if self._choice is None:
            return
        self.accept()

    def result(self):
        """``(kind, value, name)`` of the chosen entry, or None."""
        return self._choice
