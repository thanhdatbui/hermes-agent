# Quy Tắc Điều Tra & Fix Lỗi Account Switcher Missing & Upload Watchdog Premature Closure

## 1. Bản chất sự cố Watchdog đóng báo cáo sớm gây False-Positive Upload Error
- **Triệu chứng:** Watchdog báo `Đăng Video: Success (37), Lỗi script/xác minh (18)` trong khi thực tế 49 máy đã đăng thành công.
- **Nguyên nhân gốc:** 
  - `is_feed_runner_active()` chỉ bắt các pattern feed (`multi_machine_feed_session`, `run_tiktok.py`, `tiktok_runner.py`) nhưng thiếu các tiến trình đăng video ngầm (`run_post.py`, `tiktok_workflow`, `tiktok_upload`).
  - Khi 80 máy xong bước Feed, watchdog kiểm tra thấy `runner_patterns` không còn match trong khi các subprocess upload đang đăng dở.
  - Các máy chưa kịp ghi `upload_result.json` bị logic fallback của watchdog đánh nhầm thành `up_error`.
- **Giải pháp chuẩn:**
  - Luôn đưa đầy đủ `run_post.py`, `tiktok_workflow`, `tiktok_upload` vào `runner_patterns`.
  - Giữ invariant: Nếu runner/uploader còn chạy (`runner_busy=True`) và chưa hoàn tất máy, watchdog TUYỆT ĐỐI không chốt sớm.

## 2. Bản chất sự cố 5 máy "Thiếu Account" (ACCOUNT_MISSING)
- **Triệu chứng:** Runner dừng ở `profile_preflight` với lỗi `manual-needed:account-switcher-missing-expected: expected account not found in account switcher`.
- **Nguyên nhân 1 (Lệch Display Name vs Username):**
  - Trong workbook, target account là username `@thu.trangg584`, `@hng.th.v713`, `@ngc.anh.phm33`.
  - Trên popup Account Switcher thật của TikTok, tài khoản hiển thị dạng **Display Name** (ví dụ: `Trang Le`, `Hong Vu`, `Anh Pham`) thay vì username.
  - Bộ so khớp identity của `account_switcher.py` (`matches_switcher_identity`) nếu chỉ so khớp chuỗi username sẽ trả về `False`, gây ra báo nhầm nick bị mất.
- **Nguyên nhân 2 (Mất nick thật):**
  - Như M72: Nick `@m.ngc4624` thực sự bị logout khỏi Switcher, chỉ còn 7 nick khác.
- **Quy tắc Vận Hành & Thiết Kế Alert Cần Khắc Phục (User yêu cầu):**
  - **Lỗi thiếu account là LỖI NGHIÊM TRỌNG CẦN FIX GẤP**: Phải được gửi ngay về kênh **Farm Alert Telegram** (Banner Đỏ / Alert riêng biệt).
  - Không được nuốt alert qua cơ chế `_should_suppress_immediate_machine_alert` khi gặp lỗi `ACCOUNT_MISSING`.
  - Báo cáo Watchdog phiên phải bóc tách riêng danh sách máy bị thiếu/lệch nick để kỹ thuật nạp lại nick hoặc cập nhật Display Name ngay, không được gộp chung vào danh sách `Fail (N)`.
