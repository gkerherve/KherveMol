"""One-shot macOS build: .app + ad-hoc signature + DMG.

The macOS counterpart of ``build_installer.py``. Run from the project
root, on a Mac, with the interpreter that has PyInstaller:

    python packaging/build_macos.py                  # everything
    python packaging/build_macos.py --skip-freeze    # reuse dist/KherveMol.app

Produces, in ``dist/``:

* ``KherveMol-<version>-macOS-<arch>.dmg`` — drag-to-install disk image
* ``KherveMol-macOS-<arch>.dmg``           — stable-name copy, the name a
                                               "latest release" link can use

The steps, in order:

1. Freeze with PyInstaller. On macOS the spec ends in ``BUNDLE``, so this
   yields ``dist/KherveMol.app``, not a bare folder. The spec resolves
   and ``write_version()`` stamps ``khervemol/VERSION`` just before, so
   the bundle reports the commit it was actually built from.
2. Ad-hoc sign. Apple Silicon refuses to execute an unsigned Mach-O at
   all, so this is not cosmetic. It is *not* notarization — see
   ``README.macos.md`` for what that means for the person downloading it.
3. Seal it into a DMG with the ``/Applications`` symlink that makes the
   mounted window a drag-install.

There is no installer to compile: on macOS a drag-install replaces the
whole bundle atomically, so the upgrade problems ``installer.nsi`` works
around cannot happen here. There is likewise no portable zip — a ``.app``
already is one.

Copyright (C) 2026 Gwilherm Kerherve

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
"""

import argparse
import platform
import shutil
import subprocess
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent          # packaging/
_ROOT = _HERE.parent                             # project root
_DIST = _ROOT / "dist"
_APP = "KherveMol"

_ARCHES = ("arm64", "x86_64")


def _run(cmd, **kwargs):
    print("+", " ".join(str(c) for c in cmd), flush=True)
    subprocess.run([str(c) for c in cmd], check=True, **kwargs)


def write_version() -> str:
    """Write ``khervemol/VERSION`` from git, exactly as build_release.ps1
    does on Windows: a frozen bundle has no ``.git`` and would report the
    0.1.0 placeholder. Rewritten on every build, never trusted from disk."""
    count = subprocess.check_output(
        ["git", "rev-list", "--count", "HEAD"], cwd=_ROOT).decode().strip()
    sha = subprocess.check_output(
        ["git", "rev-parse", "--short", "HEAD"], cwd=_ROOT).decode().strip()
    full = f"0.1.{count}+{sha}"
    (_ROOT / "khervemol" / "VERSION").write_text(full, encoding="ascii")
    print(f"{_APP} {full}", flush=True)
    return full


def freeze() -> None:
    _run([sys.executable, "-m", "PyInstaller",
          _ROOT / f"{_APP}.spec", "--noconfirm"], cwd=_ROOT)


def read_version() -> str:
    """The numeric version the spec stamped into the bundle.

    Read back rather than re-derived, so the DMG filename cannot disagree
    with what the About box will say.
    """
    text = (_ROOT / "khervemol" / "VERSION").read_text(encoding="utf-8")
    return text.strip().split("+")[0]


def sign(app: Path) -> None:
    """Ad-hoc sign the finished tree.

    Apple Silicon kills an unsigned Mach-O at launch, so this has to
    happen — and it has to happen last, because any edit inside the
    bundle invalidates a signature applied before it.
    """
    _run(["codesign", "--force", "--deep", "--sign", "-",
          "--timestamp=none", app])
    _run(["codesign", "--verify", "--deep", "--strict", app])


def build_dmg(app: Path, version: str, arch: str) -> Path:
    stage = _ROOT / "build" / "dmg"
    if stage.exists():
        shutil.rmtree(stage)
    stage.mkdir(parents=True)
    # ditto, not copytree: it preserves the symlinks inside the Qt
    # framework tree, which a naive copy would flatten into duplicates.
    _run(["ditto", app, stage / app.name])
    # The /Applications symlink is what turns the mounted window into the
    # familiar drag-to-install gesture.
    (stage / "Applications").symlink_to("/Applications")

    out = _DIST / f"{_APP}-{version}-macOS-{arch}.dmg"
    out.unlink(missing_ok=True)
    _run(["hdiutil", "create", "-volname", _APP, "-srcfolder", stage,
          "-fs", "HFS+", "-format", "UDZO", "-imagekey", "zlib-level=9",
          "-ov", out])
    shutil.rmtree(stage)
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-freeze", action="store_true",
                        help="reuse the existing dist/KherveMol.app")
    args = parser.parse_args()

    if sys.platform != "darwin":
        raise SystemExit("build_macos.py only runs on macOS "
                         "(PyInstaller cannot cross-compile)")

    arch = platform.machine()
    if arch not in _ARCHES:
        raise SystemExit(f"unsupported architecture {arch!r}")

    write_version()
    if not args.skip_freeze:
        freeze()

    app = _DIST / f"{_APP}.app"
    if not app.is_dir():
        raise SystemExit(f"{app} not found — did PyInstaller's BUNDLE run?")

    version = read_version()
    sign(app)
    dmg = build_dmg(app, version, arch)

    stable = _DIST / f"{_APP}-macOS-{arch}.dmg"
    shutil.copy2(dmg, stable)

    print()
    print(f"{_APP} {version} ({arch})")
    for path in (dmg, stable):
        print(f"{path.name:<44} {path.stat().st_size / 1e6:>7.1f} MB")


if __name__ == "__main__":
    main()
