# Sync Hermes orchestration skills to git repo and push.
# Usage: powershell -ExecutionPolicy Bypass -File sync-orchestration-skills.ps1 [--commit-msg "msg"]
param(
    [string]$CommitMsg = "chore: sync orchestration skills"
)

$ErrorActionPreference = 'Stop'
$repo = 'D:\Taadaa\Hermes'
$skillsPath = 'skills/autonomous-ai-agents/agent-review-loops skills/software-development/hermes-orchestration-dispatcher'

Push-Location $repo
try {
    # Chỉ stage 2 skill điều phối (không đụng code Hermes khác)
    git add skills/autonomous-ai-agents/agent-review-loops/ skills/software-development/hermes-orchestration-dispatcher/
    $staged = git diff --cached --name-only | Where-Object { $_ -match '^skills/' }
    if (-not $staged) {
        Write-Output 'SKILLS_UNCHANGED: no skill changes to commit'
        exit 0
    }
    git commit -m $CommitMsg
    git push fork main
    Write-Output "SYNCED: $($staged.Count) skill files pushed"
} finally {
    Pop-Location
}
