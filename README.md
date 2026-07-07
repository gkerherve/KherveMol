<img src="docs/icon.png" width="96" align="right" alt="KherveMol icon">

# KherveMol

**Draw chemical compounds and crystal structures in 2D and 3D.**

KherveMol is a native PyQt5 desktop app in the Kherve family. It pairs an
interactive **3D ball-and-stick** viewer/builder with a flat **2D skeletal
sketcher**, over one shared molecular model. There are no heavy chemistry
dependencies — the 3D look is a pure-Python isometric projection (no
OpenGL), so it runs with just PyQt5 and qtawesome.

![KherveMol](docs/screenshot.png)

## Features

- **3D ball-and-stick viewer** — lit CPK spheres and single/double/triple
  bond sticks, depth-sorted so it reads as 3D. Drag to orbit, wheel to
  zoom, snap to any face with the view cube.
- **Build molecules by hand** — click an atom, then click an element to
  bond a new atom on. The builder respects each element's valence and
  refuses to over-bond. Drag an atom to bend a bond.
- **30+ built-in structures** — small molecules, alcohols & acids,
  hydrocarbons, polymer repeat units, and crystal unit cells
  (simple cubic, BCC, FCC, HCP, diamond, NaCl, CsCl) drawn as wireframe
  cells.
- **2D structure sketcher** — draw flat line formulae: drag to bond, click
  a bond to cycle its order, re-label or erase atoms. Flatten any 3D model
  into the sketch with one command.
- **Full periodic table** — all 118 elements, CPK-coloured, as a dockable
  element picker.
- **Molecule Explorer** — a searchable browser of the built-in models plus
  ~120 named compounds (drugs, amino acids, sugars, solvents, aromatics,
  nucleobases…), with a live preview and one-click build.
- **AI Chat** — ask chemistry questions or say "draw caffeine"; the
  assistant answers and renders the molecule. Works with Claude, ChatGPT,
  Mistral, Ollama or a local server; all network runs off the UI thread.
- **SMILES & file import (optional, via RDKit)** — type a SMILES string to
  embed a real 3D conformer, or open `.mol` / `.sdf` / `.pdb` files. Works
  headless, no Jupyter. `pip install rdkit` to enable.
- **`.kmol` save/open** and **PNG export**.
- Themeable UI shared with the rest of the Kherve family.

## Install & run

```bash
pip install -r requirements.txt
python KherveMol.py          # or: python -m khervemol
```

Requires Python 3.12+ with PyQt5 and qtawesome.

## Quick start

1. Pick a structure from the **Molecule** or **Crystal** menu (or the
   library tree on the left).
2. In **3D View**, drag to rotate, use the wheel to zoom, and the view
   cube to snap to standard orientations.
3. To build: click an atom (green ring), pick a bond order, then click an
   element in the **Add atom** palette. Press **Delete** to remove an atom.
4. Switch to **2D Sketch** to draw a flat formula, or use
   **Structure ▸ Flatten 3D → 2D sketch**.
5. **File ▸ Save** writes a `.kmol`; **File ▸ Export PNG** writes an image
   of the current tab.

See the in-app **Help ▸ User Guide** (F1) or [USERGUIDE.md](USERGUIDE.md).

## License

GPL-3.0 © 2026 Gwilherm Kerherve
