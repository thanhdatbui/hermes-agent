# Recovery-Adapter Migration Program State (2026-08-12)

Plan: `D:\Taadaa\automation-core\.hermes\plans\2026-08-12_consumer-recovery-adapter-migration.md`
Program state là condensed knowledge cho các phase sau; chi tiết từng phase nằm trong report tương ứng.

## Phases

- **P1 — `tiktok-luot nuoi acc` (feed)**: discovery → **READY_FOR_P1_IMPLEMENTATION**.
  Report: `D:\Taadaa\tiktok-luot-nuoi-acc-recovery-adapter-p1-wt\docs\ai\recovery-adapter-discovery-feed-2026-08-12.md`.
  Seams: `flows/feed_swipe_smoke.py:1020-1043` (terminal_recovery branch, CAPTURE_RECOVERY_ATTEMPT_BUDGET_EXHAUSTED/FINAL_BLOCKED); `core/ui_capture.py:110-112` (opt-in `capture_recovery_callbacks` hook, chưa được feed flow truyền); scheduler-side registry `scheduler/recovery_runtime.py:2928` (chỉ scheduler/supervisor gate, không phải in-process feed path).
  Baseline: 72+12 tests xanh; 2 module chết ở collection do pre-existing PIL `_imaging` ImportError (hermes venv).

- **P2 — `tiktok-log-in` (login)**: discovery → **READY_FOR_P2_IMPLEMENTATION** (2026-08-12).
  Report: `D:\Taadaa\tiktok-log-in-recovery-adapter-p2-wt\docs\ai\recovery-adapter-discovery-login-2026-08-12.md`.
  Seams:
  - A) `login_runner/executor.py:97` — choke point `_save_result(job, outcome.status, outcome.reason, ...)`: mọi outcome đi qua; map FAILED_SAFE / `TERMINAL_ACCOUNT_STATES` (`:36-38`: account_banned→FAILED_SAFE, login_rate_limited→RETRYABLE) → NON_RETRYABLE. Offline-testable: `tests/test_executor.py` (24 tests, toàn fake).
  - B) `login_runner/account_reconcile.py:282-285` — `FINAL_BLOCKED repeated inventory failure` = budget-exhausted (`lease is None or recovery_state["rebooted"]` sau 1 app restart + tối đa 1 guarded reboot) → map FAILED_LOCKED. Offline-testable: `tests/test_account_reconcile.py:237-250`.
  - C) Retryable hooks: `account_reconcile.py:453-521` (vòng 2 attempts/account) + `:273-278` (app-restart inventory retry) + RETRYABLE outcomes executor (`:79,81,92,172,191,202,224`).
  Guided recovery: **DISPROVED** (0 reference trong toàn bộ allowlist).
  Baseline: 48 passed / 1 failed (exit 1) — pre-existing: sibling `D:\Taadaa\Tiktok_Reg` thiếu `scripts.target_inventory` (ModuleNotFoundError qua isolated-provider import test).
  Runtime paths là 2 process riêng: `scheduler.py` → subprocess `scripts/reconcile_tiktok_accounts.py` (reconcile_target + _collect_with_recovery); `cli.py --live` → `LoginExecutor.execute` in-process.

## Recurring facts

- Origin repos dirty theo thiết kế (tiktok-log-in: 12 file ` M`, trong đó `login_runner/password_change.py` **FORBIDDEN** — không bao giờ mở).
- Interpreter mặc định cho baseline: hermes venv `C:\Users\Kibe\AppData\Local\hermes\hermes-agent\venv` (CPython 3.11.15, uv base); `automation_core` installed = **0.4.43** (không phải pin consumer).
- Pin consumer (clean HEAD): feed → core wheel 0.4.18; login → `requirements-automation-core.txt:2` tên wheel `automation_core-0.4.5` (plan nói dirty pin 0.4.24 — chưa verify, file dirty không đọc). Target chung: **core 0.4.45** (`automation-core/pyproject.toml:7`).
- Evidence dir ngoài repo theo consumer/phase: `C:\Users\Kibe\p<n>-<consumer>-discovery-evidence-<date>\`.
- Worktree naming: `D:\Taadaa\<consumer>-recovery-adapter-p<n>-wt` (branch `recovery-adapter/<consumer>-p<n>-<kind>`).
