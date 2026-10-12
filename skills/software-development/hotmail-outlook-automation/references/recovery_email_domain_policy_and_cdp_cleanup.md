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
  - Nếu không tìm thấy, rỗng, `'None'`, hoặc chứa `'thanhdatbui'`, tự động sinh `<username><3rand>@fviainboxes.com` làm mail dự kiến.
- **QUY TẮC BẤT BIẾN: CẤM ĐIỀN EXCEL / BÁO XONG TRƯỚC KHI ADD MICROSOFT THỰC TẾ:**
  - Tuyệt đối KHÔNG ghi mail khôi phục vào Excel như thể đã hoàn tất khi bot chưa thực sự chạy add trên Microsoft. Điền trước sẽ tạo dữ liệu "khống", khi bán cho khách Microsoft không thể gửi OTP về mail đó.
  - Mail khôi phục chỉ được ghi nhận chính thức vào `gmail_clean_v2.xlsx` Cột 5 **SAU KHI**:
    1. Bot Playwright điều hướng tới `account.live.com/proofs/manage/additional`.
    2. Mở modal `Thêm một cách đăng nhập khác` -> Chọn `Gửi mã qua email`.
    3. Điền địa chỉ mail domain dự kiến và bấm Tiếp theo.
    4. Gọi API `fetch_recovery_email_otp(rec_email)` lấy OTP 6 số từ `fviainboxes.com`.
    5. Điền OTP và xác nhận thành công trên giao diện Microsoft.
- **BỎ QUA CẢNH BÁO "CHỈ LƯU ĐƠN 3 NGÀY" TRÊN BOXTAIKHOAN:**
  - Cảnh báo "Chỉ lưu đơn hàng trong 3 ngày..." là thông báo tĩnh của SHOPCLONE7. Database thực tế vẫn lưu toàn bộ đơn hàng đã thanh toán từ nhiều tháng trước.
  - Phải chủ động duyệt qua pagination (các trang cũ) hoặc dùng URL lọc để tải file đơn hàng, cấm dừng tìm kiếm với lý do "quá 3 ngày".
- **Selector tương thích giao diện modal Microsoft mới:**
  - `add_sel`: Bổ sung `button:has-text('Thêm một cách đăng nhập khác')` và `div[role='button']:has-text('Thêm một cách đăng nhập khác')`.
  - `app_sel`: Bổ sung `button:has-text('Sử dụng ứng dụng')` và `button:has-text('Use an app')`.
  - `email_opt`: Dùng `text='Gửi mã qua email'`, `div:has-text('Gửi mã qua email')` để trigger chuyển hướng sang `account.live.com/proofs/Add`.
  - Form `proofs/Add`: Input email là `#EmailAddress` hoặc `input[name='EmailAddress']`; nút submit là `input[value='Tiếp theo']` hoặc `#iBtn_action`.
  - Form `proofs/Verify`: Điền mã OTP 6 số vào `#codeEntry-0..5` hoặc `#iOttText`, bấm xác nhận. Màn hình proofs/Manage sẽ hiện thẻ "Gửi mã qua email" kèm tick xanh "Cập nhật".
  - Code mẫu chuẩn đã verify live (Máy 13 OTP `382537`):
    ```python
    # 1. Fill email
    inp = page.locator('#EmailAddress, input[type="email"], input[name="EmailAddress"]').first
    inp.fill(rec_email)
    page.locator('#iBtn_action, input[value="Tiếp theo"], button:has-text("Tiếp theo")').first.click()
    # 2. Poll OTP & fill
    otp = fetch_recovery_email_otp(rec_email, timeout_seconds=40)
    if otp:
        if page.locator('#codeEntry-0').is_visible():
            for idx, ch in enumerate(otp[:6]):
                page.locator(f'#codeEntry-{idx}').fill(ch)
        else:
            page.locator('#iOttText, input[name="otc"]').first.fill(otp)
        page.locator('#iBtn_action, input[value="Tiếp theo"], #idSIButton9').first.click()
    ```

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

---

## 3. Thứ tự thực thi chuẩn trong giai đoạn CHANGE_INFO & Quy tắc Ngâm

### Vấn đề cốt lõi:
- **Tài khoản Zin trắng chưa có mail khôi phục:** Microsoft **KHÔNG CHO PHÉP BẬT 2FA AUTHENTICATOR APP TRỰC TIẾP** vì tài khoản chỉ có duy nhất 1 phương thức xác thực (Mật khẩu). Microsoft yêu cầu tối thiểu 2 phương thức xác thực trước khi bật Two-step verification.
- **Có cần ngâm thêm 7 ngày sau khi Add mail khôi phục không?**
  - **HOÀN TOÀN KHÔNG.**
  - Thời gian ngâm 7 ngày (`WAIT_7D`) là ngâm **Profile GPM + IP Proxy** để biến profile thành **Trusted Device**.
  - Việc **THÊM MỚI** (Add additional method) một mail khôi phục được Microsoft **kích hoạt ngay lập tức (Active liền tại chỗ với tích xanh "Cập nhật")**, Microsoft KHÔNG áp đặt 30 ngày hay 7 ngày chờ. (Chỉ khi gỡ đè / thay thế toàn bộ thông tin cũ mà không có mã mới bị dính 30 ngày Security Hold).

### Thứ tự 4 bước bắt buộc trong cùng 1 lần chạy CHANGE_INFO:
1. **Bước 1 (Ưu tiên số 1):** `add_recovery_email_to_account` — Mở modal ➔ chọn `Gửi mã qua email` ➔ điền `<user><3rand>@fviainboxes.com` ➔ bóc OTP qua API `fviainboxes.com` ➔ submit xác nhận.
   *(Lúc này tài khoản đã có đủ 2 phương thức: Mật khẩu + Mail khôi phục).*
2. **Bước 2:** `setup_2fa` — Thiết lập 2FA Authenticator app (TOTP) và kích hoạt công tắc Two-step verification tổng.
   *(Nếu Microsoft yêu cầu xác minh danh tính, hệ thống dùng ngay mail khôi phục vừa thêm ở Bước 1 để nhận OTP bóc qua API).*
3. **Bước 3:** `change_password` — Đổi mật khẩu mới độ dài 14 ký tự có độ phức tạp cao.
4. **Bước 4:** `sign_out_everywhere` — Bấm "Đăng xuất khỏi mọi nơi" để thu hồi toàn bộ token cũ.

👉 **Toàn bộ 4 bước chạy tuần tự trong CÙNG 1 PHIÊN duy nhất**, hoàn tất xong là tài khoản sẵn sàng xuất bán, **tuyệt đối không tốn thêm 7 ngày ngâm vô ích**!

