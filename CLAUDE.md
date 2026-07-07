# KherveMol — notes for Claude

KherveMol is a native PyQt5 desktop app in the Kherve family
(KherveFitting, KherveSheet, KhervePDF, KherveDOC, KhervePlot,
KherveDraw, KherveBook, KhervePaint). It draws **chemical compounds and
crystal structures in 3D and 2D**: an interactive ball-and-stick 3D
viewer/builder and a flat 2D skeletal sketcher, over a shared molecular
model. No heavy chemistry dependencies — the 3D look is a pure-Python
isometric projection (no OpenGL), so it installs with only PyQt5 +
qtawesome, matching the family philosophy.

## Build / run

- Python 3.12 / 3.13 with PyQt5 (+ qtawesome for icons).
- Run via `python KherveMol.py` or `python -m khervemol`.
- Crash log: `%TEMP%/khervemol_crash.log`.
- **Version string** is derived at runtime in `_version.py` from
  `git rev-list --count HEAD` and `git rev-parse --short HEAD`, cached
  with `lru_cache`. Falls back to `_FALLBACK = "0.1.0"` outside a git
  checkout. Title bar reads `KherveMol v0.1.N+sha`. The version bumps
  automatically on every commit — never edit a version constant by hand.

## File size policy

Every module in `khervemol/` should stay near **1500 lines**. If a change
would push a file meaningfully past that, split the new code into a new
module and import.

## Project layout

- `KherveMol.py` — entry script.
- `khervemol/` — package; `python -m khervemol` is the alternative entry.
  - `__init__.py`  — `APP_NAME`, version import.
  - `__main__.py`  — module entry point.
  - `_version.py`  — git-based version string.
  - `app.py`       — `main()`, crash log, Fusion style + theme.
  - `style.py`     — token-driven QSS themes (same template family as the
                     rest of the family; teal-green **signature** default
                     "Flask"; theme persists via QSettings).
  - `icons.py`     — qtawesome MDI wrapper with fallback; the **KMol**
                     app mark (wordmark + two-atom ball-and-stick on a teal
                     tile) and `view_cube_icon` (3D cube with one face
                     shaded, for the viewer's view toolbar).
  - `elements.py`  — single source of truth for per-element data across
                     the **whole periodic table** (Z = 1..118): `SYMBOLS`
                     (Z order), `NAMES`, `NUMBERS`, full Jmol `_JMOL`
                     colours, tuned ball-and-stick `COLORS`/`RADII` for the
                     common elements (with sensible defaults for the rest),
                     `VALENCE`, the 3D quick `PALETTE`, and `table_cells()`
                     yielding `(symbol, row, col)` for the classic wide
                     table (f-block below). `color/radius/valence/name/
                     number/text_color` accessors fall back gracefully.
  - `model.py`     — the geometry **engine**. Isometric `_proj`, the
                     depth-sorted `_model(atoms, bonds, edges, ...)` that
                     turns 3D coordinates into **shape specs** (circles =
                     lit spheres via a `sun` gradient, lines = sticks,
                     dashed lines = cell diagonals), `atom_specs`/
                     `bond_specs`, layout capture (`fit_params`) and
                     `drag_atom`, plus the interactive-builder ops
                     (`add_bonded_atom` respecting valence, `delete_atom`,
                     `free_valence`) and the `Molecule` container
                     (atoms `[el,x,y,z]`, bonds `[i,j,order]`, optional
                     crystal `edges`, view az/el/bond, `formula()`).
  - `library.py`   — built-in structures. `_mol_*` / `_xtal_*` builders
                     return `(atoms, bonds, edges)`; `make(name)` wraps one
                     in a `Molecule`. 30+ entries in `CATEGORIES`: simple
                     molecules, alcohols & acids, hydrocarbons, polymers
                     (zig-zag backbone), and crystal unit cells (simple
                     cubic / BCC / FCC / HCP / diamond / NaCl / CsCl, drawn
                     as wireframe cells). `is_crystal`/`default_bond`/
                     `label`/`names`.
  - `render.py`    — shape-spec → `QGraphicsItem` (`spec_to_item`,
                     `add_specs`) with the sun/linear/radial gradient
                     brushes, and `render_image(specs, w, h)` which
                     rasterises via a temporary `QGraphicsScene` for PNG
                     export.
  - `viewer3d.py`  — `Viewer3D`: the interactive 3D ball-and-stick
                     viewer/builder. Inner `_View(QGraphicsView)` renders
                     the model, orbits on background-drag (az/el), zooms on
                     wheel, drags an atom to bend a bond, clicks to select.
                     Surrounding controls: view-cube toolbar, bond-length
                     slider, labels toggle, Add-atom palette + bond-order
                     combo + delete. Crystals are rotatable/zoomable but
                     not atom-editable (`editable` = not crystal).
  - `editor2d.py`  — `Editor2D`: the flat 2D skeletal sketcher. Inner
                     `_Canvas(QGraphicsView)` holds a 2D graph (atoms
                     `[el,x,y]`, bonds `[i,j,order]`) with Draw / Move /
                     Atom / Erase tools; Draw drags atom→atom (bond) or
                     atom→empty (new bonded atom), clicking a bond cycles
                     its order. `image()` rasterises for export.
  - `periodic.py`  — `PeriodicPicker`: the **full** periodic-table grid
                     (all 118 elements, atomic number + symbol per cell,
                     CPK-coloured, f-block below) built from
                     `elements.table_cells()`. Sits in a full-width bottom
                     dock (inside a `QScrollArea`); sets the active drawing
                     element and emits `picked(symbol)`.
  - `rdkit_io.py`  — **optional** RDKit bridge (guarded import;
                     `available()`): `molecule_from_smiles` (AddHs → ETKDG
                     embed → MMFF/UFF cleanup → 3D `Molecule`),
                     `sketch_from_smiles` (`Compute2DCoords` → 2D graph),
                     `molecule_from_file` (`.mol`/`.sdf`/`.pdb`), and
                     `smiles_from_structure` (RWMol → canonical SMILES).
                     Aromatic bonds are Kekulised so orders read as 1/2/3.
                     Install with `pip install rdkit`; the app runs without
                     it and the menu items say when it's needed.
  - `document.py`  — the `.kmol` JSON format (both the 3D `Molecule` incl.
                     crystal edges + view, and the 2D sketch) and PNG
                     export. `FORMAT_VERSION`.
  - `mainwindow.py`— `MainWindow` shell: a `QTabWidget` (3D View / 2D
                     Sketch), a **left** dock (library tree) and a **bottom**
                     dock (full periodic table), both toggleable from View;
                     menus (File / Molecule / Crystal / Structure / View /
                     Help), toolbar, `.kmol` open/save, PNG export,
                     `flatten_to_2d`, and the RDKit actions (From SMILES…,
                     Import structure file…, Copy SMILES of structure — each
                     guarded by `rdkit_io.available()`).
  - `help.py`      — About dialog + in-app User Guide (`Help ▸ User
                     Guide`, F1). Keep the guide and `USERGUIDE.md` in sync
                     when features change.
- `tests/` — pytest suite (offscreen Qt; run `python -m pytest tests/`).
- `requirements.txt`, `LICENSE` (GPL-3.0).

## Architecture

- A structure is a `model.Molecule`: `atoms` = `[element, x, y, z]`,
  `bonds` = `[i, j, order]`, optional crystal `edges`, and a view
  (`az`, `el`, `bond` spread). `Molecule.specs(w, h)` projects it to a
  flat list of **shape-spec dicts** with the isometric camera.
- **Shape specs** are plain dicts (`{"shape":"circle"|"line"|"text", ...}`)
  shared by the on-screen scenes and the PNG rasteriser. A sphere is a
  circle whose `fill` is a `sun`-gradient dict (light focal point + dark
  rim) so it reads as a lit 3D ball in the element's CPK colour. This is
  the same spec vocabulary KhervePaint uses, so models could be exchanged.
- The **3D viewer** never uses OpenGL: `_model` depth-sorts atoms by the
  projected `depth` and draws far-to-near (edges, bonds, then spheres).
  Orbit/zoom just change the projection angles / view scale and rebuild.
- The **2D sketch** is an independent flat molecular graph (its own
  atoms/bonds in scene pixels), not a projection — but `Structure ▸
  Flatten 3D → 2D` projects the current 3D model into it.

## Adding a molecule or crystal

Write a `_mol_<name>()` / `_xtal_<name>()` in `library.py` returning
`(atoms, bonds, edges)`; register it in `_MODELS` (with a radius scale),
add its `LABELS` entry and put its key in the right `CATEGORIES` bucket.
Crystals whose builder name starts with `_xtal` are auto-flagged
non-editable and get true (unscaled) lattice spacing. `tests/test_library`
parametrises over `library.names()`, so a new entry is covered
automatically.

## Persistence policy

**All model/sketch properties must round-trip through the `.kmol` JSON
(`document.py`).** When adding a persisted property to `Molecule` or the
sketch, update `mol_to_dict`/`mol_from_dict` (and the sketch block) in
`document.py`, bump `FORMAT_VERSION`, keep loading backward compatible,
and extend the round-trip tests in `tests/test_document.py`.

## UI conventions

- Single main window; central `QTabWidget` with **3D View** and **2D
  Sketch**. Left dock = library tree (categories) over the periodic-table
  element picker. Top toolbar = file ops + a few quick-load structures.
- 3D View: **drag background** to orbit, **wheel** to zoom, **view cube**
  to snap to a face, **click an atom** to select (green ring), **click an
  element** in the Add-atom palette to bond it on (valence-checked),
  **drag a selected atom** to bend, **Delete** to remove.
- 2D Sketch: **Draw** (drag atom→atom or atom→empty; click a bond to cycle
  order), **Move**, **Atom** (re-label), **Erase**.
- **Window style**: Fusion default; themes shared with the family (View ▸
  Theme), teal-green signature.

## Optional RDKit integration

`rdkit_io.py` is imported behind a `try/except`; **never** import `rdkit`
at module top-level elsewhere or add it to `requirements.txt` as a hard
dependency — the app must run without it. New RDKit-backed features go in
`rdkit_io.py` (guarded), get a menu item gated on `rdkit_io.available()`,
and a test marked `skipif(not rdkit_io.available())`.

## Roadmap

- CIF → crystal import via RDKit / pymatgen (still guarded/optional).
- Auto-generate 3D coordinates from a 2D sketch when RDKit is absent (a
  small built-in force field), so the tabs are fully bidirectional offline.
- Measure tool (bond lengths / angles); multiple molecules per document.

## Commit / push policy

**Every change must land as a commit on the `dev` branch and be pushed
immediately.** No batching. No `Co-Authored-By:` trailer. Commit subjects
under 70 chars; body explains *why*, not what.

**Commit message prefix** — every subject must start with one of:
`fix:` `feat:` `refactor:` `style:` `docs:` `perf:`.

## Licensing

GPL-3.0. New source files must carry the short GPL notice at the top.
