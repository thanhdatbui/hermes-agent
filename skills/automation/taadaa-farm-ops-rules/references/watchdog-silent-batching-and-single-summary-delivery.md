# Watchdog Silent Batching & Single Summary Delivery

## Context & Problem
Các cron watchdog chạy dạng `no_agent=True` trên Hermes (giao tiếp qua Telegram channel như Farm Alert `-5373649734` hoặc DM):
- Hermes cron runner áp dụng semantics: **Bất kỳ output nào trên stdout (khác rỗng) đều được tự động gửi thành 1 tin nhắn đến target channel.**
- Khi watchdog chạy cuốn chiếu theo batch nhỏ (ví dụ mỗi 5-10 phút xử lý một cụm máy/acc qua `ThreadPoolExecutor`), nếu trong script có lệnh `print()` in kết quả từng batch lẻ (`✓ N | ✗ M`), nó sẽ liên tục bắn tin nhắn rác vào channel sau mỗi chu kỳ tick.
- Người dùng phàn nàn: *"Gì thế báo liên tục v"*.

## Rule of Silence (Nguyên tắc Im lặng tuyệt đối)
1. **Silent Batching**: Trong suốt quá trình xử lý các batch lẻ, toàn bộ tiến trình PHẢI im lặng trên stdout.
   - Dùng `sys.stderr.write()` hoặc `logging` để ghi log debug/trace (stderr KHÔNG kích hoạt delivery tin nhắn trên cron `no_agent`).
   - CẤM gọi `print()` ở cuối mỗi vòng lặp batch lẻ.
2. **Single Summary Delivery (Chỉ báo 1 lần duy nhất)**:
   - Lưu trữ state cuốn chiếu (`date`, `processed`, `total_success`, `total_fail`, `reported`, `finished`).
   - Chỉ in đúng 1 dòng tổng kết ra stdout khi:
     - Đã hoàn tất 100% danh sách cần xử lý (`all_done = True`), HOẶC
     - Đã chạm mốc kết thúc ca (ví dụ sau 23:30), VÀ
     - Chưa từng báo cáo trước đó (`not reported`), VÀ
     - Có ít nhất 1 tác vụ đã thực hiện (`total_success > 0 or total_fail > 0`).
   - Đánh dấu ngay `reported = True` vào state file sau khi in để chặn mọi tick sau đó in lại.
3. **Guard Profile / Preconditions**:
   - Lọc sạch các item chưa đủ điều kiện hạ tầng (ví dụ tài khoản chưa có Profile trong GPM DB) ngay từ khâu `get_candidates()` để tránh spam fail hàng loạt (`PROFILE_NOT_FOUND`).
