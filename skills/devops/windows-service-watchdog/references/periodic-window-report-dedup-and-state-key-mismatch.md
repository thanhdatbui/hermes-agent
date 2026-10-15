# Periodic Window Report De-duplication & State Key Mismatch

## Context & Symptom
User complaint: *"Clg report này gửi liên tục spam v t đã ép 6h 1 lần r mà"*
When a scheduled watchdog or reporting script is configured to report periodically (e.g. every 6 hours: 00:00, 06:00, 12:00, 18:00) while its underlying cronjob runs at high frequency (e.g. `*/5 * * * *` or `*/15 * * * *`), users frequently experience alert spam: 2 to 6 identical reports arrive within a 30-minute span.

---

## Root Cause Patterns

### 1. Window Predicate Wider than Cron Interval without De-duplication
A common implementation checks:
```python
is_6h_window = (now.hour in (0, 6, 12, 18) and now.minute < 30)
if is_6h_window:
    print(report)
```
With a cron interval of `*/5` or `*/15`:
- At minute 00: cron fires -> `is_6h_window` is True -> report sent.
- At minute 05 / 15: cron fires -> `is_6h_window` is STILL True -> report sent again!
- Across the 30-minute window, the script prints 2 to 6 times. For `no_agent: true` cronjobs or Telegram Bot API alerts, every non-empty output becomes a user notification.

### 2. State Key Mismatch (Dead Branch Guard)
When a de-duplication check is added:
```python
slot_6h = (now.hour // 6) * 6
sess_key = f"{today_str}_{slot_6h:02d}"

if state.get("last_reported_6h") == sess_key:
    return  # Already reported
```
If the code that saves state later writes to a legacy or different key:
```python
state["last_reported_session"] = sess_key
state["last_reported_date"] = sess_key
# ❌ Missing: state["last_reported_6h"] = sess_key
save_state(state)
```
Then `state.get("last_reported_6h")` remains `None` on every subsequent tick. The guard never triggers, resulting in repeated alerts on every tick throughout the window.

---

## Canonical De-duplication Pattern

```python
from datetime import datetime
from zoneinfo import ZoneInfo

HCMC = ZoneInfo("Asia/Ho_Chi_Minh")

def is_6h_window(now_dt: datetime) -> bool:
    return (now_dt.hour in (0, 6, 12, 18) and now_dt.minute < 30)

def should_emit_6h_report(state: dict, now_dt: datetime, force: bool = False) -> tuple[bool, str]:
    if force:
        return True, ""
    
    if not is_6h_window(now_dt):
        return False, ""
    
    today_str = now_dt.strftime("%Y-%m-%d")
    slot_6h = (now_dt.hour // 6) * 6
    sess_key = f"{today_str}_{slot_6h:02d}"
    
    # Check both canonical and legacy keys for robust backward-compatibility
    if (
        state.get("last_reported_6h") == sess_key
        or state.get("last_reported_session") == sess_key
        or state.get("last_reported_date") == sess_key
    ):
        return False, sess_key
    
    return True, sess_key

def mark_6h_report_emitted(state: dict, sess_key: str, all_done: bool = False) -> None:
    if all_done:
        state["last_reported_all_done"] = True
    state["last_reported_6h"] = sess_key
    state["last_reported_session"] = sess_key
    state["last_reported_date"] = sess_key
```

---

## Unit Testing Requirement

Every periodic report script MUST include an idempotency/anti-duplicate unit test verifying that consecutive calls within the report window emit exactly 1 notification:

```python
def test_report_final_summary_idempotency_anti_duplicate():
    state = {}
    now_dt = datetime(2026, 10, 15, 18, 5, tzinfo=HCMC)
    with patch("script.send_farm_alert") as mock_alert, \
         patch("script.now_hcmc", return_value=now_dt):
        # Call 1: First tick in 18:00 window -> alert emitted
        report_final_summary(state, all_done=False)
        assert mock_alert.call_count == 1
        
        # Call 2: Second tick (e.g. 18:10) -> alert blocked by dedup key
        report_final_summary(state, all_done=False)
        assert mock_alert.call_count == 1  # Still 1!
```
