"""Element data + periodic-table layout tests.

Copyright (C) 2026 Gwilherm Kerherve

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
"""

from khervemol import elements


def test_all_118_elements():
    assert len(elements.SYMBOLS) == 118
    assert elements.SYMBOLS[0] == "H"
    assert elements.SYMBOLS[-1] == "Og"
    assert elements.number("U") == 92
    assert elements.name("Fe") == "Iron"


def test_every_element_has_colour_and_name():
    for sym in elements.SYMBOLS:
        assert elements.color(sym).startswith("#")
        assert elements.name(sym)
        assert elements.number(sym) == elements.SYMBOLS.index(sym) + 1


def test_table_covers_every_element_once():
    cells = list(elements.table_cells())
    syms = [c[0] for c in cells]
    assert len(syms) == 118
    assert set(syms) == set(elements.SYMBOLS)
    # no two elements share a grid position
    positions = {(r, c) for _s, r, c in cells}
    assert len(positions) == 118


def test_text_colour_is_readable():
    assert elements.text_color("H") == "#111"      # white sphere -> dark ink
    assert elements.text_color("C") == "#fff"      # dark sphere -> light ink
