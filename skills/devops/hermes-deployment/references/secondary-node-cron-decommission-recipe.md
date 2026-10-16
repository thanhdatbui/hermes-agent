# Secondary Farm Node (Admin) Cron Decommissioning & Centralization Recipe

## 1. Context & Objective
When migrating from a dual-coordinator farm to a **Single Control Plane (Kibe Master ↔ Admin Thin Worker)**:
- Secondary node (Admin 201-280) stops running independent feed runners and Telegram reporting crons.
- Kibe Master takes over all scheduling (via dual-cluster `tiktok_runner.py`), monitoring (`feed_session_watchdog.py`), and alerting (`-5373649734`, `-5377611430`, `-5435853713`).
- Admin retains local-only maintenance and heavy worker processes (video rendering/downloading, local lock reaper, workbook sync).

## 2. Remote Command Execution Pattern (Allowlist-Safe)
Raw SSH (`ssh admin-farm ...`) is blocked by Coordinator terminal guard allowlists.
Use the pre-approved wrapper on Kibe:
```bash
python D:/Taadaa/tools/admin_ssh_exec.py "<command>"
```
*Note:* Always pass timeout <= 60s when invoking via Hermes `terminal` tool.

## 3. Categorization of Secondary Node Cron Jobs

### Group A: PAUSE (Reporting Watchdogs & Duplicate Schedulers)
These jobs cause alert spam, Telegram bot confusion, or runner race conditions on devices M201-280:
```powershell
# 1. Dual-Cluster runner & picker (Kibe Master already runs dual-cluster)
hermes cron pause <picker_id>               # phase9-staging-picker
hermes cron pause <runner_id>               # phase9-runner-tiktok-feed

# 2. Telegram reporting watchdogs (all pointing to secondary bot telegram:-5188753741)
hermes cron pause <feed_watchdog_id>        # tiktok-feed-session-watchdog
hermes cron pause <clear_cache_id>          # end-of-day-clear-tiktok-cache
hermes cron pause <render_watchdog_id>      # farm-render-download-watchdog
hermes cron pause <gmail_2fa_id>            # post-morning-gmail-2fa-watchdog
hermes cron pause <noon_chain_id>           # post-noon-chain-watchdog
hermes cron pause <avatar_id>               # post-evening-avatar-watchdog
hermes cron pause <gpm_login_id>            # post-evening-gpm-login-watchdog
hermes cron pause <hermes_stale_id>         # hermes-stale-watchdog
hermes cron pause <auto_trim_id>            # auto-trim-startup-files
```

### Group B: EDIT TO `--deliver local` (Host Protection Watchdogs)
Jobs that protect the physical machine (e.g. killing background screen caster to free USB bus) must continue running, but must be silenced:
```powershell
hermes cron edit <xiaowei_id> --deliver local   # xiaowei-idle-auto-close-admin
```

### Group C: KEEP ACTIVE (`deliver: local`)
These jobs execute hardware-local work on Admin and must not be touched:
- `taikhoan-run-safe-sync`: keeps `taikhoan_run_safe.xlsx` mirrored.
- `reap-dead-owner-locks`: cleans dead locks on Admin devices.
- `admin-render-worker-watchdog`: renders TikTok videos locally on Admin GPU/CPU.
- `admin-downloader-watchdog`: downloads raw footage locally.
- `sync-all-tik-keywords-cron`: syncs keyword tags locally.
- `tiktok-rolling-rename-watchdog`: local nickname rotation if configured.
- `gateway-idle-restart-watchdog`: ensures local Hermes gateway restarts cleanly.

## 4. Post-Migration Verification Checklist
1. **Admin Cron Status:**
   ```bash
   python D:/Taadaa/tools/admin_ssh_exec.py "hermes cron list"
   ```
   Verify 0 jobs have `Deliver: telegram:...`. All active jobs must show `Deliver: local`.
2. **Kibe Remote ADB Health:**
   ```bash
   python D:/Taadaa/tools/inspect_machine.py 201
   python D:/Taadaa/tools/inspect_machine.py 280
   ```
   Verify response is instant (<2s) and serial matches `PROXYgandienthoai.xlsx`.
3. **Kibe Dual-Cluster Runner Parity:**
   Verify `phase9-runner-tiktok-feed` on Kibe logs `[kibe]` and `[admin]` clusters in `D:/Taadaa/runtime/admin/cron-state/runner_simple_state.json`.
