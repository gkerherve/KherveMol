#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later — part of KherveMol.
"""crystal2scad — build a crystal or surface slab with ASE and write it as a
ball-and-stick OpenSCAD file for KherveCAD (File > Open, or open_document).

Units in the .scad are nanometres (KherveCAD nm documents).

Examples
--------
# LaNb0.9Mo0.1O4 scheelite (001), 5x5 cells, 1 cell deep, random Mo, Nb/Mo-O bonds
python3 crystal2scad.py --spacegroup 88 --setting 2 --cell 5.40 5.40 11.66 \
    --basis La 0 0.25 0.625  Nb 0 0.25 0.125  O 0.1504 0.0085 0.2111 \
    --surface 0 0 1 --layers 1 --repeat 5 5 \
    --dope Nb Mo 0.1 --bond Nb O 2.1 --bond Mo O 2.1 --expect Nb 4 \
    --color Nb "#2E8B57" --color Mo "#FFB000" \
    -o LaNbMoO4_001.scad

# From a CIF, bulk 3x3x3 supercell with Si-O bonds
python3 crystal2scad.py --cif quartz.cif --repeat 3 3 3 --bond Si O 1.8 -o quartz.scad
"""
import argparse
import random
import sys
from collections import Counter

import numpy as np
from ase.build import surface
from ase.data import atomic_numbers, covalent_radii
from ase.data.colors import jmol_colors
from ase.io import read
from ase.neighborlist import neighbor_list
from ase.spacegroup import crystal


def parse_args():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    src = p.add_argument_group("structure (a CIF, or space group + cell + basis)")
    src.add_argument("--cif")
    src.add_argument("--spacegroup", type=int)
    src.add_argument("--setting", type=int, default=1, help="space-group origin choice (1 or 2)")
    src.add_argument("--cell", type=float, nargs="+", help="a b c [alpha beta gamma], Angstrom")
    src.add_argument("--basis", nargs="+", help="El x y z  El x y z ... (asymmetric unit, fractional)")
    g = p.add_argument_group("shape")
    g.add_argument("--surface", type=int, nargs=3, metavar=("H", "K", "L"), help="cut a slab along (hkl)")
    g.add_argument("--layers", type=int, default=1, help="slab depth in repeat units along the normal")
    g.add_argument("--repeat", type=int, nargs="+", default=[1, 1], help="nx ny [nz]")
    g.add_argument("--dope", nargs=3, action="append", default=[], metavar=("HOST", "DOPANT", "FRAC"))
    g.add_argument("--seed", type=int, default=7)
    b = p.add_argument_group("bonds and look")
    b.add_argument("--bond", nargs=3, action="append", default=[], metavar=("A", "B", "MAX_A"),
                   help="draw A-B bonds up to MAX_A Angstrom (repeatable)")
    b.add_argument("--no-complete", action="store_true",
                   help="do not add the ligands a bond needs from outside the slab")
    b.add_argument("--expect", nargs=2, action="append", default=[], metavar=("EL", "N"),
                   help="check every EL has exactly N bonds")
    b.add_argument("--atom-scale", type=float, default=0.5, help="x covalent radius (default 0.5)")
    b.add_argument("--bond-radius", type=float, default=0.13, help="Angstrom")
    b.add_argument("--fn", type=int, default=20, help="sphere segments (more = rounder but slower to turn)")
    b.add_argument("--bond-fn", type=int, default=8, help="bond cylinder segments")
    b.add_argument("--color", nargs=2, action="append", default=[], metavar=("EL", "#RRGGBB"))
    p.add_argument("--name", default=None)
    p.add_argument("-o", "--out", required=True)
    return p.parse_args()


def build(a):
    if a.cif:
        atoms = read(a.cif)
    else:
        if not (a.spacegroup and a.cell and a.basis):
            sys.exit("Give --cif, or --spacegroup, --cell and --basis.")
        cell = a.cell + [90, 90, 90][len(a.cell) - 3:] if len(a.cell) < 6 else a.cell
        els, pos = a.basis[0::4], [[float(v) for v in a.basis[i + 1:i + 4]] for i in range(0, len(a.basis), 4)]
        atoms = crystal(els, basis=pos, spacegroup=a.spacegroup, setting=a.setting, cellpar=cell)
    rep = a.repeat + [1] * (3 - len(a.repeat))
    if a.surface:
        atoms = surface(atoms, tuple(a.surface), a.layers, vacuum=None, periodic=True)
        rep[2] = 1
    atoms = atoms.repeat(rep)
    if a.surface:  # top at z = 0, only in-plane periodicity
        atoms.positions[:, 2] -= atoms.positions[:, 2].max()
        atoms.pbc = [True, True, False]
    rng = random.Random(a.seed)
    for host, dop, frac in a.dope:
        idx = [i for i, s in enumerate(atoms.get_chemical_symbols()) if s == host]
        for i in rng.sample(idx, round(len(idx) * float(frac))):
            atoms[i].symbol = dop
    return atoms


def bonds_of(atoms, rules):
    """(i, j, end_position) for every bonded pair allowed by rules, using periodic images."""
    if not rules:
        return []
    sym = atoms.get_chemical_symbols()
    cutoff = max(r for r in rules.values())
    I, J, D = neighbor_list("ijD", atoms, cutoff)
    out = []
    for i, j, d in zip(I, J, D):
        r = rules.get((sym[i], sym[j]))
        if r is not None and np.linalg.norm(d) <= r:
            out.append((i, j, atoms.positions[i] + d))
    return out


def cylinder(p, q, r, fn):
    """A bond as one cheap cylinder from p to q (Angstrom in, nm out)."""
    p, q = np.asarray(p) / 10, np.asarray(q) / 10
    d = q - p
    L = np.linalg.norm(d)
    tilt = np.degrees(np.arccos(d[2] / L))
    turn = np.degrees(np.arctan2(d[1], d[0]))
    return (f"  translate([{p[0]:.4f},{p[1]:.4f},{p[2]:.4f}]) rotate([0,{tilt:.2f},{turn:.2f}]) "
            f"cylinder(h={L:.4f}, r={r:.4f}, $fn={fn});  // bond")


def colour(el, overrides):
    if el in overrides:
        return overrides[el]
    r, g, b = jmol_colors[atomic_numbers[el]]
    return "#%02X%02X%02X" % (int(r * 255), int(g * 255), int(b * 255))


def main():
    a = parse_args()
    atoms = build(a)
    sym = atoms.get_chemical_symbols()
    rules = {}
    for x, y, r in a.bond:
        rules[(x, y)] = rules[(y, x)] = float(r)
    bonds = bonds_of(atoms, rules)

    # atoms to draw: the cell's own, plus (for complete polyhedra) the image ligands outside it
    draw = [(s, p) for s, p in zip(sym, atoms.positions)]
    inside = lambda p: np.allclose(p, atoms.positions[np.argmin(np.linalg.norm(atoms.positions - p, axis=1))], atol=1e-3)
    seen = {tuple(np.round(p, 3)) for _, p in draw}
    counts = Counter()
    lines = []
    first = {x for x, _, _ in a.bond}
    for i, j, end in bonds:
        if sym[i] not in first:
            continue
        counts[i] += 1
        if not inside(end):
            if a.no_complete:
                continue
            key = tuple(np.round(end, 3))
            if key not in seen:
                seen.add(key)
                draw.append((sym[j], end))
        lines.append((sym[i], atoms.positions[i], end))

    # a slab cut through a polyhedron: keep ligands only where their centre is drawn,
    # so every polyhedron is whole and the composition stays stoichiometric
    if not a.no_complete:
        ligands = {y for _, y, _ in a.bond} - first
        bonded = {tuple(np.round(q, 3)) for _, _, q in lines}
        draw = [(s, p) for s, p in draw if s not in ligands or tuple(np.round(p, 3)) in bonded]

    for el, n in a.expect:
        bad = [i for i, s in enumerate(sym) if s == el and counts[i] != int(n)]
        print(f"check {el}: {'OK' if not bad else f'{len(bad)} atoms without {n} bonds'}")

    cols = dict(a.color)
    nm = lambda p: "[%.4f,%.4f,%.4f]" % tuple(np.asarray(p) / 10)
    name = a.name or a.out.rsplit("/", 1)[-1].rsplit(".", 1)[0]
    mod = "".join(c if c.isalnum() else "_" for c in name)
    out = [f"module {mod}() {{"]
    for el in sorted({s for s, _ in draw}, key=lambda e: -atomic_numbers[e]):
        r = covalent_radii[atomic_numbers[el]] * a.atom_scale / 10
        out.append(f'color("{colour(el, cols)}") {{  // {el} atoms')
        out += [f"  translate({nm(p)}) sphere(r={r:.4f},$fn={a.fn});  // {el}" for s, p in draw if s == el]
        out.append("}")
    br = a.bond_radius / 10
    for el in sorted({c for c, _, _ in lines}):
        partners = "/".join(sorted({y for x, y, _ in a.bond if x == el}))
        out.append(f'color("{colour(el, cols)}", 0.8) {{  // {el}-{partners} bonds')
        out += [cylinder(p, q, br, a.bond_fn) for c, p, q in lines if c == el]
        out.append("}")
    out += ["}", f"{mod}();  // {name}"]
    open(a.out, "w").write("\n".join(out) + "\n")

    comp = Counter(s for s, _ in draw)
    print(f"wrote {a.out}: " + ", ".join(f"{n} {e}" for e, n in sorted(comp.items())) + f", {len(lines)} bonds")


if __name__ == "__main__":
    main()
