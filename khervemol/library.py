"""Built-in molecule and crystal library.

Each ``_mol_*`` / ``_xtal_*`` builder returns ``(atoms, bonds, edges)``
where atoms are ``(element, x, y, z)``, bonds are ``(i, j, order)`` and
edges are optional unit-cell segments. `make(name)` wraps that in a
`model.Molecule` ready for the viewer. Metadata (LABELS, CATEGORIES)
drives the library menu / tree.

Copyright (C) 2026 Gwilherm Kerherve

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
"""

import math

from .model import (Molecule, TETRA, add, scale, plus, DEFAULT_AZ,
                    DEFAULT_EL)

_add, _scale, _plus = add, scale, plus


# --- small molecules -------------------------------------------------------
def _mol_water():
    a = math.radians(52.25)
    atoms, bonds = [], []
    i_o = _add(atoms, "O", (0.0, 0.0, 0.0))
    for sx in (1, -1):
        h = (0.96 * math.sin(a) * sx, 0.96 * math.cos(a), 0.0)
        bonds.append((i_o, _add(atoms, "H", h), 1))
    return atoms, bonds, None


def _mol_ammonia():
    atoms, bonds = [], []
    i_n = _add(atoms, "N", (0.0, 0.0, 0.0))
    for k in range(3):
        ang = math.radians(90 + k * 120)
        h = (0.82 * math.cos(ang), 0.82 * math.sin(ang), -0.40)
        bonds.append((i_n, _add(atoms, "H", h), 1))
    return atoms, bonds, None


def _mol_methane():
    atoms, bonds = [], []
    i_c = _add(atoms, "C", (0.0, 0.0, 0.0))
    for d in TETRA:
        bonds.append((i_c, _add(atoms, "H", _scale(d, 1.09)), 1))
    return atoms, bonds, None


def _mol_carbon_dioxide():
    atoms, bonds = [], []
    i_c = _add(atoms, "C", (0.0, 0.0, 0.0))
    for sx in (1, -1):
        bonds.append((i_c, _add(atoms, "O", (1.16 * sx, 0.0, 0.0)), 2))
    return atoms, bonds, None


def _mol_water_dimer():
    return _mol_water()


def _methyl(atoms, bonds, base_i, base_p, skip_dir):
    best = max(range(4), key=lambda k: (TETRA[k][0] * skip_dir[0]
                                        + TETRA[k][1] * skip_dir[1]
                                        + TETRA[k][2] * skip_dir[2]))
    for k in range(4):
        if k == best:
            continue
        bonds.append((base_i, _add(atoms, "H",
                                   _plus(base_p, _scale(TETRA[k], 1.09))), 1))


def _mol_methanol():
    atoms, bonds = [], []
    c = (0.0, 0.0, 0.0)
    i_c = _add(atoms, "C", c)
    o = _plus(c, _scale(TETRA[0], 1.43))
    i_o = _add(atoms, "O", o)
    bonds.append((i_c, i_o, 1))
    bonds.append((i_o, _add(atoms, "H", _plus(o, _scale(TETRA[1], 0.96))), 1))
    _methyl(atoms, bonds, i_c, c, TETRA[0])
    return atoms, bonds, None


def _mol_ethanol():
    atoms, bonds = [], []
    c1 = (0.0, 0.0, 0.0)
    i_c1 = _add(atoms, "C", c1)
    c2 = _plus(c1, _scale(TETRA[0], 1.54))
    i_c2 = _add(atoms, "C", c2)
    bonds.append((i_c1, i_c2, 1))
    o = _plus(c2, _scale(TETRA[1], 1.43))
    i_o = _add(atoms, "O", o)
    bonds.append((i_c2, i_o, 1))
    bonds.append((i_o, _add(atoms, "H", _plus(o, _scale(TETRA[2], 0.96))), 1))
    for k in (1, 2, 3):
        bonds.append((i_c1, _add(atoms, "H",
                                 _plus(c1, _scale(TETRA[k], 1.09))), 1))
    for k in (2, 3):
        bonds.append((i_c2, _add(atoms, "H",
                                 _plus(c2, _scale(TETRA[k], 1.09))), 1))
    return atoms, bonds, None


def _mol_formaldehyde():
    atoms, bonds = [], []
    i_c = _add(atoms, "C", (0.0, 0.0, 0.0))
    bonds.append((i_c, _add(atoms, "O", (0.0, 1.21, 0.0)), 2))
    for sx in (1, -1):
        bonds.append((i_c, _add(atoms, "H", (1.0 * sx, -0.6, 0.0)), 1))
    return atoms, bonds, None


def _mol_acetic_acid():
    atoms, bonds = [], []
    c1 = (0.0, 0.0, 0.0)
    i_c1 = _add(atoms, "C", c1)
    c2 = _plus(c1, _scale(TETRA[0], 1.52))
    i_c2 = _add(atoms, "C", c2)
    bonds.append((i_c1, i_c2, 1))
    o_dbl = _plus(c2, (0.0, 1.22, 0.4))
    bonds.append((i_c2, _add(atoms, "O", o_dbl), 2))
    o_oh = _plus(c2, (1.30, -0.2, -0.2))
    i_o = _add(atoms, "O", o_oh)
    bonds.append((i_c2, i_o, 1))
    bonds.append((i_o, _add(atoms, "H", _plus(o_oh, (0.6, -0.7, 0.0))), 1))
    _methyl(atoms, bonds, i_c1, c1, TETRA[0])
    return atoms, bonds, None


def _mol_ammonium():
    atoms, bonds = [], []
    i_n = _add(atoms, "N", (0.0, 0.0, 0.0))
    for d in TETRA:
        bonds.append((i_n, _add(atoms, "H", _scale(d, 1.02)), 1))
    return atoms, bonds, None


# --- rings and chains ------------------------------------------------------
def _ring_carbons(n, radius):
    pts = []
    for k in range(n):
        ang = math.radians(90 + k * 360.0 / n)
        pts.append((radius * math.cos(ang), radius * math.sin(ang), 0.0))
    return pts


def _mol_benzene():
    atoms, bonds = [], []
    ring = _ring_carbons(6, 1.39)
    idx = [_add(atoms, "C", p) for p in ring]
    for k in range(6):
        bonds.append((idx[k], idx[(k + 1) % 6], 2 if k % 2 == 0 else 1))
        p = ring[k]
        d = math.hypot(p[0], p[1]) or 1.0
        hp = (p[0] * (d + 1.09) / d, p[1] * (d + 1.09) / d, 0.0)
        bonds.append((idx[k], _add(atoms, "H", hp), 1))
    return atoms, bonds, None


def _chair_ring(n, radius, pucker):
    pts = []
    for k in range(n):
        ang = math.radians(90 + k * 360.0 / n)
        z = pucker if k % 2 == 0 else -pucker
        pts.append((radius * math.cos(ang), radius * math.sin(ang), z))
    return pts


def _mol_cyclohexane():
    atoms, bonds = [], []
    ring = _chair_ring(6, 1.45, 0.35)
    idx = [_add(atoms, "C", p) for p in ring]
    for k in range(6):
        bonds.append((idx[k], idx[(k + 1) % 6], 1))
        p = ring[k]
        d = math.hypot(p[0], p[1]) or 1.0
        for zc in (0.85, -0.85):
            hp = (p[0] * (d + 0.7) / d, p[1] * (d + 0.7) / d, p[2] + zc)
            bonds.append((idx[k], _add(atoms, "H", hp), 1))
    return atoms, bonds, None


def _mol_cyclopentane():
    atoms, bonds = [], []
    ring = _chair_ring(5, 1.30, 0.20)
    idx = [_add(atoms, "C", p) for p in ring]
    for k in range(5):
        bonds.append((idx[k], idx[(k + 1) % 5], 1))
    return atoms, bonds, None


def _mol_glucose():
    atoms, bonds = [], []
    ring = _chair_ring(6, 1.45, 0.30)
    els = ["O", "C", "C", "C", "C", "C"]
    idx = [_add(atoms, els[k], ring[k]) for k in range(6)]
    for k in range(6):
        bonds.append((idx[k], idx[(k + 1) % 6], 1))
    for k in range(1, 6):
        p = ring[k]
        d = math.hypot(p[0], p[1]) or 1.0
        op = (p[0] * (d + 1.4) / d, p[1] * (d + 1.4) / d, p[2] - 0.4)
        i_o = _add(atoms, "O", op)
        bonds.append((idx[k], i_o, 1))
        bonds.append((i_o, _add(atoms, "H", _plus(op, (0.4, 0.4, 0.6))), 1))
    return atoms, bonds, None


# --- hydrocarbon / polymer backbones --------------------------------------
_ZA = 1.54 * math.sin(math.radians(54.75))   # step along x
_ZB = 1.54 * math.cos(math.radians(54.75))   # up/down amplitude


def _backbone(n, x0=0.0):
    return [(x0 + k * _ZA, (_ZB if k % 2 else 0.0), 0.0) for k in range(n)]


def _add_substituent(atoms, bonds, c_i, at, sub):
    if sub in ("F", "Cl", "Br", "OH"):
        if sub == "OH":
            i_o = _add(atoms, "O", at)
            bonds.append((c_i, i_o, 1))
            bonds.append((i_o, _add(atoms, "H", _plus(at, (0.4, 0.5, 0.5))), 1))
        else:
            bonds.append((c_i, _add(atoms, sub, at), 1))
    elif sub == "CH3":
        i_m = _add(atoms, "C", at)
        bonds.append((c_i, i_m, 1))
        for d in (_plus(at, (0.0, 0.7, 0.7)), _plus(at, (0.7, 0.7, -0.4)),
                  _plus(at, (-0.7, 0.7, -0.4))):
            bonds.append((i_m, _add(atoms, "H", d), 1))
    elif sub == "phenyl":
        cx, cy, cz = at[0], at[1] + 1.4, at[2] + 0.6
        idx = []
        for k in range(6):
            ang = math.radians(90 + k * 60)
            idx.append(_add(atoms, "C", (cx + 1.2 * math.cos(ang),
                                         cy + 1.2 * math.sin(ang), cz)))
        for k in range(6):
            bonds.append((idx[k], idx[(k + 1) % 6], 2 if k % 2 == 0 else 1))
        bonds.append((c_i, idx[0], 1))


def _backbone_hydrogens(atoms, bonds, idx, pts, subs=None):
    subs = subs or {}
    n = len(pts)
    for k in range(n):
        p = pts[k]
        ty = 0.55 if k % 2 == 0 else -0.55
        up = (p[0], p[1] + ty, 0.95)
        dn = (p[0], p[1] + ty, -0.95)
        if k == 0 or k == n - 1:
            sign = -1.0 if k == 0 else 1.0
            ext = (p[0] + sign * 0.9, p[1] - (_ZB if k % 2 else 0.0) * 0.6, 0.0)
            bonds.append((idx[k], _add(atoms, "H", ext), 1))
        sub = subs.get(k)
        if sub is None:
            bonds.append((idx[k], _add(atoms, "H", up), 1))
        else:
            _add_substituent(atoms, bonds, idx[k], up, sub)
        bonds.append((idx[k], _add(atoms, "H", dn), 1))


def _polymer_atoms(n, pattern):
    atoms, bonds = [], []
    pts = _backbone(n)
    idx = [_add(atoms, "C", p) for p in pts]
    for k in range(n - 1):
        bonds.append((idx[k], idx[k + 1], 1))
    subs = {k: pattern(k) for k in range(n) if pattern(k) is not None}
    _backbone_hydrogens(atoms, bonds, idx, pts, subs)
    return atoms, bonds, None


def _mol_ethane():
    return _polymer_atoms(2, lambda k: None)


def _mol_propane():
    return _polymer_atoms(3, lambda k: None)


def _mol_butane():
    return _polymer_atoms(4, lambda k: None)


def _mol_ethene():
    atoms, bonds = [], []
    c1, c2 = (-0.67, 0.0, 0.0), (0.67, 0.0, 0.0)
    i1, i2 = _add(atoms, "C", c1), _add(atoms, "C", c2)
    bonds.append((i1, i2, 2))
    for (ci, cp, sx) in ((i1, c1, -1), (i2, c2, 1)):
        for sy in (1, -1):
            bonds.append((ci, _add(atoms, "H",
                                   (cp[0] + sx * 0.6, sy * 0.94, 0.0)), 1))
    return atoms, bonds, None


def _mol_ethyne():
    atoms, bonds = [], []
    c1, c2 = (-0.60, 0.0, 0.0), (0.60, 0.0, 0.0)
    i1, i2 = _add(atoms, "C", c1), _add(atoms, "C", c2)
    bonds.append((i1, i2, 3))
    bonds.append((i1, _add(atoms, "H", (-1.66, 0.0, 0.0)), 1))
    bonds.append((i2, _add(atoms, "H", (1.66, 0.0, 0.0)), 1))
    return atoms, bonds, None


def _mol_pet():
    atoms, bonds = [], []
    ring = _ring_carbons(6, 1.39)
    ridx = [_add(atoms, "C", p) for p in ring]
    for k in range(6):
        bonds.append((ridx[k], ridx[(k + 1) % 6], 2 if k % 2 == 0 else 1))
    for k in (1, 2, 4, 5):
        p = ring[k]
        d = math.hypot(p[0], p[1]) or 1.0
        bonds.append((ridx[k], _add(atoms, "H",
                     (p[0] * (d + 1.0) / d, p[1] * (d + 1.0) / d, 0.0)), 1))

    def _ester(anchor_i, base, direction):
        bx, by = base
        c = (bx + direction * 1.3, by, 0.0)
        i_c = _add(atoms, "C", c)
        bonds.append((anchor_i, i_c, 1))
        bonds.append((i_c, _add(atoms, "O", (c[0], c[1] + 1.15, 0.5)), 2))
        o1 = (c[0] + direction * 1.2, c[1] - 0.4, 0.0)
        i_o1 = _add(atoms, "O", o1)
        bonds.append((i_c, i_o1, 1))
        ch = (o1[0] + direction * 1.2, o1[1] - 0.6, 0.4)
        i_ch = _add(atoms, "C", ch)
        bonds.append((i_o1, i_ch, 1))
        for hy in (0.7, -0.7):
            bonds.append((i_ch, _add(atoms, "H",
                                     (ch[0], ch[1] + 0.4, hy + 0.4)), 1))
        return i_ch

    ch_a = _ester(ridx[0], (ring[0][0], ring[0][1]), 1)
    ch_b = _ester(ridx[3], (ring[3][0], ring[3][1]), -1)
    bonds.append((ch_a, ch_b, 1))
    return atoms, bonds, None


# ------------------------------------------------------------ crystal cells
_CORNERS = [(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0),
            (0, 0, 1), (1, 0, 1), (1, 1, 1), (0, 1, 1)]
_CUBE_PAIRS = [(0, 1), (1, 2), (2, 3), (3, 0), (4, 5), (5, 6), (6, 7), (7, 4),
               (0, 4), (1, 5), (2, 6), (3, 7)]


def _cube_corners(a):
    return [(x * a, y * a, z * a) for x, y, z in _CORNERS]


def _cube_edges(a):
    c = _cube_corners(a)
    return [(c[i], c[j], "solid") for i, j in _CUBE_PAIRS]


def _body_diagonals(a):
    c = _cube_corners(a)
    return [(c[0], c[6], "dash"), (c[1], c[7], "dash"),
            (c[2], c[4], "dash"), (c[3], c[5], "dash")]


def _crystal(el_at, a=2.0, extra_edges=None, bonds=None):
    atoms = [(e, p[0], p[1], p[2]) for e, p in el_at]
    edges = _cube_edges(a) + (extra_edges or [])
    return atoms, (bonds or []), edges


def _xtal_simple_cubic():
    a = 3.0
    return _crystal([("Cu", p) for p in _cube_corners(a)], a)


def _xtal_bcc():
    a = 3.0
    pts = [("Fe", p) for p in _cube_corners(a)]
    pts.append(("Fe", (a / 2, a / 2, a / 2)))
    return _crystal(pts, a, extra_edges=_body_diagonals(a))


def _xtal_fcc():
    a = 3.0
    pts = [("Al", p) for p in _cube_corners(a)]
    faces = [(a / 2, a / 2, 0), (a / 2, a / 2, a), (a / 2, 0, a / 2),
             (a / 2, a, a / 2), (0, a / 2, a / 2), (a, a / 2, a / 2)]
    pts += [("Al", p) for p in faces]
    c = _cube_corners(a)
    fdiag = [(c[0], c[2], "dash"), (c[4], c[6], "dash"),
             (c[0], c[5], "dash"), (c[3], c[6], "dash"),
             (c[0], c[7], "dash"), (c[1], c[6], "dash")]
    return _crystal(pts, a, extra_edges=fdiag)


def _xtal_hcp():
    atoms, r, hz = [], 1.6, 1.6
    for z in (0.0, 2 * hz):
        _add(atoms, "Mg", (0.0, 0.0, z))
        for k in range(6):
            ang = math.radians(k * 60)
            _add(atoms, "Mg", (r * math.cos(ang), r * math.sin(ang), z))
    for k in range(3):
        ang = math.radians(30 + k * 120)
        _add(atoms, "Mg", (r * 0.58 * math.cos(ang),
                           r * 0.58 * math.sin(ang), hz))
    edges = []
    top = [(r * math.cos(math.radians(k * 60)),
            r * math.sin(math.radians(k * 60)), 0.0) for k in range(6)]
    bot = [(p[0], p[1], 2 * hz) for p in top]
    for k in range(6):
        edges.append((top[k], top[(k + 1) % 6]))
        edges.append((bot[k], bot[(k + 1) % 6]))
        edges.append((top[k], bot[k]))
    return atoms, [], edges


def _xtal_diamond():
    a = 4.0
    atoms = []
    for p in _cube_corners(a):
        _add(atoms, "C", p)
    faces = [(a / 2, a / 2, 0), (a / 2, a / 2, a), (a / 2, 0, a / 2),
             (a / 2, a, a / 2), (0, a / 2, a / 2), (a, a / 2, a / 2)]
    for p in faces:
        _add(atoms, "C", p)
    inner = [(a / 4, a / 4, a / 4), (3 * a / 4, 3 * a / 4, a / 4),
             (3 * a / 4, a / 4, 3 * a / 4), (a / 4, 3 * a / 4, 3 * a / 4)]
    inner_idx = [_add(atoms, "C", p) for p in inner]
    bonds = []
    for ii in inner_idx:
        ip = (atoms[ii][1], atoms[ii][2], atoms[ii][3])
        dists = sorted(range(len(atoms)),
                       key=lambda k: (atoms[k][1] - ip[0]) ** 2
                       + (atoms[k][2] - ip[1]) ** 2
                       + (atoms[k][3] - ip[2]) ** 2)
        for k in dists[1:5]:
            bonds.append((ii, k, 1))
    return atoms, bonds, _cube_edges(a)


def _xtal_nacl():
    atoms = []
    step = 1.6
    for i in range(3):
        for j in range(3):
            for k in range(3):
                el = "Na" if (i + j + k) % 2 == 0 else "Cl"
                _add(atoms, el, (i * step, j * step, k * step))
    return atoms, [], _cube_edges(2 * step)


def _xtal_cscl():
    a = 3.0
    pts = [("Cl", p) for p in _cube_corners(a)]
    pts.append(("Cs", (a / 2, a / 2, a / 2)))
    return _crystal(pts, a, extra_edges=_body_diagonals(a))


def _tetra_interior(a):
    """The four diamond/zinc-blende interior sites in a cube of edge *a*."""
    return [(a / 4, a / 4, a / 4), (3 * a / 4, 3 * a / 4, a / 4),
            (3 * a / 4, a / 4, 3 * a / 4), (a / 4, 3 * a / 4, 3 * a / 4)]


def _face_centers(a):
    return [(a / 2, a / 2, 0), (a / 2, a / 2, a), (a / 2, 0, a / 2),
            (a / 2, a, a / 2), (0, a / 2, a / 2), (a, a / 2, a / 2)]


def _xtal_perovskite():
    """ABX3 perovskite (CaTiO3): A (Ca) at the corners, B (Ti) at the body
    centre, X (O) at the face centres — with the central TiO6 octahedron."""
    a = 3.2
    atoms = [("Ca", p[0], p[1], p[2]) for p in _cube_corners(a)]
    ti = len(atoms)
    atoms.append(("Ti", a / 2, a / 2, a / 2))
    o0 = len(atoms)
    for p in _face_centers(a):
        atoms.append(("O", p[0], p[1], p[2]))
    bonds = [(ti, o0 + k, 1) for k in range(6)]        # TiO6 octahedron
    return list(atoms), bonds, _cube_edges(a)


def _xtal_zincblende():
    """Zinc blende (ZnS): S on an FCC lattice, Zn in four tetrahedral holes,
    each Zn bonded to its four nearest S (like diamond, two elements)."""
    a = 4.0
    atoms = []
    for p in _cube_corners(a):
        _add(atoms, "S", p)
    for p in _face_centers(a):
        _add(atoms, "S", p)
    zn_idx = [_add(atoms, "Zn", p) for p in _tetra_interior(a)]
    bonds = []
    for zi in zn_idx:
        zp = (atoms[zi][1], atoms[zi][2], atoms[zi][3])
        near = sorted(range(len(atoms)),
                      key=lambda k: (atoms[k][1] - zp[0]) ** 2
                      + (atoms[k][2] - zp[1]) ** 2
                      + (atoms[k][3] - zp[2]) ** 2)
        for k in near[1:5]:
            bonds.append((zi, k, 1))
    return atoms, bonds, _cube_edges(a)


def _xtal_fluorite():
    """Fluorite (CaF2): Ca on an FCC lattice, F filling all eight
    tetrahedral holes."""
    a = 4.0
    atoms = []
    for p in _cube_corners(a):
        _add(atoms, "Ca", p)
    for p in _face_centers(a):
        _add(atoms, "Ca", p)
    for x in (a / 4, 3 * a / 4):
        for y in (a / 4, 3 * a / 4):
            for z in (a / 4, 3 * a / 4):
                _add(atoms, "F", (x, y, z))
    return atoms, [], _cube_edges(a)


# ------------------------------------------------------------------- registry
#: name -> (builder returning (atoms, bonds, edges), radius scale)
_MODELS = {
    "water": (_mol_water, 0.9), "ammonia": (_mol_ammonia, 0.9),
    "ammonium": (_mol_ammonium, 0.9),
    "methane": (_mol_methane, 0.9),
    "carbon_dioxide": (_mol_carbon_dioxide, 0.9),
    "methanol": (_mol_methanol, 0.9), "ethanol": (_mol_ethanol, 0.9),
    "formaldehyde": (_mol_formaldehyde, 0.9),
    "acetic_acid": (_mol_acetic_acid, 0.88),
    "ethane": (_mol_ethane, 0.9), "propane": (_mol_propane, 0.9),
    "butane": (_mol_butane, 0.9),
    "ethene": (_mol_ethene, 0.9), "ethyne": (_mol_ethyne, 0.9),
    "benzene": (_mol_benzene, 0.9), "cyclohexane": (_mol_cyclohexane, 0.88),
    "cyclopentane": (_mol_cyclopentane, 0.88),
    "glucose": (_mol_glucose, 0.82), "pet": (_mol_pet, 0.72),
    "simple_cubic": (_xtal_simple_cubic, 0.62), "bcc": (_xtal_bcc, 0.58),
    "fcc": (_xtal_fcc, 0.52), "hcp": (_xtal_hcp, 0.5),
    "diamond": (_xtal_diamond, 0.42), "nacl": (_xtal_nacl, 0.5),
    "cscl": (_xtal_cscl, 0.6), "perovskite": (_xtal_perovskite, 0.5),
    "zincblende": (_xtal_zincblende, 0.44), "fluorite": (_xtal_fluorite, 0.44),
}

#: Polymer repeat units share the zig-zag backbone builder.
_POLYMERS = {
    "polyethylene": lambda k: None,
    "polypropylene": lambda k: "CH3" if k % 2 == 0 else None,
    "pvc": lambda k: "Cl" if k % 2 == 0 else None,
    "ptfe": lambda k: "F",
    "polystyrene": lambda k: "phenyl" if k % 2 == 0 else None,
}
_POLYMER_LEN = 6

LABELS = {
    "water": "Water (H₂O)", "ammonia": "Ammonia (NH₃)",
    "ammonium": "Ammonium (NH₄⁺)",
    "methane": "Methane (CH₄)", "carbon_dioxide": "Carbon dioxide (CO₂)",
    "methanol": "Methanol", "ethanol": "Ethanol",
    "formaldehyde": "Formaldehyde", "acetic_acid": "Acetic acid",
    "ethane": "Ethane", "propane": "Propane", "butane": "Butane",
    "ethene": "Ethene", "ethyne": "Ethyne", "benzene": "Benzene",
    "cyclohexane": "Cyclohexane", "cyclopentane": "Cyclopentane",
    "glucose": "Glucose", "pet": "PET repeat unit",
    "polyethylene": "Polyethylene", "polypropylene": "Polypropylene",
    "pvc": "PVC", "ptfe": "PTFE", "polystyrene": "Polystyrene",
    "simple_cubic": "Simple cubic", "bcc": "BCC", "fcc": "FCC",
    "hcp": "HCP", "diamond": "Diamond", "nacl": "NaCl (rock salt)",
    "cscl": "CsCl", "perovskite": "Perovskite (CaTiO₃)",
    "zincblende": "Zinc blende (ZnS)", "fluorite": "Fluorite (CaF₂)",
}
CATEGORIES = [
    ("Simple molecules",
     ["water", "ammonia", "ammonium", "methane", "carbon_dioxide",
      "formaldehyde"]),
    ("Alcohols & acids",
     ["methanol", "ethanol", "acetic_acid", "glucose"]),
    ("Hydrocarbons",
     ["ethane", "propane", "butane", "ethene", "ethyne", "benzene",
      "cyclopentane", "cyclohexane"]),
    ("Polymers",
     ["polyethylene", "polypropylene", "pvc", "ptfe", "polystyrene", "pet"]),
    ("Crystal structures",
     ["simple_cubic", "bcc", "fcc", "hcp", "diamond", "nacl", "cscl",
      "zincblende", "fluorite", "perovskite"]),
]

#: Default bond spread for molecules (>1 so sticks read); crystals stay 1.0.
DEFAULT_BOND = 1.6


def is_crystal(name):
    return name in _MODELS and _MODELS[name][0].__name__.startswith("_xtal")


def default_bond(name):
    return 1.0 if is_crystal(name) else DEFAULT_BOND


def names():
    """All library keys, in category order."""
    out = []
    for _title, keys in CATEGORIES:
        out += keys
    return out


def model_data(name):
    """Return ``(atoms, bonds, edges, rscale)`` for a named model."""
    if name in _POLYMERS:
        atoms, bonds, edges = _polymer_atoms(_POLYMER_LEN, _POLYMERS[name])
        return atoms, bonds, edges, 0.92
    builder, rscale = _MODELS[name]
    atoms, bonds, edges = builder()
    return atoms, bonds, edges, rscale


def label(name):
    return LABELS.get(name, name.replace("_", " ").title())


def make(name):
    """Build a `model.Molecule` for library key *name*."""
    atoms, bonds, edges, rscale = model_data(name)
    return Molecule(atoms, bonds, name=name, label=label(name),
                    az=DEFAULT_AZ, el=DEFAULT_EL, bond=default_bond(name),
                    rscale=rscale, crystal=is_crystal(name), edges=edges)
