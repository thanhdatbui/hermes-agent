# Quy Tắc Đổi Mật Khẩu (Password Rotation) & Bẫy Màn Hình Xác Minh Danh Tính Trong Add 2FA (10/10/2026)

## 1. Quy Tắc Tự Động Đổi Pass Trong Quy Trình Add 2FA (`password_needs_rotation`)
- **Bình thường chạy Add 2FA có tự đổi pass không?**
  * **KHÔNG PHẢI NICK NÀO CŨNG ĐỔI PASS**.
  * Quy trình sử dụng hàm `password_needs_rotation(pass_value)` trong `core/passwords.py`:
    - Nếu mật khẩu trong Excel đã tồn tại và là mật khẩu chuẩn (không khớp với định dạng cũ cần rotate): **GIỮ NGUYÊN MẬT KHẨU CŨ**, chỉ bật 2FA (Authenticator App) và lưu key 32 ký tự vào cột E.
    - Nếu mật khẩu trong Excel là dạng cũ (legacy farm formats như `Ten@Ks`, `Ten123@`): Bắt buộc rotate sang mật khẩu mới.
- **Nếu cột Pass để trống (`None` hoặc rỗng `""`) thì sao?**
  * **TỰ ĐỘNG SINH & ĐỔI PASS MỚI 100%**:
    - `password_needs_rotation(None)` trả về `True`.
    - Script kích hoạt hàm `ensure_account_password_saved()`.
    - Sinh mật khẩu ngẫu nhiên 18 ký tự cực mạnh (`generate_account_password()` gồm chữ hoa, chữ thường, số, dấu gạch ngang).
    - Vượt qua màn hình xác minh danh tính của TikTok bằng OTP email.
    - Điền mật khẩu mới vào TikTok và **tự động ghi đè mật khẩu mới vào cột Mật khẩu (Cột C / Column 4) của file Excel `taikhoan_dat_v2_updated .xlsx`**.
- **Xử lý tài khoản bị sai pass trong Excel**:
  * Khi nick bị TikTok báo sai pass cũ: Chỉ cần đặt lại ô mật khẩu của dòng đó trong Excel về `None`.
  * Lần chạy kế tiếp, script sẽ coi như nick cần cấp pass mới và tự động thực hiện luồng đổi mật khẩu qua OTP email.

---

## 2. Bẫy Nút Bấm Song Ngữ Trên Màn Hình "Xác Minh Danh Tính" (Lỗi `UI_TARGET_AMBIGUOUS:Next:0`)
- **Triệu chứng**:
  - Khi script chạy vào phần đổi mật khẩu cho tài khoản đã có session hoặc tài khoản cũ, TikTok bung màn hình **"Xác minh danh tính" (Verify your identity)**.
  - Script chọn xác minh qua Email, sau đó cố gắng tìm nút để gửi mã nhưng crash với lỗi:
    ```text
    {"status": "failed", "reason": "UI_TARGET_AMBIGUOUS:Next:0"}
    ```
- **Căn nguyên cốt lõi**:
  - Trong `live_phase_b_adapter.py`, code cũ gọi `self._tap_value("Tiếp", prefix=True)`.
  - Bộ từ điển song ngữ `_BILINGUAL_LABELS` map `"Tiếp"` sang `"Next"`.
  - Trên TikTok tiếng Việt v46+, nút bấm xác nhận gửi mã OTP qua Email thường là:
    * Tiếng Việt: **"Gửi mã"**, **"Tiếp tục"**, hoặc **"Tiếp"**.
    * Tiếng Anh: **"Send code"**, **"Continue"**, hoặc **"Next"**.
  - Nếu nút trên màn hình là *"Gửi mã"*, việc chỉ tìm *"Tiếp"* / *"Next"* sẽ trả về 0 kết quả (`choices == 0`), kích hoạt `LiveAdapterError("UI_TARGET_AMBIGUOUS:Next:0")`.
- **Giải pháp chuẩn hóa trong `live_phase_b_adapter.py`**:
  - Tại các bước chuyển tiếp / gửi mã (như trong `advance_to_otp` và `ensure_account_password_saved`):
    * Quét danh sách đầy đủ các nhãn ứng viên: `["Tiếp tục", "Tiếp", "Gửi mã", "Send code", "Next", "Continue"]`.
    * Trong `advance_to_otp`, nếu `find_tappable_value` không tìm thấy target đơn nhất, fallback quét toàn bộ các node khớp nhãn có `element.center is not None` và chọn phần tử nằm ở vị trí đáy màn hình:
      ```python
      matches = [
          element for element in iter_elements(parse_xml(xml_text))
          if _matches(element, label, prefix=prefix_flag) and element.center is not None
      ]
      if matches:
          target = max(matches, key=lambda el: el.center[1])
          break
      ```

---

## 3. Bắt Buộc Đọc OTP Hotmail Qua Microsoft Graph API Trên PC (`read_tiktok_otp_from_graph_token`)
- **Cạm bẫy cũ**:
  - Trong `_read_device_email_otp`, khi gặp đuôi `@hotmail.com` hoặc `@outlook.com`, code cũ gọi `read_tiktok_otp_from_outlook_app` mở ứng dụng Outlook trên điện thoại.
  - Việc mở app Outlook trên thiết bị Android làm gián đoạn màn hình TikTok, tốn RAM, có nguy cơ làm TikTok bị reload/kill OOM, hoặc kẹt UI khi Outlook đòi đăng nhập lại.
- **Quy tắc bất biến**:
  - BẮT BUỘC gọi hàm `read_tiktok_otp_from_graph_token` từ `D:/Taadaa/Tiktok_Reg/social_reg_v1.py` trước:
    ```python
    from social_reg_v1 import read_tiktok_otp_from_graph_token
    code = read_tiktok_otp_from_graph_token(device=serial, email=email, timeout=60)
    if code and len(code) == 6:
        return code
    ```
  - Graph API đọc thẳng hộp thư trên cloud thông qua Microsoft token của PC, lấy OTP trong vòng 1-3 giây mà không chạm vào giao diện thiết bị di động.

---

## 4. Kỷ Luật Bằng Chứng Thị Giác Khi Process Chạy Nền Hoàn Thành
- **Cấm báo cáo suông**: Khi một background process (như `proc_...`) báo `completed normally (exit code 0)`, Coordinator **TUYỆT ĐỐI KHÔNG ĐƯỢC** chỉ trả lời tin nhắn khẳng định thành công mà không có ảnh.
- **Thực thi bắt buộc**:
  1. Lập tức đánh thức thiết bị hoặc mở màn hình kiểm chứng (Profile hoặc Account Switcher).
  2. Chụp ảnh màn hình máy thật (`screencap`).
  3. Dùng WinRT OCR / Vision soi mắt xác nhận đúng username hoặc danh sách switcher.
  4. Đính kèm thẻ `MEDIA:<path>` trên một dòng độc lập ngoài khối blockquote `>` để gửi trực tiếp cho User.
