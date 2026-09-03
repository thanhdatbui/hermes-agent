# Quy tắc đặt tên tiếng Việt & Xử lý các màn hình đăng ký TikTok (2026-08-23)

## 1. Quy tắc đặt tên hiển thị (Nickname / Display Name)
- **Yêu cầu:** Sau khi đăng ký hoặc hoàn tất hồ sơ tài khoản TikTok mới, nếu hệ thống hỏi đặt tên/biệt danh, **BẮT BUỘC đặt tên tiếng Việt** (viết hoa chữ đầu, ví dụ: "An", "Vy", "Hà", "Kiều Lâm", "Phước", "Tuấn",...).
- **Cơ chế triển khai:**
  - Tra prefix email qua `_VI_NAME_MAP` để lấy tên Việt gần âm.
  - Nếu không khớp thì lấy ngẫu nhiên 1 tên từ danh sách `_VI_NAME_FALLBACK`.
  - Luôn hoàn tất bấm "Lưu" / "Tiếp tục" và xác nhận popup đổi biệt danh 7 ngày 1 lần.

## 2. Xử lý màn hình Đăng nhập nhanh (One-tap / Quick Login)
- **Dấu hiệu:** Màn hình popup hoặc danh sách tài khoản đã lưu: *"Tiếp tục với tên @username"* hoặc hiển thị danh sách nick có sẵn.
- **Hành động:** Tap nút **"Sử dụng tài khoản khác"** ở dưới cùng màn hình để đưa về màn hình chọn phương thức đăng nhập bằng số điện thoại / email.

## 3. Quy định tài khoản không bắt tạo Mật khẩu (Passwordless)
- TikTok cho phép tài khoản xác thực qua OTP/Email đi thẳng vào trang Profile mà không yêu cầu tạo mật khẩu, hoặc cho phép ấn "Bỏ qua" ở bước tạo pass.
- Các tài khoản này vẫn được ghi nhận **SUCCESS**.
- Trong file tracking `taikhoan_dat_v2_updated .xlsx`, cột `PASS` để trống (`None`).

## 4. Quản lý kho mail `gmail_clean_v2.xlsx`
- `gmail_clean_v2.xlsx` là **kho mail live**.
- Tuyệt đối **không tự ý xóa email** chỉ vì đã đăng ký TikTok thành công.
- Chỉ xóa email khỏi kho khi quét check-live phát hiện email đã die/bị gỡ khỏi thiết bị **VÀ email đó chưa từng có ID TikTok trong bảng tracking**.
