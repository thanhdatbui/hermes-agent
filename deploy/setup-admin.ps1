$ErrorActionPreference = 'Stop'
$RepoRoot = Split-Path -Parent $PSScriptRoot
$HermesHome = Join-Path $env:LOCALAPPDATA 'hermes'
$CodexHome = Join-Path $env:USERPROFILE '.codex'
$Venv = Join-Path $RepoRoot 'venv'
$SyncSkills = Join-Path $PSScriptRoot 'sync-skills.ps1'

function Copy-BootstrapFile {
    param(
        [Parameter(Mandatory = $true)][string]$Source,
        [Parameter(Mandatory = $true)][string]$Destination
    )

    if ((Test-Path -LiteralPath $Source -PathType Leaf) -and -not (Test-Path -LiteralPath $Destination)) {
        Copy-Item -LiteralPath $Source -Destination $Destination
    }
}

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

if (-not (Test-Path -LiteralPath $SyncSkills -PathType Leaf)) {
    throw "Skill sync script not found: $SyncSkills"
}

Write-Host "Syncing repository skills..." -ForegroundColor Yellow
& $SyncSkills -RepoRoot $RepoRoot

$BundleHermes = Join-Path $PSScriptRoot 'hermes-home'
if (Test-Path -LiteralPath $BundleHermes -PathType Container) {
    Write-Host "Copying Hermes configuration and persona..." -ForegroundColor Yellow
    foreach ($FileName in @('config.yaml', 'SOUL.md')) {
        $Source = Join-Path $BundleHermes $FileName
        if (Test-Path -LiteralPath $Source -PathType Leaf) {
            Copy-Item -LiteralPath $Source -Destination $HermesHome -Force
        }
    }

    Write-Host "Copying missing Hermes bootstrap credentials..." -ForegroundColor Yellow
    Copy-BootstrapFile (Join-Path $BundleHermes '.env') (Join-Path $HermesHome '.env')
    Copy-BootstrapFile (Join-Path $BundleHermes 'auth.json') (Join-Path $HermesHome 'auth.json')
}

$BundleCodex = Join-Path $PSScriptRoot 'codex-home'
if (Test-Path -LiteralPath $BundleCodex -PathType Container) {
    Write-Host "Copying missing Codex bootstrap state..." -ForegroundColor Yellow
    Copy-BootstrapFile (Join-Path $BundleCodex '.cockpit_codex_auth.json') (Join-Path $CodexHome '.cockpit_codex_auth.json')
    Copy-BootstrapFile (Join-Path $BundleCodex '.codex-global-state.json') (Join-Path $CodexHome '.codex-global-state.json')
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
