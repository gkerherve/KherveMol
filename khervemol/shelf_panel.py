"""The "My molecules" panel: the shelf of kept molecules.

A list of the molecules you kept (with their formulas) and the buttons to
keep the current one, load one back, rename, reorder or delete. Double-click
loads into the 3D view; a row can also be dragged onto either view.

Copyright (C) 2026 Gwilherm Kerherve

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
"""

from PyQt5.QtCore import QMimeData, Qt, pyqtSignal
from PyQt5.QtWidgets import (QHBoxLayout, QLabel, QListWidget,
                             QListWidgetItem, QPushButton, QVBoxLayout,
                             QWidget)

from . import dnd, icons, shelf


class _ShelfList(QListWidget):
    def mimeData(self, items):
        md = QMimeData()
        for it in items:
            md.setData(dnd.MIME_COMPOUND, dnd.encode("mine", it.data(
                Qt.UserRole)))
            break
        return md

    def startDrag(self, actions):
        super().startDrag(Qt.CopyAction)


class ShelfPanel(QWidget):
    """Shows a `shelf.Shelf`; asks the window to do the work."""

    keep_requested = pyqtSignal()
    load_requested = pyqtSignal(str)
    rename_requested = pyqtSignal(str)
    delete_requested = pyqtSignal(str)
    move_requested = pyqtSignal(str, int)
    reaction_requested = pyqtSignal()

    def __init__(self, store, parent=None):
        super().__init__(parent)
        self.shelf = store
        box = QVBoxLayout(self)
        box.setContentsMargins(4, 4, 4, 4)
        hint = QLabel("Build a molecule in 3D, then <b>Keep</b> it. Use the "
                      "kept molecules in the Reaction builder as "
                      "<code>@Molecule_1</code>.")
        hint.setWordWrap(True)
        hint.setStyleSheet("color:#666;")
        box.addWidget(hint)
        self.list = _ShelfList()
        self.list.setDragEnabled(True)
        self.list.itemDoubleClicked.connect(
            lambda it: self.load_requested.emit(it.data(Qt.UserRole)))
        self.list.currentItemChanged.connect(self._sync)
        box.addWidget(self.list, 1)

        row = QHBoxLayout()
        self.keep_btn = self._btn("Keep current molecule",
                                  "mdi.bookmark-plus-outline",
                                  self.keep_requested.emit,
                                  "Store the molecule in the 3D view on the "
                                  "shelf under a name you choose")
        row.addWidget(self.keep_btn, 1)
        box.addLayout(row)
        row2 = QHBoxLayout()
        self.load_btn = self._btn("Load", "mdi.folder-upload-outline",
                                  lambda: self._emit(self.load_requested),
                                  "Show the selected molecule in 3D")
        self.rename_btn = self._btn("Rename", "mdi.rename-box",
                                    lambda: self._emit(self.rename_requested),
                                    "Rename the selected molecule")
        self.up_btn = self._btn("", "mdi.arrow-up",
                                lambda: self._move(-1), "Move up")
        self.down_btn = self._btn("", "mdi.arrow-down",
                                  lambda: self._move(1), "Move down")
        self.del_btn = self._btn("", "mdi.delete-outline",
                                 lambda: self._emit(self.delete_requested),
                                 "Remove the selected molecule from the shelf")
        for b in (self.load_btn, self.rename_btn, self.up_btn, self.down_btn,
                  self.del_btn):
            row2.addWidget(b)
        box.addLayout(row2)
        self.rx_btn = self._btn("Use in a reaction…", "mdi.flask-outline",
                                self.reaction_requested.emit,
                                "Open the Reaction builder with your kept "
                                "molecules ready to pick")
        box.addWidget(self.rx_btn)
        self.refresh()

    def _btn(self, text, icon_name, slot, tip):
        b = QPushButton(icons.icon(icon_name), text)
        b.setToolTip(tip)
        b.clicked.connect(lambda _=False: slot())
        return b

    def selected(self):
        it = self.list.currentItem()
        return it.data(Qt.UserRole) if it else None

    def _emit(self, signal):
        name = self.selected()
        if name:
            signal.emit(name)

    def _move(self, delta):
        name = self.selected()
        if name:
            self.move_requested.emit(name, delta)

    def _sync(self, *_):
        has = self.selected() is not None
        for b in (self.load_btn, self.rename_btn, self.up_btn, self.down_btn,
                  self.del_btn):
            b.setEnabled(has)
        self.rx_btn.setEnabled(len(self.shelf) > 0)

    def refresh(self, select=None):
        """Rebuild the list from the shelf, keeping (or picking) a row."""
        keep = select or self.selected()
        self.list.clear()
        for name in self.shelf.names():
            it = QListWidgetItem(f"{name}    {self.shelf.formula(name)}")
            it.setData(Qt.UserRole, name)
            it.setToolTip(f"Write it in an equation as {shelf.token(name)}")
            self.list.addItem(it)
            if name == keep:
                self.list.setCurrentItem(it)
        self._sync()
