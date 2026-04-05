# Install Inno Setup 6 CLI to .tools\InnoSetup6 (no admin) if ISCC is missing.
# Used by build_windows_installer.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Tools = Join-Path $Root ".tools\InnoSetup6"
$Iscc = Join-Path $Tools "ISCC.exe"

if (Test-Path $Iscc) {
    Write-Host "Inno Setup compiler already present: $Iscc"
    exit 0
}

New-Item -ItemType Directory -Force -Path $Tools | Out-Null
$setup = Join-Path $env:TEMP "innosetup-6.7.1.exe"
$uri = "https://github.com/jrsoftware/issrc/releases/download/is-6_7_1/innosetup-6.7.1.exe"

Write-Host "Downloading Inno Setup 6.7.1..."
Invoke-WebRequest -Uri $uri -OutFile $setup -UseBasicParsing

Write-Host "Installing silently to $Tools ..."
Start-Process -Wait -FilePath $setup -ArgumentList @(
    "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART",
    "/DIR=$Tools", "/NOICONS", "/MERGETASKS=!desktopicon"
)

if (-not (Test-Path $Iscc)) {
    throw "ISCC.exe not found after install. Expected: $Iscc"
}
Write-Host "OK: $Iscc"
