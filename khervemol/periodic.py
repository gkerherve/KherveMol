"""A compact periodic-table element picker.

`PeriodicPicker` is a small grid of element buttons laid out in their
classic table positions. Clicking one emits `picked(symbol)`. Used as the
left dock so the active drawing element is always one click away.

Copyright (C) 2026 Gwilherm Kerherve

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
"""

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (QGridLayout, QLabel, QPushButton, QVBoxLayout,
                             QWidget)

from . import elements


class PeriodicPicker(QWidget):
    picked = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._buttons = {}
        self._active = "C"
        root = QVBoxLayout(self)
        root.setContentsMargins(6, 6, 6, 6)
        title = QLabel("Active element")
        title.setStyleSheet("font-weight:bold;")
        root.addWidget(title)

        grid = QGridLayout()
        grid.setSpacing(2)
        for el, row, col in elements.TABLE:
            btn = QPushButton(el)
            btn.setFixedSize(30, 26)
            btn.setCheckable(True)
            btn.setToolTip(f"{elements.NUMBERS.get(el, '')}  "
                           f"{elements.name(el)}")
            self._style_button(btn, el, False)
            btn.clicked.connect(lambda _=False, e=el: self.set_active(e))
            grid.addWidget(btn, row, col)
            self._buttons[el] = btn
        root.addLayout(grid)
        self._info = QLabel("")
        self._info.setWordWrap(True)
        self._info.setStyleSheet("color:#555; padding-top:4px;")
        root.addWidget(self._info)
        root.addStretch(1)
        self.set_active("C")

    def _style_button(self, btn, el, active):
        color = elements.color(el)
        border = "2px solid #159c74" if active else "1px solid #999"
        btn.setStyleSheet(
            f"QPushButton {{ background:{color}; color:{elements.text_color(el)};"
            f" font-weight:bold; border:{border}; border-radius:4px; }}")

    def set_active(self, el):
        self._active = el
        for sym, btn in self._buttons.items():
            act = sym == el
            btn.setChecked(act)
            self._style_button(btn, sym, act)
        num = elements.NUMBERS.get(el, "?")
        val = elements.VALENCE.get(el, "—")
        self._info.setText(f"<b>{el}</b> — {elements.name(el)}<br>"
                           f"Z = {num},  valence {val}")
        self.picked.emit(el)

    def active(self):
        return self._active
