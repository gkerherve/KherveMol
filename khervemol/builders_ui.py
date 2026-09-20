"""Builder dialogs: crystals, surfaces, carbon nanostructures, reactions.

Each dialog gathers parameters and exposes ``entry()`` → ``(kind, value,
label)`` for `entries.build` — the main window builds it into the 3D
view. Nothing here touches the viewer directly.

Copyright (C) 2026 Gwilherm Kerherve

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
"""

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (QCheckBox, QComboBox, QDialog, QDialogButtonBox,
                             QDoubleSpinBox, QFormLayout, QHBoxLayout, QLabel,
                             QLineEdit, QPlainTextEdit, QSpinBox, QVBoxLayout)

from urllib.parse import quote

from . import crystal_library, polymers, reactions, smiles, surface
from .crystal import BuildError


class _Dialog(QDialog):
    """Common frame: a form on top, a live summary line, OK / Cancel."""

    ok_text = "Build in 3D"

    def __init__(self, title, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(460)
        self.form = QFormLayout()
        self.summary = QLabel("")
        self.summary.setWordWrap(True)
        self.summary.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.summary.setStyleSheet("color:#555; padding:4px 0;")
        self.buttons = QDialogButtonBox(QDialogButtonBox.Cancel)
        self.ok_btn = self.buttons.addButton(self.ok_text,
                                             QDialogButtonBox.AcceptRole)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        root = QVBoxLayout(self)
        root.addLayout(self.form)
        root.addWidget(self.summary)
        root.addWidget(self.buttons)

    @staticmethod
    def _spin(lo, hi, value, step=1):
        w = QSpinBox()
        w.setRange(lo, hi)
        w.setValue(value)
        w.setSingleStep(step)
        return w

    @staticmethod
    def _dspin(lo, hi, value, step=0.5, decimals=1):
        w = QDoubleSpinBox()
        w.setRange(lo, hi)
        w.setDecimals(decimals)
        w.setSingleStep(step)
        w.setValue(value)
        return w


def _crystal_combo(selected="cu"):
    """A combo of every library crystal, grouped by family."""
    box = QComboBox()
    box.setMaxVisibleItems(24)
    for cat in crystal_library.CATEGORIES:
        for c in crystal_library.LIBRARY.values():
            if c.category == cat:
                box.addItem(f"{c.name}   [{cat}]", c.key)
    box.setCurrentIndex(max(0, box.findData(selected)))
    return box


class CrystalDialog(_Dialog):
    """A block of any library crystal: cells along a, b, c."""

    def __init__(self, parent=None, key="cu"):
        super().__init__("Crystal builder", parent)
        self.combo = _crystal_combo(key)
        self.form.addRow("Crystal", self.combo)
        row = QHBoxLayout()
        self.nx, self.ny, self.nz = (self._spin(1, 12, 1) for _ in range(3))
        for label, w in (("a", self.nx), ("b", self.ny), ("c", self.nz)):
            row.addWidget(QLabel(label))
            row.addWidget(w)
        self.form.addRow("Cells", row)
        self.faces = QCheckBox("Draw atoms on the cell faces in every cell")
        self.faces.setChecked(True)
        self.form.addRow("", self.faces)
        for w in (self.nx, self.ny, self.nz):
            w.valueChanged.connect(self._update)
        self.combo.currentIndexChanged.connect(self._update)
        self.faces.toggled.connect(self._update)
        self._update()

    def crystal(self):
        return crystal_library.LIBRARY[self.combo.currentData()]

    def _update(self, *_):
        c = self.crystal()
        n = self.nx.value() * self.ny.value() * self.nz.value()
        ang = "" if (c.alpha, c.beta, c.gamma) == (90.0, 90.0, 90.0) else \
            f", α {c.alpha:g}° β {c.beta:g}° γ {c.gamma:g}°"
        self.summary.setText(
            f"{c.formula} — {c.system}, {c.space_group}. a = {c.a:.4g} Å, "
            f"b = {c.b:.4g} Å, c = {c.c:.4g} Å{ang}. {len(c.atoms)} atoms per "
            f"cell, {c.computed_density():.3g} g/cm³. About "
            f"{len(c.atoms) * n} atoms shown.")

    def entry(self):
        c = self.crystal()
        cells = f"{self.nx.value()},{self.ny.value()},{self.nz.value()}"
        value = f"{c.key}?cells={cells}"
        if not self.faces.isChecked():
            value += "&boundary=0"
        return "crystal", value, c.name


class SurfaceDialog(_Dialog):
    """A slab of any crystal cut along (hkl)."""

    def __init__(self, parent=None, key="cu"):
        super().__init__("Surface builder", parent)
        self.combo = _crystal_combo(key)
        self.form.addRow("Crystal", self.combo)
        self.miller = QLineEdit("111")
        self.miller.setToolTip("Miller indices: 111, 1 1 0, 1-10 — or four "
                               "hexagonal indices such as 0001, 10-10")
        self.form.addRow("Plane (hkl)", self.miller)
        self.auto = QCheckBox("Size the slab automatically (about 15 Å)")
        self.auto.setChecked(True)
        self.form.addRow("", self.auto)
        row = QHBoxLayout()
        self.nx, self.ny = self._spin(1, 30, 4), self._spin(1, 30, 4)
        row.addWidget(QLabel("u"))
        row.addWidget(self.nx)
        row.addWidget(QLabel("v"))
        row.addWidget(self.ny)
        self.form.addRow("Surface cells", row)
        self.layers = self._spin(1, 30, 3)
        self.form.addRow("Layers deep", self.layers)
        self.term = QComboBox()
        self.term.addItem("Automatic (widest gap between planes)", None)
        for t in (0.0, 0.25, 0.5, 0.75):
            self.term.addItem(f"Cut at {t:.2f} of a layer", t)
        self.form.addRow("Termination", self.term)
        self.auto.toggled.connect(self._sync)
        self.miller.textChanged.connect(self._update)
        self.combo.currentIndexChanged.connect(self._update)
        self.term.currentIndexChanged.connect(self._update)
        self._sync()

    def _sync(self, *_):
        for w in (self.nx, self.ny):
            w.setEnabled(not self.auto.isChecked())
        self._update()

    def _update(self, *_):
        try:
            hkl = surface.parse_miller(self.miller.text())
            c = crystal_library.LIBRARY[self.combo.currentData()]
            self.summary.setText(
                f"{surface.label(c, hkl)} — bulk-terminated slab, top "
                "surface facing up (no relaxation or reconstruction).")
            self.ok_btn.setEnabled(True)
        except BuildError as exc:
            self.summary.setText(f"⚠ {exc}")
            self.ok_btn.setEnabled(False)

    def entry(self):
        key = self.combo.currentData()
        hkl = "".join(f"-{-n}" if n < 0 else str(n)
                      for n in surface.parse_miller(self.miller.text()))
        value = f"{key}:{hkl}?layers={self.layers.value()}"
        if not self.auto.isChecked():
            value += f"&repeat={self.nx.value()},{self.ny.value()}"
        if self.term.currentData() is not None:
            value += f"&termination={self.term.currentData()}"
        return "surface", value, f"{key} ({hkl})"


class NanoDialog(_Dialog):
    """Graphene, graphite, nanoribbons, nanotubes and fullerenes."""

    TYPES = (("Graphene sheet", "graphene"), ("Graphite (0001) surface",
                                              "graphite"),
             ("Graphene nanoribbon", "ribbon"),
             ("Graphene quantum dot", "dot"),
             ("Graphene with a defect", "defect"),
             ("Carbon nanotube", "nanotube"), ("Fullerene", "fullerene"))

    def __init__(self, parent=None):
        super().__init__("Graphene, nanotubes & fullerenes", parent)
        self.type = QComboBox()
        for title, key in self.TYPES:
            self.type.addItem(title, key)
        self.form.addRow("Structure", self.type)
        self.width = self._dspin(0.6, 12, 3.0)
        self.depth = self._dspin(0.6, 12, 3.0)
        self.layers = self._spin(1, 6, 1)
        self.stacking = QComboBox()
        self.stacking.addItems(["AB", "ABA", "ABC", "AA"])
        self.twist = self._dspin(0, 30, 0.0, 1.0, 1)
        self.hydrogen = QCheckBox("Cap the edges with hydrogen")
        self.edge = QComboBox()
        self.edge.addItems(["armchair", "zigzag"])
        self.diameter = self._dspin(0.6, 8, 2.0)
        self.defect = QComboBox()
        self.defect.addItems(["vacancy", "nitrogen"])
        self.step = QCheckBox("A monatomic step on the top sheet")
        self.n = self._spin(1, 40, 5)
        self.m = self._spin(0, 40, 5)
        self.length = self._dspin(0.6, 12, 3.0)
        self.walls = self._spin(1, 4, 1)
        self.fuller = QComboBox()
        self.fuller.addItems(["c20", "c60", "c70", "c80", "c120", "c200"])
        self.fuller.setCurrentText("c60")
        self._rows = {
            "width": ("Width (nm)", self.width),
            "depth": ("Depth (nm)", self.depth),
            "layers": ("Layers", self.layers),
            "stacking": ("Stacking", self.stacking),
            "twist": ("Twist of layer 2 (°)", self.twist),
            "hydrogen": ("", self.hydrogen),
            "edge": ("Edge", self.edge),
            "diameter": ("Diameter (nm)", self.diameter),
            "defect": ("Defect", self.defect),
            "step": ("", self.step),
            "n": ("Chirality n", self.n),
            "m": ("Chirality m", self.m),
            "length": ("Length (nm)", self.length),
            "walls": ("Walls", self.walls),
            "fuller": ("Cage", self.fuller),
        }
        self._labels = {}
        for key, (text, w) in self._rows.items():
            lab = QLabel(text)
            self._labels[key] = lab
            self.form.addRow(lab, w)
        self.type.currentIndexChanged.connect(self._sync)
        for w in (self.n, self.m, self.walls):
            w.valueChanged.connect(self._update)
        self._sync()

    #: which parameter rows each structure shows
    SHOWS = {
        "graphene": ("width", "depth", "layers", "stacking", "twist",
                     "hydrogen"),
        "graphite": ("width", "depth", "layers", "step"),
        "ribbon": ("edge", "width", "length"),
        "dot": ("diameter",),
        "defect": ("defect", "width", "depth"),
        "nanotube": ("n", "m", "length", "walls", "hydrogen"),
        "fullerene": ("fuller",),
    }

    def _sync(self, *_):
        kind = self.type.currentData()
        for key, (_t, w) in self._rows.items():
            show = key in self.SHOWS[kind]
            w.setVisible(show)
            self._labels[key].setVisible(show)
        self._update()

    def _update(self, *_):
        kind = self.type.currentData()
        if kind == "nanotube":
            from . import nano
            d = nano.diameter(self.n.value(), self.m.value())
            self.summary.setText(
                f"({self.n.value()},{self.m.value()}) — "
                f"{nano.tube_kind(self.n.value(), self.m.value())}, "
                f"diameter {d:.2f} nm.")
            self.ok_btn.setEnabled(self.n.value() > 0
                                   or self.m.value() > 0)
        else:
            self.summary.setText("")
            self.ok_btn.setEnabled(True)

    def entry(self):
        kind = self.type.currentData()
        p = []
        if kind == "graphene":
            p = [f"width={self.width.value()}", f"depth={self.depth.value()}",
                 f"layers={self.layers.value()}",
                 f"stacking={self.stacking.currentText()}",
                 f"twist={self.twist.value()}",
                 f"hydrogen={int(self.hydrogen.isChecked())}"]
        elif kind == "graphite":
            p = [f"width={self.width.value()}", f"depth={self.depth.value()}",
                 f"layers={self.layers.value()}",
                 f"step={int(self.step.isChecked())}"]
        elif kind == "ribbon":
            p = [f"edge={self.edge.currentText()}",
                 f"width={self.width.value()}",
                 f"length={self.length.value()}"]
        elif kind == "dot":
            p = [f"diameter={self.diameter.value()}"]
        elif kind == "defect":
            p = [f"kind={self.defect.currentText()}",
                 f"width={self.width.value()}", f"depth={self.depth.value()}"]
        elif kind == "nanotube":
            p = [f"n={self.n.value()}", f"m={self.m.value()}",
                 f"length={self.length.value()}",
                 f"walls={self.walls.value()}",
                 f"hydrogen={int(self.hydrogen.isChecked())}"]
        else:
            p = [f"kind={self.fuller.currentText()}"]
        title = self.type.currentText()
        return "nano", f"{kind}?" + "&".join(p), title


class PolymerDialog(_Dialog):
    """A polymer chain: a preset (or your own SMILES repeat unit) repeated
    n times between two end caps."""

    def __init__(self, parent=None, key="polyethylene"):
        super().__init__("Polymer builder", parent)
        self.setMinimumWidth(520)
        self.combo = QComboBox()
        self.combo.setMaxVisibleItems(24)
        for cat in polymers.CATEGORIES:
            for k, v in polymers.PRESETS.items():
                if v[3] == cat:
                    self.combo.addItem(v[0], k)
        self.combo.addItem("Custom repeat unit…", "custom")
        self.combo.setCurrentIndex(max(0, self.combo.findData(key)))
        self.form.addRow("Polymer", self.combo)
        self.unit = QLineEdit()
        self.unit.setToolTip(
            "SMILES of one repeat unit: its first atom bonds to the previous "
            "unit and its last atom to the next — CC for polyethylene, "
            "CC(Cl) for PVC")
        self.form.addRow("Repeat unit", self.unit)
        row = QHBoxLayout()
        self.head, self.tail = QLineEdit(), QLineEdit()
        for lab, w in (("start cap", self.head), ("end cap", self.tail)):
            w.setPlaceholderText("H")
            w.setMaximumWidth(110)
            row.addWidget(QLabel(lab))
            row.addWidget(w)
        row.addStretch(1)
        self.form.addRow("End groups", row)
        self.n = self._spin(1, 200, 8)
        self.form.addRow("Repeat units (n)", self.n)
        self.combo.currentIndexChanged.connect(self._pick)
        for w in (self.unit, self.head, self.tail):
            w.textChanged.connect(self._update)
        self.n.valueChanged.connect(self._update)
        self._pick()

    def _pick(self, *_):
        key = self.combo.currentData()
        custom = key == "custom"
        for w in (self.unit, self.head, self.tail):
            w.setEnabled(custom)
        if not custom:
            _n, unit, n, _c, (head, tail) = polymers.PRESETS[key]
            for w, text in ((self.unit, unit), (self.head, head),
                            (self.tail, tail)):
                w.blockSignals(True)
                w.setText(text)
                w.blockSignals(False)
            self.n.setValue(n)
        elif not self.unit.text():
            self.unit.setText("CC(C)")
        self._update()

    def _update(self, *_):
        unit, head, tail = (self.unit.text().strip(), self.head.text().strip(),
                            self.tail.text().strip())
        try:
            text = polymers.chain_smiles(unit, self.n.value(), head, tail)
            atoms, bonds = smiles.parse_smiles(text)
            atoms, bonds = smiles.add_hydrogens(atoms, bonds)
            if len(atoms) > smiles.MAX_ATOMS:
                raise polymers.PolymerError(
                    f"{len(atoms)} atoms is more than the builder takes "
                    f"({smiles.MAX_ATOMS}) — at most "
                    f"{polymers.max_units(unit, head, tail)} units.")
            self.summary.setText(
                f"{smiles.formula_of(text)} — {len(atoms)} atoms, "
                f"{self.n.value()} × {unit}")
            self.ok_btn.setEnabled(True)
        except (polymers.PolymerError, smiles.SmilesError, ValueError,
                KeyError) as exc:
            self.summary.setText(f"⚠ {exc}")
            self.ok_btn.setEnabled(False)

    def entry(self):
        key = self.combo.currentData()
        n = self.n.value()
        if key != "custom":
            return "polymer", f"{key}?n={n}", self.combo.currentText()
        value = (f"custom?unit={quote(self.unit.text().strip(), safe='')}"
                 f"&n={n}&head={quote(self.head.text().strip(), safe='')}"
                 f"&tail={quote(self.tail.text().strip(), safe='')}")
        return "polymer", value, "Custom polymer"


class ReactionDialog(_Dialog):
    """Write a reaction, balance it, and lay it out in 3D."""

    ok_text = "Show reaction in 3D"

    def __init__(self, parent=None, equation=""):
        super().__init__("Reaction builder", parent)
        self.setMinimumWidth(560)
        self.examples = QComboBox()
        self.examples.addItem("— choose a classic reaction —", "")
        for name, eq in reactions.EXAMPLES.items():
            self.examples.addItem(name, eq)
        self.form.addRow("Examples", self.examples)
        self.text = QLineEdit(equation or "CH4 + O2 -> CO2 + H2O")
        self.text.setToolTip(
            "Species are compound names or formulas (H2O, NH4+, SO4^2-), an "
            "element (Fe), or smiles:CCO. Arrows: ->  <=>  →  ⇌")
        self.form.addRow("Equation", self.text)
        self.balance = QCheckBox("Balance the coefficients for me")
        self.balance.setChecked(True)
        self.form.addRow("", self.balance)
        self.report = QPlainTextEdit()
        self.report.setReadOnly(True)
        self.report.setMaximumHeight(150)
        self.form.addRow("Result", self.report)
        self.examples.currentIndexChanged.connect(self._pick)
        self.text.textChanged.connect(self._update)
        self.balance.toggled.connect(self._update)
        self._update()

    def _pick(self, _i):
        eq = self.examples.currentData()
        if eq:
            self.text.setText(eq)

    def _update(self, *_):
        try:
            rx = reactions.solve(self.text.text(), self.balance.isChecked())
        except (BuildError, ValueError, ZeroDivisionError) as exc:
            self.report.setPlainText(f"⚠ {exc}")
            self.ok_btn.setEnabled(False)
            return
        lines = [rx.equation, ""]
        lines.append("Balanced: atoms and charge agree on both sides."
                     if rx.balanced else "NOT balanced — check the table:")
        for el, (a, b) in rx.table.items():
            mark = "" if a == b else "   ← differs"
            lines.append(f"  {el:>7}: {a:g} → {b:g}{mark}")
        self.report.setPlainText("\n".join(lines))
        self.ok_btn.setEnabled(True)

    def entry(self):
        eq = self.text.text().strip()
        if self.balance.isChecked():
            try:
                eq = reactions.solve(eq, True).source
            except (BuildError, ValueError):
                pass
        return "reaction", eq, eq
