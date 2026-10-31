# Login Watchdog Quarantine & Reporting Fidelity Invariants

## 1. Ngữ cảnh & Triệu chứng lỗi
Khi vận hành các watchdog tự động login/nạp tài khoản định kỳ (như GPM Gmail login, TikTok, ChatGPT pool):
1. **Báo cáo tóm tắt nuốt mất chi tiết thất bại:** Báo cáo Telegram chỉ hiển thị số lượng thô (`✓ 0 | ✗ 3`) mà không kèm danh sách tài khoản hay mã lỗi (`PHONE_CHECKPOINT`, `WRONG_PASSWORD`).
2. **False Metric gây hiểu lầm (`max_proxy 0/cổng`):** Khi chốt ca không còn candidate, hàm format report nhận `proxy_count=None` mặc định, dẫn tới output `max_proxy 0/cổng`, làm người vận hành nhầm tưởng cụm proxy bị tắc/chết thay vì tài khoản dính checkpoint.
3. **Hiện tượng Zombie Candidate (Vòng lặp thử lại vô tận):**
   - Tài khoản hết hạn Cooldown 7 ngày (`retry_after <= today`) nhưng khi thử lại vẫn thất bại thì watchdog **không gia hạn ngày retry mới**, dẫn tới việc tài khoản bị bốc ra chạy liên tục mỗi ngày/mỗi ca.
   - Tài khoản dính **Hard Phone Checkpoint** (`challenge/iap` - ép nhập SĐT mới) chỉ trả về `status: FAIL` mà **không được ghi nhận cách ly** vào blacklist/status JSON, khiến ca sau lại tiếp tục thử lại và tăng nguy cơ tài khoản bị Google Disable.

## 2. Quy tắc thiết kế Watchdog Fidelity (Anti-Blindspot)
1. **Bắt buộc bảo toàn `failed_details` và `proxy_count` qua State:**
   - Khi chạy batch lẻ giữa ca, mọi tài khoản thất bại phải được push vào `failed_details` trong state file kèm `email`, `mid`, `fail_type`, `error_code`.
   - Tại tất cả các nhánh return / chốt ca (`if not candidates:`, `is_late`, `all_done`), hàm `_format_summary_report` BẮT BUỘC phải đọc và truyền đủ `failed_details` cùng `proxy_count` từ state đã lưu trong ngày.
2. **Tự động gia hạn Cooldown khi tái thất bại:**
   - Với các tài khoản từ pool cooldown (như 7 ngày, 72 giờ), nếu lần thử lại tiếp tục gặp lỗi nền tảng (`signin/rejected`, `cooldown`), script BẮT BUỘC phải tính toán lại:
     `new_retry_after = today + cooldown_delta`
     và ghi đè vào file status JSON, tuyệt đối không giữ nguyên mốc cũ khiến tài khoản bị bốc liên tục.
3. **Cơ chế Auto-Quarantine cho Hard Phone Checkpoint:**
   - Khi phát hiện `PHONE_CHECKPOINT` / `challenge/iap` (màn hình yêu cầu SĐT mà không có nút bỏ qua hoặc đã bấm thử cách khác thất bại):
     - Ghi nhận ngay vào danh sách cách ly (ví dụ `wrong_password_or_checkpoint` hoặc `cooldown_phone_checkpoint` với thời gian cách ly tối thiểu 7-14 ngày).
     - Lưu ảnh chụp màn hình bằng chứng để phục vụ đối soát.
     - Trả về mã lỗi rõ ràng để loại khỏi hàng đợi login tự động cho đến khi được xử lý thủ công hoặc hết hạn cách ly.
