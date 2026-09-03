---
title: "Farm Alert Processing SOP"
description: "Standard Operating Procedure for handling Farm Alert messages"
---

# Farm Alert Processing SOP (2026-09-03)

## 5-Step Deterministic Flow

When receiving a Farm Alert message, execute these steps **in order**:

### Step 1: Inspect Machine (MANDATORY FIRST ACTION)
```bash
python D:/Taadaa/tools/inspect_machine.py <machine_number>
```
- Captures live screenshot, UI hierarchy, focused app, serial
- **DO NOT** grep, search, or read any other files first

### Step 2: Read Flow File
```python
read_file("D:/Taadaa/tiktok-luot nuoi acc/python_runner/flows/feed_swipe_smoke.py")
```
- Exact path provided in alert payload
- Look for the specific failure point (popup handler, swipe logic, focus check)

### Step 3: Read Run Log
```python
read_file("D:/Taadaa/tiktok-luot nuoi acc/.ai-runs/latest/summary.txt")
```
- Exact path provided in alert payload
- Check last error, step, machine state

### Step 4: Apply Fix / Patch (if needed)
- If UI popup not handled → add selector to `benign_popup.py` or flow
- If focus lost → add preflight check / relaunch logic
- **Must fix at code level** so all 80-160 machines benefit

### Step 5: Canary Verification
```powershell
powershell.exe -ExecutionPolicy Bypass -File "D:\Taadaa\tiktok-luot nuoi acc\scripts\run-feed-session.ps1" -Machines <N> -Row 1 -RecoveryTestSwipes 2 -SkipAccountWorkbookSync -Run
```
- Runs 2 test swipes on the exact machine
- Confirms fix works in production environment

### Step 6: Report Result
Format: `MÁY <N> | <Account> | <Success/Fail> | <Error Code if Fail> | <Action Taken>`

---

## Critical Rules (VIOLATION = SESSION TERMINATION)
1. ❌ NO `grep -r`, `find`, `search_files` broad scan
2. ❌ NO ADB manual taps as "fix" — must patch code
3. ❌ NO skipping Step 1 inspect_machine.py
4. ❌ NO fabricating output — report real execution results only

---

## Alert Payload Format
See `references/alert_format.md` for the complete template with all 4 actionable commands embedded.