# Gmail Liveness Verification Trap: On-Device vs checkmail.live (2026-09-12)

## Context & Incident
Trong ca chạy Reg TikTok ban đêm (`_run_all_targets.py` / `social_reg_v1.py`), 16/23 máy fail với lỗi không lấy được OTP tại bước 7c (`[7c][BLOCKED_GMAIL_OTP_TIMEOUT] ... TIMEOUT at search loop after 150s` hoặc `Không lấy được OTP từ inbox`).
Coordinator ban đầu báo cáo "Gmail vẫn sống nhưng TikTok không gửi OTP" dựa trên kết quả của on-device helper `check_google_account_health_from_gmail()`.

## Root Cause of False Positive "LIVE"
- Helper `check_google_account_health_from_gmail` trên thiết bị chỉ kiểm tra các popup UI hiển thị ngay lập tức (như Google CAPTCHA đòi giải hoặc nút Sign-in relogin).
- Khi tài khoản Google bị **vô hiệu hóa/khóa ngầm từ phía backend Google**, app Gmail trên máy Android không thể sync thư mới về inbox (hộp thư tìm kiếm trống trơn dù đã pull-to-refresh 2 lần), nhưng Google không chủ động văng dialog lỗi ra màn hình.
- Do đó, script trả về `reason=target_account_not_verified` và ngộ nhận sai rằng "Google Account vẫn LIVE, do TikTok không phát OTP".

## Bắt buộc: Kiểm tra bằng checkmail.live
Khi kiểm tra độc lập 17 tài khoản Gmail đó qua công cụ `checkmail.live` (sử dụng Playwright persistent context + proxy mobile Farm `mobi1` từ repo `site ban hang clone` / `shop-stock-checklive`), **16/17 tài khoản thực tế đã CHẾT (`[die]`)**.

## Quy tắc thực thi (Mandatory Rule)
1. **CẤM TUYỆT ĐỐI** dựa vào on-device health check để kết luận tài khoản Gmail còn sống khi OTP không về.
2. **BẮT BUỘC** dùng công cụ `checkmail.live` qua Playwright / Chrome CDP kèm mobile proxy `mobi1` (`http://test.taadaa.click:5101`, auth `mobi1:TaadaaMobi#2026!`) để phân định Live vs Die chính xác.
3. Trước khi kích hoạt các mẻ batch reg TikTok số lượng lớn, phải quét danh sách Gmail trong kho nguồn `gmail_clean_v2.xlsx` qua `checkmail.live` để dọn sạch tài khoản `[die]`.
