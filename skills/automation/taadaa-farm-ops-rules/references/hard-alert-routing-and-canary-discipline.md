# Hard Alert Routing and Canary Discipline (ALL-Repo Farm)

## Background & Root Cause
When an incident alert (`🚨 [MÁY N] DỪNG PHIÊN`) arrives, the agent must NOT suffer from session inertia (e.g. running feed runner `run_tiktok.py` from `tiktok-luot nuoi acc` when the alert was produced by `tiktok-follow`).

## Hard-Routing Table

| Alert `• Script:` Value | Owning Repo Path | Official Canonical Runner / Canary |
| :--- | :--- | :--- |
| `tiktok-follow` | `D:\Taadaa\tiktok-follow` | `/d/Taadaa/python-envs/automation/Scripts/python.exe follow_runner/run_follow.py --machine N --mode 2 --config config/<cfg>.yaml --account-row-index <slot>` |
| `multi-machine-feed-session` / `feed` | `D:\Taadaa\tiktok-luot nuoi acc` | `/d/Taadaa/python-envs/automation/Scripts/python.exe run_tiktok.py --mode feed-session-smoke --device <serial> --account <acc> --machine <N> ...` |
| `social_reg` / `tiktok-reg` | `D:\Taadaa\Tiktok_Reg` | `/d/Taadaa/python-envs/automation/Scripts/python.exe social_reg_v1.py` / designated reg runners |
| `tiktok_upload` / `video` | `D:\CodexRuntime\tiktok-video` | Official upload batch runner |
| `tik3_render` / `render` | `D:\Taadaa\tik3_render` | Official render batch runner |

## Rules & Invariants
1. **Source of Truth:** The `Script:` field in the Farm Alert is the single source of truth for identifying the owning repository and runner.
2. **Cross-Runner Quarantine:** Absolutely NEVER invoke a runner from another repo (e.g. feed runner for a follow incident, or reg runner for an upload incident).
3. **Preflight Statement:** Before taking any live device action or canary run, state the routing resolution explicitly:
   `[ROUTING]: Script=<alert_script> -> Repo=<target_repo> -> Runner=<command>`
