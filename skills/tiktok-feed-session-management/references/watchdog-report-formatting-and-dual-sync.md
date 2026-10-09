# feed_session_watchdog: Report Formatting, Test Coverage & Dual-Location Sync

## 1. Dual-Location Deployment Sync
`feed_session_watchdog.py` exists in two runtime/deploy environments that must remain strictly synchronized:
- Git Deploy Repo: `D:\Taadaa\Hermes\deploy\hermes-home\scripts\feed_session_watchdog.py`
- Active Runtime: `C:\Users\Kibe\AppData\Local\hermes\scripts\feed_session_watchdog.py`
- Shared Backup: `D:\OneDrive\Taadaa_Sync_Shared\hermes-cron\scripts\feed_session_watchdog.py` (handled by `cron_sync_watchdog.py`)

When performing fixes or refactors:
- Always patch both repo and local runtime simultaneously (or immediately run `cron_sync_watchdog.py`).
- Diff check before and after to ensure zero drift: `diff -u "D:/Taadaa/Hermes/deploy/hermes-home/scripts/feed_session_watchdog.py" "C:/Users/Kibe/AppData/Local/hermes/scripts/feed_session_watchdog.py"`.

## 2. Report Block Formatting Refactor Pitfall
In `feed_session_watchdog.py`, summary metrics are calculated upstream and then formatted into `block_lines`.
- **Pitfall**: When replacing old metric calculations (e.g. removing raw `tot_nat_follows`, `tot_fy_nat_follows` in favor of `calculate_session_natural_follows`), ensure the constructed string (`nat_follow_line`) is placed into `block_lines` instead of leaving old f-string templates referencing deleted variables.
- Because `main()` only runs the block builder when an active session window finishes and meets reporting criteria, stale variable references can stay dormant until the cron fires at session close, causing an unexpected `NameError`.

## 3. Mandatory Unit Test Pattern for Main Block Formatting
In `deploy/hermes-home/scripts/test_feed_session_watchdog.py`:
- Helper unit tests alone do not exercise variable resolution inside `main()`.
- Always include an AST inspection or source check test to guard against deleted variable references:
  ```python
  def test_block_lines_uses_nat_follow_line(self):
      import inspect
      import feed_session_watchdog
      source = inspect.getsource(feed_session_watchdog.main)
      self.assertNotIn("tot_nat_follows", source)
  ```
- Fast verification command (< 30s):
  `python deploy/hermes-home/scripts/test_feed_session_watchdog.py`
- Dry-run import verification:
  `python -c "import feed_session_watchdog; print('OK')"`
