---
title: "Automation Core Alerts Module - send_farm_alert()"
description: "Reference for the send_farm_alert function that generates Actionable Alerts"
---

# automation_core.alerts.send_farm_alert() Reference

## Function Signature
```python
def send_farm_alert(
    machine: int,
    script_name: str,
    account: str,
    error_reason: str,
    serial: str | None = None,
    adb_path: str = "adb",
    chat_id: str = DEFAULT_ALERT_CHAT_ID,
) -> bool:
```

## Location
- **Source**: `D:/Taadaa/automation-core/src/automation_core/alerts.py` (lines 230-307)
- **Built**: `D:/Taadaa/automation-core/build/lib/automation_core/alerts.py`

## Key Change (2026-09-03)
**Replaced old passive alert format with Actionable Alert Format** that embeds:
1. `python D:/Taadaa/tools/inspect_machine.py {machine}`
2. `D:/Taadaa/tiktok-luot nuoi acc/python_runner/flows/feed_swipe_smoke.py`
3. `D:/Taadaa/tiktok-luot nuoi acc/.ai-runs/latest/summary.txt`
4. `powershell.exe -ExecutionPolicy Bypass -File "D:\\Taadaa\\tiktok-luot nuoi acc\\scripts\\run-feed-session.ps1" -Machines {machine} -Row 1 -RecoveryTestSwipes 2 -SkipAccountWorkbookSync -Run`

## Called From
- `feed_session_watchdog.py` (hermes_cron)
- Any watchdog that detects machine stuck state

## Output Format
HTML-formatted Telegram message with `<code>` blocks for exact commands, sent to chat_id `-5373649734` (Farm Alerts group).

## AUTO_RECOVERY_ENABLED
Currently **False** (line 32) — AI auto-recovery agent is intentionally disabled. Alert is for human/Agent action only.