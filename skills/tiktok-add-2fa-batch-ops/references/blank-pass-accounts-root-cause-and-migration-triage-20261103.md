# Triage: 252 Tài Khoản Trống Mật Khẩu (212 Admin + 40 Kibe) Trên SQLite SSOT

## Hiện Tượng & Căn Nguyên Lịch Sử
- Khi kiểm tra `farm_master.db` (bảng `tiktok_accounts`), phát hiện 252 tài khoản có `password IS NULL OR password = ''` (212 nick thuộc `tiktok_admin` và 40 nick thuộc `tiktok_kibe`). Trong đó có 141 tài khoản cụm Admin đã có sẵn 2FA secret nhưng cột mật khẩu vẫn trống.
- Nguyên nhân: Đây là dữ liệu lịch sử kế thừa trực tiếp từ 2 file Excel nguồn (`admin/taikhoan_dat_v2_updated .xlsx` dòng 67, 171, 249... và `kibe/...` dòng 25, 38...). Các tài khoản này được tạo từ các đợt đăng ký tự động đời cũ qua Hotmail/SSO/Cookie, người dùng đăng nhập bằng token/email mà chưa từng thực hiện bước thiết lập mật khẩu tĩnh (Set Password) trên TikTok.

## Cạm Bẫy Hậu Kiểm Trong Batch 2FA
- Khi chạy batch 2FA ban đêm (`run_batch_live_2fa.py`), các tài khoản `has_2fa=True` và `password=NULL` được xếp vào diện `password_only=True` để bổ sung mật khẩu.
- Cạm bẫy: Hàm hậu kiểm `_verification()` nếu kiểm tra cứng `password_saved = not password_is_blank(...)` sẽ đánh trượt toàn bộ các tài khoản vốn dĩ không có mật khẩu thành `POST_SUCCESS_VERIFICATION_FAILED`.
- Quy chuẩn nghiệm thu: Phải chấp nhận `password_ok = password_saved or target.blank_pass` khi tài khoản chỉ chạy kích hoạt 2FA mà không hoàn tất đặt mật khẩu.

## Cơ Chế Tự Động Bổ Sung Mật Khẩu (Password Rotation & Set Password)
- Khi nick được kích hoạt trong ca chạy, nếu thuộc diện `blank_pass`, worker `run_capture_phase_b.py` thông qua `LivePhaseBAdapter.ensure_account_password_saved()` sẽ:
  1. Điều hướng vào Cài đặt -> Tài khoản -> Mật khẩu.
  2. Vượt qua thử thách xác minh danh tính (Identity Challenge) qua mã OTP gửi về Hotmail (đọc tự động qua Graph API).
  3. Sinh mật khẩu chuẩn entropy farm và submit trên TikTok UI.
  4. Ghi nhận mật khẩu mới trực tiếp vào SQLite SSOT (`UPDATE tiktok_accounts SET password = ? WHERE username = ?`).
