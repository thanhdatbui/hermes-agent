# Check Gmail Live Flow & Captcha Confirmation (add mail khoi phuc)

## Quy trình xác định Mail chết do Google reCAPTCHA:
1. Mở app Gmail trên thiết bị Android: `com.google.android.gm/.ConversationListActivityGmail`
2. Tap vào Avatar tài khoản ở góc trên bên phải.
3. Bấm vào nút **"Quản lý Tài khoản Google của bạn"** (`open_manage_for_account`).
4. Nếu phiên hết hạn, Google sẽ hiển thị thông báo:
   - *"Hoàn tất đăng nhập để tiếp tục — Đã xảy ra lỗi và bạn cần đăng nhập lại"*
5. Tap vào nút **"Đăng nhập"** (xanh) $\rightarrow$ bấm **"TIẾP THEO"**.
6. **Xác định Mail Chết:**
   - Nếu màn hình hiển thị: *"Xác minh danh tính của bạn — Xác nhận bạn không phải là rô-bốt (reCAPTCHA: Tôi không phải là người máy)"*.
   - Khẳng định mail đã bị Google khóa/yêu cầu giải captcha bot.
7. **Quy trình dọn dẹp tự động (`cleanup_blocked_captcha_account`):**
   - Xóa tài khoản Google khỏi thiết bị Android (`remove_blocked_google_account_from_device`).
   - Xóa dòng tài khoản trong file `gmail_clean_v2.xlsx`.
   - Dọn dẹp dòng tài khoản tương ứng chưa có TikTok ID trong `taikhoan_dat_v2_updated .xlsx`.
