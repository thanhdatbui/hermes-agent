---
name: hermes-deployment
description: "Deploy Hermes across multiple Windows machines with skill synchronization via Git"
version: 1.0.0
author: Hermes Agent
tags: [deployment, windows, multi-machine, skill-sync, git-workflow]
---

# Hermes Deployment

Deploy Hermes from a private repository to multiple Windows machines, synchronize skills via Git, and handle multi-machine coordination without conflicts.

## Architecture

```text
Repository (private)
├── skills/                    ← Canonical source of shared skills
├── deploy/
│   ├── setup-admin.ps1        ← Initial bootstrap script
│   ├── sync-skills.ps1        ← Skill sync script
│   ├── hermes-home/           ← Bootstrap config/credentials (no skills snapshot)
│   └── codex-home/            ← Bootstrap Codex state
└── .gitignore                 ← Excludes deploy/hermes-home/skills/

Machine A/B/C
└── %LOCALAPPDATA%\hermes\
    ├── skills/                ← Runtime skills (synced from repo)
    ├── config.yaml            ← Machine-specific config
    ├── .env                   ← Machine-specific credentials
    └── auth.json              ← Machine-specific auth
```

**Key principle:** `skills/` in the repo is the **sole canonical source** for shared skills. Each machine's `%LOCALAPPDATA%\hermes\skills\` is a sync target, not a source.

## Initial Deployment

### On target machine (first time)

```powershell
# 1. Clone the private repo
git clone https://github.com/your-user/hermes-agent D:\Taadaa\Hermes
cd D:\Taadaa\Hermes

# 2. Run bootstrap
Set-ExecutionPolicy -Scope Process Bypass
.\deploy\setup-admin.ps1
```

`setup-admin.ps1` will:
- Create Python venv and install Hermes editable from repo
- Install Claude Code and Codex CLI via npm
- Call `sync-skills.ps1` to populate runtime skills
- Copy bootstrap config/credentials **only if they don't exist** (idempotent)
- Run verification: `hermes --version`, `hermes doctor`, etc.

### What setup does NOT do

- Does not overwrite existing `.env`, `auth.json`, or Codex state
- Does not snapshot skills into the repo (that's what caused divergence in earlier iterations)
- Does not copy runtime metadata (`.usage.json`, `.curator_state`, locks, ticker files)

## Skill Synchronization

### sync-skills.ps1

Syncs canonical `skills/` to runtime:

```powershell
.\deploy\sync-skills.ps1
```

**Implementation details:**
- Uses `robocopy /E` (copy subdirectories, including empty)
- Does NOT use `/MIR` or `/PURGE` (preserves machine-local skills)
- Excludes runtime metadata:
  - `.usage.json`, `.usage.json.lock`
  - `.curator_state`, `.bundled_manifest`
  - `*.lock`, `ticker*`
  - `index-cache/` directory
- Accepts robocopy exit codes 0–7 (success), fails on >7

**When to run:**
- After initial `setup-admin.ps1`
- After `git pull` if skills changed
- After creating/editing a shared skill in the repo

After sync, reload Hermes:
```text
/reload-skills
```

Or restart Hermes desktop/gateway for certainty.

## Multi-Machine Workflow

### Scenario: Two machines both modify skills or Hermes core code

#### Machine 1 (goes first)

```powershell
cd D:\Taadaa\Hermes
git add skills  # (or specific patched files under plugins/, hermes_cli/, etc.)
git commit -m "fix(core): update code or shared skills"
git push fork main   # push to remote fork for other machines to pull
```

#### Machine 2 (goes second, has uncommitted changes)

**If you have uncommitted changes:**

```powershell
# Option A: Stash (cleaner, no WIP commit)
git stash                    # Save changes
git pull --rebase fork main
git stash pop                # Restore changes
# Handle conflict if any
git add skills
git commit -m "feat(skills): update from machine 2"
git push fork main

# Option B: Commit WIP (safer if changes are substantial)
git add skills
git commit -m "WIP: skills from machine 2"
git pull --rebase fork main
# Handle conflict if any
git push fork main
```

**If you have no uncommitted changes:**

```powershell
git pull --rebase fork main
.\deploy\sync-skills.ps1
```

#### Machine 1 (pulls Machine 2's changes)

```powershell
git pull origin main
.\deploy\sync-skills.ps1
```

### Handling Git Conflicts

If both machines edited the same `SKILL.md`:

```text
CONFLICT (content): Merge conflict in skills/xxx/SKILL.md
```

**Resolution:**

1. Open the conflicted file
2. Find markers:
   ```text
   <<<<<<< HEAD
   content from one machine
   =======
   content from other machine
   >>>>>>> origin/main
   ```
3. Edit to keep correct content (or merge both)
4. Remove all markers
5. Complete the rebase:
   ```powershell
   git add skills/path/to/SKILL.md
   git rebase --continue
   git push origin main
   ```

**Abort if needed:**
```powershell
git rebase --abort
```

### Avoiding Conflicts: Use Branches

If you know two machines will edit the same skill:

```powershell
# Machine 1
git switch -c skills/machine-1
# edit → commit → push

# Machine 2
git switch -c skills/machine-2
# edit → commit → push

# Later, merge both into main
git switch main
git merge skills/machine-1
git merge skills/machine-2
git push origin main
```

Git auto-merges if files are different; conflicts only if same file was edited.

## What to Commit vs. Keep Local

### Commit to repo (shared across machines)

- `skills/<category>/<skill-name>/SKILL.md`
- `skills/<category>/<skill-name>/references/`
- `skills/<category>/<skill-name>/scripts/`
- `skills/<category>/<skill-name>/templates/`
- `deploy/setup-admin.ps1`, `deploy/sync-skills.ps1`
- `deploy/hermes-home/config.yaml`, `SOUL.md` (if shared)
- `deploy/hermes-home/.env`, `auth.json` (bootstrap only)
- `deploy/hermes-home/cron/jobs.json` (canonical cron job definitions across farm machines)
- `deploy/hermes-home/scripts/*.py` (cron runner scripts deployed to `%LOCALAPPDATA%\hermes\scripts\`)

### Keep local (machine-specific)

- `%LOCALAPPDATA%\hermes\.env` (live credentials, not bootstrap)
- `%LOCALAPPDATA%\hermes\auth.json` (live auth, not bootstrap)
- `%LOCALAPPDATA%\hermes\cron\executions.db` (local execution history/state)
- `%LOCALAPPDATA%\hermes\cron\.jobs.lock`, `.tick.lock`, `ticker_*` (runtime locks)
- `%LOCALAPPDATA%\hermes\skills/.usage.json` (runtime stats)
- `%LOCALAPPDATA%\hermes\skills/.curator_state` (curator state)
- Any skill that references:
  - Machine-specific paths (`D:\Taadaa\...` vs `C:\Users\...`)
  - Machine-specific devices/hardware
  - Machine-specific credentials
  - Experimental/personal skills

### Machine-local skills location

Create skills directly in runtime:
```text
%LOCALAPPDATA%\hermes\skills\local\my-skill\SKILL.md
```

These are not synced and remain private to that machine.

## Pitfalls

### 1. Do not edit runtime skills directly

If you edit `%LOCALAPPDATA%\hermes\skills\autonomous-ai-agents\claude-code\SKILL.md`, the next `sync-skills.ps1` will overwrite it. **Always edit the repo version**, then sync.

### 2. Do not commit deploy/hermes-home/skills/

This was an early mistake. The deploy bundle should not snapshot skills; that causes divergence. `.gitignore` should exclude `deploy/hermes-home/skills/`.

### 3. Do not use `git pull` without `--rebase`

Without `--rebase`, Git creates merge commits for every pull, polluting history. Always:
```powershell
git pull --rebase origin main
```

### 4. Do not push before pulling

If Machine 2 has uncommitted changes and tries to push without pulling Machine 1's changes first, Git will reject the push (non-fast-forward). Always pull first.

### 5. Robocopy exit codes

Robocopy uses non-standard exit codes:
- 0–7: Success (0 = no files copied, 1–7 = files copied with various success levels)
- >7: Error

`sync-skills.ps1` checks `$RobocopyExitCode -gt 7` to detect errors.

### 6. Stash vs. WIP commit

- **Stash**: Cleaner, no commit in history, but must remember to `stash pop`
- **WIP commit**: Safer if changes are substantial, but adds a "WIP" commit to history

For most cases, use stash.

## Remote OmniRoute & 9Router LAN Setup (Admin PC → Kibe PC)

When connecting a secondary machine (Admin) to the main machine's (Kibe) dual LLM proxy stack (OmniRoute at `:20129` for primary routing/combos and 9Router at `:20128` for fallback/auxiliary/compression):

1. **Find Kibe IP on LAN:** (e.g. `192.168.110.123` or Tailscale `100.88.164.111`)
2. **Set Environment Keys on Admin:**
   ```powershell
   [System.Environment]::SetEnvironmentVariable('NINEROUTER_API_KEY', '<real-key-from-kibe>', 'User')
   [System.Environment]::SetEnvironmentVariable('OMNIROUTE_API_KEY', '<real-key-from-kibe>', 'User')
   # Open a NEW PowerShell window to load environment variables, or add to %LOCALAPPDATA%\hermes\.env
   ```
3. **Configure Hermes on Admin (Current v12+ Keyed Schema):**
   ```powershell
   # 1. 9Router (port 20128)
   hermes config set providers.9router.api "http://192.168.110.123:20128/v1"
   hermes config set providers.9router.key_env "NINEROUTER_API_KEY"
   hermes config set providers.9router.transport "chat_completions"
   hermes config set providers.9router.default_model "gpt-5.6-luna"

   # 2. OmniRoute (port 20129)
   hermes config set providers.omni.api "http://192.168.110.123:20129/v1"
   hermes config set providers.omni.key_env "OMNIROUTE_API_KEY"
   hermes config set providers.omni.transport "chat_completions"
   hermes config set providers.omni.default_model "ag-gemini-pool-3"
   hermes config set providers.omni.discover_models false
   hermes config set providers.omni.models.ag-gemini-pool-3 "{}"

   # 3. Model defaults, native vision & compression
   hermes config set model.provider "omni"
   hermes config set model.default "ag-gemini-pool-3"
   hermes config set model.context_length 1000000
   hermes config set agent.image_input_mode "native"
   hermes config set agent.reasoning_effort "high"
   hermes config set auxiliary.compression.provider "omni"
   hermes config set auxiliary.compression.model "ag-gemini-pool-3"

   # 4. Multi-tier Subagent Delegation & Fallback Chain (T1: Omni AG Gemini -> T2: 9Router Worker -> T3: Omni Free)
   hermes config set delegation.provider "omni"
   hermes config set delegation.model "ag-gemini-pool-3"
   hermes config set delegation.reasoning_effort "high"
   hermes config set delegation.max_concurrent_children 4
   hermes config set delegation.max_iterations 100
   # Fallback chain for worker / delegation:
   # Level 1: ag-gemini-pool-3 (OmniRoute) -> Level 2: worker (9Router port 20128) -> Level 3: omni-free (OmniRoute)
   ```
   *Note:* Avoid legacy `auxiliary.vision` unless using a strictly text-only model. Setting `agent.image_input_mode: native` passes images directly to multimodal models (Gemini / Claude / GPT) without intermediary tool failures.
4. **API key validation:** 9Router and OmniRoute validate keys against their local databases. API keys must be real strings (never dummy `'***'`). Read active keys from Kibe `%APPDATA%\9router\db\data.sqlite` or `%LOCALAPPDATA%\hermes\.env`.
4. **Periodic Auto-Sync Cron (sync-hermes-skills-to-git):**
   Place script inside `%LOCALAPPDATA%\hermes\scripts\` and create the recurring job:
   ```powershell
   hermes cron create "every 30m" --name "sync-hermes-skills-to-git" --no-agent --script "sync-skills-to-repo.ps1"
   ```
   *CLI Rule:* `hermes cron create` expects schedule as positional arg (`"every 30m"` for recurring forever; plain `"30m"` creates a one-shot job). Script path must be relative to `~/.hermes/scripts/`.
5. **Taadaa Multi-Machine Data & Config:**
   - Host config: `TAADAA_HOST_CONFIG = D:\Taadaa\machine-config\admin.yaml`
   - Shared config/tools synced via OneDrive junction `D:\OneDrive\Taadaa_Sync_Shared`.
   - Separate per-host proxy mapping files: `D:\OneDrive\TaadaaData\admin\PROXYgandienthoai.xlsx` for Admin (200+) vs `D:\OneDrive\TaadaaData\kibe\PROXYgandienthoai.xlsx` for Kibe (1-80).
   - New-host data workbooks = headers-only templates (never copy live rows); never copy `runtime/` between hosts.
   - Full provisioning guide: `D:\Taadaa\HUONG_DAN_CAI_DAT_MAY_ADMIN.md` (mirrored in OneDrive `Taadaa_Sync_Shared`).
 Complete per-host recipe (branch map, data templates, venv, pitfalls from the 2026-08-23 Admin setup): `references/taadaa-multi-host-provisioning.md`.

### Guiding a remote setup over chat (RDP/screenshots)

The user drives the second PC while pasting screenshots back. **Send ONE command block per message**, wait for their screenshot/result, verify, then send the next step. Dumping all steps at once produced missed pieces (dropped `-m` in `python -m venv`, silently-failing double-clicked `.bat` files inside OneDrive paths). Prefer direct PowerShell commands over `.bat` double-clicks; private repos need one interactive `git clone` first to trigger the GitHub Credential Manager browser flow (`gh` CLI usually absent).

## Verification

After deployment or sync, verify:

```powershell
hermes --version
hermes doctor
hermes skills list
claude --version
codex --version
```

All should succeed without errors.

## Two-agent review loop (for Hermes development)

When modifying Hermes itself (not just skills), use this loop:

1. **Codex** → plan (what to change, file paths, migration steps)
2. **Codex** → code (implement within scope, do not touch unrelated dirty files)
3. **Claude** → audit (verify correctness, edge cases, acceptance criteria)

Prompt patterns:
- Codex plan: `"Create an implementation plan only; do not edit files or commit..."`
- Codex code: `"Implement the approved plan. You may edit ONLY: ... Do not touch unrelated dirty files..."`
- Claude audit: `"Audit the implementation. Do not edit files or commit. Check correctness against requirements..."`

See also: `agent-review-loops` — canonical worker↔reviewer loop protocol (relay RAW outputs, Phase-3 final gate, max rounds).

Full loop details: `references/two-agent-review-loop.md` (merged from the former `hermes-multi-deploy` skill).

## References

- `references/admin-bot-model-sync-prompt.md` — Self-contained prompt recipe for automating secondary machine (Admin) Hermes setup via its own bot
- `references/cron-deployment-sync.md` — Cron jobs.json and scripts bundle deployment architecture and sync recipe
- `references/two-agent-review-loop.md` — two-agent review loop for Hermes development
- `references/deploy-scripts.md` — Detailed implementation of setup-admin.ps1 and sync-skills.ps1
- `references/git-workflow.md` — Git commands for multi-machine coordination
- `references/upgrade-git-install.md` — Upgrading a git-installed Hermes source tree (shallow-clone unshallow, stash/merge/pop, CRLF-vs-logic conflict resolution, venv reinstall after big upstream merges)
- `references/restore-codex-removed-feature.md` — Restoring a feature Codex removed from the Hermes source tree (runtime-sync-package-backups as pre-deletion snapshot; 4-layer DB/RPC/tool/model-context restore; porting 0.18.2 RPC files into 0.20.0 server.py; temp-DB schema pitfall)
