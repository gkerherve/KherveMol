"""MainWindow shell: tabs (3D view / 2D sketch), library, menus, files.

Copyright (C) 2026 Gwilherm Kerherve

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
"""

import os

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (QAction, QActionGroup, QApplication, QDockWidget,
                             QFileDialog, QInputDialog, QMainWindow,
                             QMessageBox, QScrollArea, QTabWidget, QTreeWidget,
                             QTreeWidgetItem)

from . import (__version__, document, help as help_mod, icons, library, model,
               periodic, rdkit_io, style)
from .ai_assistant import AiDock
from .editor2d import Editor2D
from .explorer import MoleculeExplorer
from .viewer3d import Viewer3D


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowIcon(icons.app_icon())
        self._path = None

        self.tabs = QTabWidget()
        self.viewer = Viewer3D()
        self.sketch = Editor2D()
        self.tabs.addTab(self.viewer, "3D View")
        self.tabs.addTab(self.sketch, "2D Sketch")
        self.setCentralWidget(self.tabs)

        self.viewer.structure_changed.connect(self._on_changed)
        self.viewer.structure_changed.connect(self._sync_sketch)
        self.viewer.view_changed.connect(self._on_changed)
        self.sketch.changed.connect(self._on_changed)

        self._build_dock()
        self._build_ai_dock()
        self._build_menus()
        self._build_toolbar()
        self.statusBar().showMessage("Ready")

        self.viewer.set_molecule(library.make("ethanol"))
        self._sync_sketch()
        self._retitle()
        self.resize(1160, 780)

    # --------------------------------------------------------------- docks
    def _build_dock(self):
        # Left: the molecule / crystal library tree.
        lib_dock = QDockWidget("Library", self)
        lib_dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        for title, keys in library.CATEGORIES:
            parent = QTreeWidgetItem([title])
            font = parent.font(0)
            font.setBold(True)
            parent.setFont(0, font)
            self.tree.addTopLevelItem(parent)
            for key in keys:
                child = QTreeWidgetItem([library.label(key)])
                child.setData(0, Qt.UserRole, key)
                child.setIcon(0, icons.element_icon(_key_color(key)))
                parent.addChild(child)
            parent.setExpanded(True)
        self.tree.itemActivated.connect(self._tree_load)
        self.tree.itemDoubleClicked.connect(self._tree_load)
        lib_dock.setWidget(self.tree)
        self.addDockWidget(Qt.LeftDockWidgetArea, lib_dock)
        self._library_dock = lib_dock

        # Bottom: the full periodic table (scrolls if the window is narrow).
        pt_dock = QDockWidget("Periodic table", self)
        pt_dock.setAllowedAreas(Qt.BottomDockWidgetArea | Qt.TopDockWidgetArea)
        self.picker = periodic.PeriodicPicker()
        self.picker.picked.connect(self._on_element_picked)
        scroll = QScrollArea()
        scroll.setWidget(self.picker)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setFrameShape(QScrollArea.NoFrame)
        pt_dock.setWidget(scroll)
        self.addDockWidget(Qt.BottomDockWidgetArea, pt_dock)
        self._ptable_dock = pt_dock

    def _build_ai_dock(self):
        self.ai_dock = AiDock(self)
        self.addDockWidget(Qt.RightDockWidgetArea, self.ai_dock)
        self.ai_dock.hide()             # opened on demand from View / toolbar

    # --------------------------------------------------------------- menus
    def _build_menus(self):
        mb = self.menuBar()

        m_file = mb.addMenu("&File")
        self._act(m_file, "New", self.new_document, "Ctrl+N", "mdi.file-outline")
        self._act(m_file, "Open…", self.open_dialog, "Ctrl+O", "mdi.folder-open")
        m_file.addSeparator()
        self._act(m_file, "Save", self.save, "Ctrl+S", "mdi.content-save")
        self._act(m_file, "Save As…", self.save_as, "Ctrl+Shift+S")
        m_file.addSeparator()
        self._act(m_file, "Export PNG…", self.export_png, "Ctrl+E", "mdi.image")
        m_file.addSeparator()
        self._act(m_file, "Exit", self.close, "Ctrl+Q")

        m_mol = mb.addMenu("&Molecule")
        smi = "" if rdkit_io.available() else "  (needs RDKit)"
        self._act(m_mol, "Explorer…", self.open_explorer, "Ctrl+L",
                  "mdi.magnify")
        self._act(m_mol, "From SMILES…" + smi, self.from_smiles,
                  "Ctrl+Shift+M", "mdi.molecule")
        self._act(m_mol, "Import structure file…" + smi, self.import_file)
        self._act(m_mol, "Copy SMILES of structure" + smi, self.copy_smiles)
        m_mol.addSeparator()
        for title, keys in library.CATEGORIES:
            if title == "Crystal structures":
                continue
            sub = m_mol.addMenu(title)
            for key in keys:
                act = QAction(library.label(key), self)
                act.triggered.connect(lambda _=False, k=key: self.load_model(k))
                sub.addAction(act)

        m_xtal = mb.addMenu("&Crystal")
        for _title, keys in library.CATEGORIES:
            if _title != "Crystal structures":
                continue
            for key in keys:
                act = QAction(library.label(key), self)
                act.triggered.connect(lambda _=False, k=key: self.load_model(k))
                m_xtal.addAction(act)

        m_struct = mb.addMenu("&Structure")
        self._act(m_struct, "Flatten 3D → 2D sketch", self.flatten_to_2d)
        self._act(m_struct, "Clear 2D sketch", self.sketch.clear)

        m_view = mb.addMenu("&View")
        theme_menu = m_view.addMenu("Theme")
        group = QActionGroup(self)
        for name in style.THEMES:
            act = QAction(name, self, checkable=True)
            act.setChecked(name == style.current_theme())
            act.triggered.connect(lambda _=False, n=name: self._set_theme(n))
            group.addAction(act)
            theme_menu.addAction(act)
        m_view.addSeparator()
        self._act(m_view, "Show 3D View", lambda: self.tabs.setCurrentIndex(0))
        self._act(m_view, "Show 2D Sketch", lambda: self.tabs.setCurrentIndex(1))
        m_view.addSeparator()
        m_view.addAction(self._library_dock.toggleViewAction())
        m_view.addAction(self._ptable_dock.toggleViewAction())
        ai_toggle = self.ai_dock.toggleViewAction()
        ai_toggle.setText("AI Chat")
        m_view.addAction(ai_toggle)

        m_help = mb.addMenu("&Help")
        self._act(m_help, "User Guide", self.show_guide, "F1")
        self._act(m_help, "About KherveMol", self.show_about)

    def _act(self, menu, text, slot, shortcut=None, icon_name=None):
        act = QAction(text, self)
        if icon_name:
            act.setIcon(icons.icon(icon_name))
        if shortcut:
            act.setShortcut(shortcut)
        act.triggered.connect(slot)
        menu.addAction(act)
        return act

    def _build_toolbar(self):
        tb = self.addToolBar("Main")
        tb.setMovable(False)
        self._tb_act(tb, "New", self.new_document, "mdi.file-outline")
        self._tb_act(tb, "Open", self.open_dialog, "mdi.folder-open")
        self._tb_act(tb, "Save", self.save, "mdi.content-save")
        self._tb_act(tb, "Export", self.export_png, "mdi.image")
        tb.addSeparator()
        self._tb_act(tb, "Explorer", self.open_explorer, "mdi.magnify")
        self._tb_act(tb, "Benzene", lambda: self.load_model("benzene"),
                     "mdi.hexagon-outline")
        self._tb_act(tb, "Water", lambda: self.load_model("water"),
                     "mdi.water")
        self._tb_act(tb, "Diamond", lambda: self.load_model("diamond"),
                     "mdi.diamond-stone")
        tb.addSeparator()
        ai_toggle = self.ai_dock.toggleViewAction()
        ai_toggle.setIcon(icons.icon("mdi.robot-outline"))
        ai_toggle.setToolTip("AI Chat — ask chemistry questions, draw molecules")
        tb.addAction(ai_toggle)
        self._tb_act(tb, "Guide", self.show_guide, "mdi.help-circle-outline")

    def _tb_act(self, tb, text, slot, icon_name):
        act = QAction(icons.icon(icon_name), text, self)
        act.setToolTip(text)
        act.triggered.connect(slot)
        tb.addAction(act)
        return act

    # ------------------------------------------------------------- actions
    def _tree_load(self, item, _col=0):
        key = item.data(0, Qt.UserRole)
        if key:
            self.load_model(key)

    def load_model(self, key):
        self.viewer.set_molecule(library.make(key))
        self._sync_sketch()
        self.tabs.setCurrentIndex(0)
        self._retitle()
        self.statusBar().showMessage(f"Loaded {library.label(key)}")

    def _sync_sketch(self):
        """Mirror the current 3D molecule into the 2D sketch, projected at
        the model's orientation, so the two tabs show the same structure."""
        mol = self.viewer.mol
        if not mol.atoms:
            self.sketch.clear()
            return
        proj = [model._proj(a[1], a[2], a[3], mol.az, mol.el)
                for a in mol.atoms]
        s = 46.0
        atoms2d = [[mol.atoms[i][0], proj[i][0] * s, proj[i][1] * s]
                   for i in range(len(mol.atoms))]
        bonds2d = [[i, j, o] for i, j, o in mol.bonds]
        self.sketch.set_structure(atoms2d, bonds2d)

    def _on_element_picked(self, el):
        self.sketch.element = el
        idx = self.sketch.el_combo.findText(el)
        if idx >= 0:
            self.sketch.el_combo.setCurrentIndex(idx)

    def flatten_to_2d(self):
        if not self.viewer.mol.atoms:
            return
        self._sync_sketch()
        self.tabs.setCurrentIndex(1)
        self.statusBar().showMessage("Flattened 3D model into the 2D sketch "
                                     "(re-run to match the current rotation)")

    def _set_theme(self, name):
        style.apply_style(QApplication.instance(), name)

    # ---------------------------------------------------------- RDKit bridge
    def _need_rdkit(self):
        if rdkit_io.available():
            return True
        QMessageBox.information(
            self, "RDKit required",
            "This feature uses RDKit for SMILES parsing and structure "
            "import.\n\nInstall it with:\n\n    pip install rdkit\n\n"
            "then restart KherveMol.")
        return False

    def open_explorer(self):
        dlg = MoleculeExplorer(self)
        if dlg.exec_() != MoleculeExplorer.Accepted:
            return
        choice = dlg.result()
        if not choice:
            return
        kind, value, name = choice
        if kind == "model":
            self.load_model(value)
        else:
            self.build_smiles(value, name)

    def from_smiles(self):
        if not self._need_rdkit():
            return
        text, ok = QInputDialog.getText(
            self, "Build from SMILES",
            "Enter a SMILES string (e.g. CCO, c1ccccc1, CC(=O)O):")
        if not ok or not text.strip():
            return
        self.build_smiles(text.strip())

    def build_smiles(self, smiles, label=None):
        """Build *smiles* into the 3D viewer and 2D sketch (needs RDKit)."""
        if not self._need_rdkit():
            return
        try:
            mol = rdkit_io.molecule_from_smiles(smiles, label=label)
            self.viewer.set_molecule(mol)
            self._sync_sketch()
            self.tabs.setCurrentIndex(0)
            self._retitle()
            shown = label or smiles
            self.statusBar().showMessage(f"Built {shown} with RDKit "
                                         f"({mol.formula()})")
        except Exception as exc:                    # noqa: BLE001
            QMessageBox.warning(self, "SMILES failed", str(exc))

    def import_file(self):
        if not self._need_rdkit():
            return
        path, _ = QFileDialog.getOpenFileName(
            self, "Import structure", "",
            "Chemical files (*.mol *.sdf *.pdb);;All files (*)")
        if not path:
            return
        try:
            mol = rdkit_io.molecule_from_file(path)
            self.viewer.set_molecule(mol)
            self.tabs.setCurrentIndex(0)
            self._retitle()
            self.statusBar().showMessage(f"Imported {os.path.basename(path)} "
                                         f"({mol.formula()})")
        except Exception as exc:                    # noqa: BLE001
            QMessageBox.warning(self, "Import failed", str(exc))

    def copy_smiles(self):
        if not self._need_rdkit():
            return
        mol = self.viewer.mol
        smiles = rdkit_io.smiles_from_structure(mol.atoms, mol.bonds)
        if not smiles:
            QMessageBox.information(
                self, "No SMILES",
                "RDKit could not derive a valid SMILES from this structure "
                "(it may be a crystal lattice or chemically incomplete).")
            return
        QApplication.clipboard().setText(smiles)
        self.statusBar().showMessage(f"Copied SMILES: {smiles}")

    # -------------------------------------------------------------- files
    def new_document(self):
        self._path = None
        self.viewer.set_molecule(model.Molecule(atoms=[["C", 0.0, 0.0, 0.0]],
                                                name="custom", label="New molecule"))
        self._sync_sketch()
        self._retitle()

    def open_dialog(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open molecule", "", "KherveMol files (*.kmol);;All files (*)")
        if path:
            self.open_path(path)

    def open_path(self, path):
        try:
            mol, sk_atoms, sk_bonds = document.load(path)
        except Exception as exc:                       # noqa: BLE001
            QMessageBox.warning(self, "Open failed", str(exc))
            return
        self.viewer.set_molecule(mol)
        self.sketch.set_structure(sk_atoms, sk_bonds)
        self._path = path
        self._retitle()
        self.statusBar().showMessage(f"Opened {os.path.basename(path)}")

    def save(self):
        if self._path:
            self._write(self._path)
        else:
            self.save_as()

    def save_as(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Save molecule", "molecule.kmol",
            "KherveMol files (*.kmol)")
        if path:
            if not path.lower().endswith(".kmol"):
                path += ".kmol"
            self._write(path)
            self._path = path
            self._retitle()

    def _write(self, path):
        try:
            document.save(path, self.viewer.mol, self.sketch.atoms,
                          self.sketch.bonds)
        except Exception as exc:                       # noqa: BLE001
            QMessageBox.warning(self, "Save failed", str(exc))
            return
        self.statusBar().showMessage(f"Saved {os.path.basename(path)}")

    def export_png(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Export PNG", "molecule.png", "PNG image (*.png)")
        if not path:
            return
        if not path.lower().endswith(".png"):
            path += ".png"
        if self.tabs.currentIndex() == 0:
            document.export_png(path, self.viewer.export_specs(1200, 1000),
                                1200, 1000)
        else:
            self.sketch.image(1200, 1000).save(path, "PNG")
        self.statusBar().showMessage(f"Exported {os.path.basename(path)}")

    # -------------------------------------------------------------- helpers
    def show_guide(self):
        help_mod.GuideDialog(self).exec_()

    def show_about(self):
        help_mod.AboutDialog(self).exec_()

    def _on_changed(self):
        self._retitle()

    def _retitle(self):
        name = os.path.basename(self._path) if self._path else "Untitled"
        formula = self.viewer.mol.formula()
        extra = f" — {formula}" if formula else ""
        self.setWindowTitle(f"KherveMol v{__version__} — {name}{extra}")


def _key_color(key):
    """A representative element colour for a library entry's tree icon."""
    from . import elements
    if library.is_crystal(key):
        return "#9aa0a6"
    return elements.color("C")
