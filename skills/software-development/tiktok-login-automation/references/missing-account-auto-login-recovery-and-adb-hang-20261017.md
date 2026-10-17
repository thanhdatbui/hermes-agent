# Tự Động Phục Hồi Thiếu Nick Qua `tiktok_login_v1.py` & Xử Lý Treo Socket ADB Daemon (2026-10-17)

## 1. Sự Cố Hiện Trường
- **Tình huống**: Trong ca upload Tik 4 trên Máy 79, runner upload báo lỗi `ACCOUNT_VERIFY_MISMATCH` vì tài khoản active trên TikTok của máy là `@thanhtam5077` (của Tik 7), trong khi kịch bản Tik 4 yêu cầu nick `@hoangtuannam2602`.
- **Hành vi thụ động của bot**: Coordinator dừng lại than thở báo cáo lệch nick mà không tự động gọi luồng đăng nhập để nạp nick vào máy.
- **Phản ứng của User**: *"Bị thiếu sao k tự động gọi tiktok login log in tài khoản thiếu vào?"*.

---

## 2. Giải Pháp Tự Động Hóa Chuẩn
Khi phát hiện máy thiếu nick hoặc lệch nick mục tiêu trong Switcher:

### A. Lệnh thực thi canonical:
```bash
python D:/Taadaa/Tiktok_Reg/tiktok_login_v1.py <STT> --email <TARGET_USERNAME_HOAC_EMAIL> --ss
```
- Lệnh này tự động:
  1. Mở app TikTok, vào Profile.
  2. Mở Account Switcher (danh sách tài khoản).
  3. Nếu tài khoản đích đã có sẵn trong danh sách ➔ tự động chạm vào để chuyển phiên (`switch account`).
  4. Nếu chưa có ➔ bấm *Thêm tài khoản*, tự động lấy mật khẩu / 2FA TOTP từ tracking workbook (`taikhoan_dat_v2_updated .xlsx` hoặc `Tik*.xlsx`) để đăng nhập và vượt qua xác thực.

---

## 3. Cạm Bẫy Treo ADB Daemon Trên Galaxy S7 (ADB Socket Hang Trap)

### A. Triệu chứng:
- Khi chạy lệnh ADB cơ bản như `shell getprop sys.boot_completed` hoặc `shell settings put system accelerometer_rotation 0`, tiến trình bị treo đơ và văng:
  ```
  subprocess.TimeoutExpired: Command '['...adb.exe', '-s', '...', 'shell', 'settings put system accelerometer_rotation 0']' timed out after 20 seconds
  ```
- Thử kết nối HTTP tới atx-agent port 7912 báo `WinError 10061 (No connection could be made)`.

### B. Cách khắc phục dứt điểm:
- **CẤM** cố gắng reboot máy hay gửi thêm lệnh adb shell vì socket server trên máy tính đã bị deadlock.
- **BẮT BUỘC** giải phóng socket server trên Windows trước:
  ```python
  import subprocess
  adb = r"C:\Program Files (x86)\xiaowei\tools\adb.exe"
  subprocess.run([adb, "kill-server"], timeout=10)
  subprocess.run([adb, "start-server"], timeout=10)
  subprocess.run([adb, "devices"], timeout=10)
  ```
- Sau khi khởi động lại ADB server, thiết bị S7 sẽ nhận diện lại bình thường (`device`), và tiến trình `tiktok_login_v1.py` sẽ thực thi mượt mà không còn bị nghẽn timeout.
