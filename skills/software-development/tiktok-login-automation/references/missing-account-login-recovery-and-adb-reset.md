# Missing Account Login Recovery & Switcher Mismatch Resolution

## 1. Bối cảnh & Hiện tượng
Khi chạy automation TikTok (Upload video, lướt Feed, dưỡng nick), hệ thống gặp trường hợp:
- `ACCOUNT_VERIFY_MISMATCH`: Trên app TikTok đang mở nick khác (ví dụ: nick Tik 7) so với nick yêu cầu trong Excel (Tik 4).
- `account-switcher-missing-expected`: Account Switcher mở bottom sheet thành công nhưng không tìm thấy username đích trong danh sách tài khoản đã đăng nhập trên máy.

## 2. Kỷ luật hành động: Tự động gọi Login bù (CẤM ngồi im báo lỗi)
1. **Tra cứu thông tin tài khoản**:
   - Mở file tracking: `D:/OneDrive/TaadaaData/kibe/taikhoan_dat_v2_updated .xlsx` hoặc `Tik{N}.xlsx`.
   - Lấy `email`, `id` (username), `stt` (số máy).
2. **Kích hoạt công cụ Login chuyên dụng (`tiktok_login_v1.py`)**:
   ```bash
   python D:/Taadaa/Tiktok_Reg/tiktok_login_v1.py <STT> --email <USERNAME_HOAC_EMAIL> --ss
   ```
   - Script tự động:
     - Mở app TikTok, vào Profile, mở Account Switcher.
     - Nếu nick đã có sẵn trong danh sách ngầm: Switch thẳng vào nick.
     - Nếu nick chưa có: Điền username/email, nhập password, xử lý 2FA TOTP hoặc đọc OTP mail Graph API tự động.
3. **Phục hồi ADB Daemon khi bị Timeout**:
   - Nếu lệnh ADB bị kẹt / timeout (phổ biến sau nhiều phiên automation nặng):
     - Chạy `adb kill-server` && `adb start-server` để reset daemon sạch sẽ.
     - Kiểm tra trạng thái máy: `adb devices` và `getprop sys.boot_completed`.
4. **Tiếp tục luồng nghiệp vụ**:
   - Sau khi `tiktok_login_v1.py` hoàn tất (`exit code 0`), tiếp tục ngay quy trình upload video / feed session.
