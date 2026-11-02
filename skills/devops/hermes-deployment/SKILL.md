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
│   ├── sync-from-kibe.ps1     ← 1-click update/sync script for Admin PC
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

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
