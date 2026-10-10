# Batch Watchdog Idempotency & Partial Failure Loop Prevention

## 1. Context & Problem Statement
In scheduled cron watchdogs that supervise multi-stage batch automation (e.g. `post-noon-chain-watchdog` running `Reg Gmail -> Add 2FA TikTok` across a phone fleet), execution is often scheduled recurringly across an operational time window (e.g. `*/5 14,15,16,17,18 * * *`, checking every 5 minutes between 14:30 and 18:30).

A critical bug arises when the watchdog's idempotency check (`already_ran_today()`) is strictly coupled to 100% success of the underlying scripts:

```python
# ANTI-PATTERN: Strict success required for daily lockout
def already_ran_today(today_str: str) -> bool:
    data = load_state()
    return data.get("last_success_date") == today_str and data.get("details", {}).get("lane_status") == "success"

def save_state(today_str: str, details: dict):
    is_success = details.get("lane_status") == "success"
    # If lane_status is "failed", last_success_date is NOT updated to today!
    new_success = today_str if is_success else existing_success
    ...
```

## 2. Failure Mechanism
1. **Normal Platform Error Rate:** In batch automation (registering accounts, solving SMS, adding 2FA across 80+ devices), individual target errors are expected (e.g., `phone_verify`, `account_creation_error`, device lock conflicts).
2. **Non-Zero Exit Code:** The runner script (PowerShell `run_all.ps1` or Python runner) returns exit code `1` because some devices/accounts failed.
3. **State Lockout Bypassed:** Because exit code is `1`, `lane_status` is marked as `"failed"`. `last_success_date` remains pointing to a previous day (or unset).
4. **Immediate Re-Trigger:** As soon as the first run completes (e.g. 61 minutes, 15:25 -> 16:26), the cron scheduler fires on the next 5-minute tick (16:30).
5. **Infinite Batch Loop:** `already_ran_today()` evaluates to `False`. The watchdog triggers Run 2 (16:30 -> 17:27). Run 2 ends with code `1`, still not updating `last_success_date`. The watchdog immediately triggers Run 3 (17:30 -> ...).
6. **User Impact:** Heavy resource exhaustion on the farm, device contention, and duplicate full-page reports delivered to Telegram ("sao lại báo thành 2 lần v, chạy 2 lần à").

## 3. Best Practices & Solution Pattern

### Principle: Execution Attempt vs. Item-Level Outcome
A daily batch watchdog must distinguish between:
- **Did the batch execute its scheduled shift/turn today?** (Execution Attempt)
- **Did all items in the batch succeed?** (Telemetry / Item-Level Outcome)

### Recommended Implementation

```python
STATE_FILE = Path("D:/Taadaa/runtime/kibe/cron-state/batch_chain_state.json")
MAX_DAILY_RUNS = 1  # Or bounded retry count, e.g., 2

def already_ran_today(today_str: str) -> bool:
    if not STATE_FILE.is_file():
        return False
    try:
        data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        # Check completion date, NOT success of all items
        if data.get("last_completed_date") == today_str:
            run_count = data.get("daily_run_count", 1)
            if run_count >= MAX_DAILY_RUNS:
                return True
        return False
    except Exception:
        return False

def save_state(today_str: str, details: dict) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    existing_count = 0
    if STATE_FILE.is_file():
        try:
            old = json.loads(STATE_FILE.read_text(encoding="utf-8"))
            if old.get("last_completed_date") == today_str:
                existing_count = old.get("daily_run_count", 0)
        except Exception:
            pass

    payload = {
        "last_completed_date": today_str,
        "daily_run_count": existing_count + 1,
        "last_run_at": datetime.now(HCMC).isoformat(),
        "details": details,  # Stores g_code, metrics, etc.
    }
    tmp = STATE_FILE.parent / f".batch_state.{os.getpid()}.tmp"
    tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    os.replace(str(tmp), str(STATE_FILE))
```

### Key Invariants
1. **Unconditional Completion Lockout:** Once a multi-phase batch runs its full course and emits a final report, it MUST mark `last_completed_date = today_str` regardless of child exit codes.
2. **Explicit Bounded Retries:** If partial failures must be retried, use an explicit `daily_run_count < MAX_RETRIES` counter with an enforced cooldown interval (e.g., minimum 2 hours), NEVER an unconstrained loop on every cron tick.
3. **Atomic File Locking:** Continue using atomic `.tmp` + `os.replace()` to prevent race conditions during state writes.
