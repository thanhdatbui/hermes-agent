---
title: "Farm Alert Actionable Format Template"
description: "Standardized alert payload format for Farm Alerts channel to eliminate grep reflex"
---

# Farm Alert Actionable Format (Applied 2026-09-03)

## New Format Template
When a machine stops session, the watchdog/bot sends this exact payload:

```text
🚨 [FARM ALERT: MÁY {machine}] DỪNG PHIÊN
• Máy: {machine} | Serial: {serial or 'N/A'} | Nick: {account}
• Triệu chứng: {error_reason}

📋 BẮT BUỘC THỰC THI (KHÔNG GREP / KHÔNG TÌM KIẾM):
1. Lệnh lấy hiện trường: python D:/Taadaa/tools/inspect_machine.py {machine}
2. File flow phụ trách: D:/Taadaa/tiktok-luot nuoi acc/python_runner/flows/feed_swipe_smoke.py
3. File log run: D:/Taadaa/tiktok-luot nuoi acc/.ai-runs/latest/summary.txt
4. Lệnh canary test lại máy {machine}:
powershell.exe -ExecutionPolicy Bypass -File "D:\Taadaa\tiktok-luot nuoi acc\scripts\run-feed-session.ps1" -Machines {machine} -Row 1 -RecoveryTestSwipes 2 -SkipAccountWorkbookSync -Run
```

## Why This Works
- **Agent gets exact commands**: No ambiguity about what to run first
- **Agent gets exact file paths**: No need to search for flow file or log file
- **Eliminates grep reflex**: The "unknown TikTok state" string no longer triggers search — the alert says "run inspect_machine.py"
- **Deterministic 5-step flow**: Inspect → Evaluate → Patch → Canary → Report

## Source Code Location
Template generated from `automation_core/src/automation_core/alerts.py` function `send_farm_alert()` (lines 267-281).

## Verification Checklist
When receiving this alert, Agent MUST:
1. ✅ Run step 1 command exactly as written
2. ✅ Read step 2 file via `read_file`
3. ✅ Read step 3 file via `read_file`
4. ✅ Execute step 4 canary command
5. ✅ Report final result (Success/Fail + error code)