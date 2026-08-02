[CmdletBinding()]
param(
    [string]$RepoRoot = (Split-Path -Parent $PSScriptRoot),
    [string]$Source = (Join-Path $env:LOCALAPPDATA 'hermes\skills')
)

$ErrorActionPreference = 'Stop'
$Destination = Join-Path $RepoRoot 'skills'

if (-not (Test-Path -LiteralPath $Source -PathType Container)) {
    throw "Local Hermes skills directory not found: $Source"
}
if (-not (Test-Path -LiteralPath $Destination -PathType Container)) {
    throw "Repository skills directory not found: $Destination"
}

$SourceFull = [IO.Path]::GetFullPath($Source).TrimEnd('\', '/')
$DestinationFull = [IO.Path]::GetFullPath($Destination).TrimEnd('\', '/')
if ($SourceFull -ieq $DestinationFull) {
    throw "Local skills source and repository destination must be different directories."
}

function Test-PathWithin {
    param([string]$Parent, [string]$Child)

    return $Child.StartsWith("$Parent\", [StringComparison]::OrdinalIgnoreCase)
}

if ((Test-PathWithin -Parent $SourceFull -Child $DestinationFull) -or
    (Test-PathWithin -Parent $DestinationFull -Child $SourceFull)) {
    throw "Local skills source and repository destination must not contain one another."
}

# Fetch the configured upstream before exporting. A clean local skills tree is
# not enough: an export from a stale checkout could overwrite newer upstream
# skill changes in the working tree.
$CurrentBranch = (& git -C $RepoRoot symbolic-ref --quiet --short HEAD 2>$null | Out-String).Trim()
if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($CurrentBranch)) {
    throw "Unable to determine the current repository branch; export requires a branch with an upstream."
}
$Upstream = (& git -C $RepoRoot rev-parse --abbrev-ref --symbolic-full-name '@{upstream}' 2>$null | Out-String).Trim()
if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($Upstream)) {
    throw "The current branch has no configured upstream. Configure tracking and retry before exporting local skills."
}
$UpstreamParts = $Upstream -split '/', 2
if ($UpstreamParts.Count -ne 2 -or [string]::IsNullOrWhiteSpace($UpstreamParts[0])) {
    throw "Unable to determine the remote for upstream '$Upstream'."
}
$UpstreamRemote = $UpstreamParts[0]
& git -C $RepoRoot fetch --quiet --no-tags $UpstreamRemote
if ($LASTEXITCODE -ne 0) {
    throw "Unable to fetch upstream '$UpstreamRemote'; refusing to export from an unverified checkout."
}
$AheadBehind = (& git -C $RepoRoot rev-list --left-right --count "$Upstream...HEAD" 2>$null | Out-String).Trim()
if ($LASTEXITCODE -ne 0 -or $AheadBehind -notmatch '^\s*(\d+)\s+(\d+)\s*$') {
    throw "Unable to verify whether the repository is current with '$Upstream'."
}
$BehindCount = [int]$Matches[1]
if ($BehindCount -gt 0) {
    throw "Repository branch '$CurrentBranch' is $BehindCount commit(s) behind '$Upstream'. Pull/rebase before exporting local skills."
}
Write-Host "Verified repository branch '$CurrentBranch' is current with '$Upstream'." -ForegroundColor DarkGray

foreach ($PathToCheck in @($Source, $Destination)) {
    $Attributes = (Get-Item -LiteralPath $PathToCheck).Attributes
    if (($Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
        throw "Refusing to sync through a reparse point: $PathToCheck"
    }
}

# Do not overwrite repository skill edits that have not been pulled, merged, or committed.
$DirtySkills = @(& git -C $RepoRoot status --porcelain -- skills 2>&1)
if ($LASTEXITCODE -ne 0) {
    throw "Unable to inspect the repository worktree before export."
}
if ($DirtySkills.Count -gt 0) {
    throw "Repository skills have uncommitted changes. Pull and resolve them before exporting local skills."
}

# This is an additive/update export, not a mirror. It never deletes a skill that
# exists only in the repository, so the caller can inspect the Git diff and
# resolve changes from another machine before committing.
$ExcludedDirectories = @(
    '.hub',
    'index-cache',
    '.archive',
    '.curator_backups'
)
$ExcludedFiles = @(
    '.usage.json',
    '.usage.json.lock',
    '.curator_state',
    '.bundled_manifest',
    '.curator_suppressed',
    '*.lock',
    'ticker*',
    '.DS_Store'
)

Write-Host "Exporting local skills from $Source to repository $Destination..." -ForegroundColor Cyan
Write-Host "Runtime metadata and caches are excluded; repository-only skills are preserved." -ForegroundColor DarkGray
& robocopy.exe $Source $Destination '/E' '/COPY:DAT' '/DCOPY:DAT' '/R:2' '/W:1' '/XJ' '/XD' $ExcludedDirectories '/XF' $ExcludedFiles
$RobocopyExitCode = $LASTEXITCODE

if ($RobocopyExitCode -gt 7) {
    throw "robocopy failed with exit code $RobocopyExitCode"
}

Write-Host "Skill export completed (robocopy exit code $RobocopyExitCode). Review with git diff before committing." -ForegroundColor Green
Write-Host "Recommended next steps: inspect git diff; git diff --check; review for secrets; git add skills; git commit; git push" -ForegroundColor Yellow
