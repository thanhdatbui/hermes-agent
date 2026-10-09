# Device Lock Hard Enforcement, Reaper Safety & Anti-Parasite Protocol (23/09/2026)

## 1. Bài học xương máu: Coordinator can thiệp phá hoại tiến trình đang chạy

### Hiện tượng sai phạm
Trong ca add 2FA (`run_batch_live_2fa.py`) hoặc ca nuôi acc (`run_tiktok.py`), Coordinator thấy máy đang ở màn hình 2FA Authenticator hoặc dropdown Switcher, vội vã kết luận là "kẹt màn hình", tự ý chạy `adb shell am force-stop` và `input keyevent 3` đưa về HOME, thậm chí cố tình xóa / bẻ reservation lock.
Hậu quả: Làm đứt ngang phiên 2FA hoặc phiên nuôi nick đang chạy hợp lệ của farm.

### Bản chất lỗ hổng kiến trúc
1. **Lỗ hổng Bypass Lock trong script**: Hàm `_acquire_social_device_lock_or_skip` trong `social_reg_v1.py` dùng cờ opt-in `DEVICE_LOCK_ENABLED` (mặc định rỗng/False khi chạy CLI tay), dẫn đến việc script không hề tạo file lock chuẩn `machine_<N>.lock.json` trong `~/.codex/device-locks/`.
2. **Coordinator gọi ADB thô**: Không kiểm tra file lock `machine_<N>.lock.json` và liveness của PID sở hữu trước khi can thiệp thiết bị.

### Thiết kế chuẩn hóa: 3 Nguyên tắc Bất biến
1. **Force-stop khi test đồ**: VẪN ĐƯỢC PHÉP, nhưng **CHỈ TIẾN TRÌNH SỞ HỮU LOCK** mới có quyền gọi `am force-stop` trên máy đó để reset app về clean state. Tuyệt đối cấm tiến trình ngoài lề hoặc Coordinator nhảy vào force-stop máy của PID khác.
2. **Cơ chế Reaper 1h tự động**: File `D:/Taadaa/tiktok-luot nuoi acc/scripts/reap-dead-owner-locks.py` đã có sẵn cơ chế: quét `~/.codex/device-locks/`, nếu lock > 3600s (1 giờ) hoặc PID đã chết (`owner_process_alive() == False`) thì tự động cách ly file lock và gọi `am force-stop` + `input keyevent 3` về HOME. Coordinator **CẤM** tự ý làm thay chức năng của reaper.
3. **Hard Lock Enforcement**: Mọi script can thiệp máy bắt buộc phải gọi `acquire_device_lock(..., user_authorized=True)` ngay tại entrypoint (`register()`). Nếu conflict lock (`dev_lease is None`) -> **SAFE ABORT NGAY LẬP TỨC**, cấm thao tác ADB.

---

## 2. Quy tắc chống tạo "Nick Ký Sinh" (Anti-Parasite Account Invariant)

### Hiện tượng sai phạm
Coordinator được giao test một email Hotmail mới mua (`odessostuffen14@hotmail.com`). Thay vì kiểm tra Source of Truth xem email này đã được Farm xử lý chưa, Coordinator giả định là chưa chạy, đem cắm vào Máy 201 (dàn Admin) để test.
Khi TikTok báo *"Bạn đã đăng ký"*, Coordinator tiếp tục nhập OTP để login, vô tình đăng nhập tài khoản `@lethanhlan14` lên Máy 201 trong khi nick này **đã được Máy 22 (dàn Kibe) reg thành công từ trưa cùng ngày**!
Hậu quả: Biến `@lethanhlan14` thành nick ký sinh trên Máy 201, 1 nick online song song trên 2 thiết bị vật lý / 2 IP khác nhau, gây rủi ro quét khóa tài khoản.

### Quy trình bắt buộc trước khi test/reg/login:
1. **TRA CỨU TRẠNG THÁI HIỆN TẠI (STATE LOOKUP FIRST)**:
   - Tra cứu trong `taikhoan_dat_v2_updated .xlsx` (hoặc `tiktok_tracker.db` / `social_reg_log.txt`) xem email/username đã được gán máy nào chưa.
   - Nếu máy ghi nhận `cooldown_until` hoặc email đã có `tiktok_id` -> **DỪNG LẠI NGAY**, báo cáo đã hoàn thành, tuyệt đối không test lại.
2. **KHI TIKTOK HIỆN "BẠN ĐÃ ĐĂNG KÝ"**:
   - **DỪNG NGAY LẬP TỨC**: Không được tự ý bấm Tiếp tục và nhập OTP để login sang máy khác nếu chưa xác minh nick đó thuộc về máy nào.
   - Nếu nick thuộc máy khác trên Farm: Hủy bỏ ngay, không để tạo nick ký sinh đa thiết bị.

---

## 3. Đánh giá nguồn Hotmail dongvanfb.net cho Farm Taadaa
- **Loại 1 (ID 5 - 350đ, Hotmail TRUSTED [GRAPH API])**: **LỎ, CẤM DÙNG**. Token cấp thiếu scope `Mail.Read`, gọi Microsoft Graph API đọc OTP bị lỗi `Graph token invalid`.
- **Loại 3 (ID 57 - 350đ, HOTMAIL TRUSTED THÊM KHÔI PHỤC FVIAINBOXES.COM)**: **CHUẨN 100%**. Token full scope (`User.Read`, `Mail.Read`, `Mail.ReadWrite`, `IMAP`, `POP`, `SMTP`). Đọc OTP qua Graph API mượt mà từ PC. Phù hợp tuyệt đối flow ngâm 7 ngày đổi password, tick đá thiết bị cũ và xóa mail khôi phục.
- Sàn **không có nhãn "Chưa qua TikTok"** (chỉ bán mail via FB), nên khi mua về nạp vào farm, script tự động kiểm tra Zin khi submit form reg.
