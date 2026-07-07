"""Compound-catalog tests.

Structural checks always run; the SMILES-validity check runs only when
RDKit is installed (so a bad catalog entry is caught in a full install).

Copyright (C) 2026 Gwilherm Kerherve

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
"""

import pytest

from khervemol import catalog, rdkit_io


def test_catalog_is_populated():
    entries = catalog.all_entries()
    assert len(entries) >= 300          # curated families + generated series
    # every entry has a non-empty name and SMILES
    for name, smi in entries:
        assert name and smi


def test_generated_series_present():
    names = {n for n, _s in catalog.all_entries()}
    assert {"Methane", "Octane", "Cyclohexane"} <= names
    # a generated long-chain member exists
    assert "Icosane" in names


def test_grouped_matches_flat():
    flat = catalog.all_entries()
    grouped_total = sum(len(items) for _cat, items in catalog.grouped())
    assert grouped_total == len(flat)
    assert catalog.categories()             # non-empty, ordered


def test_no_duplicate_names_within_category():
    for _cat, items in catalog.grouped():
        names = [n for n, _s in items]
        assert len(names) == len(set(names))


@pytest.mark.skipif(not rdkit_io.available(), reason="RDKit not installed")
def test_every_smiles_parses():
    from rdkit import Chem
    bad = [(name, smi) for name, smi in catalog.all_entries()
           if Chem.MolFromSmiles(smi) is None]
    assert not bad, f"invalid SMILES in catalog: {bad}"
