# Missing Account on Device Switcher & In-Device Hotmail OTP Login Recovery (2026-10-10)

## 1. Hiện tượng & Triệu chứng
Khi nhận lệnh chuẩn hoá Avatar cho một tài khoản (ví dụ `@annapmfdh0a` Máy 44 · Tik 6):
- Sau khi trích xuất avatar, đồng bộ 2 đầu kho và cập nhật 4 tầng dữ liệu (Workbook, SQLite, state.db), runner `run_tiktok_upload_avatar.ps1` chạy độc lập văng lỗi:
  `Máy 44: LỖI (exit=2, reason=[ACCOUNT_SWITCHER_FAILED] ACCOUNT_READY verify failed: ACCOUNT_VERIFY_MISMATCH)`
- **Khám nghiệm hiện trường:**
  Mở Account Switcher trên thiết bị thật kiểm tra: TikTok trên máy mới chỉ đăng nhập 7 tài khoản (`maralbbct24`, `v.th.thoooo`, `ngongan1906`, `kellybxm52j`, `olinasbnetu`, `miumiu10434`, `oquangduong7604`), hoàn toàn **THIẾU** tài khoản mục tiêu `@annapmfdh0a` (Tik 6).

## 2. Chỉ đạo dứt khoát của Operator (Anti-Passivity)
- Khi Coordinator dừng lại báo `[BLOCKED]` vì nick chưa login trên máy, Operator lập tức ra lệnh:
  *"Thì chạy tiktok login acc đó vào"*
- **Quy tắc điều phối:** Không dừng lại ở trạng thái BLOCKED khi nick thiếu phiên login trên thiết bị nếu trong tay đã có sẵn công cụ đăng nhập tự động (`tiktok_login_v1.py` / `reconcile_tiktok_accounts.py`). Phải chủ động nối luồng login ngay trong phiên.

## 3. Bẫy Mật khẩu TikTok Thay đổi & Cứu nguy bằng Hotmail Outlook App
- **Bẫy mật khẩu:**
  Khi chạy `python D:/Taadaa/Tiktok_Reg/tiktok_login_v1.py <STT> --email <username> --ss`, script điền mật khẩu TikTok lưu trong `taikhoan_dat_v2_updated .xlsx` nhưng TikTok báo lỗi *"Mật khẩu sai"*.
- **Giải pháp bóc tách:**
  1. Kiểm tra ứng dụng Outlook trên thiết bị (`com.microsoft.office.outlook`): 100% máy farm Hotmail đều đã đăng nhập sẵn tài khoản email chính chủ (ví dụ `annapaigs47@hotmail.com`).
  2. Kích hoạt cờ `--otp-only`:
     `python D:/Taadaa/Tiktok_Reg/tiktok_login_v1.py <STT> --email <username> --otp-only --ss`
  3. Cơ chế `--otp-only`:
     - Bỏ qua form điền mật khẩu, bấm *"Quên mật khẩu?"* hoặc *"Đăng nhập bằng mã xác minh"* gửi OTP 6 số về hòm thư.
     - Script tự động đọc OTP trực tiếp từ hòm thư đến của app Outlook trên điện thoại và điền vào TikTok.
     - Login thành công mà không phụ thuộc vào mật khẩu cũ.
  4. Sau khi nick đã xuất hiện trong Switcher, quay lại chạy runner `run_tiktok_upload_avatar.ps1` để nạp avatar.
