# TikTok Suspended Account Detection & Full Device/Workbook Cleanup (2026-08-28)

## 1. Triệu chứng & Nhận diện lỗi tài khoản bị khóa (Suspended / Banned)
Khi thực hiện đăng nhập lại (Login / Reconcile) tài khoản cũ bằng Email/OTP hoặc Mật khẩu:
- Sau khi nhập OTP hoặc Mật khẩu, TikTok hiển thị thông báo lỗi:
  `Tài khoản của bạn đã bị đình chỉ.` / `Your account has been suspended.`
- UI Hierarchy: `text="Tài khoản của bạn đã bị đình chỉ."` / `text="Lỗi mã xác minh email"`.
- Classifier: Gắn nhãn `account_banned` / `ACCOUNT_SUSPENDED`, chụp ảnh màn hình bằng chứng (`screencap -p`).

## 2. Quy tắc trả lời về vị trí dòng (Excel Row vs Machine Row/Slot)
- Khi user hỏi *"thuộc row số mấy của máy đó"*:
  - Cần trả lời **Machine Slot / Row thứ N của Máy X** (ví dụ: Slot 2 / Row 2 của Máy 71).
  - Đi kèm thông tin phụ trợ: Excel Row (ví dụ 563), Tik Folder (562), ID, Gmail.

## 3. Quy trình dọn dẹp trọn gói tài khoản bị ban / rác (Workbook + Device)

### Bước 1: Backup Workbooks an toàn
Trước khi sửa bất kỳ file Excel nào, tạo backup có timestamp vào `D:\Taadaa\BACKUP_ALL\`:
- `taikhoan_dat_v2_updated .xlsx`
- `taikhoan_run_safe.xlsx`
- `Tik1.xlsx`, `Tik2.xlsx`, `Tik3.xlsx`
- `gmail_clean_v2.xlsx`

### Bước 2: Xóa thông tin khỏi các bảng Workbook
1. **`taikhoan_dat_v2_updated .xlsx` (Sheet `Tài Khoản`):**
   - Đặt `ID = None`, `PASS = None`, `2FA = None`, `GMAIL = None`, `PASS MAIL = None`, `DOB = None`, `NGÀY TẠO = None`.
   - Giữ nguyên số Máy, Tik folder và Device ID để giữ chỗ slot.
2. **`taikhoan_run_safe.xlsx` (Sheet `Accounts`):**
   - Đặt `ID = None`, `Count = 0` tại slot của máy tương ứng.
3. **`Tik1.xlsx` / `Tik2.xlsx` / `Tik3.xlsx`:**
   - Xóa ID khỏi sheet ca tương ứng nếu có.
4. **`gmail_clean_v2.xlsx`:**
   - Xóa row Gmail bị chết nếu còn nằm trong danh sách.

### Bước 3: Xóa tài khoản Google khỏi thiết bị Android
Tài khoản bị ban cần được gỡ khỏi Android Account Manager để tránh vướng sync hoặc nhận OTP rác:
1. Mở Cài đặt tài khoản: `adb shell am start -a android.settings.SYNC_SETTINGS`.
2. Tap vào tài khoản Google cần xóa (theo text email hiển thị).
3. Tap **"XÓA TÀI KHOẢN"** (`bounds` góc dưới phải).
4. Tap xác nhận **"XÓA TÀI KHOẢN"** trên popup cảnh báo.
5. Kiểm tra lại bằng `adb shell dumpsys account` đảm bảo danh sách chỉ còn các tài khoản hợp lệ.

### Bước 4: Dọn dẹp thiết bị & Giải phóng Lock
- Đưa máy về màn hình Home: `adb shell input keyevent 3`.
- Đảm bảo giải phóng sạch lock trong `C:\Users\Kibe\.codex\device-locks\`.
