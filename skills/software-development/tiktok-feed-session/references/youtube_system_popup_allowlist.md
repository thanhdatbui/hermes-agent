# YouTube / System Overlay Popup Allowlist in TikTok Feed Session

## Context & Error Signature
- **Error message:** `popup is not in the shared TikTok allowlist; manual review required; swipe recovery (2 swipes) still stuck`
- **Detected screen:** `manual-needed:popup` or `GENERIC_POPUP_SCREEN`
- **Symptom:** During feed swipe sessions, external app dialogs (such as YouTube background prompt: *"Tự động tải video về qua Wi-Fi để xem ngoại tuyến?"* / *"Download videos automatically over Wi-Fi"*) appear over the screen. Because the dialog package (`com.google.android.youtube`) or copy is not in the TikTok benign allowlist, the generic popup dismisser refuses to dismiss it, triggering fallback swipe recovery, which fails and stops the session.

## Architecture & Code Seams
1. **Runner Seam:**
   - `python_runner/flows/feed_swipe_smoke.py`:
     - Calls `dismiss_allowed_generic_popup(ctx, ...)` from `flows.benign_popup`.
     - In `_popup_type_from_dismiss`, checks if `dismiss.reason` contains `"not in the shared TikTok allowlist"` or `"not in the benign allowlist"`.
2. **Handler Seam:**
   - `python_runner/flows/benign_popup.py` & `automation_core.tiktok.benign_popup`:
     - Contains specific detectors and dismiss handlers for benign popups.
     - Maps detected popup type to action (e.g. `allowlist_dismiss`).

## Fix Pattern
1. In `python_runner/flows/benign_popup.py` (and `automation_core.tiktok.benign_popup` if shared across repos):
   - Add detector function `detect_youtube_offline_download_popup(root)`:
     - Match text markers:
       - `"Tự động tải video về qua Wi-Fi để xem ngoại tuyến?"`
       - `"Tự động tải video về qua Wi-Fi"`
       - `"Tự động tải video về"`
       - `"Download videos automatically over Wi-Fi"`
     - Match action button: `"OK"`, `"Hủy"`, `"Cancel"`, `"Đóng"`.
     - Return `BenignPopupMatch("youtube_offline_download_prompt", markers, action_element)`.
   - Register in benign popup detectors list and allowlist dismissers.
2. In `dismiss_allowed_generic_popup`:
   - Ensure the new popup type is recognized and dismissed via tap on the action button, returning `dismiss.dismissed = True`.

## Search & Navigation Pitfall
- **DO NOT** run recursive `grep -rn` or wide search across `D:/Taadaa/tiktok-luot nuoi acc` or `automation-core`. On Windows MSYS2 / large directories, this will time out after 900 seconds.
- Inspect directly in known handler files:
  - `D:/Taadaa/tiktok-luot nuoi acc/python_runner/flows/benign_popup.py`
  - `D:/Taadaa/tiktok-luot nuoi acc/python_runner/core/benign_popup.py`
  - `D:/Taadaa/automation-core/src/automation_core/tiktok/benign_popup.py`
- **ADB Path:** `adb` is not in default MSYS/Git-Bash `PATH`. Always use absolute path:
  `"C:\Program Files (x86)\xiaowei\tools\adb.exe"`
- **ADB Timeout:** Do not run unbounded `uiautomator dump` if the device is busy. Check focus first via:
  `dumpsys window windows | grep -E 'mCurrentFocus|mFocusedApp'`

