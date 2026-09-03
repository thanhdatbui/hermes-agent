# Cohort Target Identity Binding: Optional "tik" Field & Stale Lock Triage (2026-08-28)

## 1. Context & Root Cause
In `python_runner/flows/multi_machine_feed_session.py`, `_apply_cohort_identity(child_config, account)` enforces strict validation between on-device / workbook target identity and the frozen `CohortPlan` artifact loaded from `_cohort_artifact` and `_assignment_manifest`.

### The "missing:tik" validation trap:
- Cohort manifests generated for feed-only rows (e.g. Ca 2 Row 4) only specify `feed` targets (`account`, `serial`, `machine`, `account_row`), and omit the `"tik"` workbook identifier key in `entries_by_machine[m]`.
- An overly strict validation check:
  ```python
  # WRONG: Hard fail if "tik" key is absent from cohort manifest
  if "tik" not in expected:
      mismatches.append("missing:tik")
  ```
  caused **all machines in the cohort** (e.g. all 34 machines in Row 4) to abort immediately during the cohort-binding gate with:
  `[cohort-identity] machine X cohort target mismatch: cohort target identity mismatch: missing:tik`.

### The Cascade of Stale Failed-Reservation Device Locks:
- When a worker encounters `cohort-target-mismatch` before running or while reserving device locks, fallback artifact generation writes `summary.txt` and can leave `machine_<n>.lock.json` and `serial_<serial>.lock.json` in `~/.codex/device-locks/` in `status: blocked`.
- Because normal scheduling preserves `status: blocked` locks (TTL 2h), subsequent cron ticks see all devices as locked (`skipped-device-locked`) and skip the entire batch, causing silent starvation where no accounts run.

---

## 2. Correct Validation Rule
`"tik"` workbook mapping is optional in generic feed cohorts. It should only be checked if explicitly present in the cohort plan:
```python
# CORRECT: Only validate "tik" when the cohort plan specifies it
if "tik" in expected:
    val = expected.get("tik")
    if type(val) is bool or not isinstance(val, (int, str)) or not str(val).strip() or str(val) != str(account.tik):
        mismatches.append("tik")
```

---

## 3. Incident Triage & Recovery Checklist
1. **Detect Cohort Mismatch in Runtime Artifacts:**
   Inspect `D:\Taadaa\runtime\<host>\live\<day>\row-<r>-<time>\machines\machine_*\summary.txt`.
   Look for: `final_status: failed` with `reason: cohort target identity mismatch: ...`.
2. **Fix Code & Run Cohort Tests:**
   Run `pytest python_runner/tests/ -k cohort` to verify all cohort integration & unit tests pass.
3. **Clear Stale Failed-Reservation Locks:**
   Scan `~/.codex/device-locks/` for locks created during the failed run timestamp and remove them so the scheduler / runner does not skip devices on subsequent ticks:
   ```python
   import os, glob
   lock_dir = r'C:\Users\Kibe\.codex\device-locks'
   for f in glob.glob(os.path.join(lock_dir, '*.lock.json')):
       content = open(f, encoding='utf-8').read()
       if '<failed_timestamp_substring>' in content:
           os.remove(f)
   ```
4. **Sync Deployed Script:**
   Always sync updated runner scripts from `scripts/hermes_cron/tiktok_runner.py` to `%LOCALAPPDATA%\hermes\scripts\tiktok_runner.py`.
