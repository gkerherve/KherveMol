"""A browsable catalog of named compounds (name → SMILES).

Feeds the Molecule Explorer so you can pick "Aspirin" or "Glycine" from a
searchable list instead of typing SMILES by hand. Building any of these
into 3D/2D uses the RDKit bridge (`rdkit_io`); without RDKit the names and
SMILES are still browsable and copyable.

Copyright (C) 2026 Gwilherm Kerherve

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
"""

#: (category, name, SMILES). Categories are shown in first-appearance order.
CATALOG = [
    # --- Solvents -----------------------------------------------------------
    ("Solvents", "Water", "O"),
    ("Solvents", "Methanol", "CO"),
    ("Solvents", "Ethanol", "CCO"),
    ("Solvents", "Isopropanol", "CC(C)O"),
    ("Solvents", "Acetone", "CC(=O)C"),
    ("Solvents", "Acetonitrile", "CC#N"),
    ("Solvents", "DMSO", "CS(=O)C"),
    ("Solvents", "DMF", "CN(C)C=O"),
    ("Solvents", "THF", "C1CCOC1"),
    ("Solvents", "Diethyl ether", "CCOCC"),
    ("Solvents", "Ethyl acetate", "CC(=O)OCC"),
    ("Solvents", "Chloroform", "C(Cl)(Cl)Cl"),
    ("Solvents", "Dichloromethane", "C(Cl)Cl"),
    ("Solvents", "Carbon tetrachloride", "C(Cl)(Cl)(Cl)Cl"),
    ("Solvents", "Toluene", "Cc1ccccc1"),
    ("Solvents", "Benzene", "c1ccccc1"),
    ("Solvents", "Hexane", "CCCCCC"),
    ("Solvents", "Pyridine", "c1ccncc1"),

    # --- Hydrocarbons -------------------------------------------------------
    ("Hydrocarbons", "Methane", "C"),
    ("Hydrocarbons", "Ethane", "CC"),
    ("Hydrocarbons", "Propane", "CCC"),
    ("Hydrocarbons", "Butane", "CCCC"),
    ("Hydrocarbons", "Isobutane", "CC(C)C"),
    ("Hydrocarbons", "Pentane", "CCCCC"),
    ("Hydrocarbons", "Octane", "CCCCCCCC"),
    ("Hydrocarbons", "Isooctane", "CC(C)CC(C)(C)C"),
    ("Hydrocarbons", "Ethylene", "C=C"),
    ("Hydrocarbons", "Propene", "CC=C"),
    ("Hydrocarbons", "1,3-Butadiene", "C=CC=C"),
    ("Hydrocarbons", "Acetylene", "C#C"),
    ("Hydrocarbons", "Cyclopropane", "C1CC1"),
    ("Hydrocarbons", "Cyclopentane", "C1CCCC1"),
    ("Hydrocarbons", "Cyclohexane", "C1CCCCC1"),

    # --- Aromatics & heterocycles ------------------------------------------
    ("Aromatics", "Benzene", "c1ccccc1"),
    ("Aromatics", "Toluene", "Cc1ccccc1"),
    ("Aromatics", "Phenol", "Oc1ccccc1"),
    ("Aromatics", "Aniline", "Nc1ccccc1"),
    ("Aromatics", "Styrene", "C=Cc1ccccc1"),
    ("Aromatics", "Benzaldehyde", "O=Cc1ccccc1"),
    ("Aromatics", "Nitrobenzene", "O=[N+]([O-])c1ccccc1"),
    ("Aromatics", "Naphthalene", "c1ccc2ccccc2c1"),
    ("Aromatics", "Anthracene", "c1ccc2cc3ccccc3cc2c1"),
    ("Aromatics", "Furan", "c1ccoc1"),
    ("Aromatics", "Thiophene", "c1ccsc1"),
    ("Aromatics", "Pyrrole", "c1cc[nH]c1"),
    ("Aromatics", "Imidazole", "c1c[nH]cn1"),
    ("Aromatics", "Pyridine", "c1ccncc1"),
    ("Aromatics", "Pyrimidine", "c1cncnc1"),
    ("Aromatics", "Indole", "c1ccc2[nH]ccc2c1"),

    # --- Functional-group examples -----------------------------------------
    ("Functional groups", "Formaldehyde", "C=O"),
    ("Functional groups", "Acetaldehyde", "CC=O"),
    ("Functional groups", "Acetone (ketone)", "CC(=O)C"),
    ("Functional groups", "Formic acid", "OC=O"),
    ("Functional groups", "Acetic acid", "CC(=O)O"),
    ("Functional groups", "Methylamine", "CN"),
    ("Functional groups", "Trimethylamine", "CN(C)C"),
    ("Functional groups", "Acetamide", "CC(N)=O"),
    ("Functional groups", "Urea", "NC(N)=O"),
    ("Functional groups", "Nitromethane", "C[N+](=O)[O-]"),
    ("Functional groups", "Methanethiol", "CS"),
    ("Functional groups", "Dimethyl sulfide", "CSC"),
    ("Functional groups", "Dimethyl ether", "COC"),
    ("Functional groups", "Acetonitrile (nitrile)", "CC#N"),
    ("Functional groups", "Acetic anhydride", "CC(=O)OC(C)=O"),

    # --- Carboxylic acids ---------------------------------------------------
    ("Acids", "Acetic acid", "CC(=O)O"),
    ("Acids", "Propionic acid", "CCC(=O)O"),
    ("Acids", "Butyric acid", "CCCC(=O)O"),
    ("Acids", "Oxalic acid", "OC(=O)C(=O)O"),
    ("Acids", "Lactic acid", "CC(O)C(=O)O"),
    ("Acids", "Citric acid", "OC(=O)CC(O)(CC(=O)O)C(=O)O"),
    ("Acids", "Benzoic acid", "OC(=O)c1ccccc1"),
    ("Acids", "Salicylic acid", "OC(=O)c1ccccc1O"),

    # --- Amino acids --------------------------------------------------------
    ("Amino acids", "Glycine", "NCC(=O)O"),
    ("Amino acids", "Alanine", "CC(N)C(=O)O"),
    ("Amino acids", "Serine", "OCC(N)C(=O)O"),
    ("Amino acids", "Cysteine", "SCC(N)C(=O)O"),
    ("Amino acids", "Valine", "CC(C)C(N)C(=O)O"),
    ("Amino acids", "Leucine", "CC(C)CC(N)C(=O)O"),
    ("Amino acids", "Isoleucine", "CCC(C)C(N)C(=O)O"),
    ("Amino acids", "Threonine", "CC(O)C(N)C(=O)O"),
    ("Amino acids", "Methionine", "CSCCC(N)C(=O)O"),
    ("Amino acids", "Proline", "O=C(O)C1CCCN1"),
    ("Amino acids", "Phenylalanine", "NC(Cc1ccccc1)C(=O)O"),
    ("Amino acids", "Tyrosine", "NC(Cc1ccc(O)cc1)C(=O)O"),
    ("Amino acids", "Tryptophan", "NC(Cc1c[nH]c2ccccc12)C(=O)O"),
    ("Amino acids", "Aspartic acid", "NC(CC(=O)O)C(=O)O"),
    ("Amino acids", "Glutamic acid", "NC(CCC(=O)O)C(=O)O"),
    ("Amino acids", "Asparagine", "NC(CC(N)=O)C(=O)O"),
    ("Amino acids", "Glutamine", "NC(CCC(N)=O)C(=O)O"),
    ("Amino acids", "Lysine", "NCCCCC(N)C(=O)O"),
    ("Amino acids", "Arginine", "NC(CCCNC(N)=N)C(=O)O"),
    ("Amino acids", "Histidine", "NC(Cc1c[nH]cn1)C(=O)O"),

    # --- Sugars & vitamins --------------------------------------------------
    ("Sugars & vitamins", "Glucose", "OCC1OC(O)C(O)C(O)C1O"),
    ("Sugars & vitamins", "Fructose", "OCC(=O)C(O)C(O)C(O)CO"),
    ("Sugars & vitamins", "Ribose", "OCC1OC(O)C(O)C1O"),
    ("Sugars & vitamins", "Deoxyribose", "OCC1OC(O)CC1O"),
    ("Sugars & vitamins", "Sucrose",
     "OCC1OC(OC2(CO)OC(CO)C(O)C2O)C(O)C(O)C1O"),
    ("Sugars & vitamins", "Ascorbic acid (vit C)", "OCC(O)C1OC(=O)C(O)=C1O"),

    # --- Nucleobases --------------------------------------------------------
    ("Nucleobases", "Adenine", "C1=NC2=NC=NC(=C2N1)N"),
    ("Nucleobases", "Guanine", "C1=NC2=C(N1)C(=O)NC(=N2)N"),
    ("Nucleobases", "Cytosine", "C1=CC(=NC(=O)N1)N"),
    ("Nucleobases", "Thymine", "CC1=CNC(=O)NC1=O"),
    ("Nucleobases", "Uracil", "C1=CNC(=O)NC1=O"),

    # --- Drugs & bioactive --------------------------------------------------
    ("Drugs & bioactive", "Aspirin", "CC(=O)Oc1ccccc1C(=O)O"),
    ("Drugs & bioactive", "Paracetamol", "CC(=O)Nc1ccc(O)cc1"),
    ("Drugs & bioactive", "Ibuprofen", "CC(C)Cc1ccc(cc1)C(C)C(=O)O"),
    ("Drugs & bioactive", "Caffeine", "CN1C=NC2=C1C(=O)N(C(=O)N2C)C"),
    ("Drugs & bioactive", "Nicotine", "CN1CCCC1c1cccnc1"),
    ("Drugs & bioactive", "Dopamine", "NCCc1ccc(O)c(O)c1"),
    ("Drugs & bioactive", "Serotonin", "NCCc1c[nH]c2ccc(O)cc12"),
    ("Drugs & bioactive", "Adrenaline", "CNCC(O)c1ccc(O)c(O)c1"),
    ("Drugs & bioactive", "Amphetamine", "CC(N)Cc1ccccc1"),
    ("Drugs & bioactive", "Vanillin", "O=Cc1ccc(O)c(OC)c1"),
    ("Drugs & bioactive", "Menthol", "CC(C)C1CCC(C)CC1O"),
    ("Drugs & bioactive", "Camphor", "CC1(C)C2CCC1(C)C(=O)C2"),
    ("Drugs & bioactive", "Cholesterol",
     "CC(C)CCCC(C)C1CCC2C1(CCC3C2CC=C4C3(CCC(C4)O)C)C"),

    # --- Small inorganic / gases -------------------------------------------
    ("Gases & inorganic", "Carbon dioxide", "O=C=O"),
    ("Gases & inorganic", "Carbon monoxide", "[C-]#[O+]"),
    ("Gases & inorganic", "Ammonia", "N"),
    ("Gases & inorganic", "Hydrogen peroxide", "OO"),
    ("Gases & inorganic", "Sulfur dioxide", "O=S=O"),
    ("Gases & inorganic", "Hydrogen cyanide", "C#N"),
    ("Gases & inorganic", "Ozone", "[O-][O+]=O"),
]


def categories():
    """Category titles in first-appearance order."""
    seen = []
    for cat, _name, _smi in CATALOG:
        if cat not in seen:
            seen.append(cat)
    return seen


def grouped():
    """Ordered ``[(category, [(name, smiles), ...]), ...]``."""
    out = []
    index = {}
    for cat, name, smi in CATALOG:
        if cat not in index:
            index[cat] = []
            out.append((cat, index[cat]))
        index[cat].append((name, smi))
    return out


def all_entries():
    """Flat ``[(name, smiles), ...]`` for searching/validation."""
    return [(name, smi) for _cat, name, smi in CATALOG]
