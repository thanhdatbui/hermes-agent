# Case 68 (02/09/2026): Tự Động Gỡ Popup Quyền Hệ Thống / Benign Dialog Trong Vòng Lặp Khởi Động App Tránh Lỗi Mất Focus TikTok Khi Launch (Sự Cố Máy 79)

## Context & Problem
On farm machines running TikTok automation (e.g. `multi-machine-feed-session`), when TikTok is launched, Android system permission dialogs (`com.google.android.packageinstaller`, `com.android.packageinstaller`, `com.google.android.permissioncontroller`) or other benign popups may immediately appear in the foreground ("Cho phép TikTok truy cập vào danh bạ của bạn?").

### Symptoms
- The runner halts immediately on startup with:
  `prepare-tiktok failed to focus TikTok after launch`
- Telegram alert: `[MÁY 79] DỪNG PHIÊN • prepare-tiktok failed to focus TikTok after launch • Trạng thái: GIỮ HIỆN TRƯỜNG ĐỂ HERMES AGENT XỬ LÝ`
- Attached screenshot shows the system permission dialog ("Cho phép TikTok truy cập vào danh bạ của bạn?") occluding the TikTok splash/feed screen.

### Root Cause
1. In `automation-core` (`src/automation_core/startup.py`), `prepare_app_for_automation` launches the app and enters a loop of `focus_attempts` (default 10) verifying `focused_package == target` (`com.ss.android.ugc.trill`).
2. When the system permission dialog is showing, `get_focused_activity` returns package `com.google.android.packageinstaller`.
3. Because `focused_package != target`, all 10 focus check attempts fail, and startup fails closed before control is ever handed over to the main session flow's popup dispatcher (`dismiss_tiktok_popups`).

---

## Architectural Solution

### 1. `automation-core` Core Layer
- **`prepare_app_for_automation` in `src/automation_core/startup.py`**:
  - Accepts an optional `popup_dismisser: Callable[[], bool] | None = None`.
  - In the focus retry loop (`attempt 1..10`), if `not focused` and `popup_dismisser is not None`:
    - Calls `popup_dismisser()`.
    - If `popup_dismisser()` returns `True` (a popup was detected and dismissed), it waits a short settle interval (0.5s) and immediately re-queries focus.
    - Records `StartupStep("dismiss_startup_popup", "success", ...)` into the startup summary.
- **`prepare_tiktok_app` in `src/automation_core/tiktok/startup.py`**:
  - Provides a default `_default_popup_dismisser` wrapping `dismiss_tiktok_popups` with `ui_dump_reader`/`dump_current_ui` and pass-through adapters for tap, back, and relaunch.

### 2. Consumer Layer (`tiktok-luot nuoi acc`)
- **`flows/device_prepare.py` (`prepare_tiktok_app_for_automation`)**:
  - Constructs a `dismiss_popup` callback that calls `dismiss_tiktok_popups(capture_xml=..., tap=..., press_back=..., relaunch=...)`.
  - Passes `popup_dismisser=dismiss_popup` to `core_prepare_app_for_automation`.
  - Maps `action_names["dismiss_startup_popup"] = "dismiss_startup_popup"` for structured jsonl logging.

---

## Verification & Testing Contract
- **Core offline tests (`tests/test_tiktok_startup.py`)**:
  - `test_prepare_tiktok_app_dismisses_startup_popup_when_focus_is_occluded`: Mocks `focus_reader` returning `packageinstaller` on attempt 1 and `com.ss.android.ugc.trill` on attempt 2 after `popup_dismisser` dismisses the contacts permission dialog.
- **Consumer offline tests (`python_runner/tests/test_device_prepare.py`)**:
  - `test_prepare_tiktok_app_dismisses_popup_when_focus_is_blocked`: Asserts `prepare_tiktok_app_for_automation` succeeds with `status == ExitStatus.SUCCESS` and `dismiss_startup_popup` recorded in summary steps.
- **Live Canary on Machine 79**:
  - Command: `python python_runner/run_tiktok.py --mode multi-machine-feed-session --account-workbook "D:\OneDrive\TaadaaData\kibe\taikhoan_run_safe.xlsx" --machines 79 --account-row-index 2 --recovery-test-swipes 2 --prepare-tiktok --allow-navigation-only --allow-feed-swipe --cleanup-on-stop`
  - Result: `Status: success`, `Exit code: 0`.
