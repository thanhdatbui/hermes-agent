---
title: "TikTok Feed Session - Alert Integration"
description: "How TikTok feed-session integrates with Farm Alert actionable format"
---

# TikTok Feed Session — Farm Alert Integration

## Connection Point
The `multi-machine-feed-session` script (and its watchdog) uses `automation_core.alerts.send_farm_alert()` which now emits the **Actionable Alert Format** (see `taadaa-farm-ops-rules/references/alert_format.md`).

## What This Means for Feed Session Ops

### When Alert Arrives for Feed Session Machine
The alert will contain:
1. **Exact inspect command** for that machine
2. **Exact flow file**: `python_runner/flows/feed_swipe_smoke.py` (primary flow for feed session)
3. **Exact log path**: `.ai-runs/latest/summary.txt`
4. **Exact canary command**: `run-feed-session.ps1 -Machines <N> -Row 1 -RecoveryTestSwipes 2 -SkipAccountWorkbookSync -Run`

### Agent Processing (No Ambiguity)
```
receive alert
    │
    ├─▶ Step 1: python D:/Taadaa/tools/inspect_machine.py <N>
    ├─▶ Step 2: read_file(feed_swipe_smoke.py)
    ├─▶ Step 3: read_file(summary.txt)
    ├─▶ Step 4: patch feed_swipe_smoke.py / benign_popup.py / device_prepare.py
    └─▶ Step 5: run canary command from alert
```

## Common Feed Session Error Patterns
See `taadaa-farm-ops-rules/references/error_patterns.md` for the complete mapping table.

### Top 3 for Feed Session
1. **`unknown TikTok state`** → Patch `feed_swipe_smoke.py` classifier / add to `benign_popup.py`
2. **`focus lost / Launcher active`** → Patch `device_prepare.py` relaunch logic
3. **`popup not dismissed`** → Add selector to `benign_popup.py` registry

## Verification Commands
All verification commands are embedded in the alert payload — no need to remember or look up.