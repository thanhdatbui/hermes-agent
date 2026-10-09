# S7 SystemUI Occlusion & CRLF Capture Pitfall (Quick Reference)

- **SystemUI GlobalActions (Power menu):** `adb shell am broadcast -a android.intent.action.CLOSE_SYSTEM_DIALOGS`
- **Git Bash / MSYS screencap:** Always use `adb shell screencap -p /sdcard/s.png && adb pull /sdcard/s.png` to avoid binary CRLF corruption.
