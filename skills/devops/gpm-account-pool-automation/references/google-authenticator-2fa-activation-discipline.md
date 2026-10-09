# Google Authenticator 2FA Setup Automation & S7 Decoupling Discipline

## 1. Bối cảnh & Mục đích
Khi tự động hóa kích hoạt xác minh 2 bước (2-Step Verification - 2SV) Google Authenticator trên các profile trình duyệt GPMLogin (nhóm Farm S7):
- Cần tự động điều hướng, vượt qua các thử thách bảo mật của Google (password challenge, reCAPTCHA Enterprise).
- Trích xuất chuỗi Base32 Secret Key (32 ký tự).
- Tính mã xác minh 6 số bằng True UTC Google HTTP Date header và gửi xác nhận thành công.
- Lưu trữ đồng thời và an toàn vào cả 2 file quản lý Excel: `master_gmail_manager.xlsx` và `gmail_clean_v2.xlsx`.

---

## 2. Các Pitfalls Đã Xử Lý & Giải Pháp Chuẩn (2026-09-05)

### A. Pitfall 1: Tránh Shadow DOM Overlay Bằng URL Trực Tiếp
- **Vấn đề:** Khi mở `myaccount.google.com/signinoptions/twosv`, giao diện Google chèn lớp overlay / backdrop (`.uW2Fw-Sx9Kwc`, `div[role="dialog"]`) khiến Playwright bị chặn click vào nút "Authenticator" (`TimeoutError: Locator.click: Timeout exceeded`).
- **Giải pháp:** Điều hướng trực tiếp đến URL: `https://myaccount.google.com/two-step-verification/authenticator` (bỏ qua trang trung gian).
- Dùng `force=True` khi click nút *"Thiết lập"* / *"Set up"*.
- Đợi QR code load (`cant_scan.wait_for(state="visible", timeout=20000)`) trước khi click *"Không thể quét mã?"* / *"Can't scan?"* để trích xuất Secret Key 32 ký tự.

### B. Pitfall 2: Dialog Button Multi-Set & Hidden Button Collision
- **Hiện tượng:** Khi dialog thiết lập mở ra, DOM Google render 2 bộ nút song song (ví dụ: 2 nút "Tiếp theo", 2 nút "Xác minh"). Bộ nút đầu tiên có `is_visible() == False`, bộ nút thứ hai mới hiển thị `is_visible() == True`.
- **Hậu quả:** Nếu gọi `page.locator('button:has-text("Tiếp theo")').first.click()`, Playwright sẽ chọn nút đầu tiên bị ẩn và ném ngoại lệ Timeout hoặc không trigger được hành động chuyển bước tiếp theo.
- **Giải pháp:** Luôn lặp qua toàn bộ nút bên trong container modal và kiểm tra `is_visible()`:
  ```python
  for b in dialog.locator("button").all():
      if b.is_visible() and any(w in b.inner_text().lower() for w in ["next", "tiếp"]):
          b.click()
          break
  ```
- **Input Selector:** Ô nhập mã TOTP sau khi bấm Next là `input[type="text"]` (không dùng selector cứng `input[type="tel"]`).

### C. Pitfall 3: Màn Hình Trung Gian Trước reCAPTCHA Khi Vào 2SV
- **Hiện tượng:** Khi điều hướng vào URL Authenticator, Google có thể hiện màn hình trung gian *"Xác minh danh tính của bạn"* có nút *"Tiếp theo"* trước khi iframe reCAPTCHA được mount vào DOM.
- **Giải pháp:** Script cần click *"Tiếp theo"* này trước, sau đó đợi 3-4s cho iframe reCAPTCHA mount xong mới quét và giải reCAPTCHA qua Audio Challenge.
- **Lưu ý:** Nếu Google nghi ngờ bot trên IP proxy và disable nút audio (`rc-button-disabled`), ưu tiên preflight check Excel để bỏ qua nếu tài khoản đã có Secret Key từ trước.

### D. Pitfall 4: Kỷ Luật Tuyệt Đối Không Đăng Xuất Máy S7 Khỏi `device-activity`
- **Quy tắc bất biến:** TUYỆT ĐỐI CẤM vào `device-activity` và bấm "Đăng xuất" (Sign out) thiết bị Galaxy S7.
- **Lý do:** Bấm đăng xuất trên `device-activity` sẽ làm văng tài khoản Google trên điện thoại Samsung S7 thật của Farm, gây lỗi "Yêu cầu xử lý tài khoản" làm tê liệt cron nuôi acc và feed/follow.
- **Quy trình Decouple đúng:**
  1. Giữ nguyên tài khoản đang đăng nhập trên Samsung S7.
  2. Bật 2FA Google Authenticator trên GPM profile bằng script tự động.
  3. Khi đăng nhập sau này nếu Google hiện prompt S7, chọn *"Thử cách khác"* (Try another way) $\rightarrow$ chọn *"Ứng dụng xác thực"* (Authenticator) $\rightarrow$ điền mã TOTP 6 số từ Secret Key trong Excel. Tài khoản hoạt động độc lập mà không ảnh hưởng Farm.

---

## 3. Quy Trình Đồng Bộ Hai File Excel Thread-Safe

Mỗi khi kích hoạt thành công 2FA Authenticator cho tài khoản, lưu ngay lập tức vào cả 2 file:
1. `master_gmail_manager.xlsx`: Cập nhật đồng thời 2 sheet `Kibe_Farm_S7` và `Master_All` tại cột `2FA_Secret`, cập nhật timestamp `Cập Nhật`, và thêm tag ghi chú `"Bật 2FA Authenticator thành công"`.
2. `gmail_clean_v2.xlsx`: Cập nhật cột `2fa` (cột 4).
3. Đóng workbook ngay sau khi ghi (`wb.save()` và `wb.close()`), không giữ file lock.
