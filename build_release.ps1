# Build a KherveMol release (Windows).
#
#   1. Writes khervemol\VERSION from git (a frozen build has no .git).
#   2. PyInstaller -> dist\KherveMol\KherveMol.exe (one-folder build).
#   3. Zips it to dist\KherveMol_<version>.zip.
#   4. Inno Setup (if installed) -> installer\Setup_KherveMol_<version>.exe.
#
#   powershell -ExecutionPolicy Bypass -File .\build_release.ps1
#
# Uses the project's .venv when present, else the `py` launcher.
# Inno Setup 6: https://jrsoftware.org/isinfo.php (free). Without it the
# script stops after the zip.

$ErrorActionPreference = "Stop"
$ProjectRoot = $PSScriptRoot
Set-Location $ProjectRoot

$venvPy = Join-Path $ProjectRoot '.venv\Scripts\python.exe'
if (Test-Path $venvPy) { $py = @($venvPy) } else { $py = @('py') }

# 1. Version: 0.1.<commit count>+<sha>, exactly what _version.py derives.
$count = (git rev-list --count HEAD).Trim()
$sha   = (git rev-parse --short HEAD).Trim()
$Full  = "0.1.$count+$sha"
$Version = "0.1.$count"          # no '+': safe in file names and Inno
Set-Content -Path 'khervemol\VERSION' -Value $Full -Encoding ascii -NoNewline
Write-Host "Building KherveMol v$Full" -ForegroundColor Cyan

# 2. PyInstaller
Write-Host "==> pyinstaller KherveMol.spec --noconfirm" -ForegroundColor Yellow
& $py[0] -m PyInstaller KherveMol.spec --noconfirm
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed" }
$distSizeMB = [math]::Round((Get-ChildItem 'dist\KherveMol' -Recurse -File |
    Measure-Object -Property Length -Sum).Sum / 1MB, 1)
Write-Host "    dist size: $distSizeMB MB" -ForegroundColor Green

# 3. Zip
$zipPath = Join-Path $ProjectRoot "dist\KherveMol_$Version.zip"
if (Test-Path $zipPath) { Remove-Item $zipPath }
Write-Host "==> Compressing -> $zipPath" -ForegroundColor Yellow
Compress-Archive -Path 'dist\KherveMol\*' -DestinationPath $zipPath -CompressionLevel Optimal

# 4. Inno Setup
$iscc = $null
foreach ($c in @('C:\Program Files (x86)\Inno Setup 6\ISCC.exe',
                 'C:\Program Files\Inno Setup 6\ISCC.exe',
                 "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe")) {
    if (Test-Path $c) { $iscc = $c; break }
}
if (-not $iscc) {
    $onPath = Get-Command iscc.exe -ErrorAction SilentlyContinue
    if ($onPath) { $iscc = $onPath.Source }
}

if ($iscc) {
    # Stage in a short path: the OneDrive project path plus PyQt5/rdkit's deep
    # trees exceeds Windows' 260-char MAX_PATH inside ISCC.
    $stage = 'C:\tmp\kmolbuild'
    if (Test-Path $stage) { Remove-Item $stage -Recurse -Force }
    New-Item -ItemType Directory -Force -Path "$stage\packaging" | Out-Null
    Copy-Item 'KherveMol_setup.iss'     "$stage\"
    Copy-Item 'LICENSE'                 "$stage\"
    Copy-Item 'packaging\khervemol.ico' "$stage\packaging\"
    Copy-Item 'dist\KherveMol'          "$stage\dist\KherveMol" -Recurse
    Push-Location $stage
    try {
        & $iscc "/DMyAppVersion=$Version" 'KherveMol_setup.iss'
        if ($LASTEXITCODE -ne 0) { throw "Inno Setup failed" }
    } finally { Pop-Location }
    New-Item -ItemType Directory -Force -Path 'installer' | Out-Null
    Copy-Item "$stage\installer\*" 'installer' -Force
    Write-Host "  installer\Setup_KherveMol_$Version.exe" -ForegroundColor Green
} else {
    Write-Host "Inno Setup not found - skipping the installer." -ForegroundColor Yellow
}
Write-Host "Done: dist\KherveMol\KherveMol.exe, $zipPath" -ForegroundColor Cyan
