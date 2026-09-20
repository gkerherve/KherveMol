"""Export dialogs: 3D models (STL, 3MF, OBJ, PLY, GLB) and chemistry files
(XYZ, MOL, SDF, PDB, CIF).

`File ▸ Export 3D model…` asks for the format, the size (millimetres per
ångström, with the resulting dimensions shown), the style, the quality and
whether to include the cell outline; `File ▸ Export chemistry file…` just
picks a file name — the format follows the extension.

Copyright (C) 2026 Gwilherm Kerherve

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
"""

import os

from PyQt5.QtWidgets import (QCheckBox, QComboBox, QDialog, QDialogButtonBox,
                             QDoubleSpinBox, QFileDialog, QFormLayout, QLabel,
                             QMessageBox, QVBoxLayout)

from . import chemexport, meshexport
from .crystal import BuildError

_STYLE_TEXT = {"ball_and_stick": "Ball and stick",
               "space_filling": "Space filling", "sticks": "Sticks"}


def _extent_mm(mol, style, scale):
    """Rough (x, y, z) size in mm of the exported model."""
    if not mol.atoms:
        return 0.0, 0.0, 0.0
    factor = 1.0 if style == "space_filling" else float(mol.bond or 1.0)
    rad = [meshexport.ball_radius(a[0], style, mol.rscale) for a in mol.atoms]
    out = []
    for d in (1, 2, 3):
        lo = min(a[d] * factor - r for a, r in zip(mol.atoms, rad))
        hi = max(a[d] * factor + r for a, r in zip(mol.atoms, rad))
        out.append((hi - lo) * scale)
    return tuple(out)


class MeshDialog(QDialog):
    """Options for a 3D-model export."""

    def __init__(self, mol, style="ball_and_stick", parent=None):
        super().__init__(parent)
        self.mol = mol
        self.setWindowTitle("Export 3D model")
        self.setMinimumWidth(480)
        form = QFormLayout()
        self.fmt = QComboBox()
        for key, (name, tip) in meshexport.FORMATS.items():
            self.fmt.addItem(f"{name} — {tip}", key)
        form.addRow("Format", self.fmt)
        self.style = QComboBox()
        for key in meshexport.STYLES:
            self.style.addItem(_STYLE_TEXT[key], key)
        self.style.setCurrentIndex(max(0, self.style.findData(style)))
        form.addRow("Style", self.style)
        self.scale = QDoubleSpinBox()
        self.scale.setRange(0.05, 1000)
        self.scale.setDecimals(2)
        self.scale.setValue(10.0)
        self.scale.setSuffix(" mm per Å")
        self.scale.setToolTip("Size of the model: a C–C bond is 1.5 Å, so 10 "
                              "mm/Å prints it 15 mm long")
        form.addRow("Size", self.scale)
        self.size = QLabel("")
        self.size.setStyleSheet("color:#555;")
        form.addRow("", self.size)
        self.quality = QComboBox()
        for key, txt in (("low", "Low (small file)"), ("medium", "Medium"),
                         ("high", "High (smooth spheres)")):
            self.quality.addItem(txt, key)
        self.quality.setCurrentIndex(1)
        form.addRow("Quality", self.quality)
        self.stick = QDoubleSpinBox()
        self.stick.setRange(0.2, 10)
        self.stick.setValue(1.6)
        self.stick.setSuffix(" mm")
        self.stick.setToolTip("The thinnest bond, so a print is not made of "
                              "threads")
        form.addRow("Thinnest bond", self.stick)
        self.cell = QCheckBox("Include the unit-cell outline")
        self.cell.setChecked(bool(mol.edges) and mol.cell_visible)
        self.cell.setEnabled(bool(mol.edges))
        form.addRow("", self.cell)
        self.ascii = QCheckBox("Write the STL as text (bigger, human-readable)")
        form.addRow("", self.ascii)
        root = QVBoxLayout(self)
        root.addLayout(form)
        note = QLabel("Spheres and bonds overlap where they meet — slicers "
                      "and viewers merge them. Coordinates are in millimetres, "
                      "z up, standing on z = 0.")
        note.setWordWrap(True)
        note.setStyleSheet("color:#666;")
        root.addWidget(note)
        buttons = QDialogButtonBox(QDialogButtonBox.Cancel)
        self.ok_btn = buttons.addButton("Export…", QDialogButtonBox.AcceptRole)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)
        for w in (self.scale,):
            w.valueChanged.connect(self._update)
        self.style.currentIndexChanged.connect(self._update)
        self.fmt.currentIndexChanged.connect(self._sync)
        self._sync()

    def _sync(self, *_):
        self.ascii.setEnabled(self.fmt.currentData() == "stl")
        self._update()

    def _update(self, *_):
        x, y, z = _extent_mm(self.mol, self.style.currentData(),
                             self.scale.value())
        self.size.setText(f"About {x:.0f} × {y:.0f} × {z:.0f} mm "
                          f"({len(self.mol.atoms)} atoms)")

    def format(self):
        return self.fmt.currentData()

    def options(self):
        return dict(style=self.style.currentData(), scale=self.scale.value(),
                    quality=self.quality.currentData(),
                    cell=self.cell.isChecked(),
                    min_stick_mm=self.stick.value(),
                    ascii=self.ascii.isChecked())


def export_mesh(window):
    """File ▸ Export 3D model…"""
    mol = window.viewer.mol
    if not mol.atoms:
        window.statusBar().showMessage("Nothing to export.")
        return
    dlg = MeshDialog(mol, window.viewer.style, window)
    if dlg.exec_() != QDialog.Accepted:
        return
    fmt = dlg.format()
    name, tip = meshexport.FORMATS[fmt]
    path, _ = QFileDialog.getSaveFileName(
        window, f"Export {name}", f"molecule.{fmt}", f"{name} (*.{fmt})")
    if not path:
        return
    try:
        result = meshexport.export(mol, path, fmt, **dlg.options())
    except BuildError as exc:
        QMessageBox.warning(window, "Export failed", str(exc.args[0]))
        return
    extra = " (+ .mtl)" if fmt == "obj" else ""
    window.statusBar().showMessage(
        f"Exported {os.path.basename(result['path'])}{extra} — "
        f"{result['triangles']:,} triangles, {result['colours']} colours")


def _chem_filter():
    parts = [f"{n} (*.{k})" for k, (n, _t) in chemexport.FORMATS.items()]
    return ";;".join(parts)


def export_chemistry(window):
    """File ▸ Export chemistry file…"""
    mol = window.viewer.mol
    if not mol.atoms:
        window.statusBar().showMessage("Nothing to export.")
        return
    default = "crystal.cif" if mol.edges else "molecule.xyz"
    path, chosen = QFileDialog.getSaveFileName(
        window, "Export chemistry file", default, _chem_filter())
    if not path:
        return
    ext = os.path.splitext(path)[1].lstrip(".").lower()
    if ext not in chemexport.FORMATS:
        for key, (name, _t) in chemexport.FORMATS.items():
            if chosen.startswith(name):
                ext = key
        path += "." + ext if ext in chemexport.FORMATS else ""
    try:
        result = chemexport.export(mol, path, ext)
    except BuildError as exc:
        QMessageBox.warning(window, "Export failed", str(exc.args[0]))
        return
    window.statusBar().showMessage(
        f"Exported {os.path.basename(result['path'])} "
        f"({result['atoms']} atoms)")
