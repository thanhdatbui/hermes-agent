# Gmail Preflight Live Check & ChatGPT Warmup Ops

## 1. Cơ Chế Preflight Live Check & Dual Cleanup (Gmail DIE)
Trong các đợt chạy batch đăng ký TikTok qua `_run_all_targets.py`:
- **Vấn đề**: Nhiều máy S7 bị treo 150 giây ở `[7c][BLOCKED_GMAIL_OTP_TIMEOUT]` do các Gmail nguồn thực chất đã bị Google vô hiệu hóa (DIE) từ trước nên không thể nhận OTP.
- **Giải pháp**: Tích hợp `scripts/gmail_preflight_filter.py` vào trước bước phân bổ batch máy S7 để kiểm tra hàng loạt qua `check_gmail_live_batch()` (`checkmail.live`).
- **Quy tắc dọn dẹp kép (Dual Cleanup Rule - Bắt buộc)**:
  Khi `checkmail.live` xác nhận tài khoản `DIE` (`result is False`), **BẮT BUỘC** phải xử lý dọn dẹp ở cả 2 nơi song song:
  1. **Trên file Excel nguồn**: Gọi `remove_captcha_dead_email_from_source(email)` để xóa khỏi `gmail_clean_v2.xlsx`, tránh việc các phiên sau lại bốc trúng.
  2. **Trên thiết bị Android S7**: Gọi `remove_device_account_fast(serial, email)` (`remove_device_google_account.py`) để gỡ bỏ tài khoản Google DIE khỏi máy S7, không để lại tài khoản rác/die chiếm slot.
- **Fail-open resilience**: Nếu `checkmail.live` bị lỗi kết nối, timeout hoặc module ngoài gặp sự cố, hệ thống tự động fallback giữ nguyên danh sách targets để không làm ngắt quãng toàn bộ batch.
- **CLI flag**: Thêm cờ `--skip-live-check` khi cần bypass preflight.

## 2. Pitfalls Hook Warmup ChatGPT Sau Khi Reg Gmail (`gmail_reg_v10.py`)
- **Lỗi Scope Shadowing (`UnboundLocalError`)**:
  - Không bao giờ khai báo import trùng lặp bên trong thân hàm (như `from pathlib import Path` trong `persist_success_result`) khi đầu file đã có import `from pathlib import Path`. Trong Python, một câu lệnh import/gán biến bên trong hàm sẽ biến nó thành biến local của toàn bộ hàm đó, khiến các dòng gọi `Path(...)` phía trước văng lỗi `UnboundLocalError: cannot access local variable 'Path' where it is not associated with a value`.
- **Báo cáo chuỗi Watchdog (`post_noon_chain_watchdog.py`)**:
  - Bắt buộc bóc tách và hiển thị số lượng tài khoản liên kết ChatGPT thành công/thất bại ngay dưới dòng `Success` của Phase 1:
    `* ChatGPT linked: X/Y (Z fail)`
- **Canh cuốn chiếu liên kết ChatGPT giữa các ca nuôi (`watchdog_link_chatgpt_idle.py`)**:
  - Khi cần chạy bù liên kết ChatGPT trên các máy S7: BẮT BUỘC kiểm tra 3 điều kiện an toàn:
    1. Không có active device lock trên máy.
    2. Không có tiến trình TikTok/feed đang chạy trên máy.
    3. Đọc file lịch nuôi `assignment-v1-*.json` của ngày: slot nuôi tiếp theo phải cách ít nhất 25 phút để không tranh chấp thiết bị.
