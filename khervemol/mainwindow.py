"""MainWindow shell: tabs (3D view / 2D sketch), library, menus, files.

Copyright (C) 2026 Gwilherm Kerherve

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
"""

import os

from PyQt5.QtCore import QMimeData, QSettings, Qt, QTimer
from PyQt5.QtWidgets import (QAction, QActionGroup, QApplication, QDialog,
                             QDialogButtonBox, QDockWidget, QFileDialog,
                             QHBoxLayout, QInputDialog, QLabel, QMainWindow,
                             QMenu, QMessageBox, QSpinBox,
                             QTabWidget, QTreeWidget, QTreeWidgetItem,
                             QVBoxLayout)

from . import (__version__, builders_ui, chem, dnd, document, elements, entries,
               help as help_mod, icons, library, maintools, model, molrepr,
               periodic, rdkit_io, shelf, style, supercell, svgexport)
from .ai_assistant import AiDock
from .crystal import BuildError
from .editor2d import Editor2D
from .shelf_panel import ShelfPanel
from .explorer import MoleculeExplorer
from .structure_tree import StructureTree
from . import viewer3d
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
        if QSettings(*style._SETTINGS).value("renderer", "gl") == "classic":
            self.viewer.set_renderer("classic")
        self.sketch = Editor2D()
        self.tabs.addTab(self.viewer, "3D View")
        self.tabs.addTab(self.sketch, "2D Sketch")
        self.setCentralWidget(self.tabs)

        # The 2D sketch is a real editor: once you edit/drop in it, it goes
        # "dirty" and 3D edits stop overwriting it (until an explicit sync).
        self._sketch_dirty = False
        self._last_drawn = None
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
        self.viewer.periodic_requested.connect(self.show_periodic_table)
        self.viewer.molecule_changed.connect(self._remember_drawn)
        self.viewer.structure_changed.connect(self._remember_drawn)

        self._build_dock()
        self._build_ai_dock()
        self._build_menus()
        self._build_toolbar()
        self.statusBar().showMessage("Ready")

        self.viewer.set_molecule(library.make("ethanol"))
        self._sync_sketch(force=True)
        self._retitle()
        self.resize(1160, 780)
        from . import mcp_dialog
        mcp_dialog.install(self)

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
        # One section per kind of thing — molecules, crystals, surfaces,
        # graphene / nanotubes / fullerenes, reactions, and the classic
        # hand-placed models. Everything builds without RDKit.
        for n, (title, groups) in enumerate(entries.sections()):
            top = self._tree_header(title)
            for group, rows in groups:
                self._tree_group(top, group, rows, False, _entry_color)
            top.setExpanded(n < 6)
        self.tree.itemActivated.connect(self._tree_load)
        self.tree.itemDoubleClicked.connect(self._tree_load)
        lib_dock.setWidget(self.tree)
        self.addDockWidget(Qt.LeftDockWidgetArea, lib_dock)
        self._library_dock = lib_dock
        # Structure on top, library under it — one column, resizable.
        self.splitDockWidget(struct_dock, lib_dock, Qt.Vertical)
        self.resizeDocks([struct_dock, lib_dock], [300, 460], Qt.Vertical)
        self.resizeDocks([struct_dock], [300], Qt.Horizontal)

        # "My molecules": what you built and kept, in a tab beside the Library
        shelf_dock = QDockWidget("My molecules", self)
        shelf_dock.setAllowedAreas(Qt.LeftDockWidgetArea
                                   | Qt.RightDockWidgetArea)
        self.shelf = shelf.default()
        self.shelf_panel = ShelfPanel(self.shelf)
        self.shelf_panel.keep_requested.connect(self.keep_molecule)
        self.shelf_panel.load_requested.connect(self.load_kept)
        self.shelf_panel.rename_requested.connect(self.rename_kept)
        self.shelf_panel.delete_requested.connect(self.delete_kept)
        self.shelf_panel.move_requested.connect(self.move_kept)
        self.shelf_panel.reaction_requested.connect(self.open_reaction_builder)
        shelf_dock.setWidget(self.shelf_panel)
        self.addDockWidget(Qt.LeftDockWidgetArea, shelf_dock)
        self.tabifyDockWidget(lib_dock, shelf_dock)
        lib_dock.raise_()
        self._shelf_dock = shelf_dock

        # The periodic table is a window of its own (toolbar button / View
        # menu), not a dock: it was too big to keep on screen.
        self.picker = periodic.PeriodicPicker()
        self.picker.picked.connect(self._on_element_picked)
        self._ptable_window = None

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

    def _tree_group(self, parent, title, rows, expanded, color_fn):
        """Add a bold category (with (label, (kind, value)) leaves) under
        *parent* in the library tree."""
        grp = QTreeWidgetItem([title])
        font = grp.font(0)
        font.setBold(True)
        grp.setFont(0, font)
        parent.addChild(grp)
        for label, data in rows:
            child = QTreeWidgetItem([label])
            child.setData(0, Qt.UserRole, data)
            child.setIcon(0, icons.element_icon(color_fn(data)))
            tip = entries.smiles_of(*data)
            if tip:
                child.setToolTip(0, tip)
            elif data[0] == "reaction":
                child.setToolTip(0, data[1])
            grp.addChild(child)
        grp.setExpanded(expanded)

    def _build_ai_dock(self):
        self.ai_dock = AiDock(self)
        self.addDockWidget(Qt.RightDockWidgetArea, self.ai_dock)
        self.ai_dock.hide()             # opened on demand from View / toolbar

    # --------------------------------------------------------------- menus
    def _add_groups(self, parent, groups):
        """One scrollable submenu per group, one action per entry — the
        same ``entries.sections()`` the library tree is built from, so the
        menus and the tree always list the same things."""
        for group, rows in groups:
            sub = parent.addMenu(group.replace("&", "&&"))
            sub.setStyleSheet("QMenu { menu-scrollable: 1; }")
            for label, (kind, value) in rows:
                act = sub.addAction(label.replace("&", "&&"))
                tip = entries.smiles_of(kind, value)
                if tip or kind == "reaction":
                    act.setToolTip(tip or value)
                act.triggered.connect(
                    lambda _=False, k=kind, v=value, n=label:
                    self.load_entry(k, v, n))

    def _build_menus(self):
        mb = self.menuBar()
        sec = {t.split(" —")[0]: g for t, g in entries.sections()}
        self._menus = {}

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
        rd = smi
        self._act(m_mol, "Explorer…", self.open_explorer, "Ctrl+L",
                  "mdi.magnify")
        self._act(m_mol, "From SMILES…", self.from_smiles,
                  "Ctrl+Shift+M", "mdi.molecule")
        self._act(m_mol, "Import structure file…" + rd, self.import_file)
        self._act(m_mol, "Copy SMILES of structure" + rd, self.copy_smiles)
        m_mol.addSeparator()
        self._act(m_mol, "Properties…", self.show_properties, "Ctrl+I",
                  "mdi.information-outline")
        m_mol.addSeparator()
        self._add_groups(m_mol, sec["Molecules"])
        m_mol.addSeparator()
        classic = m_mol.addMenu("Classic 3D models")
        for title, keys in library.CATEGORIES:
            if title in ("Crystal structures", "Lattice systems"):
                continue
            sub = classic.addMenu(title)
            for key in keys:
                act = QAction(library.label(key), self)
                act.triggered.connect(lambda _=False, k=key: self.load_model(k))
                sub.addAction(act)
        self._menus["molecules"] = m_mol

        m_xtal = mb.addMenu("&Crystal")
        self._act(m_xtal, "Crystal builder…", self.open_crystal_builder,
                  "Ctrl+Shift+C", "mdi.cube-outline")
        self._act(m_xtal, "Surface builder…", self.open_surface_builder,
                  "Ctrl+Shift+F", "mdi.layers-outline")
        self._act(m_xtal, "Graphene, nanotubes & fullerenes…",
                  self.open_nano_builder, "Ctrl+Shift+G", "mdi.hexagon-multiple")
        m_xtal.addSeparator()
        self._add_groups(m_xtal, sec["Crystals"])
        m_surf = m_xtal.addMenu("Surfaces")
        self._act(m_surf, "Surface builder…", self.open_surface_builder)
        m_surf.addSeparator()
        self._add_groups(m_surf, sec["Surfaces"])
        m_nano = m_xtal.addMenu("Graphene, nanotubes && fullerenes")
        self._act(m_nano, "Graphene, nanotubes && fullerenes builder…",
                  self.open_nano_builder)
        m_nano.addSeparator()
        self._add_groups(m_nano, sec["Graphene, nanotubes & fullerenes"])
        self._menus.update(crystals=m_xtal, surfaces=m_surf, carbon=m_nano)
        classic = m_xtal.addMenu("Classic crystal models")
        for title, keys in library.CATEGORIES:
            if title not in ("Crystal structures", "Lattice systems"):
                continue
            sub = classic.addMenu(title)
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
        self._xtal_cell = self._act(m_xtal, "Unit cell outline",
                                    self._toggle_cell)
        self._xtal_cell.setCheckable(True)
        self._act(m_xtal, "Reset cell tilts", self.viewer.reset_tilts)
        self._act(m_xtal, "Reset colours", self.viewer.reset_colors)
        m_xtal.aboutToShow.connect(self._sync_crystal_menu)

        m_poly = mb.addMenu("&Polymer")
        self._act(m_poly, "Polymer builder…", self.open_polymer_builder,
                  "Ctrl+Shift+P", "mdi.link-variant")
        m_poly.addSeparator()
        self._add_groups(m_poly, sec["Polymers"])
        self._menus["polymers"] = m_poly

        m_rx = mb.addMenu("&Reaction")
        self._act(m_rx, "Reaction builder…", self.open_reaction_builder,
                  "Ctrl+R", "mdi.flask-outline")
        m_rx.addSeparator()
        self._add_groups(m_rx, sec["Reactions"])
        self._menus["reactions"] = m_rx

        m_struct = mb.addMenu("&Structure")
        self._act(m_struct, "Flatten 3D → 2D sketch", self.flatten_to_2d)
        self._act(m_struct, "Build 3D from 2D sketch", self.build_3d_from_sketch,
                  "Ctrl+B")
        self._act(m_struct, "Clear 2D sketch", self.sketch.clear)
        m_struct.addSeparator()
        repr_menu = m_struct.addMenu("2D representation")
        repr_group = QActionGroup(self)
        for key in molrepr.MODES:
            act = QAction(molrepr.MODE_LABELS[key], self)
            act.setCheckable(True)
            act.setChecked(key == "skeletal")
            act.triggered.connect(
                lambda _=False, k=key: self.sketch.set_mode(k))
            repr_group.addAction(act)
            repr_menu.addAction(act)

        m_view = mb.addMenu("&View")
        theme_menu = m_view.addMenu("Theme")
        group = QActionGroup(self)
        for name in style.THEMES:
            act = QAction(name, self, checkable=True)
            act.setChecked(name == style.current_theme())
            act.triggered.connect(lambda _=False, n=name: self._set_theme(n))
            group.addAction(act)
            theme_menu.addAction(act)
        rend_menu = m_view.addMenu("3D renderer")
        self._rend_group = QActionGroup(self)
        self._rend_acts = {}
        for kind, text in (("gl", "OpenGL (shaded spheres, smooth edges)"),
                           ("classic", "Classic (vector drawing)")):
            act = QAction(text, self, checkable=True)
            act.setChecked(self.viewer.renderer == kind)
            act.setEnabled(kind == "classic" or self.viewer.gl_available())
            act.triggered.connect(lambda _=False, k=kind: self._set_renderer(k))
            self._rend_group.addAction(act)
            rend_menu.addAction(act)
            self._rend_acts[kind] = act
        self.viewer.renderer_changed.connect(self._on_renderer_changed)
        style_menu = m_view.addMenu("3D style")
        self._style_group = QActionGroup(self)
        for key, text in viewer3d.STYLE_LABELS.items():
            act = QAction(text, self, checkable=True)
            act.setChecked(self.viewer.style == key)
            act.triggered.connect(lambda _=False, k=key: self.viewer.set_style(k))
            self._style_group.addAction(act)
            style_menu.addAction(act)
        self._view_cell = self._act(m_view, "Unit cell outline",
                                    self._toggle_cell)
        self._view_cell.setCheckable(True)
        self._view_cell.setChecked(True)
        m_view.aboutToShow.connect(self._sync_crystal_menu)
        m_view.addSeparator()
        self._act(m_view, "Show 3D View", lambda: self.tabs.setCurrentIndex(0))
        self._act(m_view, "Show 2D Sketch", lambda: self.tabs.setCurrentIndex(1))
        m_view.addSeparator()
        m_view.addAction(self._structure_dock.toggleViewAction())
        m_view.addAction(self._library_dock.toggleViewAction())
        m_view.addAction(self._shelf_dock.toggleViewAction())
        self._act(m_view, "Periodic table…", self.show_periodic_table,
                  "Ctrl+T", "mdi.periodic-table")
        ai_toggle = self.ai_dock.toggleViewAction()
        ai_toggle.setText("AI Chat")
        m_view.addAction(ai_toggle)

        m_help = mb.addMenu("&Help")
        self._act(m_help, "User Guide", self.show_guide, "F1")
        m_help.addSeparator()
        from .updater import Updater
        self.updater = Updater(self)
        self.updater.add_menu_actions(m_help)
        m_help.addSeparator()
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
        maintools.build(self)
        self.viewer.molecule_changed.connect(self._sync_tool_states)
        self.viewer.view_changed.connect(self._sync_tool_states)
        self.viewer.structure_changed.connect(self._sync_tool_states)
        self.viewer.selection_changed.connect(self._sync_tool_states)
        self.viewer.order_combo.currentIndexChanged.connect(
            self._sync_order_actions)
        self.tabs.currentChanged.connect(self._sync_tool_states)
        self._sync_tool_states()

    def show_periodic_table(self):
        """Open (or bring forward) the periodic-table window; clicking an
        element there sets the active element for both views."""
        if self._ptable_window is None:
            self._ptable_window = periodic.PeriodicWindow(self.picker, self)
        self._ptable_window.show()
        self._ptable_window.raise_()
        self._ptable_window.activateWindow()

    # ----------------------------------------------------- toolbar helpers
    def use_sketch_tool(self, key):
        """A 2D tool was picked on the toolbar: switch to the sketch."""
        self.sketch.set_tool(key)
        self.tabs.setCurrentIndex(1)

    def add_active_atom(self):
        self.tabs.setCurrentIndex(0)
        self.viewer.add_active()

    def set_bond_order_tool(self, index):
        self.viewer.order_combo.setCurrentIndex(index)

    def _sync_order_actions(self, index):
        if 0 <= index < len(self._order_actions):
            self._order_actions[index].setChecked(True)

    def viewer_bond_selected(self):
        self.tabs.setCurrentIndex(0)
        self.viewer.bond_selected(self.viewer.order)

    def _sync_tool_states(self, *_):
        """Grey out what does not apply: the 3D editing tools on a lattice
        or reaction scene, the film buttons on anything but a reaction, and
        keep the 2D tool highlight in step with the sketch."""
        v = self.viewer
        editable = v.editable
        for act in self._edit_actions:
            act.setEnabled(editable)
        self._edit_actions[-2].setEnabled(editable and v.can_bond_selected(
            v.order))
        self._play_action.setEnabled(v.has_animation)
        self._stop_action.setEnabled(v.has_animation and v.animating)
        self._play_action.setText("Pause" if v.playing else "Animate")
        act = self._tool_actions.get(self.sketch.tool)
        if act is not None and not act.isChecked():
            act.setChecked(True)

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
        self.load_entry(kind, value, item.text(0))

    def load_model(self, key):
        self.load_entry("model", key, library.label(key))

    def load_entry(self, kind, value, label=None):
        """Build a library entry (see `entries`) into the 3D view and mirror
        it into the 2D sketch. Reports a failure instead of raising."""
        try:
            mol = entries.build(kind, value, label)
        except (BuildError, KeyError, ValueError) as exc:
            QMessageBox.warning(self, "Cannot build", str(exc.args[0]
                                                          if exc.args else exc))
            return False
        self.viewer.set_molecule(mol)
        self._sync_sketch(force=True)
        self.tabs.setCurrentIndex(0)
        self._retitle()
        note = f" ({mol.formula()})" if mol.formula() and not mol.notes else ""
        self.statusBar().showMessage(f"Loaded {label or mol.label}{note}")
        if kind == "reaction" and self.viewer.has_animation \
                and self.tabs.currentIndex() == 0:
            # show what the equation means: play the film once, then come
            # back to the equation (Animate replays it)
            QTimer.singleShot(250, lambda: self.viewer.play(True))
        return True

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
        if not mol.atoms or mol.notes or len(mol.atoms) > 400:
            self.sketch.clear()             # a lattice / scene has no 2D form
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
        None (a crystal, surface or reaction has no skeletal form)."""
        if kind not in ("model", "compound", "smiles"):
            return None
        smi = entries.smiles_of(kind, value)
        if smi and rdkit_io.available():
            try:
                a2, b2 = rdkit_io.sketch_from_smiles(smi)
                if a2:
                    return a2, b2
            except Exception:                       # noqa: BLE001
                pass
        try:
            mol = entries.build(kind, value)
        except (BuildError, KeyError, ValueError):
            return None
        if mol.crystal:
            return None
        if kind == "model" and rdkit_io.available():
            smi = rdkit_io.smiles_from_structure(mol.atoms, mol.bonds)
            if smi:
                try:
                    a2, b2 = rdkit_io.sketch_from_smiles(smi)
                    if a2:
                        return a2, b2
                except Exception:                   # noqa: BLE001
                    pass
        return self._flatten_2d(mol)

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
        """The 3D `Molecule` for a library entry, or None (with the reason
        in the status bar)."""
        try:
            return entries.build(kind, value)
        except (BuildError, KeyError, ValueError) as exc:
            self.statusBar().showMessage(str(exc.args[0] if exc.args else exc))
            return None

    def _on_drop_compound_3d(self, kind, value):
        mol = self._compound_3d(kind, value)
        if mol is None:
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
                "Can't place that in 2D (crystals, surfaces and reactions "
                "have no skeletal form).")
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
        combo = getattr(self, "tb_element", None)
        if combo is not None and combo.currentText() != el:
            i = combo.findText(el)
            combo.blockSignals(True)
            if i < 0:               # an element outside the quick list
                combo.addItem(icons.element_icon(elements.color(el)), el)
                i = combo.findText(el)
            combo.setCurrentIndex(i)
            combo.blockSignals(False)
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

    def _set_renderer(self, kind):
        used = self.viewer.set_renderer(kind)
        QSettings(*style._SETTINGS).setValue("renderer", used)
        if used != kind:
            self.statusBar().showMessage(self.viewer.renderer_note
                                         or "OpenGL is not available here.")

    def _on_renderer_changed(self, kind):
        act = self._rend_acts.get(kind)
        if act is not None:
            act.setChecked(True)

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
        if choice:
            kind, value, name = choice
            self.load_entry(kind, value, name)

    def from_smiles(self):
        text, ok = QInputDialog.getText(
            self, "Build from SMILES",
            "Enter a SMILES string (e.g. CCO, c1ccccc1, CC(=O)O):")
        if ok and text.strip():
            self.build_smiles(text.strip())

    def build_smiles(self, smiles, label=None):
        """Build *smiles* into the 3D viewer and 2D sketch — with RDKit when
        installed, otherwise the built-in builder."""
        if not self.load_entry("smiles", smiles, label):
            return False
        engine = "RDKit" if rdkit_io.available() else "the built-in builder"
        self.statusBar().showMessage(
            f"Built {label or smiles} with {engine} "
            f"({self.viewer.mol.formula()})")
        return True

    # ------------------------------------------------------------ builders
    def _run_dialog(self, dlg):
        if dlg.exec_() == dlg.Accepted:
            kind, value, label = dlg.entry()
            self.load_entry(kind, value, label)

    def open_crystal_builder(self):
        self._run_dialog(builders_ui.CrystalDialog(self))

    def drawn_molecule(self):
        """The molecule the user has been building or loading: what is in the
        3D view if it is an editable molecule, else the last one that was —
        so it is still there after a surface replaced it."""
        v = self.viewer
        if v.editable and v.mol.atoms and not v.mol.notes:
            return v.mol.clone()
        return self._last_drawn

    def _remember_drawn(self, *_):
        v = self.viewer
        if v.editable and v.mol.atoms and not v.mol.notes \
                and not v.animating:
            self._last_drawn = v.mol.clone()

    def open_surface_builder(self):
        dlg = builders_ui.SurfaceDialog(self, molecule=self.drawn_molecule())
        if dlg.exec_() != dlg.Accepted:
            return
        kind, value, label = dlg.entry()
        try:
            ads = dlg.adsorbate()
        except (BuildError, KeyError, ValueError) as exc:
            QMessageBox.warning(self, "Cannot build", str(exc.args[0]
                                                          if exc.args else exc))
            return
        if ads is None:
            self.load_entry(kind, value, label)
            return
        try:
            base = entries.build(kind, value, label)
            mol = chem.add_adsorbate(base, ads, **dlg.placement())
        except (BuildError, KeyError, ValueError) as exc:
            QMessageBox.warning(self, "Cannot build", str(exc.args[0]
                                                          if exc.args else exc))
            return
        self.viewer.set_molecule(mol)
        self._sync_sketch(force=True)
        self.tabs.setCurrentIndex(0)
        self._retitle()
        self.statusBar().showMessage(f"{ads.label} placed on {label}")

    def open_nano_builder(self):
        self._run_dialog(builders_ui.NanoDialog(self))

    def open_polymer_builder(self):
        self._run_dialog(builders_ui.PolymerDialog(self))

    def open_reaction_builder(self):
        self._run_dialog(builders_ui.ReactionDialog(self, shelf=self.shelf))

    # ---------------------------------------------------- kept molecules
    def keep_molecule(self):
        """Put the molecule in the 3D view on the shelf, under a name."""
        mol = self.drawn_molecule()
        if mol is None:
            self.statusBar().showMessage("Nothing to keep: build or load a "
                                         "molecule in the 3D view first.")
            return
        name, ok = QInputDialog.getText(
            self, "Keep molecule",
            f"Name for this molecule ({mol.formula()}):",
            text=self.shelf.next_name())
        if not ok:
            return
        try:
            used = self.shelf.add(mol, name)
        except BuildError as exc:
            QMessageBox.warning(self, "Cannot keep", str(exc.args[0]))
            return
        self.shelf_panel.refresh(select=used)
        self._shelf_dock.show()
        self._shelf_dock.raise_()
        self.statusBar().showMessage(
            f"Kept {used} — use it in a reaction as {shelf.token(used)}.")

    def _show_shelf(self):
        self._shelf_dock.show()
        self._shelf_dock.raise_()

    def load_kept(self, name):
        self.load_entry("mine", name, name)

    def rename_kept(self, name):
        new, ok = QInputDialog.getText(self, "Rename", "New name:", text=name)
        if ok:
            try:
                self.shelf.rename(name, new)
            except BuildError as exc:
                QMessageBox.warning(self, "Cannot rename", str(exc.args[0]))
                return
            self.shelf_panel.refresh(select=new.strip())

    def delete_kept(self, name):
        self.shelf.remove(name)
        self.shelf_panel.refresh()

    def move_kept(self, name, delta):
        self.shelf.move(name, delta)
        self.shelf_panel.refresh(select=name)

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
    def _toggle_cell(self):
        """View / Crystal menu: flip the unit-cell outline."""
        self.viewer.set_cell_visible(not self.viewer.mol.cell_visible)
        self._sync_crystal_menu()

    def _sync_crystal_menu(self):
        """Keep the Crystal menu's checkmarks and enabled state in step with
        the loaded structure."""
        v = self.viewer
        self._xtal_poly.setChecked(v.poly_btn.isChecked())
        self._xtal_poly.setEnabled(v.poly_btn.isEnabled())
        self._xtal_legend.setChecked(v.legend_btn.isChecked())
        for act in (self._xtal_cell, self._view_cell):
            act.setChecked(v.cell_btn.isChecked())
            act.setEnabled(v.cell_btn.isEnabled())

    def stack_cells(self):
        """Ask for an nx × ny × nz supercell and tile the crystal into it."""
        v = self.viewer
        if str(v.mol.name).startswith("crystal:"):
            # a library crystal is rebuilt by the Crystal builder, which
            # also picks how many cells to show
            self._run_dialog(builders_ui.CrystalDialog(
                self, key=v.mol.name.split(":", 1)[1]))
            return
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
            sp.setRange(1, supercell.MAX_CELLS)
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
        shown = m.addMenu("Show as")
        for key in molrepr.MODES:
            act = shown.addAction(
                molrepr.MODE_LABELS[key],
                lambda _=False, k=key: self.sketch.set_mode(k))
            act.setCheckable(True)
            act.setChecked(self.sketch.mode == key)
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
            self.viewer.render_image(1600, 1200).save(path, "PNG")
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
                                           self.sketch.show_labels,
                                           self.sketch.mode)
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
    if library.is_crystal(key):
        return "#9aa0a6"
    return elements.color("C")


_KIND_COLORS = {"crystal": "#9aa0a6", "surface": "#b08d6e", "nano": "#4d5560",
                "reaction": "#159c74"}


def _entry_color(data):
    """Tree-icon colour for a ``(kind, value)`` library entry."""
    kind, value = data
    if kind == "model":
        return _key_color(value)
    return _KIND_COLORS.get(kind, elements.color("C"))
