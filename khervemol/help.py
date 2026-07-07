"""About dialog and in-app User Guide.

Keep the guide and the repo USERGUIDE.md in sync when features change.

Copyright (C) 2026 Gwilherm Kerherve

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
"""

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (QDialog, QDialogButtonBox, QHBoxLayout, QLabel,
                             QTextBrowser, QVBoxLayout)

from . import __version__, icons

_GUIDE = """
<h2>KherveMol — User Guide</h2>
<p>KherveMol draws chemical compounds and crystal structures in 3D and 2D.
Everything you build stays as ordinary vector geometry you can export.</p>

<h3>The two tabs</h3>
<ul>
<li><b>3D View</b> — an interactive ball-and-stick model. Atoms are lit
CPK spheres; bonds are sticks (single / double / triple). Crystals are
drawn as wireframe unit cells.</li>
<li><b>2D Sketch</b> — a flat editor drawn in the <i>same</i> ball-and-stick
style as the 3D view. Loading or building a molecule mirrors it here
automatically, so both tabs always show the same structure.</li>
</ul>

<h3>3D View</h3>
<ul>
<li><b>Rotate</b> — drag the background; or snap to a face with the
<i>view cube</i> buttons (Front / Back / Left / Right / Top / Bottom /
Isometric).</li>
<li><b>Zoom</b> — mouse wheel; <i>Reset zoom</i> refits.</li>
<li><b>Bond length</b> — the slider spreads the atoms apart.</li>
<li><b>Build</b> — click an atom to select it (green ring), then click an
element in the <i>Add atom</i> palette to bond a new atom on. The builder
respects each element's valence and refuses to over-bond. Pick the bond
order (single/double/triple) first.</li>
<li><b>Bend</b> — drag a selected atom to adjust a bond angle.</li>
<li><b>Delete</b> — select an atom and press Delete (or the button).</li>
<li><b>Labels</b> — toggle element symbols on the spheres.</li>
</ul>

<h3>2D Sketch</h3>
<p>The sketch mirrors the 3D model automatically, but you can also draw
freely:</p>
<ul>
<li><b>Draw</b> — drag from an atom to another to bond them, or drag to
empty space to spawn a new atom (of the active element) bonded to it.
Click empty space to drop a lone atom. Click an existing bond to cycle
single → double → triple.</li>
<li><b>Move</b> — drag atoms. <b>Atom</b> — click to re-label an atom to
the active element. <b>Erase</b> — click an atom or bond to remove it.</li>
</ul>

<h3>Library &amp; elements</h3>
<ul>
<li><b>Molecule</b> and <b>Crystal</b> menus (and the left library tree)
load 30+ ready-made structures — small molecules, alcohols &amp; acids,
hydrocarbons, polymers, and crystal unit cells (SC, BCC, FCC, HCP,
diamond, NaCl, CsCl, zinc blende, fluorite, perovskite).</li>
<li>The <b>periodic-table dock</b> along the bottom shows the whole table
(all 118 elements, CPK-coloured with atomic numbers); click one to make it
the active drawing element. Toggle the dock from <i>View</i>.</li>
</ul>

<h3>Molecule Explorer</h3>
<p><b>Molecule ▸ Explorer…</b> (Ctrl+L, or the magnifier on the toolbar)
opens a searchable browser of structures: the built-in 3D models plus
~120 named compounds (solvents, drugs, amino acids, sugars, aromatics,
nucleobases, functional groups…). Type in the search box to filter by
name, pick an entry to preview it, then <b>Build in 3D</b>. The built-in
models build with or without RDKit; the named compounds need RDKit.</p>

<h3>AI Chat</h3>
<p>The <b>robot</b> button on the toolbar (or <i>View ▸ AI Chat</i>) opens
an assistant that answers chemistry questions and can draw molecules. Click
the <b>⚙</b> to pick a provider (Claude, ChatGPT, Mistral, Ollama, or a
local server), a model, and your API key. Then ask things like <i>"what is
a hydrogen bond?"</i> or <i>"draw caffeine"</i> — when it suggests a
molecule it returns a SMILES that KherveMol renders into the 3D view and 2D
sketch automatically (RDKit needed for rendering). Requests run in the
background, so a slow or failed reply never freezes the app — any error
appears as a red line in the chat.</p>

<h3>SMILES &amp; structure files (RDKit)</h3>
<p>If <b>RDKit</b> is installed (<code>pip install rdkit</code>), the
<b>Molecule</b> menu unlocks:</p>
<ul>
<li><b>From SMILES…</b> — type a SMILES string (e.g. <code>CCO</code>,
<code>c1ccccc1</code>, <code>CC(=O)O</code>) and KherveMol embeds a real
3D conformer (with hydrogens, force-field cleaned) into the 3D view and a
flat depiction into the 2D sketch.</li>
<li><b>Import structure file…</b> — open a <code>.mol</code>,
<code>.sdf</code> or <code>.pdb</code> file.</li>
<li><b>Copy SMILES of structure</b> — best-effort canonical SMILES of the
current model, to the clipboard.</li>
</ul>
<p>Everything else works without RDKit; the menu items say when it's
needed.</p>

<h3>Files</h3>
<ul>
<li><b>Save / Open</b> — the native <code>.kmol</code> format stores the
3D model, its orientation, and the 2D sketch.</li>
<li><b>Export PNG</b> — a flattened image of the current tab.</li>
</ul>
"""


class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("About KherveMol")
        self.setMinimumWidth(440)
        layout = QVBoxLayout(self)
        top = QHBoxLayout()
        logo = QLabel()
        logo.setPixmap(icons.app_icon().pixmap(72, 72))
        top.addWidget(logo)
        text = QLabel(
            f"<h2>KherveMol</h2><p>Version {__version__}</p>"
            "<p>Draw chemical compounds and crystal structures in 2D and "
            "3D — a native app in the Kherve family.</p>"
            "<p>© 2026 Gwilherm Kerherve — GPL-3.0</p>")
        text.setWordWrap(True)
        text.setTextInteractionFlags(Qt.TextBrowserInteraction)
        text.setOpenExternalLinks(True)
        top.addWidget(text, 1)
        layout.addLayout(top)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)


class GuideDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("KherveMol — User Guide")
        self.setMinimumSize(620, 560)
        layout = QVBoxLayout(self)
        browser = QTextBrowser()
        browser.setHtml(_GUIDE)
        browser.setOpenExternalLinks(True)
        layout.addWidget(browser)
        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)
