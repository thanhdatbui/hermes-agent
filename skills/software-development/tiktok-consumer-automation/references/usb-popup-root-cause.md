# USB popup Samsung — chuỗi root cause đầy đủ (máy 74, 2026-08-03)

## Triệu chứng

Máy 74 avatar flow fail lặp: `AVATAR_EDIT_OPEN_FAILED`, sau đó `AVATAR_VERIFY_FAILED`
dù ảnh nguồn tốt. Kiểm tra `dumpsys window` thấy
`mCurrentFocus=com.samsung.android.MtpApplication/.USBConnection` — popup kết nối
USB của Samsung phủ lên TikTok sau khi PC sleep/bật lại. Popup này xuất hiện
BẤT KỲ LÚC NÀO (mỗi lần PC sleep), không chỉ lúc cắm USB lần đầu.

## 3 lớp nguyên nhân chồng nhau (đều phải xử lý)

### 1. Handler tồn tại nhưng máy chạy TRƯỚC khi nó có hiệu lực (timeline)

- `state_machine.py` thêm import + gọi `dismiss_usb_popup` lúc 09:02.
- Wheel core `automation_core-0.4.21` (chứa `usb_popup.py`) build lúc 09:26.
- Máy 74 chạy lúc 08:19 — TRƯỚC cả 2 mốc → popup không được dismiss.

**Bài học**: khi user hỏi "rule có trong core sao không hoạt động", kiểm tra
mtime file/wheel vs thời điểm run (`ls -la`, `ls -d runs/run_*_HHMMSS`) trước
khi kết luận. Rule mới chỉ có hiệu lực với run SAU mốc triển khai.

### 2. Env thực thi cài dở dang (dist-info mới, file module thiếu)

- `D:\Taadaa\python-envs\automation` có `automation_core-0.4.22.dist-info`
  nhưng `site-packages/automation_core/` KHÔNG có `usb_popup.py` → import fail
  im lặng.
- Chuẩn đoán: `ls site-packages/automation_core/ | grep usb` rỗng nhưng
  `pip show automation-core` báo version cao.
- Fix: `pip install --force-reinstall <wheel đúng pin>` (xem SKILL.md).

### 3. dismiss_usb_popup_shell phụ thuộc uiautomator dump — fail khi popup chặn uiautomator

- Bản đầu: `dismiss_usb_popup_shell` gọi `dismiss_usb_popup` với `_shell_ui_dump`
  (uiautomator dump). Popup chặn uiautomator → UI dump fail → `_recapture_status`
  trả `unavailable` → hàm trả False dù BACK đã đóng popup.
- Fix (finding MAJOR từ reviewer): verify đóng popup bằng **dumpsys activity
  probe** (`_shell_probe`), không dùng uiautomator. Sau mỗi action (tap
  button_cancel → keyevent 4) probe lại `usb_popup_activity_present`.
- `prepare_device` gọi `dismiss_usb_popup_shell` sau swipe_unlock, không raise
  khi absent/fail, thêm field `usb_popup_dismissed` optional vào
  `DeviceReadiness` (backward-compatible).

## Vị trí code

- `automation_core/usb_popup.py`: `usb_popup_activity_present` (dumpsys),
  `dismiss_usb_popup` (adapter), `dismiss_usb_popup_shell` (shell-only),
  `_shell_probe`, `_shell_action_and_probe`.
- `automation_core/device.py::prepare_device`: auto-dismiss cuối hàm.
- `automation_core/device_recovery.py`: `wait_until_unlocked`/`watch_device_reconnect`
  đi qua `prepare_device` → mọi consumer được phủ.

## Test

- `tests/test_usb_popup.py` + `tests/test_device_readiness.py` — 21 test, gồm
  nhánh uiautomator bị chặn (mock `adb.shell` trả ok=False cho uiautomator dump
  nhưng dumpsys activity vẫn đọc) → dismiss qua BACK vẫn trả True.
- Core suite 362 passed, consumer TikTok 259 passed.

## Popup USB khác (KHÔNG nhầm)

- `com.android.systemui.usb.UsbDebuggingActivity` = "Allow USB debugging?" (lần
  đầu bật developer mode) — core `usb_debugging.py` xử lý, KHÁC popup MTP.
- `usb_popup.py` (MTP connection) và `usb_debugging.py` (debugging consent) là
  hai module khác nhau, đừng nhầm khi tìm handler.
