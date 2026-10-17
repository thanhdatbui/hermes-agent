# Auto-Login Missing Account & ADB Bridge Reset (Incident 2026-10-17)

## 1. Hiện Tượng & User Correction
- **Bối cảnh**: Khi chạy quy trình upload video (hoặc ca nuôi feed) trên các thiết bị Farm (ví dụ M79), script dừng lại ở bước `ACCOUNT_READY` với lỗi `ACCOUNT_VERIFY_MISMATCH` do tài khoản hiển thị trên Profile/Switcher là `@thanhtam5077` (của Tik 7) trong khi ca upload Tik 4 cần nick `@hoangtuannam2602`.
- **Phản ứng sai của Agent**: Coordinator dừng phiên, phân tích switcher thiếu nick rồi báo cáo cho User hỏi "Cần đăng nhập lại nick `@hoangtuannam2602` không?" hoặc coi đó là blocker thủ công.
- **User chấn chỉnh gay gắt**:
  > "Còn máy bị lệch account là sao có sẵn hàm account switcher r mà khóc cái l gì thế"
  > "Bị thiếu sao k tự động gọi tiktok login log in tài khoản thiếu vào?"
- **Kỷ luật cốt lõi**:
  - Không được báo cáo dừng việc khi hệ thống đã có sẵn automation phục hồi.
  - Khi phát hiện nick mục tiêu thiếu trong Switcher, BẮT BUỘC chủ động gọi bộ công cụ nạp bù tài khoản (`tiktok_login_v1.py` hoặc `reconcile_tiktok_accounts.py`), sau đó tiếp tục thực thi task chính.

---

## 2. Quy Trình Nạp Bù Tài Khoản Mục Tiêu (Targeted Login Recovery)

### A. Kiểm tra nhanh cấu hình tài khoản trong tracking
File nguồn chuẩn: `D:/OneDrive/TaadaaData/kibe/taikhoan_dat_v2_updated .xlsx` hoặc `D:/OneDrive/TaadaaData/kibe/Tik<N>.xlsx`.
Lấy thông tin:
- ID TikTok (Cột C)
- Mật khẩu TikTok (Cột D)
- Secret 2FA Authenticator (Cột E)
- Email / Hotmail (Cột F)

### B. Lệnh thực thi nạp bù bằng `tiktok_login_v1.py`
Ưu tiên số 1 khi nạp bù đúng 1 nick cụ thể:
```bash
python D:/Taadaa/Tiktok_Reg/tiktok_login_v1.py <STT> --email <TARGET_ID> --ss
```
- Nếu gọi từ tiến trình cha đang giữ device lock, thêm `--allow-parent-lock`.
- Script tự động:
  1. Kiểm tra tài khoản trong tracking.
  2. Bỏ qua OTP mail nếu có đủ ID + Pass + 2FA TOTP (bypass reCAPTCHA/mail OTP).
  3. Mở app TikTok, vào Profile -> Switcher -> "Thêm tài khoản".
  4. Điền email/ID + mật khẩu + sinh mã TOTP tự động bằng `pyotp`.
  5. Chụp ảnh xác nhận kết quả (`--ss`) vào thư mục artifacts.

### C. Lệnh thay thế qua `reconcile_tiktok_accounts.py`
Nếu cần đối soát toàn diện máy và nạp bù nick theo workbook ca chạy:
```bash
python D:/Taadaa/tiktok-log-in/scripts/reconcile_tiktok_accounts.py \
  --workbook "D:/OneDrive/TaadaaData/kibe/Tik<N>.xlsx" \
  --machines <STT> \
  --expected-username <TARGET_ID> \
  --adb-path "C:/Program Files (x86)/xiaowei/tools/adb.exe" \
  --login-project "D:/Taadaa/Tiktok_Reg" \
  --allow-live-reconcile \
  --full-scope-takeover
```

---

## 3. Bẫy ADB Socket Stale & Quy Trình Reset ADB Bridge Khi Timeout

### A. Triệu chứng
Khi gọi lệnh login/reconcile:
```
[10:39:33]    → tap profile tab node (972, 1857) text='' desc='Hồ sơ' rid='com.ss.android.ugc.trill:id/oms'
Reconnecting remote ADB host localhost:5037 for serial=ce0516059d279f3e03
STOPPED: [adb-timeout] device=ce0516059d279f3e03 timeout=20s command=shell settings put system accelerometer_rotation 0
```
- Sau đó chạy bất kỳ lệnh `adb -s <serial> shell ...` nào cũng bị treo cứng quá 10s (`subprocess.TimeoutExpired`).
- Kết nối `atx-agent` cổng 7912 báo `Connection refused` hoặc không phản hồi.

### B. Nguyên nhân gốc rễ
- Host Windows ADB server (`adb.exe` port 5037) duy trì persistent socket pool tới 80 máy qua các hub USB.
- Khi một máy Samsung S7 thực hiện nhiều thao tác nặng (đổi app, render, dump XML), daemon `adbd` trên điện thoại hoặc worker thread trên host Windows bị rơi vào trạng thái wedged / dead socket.
- Thiết bị vẫn hiện trong `adb devices` nhưng mọi lệnh shell gửi qua socket cũ đều bị block vô hạn.

### C. Khắc phục dứt điểm trong O(1)
KHÔNG khởi động lại điện thoại hay rút cáp USB. Chạy ngay:
```bash
adb kill-server && adb start-server
```
Sau đó kiểm tra lại:
```python
# Verify thiết bị online và nhận lệnh shell
res = subprocess.run([adb, "-s", serial, "shell", "getprop", "sys.boot_completed"], capture_output=True, text=True, timeout=10)
assert res.stdout.strip() == "1"
```
Khi socket được reset sạch sẽ, khởi chạy lại tiến trình nạp bù nick.
