---
title: "Common Farm Alert Error Patterns"
description: "Known error_reason values and their corresponding flow files to patch"
---

# Common Farm Alert Error Patterns

## 1. `unknown TikTok state`
**Root Cause**: Classifier (`safety.py`/`classifier.py`) cannot identify current screen — missing navigation bar, search page, or new popup
**Flow to Patch**: `python_runner/flows/feed_swipe_smoke.py` → `_probe_gemphonefarm_blind_popups` / `classify_screen()`
**Recovery**: Add selector to `benign_popup.py` or extend classifier patterns

## 2. `focus lost / Launcher active`
**Root Cause**: TikTok crashed or was killed by system, returned to home screen
**Flow to Patch**: `python_runner/flows/device_prepare.py` → `prepare_tiktok_for_smoke()` / `safe_wake_unlock_preflight()`
**Recovery**: Add relaunch logic + preflight check before each swipe batch

## 3. `popup not dismissed`
**Root Cause**: New TikTok popup/modal not in benign popup registry
**Flow to Patch**: `python_runner/flows/benign_popup.py` → `BENIGN_POPUPS` registry
**Recovery**: Add new selector pattern to registry

## 4. `swipe recovery stuck`
**Root Cause**: ADB swipe on search/suggestion page just scrolls list, doesn't exit
**Flow to Patch**: `python_runner/flows/feed_swipe_smoke.py` → `_swipe_recovery_on_stuck()`
**Recovery**: Add back-button press or app relaunch instead of swipe

## 5. `login required / session expired`
**Root Cause**: TikTok session cookie expired, needs re-login
**Flow to Patch**: `python_runner/flows/tiktok_login.py` → reconciliation logic
**Recovery**: Trigger login reconcile flow

---

## Mapping: error_reason → Primary Flow File

| error_reason | Primary Flow | Secondary Files |
|-------------|--------------|-----------------|
| unknown TikTok state | feed_swipe_smoke.py | benign_popup.py, safety.py |
| focus lost | device_prepare.py | feed_swipe_smoke.py |
| popup not dismissed | benign_popup.py | feed_swipe_smoke.py |
| swipe recovery stuck | feed_swipe_smoke.py | device_prepare.py |
| login required | tiktok_login.py | tiktok_reconcile.py |

---

## Quick Decision Tree for Agent

```
receive alert
    │
    ├─▶ Step 1: inspect_machine.py <N>
    │       │
    │       └─▶ screenshot shows Launcher/home screen?
    │               │
    │               ├─ YES → Patch device_prepare.py (relaunch logic)
    │               │
    │               └─ NO → screenshot shows TikTok but unknown screen?
    │                       │
    │                       ├─ YES → Patch benign_popup.py / feed_swipe_smoke.py classifier
    │                       │
    │                       └─ NO → screenshot shows popup?
    │                               │
    │                               └─ YES → Add selector to benign_popup.py
    │
    ├─▶ Step 2: Read exact flow file from alert
    ├─▶ Step 3: Read summary.txt log
    ├─▶ Step 4: Apply code patch
    └─▶ Step 5: Run canary test command from alert
```