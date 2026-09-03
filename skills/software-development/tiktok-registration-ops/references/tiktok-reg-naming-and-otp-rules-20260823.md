# TikTok Registration Lessons & Rules (2026-08-23)

## 1. Quy tắc Đặt tên Hiển thị (Display Name / Nickname)
- **BẮT BUỘC đặt tên tiếng Việt:** Khi gặp flow "Tạo tên" / "Thêm tên" / "Đặt biệt danh" sau khi reg, luôn sử dụng tên tiếng Việt chuẩn (viết hoa chữ đầu: *An, Vy, Hà, Linh, Minh, Tuấn, Dũng, Kiều Lâm, v.v.*).
- Tuyệt đối không để nguyên prefix tiếng Anh/ký tự rác từ local part của hotmail/outlook nước ngoài (ví dụ: `Anderus`, `Jasome`, v.v.).

## 2. Xử lý Màn hình Đăng nhập Nhanh (One-Tap / Fast Login)
- Khi mở TikTok gặp màn hình "Tiếp tục với tên @username", bấm vào liên kết **"Sử dụng tài khoản khác"** ở dưới đáy màn hình để vào giao diện chọn phương thức đăng nhập bằng Email/SĐT.

## 3. Tài khoản Bỏ qua Mật khẩu (Passwordless / OTP-Only)
- Khi reg TikTok bằng OTP, TikTok thường cho phép bỏ qua bước tạo mật khẩu (vào thẳng Profile hoặc có nút "Bỏ qua").
- Trong tracking workbook (`taikhoan_dat_v2_updated .xlsx`), cột `PASS` để trống (`None`), trạng thái vẫn ghi nhận là `SUCCESS`.

## 4. Quản lý Kho `gmail_clean_v2.xlsx` vs Tracking Workbook
- `gmail_clean_v2.xlsx` là **kho mail live**, CẤM xóa mail live chỉ vì đã reg TikTok xong.
- Check-live / quarantine: chỉ xóa mail die khi CHƯA có ID TikTok trong tracking. Nếu ĐÃ có ID TikTok trong tracking thì BẮT BUỘC GIỮ.
- ID TikTok và email đăng ký bắt buộc phải nằm trên cùng một hàng trong bảng tracking.
