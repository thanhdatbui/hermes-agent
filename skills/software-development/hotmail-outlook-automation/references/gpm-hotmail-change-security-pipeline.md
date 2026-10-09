# GPM Hotmail Security Pipeline (Đổi Pass Hotmail & Sign Out Everywhere Qua GPMLogin)

## 1. Bối cảnh & Lý do thay thế Samsung S7 (User Mandate 2026-09-25)

Trước đây, hệ thống sử dụng script `cron_night_hotmail_security_watchdog.py` để đổi thông tin bảo mật Hotmail trực tiếp trên thiết bị Android Samsung S7. Tuy nhiên quy trình này bộc lộ 3 nhược điểm nghiêm trọng:
1. **Xung đột Device Lock**: Ca 4 nuôi feed và cron dọn dẹp cache TikTok (`end-of-day-clear-tiktok-cache`) diễn ra lúc 02:00 - 05:00 sáng. Script đổi pass trên S7 liên tục văng lỗi `DeviceLockUnavailable` hoặc làm gián đoạn ca nuôi feed.
2. **Thiết bị S7 yếu (RAM 4GB, chip 2016)**: Khi mở Chrome mobile load các trang quản trị tài khoản nặng nề của Microsoft (`account.live.com/proofs`), máy rất dễ bị OOM, treo uiautomator hoặc crash ứng dụng.
3. **Giao diện mobile thiếu ổn định**: Responsive layout trên mobile của Microsoft thay đổi liên tục, làm các thao tác tap màn hình dễ bị trượt tọa độ.

➡️ **Giải pháp chuẩn hóa**: Chuyển toàn bộ quy trình đổi info Hotmail lên **GPMLogin (PC)** qua script `D:\Taadaa\Hotmail\scripts\gpm_change_hotmail_security.py`.

---

## 2. Kiến trúc Tận dụng Profile GPM Mappings 1-1 Theo Máy

- Mỗi máy farm Kibe (1..80) đã được khởi tạo sẵn một profile Chrome trên GPMLogin Local API (`http://127.0.0.1:19995/api/v3`).
- Quy ước đặt tên profile trong GPM: `f"{machine:02d} - ..."` hoặc `f"{machine} - ..."` (Ví dụ: `02 - phisonglanlqwgj78@gmail.com - 5102`, `40 - nguyenkhoi14031998@gmail.com - 20040`).
- **Bảo tồn Egress IP 100%**: Profile GPM đã cấu hình đúng proxy Singbox / MobiProxy của máy đó (`192.168.110.2:20000+N` hoặc `test.taadaa.click:51xx`). Khi Hotmail đăng nhập trên profile GPM, IP xuất hiện ở phía Microsoft hoàn toàn trùng khớp với IP máy S7 đang dùng, tránh bị Microsoft gắn cờ bất thường về Geo-location.

---

## 3. Quy trình Tự động hóa Playwright CDP & Các bẫy UI Microsoft

### A. Kết nối CDP
- Gọi REST API `GET /profiles/start/{id}` tới GPMLogin (`:19995`) để nhận `remote_debugging_address` (VD: `127.0.0.1:56209`).
- Dùng `playwright.sync_api` kết nối:
  ```python
  browser = pw.chromium.connect_over_cdp(f"http://{addr}")
  context = browser.contexts[0]
  page = context.new_page()
  ```

### B. Bẫy Button Locator & Giải pháp `press("Enter")`
- Trên trang `https://login.live.com`, Microsoft thường xuyên A/B test hoặc thay đổi ID nút submit (`#idSIButton9`, `#idSubmit_SAV_btnSubmit`, button localized "Tiếp theo", "Next").
- **Kỷ luật chuẩn**: Điền text vào input xong gọi thẳng `input.press("Enter")`. Thao tác Enter submit form ngay lập tức mà không phụ thuộc vào selector của nút.

### C. Bẫy Màn hình Gợi ý Gửi Mã ("Xác minh email của bạn")
- Khi đăng nhập bằng tài khoản mua, Microsoft có thể hiển thị màn hình hỏi: *"Xác minh email của bạn - Chúng tôi sẽ gửi mã đến..."*.
- **Cách xử lý**: Bấm vào liên kết chân trang **"Sử dụng mật khẩu của bạn"** (`#idA_PWD_SwitchToPassword`, `text="Sử dụng mật khẩu của bạn"`) để chuyển sang form nhập mật khẩu tĩnh.

### D. Luồng Đổi Mật Khẩu
1. Điều hướng tới `https://account.live.com/password/change`.
2. Điền mật khẩu hiện tại (`#currentPassword`).
3. Sinh mật khẩu ngẫu nhiên mạnh 14 ký tự (`gen_strong_password()` gồm chữ hoa, chữ thường, số, ký tự đặc biệt).
4. Điền mật khẩu mới (`#newPassword`) và xác nhận (`#confirmPassword`).
5. Bấm submit (`#save` / `input[type="submit"]`).

### E. Gỡ Mail Khôi Phục Bên Bán & "Sign Out Everywhere"
1. Điều hướng tới `https://account.live.com/proofs/manage/additional`.
2. Kiểm tra danh sách phương thức xác minh: nếu thấy email khôi phục lạ của bên bán (getnada.com, fviainboxes.com, mail.tm...), thực hiện gỡ bỏ.
3. Tìm và bấm nút **"Sign out of everywhere"** ("Đăng xuất khỏi mọi nơi") ➔ Bấm xác nhận để hủy toàn bộ session và token cũ của bên bán.

### F. Đồng Bộ Dữ Liệu & Audit State
- Cập nhật mật khẩu mới vào **Cột G (PASS MAIL)** trong file Excel master `taikhoan_dat_v2_updated .xlsx`.
- Ghi nhận email đã đổi vào `D:\Taadaa\runtime\kibe\cron-state\hotmail_changed_tracker.json`.
- Chụp ảnh màn hình ở từng Checkpoint (Pre-submit & Post-submit) và in `MEDIA:<path>` theo đúng tiêu chuẩn GATE 6.
- Đóng profile qua API `GPMClient.stop_profile(profile_id)` kết hợp process cleanup.
