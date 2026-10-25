---
name: tiktok-auth-recovery-and-password-sync
description: Use when TikTok login has wrong pass. Reset via token.
---

# TikTok Auth Recovery & Password Sync

## Invariant Vận Hành (User Rule 2026-10-25)
- **Tự động cứu tài khoản khi sai pass**: Khi TikTok login báo sai mật khẩu (`Mật khẩu sai`, `Bạn cần trợ giúp đăng nhập?`) hoặc tài khoản reg email-only thiếu pass: **TUYỆT ĐỐI CẤM** dừng lại báo lỗi thủ công hay đoán mò pass.
- **BẮT BUỘC 100% tự động chuyển flow cứu tài khoản**:
  1. Tap *"Bạn cần trợ giúp đăng nhập?"* / *"Quên mật khẩu?"* trên form đăng nhập TikTok.
  2. Lấy mã xác minh OTP trực tiếp từ Microsoft Graph API trên PC (cột 9-10 `gmail_clean_v2.xlsx`, CẤM mở app Outlook trên điện thoại).
  3. Hoàn tất đăng nhập vào Home feed.
  4. Kích hoạt module `login_runner.password_change`, sinh mật khẩu mới ngẫu nhiên 16 ký tự, submit vào TikTok và đồng bộ ngay lập tức vào cột PASS của `taikhoan_dat_v2_updated .xlsx` sheet `Tài Khoản`.

## Các Pitfalls Kỹ Thuật Khi Chạy `password_change.py`
1. **Biến môi trường Single-Writer Lock bắt buộc**:
   - `os.environ["TIKTOK_PASSWORD_EXPECTED_WRITER_ID"] = "password_change_runner"`
   - `os.environ["TIKTOK_PASSWORD_WRITER_ID"] = "password_change_runner"`
   - `os.environ["HOTMAIL_WORKBOOK"] = r"D:\OneDrive\TaadaaData\admin\gmail_clean_v2.xlsx"`
   - `os.environ["TIKTOK_PASSWORD_WORKBOOK"] = r"D:\OneDrive\TaadaaData\admin\taikhoan_dat_v2_updated .xlsx"`
   - `os.environ["TIKTOK_F2A_PROVIDER_ROOT"] = r"D:\Taadaa\tiktok-add-bao-mat-f2a\python_runner"` (BẮT BUỘC trỏ vào thư mục con `python_runner`, không trỏ vào repo root).
   - Nếu thiếu `TIKTOK_PASSWORD_EXPECTED_WRITER_ID`, hàm `acquire_single_writer_workbook_lock` ném `BLOCKED_EXPECTED_WRITER_ID_MISSING` và không lưu được mật khẩu mới vào workbook dù TikTok đã đổi pass thành công.
2. **Pitfall "Mật khẩu mới không thể giống mật khẩu cũ"**:
   - Khi candidate password từ journal đã được submit thành công lên TikTok ở attempt 1 nhưng tiến trình bị ngắt trước khi ghi Excel: khi chạy attempt 2 với cùng candidate password đó, TikTok sẽ hiển thị thông báo lỗi: *"Mật khẩu mới không thể giống mật khẩu cũ"*.
   - Đây là bằng chứng xác thực TikTok ĐÃ CẬP NHẬT mật khẩu mới. Phải trích xuất mật khẩu từ journal (`<account_id>.dpapi` giải mã bằng entropy `codex-tiktok-password-change-v1`) và gọi `write_password_preserving_archive` để đồng bộ vào file Excel.
3. **Popup Solver từ `automation-core`**:
   - Khi form login / switcher bị chắn bởi bottom-sheet *"Thêm số điện thoại của bạn để tăng cường bảo mật"*, tích hợp `automation_core.tiktok_popup` (rule `add_phone_number_vi`, click nút "Đóng" `bounds=[936,861][1056,993]`) để giải phóng giao diện tự động. CẤM viết parser regex riêng.
