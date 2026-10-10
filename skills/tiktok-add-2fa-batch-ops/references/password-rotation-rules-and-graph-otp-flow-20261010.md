# Quy Tắc Xoay Vòng Mật Khẩu Phase B & Tích Hợp Graph API OTP Cho Hotmail (10/10/2026)

## 1. Cơ Chế Tự Động Đổi / Tạo Mật Khẩu Trong `tiktok-add-bao-mat-f2a`
- **Câu hỏi nghiệp vụ**: *"Bình thường add 2FA có tự đổi pass không? Nếu không có pass để None thì tự change pass phải không?"*
- **Quy tắc kỹ thuật chuẩn xác (SSOT tại `core/passwords.py`)**:
  - Hàm `password_needs_rotation(value)` kiểm tra giá trị cột Mật khẩu trong workbook Excel:
    ```python
    def password_needs_rotation(value: str | None) -> bool:
        text = str(value or "").strip()
        return (not text) or bool(_LEGACY_PASS_RE.match(text))
    ```
  - **Trường hợp TỰ ĐỘNG ĐỔI / TẠO PASS MỚI (`password_needs_rotation == True`)**:
    1. Cột Mật khẩu đang để trống (`None` hoặc `""`).
    2. Cột Mật khẩu chứa định dạng legacy cũ của farm: `Ten@Ks` hoặc `Ten+chuso+@` (vd: `Anhhoang3009@`).
    * **Hành vi**: Phase B sẽ tự động gửi mã OTP xác minh danh tính về Hotmail/Gmail ➔ bóc tách mã OTP ➔ sinh mật khẩu mới ngẫu nhiên 18 ký tự (chữ hoa, thường, số, gạch ngang) ➔ đổi mật khẩu trên TikTok ➔ **tự động ghi đè mật khẩu mới vào cột Pass trong file Excel**.
  - **Trường hợp GIỮ NGUYÊN MẬT KHẨU CŨ (`password_needs_rotation == False`)**:
    * Mật khẩu trong Excel là mật khẩu tùy biến phức tạp (ví dụ: `Xhr3K42X@J@6w`).
    * **Cạm bẫy**: Nếu mật khẩu này **bị sai thực tế trên TikTok**, Phase B mặc định **sẽ KHÔNG kích hoạt luồng đổi pass**, dẫn đến việc không thể vào các mục bảo mật yêu cầu xác nhận pass!
    * **Khắc phục**: Operator / Agent **BẮT BUỘC xóa ô pass của tài khoản đó trong Excel về `None`**. Khi pass là `None`, Phase B sẽ tự động kích hoạt luồng tạo pass mới qua OTP email và cập nhật lại Excel.

---

## 2. Tùy Chọn Chỉ Đổi Mật Khẩu (`--password-only`)
- Khi chỉ muốn xử lý cập nhật / tạo mật khẩu mới cho tài khoản mà chưa muốn bật 2FA Authenticator, sử dụng cờ:
  ```bash
  python python_runner/run_capture_phase_b.py \
    --machine <STT> \
    --serial <SERIAL> \
    --expected-username <USERNAME> \
    --source-row <ROW_EXCEL> \
    --workbook-path "D:/OneDrive/TaadaaData/admin/taikhoan_dat_v2_updated .xlsx" \
    --workbook-sheet "Tài Khoản" \
    --live \
    --password-only
  ```
- Script chạy đến bước hoàn tất lưu mật khẩu mới vào Excel rồi dừng thành công (`status=success, phase=password-only`).

---

## 3. Tích Hợp Đọc OTP Hotmail Qua Graph API Trên PC (`social_reg_v1.py`)
- **Trước đây**: Khi cần OTP từ Hotmail/Outlook, `LivePhaseBAdapter._read_device_email_otp` cố mở ứng dụng Microsoft Outlook trên điện thoại (`com.microsoft.office.outlook`). Trên điện thoại cũ (Galaxy S7), việc mở Outlook thường gây giật lag, tốn RAM và dễ làm TikTok bị OOM kill.
- **Chuẩn hóa**: Tích hợp gọi thẳng hàm `read_tiktok_otp_from_graph_token` từ `D:/Taadaa/Tiktok_Reg/social_reg_v1.py`:
  ```python
  elif any(low.endswith(sfx) for sfx in ("@hotmail.com", "@outlook.com")):
      try:
          import sys
          from pathlib import Path
          reg_dir = Path("D:/Taadaa/Tiktok_Reg")
          if str(reg_dir) not in sys.path:
              sys.path.insert(0, str(reg_dir))
          from social_reg_v1 import read_tiktok_otp_from_graph_token
          code = read_tiktok_otp_from_graph_token(device=serial, email=email, timeout=60)
          if code and len(code) == 6:
              return code
      except Exception:
          pass
  ```
- Lấy OTP trực tiếp qua HTTP REST API token trên PC trong 2-3 giây, hoàn toàn không chạm vào điện thoại.

---

## 4. Khắc Phục Lỗi `UI_TARGET_AMBIGUOUS:Next:0` Trong `advance_to_otp`
- **Hiện tượng**: Khi bấm nút chuyển bước ở màn hình bật 2FA, adapter văng lỗi:
  ```json
  {"status": "failed", "reason": "UI_TARGET_AMBIGUOUS:Next:0"}
  ```
- **Căn nguyên**:
  - Giao diện TikTok tiếng Việt hiển thị nút `Tiếp` hoặc `Tiếp tục`.
  - Bộ kiểm tra `find_tappable_value` yêu cầu tìm được đúng duy nhất 1 node (`len(choices) == 1`). Nếu có nhiều node text con lồng nhau hoặc màn hình chưa cuộn tới nút, hàm ném `LiveAdapterError`.
- **Khắc phục**:
  - Trong `advance_to_otp`, nếu `find_tappable_value` bắt gặp ambiguity, fallback duyệt qua các elements khớp nhãn và chọn element có tọa độ Y lớn nhất (`max(matches, key=lambda el: el.center[1])`), đảm bảo luôn tap trúng nút hành động ở chân màn hình.
