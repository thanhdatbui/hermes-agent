# Rollout Summary: ATX-Agent Primary across all Automation Repos (2026-08-17)

## Overview
All automation repositories in `D:\Taadaa` have been scanned, refactored, and verified to ensure ATX-Agent (Port 7912) session capture is the primary UI dump method, making shell `uiautomator dump` a fallback-only mechanism.

## Results by Repo

1. **`automation-core`**:
   - ATX session primary capture implemented via `persistent_ui.capture_atx_session_ui`.
   - Uses dynamic local port allocation (`adb forward tcp:0 tcp:7912`) to prevent multi-device race conditions.
   - Exported `resolve_proxy_mapping_path` in `automation_core.preflight`.
   - Synchronized with `D:\Taadaa\python-envs\automation\Lib\site-packages\automation_core\`.
   - Tests: 590/590 passed.

2. **`tiktok-follow`**:
   - Removed `lightweight=True` in `FollowAdapter.dump_ui` (which forced shell `uiautomator dump` bypass).
   - Updated layout selectors and sticky header scroll anchor handling for TikTok 46.x.
   - Tests: 280/280 passed.

3. **`tiktok-video`**:
   - Uses `capture_persistent_ui` / `capture_ui_xml` with ATX primary.
   - Updated test assertions for pinned core runtime version `0.4.44`.
   - Tests: 359/359 passed.

4. **`Tiktok_Reg`**:
   - Uses `_atx_capture_ui_xml` as primary in `get_ui_xml` with fallback ladder.
   - Tests: timeout suite passed.

5. **`Hotmail`**:
   - Uses ATX-primary first in `ui_xml`.
   - Tests: 184/184 passed.

6. **`tiktok-log-in`**:
   - Uses `capture_ui_xml` and `resolve_proxy_mapping_path` from core.
   - Tests: 190/190 passed.

7. **`tiktok-luot nuoi acc`**:
   - Skipped per user instruction.

8. **`tiktok-add-bao-mat-f2a`**:
   - Uses `capture_ui_xml` via core.
   - Tests: 173/173 passed.

9. **`register gmail`**:
   - Uses `capture_ui_xml` via core.
   - Tests: 70/70 passed.

## Root Directory Cleanup Policy
- `D:\Taadaa` root directory is kept clean, containing only canonical consumer repos, shared runtime (`python-envs`, `runtime`, `tools`, `machine-config`), and core repo docs.
- All temporary worktrees (`*-wt`, `*-worktrees`), temporary rule backups (`*.bak-*`, `rule-merge-backup*`), and root audit reports are archived in `D:\Taadaa\BACKUP_ALL`.
