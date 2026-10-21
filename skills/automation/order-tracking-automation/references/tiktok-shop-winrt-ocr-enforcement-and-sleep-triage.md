# TikTok Shop In-App Order Tracking: WinRT OCR Enforcement & Sleep/Dozing Triage

## 1. WinRT OCR Enforcement vs XML Fallback Ban

- **Invariant:** TikTok Shop and shopping app interfaces render via embedded WebViews, Flutter, or custom layouts. Accessibility nodes often have empty `text` or `content-desc`.
- **Primary Engine:** Windows Native OCR (`Windows.Media.Ocr.OcrEngine` with `vi-VN`/`en-US` via `automation_core.ui_extract` or `automation_core.ocr`). Operates directly on rendered pixels, reliably capturing tracking codes (`SPXVN...`, `JNT...`, `8-30` alphanumerics) and carrier names (`SPX Express`, `J&T`, `Ninja Van`, `Viettel Post`, `GHTK`).
- **Hard Gate Ban:** Calling `dumpWindowHierarchy` or `atx-agent` on port 7912 is BANNED on WebView/Shop contexts (`WebViewXmlFallbackBannedError`). `tools/ui_policy_check.py` rejects scripts containing banned tokens:
  - `uiautomator dump`
  - `dumpWindowHierarchy`
  - `atx-agent`
  - `:7912`
  - `import uiautomator2`
  - `window_dump.xml`
  - `dump_hierarchy`
- All UI extraction must route through canonical `automation_core.ui_extract` or `automation_core.ocr`.

## 2. Sleep / Dozing Screen Triage (False Disconnect Trap)

- **Symptom:** Taking an ADB screencap returns a completely black image (all pixels RGB = 0, extrema `((0, 0), (0, 0), (0, 0))`), and WinRT OCR finds 0 text boxes.
- **Root Cause:** Farm phones (e.g. Galaxy S7) enter sleep / dozing state (`mWakefulness=Dozing` or `Asleep`) during scheduled idle windows to conserve battery and thermal load. In dozing mode, Android shuts off the display framebuffer.
- **Pitfall (Agent Halting / False Report):** The agent sees 0 OCR text or black pixels and falsely assumes the phone is disconnected, USB cable is unplugged, or hardware is broken.
- **Diagnostic Step:** Check power state via:
  ```bash
  python D:/Taadaa/tools/with_device_lock.py --machine <N> -- adb -s <serial> shell dumpsys power | grep "mWakefulness="
  ```
  If `mWakefulness=Dozing` or `mWakefulness=Asleep`, the device is healthy and attached!
- **Resolution:** Wake the device under `operator_device_lock` before capturing the screen:
  ```python
  from automation_core.device_lock import operator_device_lock
  from automation_core.adb import AdbClient

  with operator_device_lock(machine=machine_id, serial=serial, timeout=30.0):
      dev = AdbClient(serial=serial)
      dev.shell(["input", "keyevent", "KEYCODE_WAKEUP"], timeout=10)
      dev.shell(["input", "keyevent", "82"], timeout=10)  # Unlock swipe if present
  ```
