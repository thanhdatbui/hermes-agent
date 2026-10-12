# Hotmail Recovery Email Domain Policy & Chrome CDP Tab Management

## 1. Quy tắc Email khôi phục (Recovery Email Policy) cho Hotmail bán

### Nguyên tắc tối cao:
- **TUYỆT ĐỐI CẤM** gán email cá nhân của User (`thanhdatbui1995@gmail.com`) vào Hotmail làm mail khôi phục vì tài khoản sau này để bán cho khách. Khách không thể lấy OTP và lộ thông tin cá nhân.
- Khi mua Hotmail từ BoxTaiKhoan / SHOPCLONE7:
  - **Lô nick Zin 100% (còn skip 7 ngày)**: Xuất ra chỉ có 4 trường (`email|pass|refresh_token|client_id`), hoàn toàn **KHÔNG có mail khôi phục**.
  - **Lô nick Trusted GraphAPI**: Shop bán kèm sẵn mail khôi phục domain `@fviainboxes.com` (5 trường).

### Định dạng mail khôi phục tự sinh chuẩn:
- **Domain:** `@fviainboxes.com` (hoặc `@smvmail.com`).
- **Cấu trúc:** `<username_clean><3_random_alphanumeric>@fviainboxes.com`.
  - Ví dụ: `rencotonejcp238@hotmail.com` ➔ `rencotonejcp2389kz@fviainboxes.com`.
- **Cơ chế đọc OTP tự động qua API:**
  - `https://fviainboxes.com/messages?username={username}&domain=fviainboxes.com`
  - `https://fviainboxes.com/message?username={username}&domain=fviainboxes.com&id={id}`
  - Không cần đăng ký tài khoản trước. Khách mua nick có thể vào web `fviainboxes.com` nhập username để tự lấy OTP.

### Cơ chế tự động hóa trong `gpm_change_hotmail_security.py`:
- Trong `get_recovery_email(email)`:
  - Kiểm tra cột 5 file `gmail_clean_v2.xlsx`.
  - Nếu không tìm thấy, rỗng, `'None'`, hoặc chứa `'thanhdatbui'`, tự động sinh `<username><3rand>@fviainboxes.com`, gọi `update_excel_security_info` ghi vào Excel rồi mới sử dụng.
- **Selector tương thích giao diện modal Microsoft mới:**
  - `add_sel`: Bổ sung `button:has-text('Thêm một cách đăng nhập khác')` và `div[role='button']:has-text('Thêm một cách đăng nhập khác')`.
  - `app_sel`: Bổ sung `button:has-text('Sử dụng ứng dụng')` và `button:has-text('Use an app')`.

---

## 2. Quản lý Tab Chrome CDP & Tối ưu RAM (CDP Tab Management)

### Đóng tab cũ có mất Cookie / Phiên đăng nhập không?
- **HOÀN TOÀN KHÔNG.**
- Cookies, Session Tokens, và LocalStorage được Chrome duy trì liên tục trong file `Cookies` (SQLite) trong thư mục User Data Profile trên ổ cứng.
- Đóng tab chỉ hủy tiến trình Render Process (giải phóng 80MB–200MB RAM mỗi tab). Mở tab mới truy cập lại domain vẫn giữ nguyên phiên đăng nhập.

### Quy trình dọn tab rác qua CDP:
1. **Lấy danh sách tab:** `GET http://127.0.0.1:9222/json`
2. **Đóng tab rác:** Gửi lệnh đóng các tab không cần thiết (tab `about:blank`, tab lỗi 404, tab CapMonster/2Captcha đã dùng xong):
   - `GET http://127.0.0.1:9222/json/close/{target_id}` hoặc qua giao thức CDP: `Target.closeTarget(targetId=...)`.
3. **Kỷ luật code automation:**
   - Mọi thao tác mở tab phụ để bóc OTP / bypass link bắt buộc phải bọc trong khối:
     ```python
     new_page = context.new_page()
     try:
         # Thao tác đọc OTP...
     finally:
         new_page.close()
     ```
