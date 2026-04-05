# Build PyInstaller EXE then compile Inno Setup installer (if ISCC is available).
# Usage: .\scripts\build_windows_installer.ps1
# Requires: Inno Setup 6 (ISCC.exe) — https://jrsoftware.org/isdl.php

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) {
    $Python = "python"
}

& $Python -m PyInstaller --noconfirm (Join-Path $Root "learningSharesDesktop.spec")
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$iscc = @(
    (Join-Path $Root ".tools\InnoSetup6\ISCC.exe"),
    "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
    "$env:ProgramFiles\Inno Setup 6\ISCC.exe"
) | Where-Object { Test-Path $_ } | Select-Object -First 1

if (-not $iscc) {
    Write-Host "Inno Setup compiler not found; installing to .tools\InnoSetup6 ..."
    & (Join-Path $PSScriptRoot "ensure_inno_setup.ps1")
    $iscc = Join-Path $Root ".tools\InnoSetup6\ISCC.exe"
    if (-not (Test-Path $iscc)) {
        Write-Host "EXE is in dist\learningSharesDesktop.exe"
        Write-Host "Install failed. Try: winget install JRSoftware.InnoSetup --silent"
        exit 1
    }
}

& $iscc (Join-Path $Root "installer\learningShares.iss")
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "Installer output: $(Join-Path $Root 'installer_output')"
