# Quy Chuẩn Đổi Mật Khẩu Hotmail Trên GPM & Quản Trị Khóa File Excel

## 1. Bẫy Xác Nhận Đổi Mật Khẩu Hotmail & Cơ Chế Verify Bắt Buộc (Anti-False-Positive)
- **Bẫy Cookie Session của Microsoft**:
  - Khi script bấm "Sign out everywhere" (Đăng xuất khỏi mọi nơi), Microsoft **không lập tức hủy phiên cookie trên trình duyệt hiện tại** (Microsoft có thông báo rõ: "Có thể mất tới 24 giờ để đăng xuất khỏi tất cả thiết bị").
  - Do đó, nếu script redirect lại `account.microsoft.com/profile` mà không xóa cookies, trình duyệt sẽ tự động vào thẳng Profile nhờ cookie phiên cũ còn lưu. Điều này tạo ra kết quả **THÀNH CÔNG GIẢ TẠO** dù mật khẩu mới chưa hề được chấp nhận.
- **Quy Trình Kiểm Thử Xác Thực Mật Khẩu Mới (Fail-Closed Verification)**:
  1. Sau khi gửi form đổi mật khẩu (`account.live.com/password/change`).
  2. Bắt buộc gọi `context.clear_cookies()` để xóa sạch toàn bộ session lưu tạm trong profile browser.
  3. Mở trang đăng nhập `https://login.live.com/`.
  4. Điền email và **nhập MẬT KHẨU MỚI** vừa tạo vào form đăng nhập, bấm Submit.
  5. Đánh giá:
     - Nếu đăng nhập thành công vào trang quản trị $\rightarrow$ Mới được coi là ĐỔI PASS THÀNH CÔNG.
     - Nếu Microsoft báo đỏ: *"Mật khẩu đó không đúng với tài khoản Microsoft của bạn"* hoặc đòi lại mật khẩu cũ $\rightarrow$ Đổi mật khẩu THẤT BẠI.
  6. **Kỷ luật dữ liệu**: Khi thất bại, cấm ghi đè vào Master Excel (`taikhoan_dat_v2_updated .xlsx`) và cấm đổi state `DONE`.

## 2. Thử Thách OTP / Verify Identity Khi Đổi Pass Web
- Truy cập link đổi mật khẩu `account.live.com/password/change` trên web thường bị chặn ở bước "Verify your email" / "Protect your account" yêu cầu nhận mã OTP gửi về chính email đó hoặc mail khôi phục.
- **Phân loại kho dữ liệu Hotmail mua**:
  - **Lô 4 trường (Legacy)**: `email|pass|refresh_token|client_id` (ví dụ: `latest_bought_70.txt`, `hotmail_all_60_bought.txt`) $\rightarrow$ Không có mail khôi phục đi kèm; muốn lấy OTP phải đọc qua token Microsoft Graph API hoặc phiên Outlook Web đã đăng nhập.
  - **Lô 5 trường (Mới)**: `email|pass|refresh_token|client_id|recovery_email` (ví dụ: `latest_bought_8_m76_79.txt`, `single_clean_for_m34.txt`) $\rightarrow$ Cột thứ 5 là mail khôi phục (thường có đuôi `@smvmail.com`, `@fviainboxes.com`) dùng để nhận mã OTP khôi phục.

## 3. Khóa Ghi Độc Quyền File Excel (Chống Corrupt File Khi Chạy Đa Worker)
- **Nguyên nhân lỗi Corrupt ZIP**: Khi chạy supervisor đa worker (như 5 worker GPM chạy song song), nếu 2 hoặc nhiều worker cùng gọi `wb.save()` vào `taikhoan_dat_v2_updated .xlsx` tại cùng một thời điểm, file Excel (.xlsx vốn là định dạng file nén ZIP) sẽ bị lỗi ghi đè phân mảnh (Bad CRC-32 / Bad magic number / corrupt zip).
- **Giải pháp**:
  - Bọc mọi khối lệnh đọc và lưu workbook bằng cơ chế **Exclusive File Lock** (`filelock.FileLock` với timeout 30-60s).
  - Luôn kiểm tra tính toàn vẹn (integrity) của file backup trước khi thực hiện các batch cập nhật hàng loạt.
