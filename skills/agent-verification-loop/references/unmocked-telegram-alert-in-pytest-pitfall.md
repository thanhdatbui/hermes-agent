# Case Study: Unmocked Alert Dispatcher in Unit Tests Causing Live Telegram Spam

## Incident Summary (2026-09-24)
- **Symptom:** User received 3 duplicate Telegram alert messages on the Farm Alerts group (`-5373649734`) within 4 minutes:
  ```text
  📋 [PREFLIGHT REG BÙ ROW 5]
  • Tổng máy thiếu: 1 (Đã chạy: 4, Cooldown: 1)
  ❌ Thất bại (4):
    - Máy 76: Máy đã đủ 8 acc (Lệch Excel - Cần kiểm tra backfill)
    - Máy 201: ...
  ```
- **Timeline & Trigger:**
  - 06:59:53, 07:02:22, 07:03:13: Another agent session ran `pytest D:/Taadaa/tools/tests/test_ensure_row_accounts.py` 3 times.
  - The test `test_admin_adb_socket_telemetry` invoked `era.run_tiktok_reg_for_machines([201], row=5, max_workers=1)`.
  - While `subprocess.run` was mocked, `send_telegram_summary` was NOT mocked.
  - `send_telegram_summary` executed a real HTTP POST request to Telegram via `requests.post`.
  - Inside `send_telegram_summary`, without a timestamp filter, it picked up the most recent run on disk (`20260924-060255`, which was an earlier run of Machine 76), combining Machine 76's failure with Machine 201 from the test parameters.

## Root Causes
1. **Unmocked External Dispatcher:** Tests exercising functions that have alert/reporting side-effects must either mock the dispatcher (`monkeypatch.setattr(era, "send_telegram_summary", lambda *a, **kw: None)`) or mock `requests.post`.
2. **Zombie Stale Artifacts in Reporting:** `send_telegram_summary` picked the latest folder in `runs/social-batch-all` purely by sorting mtime descending, without verifying whether that folder was created by the *current* execution run (`mtime >= batch_start_time - 10`).

## Solution & Invariants
1. **Production Hard Guard:**
   Always add an environment check inside outbound alert functions:
   ```python
   if "pytest" in sys.modules or os.environ.get("PYTEST_CURRENT_TEST"):
       print("[tool] [TEST ENV] Skipped alert dispatch during test execution.")
       return
   ```
2. **Batch Timestamp Scoping:**
   Pass `batch_start_time` down to reporting functions and filter artifact directories:
   ```python
   if batch_start_time is not None:
       min_ts = batch_start_time.timestamp() - 10
       dirs = [d for d in dirs if d.stat().st_mtime >= min_ts]
       if not dirs:
           return  # Skip summary if no new artifacts were produced
   ```
3. **Unit Test Verification:**
   Add an explicit unit test verifying that the alert dispatcher refuses to send network requests when run under pytest.
