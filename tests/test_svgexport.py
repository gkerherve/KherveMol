"""SVG export tests — the format KhervePaint reads (ellipses + sun radial
gradients + lines).

Copyright (C) 2026 Gwilherm Kerherve

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
"""

from khervemol import library, svgexport

_NS = "{http://www.w3.org/2000/svg}"


def test_spheres_become_ellipses_with_sun_gradients(qapp):
    mol = library.make("water")
    root = svgexport.specs_to_svg(mol.specs(200, 200), 200, 200)
    ellipses = list(root.iter(_NS + "ellipse"))
    assert len(ellipses) == len(mol.atoms)          # one per atom
    for e in ellipses:
        for attr in ("cx", "cy", "rx", "ry"):
            assert e.get(attr) is not None
    assert list(root.iter(_NS + "line"))            # bonds present
    # sun gradients: off-centre radial (cx=0.35), object bounding box,
    # written light-colour-first — exactly how KhervePaint reads them back
    suns = [g for g in root.iter(_NS + "radialGradient")
            if g.get("cx") == "0.35"]
    assert suns
    g = suns[0]
    assert g.get("gradientUnits") == "objectBoundingBox"
    assert list(g)[0].get("offset") == "0"


def test_svg_header(qapp):
    root = svgexport.specs_to_svg(library.make("methane").specs(200, 200),
                                  200, 200)
    assert root.get("viewBox") == "0 0 200 200"
    assert root.get("width", "").endswith("in")


def test_sketch_specs(qapp):
    specs = svgexport.sketch_specs([["C", 0, 0], ["O", 40, 0]], [[0, 1, 2]])
    assert any(s["shape"] == "line" for s in specs)
    assert any(s["shape"] == "text" and s["text"] == "O" for s in specs)
    # carbon stays an implicit vertex (no label) with skeletal defaults
    assert not any(s.get("text") == "C" for s in specs)


def test_normalize_shifts_to_margin():
    specs = [{"shape": "line", "x1": -10, "y1": -10, "x2": 5, "y2": 5,
              "stroke": "#000", "width": 2}]
    out, w, h = svgexport.normalize(specs, margin=10)
    assert out[0]["x1"] == 10 and out[0]["y1"] == 10     # min at (margin,margin)
    assert w == 35 and h == 35                            # span 15 + 2*margin
