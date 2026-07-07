"""Element data: CPK colours, display radii, typical valence, names.

The single source of truth for per-element appearance and chemistry used
across the model engine, the 3D viewer and the 2D sketcher.

Copyright (C) 2026 Gwilherm Kerherve

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
"""

from PyQt5.QtGui import QColor

#: CPK-ish body colour per element (the sphere's mid tone).
COLORS = {
    "H": "#f4f4f4", "He": "#d9ffff", "Li": "#cc80ff", "Be": "#c2ff00",
    "B": "#f0a0a0", "C": "#3a3a3a", "N": "#3050f8", "O": "#e01f1f",
    "F": "#77d84a", "Ne": "#b3e3f5", "Na": "#9a54e0", "Mg": "#63d84b",
    "Al": "#b0b0c0", "Si": "#b89078", "P": "#ff8000", "S": "#e6c72a",
    "Cl": "#37c837", "Ar": "#80d1e3", "K": "#7d38cc", "Ca": "#3dc23d",
    "Ti": "#9aa0a6", "Cr": "#8a99c7", "Mn": "#9c7ac7", "Fe": "#e06633",
    "Co": "#f090a0", "Ni": "#50d050", "Cu": "#c86a3a", "Zn": "#7d80b0",
    "Br": "#a1443c", "I": "#8f2fbf", "Cs": "#57178f", "Au": "#e6b800",
    "Ag": "#c0c0c8", "Pt": "#cfd0dc", "Pb": "#575961",
}

#: Relative ball radius per element (tuned for a ball-and-stick look).
RADII = {
    "H": 0.36, "He": 0.40, "Li": 0.90, "Be": 0.70, "B": 0.62,
    "C": 0.58, "N": 0.56, "O": 0.55, "F": 0.52, "Ne": 0.50,
    "Na": 0.95, "Mg": 0.80, "Al": 0.82, "Si": 0.80, "P": 0.78,
    "S": 0.76, "Cl": 0.74, "Ar": 0.72, "K": 1.05, "Ca": 0.98,
    "Ti": 0.84, "Cr": 0.80, "Mn": 0.80, "Fe": 0.80, "Co": 0.78,
    "Ni": 0.78, "Cu": 0.80, "Zn": 0.80, "Br": 0.82, "I": 0.92,
    "Cs": 1.15, "Au": 0.90, "Ag": 0.92, "Pt": 0.90, "Pb": 1.00,
}

#: Typical valence (max bonds) per element — the builder tracks free bonds.
VALENCE = {"H": 1, "C": 4, "N": 3, "O": 2, "F": 1, "Cl": 1, "Br": 1,
           "I": 1, "S": 2, "P": 3, "B": 3, "Si": 4, "Na": 1, "Mg": 2,
           "Al": 3, "Ca": 2, "K": 1, "Zn": 2}

#: Atomic number per element (for labels / periodic table).
NUMBERS = {
    "H": 1, "He": 2, "Li": 3, "Be": 4, "B": 5, "C": 6, "N": 7, "O": 8,
    "F": 9, "Ne": 10, "Na": 11, "Mg": 12, "Al": 13, "Si": 14, "P": 15,
    "S": 16, "Cl": 17, "Ar": 18, "K": 19, "Ca": 20, "Ti": 22, "Cr": 24,
    "Mn": 25, "Fe": 26, "Co": 27, "Ni": 28, "Cu": 29, "Zn": 30, "Br": 35,
    "I": 53, "Cs": 55, "Au": 79, "Ag": 47, "Pt": 78, "Pb": 82,
}

#: Full element names.
NAMES = {
    "H": "Hydrogen", "He": "Helium", "Li": "Lithium", "Be": "Beryllium",
    "B": "Boron", "C": "Carbon", "N": "Nitrogen", "O": "Oxygen",
    "F": "Fluorine", "Ne": "Neon", "Na": "Sodium", "Mg": "Magnesium",
    "Al": "Aluminium", "Si": "Silicon", "P": "Phosphorus", "S": "Sulfur",
    "Cl": "Chlorine", "Ar": "Argon", "K": "Potassium", "Ca": "Calcium",
    "Ti": "Titanium", "Cr": "Chromium", "Mn": "Manganese", "Fe": "Iron",
    "Co": "Cobalt", "Ni": "Nickel", "Cu": "Copper", "Zn": "Zinc",
    "Br": "Bromine", "I": "Iodine", "Cs": "Caesium", "Au": "Gold",
    "Ag": "Silver", "Pt": "Platinum", "Pb": "Lead",
}

#: Elements offered in the Add-atom palette, in a sensible order.
PALETTE = ["H", "C", "N", "O", "F", "P", "S", "Cl", "Br", "I"]

#: (element, row, col) layout for a compact periodic-table picker. Rows/cols
#: are 1-based grid positions in the classic table (lanthanides omitted).
TABLE = [
    ("H", 1, 1), ("He", 1, 18),
    ("Li", 2, 1), ("Be", 2, 2), ("B", 2, 13), ("C", 2, 14), ("N", 2, 15),
    ("O", 2, 16), ("F", 2, 17), ("Ne", 2, 18),
    ("Na", 3, 1), ("Mg", 3, 2), ("Al", 3, 13), ("Si", 3, 14), ("P", 3, 15),
    ("S", 3, 16), ("Cl", 3, 17), ("Ar", 3, 18),
    ("K", 4, 1), ("Ca", 4, 2), ("Ti", 4, 4), ("Cr", 4, 6), ("Mn", 4, 7),
    ("Fe", 4, 8), ("Co", 4, 9), ("Ni", 4, 10), ("Cu", 4, 11), ("Zn", 4, 12),
    ("Br", 4, 17),
    ("Ag", 5, 11), ("I", 5, 17),
    ("Cs", 6, 1), ("Pt", 6, 10), ("Au", 6, 11), ("Pb", 6, 14),
]


def color(element: str) -> str:
    return COLORS.get(element, "#c8c8c8")


def radius(element: str) -> float:
    return RADII.get(element, 0.55)


def valence(element: str) -> int:
    return VALENCE.get(element, 4)


def name(element: str) -> str:
    return NAMES.get(element, element)


def text_color(element: str) -> str:
    """Readable ink colour for a chip filled with the element's colour."""
    return "#111" if QColor(color(element)).lightnessF() > 0.5 else "#fff"
