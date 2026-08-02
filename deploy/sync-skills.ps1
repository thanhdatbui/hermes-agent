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

$SourceFull = [IO.Path]::GetFullPath($Source).TrimEnd('\', '/')
$DestinationFull = [IO.Path]::GetFullPath($Destination).TrimEnd('\', '/')
if ($SourceFull -ieq $DestinationFull) {
    throw "Repository skills source and local destination must be different directories."
}

function Test-PathWithin {
    param([string]$Parent, [string]$Child)

    return $Child.StartsWith("$Parent\", [StringComparison]::OrdinalIgnoreCase)
}

if ((Test-PathWithin -Parent $SourceFull -Child $DestinationFull) -or
    (Test-PathWithin -Parent $DestinationFull -Child $SourceFull)) {
    throw "Repository skills source and local destination must not contain one another."
}

foreach ($PathToCheck in @($Source, $Destination)) {
    if (-not (Test-Path -LiteralPath $PathToCheck -PathType Container)) {
        continue
    }
    $Attributes = (Get-Item -LiteralPath $PathToCheck).Attributes
    if (($Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
        throw "Refusing to sync through a reparse point: $PathToCheck"
    }
}

New-Item -ItemType Directory -Force -Path $Destination | Out-Null

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

function Test-ExcludedSkillPath {
    param([string]$RelativePath)

    $Parts = $RelativePath -split '[\\/]'
    if ($Parts | Where-Object { $_ -in $ExcludedDirectories }) {
        return $true
    }
    $Name = Split-Path -Leaf $RelativePath
    return [bool]($ExcludedFiles | Where-Object { $Name -like $_ })
}

function Get-SkillDirectoryHash {
    param([string]$Directory)

    # Keep this compatible with tools.skills_sync._dir_hash: MD5 over sorted
    # relative file names and file bytes. The hash is provenance metadata, not
    # a security check.
    $Hasher = [Security.Cryptography.MD5]::Create()
    try {
        $Files = @(
            Get-ChildItem -LiteralPath $Directory -File -Recurse -Force |
                ForEach-Object {
                    [PSCustomObject]@{
                        Path = $_
                        RelativePath = $_.FullName.Substring($Directory.Length).TrimStart('\', '/')
                    }
                } |
                Sort-Object -Property RelativePath
        )
        foreach ($Entry in $Files) {
            $PathBytes = [Text.Encoding]::UTF8.GetBytes($Entry.RelativePath)
            [void]$Hasher.TransformBlock($PathBytes, 0, $PathBytes.Length, $PathBytes, 0)
            $ContentBytes = [IO.File]::ReadAllBytes($Entry.Path.FullName)
            [void]$Hasher.TransformBlock($ContentBytes, 0, $ContentBytes.Length, $ContentBytes, 0)
        }
        [void]$Hasher.TransformFinalBlock([byte[]]::new(0), 0, 0)
        return ([BitConverter]::ToString($Hasher.Hash) -replace '-', '').ToLowerInvariant()
    } finally {
        $Hasher.Dispose()
    }
}

function Read-BundledManifest {
    param([string]$ManifestPath)

    $Result = @{}
    if (-not (Test-Path -LiteralPath $ManifestPath -PathType Leaf)) {
        return $Result
    }
    foreach ($Line in Get-Content -LiteralPath $ManifestPath) {
        $Trimmed = $Line.Trim()
        if ([string]::IsNullOrWhiteSpace($Trimmed)) {
            continue
        }
        $Parts = $Trimmed -split ':', 2
        if ($Parts.Count -eq 2) {
            $Result[$Parts[0].Trim()] = $Parts[1].Trim()
        } else {
            # v1 entries are deliberately treated as un-baselined, matching
            # Hermes's migration behavior.
            $Result[$Trimmed] = ''
        }
    }
    return $Result
}

function Get-SkillName {
    param([string]$SkillFile, [string]$Fallback)

    $InFrontmatter = $false
    foreach ($Line in (Get-Content -LiteralPath $SkillFile -TotalCount 400)) {
        $Trimmed = $Line.Trim()
        if ($Trimmed -eq '---') {
            if ($InFrontmatter) { break }
            $InFrontmatter = $true
            continue
        }
        if ($InFrontmatter -and $Trimmed.StartsWith('name:')) {
            $Name = $Trimmed.Substring(5).Trim().Trim('"', "'")
            if (-not [string]::IsNullOrWhiteSpace($Name)) { return $Name }
        }
    }
    return $Fallback
}

$ManifestPath = Join-Path $Destination '.bundled_manifest'
$Manifest = Read-BundledManifest -ManifestPath $ManifestPath
$SkillsToBaseline = @{}

# robocopy /E is intentionally update-only, but it would still overwrite a
# locally edited skill when the repository copy is newer. Compare each skill
# with Hermes's last-synced baseline, rather than with the current repository
# copy: an unchanged machine-B copy is therefore safe to update after a
# machine-A change.
$Conflicts = [System.Collections.Generic.List[string]]::new()
foreach ($SkillFile in Get-ChildItem -LiteralPath $Source -Filter 'SKILL.md' -File -Recurse -Force) {
    $SkillDirectory = $SkillFile.Directory.FullName
    $RelativeDirectory = $SkillDirectory.Substring($SourceFull.Length).TrimStart('\', '/')
    if (Test-ExcludedSkillPath -RelativePath $RelativeDirectory) {
        continue
    }
    $SkillName = Get-SkillName -SkillFile $SkillFile.FullName -Fallback $SkillFile.Directory.Name
    $SourceHash = Get-SkillDirectoryHash -Directory $SkillDirectory
    $DestinationDirectory = Join-Path $Destination $RelativeDirectory
    if (Test-Path -LiteralPath $DestinationDirectory -PathType Container) {
        $DestinationHash = Get-SkillDirectoryHash -Directory $DestinationDirectory
        if ($Manifest.ContainsKey($SkillName) -and
            [string]::IsNullOrWhiteSpace([string]$Manifest[$SkillName])) {
            # Match the v1 migration, but only baseline an exact current
            # repository copy because the entry has no usable origin hash.
            if ($DestinationHash -ne $SourceHash) {
                [void]$Conflicts.Add($RelativeDirectory)
                continue
            }
            $SkillsToBaseline[$SkillName] = $SourceHash
            continue
        }
        if (-not $Manifest.ContainsKey($SkillName)) {
            # Without a usable baseline, only an exact current copy is safe.
            # This protects pre-manifest/custom installs conservatively.
            if ($DestinationHash -ne $SourceHash) {
                [void]$Conflicts.Add($RelativeDirectory)
                continue
            }
        } elseif ($DestinationHash -ne [string]$Manifest[$SkillName]) {
            [void]$Conflicts.Add($RelativeDirectory)
            continue
        }
    }
    $SkillsToBaseline[$SkillName] = $SourceHash
}
if ($Conflicts.Count -gt 0) {
    $Shown = ($Conflicts | Select-Object -First 10) -join ', '
    $Suffix = if ($Conflicts.Count -gt 10) { " (and $($Conflicts.Count - 10) more)" } else { '' }
    throw "Refusing to overwrite locally modified skills: $Shown$Suffix. Review, back up, or reset the local copy before retrying."
}

Write-Host "Syncing skills from $Source to $Destination..." -ForegroundColor Cyan
& robocopy.exe $Source $Destination '/E' '/COPY:DAT' '/DCOPY:DAT' '/R:2' '/W:1' '/XJ' '/XD' $ExcludedDirectories '/XF' $ExcludedFiles
$RobocopyExitCode = $LASTEXITCODE

if ($RobocopyExitCode -gt 7) {
    throw "robocopy failed with exit code $RobocopyExitCode"
}

# Keep Hermes's runtime provenance current after the repository copy succeeds.
# Write atomically so an interrupted sync cannot leave a partial manifest.
foreach ($SkillName in $SkillsToBaseline.Keys) {
    $Manifest[$SkillName] = $SkillsToBaseline[$SkillName]
}
$ManifestTemp = "$ManifestPath.$([Guid]::NewGuid().ToString('N')).tmp"
$ManifestLines = @($Manifest.Keys | Sort-Object | ForEach-Object { "${_}:$($Manifest[$_])" })
Set-Content -LiteralPath $ManifestTemp -Value $ManifestLines -Encoding UTF8
Move-Item -LiteralPath $ManifestTemp -Destination $ManifestPath -Force

Write-Host "Skill sync completed (robocopy exit code $RobocopyExitCode)." -ForegroundColor Green
