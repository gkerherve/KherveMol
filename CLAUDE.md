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
                     table (f-block below). Also the **bond-length** data:
                     Cordero `COVALENT` radii (all 118) plus a
                     `_BOND_LENGTHS` table of experimental pair lengths,
                     behind `bond_length(a, b, order)` — C–O 1.43 Å,
                     C=O 1.23 Å, C≡N 1.16 Å; unlisted pairs fall back to the
                     radius sum shrunk by bond order. `color/radius/valence/
                     name/number/text_color` fall back gracefully.
  - `model.py`     — the geometry **engine**. Isometric `_proj`, the
                     depth-sorted `_model(atoms, bonds, edges, ...)` that
                     turns 3D coordinates into **shape specs** (circles =
                     lit spheres via a `sun` gradient, lines = sticks,
                     dashed lines = cell diagonals; bond sticks carry a
                     `_bond` tag when `tag_atoms`, for hit-testing),
                     `atom_specs`/`bond_specs`, layout capture
                     (`fit_params`) and `drag_atom`, plus the
                     interactive-builder ops (`add_bonded_atom` respecting
                     valence *and* placing the atom at its real bond length,
                     `delete_atom`, `free_valence`) and the `Molecule`
                     container (atoms `[el,x,y,z]`, bonds `[i,j,order]`,
                     optional crystal `edges`, view az/el/bond, `formula()`).
                     **Bond geometry is chemistry, not free-hand**:
                     `constrain_atom` re-projects a dragged atom onto every
                     neighbour's ideal length (alternating projections;
                     `drag_atom(..., bonds=…)` calls it, so a drag swings a
                     bond rather than stretching it), `set_bond_order` /
                     `can_set_bond_order` change an order within valence and
                     `relax_bond` re-lengthens the bond by sliding its
                     smaller `fragment` (ring bonds are left alone), and
                     `add_bond`/`can_bond` join two *existing* atoms.
                     `angle(i,j,k)` (degrees, at j) and `bond_between` serve
                     the structure outline.
  - `library.py`   — built-in structures. `_mol_*` / `_xtal_*` builders
                     return `(atoms, bonds, edges)`; `make(name)` wraps one
                     in a `Molecule`. 30+ entries in `CATEGORIES`: simple
                     molecules, alcohols & acids, hydrocarbons, polymers
                     (zig-zag backbone), and crystal unit cells (simple
                     cubic / BCC / FCC / HCP / diamond / NaCl / CsCl / zinc
                     blende / fluorite / perovskite, drawn as wireframe
                     cells; perovskite/zinc-blende include their internal
                     bonds). `is_crystal`/`default_bond`/`label`/`names`.
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
                     slider, labels toggle, **Lock lengths** toggle
                     (`lock_lengths`, on by default — the drag then feeds
                     `model.drag_atom(bonds=…)` so bonds keep their real
                     length and `show_geometry` reads them out live),
                     Add-atom palette + bond-order combo + delete. A
                     **＋active-element** button
                     (`set_active_element`/`add_active`) bonds on *any*
                     element chosen in the periodic-table dock (not just the
                     10 quick buttons); also on the right-click menu.
                     Right-click **hit-tests** the scene (`_atom_at` /
                     `_bond_at` over the `_atom` / `_bond` spec tags), parks
                     the result in `hit = (kind, index)` and emits `context`;
                     `mainwindow._bond_section` / `_atom_section` /
                     `_join_section` then build a bond menu
                     (Single/Double/Triple — valence-gated via
                     `can_set_order` — + Delete bond) or an atom menu
                     (`bondable` ▸ Bond on / Double- / Triple-bond on,
                     `start_pick` = "Select an atom on screen…").
                     **Selection is a list** (`selection`, primary = last;
                     `selected` is a property over it): Ctrl+click toggles an
                     atom in, Tab/Shift+Tab `step_selection` through the
                     atoms, and `bond_selected`/`bond_atoms` join two
                     existing atoms (`can_bond_selected` drives the *Bond
                     selected* button; `_why_not` explains a refusal).
                     `start_pick`/`cancel_pick` (Esc) is the click-the-other-
                     atom mode. Emits `selection_changed` / `molecule_changed`
                     for the structure outline. Crystals are
                     rotatable/zoomable but not atom-editable (`editable` =
                     not crystal).
  - `structure_tree.py` — `StructureTree(QTreeWidget)`: the molecule as a
                     folder-like connectivity outline in the **left top**
                     dock, above the library. `walk(atoms, bonds)` is a DFS
                     spanning tree yielding `(atom, parent, grandparent,
                     order, ring)` — heavy atoms before hydrogens, ring
                     bonds emitted once as leaves (nesting them would loop),
                     every disconnected fragment rooted off the top. Columns
                     are Atom / Bond order / Length (Å) / Angle (° at the
                     parent, from `model.angle`); the tooltip adds Z, weight,
                     free valence, coordinates and the ideal bond length.
                     Two-way selection with the viewer (`atom_selected` ↔
                     `show_atom`, `_quiet` guards the echo).
  - `editor2d.py`  — `Editor2D`: the 2D sketcher, drawn as a **proper
                     skeletal formula** (`_draw_bond`/`_draw_label`: thin
                     bond lines with double/triple parallels, carbons as
                     implicit vertices, heteroatoms as CPK-lettered labels
                     with a white halo; hydrogens implicit unless "All
                     labels"). Inner `_Canvas` holds a 2D graph (atoms
                     `[el,x,y]`, bonds `[i,j,order]`) with Draw / Move /
                     Atom / Erase tools (`set_tool`); Draw drags atom→atom
                     (bond) or atom→empty (new bonded atom via
                     `_new_bonded_atom`, snapped to a fixed length + 30°
                     angle for tidy geometry), clicking a bond cycles order.
                     **Multi-molecule canvas**: Move drags a whole connected
                     fragment (`_component`); Draw across fragments bonds
                     them, Erase a bond splits them; `add_fragment` appends
                     another molecule at a drop point; drops arrive via the
                     `molecule_dropped` signal (canvas `dropEvent`, MIME
                     `_DND_MIME`). **Enforces valence** like the 3D builder
                     (`_free`/`_bond_capacity`): refuses bonds / order
                     increases that exceed an atom's valence. Right-click
                     emits `context_requested`. `image()` rasterises for
                     export.
                     `MainWindow._sync_sketch` mirrors the 3D `Molecule`
                     into it on load / build / 3D edit — via RDKit's clean
                     `Compute2DCoords` depiction when available, else
                     `_flatten_2d` (project + drop explicit H). The reverse
                     is on demand: `build_3d_from_sketch` (Ctrl+B / context
                     menu) turns the sketch graph → SMILES → 3D.
  - `periodic.py`  — `PeriodicPicker`: the **full** periodic-table grid
                     (all 118 elements, atomic number + symbol per cell,
                     CPK-coloured, f-block below) built from
                     `elements.table_cells()`. Sits in a full-width bottom
                     dock (inside a `QScrollArea`); sets the active drawing
                     element and emits `picked(symbol)`.
  - `catalog.py`   — **300+** named compounds `(category, name, SMILES)`:
                     `_CURATED` families (solvents, aromatics, heterocycles,
                     pharmaceuticals, vitamins, hormones, steroids, terpenes,
                     fatty acids, monomers, reagents, agrochemicals…) plus
                     `_series()` generated homologous series (alkanes/enes/
                     ynes/ols/acids/amines/aldehydes/cycloalkanes — always
                     valid SMILES). `grouped()`/`all_entries()`/
                     `categories()`. Built into 3D/2D via `rdkit_io`.
  - `explorer.py`  — `MoleculeExplorer(QDialog)`: a searchable browser
                     (search box + category tree) with a live preview pane.
                     Lists the built-in models (preview/build via `library`,
                     no RDKit) and the `catalog` compounds (preview =
                     `sketch_from_smiles` → `render.specs_from_graph2d`;
                     build via SMILES, RDKit-gated). `result()` returns
                     `(kind, value, name)` where kind is `"model"` (library
                     key) or `"smiles"`; `MainWindow.open_explorer` routes
                     it to `load_model` / `build_smiles`.
  - `rdkit_io.py`  — **optional** RDKit bridge (guarded import;
                     `available()`): `molecule_from_smiles` (AddHs → ETKDG
                     embed → MMFF/UFF cleanup → 3D `Molecule`),
                     `sketch_from_smiles` (`Compute2DCoords` → 2D graph),
                     `molecule_from_file` (`.mol`/`.sdf`/`.pdb`),
                     `smiles_from_structure` (RWMol → canonical SMILES), and
                     the descriptor helpers `descriptors_from_structure` /
                     `descriptors_from_smiles` (`rdkit.Chem.Descriptors` /
                     `rdMolDescriptors`: MW, exact mass, logP, TPSA, HBD/HBA,
                     rotatable bonds, rings, InChI/InChIKey). Aromatic bonds
                     are Kekulised so orders read as 1/2/3. Install with
                     `pip install rdkit`; the app runs without it and the
                     menu items say when it's needed.
  - `properties.py`— `compute(molecule)` → ordered `(label, value)` rows and
                     `PropertiesDialog` (Molecule ▸ Properties…, Ctrl+I).
                     Formula / molecular weight / atom counts come from the
                     element data (`elements.weight`, standard atomic
                     weights for all 118), so they always work; RDKit adds
                     the rich descriptors. Crystals report a unit-cell
                     composition.
  - `document.py`  — the `.kmol` JSON format (both the 3D `Molecule` incl.
                     crystal edges + view, and the 2D sketch) and PNG
                     export. `FORMAT_VERSION`.
  - `svgexport.py` — **KhervePaint-compatible SVG** writer. `specs_to_svg`
                     turns shape specs into KhervePaint's own SVG shape
                     (spheres → `<ellipse>` with an `objectBoundingBox`
                     radial "sun" gradient written light-first,
                     `cx=0.35 cy=0.35 r=0.95 fx=0.25 fy=0.25`; bonds →
                     `<line>`), so a molecule opens in KhervePaint as
                     editable gradient-filled items (verified against
                     `khervepaint.svgio.load_svg`). `sketch_specs` makes the
                     2D skeletal line/label specs; `normalize` fits the
                     viewBox. Wired to File ▸ Export SVG (Ctrl+Shift+E) and
                     both context menus.
  - `mainwindow.py`— `MainWindow` shell: a `QTabWidget` (3D View / 2D
                     Sketch), a **left** dock (library tree — both the
                     built-in models AND the full `catalog`, 360+ leaves,
                     via `_tree_group`; `_tree_load` routes `("model",key)`
                     → `load_model` and `("smiles",smi)` → `build_smiles`)
                     (leaves drag onto the 2D canvas via `_LibraryTree`
                     mimeData → `_on_drop_molecule`/`_compound_2d` →
                     `sketch.add_fragment`) and a **bottom** dock (full
                     periodic table), both toggleable from View; the 2D
                     sketch mirrors the 3D on load/build (`_sync_sketch`) but
                     a `_sketch_dirty` flag stops 3D edits clobbering hand-
                     built multi-molecule work (force-sync on explicit
                     load / Flatten);
                     menus (File / Molecule / Crystal / Structure / View /
                     Help), toolbar, `.kmol` open/save, PNG export,
                     `flatten_to_2d`, and the RDKit actions (From SMILES…,
                     Import structure file…, Copy SMILES of structure — each
                     guarded by `rdkit_io.available()`).
  - `ai_providers.py` — dependency-free (urllib) AI backend registry:
                     Claude / ChatGPT / Mistral / Ollama / Local, each with
                     `chat()` and `list_models()`; keys/base URLs read from
                     QSettings by the dock. Ported from the family.
  - `ai_assistant.py` — `AiDock`: the **AI Chat** panel (right dock, toggled
                     from the toolbar robot / View ▸ AI Chat). A chemistry
                     assistant — answers questions, and when asked to draw a
                     molecule replies with a ``SMILES:`` line that
                     `extract_smiles` pulls out and `MainWindow.build_smiles`
                     renders into the 3D view + 2D sketch (RDKit-gated).
                     **All network runs on a `_Worker(QThread)`** with
                     done/failed signals, so a slow/failed request never
                     blocks or crashes the UI — errors show as a red chat
                     line. `AiSettingsDialog` sets provider/model/key.
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

**Never hand-place an sp3 substituent.** An atom's free bonding directions
depend on the bonds it already carries, so a fixed `TETRA` basis is only
valid for the *first* centre — reuse it on a neighbour and every
substituent lands at 70.5° (the supplement of 109.5°) instead. Use
`_grow(atoms, bonds, anchor, element)` (→ `model.add_bonded_atom`), which
picks a free tetrahedral direction and the real bond length, and
`_fill_h(atoms, bonds, anchor)` to cap the rest. Add the backbone/ring
bonds *first*, so each atom sees its neighbours before its hydrogens are
grown. Trigonal centres (carbonyl, aromatic) still need explicit geometry:
`_sp2_dirs(back, normal)` gives the two 120° directions, and `_phenyl`
builds a planar ring off an anchor. `tests/test_library` asserts no
built-in molecule has a bond angle under 95° or an over-bonded atom.

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

`rdkit` is listed in `requirements.txt` so the standard install includes
it, **but the app must still run without it**: `rdkit_io.py` imports
`rdkit` behind a `try/except` and exposes `available()`. Never import
`rdkit` at module top-level anywhere else. New RDKit-backed features go in
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
