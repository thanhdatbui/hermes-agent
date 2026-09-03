# Taadaa Workspace & Multi-Repo Hygiene and Cleanup

## Architecture & Layout Context
`D:\Taadaa` is a container directory hosting 14+ independent Git repos (such as `automation-core`, `Tiktok_Reg`, `Hermes`, `Tiktok-video`, `tiktok-luot nuoi acc`, `Hotmail`, `gan-proxy`, etc.), along with shared configurations and runtime folders.

`D:\Taadaa` itself is **NOT a Git repository** — any top-level `.git/` folder is a stray/empty artifact that causes confusion with tooling.

## Taxonomy of Junk & Artifacts

### 1. Root-Level Stray Artifacts (`D:\Taadaa\`)
* **Empty directories:** `D:\Taadaa\.git`, `D:\Taadaa\.agents`.
* **Ad-hoc scripts & exports:** `tmp_*.py` (e.g. `tmp_build_cron_inputs.py`), temporary reconciliation Excels (e.g. `Bao_Cao_*.xlsx` generated during manual audits).
* **Tool backups:** `D:\Taadaa\tools\*.bak*` left over from manual script tweaks.

### 2. Multi-Repo Backup & Sync Residue
* **Agent rule sync backups:** Syncing policies or editing `AGENTS.md` / `PROJECT_RULES.md` across repos creates backup files:
  * `AGENTS.md.bak-*`
  * `AGENTS.md.flash-high-*.bak`
  * `AGENTS.md.luna-sync-*.bak`
  * `*.py.bak-*`
* **Impact:** 80+ untracked files cluttering `git status --porcelain` across the 14 repos, making status noisy and obscuring genuine code changes.

### 3. Test & Debug Artifacts
* **Root test screenshots:** Probe runs saving screenshots directly to repo roots (e.g., `automation-core\auth_check_m*.png`, `gan-proxy\chrome_test*.png`).
* **Windows stray files:** `gan-proxy\nul` (created by incorrect redirection in batch/shell).
* **Temporary text exports:** `die_full.txt`, `die_usernames.txt`, `live_full.txt`, `live_usernames.txt` in `site ban hang clone`.
* **Stale run manifests:** Old `assignment-manifest-avatar-*.json` in `Tiktok-video`.

### 4. High-Volume Batch Run Screenshots
* `Tiktok_Reg\screenshots_social\`: Captures OTP and UI recovery screens across dozens of devices and sessions.
* `Hotmail\.ai-runs\`: Screenshots from password change and recovery test runs.

---

## Safe Scan & Inventory Script

To audit junk across `D:\Taadaa` and all repos without risking essential runtime or model data:

```python
import os, subprocess

base = 'D:/Taadaa'
repos = [d for d in os.listdir(base) if os.path.isdir(os.path.join(base, d, '.git'))]

# 1. Scan .bak and temporary files in code repos (exclude runtime, python-envs, BACKUP_ALL)
bak_files = []
test_pngs = []
temp_manifests = []

for r in sorted(repos):
    r_path = os.path.join(base, r)
    for root, dirs, files in os.walk(r_path):
        if any(x in root for x in ['.git', 'runtime', 'python-envs', 'BACKUP_ALL', 'node_modules']):
            continue
        for f in files:
            p = os.path.join(root, f)
            if '.bak' in f or f.endswith('.bak'):
                bak_files.append(p)
            elif (f.endswith('.png') or f.endswith('.jpg')) and ('screenshots' not in root and 'assets' not in root and 'icons' not in root and 'static' not in root):
                test_pngs.append(p)
            elif f.startswith('assignment-manifest-') or f.startswith('tmp_'):
                temp_manifests.append(p)

print(f"Found {len(bak_files)} .bak files")
print(f"Found {len(test_pngs)} root test images")
print(f"Found {len(temp_manifests)} temp manifests/scripts")
```

---

## Protected Directories (NEVER auto-delete)
1. `D:\Taadaa\machine-config\`: Device mappings (`kibe.yaml`, `admin.yaml`).
2. `D:\Taadaa\python-envs\`: Virtual environments.
3. `D:\Taadaa\runtime\`: Lock files, active run state, worker telemetry.
4. `D:\Taadaa\BACKUP_ALL\`: Explicit cold backups.
5. `D:\Taadaa\add mail khoi phuc\`: Specialized workflow tooling.
6. `D:\Taadaa\tools\`: Core farm utility scripts (except `*.bak*`).
