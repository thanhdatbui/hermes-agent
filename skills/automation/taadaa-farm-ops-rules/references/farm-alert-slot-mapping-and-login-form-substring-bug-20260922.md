# Case Study: Phân Tích Sự Cố Báo Lệch Slot & Bug Nhận Diện Form Password Trong Ca Nuôi Acc (2026-09-22)

## 1. Lệch Mapping DB SQLite (Slot 3 ↔ Slot 7) Khiến Cảnh Báo Ảo Văng Nick
- **Hiện tượng:** Khi chạy ca nuôi acc Slot 7 trên Máy 32, hệ thống phát cảnh báo P0: `account-switcher-missing-expected: expected account not found in account switcher`.
- **Nguyên nhân cốt lõi:**
  - File workbook `Tik7.xlsx` và `taikhoan_run_safe.xlsx` định nghĩa Máy 32 chạy nick `inhhongtram71` ở Slot 7.
  - Tuy nhiên trong bảng `farm_account_info` và `account_mapping` của `tiktok_tracker.db`, tài khoản `inhhongtram71` lại bị gán nhầm vào `tik = 3` (do lịch sử hoán đổi nick trước đó).
  - Khi script đối soát danh sách tài khoản thực tế trên Switcher với SQLite, thứ tự slot bị xáo trộn kích hoạt cảnh báo mất phiên ảo. Thực tế `inhhongtram71` vẫn LIVE 100% trên app TikTok.
- **Biện pháp xử lý:**
  - Chuẩn hóa cập nhật SQLite: `UPDATE farm_account_info SET tik = 7 WHERE username = 'inhhongtram71' AND may = 32`.

## 2. Bug Trùng Substring Trong Script Login: `'nhap ma'` ↔ `'nhap mat khau'`
- **Hiện tượng:** Máy 32 thiếu nick Slot 3 (`thanhlee327`). Khi chạy `tiktok_login_v1.py` để login lại, TikTok nhận diện đúng username và mở form "Nhập mật khẩu". Nhưng script bỏ qua mật khẩu và nhảy sang mở Outlook đòi OTP rồi dừng lại.
- **Nguyên nhân:**
  - Trong `OTP_HINTS` có chuỗi `"nhap ma"`. Khi TikTok mở form "Nhập mật khẩu", chuỗi sau khi bỏ dấu là `"nhap mat khau"`. Do `"nhap ma"` là chuỗi con của `"nhap mat khau"`, nhánh OTP bị kích hoạt trước nhánh `PASSWORD_HINTS`.
- **Biện pháp xử lý:**
  - Thêm khoảng trắng thành `"nhap ma "` trong `OTP_HINTS`.
  - Luôn đưa nhánh `PASSWORD_HINTS` lên trước `OTP_HINTS` trong `drive_login_screens`.
