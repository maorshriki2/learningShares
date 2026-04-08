#Requires -Version 5.1
# Pull latest code from GitHub, then pip install -e '.[dev]' if .venv exists.
# Run from repo root: .\loadGit.ps1
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not (Test-Path ".git")) {
    Write-Error "Not a git repository. Run this script from the project root."
}

$remote = git remote 2>$null
if (-not $remote) {
    Write-Error "No git remote. Add one: git remote add origin https://github.com/USER/REPO.git"
}

$branch = (git branch --show-current).Trim()
Write-Host "Pulling from origin ($branch)..." -ForegroundColor Cyan

git fetch --all --prune
if ($LASTEXITCODE -ne 0) { Write-Error "git fetch failed." }

# --autostash: stash local changes, pull, then re-apply (avoids "unstaged changes" block)
git pull --rebase --autostash origin $branch
if ($LASTEXITCODE -ne 0) {
    Write-Error "git pull failed. If you see stash conflicts, run: git status ; git stash list"
}

$venvPip = Join-Path $PSScriptRoot ".venv\Scripts\pip.exe"
if (Test-Path $venvPip) {
    Write-Host "Updating Python packages (editable install)..." -ForegroundColor Cyan
    & $venvPip install -e '.[dev]'
    if ($LASTEXITCODE -ne 0) {
        $hint = '.\\.venv\\Scripts\\pip install -e ".[dev]"'
        Write-Warning "pip install failed. Try manually: $hint"
    }
    else {
        Write-Host "pip finished OK." -ForegroundColor Green
    }
}
else {
    Write-Host "No .venv found; skipped pip. Create with: python -m venv .venv" -ForegroundColor Yellow
}

Write-Host "Pulled latest from GitHub; repo is up to date." -ForegroundColor Green
