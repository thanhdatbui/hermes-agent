# 6H Lifecycle Report Snapshot Reconciliation

## Why this matters
A 6-hour lifecycle report is a point-in-time snapshot. The supervisor may process more profiles after the report is generated, so a later read of the canonical state can legitimately contain new BLOCKED entries. Do not silently treat the delivered report as current state.

## Reconciliation procedure
1. Record the report/job generation time from the scheduler metadata when available.
2. Read the canonical Kibe and Admin supervisor state files directly; do not infer current counts from the Telegram text alone.
3. Recompute BLOCKED as `status in {BLOCKED, FAILED, ERROR, QUARANTINE}` and split by farm, stage, and status.
4. Compare each newly observed blocked profile's `updated_at` to the report snapshot time. Attribute only entries updated after the snapshot as post-report delta.
5. Inspect `last_result`, history, and available artifacts before assigning a cause. A bare `status=FAILED` is insufficient evidence for claiming Microsoft service error, OTP rate-limit, or missing recovery data.
6. Keep fail-closed behavior: do not bulk reset or retry BLOCKED/QUARANTINE profiles. Reopen only after per-profile cause, cooldown, and required recovery/security data are verified.

## Reporting style
Lead with deltas and actions, not a verbatim restatement of every metric. Explicitly call out report-vs-live-state mismatches and the evidence for any post-report additions. If the error payload is absent, say the cause is unclassified rather than guessing.

## Two Distinct Reporting Streams for Hotmail
1. **GPM PC Lifecycle (`hotmail-gpm-lifecycle-6h-report`, job `61570a1e37b1` → `telegram:-5583559484`)**:
   - Scope: Hotmail accounts in GPMLogin browser profiles on PC (`HOTMAIL_LOGIN` → `CHATGPT_REG` → `WAIT_7D` → `CHANGE_INFO` → `DONE`).
   - Reporting cadence: Every 6 hours (`0 */6 * * *` at `00:00, 06:00, 12:00, 18:00`).
   - Delivery destination: Delivered specifically to the dedicated Hotmail Telegram channel/topic (`telegram:-5583559484`), NOT to general Farm Alerts (`-5373649734`) or user DM threads.
   - Stage visibility invariant: Báo cáo 6h BẮT BUỘC duy trì đủ 4 khối theo vòng đời:
     (1) `🔑 TIẾN ĐỘ HOTMAIL LOGIN` (Login OK, PENDING, BLOCKED 48h cooldown)
     (2) `🤖 TIẾN ĐỘ CHATGPT REG`
     (3) `🔐 TIẾN ĐỘ CHANGE HOTMAIL & BẢO MẬT` (DONE, CHANGE_INFO, WAIT_7D)
     (4) `🌐 CHATGPT WEB POOL (:20129)`
     CẤM cắt bỏ khối Login khi nâng cấp các khối khác để đảm bảo tính observability.
   - Canonical partition formula (zero-leak invariant: `login_ok + login_pending + login_blocked == total`):
     ```python
     login_ok = sum(1 for p in profiles.values() if p.get("hotmail_login_at") or p.get("stage") != "HOTMAIL_LOGIN")
     login_pending = sum(1 for p in profiles.values() if p.get("stage") == "HOTMAIL_LOGIN" and p.get("status") not in {"BLOCKED", "FAILED", "ERROR", "QUARANTINE"} and not p.get("hotmail_login_at"))
     login_blocked = sum(1 for p in profiles.values() if p.get("stage") == "HOTMAIL_LOGIN" and p.get("status") in {"BLOCKED", "FAILED", "ERROR", "QUARANTINE"} and not p.get("hotmail_login_at"))
     ```
   - Deployment & synchronization: Khi chỉnh sửa script tại `D:/Taadaa/Hermes/deploy/hermes-home/scripts/cron_hotmail_gpm_lifecycle_6h_report.py`, BẮT BUỘC chạy `python D:/Taadaa/Hermes/deploy/hermes-home/scripts/cron_sync_watchdog.py` để đồng bộ sang local runtime và OneDrive Shared. Kích hoạt ngay bản tin mới bằng `cronjob(action='run', job_id='61570a1e37b1')`.
2. **Physical Phone Farm Outlook App (`post_noon_chain_watchdog` → `telegram:-5373649734` & `daily-tiktok-farm-tracker`)**:
   - Scope: Hotmail/Outlook accounts logged into the Outlook Android app on physical farm devices (`app_logged_in = 1` in `gmail_clean_v2.xlsx`).
   - Reporting cadence: Post-noon shifts (14:00–18:00) and 07:00 daily farm tracker.
   - When asked where "tiến độ login hotmail" is reported, distinguish GPM PC lifecycle vs physical phone farm Outlook app.

## Farm Admin (M201-280) vs Farm Kibe (M1-80) GPM Lifecycle Architecture (Updated 2026-10-13)
- **HOTMAIL_LOGIN mandatory locking**: As of 2026-10-13, the side-effect jumping from `HOTMAIL_LOGIN` directly to `CHATGPT_REG` when Microsoft Graph OAuth tokens exist was eliminated. `HOTMAIL_LOGIN` is now the mandatory initial stage for ALL Hotmail accounts across both Kibe and Admin to persist authenticated sessions/cookies in GPMLogin profiles on Kibe.
- **Why Admin ChatGPT Reg paces at 28/day**: Farm Admin only has 28 distinct Mikrotik proxy ports (`10008`–`10035`) shared across 80 machines. The supervisor enforces a strict 24h cooldown per proxy port for the same operation (`ip_action_history[port][stage]`). Thus, Admin can only process 28 accounts/day. In reports showing e.g. 84/620 (28 x 3 days) with 535 pending, the remaining accounts are NOT broken; they are safely waiting for the 24h per-IP cooldown window to roll over.
- **Kibe vs Admin Proxy Port Reality & Historical Throughput**:
  - Kibe has 39 distinct proxy ports (`5101`–`5180`), whereas Admin has only 28 ports (`10008`–`10035`). Never assume Admin has more proxy ports.
  - Admin's historical 344 accounts in `WAIT_7D` was achieved because accounts with tokens skipped `HOTMAIL_LOGIN` prior to 2026-10-13.
  - Kibe's slower throughput was compounded by a false-positive bug in `batch_gpm_hotmail_password_login.py`: matching `"bảo vệ tài khoản"` on the `account.microsoft.com` homepage cards misclassified successful logins as `BLOCKED: PROTECT_ACCOUNT_VERIFICATION`, which penalised the account with 48h cooldown and locked the proxy port for 24h. Always gate challenge detection to `login.live.com` / `login.microsoftonline.com` only.

## Evidence pattern from the lifecycle farm
A report showing 51 Kibe BLOCKED was followed by a live state showing 53: the canonical state had 52 `CHANGE_INFO` BLOCKED and 1 `HOTMAIL_LOGIN` QUARANTINE, with two profiles' `updated_at` values after the report snapshot. This is the expected way to explain a stale report without rewriting historical telemetry.
