# Case Study & Technical Pitfalls: Wrong Password Login Recovery (M211 - 2026-10-25)

## 1. Context & Incident
- **Thiết bị:** Máy M211 (Serial: `ce051605c8c1d61e04`)
- **Tài khoản:** `khanhcoi6114` (Email: `phillipkerredxa@hotmail.com`, Row 362 sheet `Tài Khoản`).
- **Hiện tượng:** Khi nạp tài khoản vào máy, TikTok báo lỗi đỏ *"Mật khẩu sai"*. Mật khẩu trong workbook từ ngày tạo (12/09/2026) không khớp với server TikTok (do nick reg email-only qua app Outlook không có bước tạo pass thật).

## 2. Recovery Workflow
1. **Bỏ qua đoán pass:** Không retry password. Chuyển sang flow cứu tài khoản bằng OTP.
2. **Microsoft Graph API OTP Reader:**
   - Đọc `refresh_token` và `client_id` từ `gmail_clean_v2.xlsx`.
   - Gọi trực tiếp Microsoft Graph API để lấy OTP 6 số trên PC.
   - Tuyệt đối không bật app Outlook trên thiết bị.
3. **Change Password & Sync:**
   - Chạy `login_runner.password_change` trên máy thật.
   - Sinh mật khẩu 16 ký tự an toàn.
   - Thiết lập các biến môi trường single-writer workbook lock:
     - `TIKTOK_PASSWORD_EXPECTED_WRITER_ID="password_change_runner"`
     - `TIKTOK_PASSWORD_WRITER_ID="password_change_runner"`
   - Ghi mật khẩu mới vào cột PASS của `taikhoan_dat_v2_updated .xlsx` qua `write_password_preserving_archive`.
