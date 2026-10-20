# GPM Hotmail Login: Interstitials, Terms Update & Passkey Bypass (2026-10-20)

## 1. Bối cảnh & Hiện tượng lỗi (Root Causes)
Khi tự động hóa đăng nhập Hotmail trên cụm GPMLogin qua Playwright/CDP (`batch_gpm_hotmail_password_login.py`), có 3 điểm nghẽn giao diện mới của Microsoft khiến tài khoản bị kẹt và văng vào trạng thái `BLOCKED` / `QUARANTINE`:

1. **Rút gọn liên kết "Use your password"**:
   - Giao diện cũ: `Use your password instead`.
   - Giao diện mới (2026): Microsoft đổi text thành `Use your password`.
   - *Hậu quả:* Code dùng selector cứng `a:has-text('Use your password instead')` bị trượt, kẹt lại ở màn hình gửi mã OTP về email khôi phục và không chuyển sang ô nhập mật khẩu.
   - *Khắc phục:* Bao quát selector: `a:has-text('Use your password')`, `button:has-text('Use your password')`, `text='Use your password'`.

2. **Bẫy ngộ nhận Đăng nhập thành công sớm (False Done URL) tại màn hình Terms ("We're updating our terms")**:
   - URL: `https://account.live.com/tou/accrue?mkt=EN-US...`
   - *Bẫy logic:* Code kiểm tra `if netloc == "account.live.com" and path not in ["/", "/login.srf"]: logged_in = True`. Vì domain là `account.live.com`, script ngộ nhận đã đăng nhập thành công vào trang quản lý tài khoản, lập tức chụp ảnh màn hình nghiệm thu rồi đóng trình duyệt!
   - *Bẫy ngôn ngữ:* Trên profile có ngôn ngữ tiếng Anh (`mkt=EN-US`), nút bấm mang text `Next`. Danh sách selector cũ chỉ có tiếng Việt (`Tiếp`, `input[value*='Tiếp']`), khiến bot không bấm được nút `Next`.
   - *Khắc phục:*
     * URL chứa `/tou` hoặc `/tou/accrue` BẮT BUỘC coi là màn hình trung gian (interstitial), KHÔNG được tính là `logged_in`.
     * Bổ sung selector Next tiếng Anh: `#iNext`, `input[value*='Next']`, `button:has-text('Next')`, `a:has-text('Next')`.
     * Sau khi click, bắt buộc chờ điều hướng (`page.wait_for_load_state("networkidle")`).

3. **Popup ép tạo Passkey FIDO (`/consumers/fido/create`)**:
   - Ngay sau khi bấm `Next` qua khỏi Terms, Microsoft tự động hiển thị màn hình tạo passkey FIDO tại `https://account.live.com/consumers/fido/create` ("Setting up your passkey...").
   - *Khắc phục:* Bắt URL chứa `/consumers/fido` hoặc text chứa `passkey` / `Passkey`, tự động tìm và click nút `Cancel` / `Hủy` / `Skip for now` / `Bỏ qua` / `Không, cảm ơn`.

4. **Màn hình Duy trì đăng nhập (KMSI - "Stay signed in?")**:
   - Bấm `#iAccept`, `input[value*='Yes']`, `button:has-text('Yes')`, `input[value*='Có']`, `button:has-text('Có')` để lưu phiên đăng nhập và cookie sống lâu dài trên profile GPM.

---

## 2. Tiêu chuẩn nghiệm thu bằng chứng (Canary Evidence Standard)
- **CẤM nghiệm thu chỉ bằng URL domain**: Domain `account.live.com` xuất hiện ở cả màn hình Terms (`/tou`) và màn hình Passkey (`/consumers/fido`).
- **Nghiệm thu chuẩn qua WinRT OCR / Vision**: Chỉ kết luận `logged_in = True` khi OCR màn hình ghi nhận các marker cốt lõi của trang quản lý tài khoản:
  * `Microsoft account`
  * `Account`
  * `Change password`
  * `Security`
  * `Subscriptions` / `Products and subscriptions`
  và không còn bất kỳ modal/dialog hay thanh tiến trình nào che khuất.

---

## 3. Quy tắc cập nhật & khử cảnh báo ảo trên Cron 6H (`cron_hotmail_gpm_lifecycle_6h_report.py`)
- **Triệt tiêu `DONE_WITHOUT_CHATGPT_REG` ảo**: Nếu tài khoản đã mang cờ `has_chatgpt: True`, không cảnh báo lỗi thiếu timestamp ISO `chatgpt_registered_at`.
- **Phân tách `QUARANTINE`**: Tài khoản có `login_retry_count >= 3` được gom vào nhóm `QUARANTINE` để cách ly và xử lý riêng, không để lẫn với hàng đợi `PENDING` thông thường.
- **Bóc tách `WAIT_7D`**: Hiển thị rõ số lượng nick đã đủ $\ge 7$ ngày (`matured_7d`) và số lượng nick còn thiếu thông tin TikTok (`missing_tiktok`).
