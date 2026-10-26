# Invariant Cấm Tuyệt Đối Shell UiAutomator Dump Trong Thu Thập Telemetry & Cứu Hộ

> Áp dụng cho: `incident_emitter.py`, `incident_auto_harness.py`, các watchdog và script cứu hộ toàn Farm.

## 1. Bản chất Invariant Của User
- **CẤM TUYỆT ĐỐI:** Mọi hành vi gọi `adb shell uiautomator dump` hoặc `uiautomator dump /sdcard/...`.
- **Lý do phần cứng:** Dàn thiết bị Samsung S7 (Android 7/8) cấu hình RAM yếu. Chạy `uiautomator dump` trên DOM sâu của app (TikTok 47.x, Outlook, Settings) sẽ bị Linux kernel SIGKILL (`EXIT=137`), làm treo adapter ADB, kẹt tiến trình `com.github.uiautomator` ngầm và dẫn đến timeout 100%.

## 2. Chuẩn Thay Thế Bắt Buộc (Dual Mechanism)
1. **Thị giác & Text (Visual / OCR):**
   - Chụp màn hình: `adb exec-out screencap -p > screen.png`.
   - Đọc Text: Bắt buộc dùng `winrt_ocr(png_path)` (Windows Native WinRT OCR).
   - Xử lý Sleep / Tắt màn hình: Nếu máy ở chế độ tắt màn hình (`mHoldingDisplaySuspendBlocker=false`), phải gửi keyevent bật sáng màn hình (`input keyevent 224`) trước khi chụp, chống chụp ra ảnh đen xì (RGB toàn 0).
2. **Cấu trúc UI XML (Hierarchy):**
   - Bắt buộc qua `atx-agent` (port 7912).
   - Local: Endpoint `http://127.0.0.1:7912/dumpUI` hoặc `automation_core.persistent_ui.dump_persistent_ui` / `capture_atx_session_ui`.
   - Remote (Admin Cluster / 192.168.110.119): Dùng device-local `atx-agent curl`:
     ```bash
     /data/local/tmp/atx-agent curl -s --max-time 8 http://127.0.0.1:7912/dumpUI
     ```
     Bypass 100% Windows Firewall và TCP forward qua LAN.
