# Kỷ Luật Giải Phóng Slot Trần 8 Nick & Phục Hồi Nick 2FA TOTP Bỏ Quên (2026-10-10)

## 1. Bối cảnh & Hiện tượng (Incident Máy 20 - @anhdo829)
- **Hiện tượng**: Nick `@anhdo829` (Lan Anh, Máy 20, Slot 1) dừng đăng video từ ngày 09/09/2026. User thắc mắc tại sao bộ lọc cảnh báo nick không đăng video không chạy.
- **Truy vết nguyên nhân**:
  1. Ngày 19/09/2026: Gmail liên kết `dotranganh221220002212@gmail.com` bị Google khóa, hệ thống ghi nhận vào `gmail_die_tong.txt`.
  2. Ở phiên làm việc trước đó, agent vội vàng kết luận "Gmail die = TikTok die", bỏ qua nick cũ và chạy batch reg tài khoản mới `@javialdzxxj` đè vào slot Máy 20.
  3. App TikTok trên Máy 20 chạm trần 8 nick (`MACHINE_FULL_8_ACCOUNTS`), nick cũ bị đẩy khỏi Switcher.
  4. Tool cảnh báo `audit_stale_upload_accounts.py` đã viết từ 06/10 nhưng chưa từng được đăng ký vào cronjob hệ thống.
- **Thực tế tài sản**: Nick `@anhdo829` đăng ký từ 04/03/2026 (7 tháng tuổi), đã có 21 video, 116 followers, 428 likes, và có sẵn **2FA Authenticator TOTP key**. Profile trên TikTok vẫn `LIVE` 100%.

---

## 2. Invariant Cốt Lõi: Độc Lập Giữa Gmail & TikTok 2FA TOTP
- 🚨 **CẤM ĐÁNH ĐỒNG "GMAIL DIE = TIKTOK DIE"**:
  - TikTok cho phép đăng nhập hoàn toàn bằng `Username` + `Password` + `Mã xác thực 2FA (TOTP 6 số)`.
  - Khi có secret key 2FA trong cột `2FA` của Master Excel, script `tiktok_login_v1.py` tự động kích hoạt `telemetry:gmail-live action=bypass_2fa_auth` và KHÔNG BAO GIỜ cần mã OTP gửi về Gmail.
  - Trước khi kết luận một tài khoản bị mất hay die: BẮT BUỘC kiểm tra (1) Cột `2FA` trong Excel có mã TOTP không, (2) Bảng `snapshots` trong `tiktok_tracker.db` xem profile có còn `LIVE` không.
  - Tuyệt đối không được reg tài khoản mới đè lên tài khoản cũ có tuổi đời và tương tác cao khi tài khoản đó có 2FA.

---

## 3. Quy Trình Giải Phóng Slot Trần 8 Nick (Slot Reclamation)

Khi máy đã đủ 8 nick, TikTok ẩn nút `+ Thêm tài khoản` (`Add account`). Để nạp lại tài khoản chính chủ, bắt buộc phải đăng xuất tài khoản mới reg / tài khoản ký sinh theo các bước:

### Bước 1: Xác định vị trí tài khoản cần gỡ (Dual-Surface Audit)
- Kiểm tra tài khoản cần đăng xuất có đang là **Active Profile** (hiển thị trên màn hình Hồ sơ chính) không.
- Nếu KHÔNG phải Active Profile: Bắt buộc mở Switcher bottom-sheet (`bounds=[0,1788][1080,1920]`, `safe_y=1832`), tap switch sang tài khoản đó trước.

### Bước 2: Điều hướng vào Cài đặt để Đăng xuất
1. Vào tab Hồ sơ (`bounds: [864,1794][1080,1920]`).
2. Tap Menu 3 gạch (`Profile menu`) tại góc phải trên: `tap(1005, 150)`.
3. Tap `Cài đặt và quyền riêng tư` (`Settings and privacy`): `tap(621, 1248)` hoặc dùng `find_text_tap`.
4. Cuộn xuống đáy màn hình Cài đặt (vuốt 5 lần `[540, 1500]` $\rightarrow$ `[540, 400]`).
5. Tap nút `Đăng xuất` (`Log out`) ở đáy trang (`bounds` thường khoảng `y=1662` - `y=1673`).

### Bước 3: Xác nhận Dialog Đăng xuất
- Bắt dialog: `Bạn có chắc chắn muốn đăng xuất?` (`Are you sure you want to log out?`).
- Tap nút `Đăng xuất` màu đỏ ở góc dưới của dialog (`bounds` khoảng `y=1662` hoặc resource-id chứa `button1`, `a6d`, `a6e`).
- Chờ 5 giây cho TikTok hoàn tất session teardown.

### Bước 4: Nghiệm thu giải phóng slot (Capture-Before-Cleanup)
- Mở lại app TikTok ➔ vào Hồ sơ ➔ mở Switcher.
- Dùng WinRT OCR kiểm tra:
  * Số lượng tài khoản còn lại đúng **7 nick**.
  * Tài khoản bị gỡ đã biến mất hoàn toàn.
  * Nút `+ Thêm tài khoản` (`Add account`) đã xuất hiện trở lại ở đáy bottom-sheet.
- Chụp ảnh bằng chứng nghiệm thu `m{M}_verified_logout.png` trước khi tiến hành nạp tài khoản mới.

---

## 4. Kỷ Luật Lập Trình & Guard Bulkhead

Khi viết script automation can thiệp thiết bị farm:
1. **Tránh gọi hàm không tồn tại**:
   - `social_reg_v1` KHÔNG có `reg.wake_device()`: Dùng `reg.keyevent(serial, 224, wait=1)` (WAKEUP) và `reg.keyevent(serial, 82, wait=1)` (UNLOCK).
   - `social_reg_v1` KHÔNG expose `_ET`: Bắt buộc khai báo `import xml.etree.ElementTree as ET`.
2. **Tuân thủ Device Lock Bulkhead (`guard_device_bulkhead.py`)**:
   - Mọi script can thiệp ADB phải chạy bọc trong `with operator_device_lock(machine=M, serial=SERIAL, project=...)`.
   - Lệnh terminal gọi script thiết bị phải chạy dạng background (`background=True, notify_on_complete=True, timeout=...`) để không block luồng Coordinator quá 60s.

---

## 5. Khôi Phục Sổ Sách Master & Đồng Bộ Dữ Liệu
Sau khi đăng nhập thành công tài khoản cũ:
1. **Master DAT (`taikhoan_dat_v2_updated .xlsx`)**:
   - Khôi phục thông tin `ID`, `PASS`, `2FA`, `GMAIL`, `NGÀY TẠO` vào đúng hàng của máy (tạo bản backup `.bak` trước khi lưu).
2. **Sheet ca chạy (`Tik1.xlsx` / `Tik2.xlsx`...)**:
   - Khôi phục tên nick và đặt cột `Video Đã Đăng` đúng mốc video tiếp theo (ví dụ đã đăng 21 video thì đặt mốc tiếp tục đăng từ clip `22.mp4`, tuyệt đối không reset về 0).
3. **`taikhoan_run_safe.xlsx`**:
   - Chạy pipeline đồng bộ `sync-safe-workbook.py` để cập nhật dữ liệu runtime.
4. **SQLite `tiktok_tracker.db`**:
   - Cập nhật cả 2 bảng `farm_account_info` và `account_mapping` về ID nick chính chủ.
5. **Watchdog Giám Sát Định Kỳ**:
   - Đảm bảo cronjob `daily-stale-upload-accounts-watchdog` chạy định kỳ mỗi sáng (07:15) để quét toàn bộ fleet, cảnh báo ngay các nick dừng đăng $\ge 3$ ngày hoặc drift giữa Excel và app.
