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

from pathlib import Path

from PyInstaller.utils.hooks import collect_all, collect_submodules

ROOT = Path(SPECPATH)
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
