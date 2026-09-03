# Fast Fail-Closed Proxy Probe in Feed Session VPN Preflight (2026-08-28)

## Bối Cảnh & Vấn Đề
- Khi một máy chủ proxy (ví dụ `test.taadaa.click`) bị sập hoặc từ chối kết nối cổng (Connection Refused / Error 10035):
  - Trước đây: Mọi máy thuộc dải proxy đó khi vào `require_vichanger_connected` đều phải chạy qua vòng lặp:
    1. Chờ proxy watcher reassign (`wait_for_proxy_ready` timeout 60s).
    2. Chờ stage-2 reconnect / retry.
    3. Chờ soft-reboot & boot timeout (180s) và proxy timeout (240s).
    -> Mỗi máy lỗi mất 4 - 6 phút.
  - Hậu quả: Khi có 64/80 máy dính proxy chết trong cùng 1 batch, 40 workers trong `ThreadPoolExecutor` bị nghẽn hoàn toàn, không thể giải phóng luồng cho 16 máy có proxy sống (`mirotik1.taadaa.click`, `khoalee.duckdns.org`).

## Giải Pháp: Fast Fail-Closed Socket Probe (`_proxy_server_live`)
- Triển khai hàm `_proxy_server_live(serial, timeout=1.5)` trong `python_runner/core/vpn_preflight.py`:
  - Trước khi bước vào bất kỳ chu kỳ recovery hay chờ đợi nào, thực hiện probe nhanh socket TCP `host:port` của proxy được gán trong `PROXYgandienthoai.xlsx` từ máy host.
  - Nếu kết nối thất bại / port đóng / unreachable (`server_alive is False`):
    - Ngay lập tức raise `ConsumerPreflightError` với lý do rõ ràng: `required Android VPN is unreachable: proxy server port is closed/refused for <serial>; skipping recovery wait to unblock other machines immediately`.
    - Trả trạng thái `blocked-vichanger-vpn` với `swipes_completed=0` chỉ trong **1.5 giây**.
  - Luồng worker được giải phóng ngay lập tức để chuyển sang xử lý các máy tiếp theo.

## Quy Tắc Lấy Dữ Liệu Máy
- **Single Source of Truth cho cấu hình nick & serial:** Bắt buộc đọc từ `taikhoan_run_safe.xlsx`.
- Không được tự suy diễn trạng thái tài khoản thiếu/rỗng khi chưa đối chiếu kỹ từng dòng trong `taikhoan_run_safe.xlsx`.
- Trường hợp cột Device ID trong workbook bị lẫn ngày tháng (`DD/MM/YYYY`), phải chuẩn hóa sang đúng serial phần cứng tương ứng của máy trước khi kết luận lỗi.
