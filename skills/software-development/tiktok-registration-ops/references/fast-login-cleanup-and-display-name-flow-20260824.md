# Xử lý Fast Login Session Rác & Đặt Tên Tiếng Việt TikTok (2026-08-24)

## 1. Fast Login One-Tap & Xóa Session Rác Không Thuộc Farm
- Khi mở TikTok gặp màn hình "Tiếp tục với tên @username":
  - Kiểm tra đối chiếu `@username` trong `taikhoan_dat_v2_updated .xlsx` và `Tik1.xlsx`.
  - Nếu không tồn tại trong farm: Bấm biểu tượng 3 chấm `...` góc trên bên phải (`com.ss.android.ugc.trill:id/yrv`) -> Chọn **"Xóa tài khoản"** (`text='Xóa tài khoản'` / `desc='Xóa'`) để xóa sạch tài khoản rác.
  - Sau đó tiếp tục bấm **"Sử dụng tài khoản khác"** (`text='Sử dụng tài khoản khác'`) để mở form đăng ký/đăng nhập tài khoản mới.

## 2. Điền Display Name Tiếng Việt Chuẩn & Sửa Lỗi IME
- Sử dụng hàm `make_tiktok_name(email)` để tạo tên tiếng Việt tương ứng gần âm với prefix email.
- Bắt buộc kích hoạt bàn phím `com.github.uiautomator/.AdbKeyboard` trước khi gõ để tránh bị gõ nhầm số/ký tự rác do bàn phím mặc định của máy (SamsungKeypad).
- Flow hoàn tất màn đặt tên:
  1. Gõ text tên tiếng Việt qua `ADB_KEYBOARD_INPUT_TEXT` (Base64).
  2. Bấm nút **"Lưu"** ở góc trên bên phải `(990, 138)` (hoặc nút **"Tiếp tục"** `(540, 1806)` tùy layout).
  3. Bấm **"Xác nhận"** `(750, 1175)` khi xuất hiện dialog giới hạn đổi tên 7 ngày.
  4. Trở về tab **"Hồ sơ"** (`(972, 1857)`) để đọc Handle/ID TikTok và lưu vào file tracking.
