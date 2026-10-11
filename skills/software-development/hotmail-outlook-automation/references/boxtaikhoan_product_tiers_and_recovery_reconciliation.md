# BoxTaiKhoan Product Tiers & Hotmail Recovery Reconciliation

## Background & Problem
Khi mua tài khoản Hotmail từ bên thứ ba (đặc biệt là các shop chạy mã nguồn SHOPCLONE7 như `boxtaikhoan.com`), có sự phân tách rõ rệt giữa các dòng sản phẩm mà hệ thống tự động phải phân loại chính xác, tránh gây lỗi giả `BLOCKED` hàng loạt.

## 1. Hai dòng sản phẩm Hotmail chính trên BoxTaiKhoan
1. **Dòng Hotmail Zin (OAuth2 Zin 100% / Còn Skip 7 Ngày, ~393đ - điển hình batch tháng 8/2026):**
   - **Định dạng dữ liệu trả về (4 trường):** `email|mail_pass|refresh_token|client_id`.
   - **Đặc điểm:** Tài khoản trắng tinh, chưa từng add mail khôi phục hay số điện thoại.
   - **Mục đích sử dụng:** Mua về để nuôi, login qua GPM, sau đó chạy tiến trình `CHANGE_INFO` để gán mail khôi phục chính chủ của farm (`thanhdatbui1995@gmail.com`).
   - **Cạm bẫy nghiêm trọng (False-BLOCKED bug):** 
     - Script kiểm tra an toàn `gpm_change_hotmail_security.py` gọi `get_recovery_email(email)`. Nếu không thấy mail khôi phục trong `gmail_clean_v2.xlsx`, script liền ném lỗi `[-] Không tìm thấy mail khôi phục trong DB/Excel cho {email}` và đánh dấu tài khoản là `BLOCKED`.
     - **Quy tắc chuẩn:** Acc Zin bản chất không có mail khôi phục cũ. Trong flow `CHANGE_INFO`, nếu tài khoản chưa có recovery mail thì KHÔNG ĐƯỢC BLOCK, mà phải trực tiếp tiến hành thêm mail khôi phục đích (`thanhdatbui1995@gmail.com`) và nghe ngóng OTP từ IMAP Gmail chính chủ.

2. **Dòng Hotmail kèm Mail Phụ / Domain riêng (~167đ - điển hình batch tháng 9/2026):**
   - **Định dạng dữ liệu trả về (5 trường):** `email|mail_pass|refresh_token|client_id|recovery_email`.
   - **Đặc điểm:** Mail khôi phục thường là domain ảo/tạm (`@fviainboxes.com`, `@smvmail.com`...).
   - **Cơ chế đọc OTP:** Sử dụng API chuyên dụng (như `mail_domain_otp_helper.py` với endpoint `https://fviainboxes.com/messages?username={u}&domain={d}`).
   - **Quy trình:** Tài khoản này đã có mail khôi phục bên thứ ba; khi thực hiện `CHANGE_INFO`, hệ thống phải vượt qua thử thách bảo mật bằng mail cũ này trước khi gỡ hoặc đổi sang mail farm.

## 2. Cạm bẫy cảnh báo "Lưu ý lưu đơn hàng quá 3 ngày" trên ShopClone7
- Giao diện client của ShopClone7 luôn hiển thị thông báo cố định:
  > *"Lịch sử đơn hàng trên hệ thống chỉ được lưu trong 3 ngày kể từ thời điểm mua. Sau thời gian này, đơn hàng dữ liệu có thể bị xóa và không thể khôi phục."*
- **Quy tắc điều phối:**
  - TUYỆT ĐỐI KHÔNG tin lời cảnh báo này mà vội kết luận đơn hàng cũ đã bị xóa.
  - Thực tế máy chủ vẫn lưu trữ đầy đủ dữ liệu của các đơn hàng cũ (tháng trước, 1-2 tháng trước).
  - Luôn chủ động điều hướng URL theo tham số phân trang (`/client/product-orders?page=N`) hoặc tra cứu trực tiếp theo mã đơn hàng `trans_id` để tải file `.txt` gốc về đối soát.

## 3. Tự động hóa tải file và xử lý hộp thoại "Save As" trên Windows
- Khi điều khiển trình duyệt tải file đơn hàng qua Web UI, Chrome có thể bật hộp thoại native Windows `Save As` (TitleBar "Save As", Class `#32770`).
- Nếu modal này treo, dùng lệnh Win32 Ctypes PostMessage để xác nhận lưu nhanh:
  ```python
  import ctypes
  user32 = ctypes.windll.user32
  # Gửi WM_COMMAND với IDOK (1) để xác nhận Save
  user32.PostMessageW(hwnd_save_as, 0x0111, 1, 0)
  ```
