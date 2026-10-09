# Pattern: Luôn Ưu Tiên 2FA Authenticator Trước OTP Email Khi Đăng Nhập TikTok (2026-09-28)

## 1. Bối cảnh & Nguyên nhân lỗi (The Trap)
- Trên màn hình "Xác minh 2 bước" (2-Step Verification) của TikTok:
  - TikTok có thể mặc định hiển thị luồng gửi mã về Email (`Sử dụng liên kết này hoặc nhập mã được gửi đến a***6@gmail.com`).
  - Đi kèm là dòng chữ "Xác minh 2 bước".
- **Cạm bẫy trong classifier cũ**:
  - `TWOFA_HINTS` chứa chuỗi `"xac minh 2 buoc"`.
  - Khi thấy chuỗi này, script ngộ nhận đây là màn hình nhập mã TOTP của Authenticator App và tự động lấy TOTP secret điền vào ô mã Email OTP -> TikTok từ chối cả 3 lần vì sai mã -> STOPPED: [2fa-app] Ma 2FA khong qua sau 3 lan.
  - Ngược lại, nếu coi toàn bộ màn hình có Email là Email OTP thì lại bỏ qua secret TOTP quý giá đã lưu trong tracking database.

## 2. Quy tắc Bắt Buộc (User Directive)
> **"Thì chọn sử dụng phương thức khác rồi dùng 2fa đi. Luôn ưu tiên 2fa trước otp mail sau."**

- **Nguyên tắc cốt lõi**:
  1. Khi tài khoản có secret 2FA (TOTP) trong tracking workbook, **BẮT BUỘC ưu tiên 2FA Authenticator bằng mọi giá**.
  2. Dù TikTok đang mặc định chìa ra form Email OTP, script phải chủ động bấm vào **`Sử dụng phương thức khác >`** (`Su dung phuong thuc khac` / `Use another method`, thường ở tọa độ `(408, 1098)`).
  3. Chọn phương thức Authenticator:
     - Nhãn Tiếng Việt của TikTok có thể là **`Trình xác thực`** hoặc **`Ứng dụng xác thực`** (Rid/text/desc). Bắt buộc regex/contains cả 2 nhãn này!
  4. Sau khi vào form Authenticator -> sinh mã TOTP chuẩn theo epoch của thiết bị -> điền mã và submit.
  5. **Chỉ khi nào** tài khoản không có 2FA secret HOẶC bấm đổi phương thức thất bại (không có tùy chọn Authenticator) thì mới fallback sang đọc Email OTP.

## 3. Khắc phục trong Code (`social_reg_v1.py` & `tiktok_login_v1.py`)
- **`handle_tiktok_authenticator_2fa`**:
  ```python
  auth_markers = ["ung dung xac thuc", "authenticator app", "google authenticator"]
  # Nếu đang ở màn 2FA nhưng là luồng Email OTP ("gui den", "email"), tap "Su dung phuong thuc khac" để chuyển sang Authenticator
  if not any(h in flat for h in auth_markers) and (any(h in flat for h in ["gui den", "email"]) or "xac minh 2 buoc" in flat):
      log("[2fa-app] Email OTP screen -> switch to another method")
      if not find_text_tap(device_id, "Sử dụng phương thức khác", "Su dung phuong thuc khac", "Use another method", wait=0.5):
          tap(device_id, 408, 1098, wait=0.5)
      time.sleep(1.5)
      if not find_text_tap(device_id, "Trình xác thực", "Trinh xac thuc", "Ứng dụng xác thực", "Ung dung xac thuc", "Authenticator App", "Authenticator", wait=0.5):
          log("[2fa-app] Khong thay lua chon Authenticator App")
          return False
      time.sleep(1.5)
  ```
- **Vòng lặp `drive_login_screens`**:
  ```python
  # Luôn ưu tiên Authenticator 2FA trước:
  if any(h in flat for h in TWOFA_AUTHENTICATOR_HINTS) or any(h in flat for h in TWOFA_GENERIC_HINTS):
      log(f"[telemetry:auth-screen] action=authenticator_2fa_dispatched round={round_idx}")
      auth_ok = handle_tiktok_authenticator_2fa(device_id, email, stt=stt)
      if auth_ok:
          time.sleep(D_LONG)
          continue
      # Nếu không có Authenticator / không chuyển được, mới fallback sang Email OTP
      log(f"[telemetry:auth-screen] action=fallback_email_otp_2fa round={round_idx}")
      handle_tiktok_email_otp(device_id, email, account["mail_pass"], stt=stt)
      time.sleep(D_LONG)
      continue
  ```

## 4. Xử lý Màn hình Tiểu sử (Bio Screen Onboarding)
- TikTok sau khi login thành công thường hiện màn hình thêm "Tiểu sử" ("Bạn có thể chỉnh sửa tiểu sử bất cứ lúc nào") kèm nút "Hủy" `[24,72][167,204]` hoặc nút "Lưu" `[922,72][1056,204]`.
- Trong `handle_post_auth_screens`: Bắt buộc detect `"tieu su"` / `"chinh sua tieu su"` và bấm `Hủy` (hoặc fallback coordinate `(95, 138)`) để vượt qua vào thẳng Feed/Profile, tránh timeout kẹt màn hình.
