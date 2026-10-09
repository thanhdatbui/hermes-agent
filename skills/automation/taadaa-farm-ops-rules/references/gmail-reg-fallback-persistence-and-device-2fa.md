# Case: Gmail Reg Single-Run Success Fallback Persistence & On-Device 2FA

## 1. Triệu chứng & Bối cảnh
- Khi chạy canary đơn lẻ hoặc kiểm thử trực tiếp `python gmail_reg_v10.py <stt> --ss` (không truyền cờ `--result-dir`):
  - Tài khoản Gmail tạo thành công 100% trên điện thoại Samsung S7 (`dumpsys account` đã có tài khoản).
  - Nhưng script bỏ qua bước lưu (`[WORKBOOK_GUARD] Skip success persistence; use --result-dir and merge step for workbook writes`).
  - Hậu quả: Mật khẩu chỉ tồn tại trong RAM của tiến trình Python, kết thúc lệnh là mất vĩnh viễn, không thể đăng nhập lại trên web hay cấu hình 2FA.

## 2. Nguyên tắc CẤM KỴ Tuyệt Đối
- **CẤM TUYỆT ĐỐI đoán mật khẩu / tự suy diễn pass theo công thức `build_password()` rồi điền bậy vào file Excel.**
  - `build_password()` có hàng chục nhánh random, không thể đoán mò.
  - Điền dữ liệu giả/sai vào workbook nguồn (`gmail_clean_v2.xlsx`) sẽ làm hỏng dữ liệu hạ tầng và dây chuyền đăng ký TikTok tiếp theo.
  - Khi phát hiện mất pass: Nhận lỗi ngay lập tức, gỡ tài khoản lỗi khỏi máy (`Settings -> Accounts -> Remove Account`), dọn Excel và cho chạy lại.

## 3. Khắc phục Cốt lõi (Vá cứng trong `gmail_reg_v10.py`)
Tại hàm `persist_success_result(acc)`:
- Nếu không có `--result-dir`:
  - Tự động lưu fallback JSON tại `RUNTIME_ROOT/success_results/machine_{stt}.success.json`.
  - Gọi trực tiếp `single_writer_workbook_update` từ `scripts.merge_success_results` để chèn thẳng record vào `D:\OneDrive\TaadaaData\kibe\gmail_clean_v2.xlsx`.
  - Không bao giờ để rơi rụng mật khẩu dù chạy bằng bất kỳ phương thức nào.

## 4. Cơ chế Bật 2FA Google Authenticator trên Thiết bị (Android S7)
- **Đặc tính Google:** Để truy cập `Xác minh 2 bước` (2-Step Verification) trong Quản lý Tài khoản Google, Google **bắt buộc xác thực lại mật khẩu**.
- **Kịch bản chuẩn:**
  1. Bật 2FA **ngay trong luồng `gmail_reg_v10.py`** sau bước 13 (khi vừa vào được Inbox và biến `acc["pass"]` còn nguyên trong bộ nhớ).
  2. Mở `Quản lý Tài khoản Google -> Bảo mật và đăng nhập -> Xác minh 2 bước`.
  3. Tự động điền `acc["pass"]` để vượt qua màn hình xác minh danh tính.
  4. Chọn `Ứng dụng Authenticator -> Không thể quét mã QR`.
  5. Trích xuất Secret Key (Base32 32 ký tự), dùng `pyotp.TOTP(secret_key).now()` sinh mã 6 số OTP xác nhận.
  6. Lưu Secret Key vào cột `2FA` của `gmail_clean_v2.xlsx`.
