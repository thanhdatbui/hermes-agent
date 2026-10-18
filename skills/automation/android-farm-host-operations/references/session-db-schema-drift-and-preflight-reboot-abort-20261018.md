# In-Flight Session Preservation Schema Drift & Preflight Reboot Abort Incident (2026-10-18)

## 1. Hiện Tượng & Triệu Chứng
- **Triệu chứng tại ca nuôi:** Ca 1 Phiên 1 (06:05 Sáng) và Ca 2 Phiên 1 (12:03 Trưa) bị "Lỗi App TikTok/Script" hàng loạt trên cả 2 cụm Kibe và Admin:
  * Ca 1 Phiên 1: Kibe 73 fail (39 spinner, 24 account-switcher-not-open), Admin 79 fail (55 spinner, 12 switcher).
  * Ca 2 Phiên 1: Kibe 77 fail (34 spinner, 31 switcher), Admin 73 fail (51 spinner, 10 switcher).
  * Đến Phiên 2 (08:00 sáng), hệ thống tự động phục hồi lên **123/160 máy thành công** (Kibe 69, Admin 54).
- **Hiện trường màn hình thiết bị thật:** OCR bằng chứng màn hình M1 (`profile_switcher_3_settled\screen.png`) chứng minh nick mục tiêu (`@ginnyhanstei80`) đã nằm sẵn trên app, không hề mất nick, không văng login.

## 2. Bản Chất Kỹ Thuật: Chuỗi Domino Nghẽn Bus USB 2.0 EHCI Do Bị Hủy Reboot

### A. Lỗi Schema Mismatch Tại `preserve_in_flight_sessions`
- Trong `D:\Taadaa\tools\services\Taadaa_Service\farm_preflight_daily_reset.py`, hàm `preserve_in_flight_sessions()` được gọi lúc 05:20 sáng trước khi phát lệnh reboot.
- Hàm này kiểm tra tính toàn vẹn cấu trúc database trước khi ghi đè cờ `resume_pending`:
  ```python
  _SESSION_SCHEMA_REQUIREMENTS = {
      "gateway_routing": ("scope", "key", "value"),
      "messages": ("id", "session_id", "role", "tool_calls", "timestamp", "active"),
  }
  ```
- **Tử huyệt:** Trong SQLite database thực tế của Hermes `SessionDB`, bảng `gateway_routing` có các cột:
  `scope (TEXT)`, `session_key (TEXT)`, `entry_json (TEXT)`, `updated_at (REAL)`.
- Hai cột `'key'` và `'value'` không tồn tại (đã đổi tên thành `session_key` và `entry_json`).
- `farm_preflight_daily_reset.py` quăng lỗi:
  `RuntimeError: schema SessionDB khong khop: bang gateway_routing thieu cot ['key', 'value']`
- Cơ chế fail-safe bảo toàn session của script đã **hủy toàn bộ tiến trình reboot cả Kibe lẫn Admin PC** (`aborted_preserve_failed`).

### B. Hậu Quả Cascade Trên Host Server Dual Xeon X99
- Do mốc 05:20 bị crash và mốc 11:20 bị skip (vướng active lock), Host PC Kibe chạy thông suốt >20 giờ liên tục kể từ chiều hôm trước.
- Bộ điều khiển Intel C610/X99 USB 2.0 EHCI (`8D26`, `8D2D`) bị tích tụ nghẽn endpoint buffer sau hàng chục nghìn lượt command ADB.
- Khi bước vào Phiên 1 của ca nuôi, 25 workers đồng loạt đổ tải kiểm tra proxy, mở app và chụp màn hình/dump XML.
- Độ trễ I/O trên bus USB 2.0 vọt từ 0.2s lên 5s–10s, gây ra hiện tượng kép:
  1. `_wait_for_profile_loading_spinner`: Lệnh `ctx.adb.dump_ui(timeout=5)` bị trễ hoặc timeout 5s, runner phán đoán nhầm là `profile loading spinner still visible or UI dump failed`.
  2. `tap_profile_switch_anchor`: Thao tác click vào switcher anchor diễn ra nhưng chụp màn hình xác nhận sau đó bị timeout 10s, runner phán đoán nhầm là `manual-needed:account-switcher-not-open: profile screen remained after switch-anchor tap`.
- Tại Phiên 2 (08:00), khi hàng loạt máy đã stagger xong và áp lực socket lắng xuống, 123 máy hoàn tất mượt mà.

## 3. Quy Trình Khắc Phục Chuẩn
1. **Sửa Schema Check Trong `farm_preflight_daily_reset.py`:**
   Cập nhật `_SESSION_SCHEMA_REQUIREMENTS`:
   ```python
   _SESSION_SCHEMA_REQUIREMENTS = {
       "gateway_routing": ("scope", "session_key", "entry_json"),
       "messages": ("id", "session_id", "role", "tool_calls", "timestamp", "active"),
   }
   ```
2. **Đồng bộ file service sang thư mục triển khai:**
   Sao chép bản vá từ `D:\Taadaa\tools\services\Taadaa_Service\farm_preflight_daily_reset.py` sang `C:\Taadaa_Service\farm_preflight_daily_reset.py`.
3. **Kiểm tra Preflight Check-Only:**
   Chạy `python D:/Taadaa/tools/services/Taadaa_Service/farm_preflight_daily_reset.py --check-only` để bảo đảm `preserve_in_flight_sessions` trả về integer `>= 0` và exit code 0.
4. **Nhận diện Bẫy Phân Loại Fallback Của Watchdog:**
   Khi nhận alert hàng loạt "Lỗi App TikTok/Script", đối soát ngay Uptime hệ thống và `summary.txt`. Nếu thấy spinner/switcher tăng vọt cùng lúc với máy rớt ADB/USB, nguyên nhân 100% là do nghẽn bus USB EHCI phần cứng do trôi mốc reboot, không phải lỗi logic app TikTok.
