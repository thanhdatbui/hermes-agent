[CmdletBinding()]
param(
    [string]$RepoRoot = (Split-Path -Parent $PSScriptRoot),
    [string]$Destination = (Join-Path $env:LOCALAPPDATA 'hermes\skills')
)

$ErrorActionPreference = 'Stop'
$Source = Join-Path $RepoRoot 'skills'

if (-not (Test-Path -LiteralPath $Source -PathType Container)) {
    throw "Canonical skills directory not found: $Source"
}

New-Item -ItemType Directory -Force -Path $Destination | Out-Null

$ExcludedDirectories = @('index-cache')
$ExcludedFiles = @(
    '.usage.json',
    '.usage.json.lock',
    '.curator_state',
    '.bundled_manifest',
    '*.lock',
    'ticker*'
)

Write-Host "Syncing skills from $Source to $Destination..." -ForegroundColor Cyan
& robocopy.exe $Source $Destination '/E' '/XD' $ExcludedDirectories '/XF' $ExcludedFiles
$RobocopyExitCode = $LASTEXITCODE

if ($RobocopyExitCode -gt 7) {
    throw "robocopy failed with exit code $RobocopyExitCode"
}

Write-Host "Skill sync completed (robocopy exit code $RobocopyExitCode)." -ForegroundColor Green
