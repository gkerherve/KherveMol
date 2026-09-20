# KherveMol — User Guide

KherveMol draws chemical compounds and crystal structures in 3D and 2D.
Everything you build stays as ordinary vector geometry you can export.

## The two tabs

- **3D View** — an interactive ball-and-stick model. Atoms are lit CPK
  spheres; bonds are sticks (single / double / triple). Crystals are drawn
  as wireframe unit cells.
- **2D Sketch** — a proper *skeletal* structural formula (line bonds,
  carbons as vertices, heteroatoms lettered, hydrogens implicit). Loading or
  building a molecule mirrors it here automatically; you can also draw
  freely.

**How the tabs relate.** They are two views of the *same* molecule: 3D is
ball-and-stick, 2D is a skeletal formula. Loading a molecule, building from
SMILES/the Explorer, or editing atoms in 3D updates the 2D automatically.
The reverse isn't automatic — a flat drawing has no 3D shape until it's
computed — so after drawing/editing the 2D sketch, run **Structure ▸ Build
3D from 2D sketch** (Ctrl+B, or right-click ▸ Build 3D) to regenerate the
matching 3D model. Both views also have **right-click menus**.

## 3D View

- **Rotate** — drag the background, or snap to a face with the *view cube*
  buttons (Front / Back / Left / Right / Top / Bottom / Isometric).
- **Zoom** — mouse wheel; *Reset zoom* refits the model.
- **Bond length** — the slider spreads the atoms apart.
- **Build** — click an atom to select it (green ring), then click an
  element in the **Add atom** palette to bond a new atom on. The builder
  respects each element's valence and refuses to over-bond. Choose the
  bond order (single / double / triple) first.
- **Bend** — drag a selected atom to adjust a bond angle. With **Lock
  lengths** on (the default) every bond is held at its real chemical length
  — C–O 1.43 Å, C=O 1.23 Å, C–H 1.09 Å, C≡N 1.16 Å … — so dragging swings
  the bond around instead of stretching it, and the status line reads out
  the live lengths. Untick it to move an atom freely.
- **Right-click a bond** — set it **Single** / **Double** / **Triple**, or
  delete it. The bond is re-lengthened to match (a C–O single contracts to
  a C=O double, pulling the smaller side of the molecule with it). Orders
  neither atom has the free valence for are greyed out.
- **Right-click an atom** — **Bond on** ▸ pick an element to attach it, or
  double/triple-bond it on. Only elements that fit the atom's remaining
  valence are listed; the element selected in the periodic table is offered
  too. The same submenu ends with **Select an atom on screen…**, which lets
  you click the *other* atom to bond to (Esc cancels).
- **Bond two atoms that already exist** — click one, **Ctrl+click** the
  other (it gets a lighter ring), then press **Bond selected** — or
  right-click either one and choose **Bond C0–C1**. The two are pulled to
  the correct length: if they are separate fragments, the smaller one slides
  along the new bond axis, keeping its own geometry; closing a ring moves
  nothing.
- **Tab / Shift+Tab** — step the selection from atom to atom, so you can
  reach an atom hidden behind another.
- **Delete** — select an atom and press **Delete** (or the button).
- **Labels** — toggle element symbols on the spheres.

- **Atom colour…** — select an atom and recolour it. On a molecule the
  colour rides on that one atom; on a crystal it recolours every atom of
  the same element **and lattice site** (a lattice is rebuilt on every
  draw, so its colours are stored as a rule, not on the atoms).
- **Legend** — a colour key beside the structure, one lit sphere per
  element and site. It is part of the PNG and SVG export.
- **Polyhedra** — translucent coordination polyhedra: for every atom with
  four or more bonded neighbours, the faces those neighbours span. This is
  the VESTA-style view — perovskite's TiO₆ octahedra, diamond's tetrahedra.
  The button is greyed out when nothing is ≥4-coordinate.

Crystals are fixed lattices: rotatable, zoomable, recolourable and
stackable, but not atom-editable.

## Crystals & unit cells

The **Crystal** menu holds two families:

- **Crystal structures** — the cubic family and its relatives: simple
  cubic, BCC, FCC, HCP, diamond, NaCl, CsCl, zinc blende, fluorite and
  perovskite, drawn as wireframe unit cells.
- **Lattice systems** — the six non-cubic systems (tetragonal,
  orthorhombic, hexagonal, rhombohedral, monoclinic, triclinic), built
  from their lattice parameters *a, b, c, α, β, γ*. The status line shows
  those parameters.

A body- or face-centre atom of the same element as the corners would be
invisible against them, so those **hidden sites are tinted** — blue for a
body centre, salmon for a face centre, violet for an interior tetrahedral
site, green for HCP's middle layer. The legend names them.

### Stacking

**Crystal ▸ Stack unit cells…** (Ctrl+U), or the **Supercell** boxes under
the 3D view, repeat the cell up to 12 times along each lattice vector.
Cells stack along their *own* vectors, so a hexagonal or monoclinic
supercell leans the way the crystal really does rather than sitting on a
square grid. Atoms, bonds and cell edges shared between neighbouring cells
are drawn once, so corners don't pile up.

Every atom knows which cell it belongs to — click one and the status line
names its cell.

### Tilting a cell

The **Tilt cell** boxes rotate the unit cell of the selected atom about
x, y and z. A tilt is a **defect, not a detached grain**: the tilted cell
shares its corner and face atoms with its neighbours, so those neighbours
deform to follow it and the lattice stays connected. Nothing is
duplicated, and a cell no tilted neighbour touches does not move at all.

Click an atom of the cell you want to tilt first. The rest of that cell is
then **outlined in orange**, so you can see which cell the boxes will
rotate before you turn them — a corner is shared between neighbouring
cells, and the outline says which of them counts as yours. The boxes show
that cell's current tilt.

Your selected atom **stays selected** as you turn the boxes: a tilt moves
atoms but never renumbers them, so the green ring stays on the atom you
picked and each further turn keeps rotating the same cell. **Reset tilts**
straightens everything.

Right-clicking a crystal offers the same actions on the cell you clicked.

## 2D Sketch

- **Draw** — drag from an atom to another atom to bond them, or drag to
  empty space to spawn a new atom (of the active element) bonded to it.
  Click empty space to drop a lone atom. Click an existing bond to cycle
  single → double → triple.
- **Move** — drag an atom to move its **whole molecule**.
- **Atom** — click an atom to re-label it to the active element.
- **Erase** — click an atom (removes it and its bonds) or a bond.
- **Show as** — how the same graph is drawn:
  - **Skeletal** (default) — bond lines, carbons as implicit vertices,
    heteroatoms lettered, hydrogens implied.
  - **Structural formula** — every atom lettered, hydrogens included.
  - **Lewis structure** — the structural drawing plus lone-pair dots,
    placed on the sides of each atom that no bond is using.
  - **Condensed formula** — the molecular formula alone.

  Lewis and condensed are *views*: the drawing tools switch off there, so
  a click can't move an atom you can no longer see. Switch back to
  Skeletal or Structural to keep editing. SVG export follows the mode.

The formula in the status bar counts the hydrogens a skeletal drawing
leaves implicit, so a C–C–O sketch reads C₂H₆O rather than C₂O.
- **All labels** shows every atom's symbol (including carbons); **Clear**
  empties the sketch.

New bonds snap to a fixed length and 30° angles, so hand-drawn chains keep
tidy (~120°) geometry. The sketch also **enforces valence** — it won't add
or raise a bond past what an atom can hold (oxygen stops at two bonds,
carbon at four), so you can't draw chemically impossible structures.

### Assembling molecules

The 2D sketch is a multi-molecule canvas:

- **Drag a compound from the library** onto the sketch to drop it in as a
  new molecule — drag several to place them side by side.
- **Move** each molecule independently.
- **Draw** from an atom in one molecule to an atom in another to **bond them
  together** (valence permitting).
- **Erase** a bond to **break** a molecule into pieces, then move them apart
  or re-bond.

Then **Structure ▸ Build 3D from 2D sketch** (Ctrl+B) turns what you've
assembled into a 3D model.

## Library & elements

- The **left library tree** lists everything KherveMol can build, in
  sections: **Molecules** (700+: gases, acids, salts, oxides, VSEPR
  shapes, hydrocarbons, aromatics, biomolecules, medicines…),
  **Crystals** (120+), **Surfaces** (60 ready faces), **Graphene,
  nanotubes & fullerenes**, **Reactions** (36 classics) and the original
  **Classic 3D models** (including the six non-cubic lattice
  systems with their supercell, tilt and colour tools). Everything builds without RDKit — a built-in
  SMILES parser and 3D embedder does the work (RDKit takes over when it is
  installed, for force-field-cleaned geometry). The **Explorer** (Ctrl+L)
  is the same list with search and a preview.
- **Double-click** a leaf to load it, or **drag** it onto either view:
  - onto the **3D view**, it merges in as a second, unbonded fragment,
    parked clear of what's already there — then Ctrl+click an atom in each
    and press **Bond selected** to join them. An empty view (or a crystal)
    is simply replaced, since a lattice has no room for a guest molecule.
  - onto the **2D sketch**, it drops where you let go, as a new fragment.
- The **periodic-table dock** along the bottom shows the whole table (all
  118 elements, CPK-coloured with atomic numbers). Click one to set the
  **active element** (header shows its name, Z and valence). It drives both
  tabs: in the 3D view, select an atom and click the **＋*El*** button (or
  right-click ▸ *Add …*) to bond an atom of **any** element on — not just
  the ten quick buttons. Toggle the dock from **View**.

## Structure outline

The **Structure dock**, above the library, is the current molecule as a
connectivity tree: the backbone runs straight down the panel, and everything
that hangs off it — hydrogens, side groups, ring closures — nests one level
in. The outline starts at one end of the molecule's longest chain, so a
straight chain reads as a flat list rather than a staircase, and a branch
only indents where the molecule actually branches.

Each row carries the geometry of the bond that reached it: its **order**
(– = ≡), its **length** in ångström, and the **bond angle** at the parent
atom. Hover a row for the atom's atomic number, weight, free valence,
coordinates and how far its bond sits from the ideal length.

- A bond that closes a **ring** cannot nest (it would loop forever), so it
  shows as a greyed leaf: *↻ closes ring to C5*.
- **Disconnected fragments** each get their own branch off the root — which
  is how you spot two pieces that still need bonding together.
- Click a row to select that atom in the 3D view; selecting in 3D scrolls
  the tree to it.
- **Drag one row onto another** to re-bond that atom — everything hanging
  off it comes along, and the fragment swings onto a free direction of its
  new anchor at the right bond length. Drops that chemistry forbids (onto an
  atom with no free valence, or onto something that would travel with the
  atom you're dragging) show a "no" cursor.

Toggle the dock from **View**.

## Molecule Explorer

**Molecule ▸ Explorer…** (Ctrl+L, or the magnifier button) opens one
searchable browser of every structure — molecules, crystals, surfaces,
graphene / nanotubes / fullerenes and reactions. Type in the search box
to filter by name, formula or family, click an entry to preview it in 3D,
then **Build in 3D** to load it (and mirror it into the 2D sketch where
that makes sense).

## Toolbars

Two rows of icon buttons hold every way to make a structure.

**Top row** — file operations (New, Open, Save, PNG, SVG), the **Explorer**
and **SMILES**, then one split button per library: **Molecules**,
**Polymers**, **Crystals**, **Surfaces**, **Carbon** and **Reactions**.
Click the icon to open that library's builder (the Explorer for
Molecules); click the arrow to pick straight from the list. These are the
same lists as the menus and the library tree. Then Properties, AI Chat and
the Guide.

**Second row** — drawing tools:

- **2D**: Draw, Move, Atom and Erase for the sketch (picking one switches to
  the 2D tab), and Clear.
- **Element**: the element drawn or added, in both views (any element from
  the periodic table dock also lands here).
- **3D**: Add atom (bonds the chosen element onto the selected atom),
  Single / Double / Triple bond order, Bond (join the two selected atoms),
  Delete, Labels and Lock lengths.
- **3D → 2D** and **2D → 3D** convert between the views.
- **Animate** / **Equation** play a reaction film and return to the equation.

Buttons grey out when they do not apply — the 3D editing tools on a crystal
or reaction scene, the film buttons on anything but a reaction.

## Polymers

**Polymer ▸ Polymer builder…** (Ctrl+Shift+P) repeats a unit *n* times. Pick
one of 40 presets — polyethylene, polypropylene, PVC, PTFE, polystyrene,
PMMA, PAN, rubbers, PEO, PET, PLA, nylon 6 and 6,6, Kevlar, polyurethane,
polycarbonate, silicone, polythiophene… — or choose *Custom repeat unit…* and
type a SMILES fragment whose first atom bonds to the previous unit and whose
last atom bonds to the next (`CC(Cl)` is PVC). The ends are capped with
hydrogen unless you give end groups. The result is an ordinary molecule you
can rotate, edit and export; up to about 400 atoms (the summary tells you
when *n* is too big).

## Crystals, surfaces and carbon nanostructures

The **Crystal** menu opens three builders (their entries are also in the
library tree):

- **Crystal builder…** (Ctrl+Shift+C) — pick any of 120+ crystals and how
  many unit cells to show along a, b and c. The block is drawn with its
  cell outline, and bonds between nearest neighbours. Atoms on a cell face
  are drawn in every cell that shares it, so the block looks complete;
  untick the option for the true contents of the cell. The summary line
  gives the space group, lattice parameters, atoms per cell and density.
- **Surface builder…** (Ctrl+Shift+F) — cut a slab of any crystal along
  any plane: type Miller indices (`111`, `1 1 0`, `1-10`) or four
  hexagonal indices (`0001`, `10-10`). Leave *size automatically* on, or set
  the number of surface cells and layers. *Termination* picks where the
  cut falls (automatic = the widest gap between planes, which breaks the
  fewest bonds). Slabs are bulk-terminated — no relaxation or
  reconstruction.
- **Graphene, nanotubes & fullerenes…** (Ctrl+Shift+G) — graphene sheets
  (1–6 layers stacked AB / ABA / ABC / AA, or a twisted second layer),
  graphite surfaces (with a step), armchair / zigzag nanoribbons, quantum
  dots, a vacancy or nitrogen doping, single- and multi-walled (n,m)
  nanotubes, and C20 / C60 / C70 / C80 … cages.

Crystals, surfaces and sheets are **fixed lattices**: they rotate and zoom
but their atoms are not editable. Fullerenes are ordinary molecules.

## Reactions

**Reaction ▸ Reaction builder…** (Ctrl+R) takes an equation and draws it
in 3D. Write it as `2 H2 + O2 -> 2 H2O`, `CH4 + 2 O2 -> CO2 + 2 H2O` or
`N2 + 3 H2 <=> 2 NH3`; arrows are `->  =>  →  <=>  ⇌  =` with a space on
each side, and each `+` has spaces round it. Species are compound names or
formulas (`H2O`, `ethanol`, `NH4+`, `SO4^2-`), an element (`Fe`, `Na+`) or
`smiles:CCO`.

- Leave **Balance the coefficients for me** ticked and KherveMol finds the
  smallest whole coefficients that conserve every element **and the
  charge**; give some coefficients yourself and it fills in the rest. Untick
  it to check your own coefficients — the table lists any element that
  differs between the two sides.
- The 3D scene puts the molecules left to right, a coefficient up to 6
  drawing that many copies, with plus signs, the arrow (double for ⇌) and the
  formula under each species. Rotate and zoom as usual; the scene is
  read-only.
- **Animate** (the row under the 3D view) plays the reaction as a film:
  the reactants approach and pack together, their atoms travel to the
  product positions while the reactant bonds break and the product bonds
  form (half-way through the middle phase), and the products separate.
  KherveMol decides which atom becomes which by keeping as many bonds as
  possible, then keeping neighbours together, then the shortest trips — so an
  ethene + H₂ → ethane film keeps the C–C and four C–H bonds and only moves
  the two new hydrogens. Drag the slider to scrub, pause, loop, or change the
  speed; **■ Equation** returns to the equation with its arrow. (Fractional
  coefficients such as ½ O₂ have no film.)
- **Reaction ▸ Classic reactions** and the tree's *Reactions* section hold 36
  examples: combustion, photosynthesis, Haber and contact processes,
  neutralisation, esterification, thermite, and more.

## 3D rendering

The 3D view is drawn with **OpenGL**: per-pixel lit spheres and cylinders
with specular highlights, a rim light, depth fog and 4× anti-aliasing;
each bond is drawn in halves coloured by its two atoms. **View ▸ 3D
renderer** switches to the *Classic* vector renderer (always available, and
used automatically where OpenGL is not). **View ▸ 3D style** (or the Style
box under the view) chooses *Ball & stick*, *Space filling* or *Sticks*.
**Export PNG** renders the current view at 1600 × 1200 with the same
renderer.

## Properties

**Molecule ▸ Properties…** (Ctrl+I) opens a table of the current molecule's
properties. Formula, molecular weight and atom counts always work. With
RDKit installed it adds exact mass, LogP, TPSA, H-bond donors/acceptors,
rotatable bonds, ring counts, canonical SMILES, and InChI / InChIKey.
A crystal reports its lattice instead: the lattice parameters, the
supercell and how many unit cells it holds, which cells are tilted, and
the coordination number of each element. Its mass row is labelled **Mass
drawn**, because the number is the mass of the atoms on screen, not a
molar mass — and a stacked cell says so outright, since atoms shared
between cells are counted once and the formula is therefore not the
stoichiometric unit.

## AI Chat

The **robot** button on the toolbar (or **View ▸ AI Chat**) opens an
assistant that answers chemistry questions and can draw molecules for you.

1. Click the **⚙** button and choose a provider (Anthropic/Claude, OpenAI,
   Mistral, Ollama, or a local server), a model, and paste your API key.
   (Ollama and a local server need no key.)
2. Ask a question — *"what is aromaticity?"* — or request a structure —
   *"draw aspirin"*, *"show me glucose"*. When the assistant suggests a
   molecule it returns a SMILES that KherveMol renders into the 3D view and
   2D sketch automatically (RDKit required for rendering).

Requests run in the background, so a slow or failed reply never freezes the
app; errors appear as a red line in the chat. Crystal cells aren't SMILES —
the assistant will point you to the Crystal menu for those.

## SMILES & structure files (optional — RDKit)

Install RDKit to unlock structure import — it has a native Python API and
needs no Jupyter:

```
pip install rdkit
```

Then the **Molecule** menu gains:

- **From SMILES…** (Ctrl+Shift+M) — type a SMILES string (e.g. `CCO`,
  `c1ccccc1`, `CC(=O)O`). KherveMol adds hydrogens, embeds a real 3D
  conformer (ETKDG + force-field cleanup) into the 3D view, and a flat
  depiction into the 2D sketch. This works **without** RDKit too, using the
  built-in builder (VSEPR shapes, ring templates, a light relaxation); RDKit
  simply gives more refined geometry.
- **Import structure file…** — open a `.mol`, `.sdf`, or `.pdb` file (uses
  the file's own 3D coordinates when present).
- **Copy SMILES of structure** — best-effort canonical SMILES of the
  current model, to the clipboard.

Without RDKit the app runs normally: SMILES and the whole library build with
the built-in builder; only structure-file import and *Copy SMILES* need RDKit.

## Structure menu

- **Flatten 3D → 2D sketch** — projects the current 3D model (at its
  current orientation) into the 2D sketch as a flat graph.
- **Clear 2D sketch** — empties the sketcher.

## Files

- **Save / Open** — the native `.kmol` format stores the 3D model, its
  orientation and bond length, the scene annotations of a reaction, and
  the 2D sketch, so a document round-trips completely.
- **Export PNG** — an image of whichever tab is active (the 3D view at
  1600 × 1200 through the active renderer).
- **Export SVG (KhervePaint)** (Ctrl+Shift+E) — writes an SVG that opens in
  **KhervePaint** as native, editable items (each atom a gradient-filled
  ellipse, each bond a line). Exports the 3D ball-and-stick or the 2D
  skeletal formula depending on the active tab.

## Keyboard shortcuts

| Action | Shortcut |
|---|---|
| New | Ctrl+N |
| Open | Ctrl+O |
| Save | Ctrl+S |
| Save As | Ctrl+Shift+S |
| Export PNG | Ctrl+E |
| Crystal builder | Ctrl+Shift+C |
| Surface builder | Ctrl+Shift+F |
| Graphene, nanotubes & fullerenes | Ctrl+Shift+G |
| Reaction builder | Ctrl+R |
| User Guide | F1 |
| Delete selected atom (3D) | Delete |
| Step the selection (3D) | Tab / Shift+Tab |
| Add an atom to the selection (3D) | Ctrl+click |
| Cancel "select an atom on screen" | Esc |
