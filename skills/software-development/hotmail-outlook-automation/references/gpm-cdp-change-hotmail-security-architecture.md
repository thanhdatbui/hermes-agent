# GPM Playwright CDP Hotmail Security Architecture & Microsoft Identity Quirks

## 1. Bối cảnh & Lý do chuyển từ Android S7 sang GPMLogin (PC)

Trước đây, watchdog đổi pass Hotmail (`cron_night_hotmail_security_watchdog.py`) chạy Chrome mobile trực tiếp trên điện thoại Samsung Galaxy S7 (2016). Điều này gặp 3 vấn đề chí mạng:
1. **Tranh chấp Device Lock**: Khung giờ đêm 02:00 - 05:00 là lúc farm chạy Ca 4 nuôi feed và dọn cache TikTok (`end-of-day-clear-tiktok-cache`). Watchdog mở máy S7 thấy vướng lock phải hủy bỏ (`DeviceLockUnavailable`).
2. **Giới hạn phần cứng S7**: RAM 4GB, CPU Exynos 8890 cũ rất dễ bị tràn bộ nhớ (OOM) hoặc crash khi tải các trang bảo mật nặng nề của Microsoft (`account.live.com/proofs`).
3. **Layout Web Mobile bất ổn**: Giao diện mobile của Microsoft liên tục thay đổi, tọa độ tap qua ADB dễ lệch.

➡️ **Giải pháp chuẩn**: Chuyển toàn bộ luồng đổi mật khẩu và đổi thông tin bảo mật Hotmail lên **GPMLogin (PC)** qua Playwright CDP:
- Không chiếm máy farm: 0% tải trên dàn S7.
- Tốc độ xử lý PC: Khởi động profile trong 1s, kết nối CDP trong 0.2s, load trang mượt mà.
- Đồng nhất IP 100%: Profile GPM của từng máy đã gán sẵn proxy Singbox 4G tương ứng (M2/M40 dùng chung port proxy `5102`), không lo checkpoint vị trí địa lý lạ.

---

## 2. Cấu trúc Triển khai (`gpm_change_hotmail_security.py`)

- **Vị trí script**: `D:\Taadaa\Hotmail\scripts\gpm_change_hotmail_security.py`
- **Thư viện**: `GPMClient` (`D:\Taadaa\GPM auto\src\gpm_client.py`), `playwright.sync_api`.
- **Tham số CLI**:
  - `--machine <N>`: Chỉ định máy farm (e.g. 2, 40).
  - `--email <email>`: Chỉ định email cụ thể.
  - `--canary`: Chạy đúng 1 tài khoản đại diện kiểm chứng.
  - `--live`: Bắt buộc để thực sự click submit đổi pass và ghi Excel.
  - `--max-targets <N>`: Giới hạn số lượng tài khoản mỗi lượt.

---

## 3. Các Bẫy Giao diện & Kỹ thuật Xử lý Microsoft Identity (Playwright CDP)

1. **Điền Form Đăng nhập & Submit**:
   - Tránh click nút submit bằng ID cố định `#idSIButton9` (có thể bị che hoặc chưa render).
   - Dùng lệnh bàn phím:
     ```python
     email_input.fill(email)
     email_input.press("Enter")
     ```
2. **Bẫy Gợi ý Gửi Mã Xác minh thay vì Hiện Ô Password**:
   - Microsoft thường ưu tiên luồng passwordless: hiển thị *"Xác minh email của bạn ... Chúng tôi sẽ gửi mã"* kèm nút *"Gửi mã"*.
   - Phía dưới có link chuyển sang dùng mật khẩu:
     ```python
     switch_pwd = page.locator("#idA_PWD_SwitchToPassword, text='Sử dụng mật khẩu của bạn', text='Use your password instead'")
     if switch_pwd.is_visible(timeout=3000):
         switch_pwd.click()
     ```
   - Sau khi click, ô `#i0118` mới xuất hiện để điền password.
3. **Bẫy Duy trì Đăng nhập (KMSI - Keep Me Signed In)**:
   - Bấm nút "Không" (`#idBtn_Back`) để tránh lưu session cookie dơ.
4. **Quy trình Đổi Mật khẩu (`account.live.com/password/change`)**:
   - Sinh mật khẩu mạnh 14 ký tự (`secrets.choice` gồm chữ hoa, chữ thường, số, ký tự đặc biệt).
   - Điền `#currentPassword`, `#newPassword`, `#confirmPassword`.
   - Bấm Submit (`#save` hoặc `#idSubmit_SAV_btnSubmit`).
5. **Gỡ Email Khôi phục Lạ & Đăng xuất Khỏi Mọi Nơi (`account.live.com/proofs/manage/additional`)**:
   - Tìm và bấm *"Đăng xuất khỏi mọi nơi"* (*"Sign out of everywhere"*) ➔ Xác nhận.
   - Hủy bỏ toàn bộ session, cookie, refresh token cũ của bên bán hòm thư.
6. **Cập nhật Dữ liệu Atomic**:
   - Ghi mật khẩu mới vào **Cột G (PASS MAIL)** của workbook `taikhoan_dat_v2_updated .xlsx`.
   - Ghi nhận trạng thái vào `D:\Taadaa\runtime\kibe\cron-state\hotmail_changed_tracker.json`.
   - Tuân thủ GATE 6: Chụp và lưu ảnh screenshot tại mỗi checkpoint (Login, Pre-change, Post-change, Signout) và xuất `MEDIA:<path>`.
