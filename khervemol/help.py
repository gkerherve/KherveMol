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
<li><b>3D View</b> — an interactive OpenGL model. Atoms are lit CPK
spheres; bonds are sticks (single / double / triple). Crystals show their
unit cell as an outline.</li>
<li><b>2D Sketch</b> — a proper <i>skeletal</i> structural formula (line
bonds, carbons as vertices, heteroatoms lettered, hydrogens implicit).
Loading or building a molecule mirrors it here automatically.</li>
</ul>

<h3>How the 2D and 3D tabs relate</h3>
<ul>
<li>They are two <b>views of the same molecule</b> in different styles: 3D
is ball-and-stick, 2D is a skeletal formula.</li>
<li>Loading a molecule, building from SMILES/the Explorer, or editing atoms
in 3D <b>updates the 2D sketch automatically</b>.</li>
<li>The 2D → 3D direction is <b>not</b> automatic (a flat drawing has no 3D
shape until it's computed). When you've drawn or edited the 2D sketch, use
<b>Structure ▸ Build 3D from 2D sketch</b> (Ctrl+B, or right-click ▸ Build
3D) to generate the matching 3D model. That's why the 3D can look
different until you run it.</li>
</ul>

<h3>Right-click menus</h3>
<p>Right-click the <b>3D view</b> for standard views, reset zoom, labels,
delete atom, Properties, Copy SMILES, flatten to 2D and export. Right-click
the <b>2D sketch</b> to build 3D from it, switch tools, toggle labels, clear
or export.</p>

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
<li><b>Bend</b> — drag a selected atom to adjust a bond angle. With
<i>Lock lengths</i> on (the default) every bond is held at its real
chemical length (C–O 1.43 Å, C=O 1.23 Å, C–H 1.09 Å …), so the bond
swings around rather than stretching; the status line reads out the live
lengths. Untick it to move an atom freely.</li>
<li><b>Right-click a bond</b> — set it <i>Single</i> / <i>Double</i> /
<i>Triple</i>, or delete it. The bond is re-lengthened to match (a C–O
single shortens to a C=O double), and orders the two atoms' valences
cannot carry are greyed out.</li>
<li><b>Right-click an atom</b> — <i>Bond on</i> ▸ pick an element to
attach it, or double/triple-bond it on. Only elements that fit the
remaining valence are offered. The submenu ends with <i>Select an atom on
screen…</i>, which bonds to whichever atom you click next (Esc cancels).</li>
<li><b>Bond two existing atoms</b> — click one, <b>Ctrl+click</b> the
other, then <i>Bond selected</i> (or right-click ▸ <i>Bond C0–C1</i>).
Separate fragments are pulled to the correct bond length, the smaller one
sliding in with its geometry intact.</li>
<li><b>Tab / Shift+Tab</b> — step the selection through the atoms, to reach
one hidden behind another.</li>
<li><b>Delete</b> — select an atom and press Delete (or the button).</li>
<li><b>Labels</b> — toggle element symbols on the spheres.</li>
<li><b>Atom colour…</b> — recolour the selected atom. On a molecule the
colour rides on that atom; on a crystal it recolours every atom of the same
element <b>and lattice site</b>.</li>
<li><b>Legend</b> — a colour key beside the structure, one lit sphere per
element and site. It is included in the PNG and SVG export.</li>
<li><b>Polyhedra</b> — translucent coordination polyhedra: for every atom
with four or more bonded neighbours, the faces those neighbours span (the
VESTA look — perovskite's TiO<sub>6</sub> octahedra, diamond's tetrahedra).
Greyed out when nothing is ≥4-coordinate.</li>
</ul>

<h3>Crystals &amp; unit cells</h3>
<p>The <b>Crystal</b> menu holds the cubic family (simple cubic, BCC, FCC,
HCP, diamond, NaCl, CsCl, zinc blende, fluorite, perovskite) and the six
non-cubic <b>lattice systems</b> — tetragonal, orthorhombic, hexagonal,
rhombohedral, monoclinic and triclinic — built from their lattice
parameters <i>a, b, c, α, β, γ</i>, which the status line shows.</p>
<p>A body- or face-centre atom of the same element as the corners would be
invisible against them, so those hidden sites are <b>tinted</b>: blue for a
body centre, salmon for a face centre, violet for an interior tetrahedral
site, green for HCP's middle layer. The legend names them.</p>
<ul>
<li><b>Stack</b> — <i>Crystal ▸ Stack unit cells…</i> (Ctrl+U), or the
<b>Supercell</b> boxes under the view, repeat the cell up to 12 times along
each lattice vector. Cells stack along their <i>own</i> vectors, so a
hexagonal or monoclinic supercell leans the way the crystal really does.
Atoms, bonds and cell edges shared between neighbours are drawn once.</li>
<li><b>Tilt</b> — click an atom, then use the <b>Tilt cell</b> boxes to
rotate its unit cell. The rest of that cell is outlined in orange, so you
can see which cell will move before you turn the boxes; your atom stays
selected as you turn them, so each further turn rotates the same cell.
A tilt is a <b>defect, not a detached grain</b>: the tilted cell shares its
corner and face atoms with its neighbours, so they deform to follow and the
lattice stays connected — nothing is duplicated, and a cell no tilted
neighbour touches does not move at all.</li>
<li><b>Right-click a crystal</b> for the same actions on the cell you
clicked.</li>
</ul>

<h3>Structure outline</h3>
<p>The <b>Structure</b> dock, above the library, shows the molecule as a
connectivity tree. The backbone runs straight down the panel and only real
branches indent — hydrogens, side groups and ring closures nest under the
atom they hang off. Every row carries its bond <b>order</b>, <b>length</b>
(Å) and the <b>bond angle</b> at its parent; hover for coordinates, free
valence and the ideal length. Ring bonds appear as a leaf (<i>↻ closes ring
to C5</i>), and disconnected fragments each branch off the root.</p>
<ul>
<li>Click a row to select that atom in 3D, and vice versa.</li>
<li><b>Drag a row onto another</b> to re-bond that atom — everything
hanging off it comes along and swings onto a free direction of the new
anchor. Chemically impossible drops show a "no" cursor.</li>
</ul>

<h3>Dragging from the library</h3>
<p>Double-click a library leaf to load it, or <b>drag</b> it onto either
view. Dropped on the <b>3D view</b> it merges in as a second, unbonded
fragment parked clear of the current structure — Ctrl+click an atom in each
and press <i>Bond selected</i> to join them. Dropped on the <b>2D
sketch</b> it lands where you let go. An empty 3D view, or a crystal, is
replaced rather than merged.</p>

<h3>2D Sketch</h3>
<p>The sketch mirrors the 3D model automatically, but you can also draw
freely:</p>
<ul>
<li><b>Draw</b> — drag from an atom to another to bond them, or drag to
empty space to spawn a new atom (of the active element) bonded to it.
Click empty space to drop a lone atom. Click an existing bond to cycle
single → double → triple.</li>
<li><b>Move</b> — drag an atom to move its <b>whole molecule</b>. <b>Atom</b>
— click to re-label an atom to the active element. <b>Erase</b> — click an
atom or bond to remove it.</li>
<li><b>Show as</b> — draw the same graph as a <i>Skeletal</i> formula (the
default), a <i>Structural formula</i> with every atom lettered, a
<i>Lewis structure</i> with lone-pair dots on the sides no bond is using,
or the <i>Condensed formula</i> alone. Lewis and condensed are views, so
the drawing tools switch off there; SVG export follows the mode.</li>
</ul>
<p>The formula in the status bar counts the hydrogens a skeletal drawing
leaves implicit, so a C–C–O sketch reads C<sub>2</sub>H<sub>6</sub>O rather
than C<sub>2</sub>O.</p>
<p>New bonds snap to a fixed length and 30° angles, so hand-drawn chains
keep tidy (≈120°) geometry. The sketch also <b>enforces valence</b>: it
won't add or raise a bond beyond what an atom can hold (oxygen stops at two
bonds), so you can't draw chemically impossible structures.</p>

<h4>Assembling molecules</h4>
<p>The 2D sketch is a multi-molecule canvas — build compounds by combining
pieces:</p>
<ul>
<li><b>Drag a compound from the library</b> onto the sketch to drop it in as
a new molecule (drag several to place them side by side).</li>
<li><b>Move</b> each molecule around independently.</li>
<li><b>Draw</b> from an atom in one molecule to an atom in another to
<b>bond them together</b> (valence permitting).</li>
<li><b>Erase</b> a bond to <b>break</b> a molecule into pieces, which you
can then move apart or re-bond.</li>
</ul>
<p>Use <b>Structure ▸ Build 3D from 2D sketch</b> (Ctrl+B) to turn what
you've assembled into a 3D model.</p>

<h3>Library &amp; elements</h3>
<ul>
<li>The <b>left library tree</b> lists everything KherveMol can build,
in sections: <b>Molecules</b> (700+ — gases, acids, salts, oxides, VSEPR
shapes, hydrocarbons, aromatics, biomolecules, medicines…),
<b>Crystals</b> (120+), <b>Surfaces</b> (60 ready faces), <b>Graphene,
nanotubes &amp; fullerenes</b>, <b>Reactions</b> (36 classics) and the
original <b>Classic 3D models</b>. Everything builds without RDKit — a
built-in SMILES parser and 3D embedder does the work (RDKit takes over
when installed, for force-field-cleaned geometry). The <b>Explorer</b>
(Ctrl+L) is the same list with search and a preview.</li>
<li>The <b>periodic-table dock</b> along the bottom shows the whole table
(all 118 elements, CPK-coloured with atomic numbers). Click one to make it
the <b>active element</b>. This drives both the 2D sketch and the 3D
builder: in the 3D view, select an atom then click the <b>＋<i>El</i></b>
button (or right-click ▸ <i>Add …</i>) to bond an atom of <i>any</i>
element on — not just the ten quick buttons. Every element in the table
can be added: it bonds where chemistry allows (including Xe/Kr compounds),
otherwise it's dropped in as a free atom (e.g. the inert He/Ne/Ar). Toggle
the dock from <i>View</i>.</li>
</ul>

<h3>Molecule Explorer</h3>
<p><b>Molecule ▸ Explorer…</b> (Ctrl+L, or the magnifier on the toolbar)
opens one searchable browser of every molecule, crystal, surface,
nanostructure and reaction. Type in the search box to filter by name,
formula or family, pick an entry to preview it in 3D, then <b>Build in
3D</b>.</p>

<h3>Toolbars</h3>
<p>Two rows of icon buttons hold every way to make a structure. The
<b>top row</b> has the file operations, the Explorer and SMILES, then one
split button per library — <b>Molecules, Polymers, Crystals, Surfaces,
Carbon, Reactions</b>: click the icon for that library's builder, the arrow
to pick straight from the list (the same lists as the menus and the tree).
The <b>second row</b> holds the drawing tools: <b>2D</b> Draw / Move / Atom /
Erase and Clear, the active <b>Element</b>, and the <b>3D</b> builder — Add
atom, Single / Double / Triple, Bond, Delete, Labels, Lock — plus 3D → 2D,
2D → 3D and the reaction <b>Animate</b> / <b>Equation</b>. Buttons grey out
when they do not apply.</p>

<h3>Polymers</h3>
<p><b>Polymer ▸ Polymer builder…</b> (Ctrl+Shift+P) repeats a unit <i>n</i>
times: 40 presets (PE, PP, PVC, PTFE, PS, PMMA, rubbers, PEO, PET, PLA,
nylons, Kevlar, silicone, polythiophene…) or a custom SMILES repeat unit
(first atom bonds to the previous unit, last atom to the next — e.g.
<code>CC(Cl)</code> for PVC). Ends are hydrogen-capped unless you give end
groups. Up to about 400 atoms.</p>

<h3>Crystals, surfaces and carbon nanostructures</h3>
<p>The <b>Crystal</b> menu opens three builders (their entries are also in
the library tree):</p>
<ul>
<li><b>Crystal builder…</b> (Ctrl+Shift+C) — any of 120+ crystals, and how
many unit cells to show along a, b and c. The block is drawn with its cell
outline and the bonds between nearest neighbours; atoms on a cell face are
drawn in every cell that shares it (untick for the true cell contents). The
summary gives the space group, lattice, atoms per cell and density.</li>
<li><b>Surface builder…</b> (Ctrl+Shift+F) — a slab of any crystal cut
along any plane: type Miller indices (<code>111</code>, <code>1 1 0</code>,
<code>1-10</code>) or four hexagonal indices (<code>0001</code>,
<code>10-10</code>), then cells, layers and <i>termination</i> (automatic =
the widest gap between planes, breaking the fewest bonds). Slabs are
bulk-terminated: no relaxation or reconstruction.</li>
<li><b>Graphene, nanotubes &amp; fullerenes…</b> (Ctrl+Shift+G) — graphene
sheets (1–6 layers, AB / ABA / ABC / AA or twisted), graphite surfaces, armchair
and zigzag nanoribbons, quantum dots, a vacancy or nitrogen doping, (n,m)
nanotubes, single- or multi-walled, and C20 / C60 / C70 / C80 … cages.</li>
</ul>
<p>Crystals, surfaces and sheets are fixed lattices: they rotate and zoom
but their atoms are not editable.</p>

<h3>Reactions</h3>
<p><b>Reaction ▸ Reaction builder…</b> (Ctrl+R) takes an equation and draws
it in 3D. Write <code>2 H2 + O2 -&gt; 2 H2O</code>, <code>CH4 + 2 O2 -&gt;
CO2 + 2 H2O</code> or <code>N2 + 3 H2 &lt;=&gt; 2 NH3</code> (arrows
<code>-&gt; =&gt; → &lt;=&gt; ⇌ =</code> with a space each side; spaces round
each <code>+</code>). Species are compound names or formulas
(<code>H2O</code>, <code>ethanol</code>, <code>NH4+</code>,
<code>SO4^2-</code>), an element (<code>Fe</code>, <code>Na+</code>) or
<code>smiles:CCO</code>.</p>
<ul>
<li>With <i>Balance the coefficients for me</i> ticked, KherveMol finds the
smallest whole coefficients that conserve every element <b>and the
charge</b> (coefficients you give are kept). Untick it to check your own —
the table shows any element that differs.</li>
<li>The scene puts the molecules left to right (a coefficient up to 6 draws
that many copies), with plus signs, the arrow (double for ⇌) and the formula
under each species. It is read-only; rotate and zoom as usual.</li>
<li><b>Animate</b> (row under the 3D view) plays the reaction as a film:
reactants approach, their atoms travel to the product positions as bonds
break and form, and the products separate. Atoms are matched to keep as many
bonds as possible. Scrub with the slider, pause, loop, or change the speed;
<b>■ Equation</b> returns to the static scene. (No film for fractional
coefficients.)</li>
<li><b>Reaction ▸ Classic reactions</b> holds 36 examples — combustion,
photosynthesis, Haber and contact processes, neutralisation, esterification,
thermite…</li>
</ul>

<h3>3D rendering</h3>
<p>The 3D view is drawn with <b>OpenGL</b>: per-pixel lit spheres and
cylinders with specular highlights, a rim light, depth fog and 4×
anti-aliasing; each bond is drawn in halves coloured by its two atoms.
<b>View ▸ 3D renderer</b> switches to the <i>Classic</i> vector renderer
(used automatically where OpenGL is not available). <b>View ▸ 3D style</b>
chooses <i>Ball &amp; stick</i>, <i>Space filling</i> or <i>Sticks</i>.
<b>Export PNG</b> renders the current view at 1600 × 1200.</p>

<h3>Properties</h3>
<p><b>Molecule ▸ Properties…</b> (Ctrl+I) shows the current molecule's
formula, molecular weight and atom counts — these always work. With
<b>RDKit</b> installed it adds exact mass, LogP, TPSA, H-bond donors and
acceptors, rotatable bonds, ring counts, the canonical SMILES and the
InChI / InChIKey. Crystals are reported as a unit-cell composition.</p>

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
flat depiction into the 2D sketch. Without RDKit the built-in builder does
this too.</li>
<li><b>Import structure file…</b> — open a <code>.mol</code>,
<code>.sdf</code> or <code>.pdb</code> file.</li>
<li><b>Copy SMILES of structure</b> — best-effort canonical SMILES of the
current model, to the clipboard.</li>
</ul>
<p>Everything else works without RDKit; only structure-file import and
<i>Copy SMILES</i> need it.</p>

<h3>Files</h3>
<ul>
<li><b>Save / Open</b> — the native <code>.kmol</code> format stores the
3D model, its orientation, a reaction's annotations, and the 2D
sketch.</li>
<li><b>Export PNG</b> — an image of the current tab (the 3D view at
1600 × 1200 through the active renderer).</li>
<li><b>Export SVG (KhervePaint)</b> (Ctrl+Shift+E) — writes an SVG that
<b>opens in KhervePaint</b> as native, editable items: each atom becomes a
gradient-filled ellipse and each bond a line. Exports the 3D ball-and-stick
or the 2D skeletal formula, depending on the active tab.</li>
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
