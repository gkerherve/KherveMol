"""Molecule Explorer — a searchable browser of structures to build.

Instead of typing SMILES blind, open the Explorer (Molecule ▸ Explorer…)
and pick a compound by name from a categorised, searchable tree: the
built-in 3D models plus ~120 named compounds (solvents, drugs, amino
acids, sugars, aromatics, nucleobases, functional groups…). The right
pane previews the selected structure; **Build** loads it into the 3D view
(and 2D sketch). Named compounds are built via RDKit; the built-in models
work with or without it.

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

from . import catalog, library, rdkit_io, render


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
    where kind is ``"model"`` (value = library key) or ``"smiles"``."""

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
        self.search.setPlaceholderText("Search compounds…  (name or formula)")
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

        if not rdkit_io.available():
            note = QLabel("⚠ Install RDKit (pip install rdkit) to preview and "
                          "build the named compounds. The built-in 3D models "
                          "work without it.")
            note.setWordWrap(True)
            note.setStyleSheet("color:#a06000;")
            root.addWidget(note)

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
        # Built-in models (always buildable)
        top = QTreeWidgetItem(["Built-in 3D models"])
        self._bold(top)
        self.tree.addTopLevelItem(top)
        for title, keys in library.CATEGORIES:
            grp = QTreeWidgetItem([title])
            top.addChild(grp)
            for key in keys:
                it = QTreeWidgetItem([library.label(key)])
                it.setData(0, Qt.UserRole, ("model", key, library.label(key)))
                grp.addChild(it)
        top.setExpanded(True)

        # Named catalog (SMILES)
        cat_top = QTreeWidgetItem(["Named compounds"])
        self._bold(cat_top)
        self.tree.addTopLevelItem(cat_top)
        for cat, entries in catalog.grouped():
            grp = QTreeWidgetItem([cat])
            cat_top.addChild(grp)
            for name, smi in entries:
                it = QTreeWidgetItem([name])
                it.setData(0, Qt.UserRole, ("smiles", smi, name))
                it.setToolTip(0, smi)
                grp.addChild(it)
        cat_top.setExpanded(True)

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
        self.build_btn.setEnabled(data is not None
                                  and (data[0] == "model"
                                       or rdkit_io.available()))
        if data is None:
            self.preview.show_text("")
            self.info.setText("Select a compound to preview it.")
            return
        kind, value, name = data
        try:
            if kind == "model":
                mol = library.make(value)
                self.preview.show_specs(mol.specs(300, 260))
                self.info.setText(
                    f"<b>{name}</b> &nbsp; [{mol.formula()}]<br>"
                    "Built-in 3D model — works without RDKit.")
            else:
                if rdkit_io.available():
                    atoms, bonds = rdkit_io.sketch_from_smiles(value)
                    self.preview.show_specs(
                        render.specs_from_graph2d(atoms, bonds))
                    self.info.setText(f"<b>{name}</b><br>"
                                      f"SMILES: <code>{value}</code>")
                else:
                    self.preview.show_text("Install RDKit to preview")
                    self.info.setText(f"<b>{name}</b><br>"
                                      f"SMILES: <code>{value}</code>")
        except Exception as exc:                        # noqa: BLE001
            self.preview.show_text("Preview unavailable")
            self.info.setText(f"<b>{name}</b><br>SMILES: <code>{value}</code>"
                              f"<br><span style='color:#b00'>{exc}</span>")

    def _on_double(self, item, _col=0):
        if item.data(0, Qt.UserRole) is not None:
            self._build()

    def _build(self):
        if self._choice is None:
            return
        if self._choice[0] == "smiles" and not rdkit_io.available():
            return
        self.accept()

    def result(self):
        """``(kind, value, name)`` of the chosen entry, or None."""
        return self._choice
