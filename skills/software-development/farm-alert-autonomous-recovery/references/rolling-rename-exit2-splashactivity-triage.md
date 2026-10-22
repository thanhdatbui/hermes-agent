# Rolling Rename Watchdog — exit_2 / SplashActivity Stuck Triage

**Context:** `tiktok-rolling-rename-watchdog` cron fires alerts of the form:
```
⚠️ [ROLLING RENAME FAILED] May <N>: @<handle> reason=exit_2
```

## exit_2 Semantics

`exit_2` from the canonical rename runner (`do_rename_canonical_runner.py`) means:

> **Profile screen was not detected within the runner's timeout.**

The runner waited for the TikTok Profile page (with "Sửa hồ sơ" / edit-profile buttons) but never saw it. The script exits cleanly with code 2 to signal "could not proceed — device not in expected state", NOT a code crash.

## Root Cause: App Stuck at SplashActivity

Most common cause (confirmed 2026-10-22, Máy 64 + 69):

```
mCurrentFocus=Window{...} com.ss.android.ugc.trill/com.ss.android.ugc.aweme.splash.SplashActivity
```

- App is frozen at startup splash screen — cannot load main UI
- Rename runner opens Profile → never arrives → times out → exit_2

**Inspect command for quick triage:**
```bash
python D:/Taadaa/tools/inspect_machine.py <N>
```
Check the `Current Focus` line. If it shows `SplashActivity`, the issue is TRANSIENT device state.

## Device-Specific Risk

**SM-G930F / SM-G930S (Galaxy S7)** — elevated risk of SplashActivity freeze when:
- Proxy or network is slow/blocked (app can't load feed on startup)
- App crashed mid-session and wasn't restarted by watchdog
- Device woke from deep sleep and TikTok resumed into a broken state

## Classification: TRANSIENT — NOT a code bug

- **Unit tests:** All 39 rename runner tests pass when `exit_2` fires on these devices
- **Cron continues:** Other machines succeed normally (111 candidates, only 2 failed)
- Treat `exit_2` failures as TRANSIENT if:
  - `inspect_machine.py` shows SplashActivity as current focus
  - Other machines are succeeding in the same cron run
  - No code changes were deployed recently

## Recommended Response

1. Run `inspect_machine.py <N>` — confirm SplashActivity in focus
2. If SplashActivity confirmed → classify TRANSIENT, no code change needed
3. Cron will retry on next scheduled run automatically
4. If failure persists across 3+ consecutive cron runs on the same machine → investigate proxy liveness or restart ADB/app via `adb shell am force-stop com.ss.android.ugc.trill`

## DO NOT

- Do NOT patch rename runner code for exit_2 when SplashActivity is the cause
- Do NOT dispatch a Worker to "fix" exit_2 without first running `inspect_machine.py`
- Do NOT assume code regression — run focused tests first (`pytest tests/test_do_rename_canonical_runner.py -v`)

## Verification Baseline (2026-10-22)

```
39 passed in 3.19s — test_do_rename_canonical_runner.py
```
Code is correct. SplashActivity = device issue, not logic bug.
