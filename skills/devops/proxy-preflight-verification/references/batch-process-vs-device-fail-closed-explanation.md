# Chẩn đoán phân biệt giữa Tiến trình Batch và Thiết bị Android (Proxy Fail-Closed)

## Bối cảnh & Hiện tượng gây hiểu nhầm
Khi toàn bộ dải proxy/VPN bị sập từ phía server (ví dụ toàn bộ port proxy connection refused / timeout):
- Người vận hành quan sát thấy trên máy tính các tiến trình `powershell.exe` hoặc `run-feed-session.ps1` vẫn đang chạy hoặc task manager hiển thị CPU/process của batch.
- Dễ dẫn đến nghi vấn: "Tại sao hàng loạt máy lỗi VPN/proxy mà hệ thống vẫn cho chạy?"

## Bản chất vận hành thực tế
1. **Tiến trình Host (Batch Scheduler / Process Pool):**
   - Khung điều phối (`run-feed-session.ps1`, `ThreadPoolExecutor`) được cron kích hoạt theo đợt để quét danh sách các máy trong cohort.
   - Tiến trình trên host vẫn phải sống để duyệt tuần tự/song song qua từng máy trong danh sách và thu thập báo cáo kết thúc phiên.

2. **Chặn đứng ở tầng thiết bị (Fail-Closed Gate):**
   - Ngay ở bước đầu tiên khi worker nhận việc (`preflight_phase`), hàm `require_vichanger_connected` kiểm tra TCP socket probe hoặc broadcast `GET_IP`.
   - Khi phát hiện proxy server chết, worker lập tức ném `ConsumerPreflightError` (`blocked-vichanger-vpn`), `swipes_completed = 0`.
   - **Tuyệt đối KHÔNG:** không mở app TikTok, không lướt feed, không follow bằng Direct IP của mạng gia đình/host.
   - Khóa thiết bị được chuyển về `blocked` (giữ nguyên hiện trường) để bảo vệ tài khoản.

## Quy tắc giải thích cho người dùng
- Phải tách bạch rõ ràng giữa:
  1. **Tiến trình quản lý batch trên Windows (Host Process)**: Vẫn chạy để điều phối và ghi nhận log/kết quả.
  2. **Hành vi trên thiết bị Android thật (Device Action)**: Đã bị chặn đứng an toàn 100% (fail-closed, 0 action trên app).
- Tránh trả lời chung chung khiến người dùng hiểu lầm là thiết bị đang lướt feed lộ IP thật.
