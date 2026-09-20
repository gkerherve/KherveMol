"""The main window's toolbars: every way to make a structure, as icons.

Two rows of icon-only buttons (names are in the tooltips). The top row
holds the file operations and every *library* — a button that opens the
same menu the menubar shows (builder first, then the entries the library
tree lists). The second
row holds the *drawing* tools: the 2D sketch tools and element, the 3D
builder (add an atom, bond order, join, delete, labels), conversion
between the two views, and the reaction film.

Copyright (C) 2026 Gwilherm Kerherve

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
"""

from PyQt5.QtCore import QSize, Qt
from PyQt5.QtWidgets import (QAction, QActionGroup, QComboBox, QLabel,
                             QToolBar, QToolButton)

from . import elements, icons


def _toolbar(win, title):
    tb = QToolBar(title, win)
    tb.setMovable(False)
    tb.setIconSize(QSize(20, 20))
    # icons only — the label under each icon made the bar tall; the name
    # is in the tooltip (a button without an icon still shows its text)
    tb.setToolButtonStyle(Qt.ToolButtonIconOnly)
    win.addToolBar(tb)
    return tb


def _action(win, tb, text, slot, icon_name, tip=None, checkable=False):
    act = QAction(icons.icon(icon_name), text, win)
    act.setToolTip(tip or text)
    act.setCheckable(checkable)
    if checkable:
        act.toggled.connect(slot)
    else:
        act.triggered.connect(slot)
    tb.addAction(act)
    return act


def _split(win, tb, text, icon_name, slot, menu, tip):
    """A menu button: click = the library's menu (its first entry is the
    builder). *slot* is kept for the tooltip's sake only."""
    btn = QToolButton()
    btn.setText(text)
    btn.setIcon(icons.icon(icon_name))
    btn.setToolTip(tip)
    btn.setToolButtonStyle(Qt.ToolButtonIconOnly)
    btn.setPopupMode(QToolButton.InstantPopup)
    btn.setStyleSheet("QToolButton::menu-indicator { image: none; }")
    btn.setMenu(menu)
    tb.addWidget(btn)
    return btn


def build(win):
    """Create the toolbars on *win* (a `MainWindow` whose menus exist)."""
    m = win._menus
    top = _toolbar(win, "Files and libraries")
    _action(win, top, "New", win.new_document, "mdi.file-outline",
            "New document (Ctrl+N)")
    _action(win, top, "Open", win.open_dialog, "mdi.folder-open",
            "Open a .kmol file (Ctrl+O)")
    _action(win, top, "Save", win.save, "mdi.content-save",
            "Save (Ctrl+S)")
    _action(win, top, "PNG", win.export_png, "mdi.image",
            "Export the current tab as a PNG (Ctrl+E)")
    _action(win, top, "SVG", win.export_svg, "mdi.vector-square",
            "Export an SVG that opens in KhervePaint (Ctrl+Shift+E)")
    top.addSeparator()
    _action(win, top, "Explorer", win.open_explorer, "mdi.magnify",
            "Search every molecule, crystal, surface, polymer and reaction "
            "(Ctrl+L)")
    _action(win, top, "SMILES", win.from_smiles, "mdi.molecule",
            "Build a molecule from a SMILES string (Ctrl+Shift+M)")
    top.addSeparator()
    _split(win, top, "Molecules", "mdi.atom", win.open_explorer,
           m["molecules"], "Molecules — 700, by family (menu; the Explorer searches them)")
    _split(win, top, "Polymers", "mdi.link-variant",
           win.open_polymer_builder, m["polymers"],
           "Polymers — Polymer builder, then PE, PVC, nylon, PET… "
           "(Ctrl+Shift+P)")
    _split(win, top, "Crystals", "mdi.cube-outline",
           win.open_crystal_builder, m["crystals"],
           "Crystals — Crystal builder and 120+ crystals "
           "(Ctrl+Shift+C)")
    _split(win, top, "Surfaces", "mdi.layers-outline",
           win.open_surface_builder, m["surfaces"],
           "Surfaces — Surface builder and 60 ready faces (Ctrl+Shift+F)")
    _split(win, top, "Carbon", "mdi.hexagon-multiple",
           win.open_nano_builder, m["carbon"],
           "Carbon — graphene, nanotubes and fullerenes (Ctrl+Shift+G)")
    _split(win, top, "Reactions", "mdi.flask-outline",
           win.open_reaction_builder, m["reactions"],
           "Reactions — Reaction builder and 36 classics (Ctrl+R)")
    top.addSeparator()
    _action(win, top, "Properties", win.show_properties,
            "mdi.information-outline", "Formula, weight and descriptors "
            "(Ctrl+I)")
    ai = win.ai_dock.toggleViewAction()
    ai.setIcon(icons.icon("mdi.robot-outline"))
    ai.setText("AI Chat")
    ai.setToolTip("AI Chat — ask chemistry questions, draw molecules")
    top.addAction(ai)
    _action(win, top, "Guide", win.show_guide, "mdi.help-circle-outline",
            "User guide (F1)")

    win.addToolBarBreak()
    draw = _toolbar(win, "Drawing tools")
    draw.addWidget(QLabel(" 2D "))
    win._tool_actions = {}
    group = QActionGroup(win)
    for key, text, icon_name, tip in (
            ("draw", "Draw", "mdi.pencil",
             "Draw bonds: drag atom→atom, or atom→empty for a new atom; "
             "click a bond to cycle its order"),
            ("move", "Move", "mdi.cursor-move",
             "Drag an atom to move its whole molecule"),
            ("atom", "Atom", "mdi.format-text",
             "Click an atom to re-label it with the chosen element"),
            ("erase", "Erase", "mdi.eraser",
             "Click an atom or bond to remove it")):
        act = QAction(icons.icon(icon_name), text, win)
        act.setCheckable(True)
        act.setToolTip(tip)
        act.setChecked(key == "draw")
        act.triggered.connect(lambda _=False, k=key: win.use_sketch_tool(k))
        group.addAction(act)
        draw.addAction(act)
        win._tool_actions[key] = act
    _action(win, draw, "Clear", win.sketch.clear, "mdi.close-circle-outline",
            "Clear the 2D sketch")
    draw.addSeparator()
    draw.addWidget(QLabel(" Element "))
    win.tb_element = QComboBox()
    win.tb_element.setToolTip("The element drawn / added (the periodic "
                              "table at the bottom picks any element)")
    for el in elements.PALETTE:
        win.tb_element.addItem(icons.element_icon(elements.color(el)), el)
    win.tb_element.currentTextChanged.connect(win._on_element_picked)
    draw.addWidget(win.tb_element)
    _action(win, draw, "Table", win.show_periodic_table,
            "mdi.periodic-table", "Periodic table — pick any of the 118 "
            "elements (Ctrl+T)")
    draw.addSeparator()
    draw.addWidget(QLabel(" 3D "))
    win._edit_actions = []
    add = _action(win, draw, "Add atom", win.add_active_atom,
                  "mdi.plus-circle-outline",
                  "Bond a new atom of the chosen element onto the selected "
                  "atom (valence-checked)")
    win._edit_actions.append(add)
    order_group = QActionGroup(win)
    win._order_actions = []
    for i, (text, icon_name) in enumerate((("Single", "mdi.minus"),
                                           ("Double", "mdi.equal"),
                                           ("Triple", "mdi.menu"))):
        act = QAction(icons.icon(icon_name), text, win)
        act.setCheckable(True)
        act.setChecked(i == 0)
        act.setToolTip(f"{text} bond for the atoms you add or join")
        act.triggered.connect(lambda _=False, k=i: win.set_bond_order_tool(k))
        order_group.addAction(act)
        draw.addAction(act)
        win._order_actions.append(act)
        win._edit_actions.append(act)
    join = _action(win, draw, "Bond", win.viewer_bond_selected,
                   "mdi.link", "Bond the two selected atoms (Ctrl+click a "
                   "second atom)")
    dele = _action(win, draw, "Delete", win.viewer.delete_selected,
                   "mdi.delete-outline", "Delete the selected atom "
                   "(Delete)")
    win._edit_actions += [join, dele]
    win._labels_action = _action(
        win, draw, "Labels", win.viewer.labels_btn.setChecked,
        "mdi.tag-text-outline", "Show element symbols on the atoms",
        checkable=True)
    win.viewer.labels_btn.toggled.connect(win._labels_action.setChecked)
    win._lock_action = _action(
        win, draw, "Lock", win.viewer.lock_btn.setChecked,
        "mdi.lock-outline", "Hold bonds at their real length while "
        "dragging an atom", checkable=True)
    win._lock_action.setChecked(win.viewer.lock_btn.isChecked())
    win.viewer.lock_btn.toggled.connect(win._lock_action.setChecked)
    draw.addSeparator()
    _action(win, draw, "3D → 2D", win.flatten_to_2d, "mdi.arrow-decision",
            "Flatten the 3D model into the 2D sketch")
    _action(win, draw, "2D → 3D", win.build_3d_from_sketch,
            "mdi.rotate-3d", "Build a 3D model from the 2D sketch "
            "(Ctrl+B, needs RDKit)")
    draw.addSeparator()
    win._play_action = _action(win, draw, "Animate", win.viewer.toggle_animation,
                               "mdi.play", "Play the reaction as a film — "
                               "atoms rearrange")
    win._stop_action = _action(win, draw, "Equation",
                               win.viewer.stop_animation, "mdi.stop",
                               "Back to the equation with its arrow")
    return top, draw
