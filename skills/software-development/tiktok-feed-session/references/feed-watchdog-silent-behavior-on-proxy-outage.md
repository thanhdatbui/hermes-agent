# Feed Watchdog Silent Behavior on Proxy/VPN Fail-Closed Outages

## Bối cảnh & Hiện tượng
Khi người dùng thắc mắc: *"Sáng nay máy không chạy nhưng sao không thấy báo cáo từng phiên như bình thường?"*.

## Cơ chế vận hành thực tế
1. **Fast Fail-Closed Server Socket Probe**:
   - Khi dải port proxy server (ví dụ `test.taadaa.click:5101..5124`) bị sập / timeout / Connection Refused từ bên ngoài, preflight `require_vichanger_connected` lập tức chặn đứng toàn bộ máy trong <=1.5s/worker.
   - Không máy nào được phép mở TikTok hay lướt feed bằng Direct IP.
   - Trạng thái lock được set sang `blocked`, giữ nguyên hiện trường an toàn.

2. **Hệ quả đối với Run Artifacts**:
   - Do tất cả máy bị chặn ngay tại preflight trước khi vào phiên thực thi, runner thoát mà không tạo các thư mục chạy `row-X-HHMMSS` bên trong `D:\Taadaa\runtime\kibe\live\YYYY-MM-DD`.

3. **Nguyên tắc Watchdog im lặng (`feed_session_watchdog.py`)**:
   - Watchdog chạy cron `no_agent: true` mỗi 5 phút để tổng hợp báo cáo.
   - Watchdog chỉ phát tin nhắn Telegram khi phát hiện thư mục `row-X-HHMMSS` có kết quả máy hoàn tất.
   - Khi không có thư mục run artifact nào, script trả về stdout rỗng. Cron engine nhận diện `empty stdout = silent` và không gửi tin nhắn rác lên Telegram.

## Quy trình kiểm tra & Chẩn đoán nhanh khi mất báo cáo
Khi không thấy báo cáo phiên xuất hiện:
1. **Kiểm tra socket port proxy server**:
   ```bash
   python -c "import socket; s=socket.socket(); s.settimeout(2); print('5101 open:', s.connect_ex(('test.taadaa.click', 5101)) == 0)"
   ```
2. **Kiểm tra Lease & Lock state**:
   - Đọc `D:\Taadaa\runtime\kibe\cron-state\runner-live-lease\YYYY-MM-DD.json`.
   - Kiểm tra `~/.codex/device-locks/` xem có máy nào đang giữ lock `blocked` không.
3. **Kết luận chính xác cho User**:
   - Giải thích rõ: Hệ thống đã bảo vệ an toàn (không để máy chạy Direct IP khi mất proxy), runner dừng ngay tại preflight nên không có artifact phiên để watchdog tổng hợp tin nhắn. Cần khôi phục dải proxy server để farm tiếp tục chạy.
