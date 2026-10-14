# TikTok Feed Session Recovery: Proxy Preflight Timeout & Cold Launch Focus (2026-10-14)

## 1. Sự cố rụng máy hàng loạt (Mass Machine Drop)
- Trong các phiên nuôi acc hàng loạt (Ca 1/2), nếu có 30-50 máy đột ngột báo lỗi `blocked-proxy-vpn` hoặc `prepare-tiktok failed to focus TikTok after launch`:
  + Kiểm tra ngay log `summary.txt` của các máy bị fail trong runtime directory (`D:/Taadaa/runtime/kibe/live/...`).

## 2. Các điểm nghẽn kỹ thuật đã xác định & cách xử lý

### A. ADB Settings Query Timeout trong VPN Preflight
- **Vấn đề:** `python_runner/core/vpn_preflight.py` thực hiện:
  `adb.shell(["settings", "get", "global", "http_proxy"], timeout=3.0, check=False)`
  Khi chạy song song 16–30 workers hoặc qua ADB socket mạng LAN (Admin Remote PC), thời gian phản hồi thường vượt quá 3s. Hàm bắt timeout và quy kết thành `device is offline or ADB/USB disconnected`, làm rụng máy oan.
- **Chuẩn hóa:**
  1. Nâng timeout tối thiểu lên `8.0s`.
  2. Bọc vòng lặp retry 2 lần với khoảng nghỉ `1.0s` giữa 2 lần thử trước khi raise exception.

### B. Thời gian chờ Focus ứng dụng TikTok trên Samsung S7
- **Vấn đề:** `python_runner/flows/device_prepare.py` định nghĩa `PREPARE_FOCUS_MAX_ATTEMPTS = 10` với delay `1.5s` (tổng 15s). Trên máy Samsung Galaxy S7 phần cứng cũ, TikTok v47.0.3 khởi động nguội sau force-stop mất 16–22s.
- **Chuẩn hóa:**
  1. Tăng `PREPARE_FOCUS_MAX_ATTEMPTS = 16` (tổng 24s) để app kịp hoàn thành splash screen.
  2. Phối hợp với Fast Fail-Closed để không ngắt phiên sớm khi app chỉ đang nạp chậm.

## 3. Lưu ý Guard khi Dispatch Worker (delegate_task)
- Giới hạn tối đa <= 2 files mỗi task (1 file logic + 1 file test).
- Luôn kèm câu lệnh Fail-Fast: `FAIL_FAST: Nếu trong <= 3 iterations đầu thấy scope bất khả thi với budget 15 calls thì DỪNG NGAY (ABORT)...`
- `FOCUSED_TEST` bắt buộc dùng relative path không khoảng trắng (`python_runner/...`), vì parser regex `[^\s]+\.py` sẽ từ chối đường dẫn chứa khoảng trắng như `D:/Taadaa/tiktok-luot nuoi acc/...`.
