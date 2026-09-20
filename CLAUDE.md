# KherveMol — notes for Claude

KherveMol is a native PyQt5 desktop app in the Kherve family
(KherveFitting, KherveSheet, KhervePDF, KherveDOC, KhervePlot,
KherveDraw, KherveBook, KhervePaint). It draws **chemical compounds and
crystal structures in 3D and 2D**: an interactive ball-and-stick 3D
viewer/builder and a flat 2D skeletal sketcher, over a shared molecular
model. No heavy dependencies: the 3D view is **OpenGL** (impostor-shaded
spheres and cylinders through PyQt5's own `QOpenGLWidget` — no PyOpenGL), with
the older pure-Python isometric projection kept as an automatic fallback, so
it installs with only PyQt5 + qtawesome, matching the family philosophy.
The molecule / crystal / surface / reaction content is ported from
KherveCAD's Qt-free chemistry modules and needs no RDKit either.

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
  - `lattices.py`  — non-cubic **crystal geometry**: `lattice_vectors(a,b,c,
                     α,β,γ)` → the three cell vectors (crystallographic
                     convention: **a** along x, **b** in xy at γ), `cell()`
                     building the parallelepiped (8 corners + 12 edges),
                     `PARAMS`/`LATTICE_VECTORS`/`PARAM_TEXT` for the six
                     systems (tetragonal, orthorhombic, hexagonal,
                     rhombohedral, monoclinic, triclinic; builders named
                     `_xtal_*` so `library.is_crystal` picks them up), plus
                     `rotation(rx,ry,rz)` (a cell tilt) and
                     `coordination_faces(pts)` (convex hull of a
                     coordination shell — 8 triangles for an octahedron, 6
                     squares for a cube).
  - `supercell.py` — `tile(atoms,bonds,edges,nx,ny,nz,vectors,tilts,owners)`
                     stacks a unit cell face-to-face along its **own**
                     lattice vectors (the cubic family falls back to its
                     wireframe extent), de-duplicating shared corner/face
                     atoms, bonds and edges by rounded coordinate.
                     **A tilt is a defect, not a detached grain**: atoms are
                     laid on ONE node table keyed by the *untilted*
                     position, then each node is displaced by the *average*
                     rotation of the tilted cells that own it (untilted
                     owners contribute 0) — so a tilted cell drags the atoms
                     it shares with its neighbours, they deform to follow,
                     and an isolated tilt stays rigid. Two membership
                     views come back: `owners` gives each atom ONE home cell
                     (how clicking an atom picks a cell) and `members` gives
                     each cell ALL its atoms, shared corners included (how a
                     whole cell is outlined). Atom order is keyed by the
                     *untilted* position, so **a tilt never renumbers** —
                     only a change of cell counts does.
                     `MAX_CELLS = 12` / `clamp` cap the size — tiling
                     is O(cells × atoms) and every rebuild re-adds every
                     sphere, so 12³ is already ~3 s.
  - `molcolor.py`  — colours and polyhedra. Two mechanisms, matching how
                     each structure is stored: an **editable molecule** owns
                     its atoms, so a colour rides on the atom (optional 5th
                     slot `[el,x,y,z,tint]`); a **crystal** is regenerated
                     from its builder on every draw, so colours live in a
                     map keyed by `color_key` — element + site tint (`"Fe"`
                     vs `"Fe@#2f6fed"`), re-applied by `apply_colors`.
                     `SITE_COLORS` tints the hidden lattice sites (body /
                     face / inner / mid) that would otherwise vanish against
                     identical corners. `coordination_polyhedra` /
                     `has_polyhedra` build the VESTA-style translucent faces
                     for every ≥4-coordinate atom; `legend_entries` /
                     `legend_specs` are the colour key.
  - `molrepr.py`   — 2D **representations** of a molecular graph:
                     `MODES` = skeletal / structural / lewis / condensed.
                     `implicit_hydrogens` + `hill_formula` count the H a
                     skeletal drawing leaves implicit (a C–C–O sketch is
                     C₂H₆O, not C₂O — that is what the status bar and the
                     condensed drawing report), `lone_pairs` /
                     `dot_positions` place Lewis dots on the directions
                     farthest from any bond, and an implied H consumes a
                     valence electron just as a drawn bond does.
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
                     `add_bond`/`can_bond` join two *existing* atoms,
                     `merge` appends another structure as a clear fragment,
                     and `reattach`/`can_reattach`/`moving_fragment` unhook
                     an atom (with everything hanging off it) onto a new
                     anchor. `angle(i,j,k)` (degrees, at j) and
                     `bond_between` serve the structure outline.
                     `_model(..., poly=True)` interleaves translucent
                     coordination-polyhedron **polygons** into the same
                     depth sort as the spheres (so a centre atom shows
                     through its own front faces), and `colors=` applies a
                     crystal's element/site override map. An atom's optional
                     5th slot is its colour; `atom_specs(label=True)` emits
                     a real centred **text** spec (the flag used to set a
                     key nothing rendered).
                     `Molecule.cell_visible` (persisted, format 4) switches the cell/slab outline
                     off: renderers draw `shown_edges`, not `edges`.
                     `Molecule` carries the **lattice state** — `cells`,
                     `tilts`, `colors`, `poly` — plus `rebuild()` (regenerate
                     a crystal for the current cells/tilts, refreshing
                     `owners`/`members`), `cell_of` (one home cell),
                     `cell_members` (the whole cell), `prune_tilts`,
                     `can_stack` and
                     `_frozen_fit` (a supercell's layout is anchored to its
                     **untilted** geometry, else tilting one cell would
                     chase its protruding corners and rescale the whole
                     crystal).
  - `smiles.py`    — Qt-free **SMILES reader + 3D embedder** (ported from
                     KherveCAD `molecule.py`): `parse_smiles`, implicit H,
                     VSEPR electron-domain shapes with lone pairs, whole-ring
                     placement (polygons, fused rings), a light relaxation;
                     `from_smiles` → `Compound` (atoms/bonds/charges, Å),
                     `formula_of` (parse-only Hill formula), `formula_counts`.
                     Aromatic bonds are 1.5 here; `chem.kekulize` turns them
                     into 1/2 for the viewer.
  - `compounds.py`, `compounds_more.py`, `compounds_extra.py` — the **700+
                     compound library** `COMPOUNDS[key] = (name, SMILES,
                     category, formula)`: KherveCAD's 490 + extra elements /
                     oxides / salts / halides + the unique entries of
                     `catalog` absorbed at import (`_absorb_catalog`).
                     `get(key|name|alias)` → `Compound`; `ALIASES` (ethene →
                     ethylene …). Formulas in `compounds_extra` and absorbed
                     rows are *computed* from the SMILES.
  - `crystal.py`, `crystal_library.py` — `Crystal` (lattice + every atom of
                     the conventional cell as fractions; density / nearest
                     distance for tests) and **122 crystals** in six
                     families, built from prototype functions (`fcc`, `bcc`,
                     `hcp`, `diamond`, `zinc_blende`, `rock_salt`, `fluorite`,
                     `wurtzite`, `rutile` …). Tests pin every entry to its
                     density and nearest-neighbour distance.
  - `surface.py`   — slab of any crystal cut along (hkl): `parse_miller`,
                     `in_plane_basis` (primitive 2D cell, centring-aware),
                     `surface_cell`, `widest_gap` termination. Bulk-terminated.
  - `nano.py`      — graphene (AA/AB/ABA/ABC, twisted), ribbons, dots,
                     vacancies / N-doping, graphite surface, (n,m) nanotubes,
                     fullerenes (C20/C60/C70… capped tubes).
  - `chem.py`      — the bridge to the viewer: `to_model` (Compound →
                     `model.Molecule`, Kekulé-fied, **principal-axis
                     oriented** so flat molecules face the viewer),
                     `crystal_model` / `crystal_stack` (a library crystal is a
                     stackable `crystal:<key>` Molecule: `Molecule.rebuild`
                     tiles its closed cell with `supercell.tile`, so the
                     KhervePaint tilt-as-a-defect works on all 122 crystals;
                     bonds are found on the *untilted* block and applied by
                     index; `boundary=False` gives a fixed `cell:<key>`
                     block), `surface_model` (auto-sized slab),
                     `nano_model`, `find_bonds`, `orient`.
  - `reactions.py` — `solve(text)` → `Reaction` (parse, exact rational
                     balance over atoms **and charge**, `source` / `equation`),
                     `layout(rx)` → a `Molecule` whose `notes` carry the
                     coefficients, `+`, arrow (double for ⇌) and formulas;
                     `EXAMPLES` = 36 classics (a test balances and lays out
                     every one).
  - `rxanim.py`    — reaction **animation** (Qt-free): `map_atoms` pairs each
                     reactant atom with a product atom of the same element
                     (seed by neighbourhood signature + distance, then swap
                     hill-climbing on: bonds kept, neighbours in the same
                     product molecule, least travel); `Animation` keyframes
                     A spread → B packed → C products packed → D spread, bonds
                     switch reactant→product at p=0.5; `apply(mol,p)` mutates
                     the scene (reactant atoms only), `restore` brings the
                     static equation back. Built by `reactions._animation`
                     (None for fractional coefficients); `Molecule.reaction`
                     (persisted) lets `reactions.attach_animation` rebuild it
                     after a load. `Viewer3D` has the Animate row (play /
                     scrub / speed / loop).
  - `entries.py`   — every library leaf is a `(kind, value)` pair
                     (`model|compound|smiles|crystal|surface|nano|reaction`);
                     `build` makes the `Molecule`, `sections()` feeds the
                     tree and the Explorer, `build_smiles` prefers RDKit and
                     falls back to `chem.smiles_model`. Values with options are
                     query strings (`cu?cells=2,2,2`, `si:111?layers=4`,
                     `graphene?width=3&layers=2`).
  - `updater.py`   — **auto-update from GitHub** for a source checkout: `check`
                     (`git fetch` + ahead/behind/dirty vs the upstream),
                     `fast_forward` (only when strictly behind and clean),
                     `changelog_markdown` (commit subjects by `feat:`/`fix:`),
                     `CheckWorker` (QThread) and the `Updater` controller
                     (Help ▸ Check for Updates… / Update Automatically;
                     `schedule()` is called only by `app.main`, so tests never
                     fetch; `KHERVEMOL_NO_UPDATE=1` disables). Non-git installs
                     compare against the latest GitHub release. Tests use
                     temporary local repos. No installer / DMG pipeline exists
                     (KherveCAD has one), so there is nothing to download.
  - `shelf.py`, `shelf_panel.py` — **"My molecules"**: `Shelf` keeps named
                     molecules (atoms + bonds, JSON in the user state dir,
                     `KHERVEMOL_STATE_DIR` overrides — tests set it to a temp
                     folder) with `add / rename / move / remove / compound /
                     model`; `token(name)` = `@Molecule_1`. `reactions.resolve`
                     understands `@name` (via `shelf.default()`), `entries`
                     has kind `mine`, and `ShelfPanel` is the dock tabbed
                     beside the Library (Keep / Load / Rename / reorder /
                     Delete / Use in a reaction; rows drag onto the views).
                     `ReactionDialog` has the *My molecules* row
                     (`insert_species`).
  - `adsorbates.py` — molecules lying on a surface, as **groups** (`Molecule.groups`
                     = `{"name","start","count"}`, persisted in the `.kmol`, format
                     5): `add` (orient flat/upright/as drawn, spin, first free spot
                     on a spiral), `translate`, `rotate` (about the group's own
                     centre), `place` (absolute x/y/height above the top layer),
                     `drag` (screen drag → in-plane slide, or lift), `remove`
                     (re-indexes atoms, bonds and later groups), `pose`.
                     `Viewer3D` has the *On the surface* row (`_group_row`,
                     `nudge_group`, `add_group`, `remove_current_group`) and both
                     views drag a group atom in `mouseMoveEvent` (mode "group").
                     `builders_ui._AdsorbateRows` is shared by `SurfaceDialog` and
                     `AddMoleculeDialog`; MCP has `add_to_surface`,
                     `move_adsorbate`, `remove_adsorbate`.
  - `meshexport.py`, `chemexport.py`, `exports_ui.py` — **export formats**.
                     `meshexport` (Qt-free): `build_mesh(mol, style, scale
                     mm/Å, quality, cell, min_stick_mm)` → `Mesh` (UV spheres +
                     two-colour bond cylinders, outward-wound closed shells, z up
                     standing on z=0) and writers STL (binary/ASCII), 3MF
                     (`basematerials`, one per colour), OBJ+MTL, PLY, GLB;
                     `export(mol, path)`. `chemexport` (Qt-free): XYZ, MOL/SDF
                     V2000, PDB (CRYST1 + CONECT), CIF (P1; cell from
                     `crystal:<key>` lattice × cells, a single-parallelepiped
                     outline, or the outline's bounding box; periodic crystals
                     wrapped + de-duplicated). `exports_ui`: `MeshDialog`, the
                     File ▸ Export 3D model… / Export chemistry file… actions and
                     toolbar buttons; MCP `export_model` takes the same options.
  - `polymers.py`  — Qt-free polymer chains: `PRESETS` (40 repeat units as
                     SMILES fragments + end caps, five families),
                     `chain_smiles(unit, n, head, tail)`, `build_chain`,
                     `max_units`. A polymer is just a long molecule built by
                     `smiles`; `entries` kind `polymer` (`pvc?n=6`,
                     `custom?unit=…&n=…`).
  - `maintools.py` — the two **toolbars**: top row = files + a split button
                     per library (face = builder, arrow = the same menu the
                     menubar shows, via `MainWindow._menus`), second row =
                     drawing tools (2D tools synced to `Editor2D.tool`,
                     element combo, 3D add / order / bond / delete / labels /
                     lock, 3D↔2D, film). `MainWindow._sync_tool_states`
                     enables what applies. Menus are built from
                     `entries.sections()` by `_add_groups`, so menus, tree
                     and toolbar can never disagree.
  - `builders_ui.py` — Crystal / Surface / Nano / Polymer / Reaction dialogs; each has
                     `entry()` → `(kind, value, label)`.
  - `glview.py`, `glshaders.py` — the **OpenGL viewer**: `Scene` (CPU layout,
                     projection identical to `model._proj`, hit-testing,
                     vertex arrays — testable offscreen) and `GLView`
                     (`QOpenGLWidget`, GLSL 120 impostors, 4× MSAA, gradient
                     background, selection halos, QPainter overlay for labels
                     and `notes`, FBO `render_image`). `Viewer3D.set_renderer`
                     swaps `GLView` ⇄ classic `_View`; any GL failure falls
                     back automatically. Offscreen / `KHERVEMOL_RENDERER=
                     classic` always use classic (the test suite does).
  - `library.py`   — the original hand-placed models ("Classic 3D models"). `model_data(name, cells, tilts,
                     owners)` tiles a crystal via `supercell.tile`;
                     `can_stack` / `lattice_vectors` gate and steer it. The
                     six `lattices.MODELS` join `_MODELS`/`LABELS` and the
                     `Lattice systems` category. `_site()` places an atom on
                     a hidden lattice site with its `SITE_COLORS` tint. `_mol_*` / `_xtal_*` builders
                     return `(atoms, bonds, edges)`; `make(name)` wraps one
                     in a `Molecule`. 30+ entries in `CATEGORIES`: simple
                     molecules, alcohols & acids, hydrocarbons, polymers
                     (zig-zag backbone), and crystal unit cells (simple
                     cubic / BCC / FCC / HCP / diamond / NaCl / CsCl / zinc
                     blende / fluorite / perovskite, drawn as wireframe
                     cells; perovskite/zinc-blende include their internal
                     bonds). `is_crystal`/`default_bond`/`label`/`names`.
  - `render.py`    — shape-spec → `QGraphicsItem` (`spec_to_item`,
                     `add_specs`; `polygon` + `opacity` for the polyhedra,
                     and `anchor: "center"` on a text spec) with the sun/linear/radial gradient
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
                     for the structure outline. Accepts library **drops**
                     (`dnd.MIME_COMPOUND` → `compound_dropped` →
                     `MainWindow._on_drop_compound_3d` → `add_molecule`, which
                     `model.merge`s the compound in as a clear second fragment
                     — or replaces an empty view / a crystal), and
                     `reattach` serves the structure tree's drag. Crystals are
                     rotatable/zoomable but not atom-editable (`editable` =
                     not crystal) — though their atoms **are** tagged for
                     hit-testing, since clicking one is how you pick a cell
                     to tilt or a site to recolour.
                     The **crystal panel**: a Supercell row (three spins,
                     `set_cells` → `Molecule.rebuild`) and a Tilt-cell row
                     (`set_tilt`, which **keeps the selection** — a tilt
                     does not renumber, so the atom you picked stays picked
                     and the next spin turn hits the same cell; only a tilt
                     applied from a menu picks an atom, and it must be one
                     the cell *owns* or a shared corner would redirect the
                     next turn), both hidden for a molecule;
                     `tilt_cell`/`tilt_cell_atoms` say which cell would
                     rotate, and `_View.rebuild` rings it in dashed orange
                     so the target is visible before you turn anything; plus `pick_color`/`reset_colors`, a `Legend`
                     toggle (`_legend_specs`, drawn beside the model and
                     included in export) and a `Polyhedra` toggle, all of
                     which suit either kind of structure.
  - `dnd.py`       — drag-and-drop payloads: `MIME_COMPOUND` (a library leaf,
                     `"kind|value"`, dropped on either view) and `MIME_ATOM`
                     (a structure-tree row), plus `encode`/`decode`.
  - `structure_tree.py` — `StructureTree(QTreeWidget)`: the molecule as a
                     connectivity outline in the **left top** dock, above the
                     library. `walk(atoms, bonds)` is a DFS spanning tree
                     yielding `(atom, parent, grandparent, order, ring)` —
                     heavy atoms before hydrogens, ring bonds emitted once as
                     leaves (nesting them would loop), every disconnected
                     fragment rooted off the top. `_root_atom` starts at an
                     endpoint of the heavy-atom **diameter** and
                     `_continuations` renders each atom's biggest child at the
                     *same* indent, so a backbone is a flat list and only real
                     branches nest (a chain used to stair-step off the panel).
                     Columns are Atom / Bond order / Length (Å) / Angle (° at
                     the parent, from `model.angle`); the tooltip adds Z,
                     weight, free valence, coordinates and the ideal bond
                     length. Two-way selection with the viewer
                     (`atom_selected` ↔ `show_atom`, `_quiet` guards the
                     echo). **Dragging a row onto another** re-bonds that atom
                     (`can_drop` gates the drag with `model.can_reattach`, so
                     an impossible drop shows a "no" cursor; the drop emits
                     `reattach_requested` → `MainWindow._on_reattach` →
                     `Viewer3D.reattach`). Qt never reorders rows itself.
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
                     A **Show as** combo switches representation
                     (`molrepr.MODES`); Lewis and condensed are read-only
                     views (`editable` is False there, so a click cannot
                     move an atom you can no longer see), and `formula()`
                     counts implicit hydrogens.
                     `MainWindow._sync_sketch` mirrors the 3D `Molecule`
                     into it on load / build / 3D edit — via RDKit's clean
                     `Compute2DCoords` depiction when available, else
                     `_flatten_2d` (project + drop explicit H). The reverse
                     is on demand: `build_3d_from_sketch` (Ctrl+B / context
                     menu) turns the sketch graph → SMILES → 3D.
  - `periodic.py`  — `PeriodicPicker`: the **full** periodic-table grid
                     (all 118 elements, atomic number + symbol per cell,
                     CPK-coloured, f-block below) built from
                     `elements.table_cells()`. `PeriodicWindow` holds it in a
                     non-modal tool window opened by the toolbar Table
                     button / View menu / Ctrl+T (no longer a dock); sets the active drawing
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
                     the rich descriptors. A crystal reports its **lattice**
                     instead (`_crystal_rows`): lattice parameters,
                     supercell and cell count, tilted cells, coordination
                     number per element — and its mass row is "Mass drawn",
                     since a lattice has no molar mass and a stacked cell's
                     formula is not the stoichiometric unit.
  - `document.py`  — the `.kmol` JSON format (both the 3D `Molecule` incl.
                     crystal edges + view + lattice state, and the 2D
                     sketch) and PNG export. `FORMAT_VERSION` = 2 added
                     `cells`/`tilts`/`colors`/`poly` and the per-atom colour
                     slot; v1 still loads. A crystal is `rebuild()`-ed on
                     load so `owners` comes back with it.
  - `svgexport.py` — **KhervePaint-compatible SVG** writer. `specs_to_svg`
                     turns shape specs into KhervePaint's own SVG shape
                     (spheres → `<ellipse>` with an `objectBoundingBox`
                     radial "sun" gradient written light-first,
                     `cx=0.35 cy=0.35 r=0.95 fx=0.25 fy=0.25`; bonds →
                     `<line>`), so a molecule opens in KhervePaint as
                     editable gradient-filled items (verified against
                     `khervepaint.svgio.load_svg`). A `polygon` spec becomes KhervePaint's
                     editable `PolygonItem`, and only `anchor: "center"` text is
                     centred (it used to centre everything, which sat the
                     legend's labels on top of their spheres).
                     `sketch_specs(..., mode=)` makes the 2D line/label
                     specs for the current `molrepr` mode; `normalize` fits the
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
  - `mcp_*.py`    — the **MCP server** (KherveCAD's architecture, renamed):
                     `mcp_server.py` is the Qt-free stdio JSON-RPC server an
                     assistant launches (`python -m khervemol.mcp_server` /
                     `KherveMol.py --mcp-server`); it forwards `tools/call` over
                     a loopback socket to `mcp_bridge.McpBridge` (in-app
                     `QTcpServer` on 127.0.0.1, random token in a 0600
                     `mcp-bridge.json` in the per-user state dir —
                     `KHERVEMOL_STATE_DIR` overrides; **off until the user
                     enables it**; access levels read / edit / full).
                     `mcp_http.py` is the same bridge as Streamable HTTP
                     (Origin + bearer checked). `mcp_schema.py` (Qt-free) holds
                     the tool table and `check_args`, the validation layer;
                     `mcp_tools.py` runs each tool on the GUI thread against the
                     live `MainWindow` (never a modal dialog); `mcp_library.py`
                     has the list / search / resolve helpers; `mcp_hosts.py`
                     writes the config entry into Claude Desktop / Claude Code /
                     Cursor / …; `mcp_dialog.py` is the AI ▸ Connect to Claude
                     (MCP)… dialog and `install(window)`. A new tool = a
                     `TOOLS` entry + a `_t_<name>` method (+ a mention in the
                     server `_INSTRUCTIONS`); `tests/test_mcp.py` enforces it.
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
- The **3D viewer** draws with OpenGL (`glview.py`) by default; the classic
  `_model` path depth-sorts atoms by the projected `depth` and draws
  far-to-near (edges, bonds, then spheres). Both use the same isometric
  az/el projection (`model._proj`), so orientation, hit-testing, drag and
  exports agree. Orbit/zoom just change the projection angles / view scale.
- `Molecule.notes` are scene annotations (reaction text / arrows) in world
  Å; drawn by `model.note_specs` (classic) and `GLView._paint_notes` (GL);
  persisted in the `.kmol`.
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
it, **but the app must still run without it** (SMILES, the whole library,
crystals, surfaces and reactions all build with the pure-Python `smiles`
embedder; RDKit only refines geometry, imports structure files and writes
SMILES from a structure): `rdkit_io.py` imports
`rdkit` behind a `try/except` and exposes `available()`. Never import
`rdkit` at module top-level anywhere else. New RDKit-backed features go in
`rdkit_io.py` (guarded), get a menu item gated on `rdkit_io.available()`,
and a test marked `skipif(not rdkit_io.available())`.

## Adding a crystal / lattice system

A cubic-family cell is an `_xtal_*` builder in `library.py` (see above). A
system defined by lattice **parameters** goes in `lattices.PARAMS` instead
— `(element, a, b, c, α, β, γ)` — and everything else follows: the builder,
`LATTICE_VECTORS` (so `supercell.tile` stacks it in the right skewed
orientation), the label, the parameter read-out and the registry entry.
Put an atom on a **hidden site** (a body/face centre, an interior hole) with
`library._site(atoms, el, p, site)`, never a plain `_add`: the same element
as the corners is invisible against them without its `SITE_COLORS` tint.
`tests/test_crystal.py` parametrises over the lattice systems and the
stackable crystals, so a new entry is covered automatically.

## Roadmap

- CIF → crystal import (still guarded/optional).
- User-editable lattice parameters (a, b, c, α, β, γ) on a loaded system,
  persisted in the `.kmol` file, rather than the illustrative defaults.
- 2D sketch → 3D without RDKit: write SMILES from the sketch graph so
  `smiles.from_smiles` can embed it (only the reverse direction is offline
  today).
- Reaction film: curved atom paths and bond fade instead of a hard switch.
- Measure tool (bond lengths / angles); multiple molecules per document.

## Commit / push policy

**Every change must land as a commit on the `dev` branch and be pushed
immediately.** No batching. No `Co-Authored-By:` trailer. Commit subjects
under 70 chars; body explains *why*, not what.

**Commit message prefix** — every subject must start with one of:
`fix:` `feat:` `refactor:` `style:` `docs:` `perf:`.

## Licensing

GPL-3.0. New source files must carry the short GPL notice at the top.
