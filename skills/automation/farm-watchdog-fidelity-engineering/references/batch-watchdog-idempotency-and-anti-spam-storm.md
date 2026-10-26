# Batch Watchdog Idempotency & Anti-Spam Storm Engineering

## 1. Problem Statement & Incident Post-Mortem (26/10/2026)
In distributed multi-cluster phone farm automation (160+ devices across Kibe and Admin hosts), cron watchdogs are configured to run periodically (e.g. every 15 minutes) during idle windows (e.g. night window 21:30 - 04:00, or post-noon window 14:30 - 17:30).

### The Failure Mode:
1. A batch watchdog (`cron_night_tiktok_2fa_watchdog.py` or `post_noon_chain_watchdog.py`) executes a 40-device batch across clusters.
2. Real-world physical farm conditions produce normal partial failures (e.g. carrier proxies temporarily dropped, Google `phone_verify` challenge, app update popups).
3. The watchdog concludes with `status = "partial_failure"` and dispatches a structured report to Telegram.
4. **The Flaw:** The idempotency predicate conflated execution completion with 100% success:
   ```python
   # BUGGY CODE:
   def already_ran_today(today_str: str) -> bool:
       state = load_state()
       is_success = state.get("last_2fa_success") is True or state.get("last_success_date") == today_str
       return bool((state.get("last_2fa_date") == today_str or state.get("last_success_date") == today_str) and is_success)
   ```
5. Because `is_success` was `False`, `already_ran_today()` returned `False`.
6. On the next 15-minute cron tick, after the lane lock expired, the scheduler believed the batch had *never run today*.
7. The entire batch was launched again, taking 1-2 hours, followed by another Telegram report, repeating at 00:38, 02:34, 03:23, 10:32, 11:17...
8. **Consequences:**
   - Telegram channels spammed relentlessly with near-identical reports.
   - Farm devices locked in infinite repetitive automation, consuming SIM data and battery.
   - Normal operational shifts (feed sessions, TikTok cache cleanup) blocked due to lock contention.

---

## 2. Architectural Remedy: Decoupled Idempotency Contract

### Rule 1: Completion $\neq$ Zero-Failure
A batch run is a **scheduled event**, not an assertion that every device succeeded. Once the fleet has been traversed for the target date/shift:
```python
def already_ran_today(today_str: str) -> bool:
    state = load_state()
    # Record that the day's batch has executed, stopping unattended loops
    return bool(state.get("last_2fa_date") == today_str or state.get("last_success_date") == today_str)
```
For JSON state files with `last_run_at`:
```python
def already_ran_today(today_str: str) -> bool:
    if not STATE_FILE.is_file():
        return False
    try:
        data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        return data.get("last_run_at", "").startswith(today_str) or data.get("last_success_date") == today_str
    except Exception:
        return False
```

### Rule 2: Explicit Operator Rerun Flag (`--force`)
Unattended cron runs MUST NEVER automatically retry a failed batch on the next tick. Retries are strictly reserved for:
1. Operator explicit command via `--force`.
2. Targeted recovery scripts operating only on the specific failed machines (`inspect_machine.py`, `sol_repair.py`), rather than re-traversing the full 160-device fleet.

### Rule 3: Single Telegram Report Per Shift
Each phase of a multi-phase watchdog (e.g. Phase 1 Reg Gmail, Phase 2 Add 2FA) must dispatch at most **one** summary report to its dedicated Telegram channel per shift, unless triggered with `--force`.
