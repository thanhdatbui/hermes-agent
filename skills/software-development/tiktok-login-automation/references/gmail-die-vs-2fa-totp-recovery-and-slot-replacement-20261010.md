# CẤM ĐÁNH ĐỒNG GMAIL DIE = TIKTOK DIE: QUY TRÌNH PHỤC HỒI NICK 2FA TOTP & GIẢI PHÓNG TRẦN 8 NICK (2026-10-10)

## 1. NGUYÊN NHÂN SỰ CỐ & CẠM BẪY ĐÁNH ĐỒNG
- **Sai lầm phổ biến của Agent**: Khi thấy Gmail liên kết nằm trong sổ đen `gmail_die_tong.txt` hoặc bị Google vô hiệu hóa, vội vàng kết luận "tài khoản TikTok đã die", tự ý ghi đè nick mới lên Master Excel và chạy reg nick bù.
- **Thực tế kỹ thuật**:
  - TikTok hỗ trợ 2FA độc lập qua Authenticator App (TOTP secret 32 ký tự).
  - Khi đăng nhập bằng `Username + Password`, TikTok chỉ yêu cầu nhập 6 số TOTP từ ứng dụng xác thực, **HOÀN TOÀN KHÔNG gửi mã xác minh về Gmail**.
  - Các nick già (6-12 tháng tuổi, có sẵn hàng chục video, follower và view) là tài sản cực kỳ giá trị của farm. Việc tự ý khai tử các nick này và thay bằng nick non mới reg là tổn thất nghiêm trọng.

## 2. INVARIANT BẮT BUỘC TRƯỚC KHI KHAI TỬ BẤT KỲ TÀI KHOẢN NÀO
Trước khi đánh dấu một nick là `DEAD` hoặc thay thế bằng tài khoản khác:
1. **Kiểm tra trạng thái Public Profile / Snapshots**: Tra cứu bảng `snapshots` trong `tiktok_tracker.db` xem nick có trạng thái `LIVE` không.
2. **Kiểm tra khóa 2FA TOTP**: Tra cứu cột `2FA` trong Master DAT (`taikhoan_dat_v2_updated .xlsx`) hoặc backup.
3. **Quy tắc bất di bất dịch**:
   - Nếu nick CÓ khóa 2FA: **CẤM TUYỆT ĐỐI KHAI TỬ / DROP NICK**.
   - Phải giữ nguyên slot và ưu tiên nạp lại bằng `tiktok_login_v1.py` với cơ chế bypass Gmail live gate (`has_2fa_auth = True`).

---

## 3. QUY TRÌNH 4 BƯỚC THAY THẾ NICK NON, PHỤC HỒI NICK CŨ TRÊN MÁY CHẠM TRẦN 8 ACC

Khi thiết bị đã chạm trần 8 account (ví dụ: máy đang chứa nick non mới reg làm mất slot của nick cũ):

### Bước 1: Đăng xuất giải phóng slot (Active Profile hoặc Switcher)
1. Xác định nick non cần gỡ (ví dụ `@javialdzxxj`).
2. Mở app TikTok, điều hướng vào `Hồ sơ` (`Profile`).
3. Nếu nick non đang là Active Profile:
   - Tap menu 3 gạch (`tap(1005, 150)`).
   - Tap `Cài đặt và quyền riêng tư`.
   - Cuộn xuống đáy màn hình Cài đặt (vuốt `540, 1500 -> 540, 400`).
   - Tap `Đăng xuất` và xác nhận pop-up dialog.
4. Nếu nick non đang nằm trong Switcher: Chuyển sang nick đó làm active rồi thực hiện luồng logout như trên.
5. **Nghiệm thu**: Chụp ảnh Switcher, dùng WinRT OCR kiểm tra máy chỉ còn đúng **7 tài khoản chuẩn** trước khi chuyển sang Bước 2.

### Bước 2: Nạp lại nick cũ có 2FA qua `tiktok_login_v1.py`
1. Đảm bảo thông tin nick cũ trong `taikhoan_dat_v2_updated .xlsx` có đủ `ID`, `PASS`, `2FA` (Secret key).
2. Chạy:
   ```bash
   python D:/Taadaa/Tiktok_Reg/tiktok_login_v1.py <STT> --email <username> --ss
   ```
3. Script tự động phát hiện `has_2fa_auth = True`, log `[telemetry:gmail-live] action=bypass_2fa_auth`, tự sinh TOTP qua `pyotp` và điền vào form 2FA của TikTok.
4. **Lưu ý về exit code**: Nếu script log `✓ [login-success] home feed UI proof` và `[profile] handle=@<username>` nhưng báo `STOPPED: TRACKING_ROW_CHANGED`, nick **ĐÃ LOGIN THÀNH CÔNG**. Không được coi đây là lỗi login mà cần kiểm tra ngay hiện trường UI.

### Bước 3: Nghiệm thu hình ảnh thực tế (Dual Evidence Gate)
Chụp và chạy WinRT OCR trên 2 màn hình:
1. **Màn hình Profile**: Xác nhận đúng `@username`, số follow, like, video cũ.
2. **Màn hình Switcher**: Xác nhận đủ 8/8 account, nick cũ nằm trong danh sách.

### Bước 4: Đồng bộ toàn diện hệ thống quản lý & Giữ nguyên lịch sử nuôi
1. **Master DAT (`taikhoan_dat_v2_updated .xlsx`)**: Cập nhật chuẩn xác ID, PASS, 2FA, DOB, Created Date.
2. **Sổ ca đăng video (`Tik1.xlsx` đến `Tik8.xlsx`)**:
   - Cột `ID`: Gán đúng `@username`.
   - Cột `Video Đã Đăng`: Ghi nhận đúng số clip đã đăng trong quá khứ (ví dụ `21`). **CẤM reset về 0** khiến bot đăng lặp lại các clip cũ từ `1.mp4`.
3. **Sổ ca an toàn (`taikhoan_run_safe.xlsx`)**: Đồng bộ số video đã đăng tương ứng.
4. **Khôi phục trạng thái Follow (`follow_state_<m>_row_<r>.json`)**:
   - Khôi phục file state cũ từ backup (`.bak_anhdo_*`) để giữ danh sách UID đã follow.
   - Tuyệt đối không để state trắng khiến bot follow trùng lặp các nick cũ.
5. **Cơ sở dữ liệu SQLite (`tiktok_tracker.db`)**:
   - Update `farm_account_info` và `account_mapping` khớp `(may, tik, username)`.
