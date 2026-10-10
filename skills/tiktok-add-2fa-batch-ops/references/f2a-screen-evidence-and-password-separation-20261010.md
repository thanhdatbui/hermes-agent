# 2FA Visual Evidence Invariant, Password Separation, and Graph API OTP (10/10/2026)

## 1. Bẫy Sai Bằng Chứng Nghiệm Thu 2FA: Account Switcher vs 2FA Screen

### Hiện tượng & Phản ứng từ Người dùng
- Sau khi chạy tiến trình bật 2FA cho tài khoản (`run_capture_phase_b.py`), Agent gửi ảnh chụp menu **Chuyển đổi tài khoản (Account Switcher)** hoặc tab **Hồ sơ (Profile)** để báo cáo hoàn thành.
- Người dùng lập tức bức xúc và chất vấn gay gắt:
  > *"Hình chứng minh đâu. Sao lại vi phạm k gửi hình r"*
  > *"Cái t cần là chứng minh có 2fa r chứ gửi linh tinh gì v"*

### Bản chất & Quy tắc bất biến
- Ảnh Account Switcher chỉ chứng minh tài khoản đó **đã được lưu phiên đăng nhập trên thiết bị**. Nó **HOÀN TOÀN KHÔNG CHỨNG MINH ĐƯỢC TÀI KHOẢN ĐÃ ĐƯỢC BẬT 2FA HAY CHƯA!**
- **Bằng chứng thị giác DUY NHẤT hợp lệ cho tác vụ Add 2FA:**
  * BẮT BUỘC là ảnh chụp thực tế màn hình **"Xác minh 2 bước" (Two-step verification)** trong mục *Cài đặt và quyền riêng tư > Bảo mật*.
  * Phải nhìn thấy rõ ràng dòng chữ:
    - **"Xác minh 2 bước đang bật"**
    - Phương thức **"Trình xác thực: Bật"** (hoặc Authenticator app: On)
    - Phương thức **"Email: Bật"** (kèm email hiển thị dạng mask)
- **Cơ chế tự động lưu ảnh trước Teardown:**
  Trong `live_phase_b_adapter.py`, hàm `tiktok_2fa_enabled()` được cấy lệnh tự động chụp và kéo ảnh về máy host trước khi kiểm tra trạng thái và trước khi khối `finally` đóng ứng dụng:
  ```python
  self.adb.shell(["screencap", "-p", "/sdcard/2fa_proof.png"], check=False)
  subprocess.run([
      "adb", "-H", host, "-s", serial,
      "pull", "/sdcard/2fa_proof.png", f"D:/Taadaa/tmp/m{machine}_2fa_status_proof.png"
  ], timeout=12)
  ```
  Nhờ đó, luôn đảm bảo có sẵn file ảnh bằng chứng màn hình 2FA để gửi ngay lập tức cho người dùng kèm thẻ `MEDIA:`.

---

## 2. Phân Định Rạch Ròi: Bật 2FA Thành Công vs Đổi Mật Khẩu (Password Rotation)

### Hiện tượng & Cạm bẫy nhận vơ
- Người dùng hỏi: *"Có cả pass ms r phải k"*.
- Nếu Agent vội vàng kết luận "đã có pass mới" dựa trên việc lệnh Phase B trả về `status: success` thì sẽ phạm sai lầm nghiêm trọng (Hallucination claim).

### Cơ chế kỹ thuật trong Phase B Runner
1. **Quy trình chạy 2FA (`execute_phase_b`)**:
   - Bước 1: Điều hướng vào mục Bảo mật và bật Trình xác thực 2FA.
   - Bước 2: Lưu Secret 32 ký tự vào Journal / Workbook (Cột E).
   - Bước 3: Gọi `operations.ensure_password_saved()`.
2. **Cơ chế Fail-Safe của `ensure_account_password_saved()`**:
   - Khi đổi mật khẩu, TikTok yêu cầu một bước *"Xác minh danh tính"* riêng (gửi mã OTP về email).
   - Nếu trong vòng 8 bước điều hướng không vào được form đổi mật khẩu (hoặc chưa lấy được OTP), hàm sẽ **soft-return (trả về nhẹ nhàng) mà không ném exception**:
     ```python
     # Fail-safe: Nếu sau 8 lần điều hướng không vào được form đổi mật khẩu,
     # giữ nguyên mật khẩu hiện tại trong workbook, không làm crash toàn bộ phiên add 2FA.
     return
     ```
   - **Hậu quả**: Tiến trình Phase B vẫn báo `success` vì 2FA Authenticator đã bật thành công, nhưng ô Mật khẩu trong Excel (Cột C) **VẪN LÀ `None`** và mật khẩu trên TikTok **CHƯA ĐƯỢC ĐỔI**!
3. **Quy tắc phát ngôn trung thực**:
   - BẮT BUỘC kiểm tra trực tiếp giá trị trong file Excel sau khi chạy.
   - Nếu ô Pass là `None`, BẮT BUỘC trả lời rõ ràng: **2FA Authenticator đã bật thành công 100%, nhưng Mật khẩu CHƯA đổi (vẫn là `None` trong file Excel)**. Tuyệt đối không được nói nước đôi hoặc nhận vơ.

---

## 3. Tích Hợp Microsoft Graph API PC Cho Luồng Nhận OTP Đổi Mật Khẩu

### Nguyên nhân kẹt cũ
- Trong `live_phase_b_adapter.py`, hàm `_read_device_email_otp()` ban đầu chỉ gọi `read_tiktok_otp_from_outlook_app()` (đọc thư qua ứng dụng Outlook Android trên điện thoại).
- Trên các thiết bị Farm thực tế (đặc biệt cụm Admin), máy KHÔNG cài hoặc không đăng nhập app Outlook, dẫn đến không thể đọc OTP để vượt qua bước *"Xác minh danh tính"* khi đổi pass.

### Bản vá kết nối Graph API PC
Nối trực tiếp hàm `read_tiktok_otp_from_graph_token` từ repo `Tiktok_Reg` vào adapter:
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
    # Fallback xuống app Outlook nếu Graph API không khả dụng
    ...
```

---

## 4. Bẫy Lệch Dòng Khi Truyền `--source-row` (Row Index Mismatch)

- Trong file `taikhoan_dat_v2_updated .xlsx`, số thứ tự máy (Cột A - STT) không trùng với chỉ số dòng Excel (Row Index).
- **Ví dụ thực tế**:
  * Dòng 241: STT máy là **260**.
  * Dòng 242: STT máy mới là **261** (nick `ngohuong0265`).
- Nếu nhầm lẫn truyền `--source-row 241` cho máy 261, hàm `inspect_target()` trong `workbook.py` sẽ so khớp Cột A (`260`) với `--machine 261` -> trả về `WorkbookPreflight(identity_matches=False)` -> crash ngay lập tức với lỗi `WorkbookError`.
- **Giải pháp**: Luôn dùng script Python `iter_rows(values_only=True)` để đối soát chính xác chỉ số dòng thực tế (`row_idx`) khớp cả Cột A (STT máy) và Cột C (Username) trước khi truyền cờ `--source-row`.
