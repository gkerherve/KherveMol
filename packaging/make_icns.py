"""Render the KherveMol mark into a macOS ``.icns``.

The macOS counterpart of ``make_icon.py``: same mark, different
container. Written to an explicit path (the spec puts it under
``build/``) rather than committed, so no binary that only one platform
ever reads sits in the tree:

    python packaging/make_icns.py build/KherveMol.icns

The source is the committed 1024px export in ``packaging/icons/`` rather
than a fresh Qt render, so the icon needs neither a display nor Pillow on
the build machine. ``sips`` and ``iconutil`` are both part of macOS, so a
Mac build needs nothing installed beyond the app's own requirements;
off-macOS it falls back to Pillow's ICNS writer so the script is at least
testable there.

Regenerate the 1024px PNG after editing the mark in ``khervemol/icons.py``:
``khervemol.icons._paint_kmol(1024).save('packaging/icons/khervemol_1024.png')``.

Copyright (C) 2026 Gwilherm Kerherve

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
"""

import subprocess
import sys
import tempfile
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_SRC = _HERE / "icons" / "khervemol_1024.png"

#: (pixel size, name) for every slot in an iconset. macOS picks the @2x
#: variant on a Retina display, so each logical size is listed twice.
_SLOTS = [
    (16, "icon_16x16.png"), (32, "icon_16x16@2x.png"),
    (32, "icon_32x32.png"), (64, "icon_32x32@2x.png"),
    (128, "icon_128x128.png"), (256, "icon_128x128@2x.png"),
    (256, "icon_256x256.png"), (512, "icon_256x256@2x.png"),
    (512, "icon_512x512.png"), (1024, "icon_512x512@2x.png"),
]


def build_icns(out: Path) -> Path:
    if not _SRC.is_file():
        raise SystemExit(f"icon source missing: {_SRC}")
    out.parent.mkdir(parents=True, exist_ok=True)
    if sys.platform != "darwin":
        _build_with_pillow(out)
        return out

    with tempfile.TemporaryDirectory() as tmp:
        iconset = Path(tmp) / "KherveMol.iconset"
        iconset.mkdir()
        for size, name in _SLOTS:
            subprocess.run(
                ["sips", "-z", str(size), str(size), str(_SRC),
                 "--out", str(iconset / name)],
                check=True, stdout=subprocess.DEVNULL,
            )
        subprocess.run(["iconutil", "-c", "icns", str(iconset),
                        "-o", str(out)], check=True)
    return out


def _build_with_pillow(out: Path) -> None:
    """Off-macOS fallback — no sips/iconutil, so use Pillow."""
    from PIL import Image

    image = Image.open(_SRC).convert("RGBA")
    image.save(out, format="ICNS",
               sizes=[(s, s) for s in (16, 32, 64, 128, 256, 512, 1024)])


def main() -> None:
    out = (Path(sys.argv[1]) if len(sys.argv) > 1
           else _HERE.parent / "build" / "KherveMol.icns")
    build_icns(out)
    print(f"{out}  <-  {_SRC.name}")


if __name__ == "__main__":
    main()
