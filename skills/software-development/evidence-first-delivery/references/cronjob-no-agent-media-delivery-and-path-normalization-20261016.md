# Cronjob `no_agent=True` Native MEDIA Delivery and POSIX Path Normalization

**Date:** 2026-10-16  
**Context:** Cronjob `tiktok-rolling-rename-watchdog` ran on schedule with `no_agent=True` and delivered stdout to Telegram.  
**Symptom:** User received text:
```
✅ [ROLLING RENAME] Máy 48: @inhkhanhngan1295 -> 'Thu Toàn' | Ảnh: D:\Taadaa\reports\m48_inhkhanhngan1295_rename_confirmed.png
```
User immediately asked: *"Ảnh đâu"* and *"Vụ media t nhớ fix r mà vẫn bị à hay t nhớ sai"*.

## Root Cause Analysis

1. **Bare Text Prefix vs Protocol Tag:**
   - In `no_agent=True` mode, Hermes captures stdout verbatim and forwards it to the Telegram platform adapter.
   - The Telegram platform adapter (`extract_media`) scans ONLY for the exact protocol token `MEDIA:<path>` on its own line.
   - Printing `| Ảnh: D:\...` or `Ảnh: <path>` is treated as plain text prose, not an attachment directive. Telegram renders it as plain text without uploading any photo.

2. **Windows Backslash Path Corruption:**
   - Windows file paths natively produce backslashes `\` (`D:\Taadaa\reports\...`).
   - Even if prefixed with `MEDIA:`, un-normalized Windows backslashes get mangled during string parsing or regex tokenization (e.g., `\r` treated as carriage return, `\t` treated as tab, `\a` treated as bell).
   - This causes Telegram media lookup to fail silently on the local filesystem and drop the image delivery.

3. **User Friction:**
   - The user previously fixed/hardened the media parser in the Telegram gateway and rightfully expects all completion reports claiming to have an image to deliver native photos automatically.
   - Printing text paths forces the user to ask "Ảnh đâu" and breaks trust.

## Mechanical Fix Pattern

In every Python script executed by cron (`no_agent=True`) or watchdog daemons that report visual evidence:

```python
# 1. Normalize path to POSIX forward slashes
p_posix = str(proof_png).replace("\\", "/")

# 2. Output on a separate line with MEDIA: protocol tag
print(f"✅ [TASK_NAME] Máy {machine:02d}: @{username} -> '{new_name}'\nMEDIA:{p_posix}", flush=True)
```

## Mandatory Verification Checklist

1. **Protocol Token:** Check that `MEDIA:` is the exact prefix, followed immediately by the path (no spaces after `MEDIA:`).
2. **Path Normalization:** Assert `\` is replaced by `/` before printing.
3. **Dedicated Line:** Ensure `MEDIA:<path>` is on its own line (not in-line with status text or behind a pipe `|`).
4. **Synchronization:** Sync the updated script across all tiers (local tools, %LOCALAPPDATA%\hermes\scripts, and OneDrive/Admin-PC).
