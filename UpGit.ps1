#Requires -Version 5.1
# Stage local changes, commit, and push to GitHub (upload from this PC).
# Run from repo root: .\UpGit.ps1
# Optional: .\UpGit.ps1 -Message "your message"
param(
    [Parameter(Position = 0)]
    [string]$Message = ""
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not (Test-Path ".git")) {
    Write-Error "Not a git repository. Run this script from the project root."
}

$branch = (git branch --show-current 2>$null)
if (-not $branch) { Write-Error "Could not detect current branch." }
$branch = $branch.Trim()

$remote = git remote 2>$null
if (-not $remote) {
    Write-Error "No git remote. Add one: git remote add origin https://github.com/USER/REPO.git"
}

Write-Host "Branch: $branch" -ForegroundColor Cyan

# Do not use 2>&1 here: Git prints progress to stderr; PowerShell treats that as errors.
git pull --rebase --autostash origin $branch
if ($LASTEXITCODE -ne 0) {
    Write-Error "git pull --rebase failed. Resolve conflicts or sync with loadGit.ps1, then try again."
}

git add -A
$dirty = git status --porcelain
if (-not $dirty) {
    Write-Host "Nothing to commit; skipping push." -ForegroundColor Yellow
    exit 0
}

if (-not $Message) {
    $Message = "Update $(Get-Date -Format 'yyyy-MM-dd HH:mm')"
}

git commit -m $Message
if ($LASTEXITCODE -ne 0) {
    Write-Error "git commit failed."
}

git push -u origin $branch
if ($LASTEXITCODE -ne 0) {
    Write-Error "git push failed. Check auth (HTTPS/SSH) and that the GitHub repo exists."
}

Write-Host "Pushed to origin/$branch successfully." -ForegroundColor Green
