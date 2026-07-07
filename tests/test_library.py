"""Library tests — every model builds and projects to specs.

Copyright (C) 2026 Gwilherm Kerherve

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
"""

import pytest

from khervemol import library


@pytest.mark.parametrize("name", library.names())
def test_every_model_builds(name, qapp):
    mol = library.make(name)
    assert mol.atoms, name
    specs = mol.specs(400, 400)
    assert specs, name
    assert any(s["shape"] == "circle" for s in specs), name


def test_crystal_flag():
    assert library.make("diamond").crystal
    assert library.make("nacl").crystal
    assert not library.make("water").crystal


def test_crystals_carry_edges():
    mol = library.make("bcc")
    assert mol.edges, "crystal unit cell must have frame edges"


def test_labels_present():
    for name in library.names():
        assert library.label(name)
