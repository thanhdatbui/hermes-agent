# Sync Hermes skills, SOUL and brain memories to git repo and push.
# Usage: powershell -ExecutionPolicy Bypass -File sync-orchestration-skills.ps1 [--commit-msg "msg"]
param(
    [string]$CommitMsg = "chore: sync skills and brain memories"
)

$ErrorActionPreference = 'Stop'
$repo = 'D:\Taadaa\Hermes'

Push-Location $repo
try {
    # 1. Export tat ca skill tu runtime AppData sang repo Hermes
    $localSkills = Join-Path $env:LOCALAPPDATA 'hermes\skills'
    $repoSkills = Join-Path $repo 'skills'

    if (Test-Path $localSkills) {
        Get-ChildItem -Path $localSkills -Directory | Where-Object { $_.Name -notmatch '^\.' } | ForEach-Object {
            $cat = $_.Name
            $catSrc = $_.FullName
            $catDst = Join-Path $repoSkills $cat
            if (-not (Test-Path $catDst)) {
                New-Item -ItemType Directory -Path $catDst -Force | Out-Null
            }
            robocopy $catSrc $catDst /E /NDL /NFL /NJH /NJS /XD .hub index-cache .archive .curator_backups /XF .usage.json* .curator* *.lock | Out-Null
        }
    }

    # 2. Export SOUL.md và memories (BỘ NÃO TRỢ LÝ) sang repo Hermes
    $localSoul = Join-Path $env:LOCALAPPDATA 'hermes\SOUL.md'
    $repoSoul = Join-Path $repo 'deploy\hermes-home\SOUL.md'
    if (Test-Path $localSoul) {
        Copy-Item $localSoul -Destination $repoSoul -Force
    }

    $localMem = Join-Path $env:LOCALAPPDATA 'hermes\memories'
    $repoMem = Join-Path $repo 'deploy\hermes-home\memories'
    if (Test-Path $localMem) {
        if (-not (Test-Path $repoMem)) {
            New-Item -ItemType Directory -Path $repoMem -Force | Out-Null
        }
        robocopy $localMem $repoMem /E /NDL /NFL /NJH /NJS /XF *.lock | Out-Null
    }

    # 3. Export các file chính sách cốt lõi của Farm
    $localSubRules = 'D:\Taadaa\HERMES_SUBAGENT_RULES.md'
    if (Test-Path $localSubRules) {
        Copy-Item $localSubRules -Destination (Join-Path $repo 'HERMES_SUBAGENT_RULES.md') -Force
        Copy-Item $localSubRules -Destination (Join-Path $repo 'deploy\hermes-home\HERMES_SUBAGENT_RULES.md') -Force
    }

    $localAgents = 'D:\Taadaa\AGENTS.md'
    if (Test-Path $localAgents) {
        Copy-Item $localAgents -Destination (Join-Path $repo 'AGENTS.md') -Force
        Copy-Item $localAgents -Destination (Join-Path $repo 'deploy\hermes-home\AGENTS.md') -Force
    }

    # 4. Stage và kiểm tra thay đổi
    git add skills/ deploy/hermes-home/SOUL.md deploy/hermes-home/memories/ HERMES_SUBAGENT_RULES.md deploy/hermes-home/HERMES_SUBAGENT_RULES.md AGENTS.md deploy/hermes-home/AGENTS.md

    $staged = git status --porcelain skills/ deploy/hermes-home/SOUL.md deploy/hermes-home/memories/ HERMES_SUBAGENT_RULES.md deploy/hermes-home/HERMES_SUBAGENT_RULES.md AGENTS.md deploy/hermes-home/AGENTS.md
    if (-not $staged) {
        Write-Output "SKILLS_UNCHANGED"
        exit 0
    }

    # 5. Commit và Push an toàn lên GitHub
    git commit -m $CommitMsg -- skills/ deploy/hermes-home/SOUL.md deploy/hermes-home/memories/ HERMES_SUBAGENT_RULES.md deploy/hermes-home/HERMES_SUBAGENT_RULES.md AGENTS.md deploy/hermes-home/AGENTS.md
    git push fork main
    Write-Output "SYNCED: skills and brain memories pushed to fork main"
} finally {
    Pop-Location
}
