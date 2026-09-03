# 2026-08-16: OTP dính vào field DOB + reg 4 máy hotmail (38/54/57/66)

## Bối cảnh
Batch reg 4 máy hotmail sau khi login Outlook app xong (mỗi máy đã add mail).
Kết quả batch: 54 SUCCESS; 38/57/66 FAILED.

## Bug: OTP bị nhập vào field Ngày sinh (máy 38)

### Triệu chứng
- Log: `[otp-enter] no confirm button -> sent Enter` → `✓ Email verification code entered`
  → `✗ Timeout chờ login success` → PENDING.
- Ảnh kết quả: màn "Ngày sinh của bạn là ngày nào?" với **dãy OTP (712503) nằm
  trong ô input field ngày sinh** — script type OTP vào field đó vì TikTok đã
  chuyển màn từ OTP sang DOB trong lúc nhập (timing race).

### Root cause
`handle_tiktok_email_otp` type OTP xong → TikTok tự chuyển sang màn DOB
(đăng ký mới flow: OTP xong → DOB → password). Script sau đó `sleep(D_LONG)`
rồi mới check màn birthday (bước 7d) — nhưng OTP vẫn bị gõ vào field DOB vì
thời điểm type trùng lúc màn đổi.

### Fix (user hướng dẫn: "Chạy tiếp hàm ở trạng thái hiện tại", KHÔNG chạy lại từ đầu)
1. Máy đang ở màn DOB (OTP dính field) → **gọi trực tiếp `fill_birthday`**:
   `social_reg_v1.fill_birthday("<serial>", "<dob hoặc ''>", stt=38)`
   - DOB trống trong workbook → fallback `01/01/1999` (built-in).
   - `fill_birthday` scroll drum picker (ngày/tháng/năm) tới target, đọc
     `[birthday] UI final='1 tháng 1, 1999'`, tap "Tiếp tục" (540,1603).
2. Sau DOB → màn password TikTok → chạy lại script với **`--resume`**:
   `python social_reg_v1.py 38 --resume --email <mail> --ss`
   → script tiếp tục từ màn hiện tại (bước 8 fill_password_and_login → post-auth
   → wait_login_success → tracking).
3. Kết quả: `✅ SUCCESS: augustusdanteamathyst7@hotmail.com` (TikID augustusdant7,
   tracking row 301, backup workbook trước write).

### Rule rút ra (user nhấn mạnh)
- **Fail giữa chừng → resume từ màn hiện tại, KHÔNG chạy lại reg từ đầu**
  (chạy lại phá state đã qua: OTP đã dùng, màn đã đi).
- **Bước script không qua được → gửi ảnh cho user liền, chờ duyệt** — không tự
  đoán tọa độ/lòng vòng (xem thêm skill `taadaa-farm-ops-rules`).

## Lỗi `[06_email_option] Không tìm thấy Email/Username` (máy 57/66)

### Triệu chứng
- Log: `[06_email_option] Không tìm thấy: ('Email/tên người dùng', ...)` → STOPPED.
- XML fail: màn `I18nSignUpActivity` chỉ có `text="Số điện thoại"`, `"+84"`,
  `"Đăng nhập"`, `"Tạo tài khoản"`, `"VN"` — **không có tab/icon email hiển thị**.

### Trạng thái
Chưa fix tại thời điểm ghi — màn đăng ký mới hiển thị mặc định SĐT, cần user
hướng dẫn tìm entry email (tab ẩn / toggle / scroll). Ghi lại để session sau
tiếp tục: máy 57 (ce11160b54ee2f3403) + 66 (ce12160c2a99962905) đều kẹt đây,
Outlook app đã có mail đúng (Derek / Daunte), chỉ cần qua được màn chọn email.

## Serial map (đã dùng phiên này)
- 38 = ce06160685310f1c04
- 54 = ce12160c81c8acae0c
- 57 = ce11160b54ee2f3403
- 66 = ce12160c2a99962905

## Rotation guard (nhắc lại)
`prepare_device(lock_rotation=True)` có thể bật lại accelerometer_rotation=1 trên
Samsung → trước mỗi bước lock: `settings put system accelerometer_rotation 0` +
`user_rotation 0` + `wm user-rotation lock 0`; verify bằng `settings get` + PIL size.
