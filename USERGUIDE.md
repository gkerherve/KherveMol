# KherveMol — User Guide

KherveMol draws chemical compounds and crystal structures in 3D and 2D.
Everything you build stays as ordinary vector geometry you can export.

## The two tabs

- **3D View** — an interactive ball-and-stick model. Atoms are lit CPK
  spheres; bonds are sticks (single / double / triple). Crystals are drawn
  as wireframe unit cells.
- **2D Sketch** — a flat editor drawn in the *same* ball-and-stick style as
  the 3D view. Loading or building a molecule mirrors it here automatically,
  so both tabs always show the same structure; you can still draw freely.

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
  BCC, FCC, HCP, diamond, NaCl, CsCl, zinc blende, fluorite, perovskite).
- The **periodic-table dock** along the bottom shows the whole table (all
  118 elements, CPK-coloured with atomic numbers). Click one to set the
  active drawing element; the header shows its name, atomic number and
  valence. Toggle the dock (and the library) from the **View** menu.

## Molecule Explorer

**Molecule ▸ Explorer…** (Ctrl+L, or the magnifier button) opens a
searchable browser of structures — the built-in 3D models plus ~120 named
compounds grouped by family (solvents, hydrocarbons, aromatics, functional
groups, acids, amino acids, sugars & vitamins, nucleobases, drugs &
bioactive, gases). Type in the search box to filter by name, click an
entry to preview it, then **Build in 3D** to load it into the 3D view (and
2D sketch). The built-in models build with or without RDKit; the named
compounds are built from SMILES via RDKit.

## Properties

**Molecule ▸ Properties…** (Ctrl+I) opens a table of the current molecule's
properties. Formula, molecular weight and atom counts always work. With
RDKit installed it adds exact mass, LogP, TPSA, H-bond donors/acceptors,
rotatable bonds, ring counts, canonical SMILES, and InChI / InChIKey.
Crystals are shown as a unit-cell composition (molecular descriptors don't
apply to a periodic lattice).

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
  depiction into the 2D sketch.
- **Import structure file…** — open a `.mol`, `.sdf`, or `.pdb` file (uses
  the file's own 3D coordinates when present).
- **Copy SMILES of structure** — best-effort canonical SMILES of the
  current model, to the clipboard.

Without RDKit the app runs normally; these menu items note that it's
needed.

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
