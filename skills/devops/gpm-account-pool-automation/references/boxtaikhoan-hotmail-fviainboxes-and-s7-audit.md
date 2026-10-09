# BoxTaiKhoan Hotmail, Fviainboxes Recovery & S7 Phone Audit Workflow

## 1. Bản chất nguồn hàng Hotmail BoxTaiKhoan & Mail khôi phục `@fviainboxes.com`

- **Nguồn gốc phôi mua (`boxtaikhoan.com`)**:
  - Gói ID 129: *Tài Khoản Hotmail TRUSTED GraphAPI - Live Vĩnh Viễn, Mail Khôi Phục Fviainboxes - Chưa Qua Dịch Vụ* (giá ~166đ/mail).
  - API endpoint: `https://boxtaikhoan.com/api/profile.php?api_key={api_key}` (User: `thanhdatbui1995`).
  - Phôi mua về bao gồm: `email | pass_mail | mail_khoi_phuc | refresh_token | client_id`.
  - Toàn bộ được nạp vào kho authoritative: `D:\OneDrive\TaadaaData\kibe\gmail_clean_v2.xlsx` (Cột 5: `mail khôi phục`, Cột 9: `token`, Cột 10: `client_id`).

- **Đặc điểm định danh Mail Khôi Phục Fviainboxes**:
  - Cấu trúc: `<username><random_suffix>@fviainboxes.com` (ví dụ: `murtaghshandy156` $\rightarrow$ `murtaghshandy1563pf@fviainboxes.com`).
  - **Bản chất kỹ thuật (Phát hiện thực tế)**: `@fviainboxes.com` là một dịch vụ Temp-Mail công khai trực tiếp trên web (`https://fviainboxes.com/`), tương thích họ `generator.email`.
  - Hộp thư này **hoàn toàn có thể truy cập công khai**: chỉ cần vào web `https://fviainboxes.com/`, nhập prefix (ví dụ `murtaghshandy1563pf`), bấm `Get Email` là hòm thư tự động hiển thị nhận thư mới từ Microsoft.

---

## 2. Quy tắc Bất Biến Xử Lý Mail Khôi Phục (Recovery Verification Rules)

Khi đăng nhập Hotmail trên GPM hoặc Web, nếu Microsoft chặn ở màn hình:
> *"We'll send a code to [hidden_email]. To verify this is your email, enter it here."*

1. **Quy tắc Khoa Lê (`khoa...` / `khoale...` / `khoalee...`) (User Hard Invariant)**:
   - Nếu mail khôi phục hiển thị là `khoa...` (ví dụ `khoalemagic@gmail.com`, `khoaleemagic@gmail.com`):
   - **BẮT BUỘC BÁO LẠI VÀ BỎ QUA (SKIP)**:
     - Gán ngay `status: "BLOCKED"`.
     - Báo cáo rõ danh sách nick dính `khoa...` cho User.
     - CẤM tự ý thử xác minh, CẤM gõ mật khẩu lại, CẤM thử OTP.
   - *Lý do*: Đây là dàn nick cổ (>6 tháng) dính mail khôi phục của đối tác Khoa Lê, chỉ xử lý thủ công khi có OTP trực tiếp từ Khoa.

2. **Quy tắc Vượt Checkpoint Temp-Mail Fviainboxes (`@fviainboxes.com`)**:
   - Dùng WinRT OCR (`windows-native-ocr`) soi chuỗi gợi ý: `We'll send a code to mu*****@fviainboxes.com`.
   - Tra cứu địa chỉ đầy đủ từ Cột 5 `gmail_clean_v2.xlsx` (ví dụ `murtaghshandy1563pf@fviainboxes.com`).
   - **Quy trình lấy OTP khôi phục tự động / bán tự động**:
     1. Nhập địa chỉ đầy đủ vào form Microsoft để yêu cầu gửi mã xác nhận.
     2. Mở trình duyệt truy cập `https://fviainboxes.com/` (hoặc cào DOM / gọi GET request).
     3. Nhập prefix hòm thư (`murtaghshandy1563pf`) $\rightarrow$ Click `Get Email`.
     4. Đọc mã xác nhận 7 số của Microsoft trong hòm thư hiển thị trên web.
     5. Điền mã vào form Microsoft để giải phóng tài khoản, đưa về trạng thái Live.

---

## 3. Quy trình Audit Hiện trường Máy S7 (Kiểm tra Hotmail đã log vào máy chưa)

Khi cần xác minh một tài khoản Hotmail đã từng được đăng nhập hoặc lưu session trên máy S7 thật hay chưa:

### Bước 1: Kiểm tra Android Account Manager (Tầng Hệ Thống)
```bash
"/c/Program Files (x86)/xiaowei/tools/adb.exe" -s <serial> shell dumpsys account | grep -E "Account \{name="
```
- Hotmail trên Android S7 thường được thêm qua Gmail IMAP (type: `com.google.android.gm.legacyimap`).
- Nếu không thấy email trong danh sách này $\rightarrow$ Hệ thống Android chưa từng lưu credential.

### Bước 2: Kiểm tra Ứng dụng Outlook App (Tầng Ứng Dụng)
1. Mở app Outlook:
   ```bash
   "/c/Program Files (x86)/xiaowei/tools/adb.exe" -s <serial> shell monkey -p com.microsoft.office.outlook -c android.intent.category.LAUNCHER 1
   ```
2. Vào màn hình Settings để xem danh sách toàn bộ tài khoản:
   - Trên giao diện tablet/landscape (1920x1080): Tap icon bánh răng Settings tại `(70, 1020)` hoặc tap hamburger menu tại `(70, 150)`.
   - Vuốt nhẹ danh sách: `adb -s <serial> shell input swipe 500 800 500 300`.
3. Chụp màn hình và chạy WinRT OCR:
   ```bash
   adb -s <serial> exec-out screencap -p > D:/Taadaa/mXX_outlook_settings.png
   python "C:/Users/Kibe/AppData/Local/hermes/skills/productivity/windows-native-ocr/scripts/winrt_ocr.py" D:/Taadaa/mXX_outlook_settings.png
   ```
4. Đọc mục *Tài khoản thư*: Nếu không có email mục tiêu $\rightarrow$ Xác nhận 100% chưa đăng nhập Outlook.
5. Thoát về Home ngay sau khi kiểm tra: `adb -s <serial> shell input keyevent KEYCODE_HOME`.

### Bước 3: Đối soát Lịch sử Reg TikTok & Graph API Token
- Tra cứu email trong `D:\Taadaa\Tiktok_Reg\social_reg_log.txt`:
  - Nếu thấy dòng: `[otp-graph] Mailbox có token Graph API -> Đọc OTP trực tiếp qua PC (CẤM mở Outlook app)`.
  - Điều này xác nhận: Tài khoản đã reg TikTok tự động từ xa bằng cách gọi Microsoft Graph API trên PC để lấy OTP 6 số, **hoàn toàn không cần và chưa từng mở app Outlook trên máy S7**.
  - Kiểm tra file tracking: `D:\Taadaa\runtime\kibe\artifacts\runs\social-batch-all\...\tracking_result_*.json` để đối chiếu `tiktok_id`, mật khẩu TikTok và trạng thái gán máy.

---

## 4. Bẫy Chrome Profile khi truy cập BoxTaiKhoan / Sàn MMO qua CDP

- **Bẫy User Main Profile vs Hermes Isolated Profile**:
  - User lưu session đăng nhập thực tế của BoxTaiKhoan, Shopee, sàn MMO tại:
    `C:\Users\Kibe\AppData\Local\Google\Chrome\User Data` (Profile: `Profile 4` - `jinrakal@gmail.com`).
  - Phiên Hermes Chrome CDP mặc định chạy độc lập tại:
    `C:\Users\Kibe\AppData\Local\hermes\browser_profile` (Profile: `Default`).
  - Khi dùng CDP cổng 9222 trên Hermes profile điều hướng sang `boxtaikhoan.com/product-orders`, web sẽ tự động redirect về `boxtaikhoan.com/client/login` do thiếu cookie phiên `user_login`.
  - **Khắc phục**: Khi User yêu cầu kiểm tra đơn hàng trực tiếp trên trình duyệt, tuân thủ skill `logged-in-chrome-cdp-marketplace`: kết nối vào đúng profile cá nhân của user (`Profile 4`) hoặc dùng API trực tiếp qua `api_key`.
