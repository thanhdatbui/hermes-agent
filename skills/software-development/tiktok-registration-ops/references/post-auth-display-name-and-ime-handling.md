# TikTok Registration Post-Auth Display Name & IME Handling (2026-08-24)

## 1. Màn hình Đặt Tên / Biệt Danh (Nickname Screen - 0/30 chars)
- **Hiện tượng**: Sau khi đăng ký thành công qua Email/OTP, TikTok chuyển sang màn hình "Tên" (placeholder *"Thêm tên bạn mong muốn"*, giới hạn 0/30 ký tự, nút "Lưu" ở góc trên bên phải).
- **Quy tắc**:
  - Đặt tên tiếng Việt chuẩn âm/gần giống email nguồn qua `make_tiktok_name(email)`.
  - Bắt buộc kích hoạt và set `com.github.uiautomator/.AdbKeyboard` trước khi broadcast text tiếng Việt (`ADB_KEYBOARD_INPUT_TEXT`), tránh trường hợp gửi nhầm số STT hoặc mất ký tự do IME mặc định.
  - Bấm nút **"Lưu"** ở góc trên bên phải (tọa độ `(990, 138)` hoặc text 'Lưu').
  - Bấm **"Xác nhận"** trên dialog cảnh báo đổi tên 7 ngày nếu xuất hiện.
  - Sau khi lưu tên, chuyển sang tab **Hồ sơ** để đọc `handle` (@username) và lưu vào file tracking `taikhoan_dat_v2_updated .xlsx`.

## 2. Giao diện Gợi ý Đăng nhập nhanh (Quick Login Overlay)
- **Hiện tượng**: Khi mở app TikTok hoặc bấm "Thêm tài khoản", TikTok có thể hiện màn hình đăng nhập nhanh với avatar và nút *"Tiếp tục với tên @username_cu"*.
- **Xử lý**: Đây là cache session cũ không thuộc máy, phải bấm dòng text **"Sử dụng tài khoản khác"** ở dưới đáy màn hình để vào form đăng ký tài khoản mới.
