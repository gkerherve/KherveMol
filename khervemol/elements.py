"""Element data: CPK colours, display radii, typical valence, names.

The single source of truth for per-element appearance and chemistry used
across the model engine, the 3D viewer and the 2D sketcher. Covers the
whole periodic table (Z = 1..118): full names, atomic numbers and Jmol
CPK colours, plus tuned ball-and-stick radii / valences for the common
elements and sensible defaults for the rest.

Copyright (C) 2026 Gwilherm Kerherve

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
"""

from PyQt5.QtGui import QColor

#: Element symbols in atomic-number order (index 0 == Z 1).
SYMBOLS = [
    "H", "He", "Li", "Be", "B", "C", "N", "O", "F", "Ne", "Na", "Mg", "Al",
    "Si", "P", "S", "Cl", "Ar", "K", "Ca", "Sc", "Ti", "V", "Cr", "Mn", "Fe",
    "Co", "Ni", "Cu", "Zn", "Ga", "Ge", "As", "Se", "Br", "Kr", "Rb", "Sr",
    "Y", "Zr", "Nb", "Mo", "Tc", "Ru", "Rh", "Pd", "Ag", "Cd", "In", "Sn",
    "Sb", "Te", "I", "Xe", "Cs", "Ba", "La", "Ce", "Pr", "Nd", "Pm", "Sm",
    "Eu", "Gd", "Tb", "Dy", "Ho", "Er", "Tm", "Yb", "Lu", "Hf", "Ta", "W",
    "Re", "Os", "Ir", "Pt", "Au", "Hg", "Tl", "Pb", "Bi", "Po", "At", "Rn",
    "Fr", "Ra", "Ac", "Th", "Pa", "U", "Np", "Pu", "Am", "Cm", "Bk", "Cf",
    "Es", "Fm", "Md", "No", "Lr", "Rf", "Db", "Sg", "Bh", "Hs", "Mt", "Ds",
    "Rg", "Cn", "Nh", "Fl", "Mc", "Lv", "Ts", "Og",
]

_NAMES = [
    "Hydrogen", "Helium", "Lithium", "Beryllium", "Boron", "Carbon",
    "Nitrogen", "Oxygen", "Fluorine", "Neon", "Sodium", "Magnesium",
    "Aluminium", "Silicon", "Phosphorus", "Sulfur", "Chlorine", "Argon",
    "Potassium", "Calcium", "Scandium", "Titanium", "Vanadium", "Chromium",
    "Manganese", "Iron", "Cobalt", "Nickel", "Copper", "Zinc", "Gallium",
    "Germanium", "Arsenic", "Selenium", "Bromine", "Krypton", "Rubidium",
    "Strontium", "Yttrium", "Zirconium", "Niobium", "Molybdenum",
    "Technetium", "Ruthenium", "Rhodium", "Palladium", "Silver", "Cadmium",
    "Indium", "Tin", "Antimony", "Tellurium", "Iodine", "Xenon", "Caesium",
    "Barium", "Lanthanum", "Cerium", "Praseodymium", "Neodymium",
    "Promethium", "Samarium", "Europium", "Gadolinium", "Terbium",
    "Dysprosium", "Holmium", "Erbium", "Thulium", "Ytterbium", "Lutetium",
    "Hafnium", "Tantalum", "Tungsten", "Rhenium", "Osmium", "Iridium",
    "Platinum", "Gold", "Mercury", "Thallium", "Lead", "Bismuth", "Polonium",
    "Astatine", "Radon", "Francium", "Radium", "Actinium", "Thorium",
    "Protactinium", "Uranium", "Neptunium", "Plutonium", "Americium",
    "Curium", "Berkelium", "Californium", "Einsteinium", "Fermium",
    "Mendelevium", "Nobelium", "Lawrencium", "Rutherfordium", "Dubnium",
    "Seaborgium", "Bohrium", "Hassium", "Meitnerium", "Darmstadtium",
    "Roentgenium", "Copernicium", "Nihonium", "Flerovium", "Moscovium",
    "Livermorium", "Tennessine", "Oganesson",
]

NUMBERS = {sym: i + 1 for i, sym in enumerate(SYMBOLS)}
NAMES = {sym: _NAMES[i] for i, sym in enumerate(SYMBOLS)}

#: Standard Jmol CPK colours for every element (fallback appearance).
_JMOL = {
    "H": "#ffffff", "He": "#d9ffff", "Li": "#cc80ff", "Be": "#c2ff00",
    "B": "#ffb5b5", "C": "#909090", "N": "#3050f8", "O": "#ff0d0d",
    "F": "#90e050", "Ne": "#b3e3f5", "Na": "#ab5cf2", "Mg": "#8aff00",
    "Al": "#bfa6a6", "Si": "#f0c8a0", "P": "#ff8000", "S": "#ffff30",
    "Cl": "#1ff01f", "Ar": "#80d1e3", "K": "#8f40d4", "Ca": "#3dff00",
    "Sc": "#e6e6e6", "Ti": "#bfc2c7", "V": "#a6a6ab", "Cr": "#8a99c7",
    "Mn": "#9c7ac7", "Fe": "#e06633", "Co": "#f090a0", "Ni": "#50d050",
    "Cu": "#c88033", "Zn": "#7d80b0", "Ga": "#c28f8f", "Ge": "#668f8f",
    "As": "#bd80e3", "Se": "#ffa100", "Br": "#a62929", "Kr": "#5cb8d1",
    "Rb": "#702eb0", "Sr": "#00ff00", "Y": "#94ffff", "Zr": "#94e0e0",
    "Nb": "#73c2c9", "Mo": "#54b5b5", "Tc": "#3b9e9e", "Ru": "#248f8f",
    "Rh": "#0a7d8c", "Pd": "#006985", "Ag": "#c0c0c0", "Cd": "#ffd98f",
    "In": "#a67573", "Sn": "#668080", "Sb": "#9e63b5", "Te": "#d47a00",
    "I": "#940094", "Xe": "#429eb0", "Cs": "#57178f", "Ba": "#00c900",
    "La": "#70d4ff", "Ce": "#ffffc7", "Pr": "#d9ffc7", "Nd": "#c7ffc7",
    "Pm": "#a3ffc7", "Sm": "#8fffc7", "Eu": "#61ffc7", "Gd": "#45ffc7",
    "Tb": "#30ffc7", "Dy": "#1fffc7", "Ho": "#00ff9c", "Er": "#00e675",
    "Tm": "#00d452", "Yb": "#00bf38", "Lu": "#00ab24", "Hf": "#4dc2ff",
    "Ta": "#4da6ff", "W": "#2194d6", "Re": "#267dab", "Os": "#266696",
    "Ir": "#175487", "Pt": "#d0d0e0", "Au": "#ffd123", "Hg": "#b8b8d0",
    "Tl": "#a6544d", "Pb": "#575961", "Bi": "#9e4fb5", "Po": "#ab5c00",
    "At": "#754f45", "Rn": "#428296", "Fr": "#420066", "Ra": "#007d00",
    "Ac": "#70abfa", "Th": "#00baff", "Pa": "#00a1ff", "U": "#008fff",
    "Np": "#0080ff", "Pu": "#006bff", "Am": "#545cf2", "Cm": "#785ce3",
    "Bk": "#8a4fe3", "Cf": "#a136d4", "Es": "#b31fd4", "Fm": "#b31fba",
    "Md": "#b30da6", "No": "#bd0d87", "Lr": "#c70066", "Rf": "#cc0059",
    "Db": "#d1004f", "Sg": "#d90045", "Bh": "#e00038", "Hs": "#e6002e",
    "Mt": "#eb0026", "Ds": "#c9c9c9", "Rg": "#c9c9c9", "Cn": "#c9c9c9",
    "Nh": "#c9c9c9", "Fl": "#c9c9c9", "Mc": "#c9c9c9", "Lv": "#c9c9c9",
    "Ts": "#c9c9c9", "Og": "#c9c9c9",
}

#: Tuned ball-and-stick body colours for common elements (nicer than raw
#: Jmol for a lit-sphere look); everything else falls back to _JMOL.
COLORS = {
    "H": "#f4f4f4", "C": "#3a3a3a", "N": "#3050f8", "O": "#e01f1f",
    "F": "#77d84a", "Cl": "#37c837", "Br": "#a1443c", "I": "#8f2fbf",
    "P": "#ff8000", "S": "#e6c72a", "B": "#f0a0a0", "Si": "#b89078",
    "Na": "#9a54e0", "K": "#7d38cc", "Mg": "#63d84b", "Ca": "#3dc23d",
    "Fe": "#e06633", "Zn": "#7d80b0", "Cu": "#c86a3a", "Al": "#b0b0c0",
    "Ti": "#9aa0a6", "Cs": "#57178f",
}

#: Relative ball radius per element (ball-and-stick look); default 0.7.
RADII = {
    "H": 0.36, "He": 0.40, "Li": 0.90, "Be": 0.70, "B": 0.62,
    "C": 0.58, "N": 0.56, "O": 0.55, "F": 0.52, "Ne": 0.50,
    "Na": 0.95, "Mg": 0.80, "Al": 0.82, "Si": 0.80, "P": 0.78,
    "S": 0.76, "Cl": 0.74, "Ar": 0.72, "K": 1.05, "Ca": 0.98,
    "Ti": 0.84, "Cr": 0.80, "Mn": 0.80, "Fe": 0.80, "Co": 0.78,
    "Ni": 0.78, "Cu": 0.80, "Zn": 0.80, "Br": 0.82, "I": 0.92,
    "Cs": 1.15, "Au": 0.90, "Ag": 0.92, "Pt": 0.90, "Pb": 1.00,
}
_DEFAULT_RADIUS = 0.72

#: Typical valence (max bonds) — the builder tracks free bonds; default 4.
VALENCE = {"H": 1, "C": 4, "N": 3, "O": 2, "F": 1, "Cl": 1, "Br": 1,
           "I": 1, "S": 2, "P": 3, "B": 3, "Si": 4, "Na": 1, "Mg": 2,
           "Al": 3, "Ca": 2, "K": 1, "Zn": 2, "He": 0, "Ne": 0, "Ar": 0,
           "Kr": 0, "Xe": 0}

#: Elements offered in the 3D viewer's quick Add-atom palette.
PALETTE = ["H", "C", "N", "O", "F", "P", "S", "Cl", "Br", "I"]

# ---------------------------------------------------------- table geometry
#: Each period as a row of 18 symbols (None = a gap in that group). Period 6
#: and 7 keep La / Ac in group 3; the f-block (Ce..Lu, Th..Lr) sits below.
_PERIODS = [
    ["H"] + [None] * 16 + ["He"],
    ["Li", "Be"] + [None] * 10 + ["B", "C", "N", "O", "F", "Ne"],
    ["Na", "Mg"] + [None] * 10 + ["Al", "Si", "P", "S", "Cl", "Ar"],
    ["K", "Ca", "Sc", "Ti", "V", "Cr", "Mn", "Fe", "Co", "Ni", "Cu", "Zn",
     "Ga", "Ge", "As", "Se", "Br", "Kr"],
    ["Rb", "Sr", "Y", "Zr", "Nb", "Mo", "Tc", "Ru", "Rh", "Pd", "Ag", "Cd",
     "In", "Sn", "Sb", "Te", "I", "Xe"],
    ["Cs", "Ba", "La", "Hf", "Ta", "W", "Re", "Os", "Ir", "Pt", "Au", "Hg",
     "Tl", "Pb", "Bi", "Po", "At", "Rn"],
    ["Fr", "Ra", "Ac", "Rf", "Db", "Sg", "Bh", "Hs", "Mt", "Ds", "Rg", "Cn",
     "Nh", "Fl", "Mc", "Lv", "Ts", "Og"],
]
_LANTHANIDES = ["Ce", "Pr", "Nd", "Pm", "Sm", "Eu", "Gd", "Tb", "Dy", "Ho",
                "Er", "Tm", "Yb", "Lu"]
_ACTINIDES = ["Th", "Pa", "U", "Np", "Pu", "Am", "Cm", "Bk", "Cf", "Es",
              "Fm", "Md", "No", "Lr"]


def table_cells():
    """Yield ``(symbol, row, col)`` for the whole periodic table.

    Main body occupies rows 1..7, columns 1..18; the two f-block series sit
    in rows 9 and 10 (a blank row 8 leaves a gap), columns 4..17 — the
    classic wide layout."""
    for r, period in enumerate(_PERIODS, start=1):
        for c, sym in enumerate(period, start=1):
            if sym is not None:
                yield sym, r, c
    for c, sym in enumerate(_LANTHANIDES, start=4):
        yield sym, 9, c
    for c, sym in enumerate(_ACTINIDES, start=4):
        yield sym, 10, c


# -------------------------------------------------------------- accessors
def color(element: str) -> str:
    return COLORS.get(element) or _JMOL.get(element, "#c8c8c8")


def radius(element: str) -> float:
    return RADII.get(element, _DEFAULT_RADIUS)


def valence(element: str) -> int:
    return VALENCE.get(element, 4)


def name(element: str) -> str:
    return NAMES.get(element, element)


def number(element: str):
    return NUMBERS.get(element)


def text_color(element: str) -> str:
    """Readable ink colour for a chip filled with the element's colour."""
    return "#111" if QColor(color(element)).lightnessF() > 0.5 else "#fff"
