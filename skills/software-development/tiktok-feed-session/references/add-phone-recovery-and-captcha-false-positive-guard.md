# Add Phone Recovery & Captcha False Positive Guard

## Context & Problem
During large-scale TikTok feed sessions (e.g., Farm Admin 80-device fleet), a transient transport glitch or ADB timeout after closing the "Add Phone" (Thêm số điện thoại) popup can trigger a false positive systemic alert:
`⚠️ [CẢNH BÁO XÁC MINH / CAPTCHA TẠM THỜI]: Phát hiện 1 máy gặp captcha/xác minh (chưa mất phiên):`
`   • Máy M233: Add phone close recapture did not verify a known TikTok screen with TikTok focus: unknown`

This alert was caused by two compounding bugs across two separate repositories: `tiktok-luot nuoi acc` and `automation-core`.

---

## 1. Flow Seam Bug: `benign_popup.py` (`tiktok-luot nuoi acc`)

### Symptoms
When closing the Add Phone popup via Close X (`dismiss_close_x`), the runner executes `_sleep_and_recapture`. If ADB screencap or UIAutomator dump encounters a transport timeout, `capture_calibration_attempt` returns a dictionary where `detected_screen` is `None` (not set).

### Root Causes
1. **Missed Recovery Loop Trigger:**
   The code checked:
   ```python
   if after.get("detected_screen") == "unknown":
       for back_i in range(1, 4): ...
   ```
   When `detected_screen` is `None`, `None == "unknown"` evaluates to `False`. The entire 3-step BACK recovery loop was skipped, immediately falling through to fail-closed with `"Add phone close recapture did not verify a known TikTok screen with TikTok focus: unknown"`.
2. **Premature Loop Exit:**
   Inside the recovery loop:
   ```python
   if screen != "unknown":
       break
   ```
   If `screen` remained `None` on the first retry, `None != "unknown"` evaluated to `True`, prematurely aborting the loop after a single attempt instead of trying all 3 BACK attempts.

### Canonical Fix
Use `_attempt_detected_screen`:
```python
if _attempt_detected_screen(after) in ("", "unknown"):
    for back_i in range(1, 4):
        ...
        screen = _attempt_detected_screen(recovered)
        if screen in _KNOWN_TIKTOK_SCREENS_AFTER_ADD_PHONE:
            after = recovered
            break
        if screen and screen != "unknown":
            break
```

---

## 2. Aggregator False Positive: `batch_aggregator.py` (`automation-core`)

### Symptoms
The batch aggregator flagged the run as having a `challenge_failure` (captcha/verification), triggering an automated high-priority alert even when systemic clusters were 0 and the overall failure rate was below the 20% threshold.

### Root Cause
`CHALLENGE_KEYWORDS` included bare `"verify"`:
```python
CHALLENGE_KEYWORDS = ("verification", "manual_challenge", "checkpoint", "captcha", "verify")
```
Any assertion or error message containing the English verb "verify" (e.g., `"recapture did not verify"`, `"failed to verify"`, `"could not verify"`) was classified as a captcha/challenge failure.

### Canonical Fix
1. Remove bare `"verify"` from `CHALLENGE_KEYWORDS`, replacing it with explicit Vietnamese terms: `"xác minh"`, `"xac minh"`.
2. Introduce `CHALLENGE_EXCLUSIONS`:
   ```python
   CHALLENGE_EXCLUSIONS: tuple[str, ...] = (
       "did not verify",
       "failed to verify",
       "could not verify",
       "cannot verify",
       "unable to verify",
       "recapture did not verify",
   )
   ```
3. Exclude non-challenge assertions before categorizing:
   ```python
   challenge_failures = [
       m for m in failed
       if not any(ex in (m.error_message or "").lower() for ex in CHALLENGE_EXCLUSIONS)
       and (
           any(kw in (m.error_message or "").lower() for kw in CHALLENGE_KEYWORDS)
           ...
       )
   ]
   ```

---

## Verification
- **automation-core:** `pytest tests/test_batch_aggregator.py -k test_recapture_did_not_verify`
- **tiktok-luot nuoi acc:** `python -m py_compile python_runner/flows/benign_popup.py`
