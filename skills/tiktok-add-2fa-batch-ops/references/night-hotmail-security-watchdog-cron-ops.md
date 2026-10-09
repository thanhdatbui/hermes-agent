# Hướng Dẫn Vận Hành Cron Bảo Mật Hotmail (night-hotmail-security-watchdog)

## 1. Bối cảnh & Lý do hình thành
- Trong quy trình nuôi nick TikTok của Taadaa Farm, tài khoản Hotmail mua từ shop thường chỉ có mật khẩu của bên bán và token API.
- Nếu không đổi mật khẩu và gỡ mail khôi phục của bên bán, bên bán có thể dùng token cũ hoặc bấm quên mật khẩu để back lại hòm thư và chiếm quyền tài khoản TikTok.
- **Rào cản Microsoft (MIN_LOGIN_AGE_DAYS = 7):** Tài khoản Hotmail mới mua/mới gán vào máy nếu vội vàng đổi thông tin ngay sẽ bị Microsoft kích hoạt checkpoint (khóa tài khoản, bắt OTP SMS, kẹt 30 ngày security pending). Bắt buộc phải ngâm tài khoản trên thiết bị và IP proxy tối thiểu 7 ngày.
- **Tối ưu thao tác (Tránh vòng lặp login Outlook 2 lần):**
  + Không đăng nhập vào App Outlook bằng pass cũ ở Ngày 0.
  + Ngày 0: Chỉ đăng nhập trên Chrome (để lưu session/cookie).
  + Đợi đủ 7 ngày: Chạy script đổi pass trên Chrome + gỡ mail khôi phục + bấm Sign out everywhere.
  + Sau đó mới đăng nhập App Outlook 1 lần duy nhất bằng pass mới.

## 2. Thông tin CronJob
- **Tên Cron:** `night-hotmail-security-watchdog` (Hermes Job ID: `32d81babe28e`)
- **Lịch trình:** `0 3 * * *` (03:00 Sáng mỗi ngày)
- **Lý do chọn khung 03:00 sáng:**
  + Sau khi Ca 4 (Nuôi đêm) kết thúc lúc 02:30.
  + Trước khi Ca 1 (Nuôi sáng) bắt đầu lúc 06:00.
  + Toàn bộ máy farm rảnh rỗi tuyệt đối (cron dọn cache chỉ chạy mất ~10-15 phút), có từ 2 đến 3 tiếng rảnh liên tục, không bị đụng độ feed hay thiếu thời gian.
- **Script wrapper:** `C:\Users\Kibe\AppData\Local\hermes\scripts\night_hotmail_security_watchdog_wrapper.py`
- **Script lõi:** `D:\Taadaa\Hotmail\scripts\cron_night_hotmail_security_watchdog.py`

## 3. Điều kiện lọc mục tiêu & Tính lũy tiến (Idempotent)
Mỗi lần chạy lúc 03:00 sáng, script quét sheet "Tài Khoản" trong `D:\OneDrive\TaadaaData\kibe\taikhoan_dat_v2_updated .xlsx` theo 4 điều kiện:
1. Mail là `@hotmail.com`, `@outlook.com`, `@live.com`, `@msn.com`.
2. Đã reg TikTok và đã có 2FA TOTP (Cột E có dữ liệu).
3. Đủ tuổi ngâm $\ge$ 7 ngày (tính theo Cột I - NGÀY TẠO).
4. Chưa từng đổi pass: Đối soát qua sổ cái `D:\Taadaa\runtime\kibe\cron-state\hotmail_changed_tracker.json`.

## 4. Các bước thực thi tự động trên từng máy rảnh
1. Kiểm tra và chiếm `DeviceLock` an toàn của máy.
2. Khóa cứng hướng màn hình chiều dọc (Portrait `user_rotation=0`), cấm xoay ngang.
3. Mở Chrome trên máy S7 (qua đúng Proxy 4G của máy) chạy `flows/hotmail_security.py`:
   - Đổi sang mật khẩu ngẫu nhiên mạnh (14 ký tự).
   - Gỡ mail khôi phục của bên bán (`remove-getnada` / blacklist domains rác).
   - Bấm "Sign out everywhere" để thu hồi (revoke) toàn bộ session cũ của bên bán và hủy token cũ.
4. Cập nhật mật khẩu mới vào Cột G (`PASS_MAIL`) của Excel.
5. Ghi nhận vào state file `hotmail_changed_tracker.json` để không bao giờ chạy lại nick này.
6. Teardown: force-stop Chrome và đưa máy về Home an toàn.
