# Multi-Repo Workspace Hygiene and Artifact Cleanup

## Multi-Repo Environment Pattern
When working in multi-repository workspaces (e.g. `D:\Taadaa` containing 14+ independent Git repos), automated agents, policy sync scripts, and batch tasks frequently create untracked residue:

1. **Backup File Proliferation (`*.bak*`):**
   - Automated sync scripts for `AGENTS.md` and `PROJECT_RULES.md` leave timestamped backups across multiple repos (`AGENTS.md.bak-*`, `AGENTS.md.flash-high-*.bak`, `AGENTS.md.luna-sync-*.bak`, `*.py.bak-*`).
   - These pollute `git status --porcelain` and create false signals during multi-repo audits.

2. **Top-Level Stray Artifacts:**
   - Stray `.git/` or `.agents/` directories at the workspace root (outside individual repos) that are not active repos.
   - Temporary scripts (`tmp_*.py`) and ad-hoc analysis workbooks (`Bao_Cao_*.xlsx`).

3. **Debug & Test Artifacts:**
   - Ad-hoc test screenshots (`auth_check_*.png`, `chrome_test*.png`, `m*_check.png`) dumped in repository root directories instead of ephemeral temp folders.
   - Malformed batch redirection files (e.g., Windows `nul` file).
   - Old batch assignment manifests (`assignment-manifest-*.json`) and temporary result lists (`die_*.txt`, `live_*.txt`).

## Safe Inventory & Cleanup Rules

1. **Segregation of Protected vs Cleanup Scope:**
   - **Protected (NEVER delete):** `runtime/` (locks, live state), `python-envs/` (virtualenvs), `machine-config/` (host definitions), `tools/` (core scripts), `BACKUP_ALL/`.
   - **Cleanup Scope:** `*.bak*` across all repos, stray empty root dirs (`.git/`, `.agents/`), root-level test screenshots, obsolete `tmp_*.py`.

2. **Inventory Verification Pattern:**
   Always run a non-destructive audit script to categorize files before taking any bulk delete actions:

```python
import os

base = 'D:/Taadaa'
repos = [d for d in os.listdir(base) if os.path.isdir(os.path.join(base, d, '.git'))]

bak_files = []
for r in repos:
    r_path = os.path.join(base, r)
    for root, dirs, files in os.walk(r_path):
        if any(x in root for x in ['.git', 'runtime', 'python-envs', 'BACKUP_ALL']):
            continue
        for f in files:
            if '.bak' in f or f.endswith('.bak'):
                bak_files.append(os.path.join(root, f))
print(f"Total .bak files across repos: {len(bak_files)}")
```
