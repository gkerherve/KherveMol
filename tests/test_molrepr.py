"""2D representations: implicit hydrogens, Hill formulas, Lewis dots.

Copyright (C) 2026 Gwilherm Kerherve

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
"""

import math

import pytest

from khervemol import library, molrepr

#: A skeletal ethanol sketch: C–C–O, no hydrogens drawn.
_ETHANOL = ([["C", 0, 0], ["C", 40, 0], ["O", 80, 0]],
            [[0, 1, 1], [1, 2, 1]])


def test_implicit_hydrogens_fill_the_free_valence():
    atoms, bonds = _ETHANOL
    assert molrepr.implicit_hydrogens(atoms, bonds) == [3, 2, 1]


def test_a_skeletal_sketch_reports_the_real_formula():
    atoms, bonds = _ETHANOL
    assert molrepr.hill_formula(atoms, bonds) == "C₂H₆O"


def test_the_formula_does_not_double_count_explicit_hydrogens():
    atoms = [["O", 0, 0], ["H", 10, 0], ["H", -10, 0]]
    bonds = [[0, 1, 1], [0, 2, 1]]
    assert molrepr.hill_formula(atoms, bonds) == "H₂O"


def test_a_double_bond_uses_two_valences():
    """C=O is formaldehyde; the same pair single-bonded is CH₄O."""
    atoms = [["C", 0, 0], ["O", 40, 0]]
    assert molrepr.hill_formula(atoms, [[0, 1, 2]]) == "CH₂O"
    assert molrepr.hill_formula(atoms, [[0, 1, 1]]) == "CH₄O"


def test_hill_order_is_carbon_hydrogen_then_alphabetical():
    atoms = [["O", 0, 0], ["C", 1, 0], ["N", 2, 0], ["H", 3, 0]]
    out = molrepr.hill_formula(atoms, [], implicit=False)
    assert out.startswith("CH")
    assert out.index("N") < out.index("O")


def test_plain_digits_are_available_for_non_unicode_output():
    atoms, bonds = _ETHANOL
    assert molrepr.hill_formula(atoms, bonds,
                                unicode_subscripts=False) == "C2H6O"


# ------------------------------------------------------------------- Lewis
def test_water_oxygen_carries_two_lone_pairs():
    assert molrepr.lone_pairs("O", 2, 0) == 2
    assert molrepr.lone_pairs("N", 3, 0) == 1
    assert molrepr.lone_pairs("C", 4, 0) == 0


def test_implicit_hydrogens_consume_lone_pairs():
    """Skeletal methanol's carbon has one drawn bond but three implied H —
    it has no lone pair, and must not be drawn with one."""
    assert molrepr.lone_pairs("C", 1, 3) == 0


def test_an_unknown_element_gets_no_dots_rather_than_a_guess():
    assert molrepr.lone_pairs("Fe", 2, 0) == 0


def test_dots_come_in_pairs_and_avoid_the_bonds():
    atoms = [["O", 0.0, 0.0], ["H", 40.0, 0.0]]
    bonds = [[0, 1, 1]]
    dots = molrepr.dot_positions(0, atoms, bonds, radius=12.0, spacing=3.0)
    assert len(dots) == 2 * molrepr.lone_pairs("O", 1, 1)
    for x, y in dots:
        angle = math.degrees(math.atan2(y, x))
        assert abs(angle) > 25          # nowhere near the bond along +x


def test_no_dots_where_there_are_no_lone_pairs():
    atoms = [["C", 0.0, 0.0]]
    assert molrepr.dot_positions(0, atoms, [], 12.0, 3.0) == []


# ------------------------------------------------------------------- modes
def test_only_the_structural_modes_letter_every_atom():
    assert molrepr.shows_all_labels("lewis")
    assert molrepr.shows_all_labels("structural")
    assert not molrepr.shows_all_labels("skeletal")
    assert not molrepr.shows_all_labels("condensed")


def test_every_mode_has_a_label():
    assert set(molrepr.MODE_LABELS) == set(molrepr.MODES)


# --------------------------------------------------------------- the editor
def test_the_editor_switches_representation(qapp):
    from khervemol.editor2d import Editor2D
    e = Editor2D()
    e.set_structure(*_ETHANOL)
    assert e.formula() == "C₂H₆O"
    for mode in molrepr.MODES:
        e.set_mode(mode)
        assert e.mode == mode
        assert e.canvas.scene().items() or mode == "condensed"


def test_a_view_mode_cannot_be_drawn_on(qapp):
    from khervemol.editor2d import Editor2D
    e = Editor2D()
    e.set_structure(*_ETHANOL)
    assert e.editable
    e.set_mode("lewis")
    assert not e.editable
    e.set_mode("condensed")
    assert not e.editable
    e.set_mode("skeletal")
    assert e.editable


def test_lewis_mode_draws_dots(qapp):
    from khervemol.editor2d import Editor2D
    e = Editor2D()
    e.set_structure(*_ETHANOL)
    e.set_mode("structural")
    plain = len(e.canvas.scene().items())
    e.set_mode("lewis")
    assert len(e.canvas.scene().items()) > plain


def test_condensed_mode_draws_only_the_formula(qapp):
    from khervemol.editor2d import Editor2D
    e = Editor2D()
    e.set_structure(*_ETHANOL)
    e.set_mode("condensed")
    items = e.canvas.scene().items()
    assert len(items) == 1
    assert items[0].text() == "C₂H₆O"


def test_the_svg_export_follows_the_mode():
    from khervemol import svgexport
    atoms, bonds = _ETHANOL
    skeletal = svgexport.sketch_specs(atoms, bonds, mode="skeletal")
    lewis = svgexport.sketch_specs(atoms, bonds, mode="lewis")
    condensed = svgexport.sketch_specs(atoms, bonds, mode="condensed")
    assert len(lewis) > len(skeletal)
    assert len(condensed) == 1
    assert condensed[0]["text"] == "C₂H₆O"


def test_a_built_in_molecule_keeps_its_formula_in_2d(qapp):
    """Flattening a 3D model drops the explicit hydrogens, so the sketch's
    formula must still match the 3D one."""
    from khervemol.editor2d import Editor2D
    mol = library.make("ethanol")
    flat = [[a[0], a[1] * 40, a[2] * 40] for a in mol.atoms]
    e = Editor2D()
    e.set_structure(flat, [list(b) for b in mol.bonds])
    assert e.formula() == "C₂H₆O"
