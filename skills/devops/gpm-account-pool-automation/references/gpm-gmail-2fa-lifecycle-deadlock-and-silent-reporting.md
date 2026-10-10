# GPM Gmail 2FA Lifecycle Deadlock & Silent Reporting Triage

## 1. Triệu Chứng & Phản Ứng Của Người Dùng
Khi người dùng bức xúc hỏi: *"Sao cứ báo như v hoài thế"* hoặc *"Tao hỏi này mà ngáo à"* khi reply vào thông báo cronjob:
- Báo cáo định kỳ (ví dụ mỗi 6 tiếng) gửi nguyên văn bảng thống kê giống hệt nhau:
  `• Đã bật 2FA thành công: 82/83 (98.8%) | Đang ngâm: 1 | Tiến độ trong 6h qua: 0 sự kiện`.
- Số liệu hoàn toàn đứng im qua nhiều ngày nhưng tin nhắn vẫn bắn đều đặn về Telegram.

---

## 2. Hai Nguyên Nhân Cốt Lõi

### 2.1 Vi Phạm Nguyên Tắc Silent Watchdog (`no_agent: true`)
- Trong Hermes, khi job được khai báo `no_agent: true`:
  - **Stdout không rỗng**: Tự động gửi nguyên văn nội dung làm tin nhắn Telegram.
  - **Stdout rỗng**: Hệ thống hiểu là **SILENT** (không có gì mới / không lỗi), không gửi tin nhắn.
- **Lỗi phổ biến**: Script báo cáo (`*_6h_report.py`) luôn `print()` tiêu đề và số liệu tổng quan ngay cả khi `len(recent_events) == 0`.
- **Quy chuẩn sửa**:
  ```python
  # SILENT WATCHDOG: Nếu không có sự kiện mới trong chu kỳ -> Im lặng tuyệt đối (chống spam)
  if not recent_6h_events:
      return 0
  ```
  Đồng bộ bắt buộc sang cả 3 thư mục:
  1. `C:/Users/Kibe/AppData/Local/hermes/scripts/`
  2. `D:/Taadaa/Hermes/deploy/hermes-home/scripts/`
  3. `D:/OneDrive/Taadaa_Sync_Shared/hermes-cron/scripts/`

### 2.2 Tam Giác Kẹt Vòng Lặp (3-Cron Lifecycle Deadlock)
Khi 1 profile trong Group 10 (`Google_Live_Ready`) bị rớt session Google (`NEEDS_LOGIN`):
1. **Cron Nuôi** (`cron_gpm_gmail_nurture`): Bỏ qua profile vì `status == "NEEDS_LOGIN"`.
2. **Cron Bật 2FA** (`post_morning_gmail_2fa`): Bỏ qua vì chốt chặn an toàn (Soaking Gate) yêu cầu phải có phiên nuôi thành công gần nhất.
3. **Cron Đăng Nhập Buổi Tối** (`post_evening_gpm_login`): Chỉ quét các tài khoản chưa có trong Group 10; tài khoản này đã nằm trong Group 10 rồi nên bị bỏ qua.
$\rightarrow$ Tài khoản biến thành "xác sống" kẹt ngâm vĩnh viễn, không script nào nhận xử lý.

---

## 3. Quy Trình Vượt Thử Thách Google Sign-in & Bật 2FA Tự Động

### 3.1 Xử Lý reCAPTCHA Inline Trên Trang Identifier
1. Điền email `#identifierId`, nhấn Enter.
2. Nếu xuất hiện *"Confirm you're not a robot"*: Nhấn nút `Next` / `Tiếp theo` trên trang chính để kích hoạt tải iframe `enterprise/anchor` và `bframe`.
3. Gọi hàm giải âm thanh `solve_recaptcha_audio(page)`.
4. Sau khi checkbox tick xanh, nhấn nút `Next` (`#recaptchaNext`) để chuyển sang màn hình mật khẩu.

### 3.2 Bỏ Qua Màn Hình Gợi Ý Video Selfie
Google có thể yêu cầu: *"Protect your account access with a selfie"*.
- Nhận diện URL `verification/selfie/precollection` hoặc nút `button:has-text("Not now")`.
- Bấm `Not now` để vào thẳng `myaccount.google.com`.

### 3.3 Duyệt Tự Động Google Prompt Trên Galaxy S7 (Máy N)
Khi điều hướng tới `/two-step-verification/authenticator`, Google có thể yêu cầu step-up verification qua Google Prompt:
1. Trích xuất mã PIN hiển thị trên web: Tìm thẻ `strong`, `b` trong `div[role="main"]` hoặc regex `\b(\d{1,2})\b`.
2. Giữ `acquire_device_lock` cho máy S7 tương ứng (`serial`).
3. Port-forward `atx-agent` (port 7912 $\rightarrow$ 17000 + M), bật màn hình (`keyevent 224`), mở khóa (`keyevent 82`).
4. Kéo thanh thông báo (`cmd statusbar expand-notifications`).
5. Tìm và bấm thông báo Google của email đó.
6. Khi dialog xuất hiện: Bấm *"Có" / "Yes"*, sau đó bấm đúng số PIN khớp với trên web.
7. Đợi web chuyển hướng khỏi `challenge/dp`.

### 3.4 Bật 2FA Google Authenticator & Đồng Bộ Master Data
1. Tại trang `/two-step-verification/authenticator`, bấm *"Thiết lập"* / *"Set up"*.
2. Bấm *"Không thể quét mã?"* / *"Can't scan it?"*.
3. Trích xuất Secret Key 32 ký tự Base32 từ dialog.
4. Tính mã TOTP chuẩn True UTC Google: `pyotp.TOTP(secret_key).at(get_google_server_utc_time())`.
5. Điền mã, bấm *"Xác minh"*, bấm *"Xong"*.
6. Lưu ảnh bằng chứng `screenshot`, soi mắt qua `winrt_ocr` / `browser_vision`.
7. Ghi cập nhật Secret Key đồng bộ:
   - `master_gmail_manager.xlsx` (các sheet `Master_All`, `Kibe_Farm_S7`, `Gmail_Dat`).
   - `gmail_clean_v2.xlsx`.
   - `gpm_gmail_nurture_state.json`: cập nhật `status: "success"`, `last_nurtured: time.time()`.
   - `post_morning_gmail_2fa_state.json`: ghi nhận thành công.
