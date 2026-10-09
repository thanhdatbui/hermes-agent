# Gmail DIE Cleanup on Device & Checkmail.live Web Verification (2026-09-12)

## 1. Bản chất sự cố Gmail DIE ngầm & Lệch chẩn đoán
- **Lỗ hổng On-device health check:** `check_google_account_health_from_gmail` trên thiết bị chỉ phát hiện tài khoản lỗi khi Google Account hiện popup CAPTCHA / Re-login bắt buộc trên UI. Khi Google khóa/disable tài khoản từ backend, app Gmail vẫn mở bình thường nhưng hộp thư ngừng đồng bộ và không nhận được email/OTP mới.
- **Hậu quả:** Script automation (`social_reg_v1.py`) ngộ nhận Gmail vẫn LIVE và đổ thừa cho TikTok không gửi OTP hoặc lỗi mạng.
- **Quy tắc bắt buộc:** Mọi tác vụ kiểm tra trạng thái Gmail khi OTP không về **BẮT BUỘC dùng web `checkmail.live`** (qua Playwright và proxy mobile farm `mobi1` tại `D:/Taadaa/tools/check_gmail_live_fast.py`).

## 2. Quy trình xử lý kép (Workbook + Thiết bị Android)
Khi `checkmail.live` xác nhận một Gmail bị `[die]`:
1. **Xóa khỏi kho nguồn:** Gọi `remove_captcha_dead_email_from_source(email)` xóa dòng tương ứng trong `D:/OneDrive/TaadaaData/kibe/gmail_clean_v2.xlsx` (có backup trước khi xóa).
2. **Ghi log audit:** Lưu thông tin vào sheet `Audit Pending` trong `taikhoan_dat_v2_updated .xlsx`.
3. **Đánh dấu danh sách máy cần dọn:** Ghi nhận email DIE vào `D:/Taadaa/runtime/kibe/gmail_die_by_machine.json` theo từng STT máy.
4. **Gỡ tài khoản trên thiết bị:** Trước khi ca reg mới bắt đầu, script đọc `gmail_die_by_machine.json`, kiểm tra `dumpsys account` trên máy và kích hoạt `remove_device_google_account.py` (vào `Settings -> Accounts -> Google -> Remove account`) để gỡ sạch tài khoản DIE, tránh nghẽn slot và tránh việc app Gmail sync nhầm profile lỗi.

## 3. Nguyên nhân tỷ lệ DIE cao ở dàn Gmail mới reg (Tháng 9/2026 ~ 70%)
1. **Thiếu Email khôi phục (Recovery Email):** Các tài khoản reg mới trong `gmail_reg_v10.py` không được gán recovery email (`mail khôi phục` để trống). Google AI đánh dấu tài khoản rủi ro cao (ghost account) và quét khóa sau 3–5 ngày.
2. **Trùng subnet IP / Thiếu xoay IP:** Các máy farm chạy batch ban đêm từ cùng một cổng proxy/IP mà không có độ giãn cách hoặc không kích hoạt đổi IP (`recreate modem`) trước mỗi lượt reg.
3. **Entropy profile thấp:** Cấu trúc họ tên + năm sinh bị nhận diện pattern tự động.
