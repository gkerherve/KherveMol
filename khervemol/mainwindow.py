"""MainWindow shell: tabs (3D view / 2D sketch), library, menus, files.

Copyright (C) 2026 Gwilherm Kerherve

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
"""

import os

from PyQt5.QtCore import QMimeData, Qt
from PyQt5.QtWidgets import (QAction, QActionGroup, QApplication, QDialog,
                             QDialogButtonBox, QDockWidget, QFileDialog,
                             QHBoxLayout, QInputDialog, QLabel, QMainWindow,
                             QMenu, QMessageBox, QScrollArea, QSpinBox,
                             QTabWidget, QTreeWidget, QTreeWidgetItem,
                             QVBoxLayout)

from . import (__version__, catalog, dnd, document, elements, help as help_mod,
               icons, library, model, periodic, rdkit_io, style, svgexport)
from .ai_assistant import AiDock
from .editor2d import Editor2D
from .explorer import MoleculeExplorer
from .structure_tree import StructureTree
from .viewer3d import Viewer3D


class _LibraryTree(QTreeWidget):
    """Tree whose leaves can be dragged onto either view — the 3D viewer
    merges the compound in as a fragment, the 2D canvas drops it where you
    let go."""

    def mimeData(self, items):
        md = QMimeData()
        for it in items:
            data = it.data(0, Qt.UserRole)
            if data:
                md.setData(dnd.MIME_COMPOUND, dnd.encode(data[0], data[1]))
                break
        return md

    def startDrag(self, actions):
        super().startDrag(Qt.CopyAction)


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

        # The 2D sketch is a real editor: once you edit/drop in it, it goes
        # "dirty" and 3D edits stop overwriting it (until an explicit sync).
        self._sketch_dirty = False
        self._syncing = False
        self.viewer.structure_changed.connect(self._on_changed)
        self.viewer.structure_changed.connect(
            lambda: self._sync_sketch(force=False))
        self.viewer.view_changed.connect(self._on_changed)
        self.viewer.context.connect(self._viewer_menu)
        self.sketch.changed.connect(self._on_sketch_changed)
        self.sketch.context_requested.connect(self._sketch_menu)
        self.sketch.molecule_dropped.connect(self._on_drop_molecule)
        self.viewer.compound_dropped.connect(self._on_drop_compound_3d)

        self._build_dock()
        self._build_ai_dock()
        self._build_menus()
        self._build_toolbar()
        self.statusBar().showMessage("Ready")

        self.viewer.set_molecule(library.make("ethanol"))
        self._sync_sketch(force=True)
        self._retitle()
        self.resize(1160, 780)

    # --------------------------------------------------------------- docks
    def _build_dock(self):
        # Left, top: the current molecule as a connectivity outline.
        struct_dock = QDockWidget("Structure", self)
        struct_dock.setAllowedAreas(Qt.LeftDockWidgetArea
                                    | Qt.RightDockWidgetArea)
        self.structure = StructureTree()
        self.structure.atom_selected.connect(self.viewer.select_atom)
        self.structure.reattach_requested.connect(self._on_reattach)
        self.viewer.molecule_changed.connect(
            lambda: self.structure.set_molecule(self.viewer.mol))
        self.viewer.structure_changed.connect(self.structure.rebuild)
        self.viewer.selection_changed.connect(
            lambda: self.structure.show_atom(self.viewer.selected))
        struct_dock.setWidget(self.structure)
        self.addDockWidget(Qt.LeftDockWidgetArea, struct_dock)
        self._structure_dock = struct_dock

        # Left, below it: the molecule / crystal library tree.
        lib_dock = QDockWidget("Library", self)
        lib_dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        self.tree = _LibraryTree()
        self.tree.setHeaderHidden(True)
        self.tree.setDragEnabled(True)          # drag a compound to the 2D tab
        # Two clear sections. Built-in 3D models (build without RDKit),
        # sub-groups expanded:
        models_top = self._tree_header("Built-in 3D models")
        for title, keys in library.CATEGORIES:
            self._tree_group(models_top, title,
                             [(library.label(k), ("model", k)) for k in keys],
                             True, lambda k: _key_color(k[1]))
        models_top.setExpanded(True)
        # The full named-compound catalog (SMILES), grouped by family — the
        # top node is expanded so all the families show, but each family
        # starts collapsed (there are hundreds of compounds):
        n = len(catalog.all_entries())
        cpd_top = self._tree_header(f"Named compounds — {n}")
        for cat, entries in catalog.grouped():
            self._tree_group(cpd_top, cat,
                             [(name, ("smiles", smi)) for name, smi in entries],
                             False, lambda _v: elements.color("C"))
        cpd_top.setExpanded(True)
        self.tree.itemActivated.connect(self._tree_load)
        self.tree.itemDoubleClicked.connect(self._tree_load)
        lib_dock.setWidget(self.tree)
        self.addDockWidget(Qt.LeftDockWidgetArea, lib_dock)
        self._library_dock = lib_dock
        # Structure on top, library under it — one column, resizable.
        self.splitDockWidget(struct_dock, lib_dock, Qt.Vertical)
        self.resizeDocks([struct_dock, lib_dock], [300, 460], Qt.Vertical)

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

    def _tree_header(self, title):
        """A bold, non-selectable top-level section header in the tree."""
        item = QTreeWidgetItem([title])
        font = item.font(0)
        font.setBold(True)
        font.setPointSizeF(font.pointSizeF() + 1)
        item.setFont(0, font)
        item.setFlags(Qt.ItemIsEnabled)             # header, not a leaf
        self.tree.addTopLevelItem(item)
        return item

    def _tree_group(self, parent, title, entries, expanded, color_fn):
        """Add a bold category (with (label, (kind, value)) leaves) under
        *parent* in the library tree."""
        grp = QTreeWidgetItem([title])
        font = grp.font(0)
        font.setBold(True)
        grp.setFont(0, font)
        parent.addChild(grp)
        for label, data in entries:
            child = QTreeWidgetItem([label])
            child.setData(0, Qt.UserRole, data)
            child.setIcon(0, icons.element_icon(color_fn(data)))
            if data[0] == "smiles":
                child.setToolTip(0, data[1])
            grp.addChild(child)
        grp.setExpanded(expanded)

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
        self._act(m_file, "Export SVG (KhervePaint)…", self.export_svg,
                  "Ctrl+Shift+E", "mdi.vector-square")
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
        self._act(m_mol, "Properties…", self.show_properties, "Ctrl+I",
                  "mdi.information-outline")
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
        for title, keys in library.CATEGORIES:
            if title not in ("Crystal structures", "Lattice systems"):
                continue
            sub = m_xtal.addMenu(title)
            for key in keys:
                act = QAction(library.label(key), self)
                act.triggered.connect(lambda _=False, k=key: self.load_model(k))
                sub.addAction(act)
        m_xtal.addSeparator()
        self._act(m_xtal, "Stack unit cells…", self.stack_cells, "Ctrl+U")
        self._xtal_poly = self._act(m_xtal, "Coordination polyhedra",
                                    self.viewer.poly_btn.toggle)
        self._xtal_poly.setCheckable(True)
        self._xtal_legend = self._act(m_xtal, "Colour legend",
                                      self.viewer.legend_btn.toggle)
        self._xtal_legend.setCheckable(True)
        self._act(m_xtal, "Reset cell tilts", self.viewer.reset_tilts)
        self._act(m_xtal, "Reset colours", self.viewer.reset_colors)
        m_xtal.aboutToShow.connect(self._sync_crystal_menu)

        m_struct = mb.addMenu("&Structure")
        self._act(m_struct, "Flatten 3D → 2D sketch", self.flatten_to_2d)
        self._act(m_struct, "Build 3D from 2D sketch", self.build_3d_from_sketch,
                  "Ctrl+B")
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
        m_view.addAction(self._structure_dock.toggleViewAction())
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
        data = item.data(0, Qt.UserRole)
        if not data:
            return
        kind, value = data
        if kind == "model":
            self.load_model(value)
        else:
            self.build_smiles(value, item.text(0))

    def load_model(self, key):
        self.viewer.set_molecule(library.make(key))
        self._sync_sketch(force=True)
        self.tabs.setCurrentIndex(0)
        self._retitle()
        self.statusBar().showMessage(f"Loaded {library.label(key)}")

    def _sync_sketch(self, force=False):
        """Mirror the current 3D molecule into the 2D sketch as a proper
        skeletal structure. Skipped when the sketch has been edited by hand
        (unless *force*), so multi-molecule work isn't clobbered."""
        if self._sketch_dirty and not force:
            return
        self._syncing = True
        try:
            self._do_sync_sketch()
        finally:
            self._syncing = False
            self._sketch_dirty = False

    def _do_sync_sketch(self):
        mol = self.viewer.mol
        if not mol.atoms:
            self.sketch.clear()
            return
        if not mol.crystal and rdkit_io.available():
            smiles = rdkit_io.smiles_from_structure(mol.atoms, mol.bonds)
            if smiles:
                try:
                    a2, b2 = rdkit_io.sketch_from_smiles(smiles)
                    if a2:
                        self.sketch.set_structure(a2, b2)
                        return
                except Exception:                   # noqa: BLE001
                    pass
        self.sketch.set_structure(*self._flatten_2d(mol))

    def _on_sketch_changed(self):
        if not self._syncing:
            self._sketch_dirty = True
        self._retitle()

    # ------------------------------------------------ drag-and-drop from library
    def _compound_2d(self, kind, value):
        """The 2D graph (atoms [el,x,y], bonds) for a library entry, or
        None (crystal, or SMILES compound without RDKit)."""
        if kind == "model":
            mol = library.make(value)
            if mol.crystal:
                return None
            if rdkit_io.available():
                smi = rdkit_io.smiles_from_structure(mol.atoms, mol.bonds)
                if smi:
                    try:
                        a2, b2 = rdkit_io.sketch_from_smiles(smi)
                        if a2:
                            return a2, b2
                    except Exception:               # noqa: BLE001
                        pass
            return self._flatten_2d(mol)
        if not rdkit_io.available():
            return None
        try:
            a2, b2 = rdkit_io.sketch_from_smiles(value)
            return (a2, b2) if a2 else None
        except Exception:                           # noqa: BLE001
            return None

    def _on_reattach(self, atom, anchor):
        """A row was dragged onto another in the structure tree."""
        parent = self.structure.parent_of(atom)
        if self.viewer.reattach(atom, parent, anchor):
            a = self.viewer.mol.atoms[atom][0]
            b = self.viewer.mol.atoms[anchor][0]
            self.statusBar().showMessage(f"Re-bonded {a}{atom} onto "
                                         f"{b}{anchor}.")
        else:
            self.statusBar().showMessage(self.viewer.status.text())

    def _compound_3d(self, kind, value):
        """The 3D `Molecule` for a library entry, or None (SMILES compound
        without RDKit)."""
        if kind == "model":
            return library.make(value)
        if not rdkit_io.available():
            return None
        try:
            return rdkit_io.molecule_from_smiles(value)
        except Exception:                           # noqa: BLE001
            return None

    def _on_drop_compound_3d(self, kind, value):
        mol = self._compound_3d(kind, value)
        if mol is None:
            self.statusBar().showMessage(
                "Install RDKit to build named compounds in 3D.")
            return
        merging = bool(self.viewer.mol.atoms) and not self.viewer.mol.crystal \
            and not mol.crystal
        self.viewer.add_molecule(mol)
        self.statusBar().showMessage(
            f"Added {mol.label} as a second fragment — Ctrl+click an atom in "
            "each and press Bond selected to join them."
            if merging else f"Loaded {mol.label}.")

    def _on_drop_molecule(self, kind, value, x, y):
        result = self._compound_2d(kind, value)
        if result is None:
            self.statusBar().showMessage(
                "Can't place that in 2D (crystal, or install RDKit for "
                "named compounds).")
            return
        self.sketch.add_fragment(result[0], result[1], x, y)
        self.tabs.setCurrentIndex(1)
        self.statusBar().showMessage(
            "Dropped a molecule — Move it, or use Draw to bond it to "
            "another; Erase a bond to split them.")

    def _flatten_2d(self, mol):
        """Project the 3D model to a flat 2D graph (fallback depiction).
        Molecules drop their explicit hydrogens for a skeletal look;
        crystals keep every atom."""
        drop_h = not mol.crystal
        keep = [i for i, a in enumerate(mol.atoms)
                if not (drop_h and a[0] == "H")]
        remap = {old: new for new, old in enumerate(keep)}
        s = 46.0
        atoms2d = []
        for i in keep:
            a = mol.atoms[i]
            px, py, _d = model._proj(a[1], a[2], a[3], mol.az, mol.el)
            atoms2d.append([a[0], px * s, py * s])
        bonds2d = [[remap[i], remap[j], o] for i, j, o in mol.bonds
                   if i in remap and j in remap]
        return atoms2d, bonds2d

    def build_3d_from_sketch(self):
        """Turn the current 2D sketch into a 3D model (needs RDKit)."""
        if not self.sketch.atoms:
            self.statusBar().showMessage("The 2D sketch is empty.")
            return
        if not self._need_rdkit():
            return
        smiles = rdkit_io.smiles_from_structure(self.sketch.atoms,
                                                self.sketch.bonds)
        if not smiles:
            QMessageBox.information(
                self, "Build 3D",
                "Could not read the 2D sketch as a valid molecule. Check "
                "that the atoms and bonds make chemical sense.")
            return
        self.build_smiles(smiles)

    def _on_element_picked(self, el):
        # The periodic-table dock sets the active element for BOTH the 2D
        # sketch and the 3D builder's ＋ button / right-click "Add".
        self.viewer.set_active_element(el)
        self.sketch.element = el
        idx = self.sketch.el_combo.findText(el)
        if idx >= 0:
            self.sketch.el_combo.setCurrentIndex(idx)

    def flatten_to_2d(self):
        if not self.viewer.mol.atoms:
            return
        self._sync_sketch(force=True)
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
            self._sync_sketch(force=True)
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

    # ------------------------------------------------------------- crystal
    def _sync_crystal_menu(self):
        """Keep the Crystal menu's checkmarks and enabled state in step with
        the loaded structure."""
        v = self.viewer
        self._xtal_poly.setChecked(v.poly_btn.isChecked())
        self._xtal_poly.setEnabled(v.poly_btn.isEnabled())
        self._xtal_legend.setChecked(v.legend_btn.isChecked())

    def stack_cells(self):
        """Ask for an nx × ny × nz supercell and tile the crystal into it."""
        v = self.viewer
        if not v.mol.can_stack:
            QMessageBox.information(
                self, "Stack unit cells",
                "Load a stackable crystal first — the cubic family and the "
                "six non-cubic lattice systems tile into a supercell.\n\n"
                "(The HCP model is already drawn as a full hexagonal prism, "
                "so it doesn't repeat on its own cell.)")
            return
        dlg = QDialog(self)
        dlg.setWindowTitle(f"Stack {v.mol.label}")
        root = QVBoxLayout(dlg)
        root.addWidget(QLabel("Repeat the unit cell along each lattice "
                              "vector. Shared corner and face atoms are "
                              "drawn once."))
        row = QHBoxLayout()
        spins = []
        for axis, n in zip("abc", v.mol.cells):
            row.addWidget(QLabel(f"{axis}:"))
            sp = QSpinBox()
            sp.setRange(1, 20)
            sp.setValue(n)
            spins.append(sp)
            row.addWidget(sp)
        row.addStretch(1)
        root.addLayout(row)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok
                                   | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)
        root.addWidget(buttons)
        if dlg.exec_() == QDialog.Accepted:
            v.set_cells(*(sp.value() for sp in spins))

    def show_properties(self):
        from .properties import PropertiesDialog
        PropertiesDialog(self.viewer.mol, self).exec_()

    # ------------------------------------------------------- context menus
    def _bond_section(self, m, bond_index):
        """Right-clicked a stick: set its order, or cut it."""
        v = self.viewer
        head = m.addAction(f"Bond  {v.bond_label(bond_index)}")
        head.setEnabled(False)
        current = v.mol.bonds[bond_index][2]
        for order, label in ((1, "Single"), (2, "Double"), (3, "Triple")):
            act = m.addAction(
                label, lambda _=False, o=order: v.set_bond_order(bond_index, o))
            act.setCheckable(True)
            act.setChecked(order == current)
            act.setEnabled(v.can_set_order(bond_index, order))
        m.addSeparator()
        m.addAction("Delete bond", lambda: v.delete_bond(bond_index))

    def _atom_section(self, m, atom_index):
        """Right-clicked a sphere: bond an element onto it, join it to another
        atom already on screen, or delete it."""
        v = self.viewer
        el = v.mol.atoms[atom_index][0]
        free = model.free_valence(v.mol.atoms, v.mol.bonds, atom_index)
        head = m.addAction(f"Atom  {el} ({elements.name(el)}) — "
                           f"{free} free of {elements.valence(el)}")
        head.setEnabled(False)
        for order, label in ((1, "Bond on"), (2, "Double-bond on"),
                             (3, "Triple-bond on")):
            options = v.bondable(atom_index, order)
            if not options:
                continue
            sub = m.addMenu(label)
            for sym in options:
                sub.addAction(
                    f"{sym} — {elements.name(sym)}",
                    lambda _=False, s=sym, o=order: v.bond_element(
                        atom_index, s, o))
            active = v.active_element
            if active not in options and elements.valence(active) >= order:
                sub.addSeparator()
                sub.addAction(
                    f"{active} — {elements.name(active)} (table)",
                    lambda _=False, s=active, o=order: v.bond_element(
                        atom_index, s, o))
            # …or join it to an atom that's already there
            sub.addSeparator()
            sub.addAction(
                "Select an atom on screen…",
                lambda _=False, o=order: v.start_pick(atom_index, o))
        self._join_section(m, atom_index)
        m.addAction("Delete atom", v.delete_selected)

    def _join_section(self, m, atom_index):
        """'Bond to the other selected atom' — the Ctrl+click / Tab path."""
        v = self.viewer
        others = [i for i in v.selection if i != atom_index]
        if not others:
            return
        partner = others[-1]
        a, b = v.mol.atoms[partner][0], v.mol.atoms[atom_index][0]
        sub = m.addMenu(f"Bond to {a}{partner} (also selected)")
        for order, label in ((1, "Single"), (2, "Double"), (3, "Triple")):
            act = sub.addAction(
                label, lambda _=False, o=order: v.bond_atoms(partner,
                                                             atom_index, o))
            act.setEnabled(model.can_bond(v.mol.atoms, v.mol.bonds, partner,
                                          atom_index, order))
        sub.setTitle(f"Bond {a}{partner}–{b}{atom_index}")

    def _viewer_menu(self, gpos):
        from .viewer3d import STANDARD_VIEWS
        m = QMenu(self)
        kind, index = self.viewer.hit
        if self.viewer.editable and kind == "bond":
            self._bond_section(m, index)
            m.addSeparator()
        elif self.viewer.editable and kind == "atom":
            self._atom_section(m, index)
            m.addSeparator()
        views = m.addMenu("View from")
        for title, az, el in STANDARD_VIEWS:
            views.addAction(
                title, lambda _=False, a=az, e=el: self.viewer._set_view(a, e))
        m.addAction("Reset zoom", self.viewer.view.reset_zoom)
        m.addAction("Toggle labels", self.viewer.labels_btn.toggle)
        if not self.viewer.editable:
            self._crystal_section(m, kind, index)
        if self.viewer.editable:
            lock = m.addAction("Lock bond lengths", self.viewer.lock_btn.toggle)
            lock.setCheckable(True)
            lock.setChecked(self.viewer.lock_lengths)
            if kind is None:
                el = self.viewer.active_element
                m.addAction(f"Add {el} ({elements.name(el)}) atom",
                            self.viewer.add_active)
                if len(self.viewer.selection) >= 2:
                    self._join_section(m, self.viewer.selected)
                if self.viewer.selected is not None:
                    m.addAction("Delete selected atom",
                                self.viewer.delete_selected)
        m.addSeparator()
        m.addAction("Properties…", self.show_properties)
        if rdkit_io.available():
            m.addAction("Copy SMILES", self.copy_smiles)
        m.addAction("Flatten to 2D sketch", self.flatten_to_2d)
        m.addAction("Export PNG…", self.export_png)
        m.addAction("Export SVG (KhervePaint)…", self.export_svg)
        m.exec_(gpos)

    def _crystal_section(self, m, kind, index):
        """The lattice actions on a crystal's right-click menu: stacking,
        the tilt of the clicked atom's cell, colours and polyhedra."""
        v = self.viewer
        if v.mol.can_stack:
            m.addAction("Stack unit cells…", self.stack_cells)
        if kind == "atom" and index is not None and index < len(v.mol.atoms):
            v.select_atom(index)
            atom = v.mol.atoms[index]
            m.addSeparator()
            head = m.addAction(f"{atom[0]} ({elements.name(atom[0])})")
            head.setEnabled(False)
            m.addAction("Atom colour…", v.pick_color)
            if v.mol.stacked:
                cell = v.mol.cell_of(index)
                sub = m.addMenu(f"Tilt cell ({cell.replace(',', ', ')})")
                for label, angles in (("15° about x", (15, 0, 0)),
                                      ("15° about y", (0, 15, 0)),
                                      ("15° about z", (0, 0, 15)),
                                      ("Straighten", (0, 0, 0))):
                    sub.addAction(label, lambda _=False, c=cell, a=angles:
                                  v.set_tilt(c, a))
        m.addSeparator()
        poly = m.addAction("Coordination polyhedra", v.poly_btn.toggle)
        poly.setCheckable(True)
        poly.setChecked(v.poly_btn.isChecked())
        poly.setEnabled(v.poly_btn.isEnabled())
        legend = m.addAction("Colour legend", v.legend_btn.toggle)
        legend.setCheckable(True)
        legend.setChecked(v.legend_btn.isChecked())
        m.addAction("Reset colours", v.reset_colors)
        if v.mol.tilts:
            m.addAction("Reset cell tilts", v.reset_tilts)

    def _sketch_menu(self, gpos):
        m = QMenu(self)
        m.addAction("Build 3D from this sketch", self.build_3d_from_sketch)
        m.addAction("Refresh 2D from 3D model", self._sync_sketch)
        m.addSeparator()
        tools = m.addMenu("Tool")
        for key, label in (("draw", "Draw"), ("move", "Move"),
                           ("atom", "Atom"), ("erase", "Erase")):
            act = tools.addAction(
                label, lambda _=False, k=key: self.sketch.set_tool(k))
            act.setCheckable(True)
            act.setChecked(self.sketch.tool == key)
        m.addAction("Toggle all labels", self.sketch.labels_btn.toggle)
        m.addAction("Clear sketch", self.sketch.clear)
        m.addSeparator()
        m.addAction("Export PNG…", self.export_png)
        m.addAction("Export SVG (KhervePaint)…", self.export_svg)
        m.exec_(gpos)

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
        self._sync_sketch(force=True)
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

    def export_svg(self):
        """Write a KhervePaint-compatible SVG of the current tab."""
        path, _ = QFileDialog.getSaveFileName(
            self, "Export SVG (opens in KhervePaint)", "molecule.svg",
            "SVG image (*.svg)")
        if not path:
            return
        if not path.lower().endswith(".svg"):
            path += ".svg"
        if self.tabs.currentIndex() == 0:
            specs = self.viewer.export_specs(1000, 800)
        else:
            specs = svgexport.sketch_specs(self.sketch.atoms,
                                           self.sketch.bonds,
                                           self.sketch.show_labels)
        specs, w, h = svgexport.normalize(specs)
        svgexport.save_specs(path, specs, w, h)
        self.statusBar().showMessage(
            f"Exported {os.path.basename(path)} — open it in KhervePaint")

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
