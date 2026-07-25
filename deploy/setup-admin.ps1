$ErrorActionPreference = 'Stop'
$RepoRoot = Split-Path -Parent $PSScriptRoot
$HermesHome = Join-Path $env:LOCALAPPDATA 'hermes'
$CodexHome = Join-Path $env:USERPROFILE '.codex'
$Venv = Join-Path $RepoRoot 'venv'

Write-Host "== Hermes admin setup ==" -ForegroundColor Cyan
Write-Host "Repo: $RepoRoot"
Write-Host "Hermes home: $HermesHome"

if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
    throw "Python launcher 'py' not found. Install Python 3.11+ first."
}

if (-not (Test-Path (Join-Path $Venv 'Scripts\python.exe'))) {
    Write-Host "Creating virtual environment..." -ForegroundColor Yellow
    & py -3.11 -m venv $Venv
}

$Python = Join-Path $Venv 'Scripts\python.exe'
Write-Host "Installing Hermes from this checkout..." -ForegroundColor Yellow
& $Python -m pip install --upgrade pip
& $Python -m pip install --editable $RepoRoot

Write-Host "Installing Claude Code and Codex CLI..." -ForegroundColor Yellow
if (Get-Command npm -ErrorAction SilentlyContinue) {
    & npm install --global '@anthropic-ai/claude-code' '@openai/codex'
} else {
    throw "npm not found. Install Node.js/npm first."
}

New-Item -ItemType Directory -Force -Path $HermesHome | Out-Null
New-Item -ItemType Directory -Force -Path $CodexHome | Out-Null

$BundleHermes = Join-Path $PSScriptRoot 'hermes-home'
if (Test-Path $BundleHermes) {
    Write-Host "Copying Hermes configuration, skills, plugins and credentials..." -ForegroundColor Yellow
    Get-ChildItem -LiteralPath $BundleHermes -Force | Copy-Item -Destination $HermesHome -Recurse -Force
}

$BundleCodex = Join-Path $PSScriptRoot 'codex-home'
if (Test-Path $BundleCodex) {
    Write-Host "Copying Codex state and credentials..." -ForegroundColor Yellow
    Copy-Item -Path (Join-Path $BundleCodex '*') -Destination $CodexHome -Recurse -Force
}

$Hermes = Join-Path $Venv 'Scripts\hermes.exe'
if (-not (Test-Path $Hermes)) {
    $Hermes = Join-Path $Venv 'Scripts\hermes'
}

Write-Host "== Verification ==" -ForegroundColor Cyan
& $Hermes --version
& $Hermes doctor
& $Hermes skills list
& $Hermes tools list
& claude --version
& codex --version

Write-Host "Setup completed from the checked-out Hermes repository." -ForegroundColor Green
Write-Host "If a credential is rejected, run the relevant login command and rerun verification." -ForegroundColor Yellow
