---
name: android-wifi-profile-cleanup
description: "Use when cleaning rogue Wi-Fi profiles on Android farms."
version: 1.0.0
author: Hermes Agent
tags: [android, wifi, farm, adb, cleanup, evidence]
---
# Android Wi-Fi Profile Cleanup

Use this class-level workflow when Android farm phones auto-connect to a non-farm SSID and must be returned to their fixed Aruba SSID. The goal is to remove only the confirmed rogue profile, preserve the farm profile, and leave a machine-level audit trail.

## Safety contract

- Never use a rogue SSID as a fallback or recovery network.
- **CẤM BÁO "ĐỂ IM CHỜ TỰ PHỤC HỒI" KHI CHƯA ĐỐI SOÁT CỜ PHẠT / XÁC THỰC:** Tuyệt đối CẤM suy đoán thụ động "chờ qua đêm/chờ sáng mai Wi-Fi tự phục hồi". Khi máy mất IP hoặc không kết nối, bắt buộc trích xuất ngay cờ `mNetworkSelectionDisableReason` trong `dumpsys wifi` và chạy WinRT OCR trên màn hình Cài đặt Wi-Fi. Nếu thấy dòng đỏ **"Đã xảy ra lỗi xác thực"** (`DISABLED_BY_WRONG_PASSWORD` / `ASSOCIATION_REJECTION`), Android OS sẽ **bỏ qua vĩnh viễn SSID đó trong mọi chu kỳ quét nền** — tình trạng này KHÔNG BAO GIỜ tự khỏi nếu không can thiệp xóa profile kẹt và nạp lại mật khẩu chuẩn.
- **Poison SSID Strict Blacklist (`Dat`, `Dat-1`, `BOX`)**: Tuyệt đối CẤM đưa các SSID ngoại lai ngoài farm (`Dat`, `Dat-1`, `BOX`) vào bất kỳ file cấu hình, tài liệu, script cứu hộ, hoặc logic fallback nào. Mọi SSID ngoài 4 AP Aruba quy hoạch cứng (`kibe 1`, `kibe 2`, `admin 1`, `admin 2`) đều là Poison SSID — hành động duy nhất được phép khi phát hiện là tiêu diệt/xóa vĩnh viễn (Purge/Forget) khỏi toàn bộ thiết bị. CẤM TUYỆT ĐỐI agent/script tự ý thử kết nối vào `Dat` để "chữa cháy" hay "test".
- **Saved Network Roam Trap**: Removing fallback logic from host Python scripts is NOT enough. If phones previously joined a rogue SSID, Android OS stores the profile in `WifiConfigStore.xml` (priority 100) and will auto-roam to it during radio toggles or AP load spikes. Cleanup MUST actively verify and re-bind all devices.
- Never remove a network by guessing an ID, by iterating through all IDs, or by trusting stale `dumpsys wifi` event history.
- Every device mutation runs under `D:/Taadaa/tools/with_device_lock.py --machine <N> -- ...` with the correct cluster/serial.
- Do not use `adb shell input tap`, `input keyevent`, or `input swipe` as a substitute for fixing network state.
- Do not read or expose Wi-Fi passwords in reports; use placeholders such as `<FARM_WIFI_PASSWORD>`.
- A device with no current rogue-SSID evidence is `NO_DAT_EVIDENCE` (or equivalent) and is not modified.

## Fixed target mapping

Resolve the machine number from the canonical workbook/mapping before changing anything:

- M01–M40 → `kibe 1`
- M41–M80 → `kibe 2`
- M201–M240 → `admin 1`
- M241–M280 → `admin 2`

Do not infer a target from the currently connected SSID. Do not move a phone between AP groups.

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
