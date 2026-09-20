# KherveMol on macOS

Two native disk images per release, built on GitHub's macOS runners
(`.github/workflows/macos-build.yml`):

- `KherveMol-<version>-macOS-arm64.dmg` — Apple Silicon (M1 and later)
- `KherveMol-<version>-macOS-x86_64.dmg` — Intel

Open the DMG and drag KherveMol to Applications.

## First launch

The app is **ad-hoc signed, not notarized**. Apple Silicon refuses to run an
unsigned binary at all, so the ad-hoc signature is required; notarization needs a
paid Apple Developer account, which this project does not have. macOS therefore
quarantines the download. On first launch, right-click the app, choose **Open**,
then **Open** again — or run:

    xattr -dr com.apple.quarantine /Applications/KherveMol.app

## Building it yourself

    pip install -r requirements.txt pyinstaller
    python packaging/build_macos.py

`build_macos.py` writes `khervemol/VERSION` from git, freezes the app with
`KherveMol.spec` (which ends in a `BUNDLE` step on macOS), ad-hoc signs the `.app`
and seals it into a DMG. PyInstaller cannot cross-compile, so this only runs on a Mac.
The icon is built from `packaging/icons/khervemol_1024.png` by `packaging/make_icns.py`.
