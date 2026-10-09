# On-Device Global HTTP Proxy Probe Precedence (2026-09-06 Incident)

## Sự cố (Incident Context)
- **Cảnh báo**: `[FARM ALERT: MÁY 26] DỪNG PHIÊN - required Android VPN/proxy is unreachable: proxy server port is closed/refused for ce081608c4e3ed1e05; skipping recovery wait to unblock other machines immediately`.
- **Hiện tượng**: Hàng loạt máy farm bị ngắt ngay tại bước preflight (`swipes_completed=0`), người vận hành nghi ngờ mạng farm bị phá hoặc VPN sập diện rộng.
- **Thực tế thiết bị**:
  - Máy 26 (`ce081608c4e3ed1e05`) kết nối ADB bình thường.
  - Card `wlan0` nhận IP `192.168.110.205/24`.
  - Thiết bị được gán proxy Sing-box: `192.168.110.2:20026` qua `settings put global http_proxy`.
  - Kiểm tra TCP socket từ host: `socket.connect_ex(('192.168.110.2', 20026))` trả về `0` (CỔNG ĐANG MỞ & HOẠT ĐỘNG HOÀN TOÀN TỐT).

## Nguyên nhân gốc (Root Cause)
1. **Lệch nguồn dữ liệu proxy giữa Workbook và Thiết bị**:
   - Dàn farm đã chuyển sang dùng cụm Sing-box container nội bộ (`192.168.110.2:20001..20080`).
   - File Excel mapping trên host (`D:\OneDrive\TaadaaData\kibe\PROXYgandienthoai.xlsx`) vẫn lưu cấu hình cũ từ giai đoạn dùng proxy Mobifone (`test.taadaa.click:5101..5138`), vốn đã bị đóng hoàn toàn trên internet.
2. **Cơ chế Fast Socket Probe thiếu context thiết bị**:
   - Trong `python_runner/core/vpn_preflight.py`, hàm `_proxy_server_live(serial, timeout=1.5)` chỉ đọc file Excel workbook để lấy chuỗi `host:port`.
   - Vì file Excel ghi `test.taadaa.click:5132` (cổng bị từ chối kết nối), probe TCP socket trả về `False`.
   - Cơ chế Fast Fail-Closed lập tức kích hoạt, chặn đứng phiên chạy của Máy 26 và hàng loạt máy khác dù proxy thực tế trên máy không hề chết.

## Giải pháp chuẩn hóa (Remediation)
1. **Ưu tiên On-Device Proxy trước Workbook**:
   - Hàm `_proxy_server_live` bắt buộc nhận thêm tham số `adb: AdbClient | None = None`.
   - Nếu có `adb`, truy vấn trực tiếp từ thiết bị: `adb.shell(["settings", "get", "global", "http_proxy"], timeout=3.0, check=False)`.
   - Nếu giá trị hợp lệ (khác `null`, `:0`, `none`), sử dụng ngay proxy này để probe TCP socket.
   - Chỉ fallback về workbook `get_default_proxy_mapping()` khi trên thiết bị chưa được cấu hình `http_proxy`.
2. **Truyền `adb=adb` tại Consumer Preflight**:
   - Trong `require_proxy_connected`, khi gọi `_proxy_server_live(serial, timeout=1.5)`, bắt buộc truyền đối tượng `adb=adb` đã khởi tạo.
