# Runner Preflight Wi-Fi Fallback & Roam Triage

## Bối cảnh & Hiện tượng (2026-10-10)
Trong các phiên chạy nuôi feed (`multi-machine-feed-session`), nhiều máy báo lỗi rớt Wi-Fi (`dumpsys connectivity: Wi-Fi not connected`) hoặc lỗi nghẽn Proxy (`dial tcp 192.168.110.2:100xx: connect: network is unreachable`). Mặc dù ngoài nền có `farm_wifi_auto_healer.py`, máy vẫn bị tính fail trong phiên nuôi.

## 4 Nguyên nhân gốc đã được kiểm chứng
1. **Thiếu biến môi trường `FARM_WIFI_PROFILES_FILE` trong Runner**:
   - `python_runner/core/vpn_preflight.py` có cơ chế tự cứu Cấp 2 (`adbjoinwifi`), nhưng lấy credentials qua `_load_wifi_profiles()`.
   - `_load_wifi_profiles()` chỉ đọc từ `os.environ.get("FARM_WIFI_PROFILES_FILE")` hoặc `FARM_WIFI_PROFILES`.
   - Khi runner được kích hoạt từ PowerShell (`run-feed-session.ps1`) hoặc `tiktok_runner.py`, biến môi trường này không được truyền vào.
   - Kết quả: `get_wifi_credentials_for_machine(machine)` trả về `None`, code bỏ qua Cấp 2 và ném lỗi fail-closed ngay lập tức.
   - **Giải pháp**: Preflight bắt buộc phải có fallback trỏ tới `D:/Taadaa/machine-config/farm_wifi_profiles.json` nếu env rỗng.
   - **Telemetry & Closeout Gate Requirement**:
     - Phát sinh log INFO: `_VPN_TIMEOUT_LOGGER.info("WIFI_PROFILES_FILE_LOAD path=%s", Path(file_path).name)` để Sol Reviewer và watchdog có thể kiểm chứng runtime mà không làm lộ credentials.
     - Reviewer yêu cầu unit test xác nhận cả fallback trong runner script (`run-feed-session.ps1`) và assertion bắt log `WIFI_PROFILES_FILE_LOAD` trong `test_vpn_preflight_router.py`.

2. **Lệch pha thời gian (Timing Mismatch)**:
   - Worker preflight chỉ chờ 2 giây sau khi toggle Wi-Fi.
   - `farm_wifi_auto_healer.py` chạy theo nhịp cronjob mỗi 5 phút (`*/5 * * * *`).
   - Nếu worker không tự ép join lại tại chỗ trong vòng 5-8 giây, nó sẽ fail phiên trước khi cronjob kịp quét đến.

3. **Bẫy Saved Network Roam Trap (SSID `Dat` / dải `192.168.10.x`)**:
   - Các máy từng lưu mạng ngoài farm (`Dat`) sẽ tự nhảy sang dải `192.168.10.x` khi AP Aruba bị nghẽn tải.
   - Từ `192.168.10.x`, máy không thể kết nối tới MikroTik proxy IP `192.168.110.2:100xx` (báo `network is unreachable`).
   - **Giải pháp**: Xóa vĩnh viễn cấu hình mạng rác trong Android bằng `service call wifi 14 i32 <net_id>` (tham khảo `android-wifi-profile-cleanup`).

4. **Nghẽn bảng MAC & Association Rejection trên AP Aruba**:
   - 40 máy Samsung S7 (Android 8) trên mỗi AP tạo tải burst lớn khi cùng lúc load feed TikTok.
   - Cần đảm bảo lệnh `adbjoinwifi` luôn bọc nháy kép/nháy đơn quanh SSID có dấu cách (`'kibe 1'`, `'kibe 2'`, `'admin 1'`, `'admin 2'`) để tránh bị shell cắt cụt tên SSID.
