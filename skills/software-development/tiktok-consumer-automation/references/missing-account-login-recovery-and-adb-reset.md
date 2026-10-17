# Account Reconcile & Missing Login Recovery Discipline

## 1. Bối cảnh & Hiện tượng
Khi chạy quy trình upload video (`tiktok-video`) hoặc nuôi nick (`tiktok-luot nuoi acc`), máy có thể gặp lỗi:
- `ACCOUNT_VERIFY_MISMATCH`: Trên app TikTok đang mở nick khác (ví dụ: nick Tik 7) so với nick yêu cầu trong Excel (Tik 4), hoặc nick đích chưa được thêm vào thiết bị.
- `account-switcher-missing-expected`: Account Switcher mở thành công nhưng không tìm thấy username đích trong danh sách tài khoản đã đăng nhập.

## 2. Quy tắc xử lý: Cấm ngồi im báo lỗi, tự động gọi Login bù
Khi gặp lỗi thiếu account hoặc switcher không có nick:
1. **Tra cứu tọa độ tài khoản trong tracking**:
   - Mở file Excel tổng hợp `D:/OneDrive/TaadaaData/kibe/taikhoan_dat_v2_updated .xlsx` hoặc file cấu hình Tik tương ứng (`Tik{N}.xlsx`).
   - Lấy `email`, `id`, `stt` (số máy).
2. **Kích hoạt công cụ Login chuyên dụng (`tiktok_login_v1.py`)**:
   - Sử dụng script độc lập:
     ```bash
     python D:/Taadaa/Tiktok_Reg/tiktok_login_v1.py <STT> --email <USERNAME_HOAC_EMAIL> --ss
     ```
   - Script tự động:
     - Mở app TikTok, vào Profile, mở Account Switcher.
     - Nếu nick đã có sẵn trong danh sách ngầm: Switch thẳng vào nick.
     - Nếu nick chưa có: Tự động chuyển qua luồng nạp nick, nhập OTP/2FA TOTP (bypass mail nhờ secret key hoặc đọc mail Graph).
3. **Phục hồi ADB Daemon khi bị Timeout**:
   - Nếu lệnh ADB bị kẹt / timeout (thường xảy ra sau nhiều phiên automation nặng hoặc switch profile):
     - Chạy `adb kill-server` && `adb start-server` để reset daemon sạch sẽ.
     - Kiểm tra trạng thái máy: `adb devices` và `getprop sys.boot_completed`.
4. **Tiếp quản và Upload Video**:
   - Sau khi `tiktok_login_v1.py` trả về exit code 0 và xác nhận nick đã nằm ở Profile (`post-login` / `profile-ready`), ngay lập tức kích hoạt lại canary hoặc batch upload video tương ứng.
