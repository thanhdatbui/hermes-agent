# uiautomator "UiAutomationService already registered" Device Failure Pattern (2026-08-12)

## Symptoms
- `uiautomator dump` → `Killed` / exit 136 immediately
- `logcat` shows: `java.lang.IllegalStateException: UiAutomationService already registered!`
- `ps -A | grep uiautomator` shows `com.github.uiautomator` process alive
- Force-stop + atx kill + `uiautomator quit` NOT sufficient
- Must kill the uiautomator process PID directly: `kill -9 <pid>`

## Root Cause
`com.github.uiautomator` app (u0_a184) holds `UiAutomationService` handle. Standard force-stop doesn't release it on some devices. Shell `uiautomator dump` tries to register a second service → `already registered` exception.

## Recovery (live-proven máy 38)
```bash
# 1. Full ATX cleanup
adb shell "pkill -9 -f atx-agent; am force-stop com.github.uiautomator; am force-stop com.github.uiautomator.test; uiautomator quit"

# 2. Find and kill uiautomator PID directly
pid=$(adb shell "ps -A | grep com.github.uiautomator | awk '{print \$2}'")
adb shell "kill -9 $pid; am force-stop com.github.uiautomator"

# 3. Verify
adb shell "uiautomator dump /sdcard/test.xml >/dev/null 2>&1; [ -f /sdcard/test.xml ] && echo OK || echo FAIL"
```

## Decision Rule
**If machine requires PID-level kill to dump → device is unreliable. Remove from farm rotation.**
- Máy 38: recovered once but unstable → exclude
- Máy 54: same pattern → exclude
- Do NOT waste regression cycles on hardware with stuck UiAutomationService

## Evidence
- Máy 38: `SHELL_DUMP_OK size=21349` only after `kill -9 17204` (uiautomator PID)
- Máy 54: `DUMP_OK size=21744` after standard ATX kill (no PID kill needed — less severe)
- Both machines had identical Samsung SM-G930F hardware but different failure severity

## Tracking Workbook Staleness — Pre-existing Account Detection Gap
4 hotmail machines (38, 54, 57, 66) ALL had pre-existing TikTok accounts:
- Detector reported "clean" targets because `taikhoan_dat_v2_updated .xlsx` missing rows
- Script detected at runtime: `email DA CO tai khoan` → `FINAL_BLOCKED OTP_REJECTED_NO_FRESH_CODE`
- **Fix:** Before batch, cross-check detector targets against workbook rows with non-empty Tik ID (col C). Auto-flag machines where detector says "clean" but workbook has TikTok ID.
- Pre-batch validation script: `scripts/validate_clean_targets.py` (to create)