---
title: "Farm Alert Actionable Format Template"
description: "Standardized alert payload format for Farm Alerts channel to eliminate grep reflex"
---

# Farm Alert Actionable Format (Applied 2026-09-03)

## New Format Template
When a machine stops session, the watchdog/bot sends this exact payload:

```text
🚨 [FARM ALERT: MÁY {machine}] DỪNG PHIÊN
• Quy trình / Script: {process_name} ({repo_name})
• Máy: {machine} | Serial: {serial or 'N/A'} | Nick: {account}
• Triệu chứng: {error_reason}
• Hiện trường: ĐANG MỞ

📋 BẮT BUỘC THỰC THI (5 BƯỚC RECOVERY - CẤM ADB TAY / CẤM QUÉT ĐĨA):
1. B1 (Inspect): python D:/Taadaa/tools/inspect_machine.py {machine}
2. B2 (Root Cause): Đọc log run (D:/Taadaa/tiktok-luot nuoi acc/.ai-runs/latest/summary.txt) & mở flow (D:/Taadaa/tiktok-luot nuoi acc/python_runner/flows/feed_swipe_smoke.py)
3. B3 (Patch Code): SỬA CODEBASE trong repo để script tự xử lý lỗi (CẤM gõ lệnh ADB ngoài chữa ngọn)
4. B4 (Canary Test): Chạy lệnh kiểm chứng thực tế:
   powershell.exe -ExecutionPolicy Bypass -File "D:\Taadaa\tiktok-luot nuoi acc\scripts
un-feed-session.ps1" -Machines {machine} -Row 1 -RecoveryTestSwipes 2 -SkipAccountWorkbookSync -Run
5. B5 (Closeout): Báo cáo diff code + kết quả canary
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