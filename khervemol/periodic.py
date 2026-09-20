"""The full periodic-table element picker.

`PeriodicPicker` lays out every element (Z = 1..118) in the classic wide
table — s/p/d blocks in rows 1..7 and the f-block (lanthanides / actinides)
below. Each cell shows the atomic number and symbol, coloured by the Jmol
CPK scheme. Clicking one emits `picked(symbol)` and sets it active.
`PeriodicWindow` holds it in a small window of its own, opened from the
toolbar, so the table costs no room in the main window.

Copyright (C) 2026 Gwilherm Kerherve

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
"""

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (QDialog, QGridLayout, QHBoxLayout, QLabel,
                             QPushButton, QScrollArea, QSizePolicy,
                             QVBoxLayout, QWidget)

from . import elements

_CELL_W = 40
_CELL_H = 34


class _ElementButton(QPushButton):
    def __init__(self, symbol):
        super().__init__()
        self.symbol = symbol
        self.setCheckable(True)
        self.setFixedSize(_CELL_W, _CELL_H)
        z = elements.number(symbol)
        self.setText(f"{z}\n{symbol}")
        self.setToolTip(f"{z} — {elements.name(symbol)} "
                        f"(valence {elements.valence(symbol)})")
        self._paint(False)

    def _paint(self, active):
        color = elements.color(self.symbol)
        border = ("2px solid #0c3b2e" if active else "1px solid #7f8a86")
        self.setStyleSheet(
            "QPushButton {"
            f" background:{color}; color:{elements.text_color(self.symbol)};"
            f" border:{border}; border-radius:4px;"
            " font-size:8px; font-weight:bold; text-align:center;"
            " padding:0px; }"
            "QPushButton:hover { border:2px solid #159c74; }")


class PeriodicPicker(QWidget):
    picked = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._buttons = {}
        self._active = "C"
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)

        root = QVBoxLayout(self)
        root.setContentsMargins(8, 6, 8, 6)
        root.setSpacing(4)

        header = QHBoxLayout()
        title = QLabel("Periodic table")
        title.setStyleSheet("font-weight:bold;")
        header.addWidget(title)
        header.addStretch(1)
        self._info = QLabel("")
        self._info.setStyleSheet("color:#333;")
        header.addWidget(self._info)
        root.addLayout(header)

        grid = QGridLayout()
        grid.setSpacing(2)
        grid.setContentsMargins(0, 0, 0, 0)
        for sym, row, col in elements.table_cells():
            btn = _ElementButton(sym)
            btn.clicked.connect(lambda _=False, e=sym: self.set_active(e))
            grid.addWidget(btn, row, col)
            self._buttons[sym] = btn
        # markers where La / Ac series pull out of the main body
        for r, txt in ((6, "57-71"), (7, "89-103")):
            lab = QLabel(txt)
            lab.setAlignment(Qt.AlignCenter)
            lab.setStyleSheet("color:#888; font-size:8px;")
            grid.addWidget(lab, r, 3)
        grid.setRowMinimumHeight(8, 6)          # gap before the f-block
        wrap = QWidget()
        wrap.setLayout(grid)
        root.addWidget(wrap, 0, Qt.AlignLeft)
        root.addStretch(1)
        self.set_active("C")

    def set_active(self, el):
        self._active = el
        for sym, btn in self._buttons.items():
            act = sym == el
            btn.setChecked(act)
            btn._paint(act)
        z = elements.number(el)
        val = elements.valence(el)
        self._info.setText(f"<b>{el}</b> — {elements.name(el)} &nbsp; "
                           f"Z = {z}, valence {val}")
        self.picked.emit(el)

    def active(self):
        return self._active


class PeriodicWindow(QDialog):
    """The periodic table in its own non-modal window. It stays open while
    you work: each click sets the active element, and it scrolls if the
    screen is small."""

    def __init__(self, picker, parent=None):
        super().__init__(parent, Qt.Tool)
        self.setWindowTitle("Periodic table")
        self.setModal(False)
        box = QVBoxLayout(self)
        box.setContentsMargins(6, 6, 6, 6)
        scroll = QScrollArea()
        scroll.setWidget(picker)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        box.addWidget(scroll)
        picker.show()
        hint = picker.sizeHint()
        self.resize(hint.width() + 30, hint.height() + 30)
