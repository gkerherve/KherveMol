# KherveMol — User Guide

KherveMol draws chemical compounds and crystal structures in 3D and 2D.
Everything you build stays as ordinary vector geometry you can export.

## The two tabs

- **3D View** — an interactive ball-and-stick model. Atoms are lit CPK
  spheres; bonds are sticks (single / double / triple). Crystals are drawn
  as wireframe unit cells.
- **2D Sketch** — a flat skeletal editor for line formulae.

## 3D View

- **Rotate** — drag the background, or snap to a face with the *view cube*
  buttons (Front / Back / Left / Right / Top / Bottom / Isometric).
- **Zoom** — mouse wheel; *Reset zoom* refits the model.
- **Bond length** — the slider spreads the atoms apart.
- **Build** — click an atom to select it (green ring), then click an
  element in the **Add atom** palette to bond a new atom on. The builder
  respects each element's valence and refuses to over-bond. Choose the
  bond order (single / double / triple) first.
- **Bend** — drag a selected atom to adjust a bond angle.
- **Delete** — select an atom and press **Delete** (or the button).
- **Labels** — toggle element symbols on the spheres.

Crystals are fixed lattices: rotatable and zoomable, but not
atom-editable.

## 2D Sketch

- **Draw** — drag from an atom to another atom to bond them, or drag to
  empty space to spawn a new atom (of the active element) bonded to it.
  Click empty space to drop a lone atom. Click an existing bond to cycle
  single → double → triple.
- **Move** — drag atoms around.
- **Atom** — click an atom to re-label it to the active element.
- **Erase** — click an atom (removes it and its bonds) or a bond.
- **All labels** shows every atom's symbol (including carbons); **Clear**
  empties the sketch.

## Library & elements

- The **Molecule** and **Crystal** menus — and the library tree on the
  left — load 30+ ready-made structures: simple molecules, alcohols &
  acids, hydrocarbons, polymers, and crystal unit cells (simple cubic,
  BCC, FCC, HCP, diamond, NaCl, CsCl).
- The **periodic-table dock** sets the active element used for 2D drawing;
  it also shows each element's atomic number and valence.

## Structure menu

- **Flatten 3D → 2D sketch** — projects the current 3D model (at its
  current orientation) into the 2D sketch as a flat graph.
- **Clear 2D sketch** — empties the sketcher.

## Files

- **Save / Open** — the native `.kmol` format stores the 3D model, its
  orientation and bond length, and the 2D sketch, so a document
  round-trips completely.
- **Export PNG** — a flattened image of whichever tab is active.

## Keyboard shortcuts

| Action | Shortcut |
|---|---|
| New | Ctrl+N |
| Open | Ctrl+O |
| Save | Ctrl+S |
| Save As | Ctrl+Shift+S |
| Export PNG | Ctrl+E |
| User Guide | F1 |
| Delete selected atom (3D) | Delete |
