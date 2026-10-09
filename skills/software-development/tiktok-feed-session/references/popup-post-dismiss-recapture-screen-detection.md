# Popup Post-Dismiss Recapture Screen Detection & BACK Recovery Loop

## Context & Problem
During benign popup dismissal in TikTok feed automation (e.g. `dismiss_add_phone_popup` in `python_runner/flows/benign_popup.py`):
When the popup close button (e.g. Close X) is tapped, the runner recaptures the screen via `capture_calibration_attempt` to verify that the app returned to a valid TikTok screen (e.g. `for-you`, `profile`, `home`).

On real Android farm devices (especially over remote ADB hosts or weak devices like Samsung Galaxy S7), post-dismiss capture can experience transient ADB transport timeouts (e.g. `exec-out screencap -p` timeout after 600s, `ATX_SESSION_UNAVAILABLE`).
When capture fails to produce a screenshot or XML dump, `capture_calibration_attempt` returns a dictionary where `detected_screen` is `None` (missing/unclassified).

## Pitfall 1: False Negative on Pre-Loop Recovery Condition
Code historically checked:
```python
# BUGGY:
if after.get("detected_screen") == "unknown":
    for back_i in range(1, 4):
        ...
```
When `after.get("detected_screen")` was `None`:
- `None == "unknown"` evaluates to `False`.
- The entire BACK recovery loop (1 to 3 BACK keyevents) was completely skipped.
- The flow fell through directly to the post-dismiss blocker assertion:
  ```python
  if consumer_match and not _is_known_tiktok_screen_after_add_phone(ctx, after):
      return PopupDismissResult(
          dismissed=False,
          reason=(
              "Add phone close recapture did not verify a known TikTok screen "
              f"with TikTok focus: {_attempt_detected_screen(after) or 'unknown'}"
          ),
          ...
      )
  ```
- Result: The session terminated with `manual-needed` and failed the entire machine run, even though pressing BACK 1-2 times would have easily dismissed the keyboard/overlay.

## Pitfall 2: Premature Break Inside the BACK Recovery Loop
Inside the BACK recovery loop:
```python
# BUGGY:
screen = recovered.get("detected_screen")
if screen in _KNOWN_TIKTOK_SCREENS_AFTER_ADD_PHONE:
    after = recovered
    break
if screen != "unknown":
    break
```
When `recovered.get("detected_screen")` is `None`:
- `None != "unknown"` evaluates to `True`.
- The loop broke on `back_i = 1`, aborting the recovery attempt immediately instead of exhausting the planned 3 attempts.

## Canonical Pattern & Fix
Always use `_attempt_detected_screen(...)` to handle `None`, empty string, and `"unknown"` consistently:

1. **Pre-loop condition**:
```python
if after is not None and _attempt_detected_screen(after) in ("", "unknown"):
    for back_i in range(1, 4):
        ensure_run_plan_deadline(ctx.config, f"Add phone post-dismiss BACK {back_i}")
        back = ctx.adb.shell(["input", "keyevent", "BACK"], timeout=ctx.timeout("adb_seconds", 15))
        if not back.ok:
            break
        time.sleep(0.5)
        recovered = capture_calibration_attempt(...)
        rec_screen = _attempt_detected_screen(recovered)
        if rec_screen in _KNOWN_TIKTOK_SCREENS_AFTER_ADD_PHONE:
            after = recovered
            break
        # Only break if a definite known non-empty, non-unknown screen was reached
        if rec_screen and rec_screen != "unknown":
            break
```

2. **Downstream Alert Isolation**:
Ensure batch aggregators do not match `"recapture did not verify"` as a challenge/captcha failure. See `automation-core-development` reference `references/batch-aggregator-session-lost-vs-challenge.md`.
