# Deploy Scripts Implementation

Detailed implementation patterns for Hermes multi-machine deployment scripts.

## setup-admin.ps1

```powershell
# deploy/setup-admin.ps1
# Bootstrap script for new Windows machines

$ErrorActionPreference = "Stop"

# Resolve paths
$RepoRoot = Split-Path -Parent $PSScriptRoot
$HermesHome = "$env:LOCALAPPDATA\hermes"
$CodexHome = "$env:USERPROFILE\.codex"
$VenvPath = Join-Path $RepoRoot ".venv"

Write-Host "=== Hermes Admin Setup ===" -ForegroundColor Cyan
Write-Host "Repo: $RepoRoot"
Write-Host "Hermes Home: $HermesHome"

# Check Python
$pythonCmd = "python"
try {
    $pythonVersion = & $pythonCmd --version 2>&1
    Write-Host "Found Python: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Error "Python not found. Install Python 3.11+ first."
    exit 1
}

# Create venv if needed
if (-not (Test-Path (Join-Path $VenvPath "Scripts\python.exe"))) {
    Write-Host "Creating virtual environment..." -ForegroundColor Yellow
    & $pythonCmd -m venv $VenvPath
}

# Activate venv
$activateScript = Join-Path $VenvPath "Scripts\Activate.ps1"
. $activateScript

# Install Hermes
Write-Host "Installing Hermes from checkout..." -ForegroundColor Yellow
pip install --upgrade pip
pip install -e .

# Install Claude Code and Codex CLI
Write-Host "Installing Claude Code and Codex CLI..." -ForegroundColor Yellow
npm install -g @anthropic-ai/claude-code
npm install -g @openai/codex

# Create directories
New-Item -ItemType Directory -Force -Path $HermesHome | Out-Null
New-Item -ItemType Directory -Force -Path $CodexHome | Out-Null

# Call sync-skills
$syncSkillsPath = Join-Path $PSScriptRoot "sync-skills.ps1"
& $syncSkillsPath

# Copy bootstrap files (only if destination doesn't exist)
function Copy-BootstrapFile {
    param(
        [Parameter(Mandatory=$true)][string]$Source,
        [Parameter(Mandatory=$true)][string]$Destination
    )
    
    if (-not (Test-Path $Destination)) {
        Copy-Item $Source -Destination $Destination
        Write-Host "Copied bootstrap: $Destination" -ForegroundColor Green
    } else {
        Write-Host "Skipped (exists): $Destination" -ForegroundColor Yellow
    }
}

$bootstrapConfig = Join-Path $PSScriptRoot "hermes-home\config.yaml"
if (Test-Path $bootstrapConfig) {
    Copy-Item $bootstrapConfig -Destination (Join-Path $HermesHome "config.yaml") -Force
}

Copy-BootstrapFile (Join-Path $PSScriptRoot "hermes-home\.env") (Join-Path $HermesHome ".env")
Copy-BootstrapFile (Join-Path $PSScriptRoot "hermes-home\auth.json") (Join-Path $HermesHome "auth.json")

$bootstrapCodex = Join-Path $PSScriptRoot "codex-home"
if (Test-Path $bootstrapCodex) {
    Get-ChildItem $bootstrapCodex -File | ForEach-Object {
        $destFile = Join-Path $CodexHome $_.Name
        Copy-BootstrapFile $_.FullName $destFile
    }
}

# Verification
Write-Host "`n=== Verification ===" -ForegroundColor Cyan
& hermes --version
& hermes doctor
& hermes skills list
& claude --version
& codex --version

Write-Host "`nSetup complete!" -ForegroundColor Green
Write-Host "Run '.\deploy\sync-skills.ps1' after 'git pull' to sync skills." -ForegroundColor Yellow
```

## sync-skills.ps1

```powershell
# deploy/sync-skills.ps1
# Sync canonical skills from repo to runtime

param(
    [string]$Source = (Join-Path $PSScriptRoot "..\skills"),
    [string]$Destination = "$env:LOCALAPPDATA\hermes\skills"
)

$ErrorActionPreference = "Stop"

Write-Host "=== Skill Sync ===" -ForegroundColor Cyan
Write-Host "Source: $Source"
Write-Host "Destination: $Destination"

# Validate source
if (-not (Test-Path $Source)) {
    Write-Error "Source directory not found: $Source"
    exit 1
}

# Ensure destination exists
if (-not (Test-Path $Destination)) {
    New-Item -ItemType Directory -Force -Path $Destination | Out-Null
}

# Define exclusions
$ExcludeFiles = @(
    ".usage.json",
    ".usage.json.lock",
    ".curator_state",
    ".bundled_manifest",
    "*.lock",
    "ticker*"
)

$ExcludeDirs = @("index-cache")

# Build robocopy exclusion arguments
$excludeArgs = @()
foreach ($file in $ExcludeFiles) {
    $excludeArgs += "/XF"
    $excludeArgs += $file
}
foreach ($dir in $ExcludeDirs) {
    $excludeArgs += "/XD"
    $excludeArgs += $dir
}

# Execute robocopy
Write-Host "`nSyncing skills..." -ForegroundColor Yellow
& robocopy $Source $Destination /E /NDL /NJH /NJS /NC /NS /NP @excludeArgs
$RobocopyExitCode = $LASTEXITCODE

# Interpret exit code
if ($RobocopyExitCode -gt 7) {
    Write-Error "Robocopy failed with exit code $RobocopyExitCode"
    exit $RobocopyExitCode
}

Write-Host "Sync complete (exit code: $RobocopyExitCode)" -ForegroundColor Green
Write-Host "`nReload Hermes with: /reload-skills" -ForegroundColor Yellow
```

## Robocopy Exit Codes

Robocopy uses non-standard exit codes:

| Code | Meaning |
|------|---------|
| 0 | No files copied, no errors |
| 1 | Files copied successfully |
| 2 | Extra files detected in destination |
| 3 | Files copied + extra files |
| 4 | Mismatched files detected |
| 5 | Files copied + mismatched |
| 6 | Extra + mismatched files |
| 7 | All conditions (copy + extra + mismatch) |
| 8+ | Errors occurred |

**Key insight:** Codes 0–7 are all "success" variants. The script checks `-gt 7` to detect actual errors.

## .gitignore Additions

```gitignore
# Deliberate private admin deployment bundle
# This repository is private; credentials are intentionally committed for bootstrap.
!deploy/hermes-home/.env
!deploy/hermes-home/auth.json
!deploy/codex-home/.cockpit_codex_auth.json
!deploy/codex-home/.codex-global-state.json

# Exclude skill snapshot from deploy bundle (prevents divergence)
deploy/hermes-home/skills/
```

## Bootstrap Files Structure

```text
deploy/
├── hermes-home/
│   ├── .env                    ← Bootstrap env (committed)
│   ├── auth.json               ← Bootstrap auth (committed)
│   └── config.yaml             ← Shared config (committed)
├── codex-home/
│   ├── .cockpit_codex_auth.json    ← Bootstrap Codex auth
│   └── .codex-global-state.json    ← Bootstrap Codex state
├── setup-admin.ps1             ← Initial setup
└── sync-skills.ps1             ← Skill sync
```

**Note:** `deploy/hermes-home/skills/` is explicitly excluded to prevent the snapshot divergence problem that caused the earlier iteration issues.
