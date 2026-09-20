# -*- mode: python ; coding: utf-8 -*-
#
# PyInstaller build spec for KherveMol.
#
#   pip install pyinstaller
#   pyinstaller KherveMol.spec --noconfirm   # -> dist/KherveMol/KherveMol.exe
#
# One-dir build: starts instantly (no temp extraction). Prefer
# build_release.ps1, which first writes khervemol/VERSION (a frozen build has
# no .git, so the git-derived version would otherwise fall back to 0.1.0),
# then runs this spec and Inno Setup.
#
# Copyright (C) 2026 Gwilherm Kerherve. GPL-3.0.

import subprocess
import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_all, collect_submodules

ROOT = Path(SPECPATH)
IS_MAC = sys.platform == "darwin"

# Windows takes the committed .ico; macOS needs an .icns, built on demand
# from the committed 1024px PNG so no binary only one platform reads sits
# in the tree (packaging/make_icns.py).
if IS_MAC:
    ICON_PATH = ROOT / "build" / "KherveMol.icns"
    if not ICON_PATH.is_file():
        subprocess.run([sys.executable,
                        str(ROOT / "packaging" / "make_icns.py"),
                        str(ICON_PATH)], check=True)
else:
    ICON_PATH = ROOT / "packaging" / "khervemol.ico"

datas = []
binaries = []
# The MCP bridge / updater / RDKit bridge are reached through lazy imports.
hiddenimports = collect_submodules("khervemol") + [
    "PyQt5.QtNetwork", "PyQt5.QtOpenGL", "PyQt5.QtSvg",
    # QOpenGLContext.versionFunctions() imports these by name at runtime, so
    # static analysis never sees them; without them the viewer silently
    # falls back to the slow classic renderer.
    "PyQt5._QOpenGLFunctions_2_0", "PyQt5._QOpenGLFunctions_2_1",
    "PyQt5._QOpenGLFunctions_4_1_Core",
]

# qtawesome ships its icon fonts as data files. Required: without them every
# toolbar icon silently falls back to blank.
_d, _b, _h = collect_all("qtawesome")
datas += _d; binaries += _b; hiddenimports += _h

# RDKit is optional at runtime (khervemol/rdkit_io.py guards the import) but
# the standard install includes it, so bundle it when it is present.
try:
    _d, _b, _h = collect_all("rdkit")
    datas += _d; binaries += _b; hiddenimports += _h
except Exception:
    print("KherveMol.spec: rdkit not installed - building without it")

# The build machine's PyInstaller cannot bundle a frozen `.git`; the version
# file is written by build_release.ps1 just before this spec runs.
_version_file = ROOT / "khervemol" / "VERSION"
if _version_file.is_file():
    datas.append((str(_version_file), "khervemol"))

a = Analysis(
    [str(ROOT / "KherveMol.py")],
    pathex=[str(ROOT)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Other Qt bindings / toolkits: KherveMol is PyQt5-only.
        "PyQt6", "PySide2", "PySide6", "tkinter",
        # Heavy dev-environment packages the app never imports.
        "matplotlib", "scipy", "pandas", "IPython", "jedi", "notebook",
        "pytest", "setuptools",
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="KherveMol",
    icon=str(ICON_PATH),
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,                  # UPX breaks Qt/OpenGL DLLs on some machines
    console=False,              # GUI app - no console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="KherveMol",
)

# --------------------------------------------------------- macOS bundle

if IS_MAC:
    # CFBundleShortVersionString has to be dot-separated digits; the
    # git-derived string carries a "+sha" suffix Finder rejects.
    _short_version = "0.1.0"
    if _version_file.is_file():
        _short_version = (_version_file.read_text(encoding="utf-8")
                          .strip().split("+")[0] or _short_version)

    app = BUNDLE(
        coll,
        name="KherveMol.app",
        icon=str(ICON_PATH),
        bundle_identifier="com.kerherve.khervemol",
        version=_short_version,
        info_plist={
            "CFBundleName": "KherveMol",
            "CFBundleDisplayName": "KherveMol",
            "CFBundleShortVersionString": _short_version,
            "CFBundleVersion": _short_version,
            "LSMinimumSystemVersion": "11.0",
            # Without this the 2D sketcher and the OpenGL viewer draw at 1x
            # and get scaled up, so every line reads soft on a Retina display.
            "NSHighResolutionCapable": True,
            "NSRequiresAquaSystemAppearance": False,
            "NSHumanReadableCopyright":
                "Copyright (C) 2026 Gwilherm Kerherve. GPL-3.0.",
        },
    )
