# Gmail OTP Timeout & checkmail.live Diagnostics (Tiktok_Reg)

## 1. Hiện trạng & Triệu chứng
Khi chạy batch reg TikTok với target là Gmail (ví dụ: `[PREFLIGHT REG BÙ ROW 7]`), các máy gặp lỗi:
`[7c][BLOCKED_GMAIL_OTP_TIMEOUT] <email>: [otp-gmail] TIMEOUT at ... after 150s for <email>`

## 2. Điểm nghẽn cấu trúc trong code (`social_reg_v1.py`)
1. **Không có Preflight check:** Runner (`_run_all_targets.py`) đọc target từ source/workbook và đẩy thẳng vào TikTok mà không kiểm tra tình trạng live/die của tài khoản Gmail qua web trước.
2. **Crash trước khi chạm Fallback check live:**
   - Trong `social_reg_v1.py` (dòng 8093–8113), đã có code fallback gọi `check_gmail_is_live(email)` qua `D:/Taadaa/tools/check_gmail_live_fast.py`.
   - Tuy nhiên, khi `_try_get_otp_gmail_app()` không tìm thấy mã trong vòng 150s (`GMAIL_OTP_ATTEMPT_TIMEOUT`), hàm tự raise `AutomationStepTimeout`.
   - Khối try-except ở bước 7c (dòng 7971 và 8082) bắt `AutomationStepTimeout` và lập tức quăng `RuntimeError(f"[7c][BLOCKED_GMAIL_OTP_TIMEOUT] {email}: {e}")` làm dừng lượt reg của máy.
   - Kết quả: Code **chưa bao giờ chạm tới được đoạn check live** ở dòng 8093.

## 3. Tool có sẵn trong hệ thống
- File: `D:/Taadaa/tools/check_gmail_live_fast.py`
- Cơ chế: Dùng Playwright với Chromium GPM, định tuyến qua proxy mobi1 (`http://test.taadaa.click:5101`), kiểm tra trực tiếp trạng thái live/die trên `https://checkmail.live/`.
- CLI: `python D:/Taadaa/tools/check_gmail_live_fast.py <email>` (exit code 0 = LIVE, exit code 1 = DIE).

## 4. Quy trình xử lý tối ưu
1. **Tiền kiểm tra (Preflight check):**
   - Trước khi dispatch S7 vào TikTok, kiểm tra danh sách target Gmail bằng `check_gmail_is_live`.
   - Mail DIE: loại khỏi hàng đợi, đánh dấu / xóa khỏi source ngay để tránh việc máy mở TikTok và treo chờ 150s.
2. **Xử lý ngoại lệ tại chỗ (Step 7c):**
   - Trong `social_reg_v1.py`, tại khối `except (AutomationStepTimeout, AdbCommandTimeout)`, cần gọi `check_gmail_is_live(email)` trước khi re-raise.
   - Nếu DIE: Xóa khỏi source (`remove_captcha_dead_email_from_source`), đánh dấu DIE trong audit pending, giải phóng máy.
   - Nếu LIVE: Báo cáo rõ Gmail vẫn LIVE nhưng không nhận được thư OTP từ TikTok (hoặc app Gmail trên máy kẹt sync/chưa tải mail mới).
