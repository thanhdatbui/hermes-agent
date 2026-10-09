# Quy Chuẩn Đổi Mật Khẩu Hotmail Qua GPM & Bảo Toàn Excel Master

## 1. Kiểm Chứng Đổi Mật Khẩu Hotmail Trên GPM (Chống Báo Cáo Ảo)
- **Bẫy Session của Microsoft**:
  - Khi bấm submit form đổi mật khẩu hoặc click "Sign out everywhere" (Đăng xuất khỏi mọi nơi), Microsoft **KHÔNG** hủy cookie/session của trình duyệt hiện tại ngay lập tức (Microsoft nêu rõ có thể mất tới 24h).
  - Do đó, việc trình duyệt tự động redirect vào `account.microsoft.com/profile` hoặc `account.microsoft.com/` **KHÔNG CHỨNG MINH** mật khẩu đã được đổi thành công, vì cookie cũ vẫn còn hiệu lực.
- **Quy trình Verify BẮT BUỘC (Fail-Closed Verification)**:
  1. Sau khi submit form đổi mật khẩu trên trang `account.live.com/password/change`.
  2. Bắt buộc gọi `context.clear_cookies()` để xóa sạch toàn bộ session lưu tạm.
  3. Mở trang đăng nhập `https://login.live.com/`.
  4. Điền email và **GÕ MẬT KHẨU MỚI** vừa tạo vào form đăng nhập, sau đó bấm Submit.
  5. **Đánh giá kết quả thực tế**:
     - Nếu Microsoft chấp nhận mật khẩu mới và đăng nhập thành công vào trang quản lý $\rightarrow$ Xác nhận ĐỔI MẬT KHẨU THÀNH CÔNG.
     - Nếu Microsoft báo đỏ: *"Mật khẩu đó không đúng với tài khoản Microsoft của bạn"* hoặc đòi lại mật khẩu cũ $\rightarrow$ Đổi mật khẩu THẤT BẠI.
  6. **Kỷ luật dữ liệu**: Khi đổi mật khẩu thất bại, TUYỆT ĐỐI CẤM ghi đè vào Master Excel (`taikhoan_dat_v2_updated .xlsx`) và CẤM cập nhật trạng thái `DONE` trong tracker/supervisor state.

## 2. Thử Thách OTP / Verify Identity Khi Đổi Pass
- Khi truy cập link đổi mật khẩu `account.live.com/password/change` trên web, Microsoft thường yêu cầu xác minh bảo mật bổ sung ("Verify your email" / "Protect your account").
- Microsoft sẽ yêu cầu gửi mã OTP 7 số về chính email đó hoặc về **Email Khôi Phục (Recovery Email)** đã liên kết.
- **Phân loại kho dữ liệu Hotmail mua**:
  - **Lô 4 trường (Legacy)**: `email|pass|refresh_token|client_id` (ví dụ: `latest_bought_70.txt`, `hotmail_all_60_bought.txt`) $\rightarrow$ Không có mail khôi phục đi kèm; muốn lấy OTP phải đọc qua token Microsoft Graph API hoặc phiên Outlook Web đã đăng nhập.
  - **Lô 5 trường (Mới)**: `email|pass|refresh_token|client_id|recovery_email` (ví dụ: `latest_bought_8_m76_79.txt`, `single_clean_for_m34.txt`) $\rightarrow$ Cột thứ 5 là mail khôi phục (thường có đuôi `@smvmail.com`, `@fviainboxes.com`) dùng để nhận mã OTP khôi phục.

## 3. Khóa Ghi Độc Quyền File Excel (Chống Corrupt File Khi Chạy Đa Worker)
- **Nguyên nhân lỗi Corrupt ZIP**: Khi chạy supervisor đa worker (như 5 worker GPM chạy song song), nếu 2 hoặc nhiều worker cùng gọi `wb.save()` vào `taikhoan_dat_v2_updated .xlsx` tại cùng một thời điểm, file Excel (.xlsx vốn là định dạng file nén ZIP) sẽ bị lỗi ghi đè phân mảnh (Bad CRC-32 / Bad magic number / corrupt zip).
- **Giải pháp**:
  - Bọc mọi khối lệnh đọc và lưu workbook bằng cơ chế **Exclusive File Lock** (dùng `filelock.FileLock` với timeout hợp lý, ví dụ 30-60s).
  - Luôn kiểm tra tính toàn vẹn (integrity) của file backup trước khi thực hiện các batch cập nhật hàng loạt.
