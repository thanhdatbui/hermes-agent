# Case 92: Tự Động Reconnect ADB Transport Khi Probe Mạng / Proxy Timeout & Cơ Chế Self-Healing (2026-09-04)

## 1. Hiện tượng & Sự cố thực tế
Khi chạy quy trình nuôi acc (`tiktok-luot nuoi acc`), máy gặp hiện tượng kẹt socket USB/ADB sau nhiều giờ hoạt động liên tục.
Lệnh probe mạng `adb shell ip addr show wlan0` hoặc `dumpsys connectivity` bị timeout quá deadline (`adb command timed out: ...`).

## 2. Anti-Pattern (Lỗi xử lý trước đây)
- **Sai lầm 1: Nuốt lỗi sai phân loại.** Exception `ADBError("adb command timed out: ...")` không được xem là `transport_lost` trong `is_connection_lost()`, khiến runner hiểu nhầm là router proxy bị mất mạng và kích hoạt kill switch (`required router proxy is unreachable`).
- **Sai lầm 2: Chữa ngọn bằng lệnh shell ngoài.** Chạy lệnh `adb reconnect` từ bên ngoài để gỡ kẹt rồi chạy canary, để lại codebase chưa có cơ chế tự phục hồi, khiến các máy khác gặp lỗi tương tự trong tương lai.

## 3. Giải pháp chuẩn (Case Fix trong Codebase)
1. **Phân loại chính xác Timeout thành Transport Loss:**
   - Trong `automation_core/adb.py`, bổ sung `"adb command timed out"` vào `CONNECTION_LOST_MARKERS` và hàm `is_connection_lost()`.
2. **Auto-Reconnect Self-Healing trong Preflight:**
   - Trong `python_runner/core/vpn_preflight.py` (`require_proxy_connected`), khi initial probe hoặc recovery probe bắt được `is_connection_lost` hoặc `timed out`:
     + Tự động gọi `adb.reconnect()` / `_reconnect_device()` để giải phóng socket transport phía PC và daemon.
     + Chờ 2.0s để thiết bị ổn định kết nối.
     + Thử lại probe lần 2 trước khi kết luận fail-closed.
3. **Tối ưu Bounded Timeout On-Device:**
   - Đặt deadline hợp lý (`max(4.0, ...)` / `min(..., 8.0)`) cho các lệnh `ip addr`, `dumpsys connectivity`, `settings get` trong `automation_core/preflight.py`.

## 4. Quy tắc vận hành
- Khi nhận Farm Alert `[MÁY N]`, **BẮT BUỘC** thực hiện theo chu trình 5 bước recovery: Inspect -> Root Cause -> Patch Codebase -> Canary Test -> Closeout.
- Tuyệt đối cấm gõ lệnh ADB tay chữa ngọn. Mọi lỗi phải được bọc bằng exception handling và auto-recovery trong script.
