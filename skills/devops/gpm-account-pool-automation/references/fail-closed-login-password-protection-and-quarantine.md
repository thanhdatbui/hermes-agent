# Fail-Closed Password Login & Hard-Lock Quota Protection

## 1. Bối cảnh & Vấn đề Cốt lõi
Khi hệ thống tự động đăng nhập (Hotmail trên GPM, Gmail qua Google SSO, hoặc TikTok trên điện thoại Android):
- **Nguy cơ chí mạng**: Nếu tài khoản bị sai mật khẩu (do workbook lệch pass, pass cũ chưa update) hoặc bị yêu cầu bảo mật đặc biệt, mà script tiếp tục vòng lặp tự động thử lại ở các chu kỳ (ticks) sau, các dịch vụ (Microsoft, Google, TikTok) sẽ lập tức kích hoạt cơ chế chống brute-force:
  - Microsoft: Tạm khóa đăng nhập (`cố gắng đăng nhập quá nhiều lần`, `account has been locked`), bắt xác minh email khôi phục hoặc khóa tài khoản.
  - Google: Tăng độ khó reCAPTCHA, kích hoạt SMS checkpoint cứng, hoặc vô hiệu hóa tài khoản (`account disabled`).
  - TikTok: Khóa thiết bị, rate limit IP/máy (`truy cập dịch vụ quá thường xuyên`).
- **Quy tắc Bất di bất dịch (User Invariant)**: Khi gặp bất kỳ lỗi nào liên quan đến sai pass, rate limit hoặc form error sau khi nhập pass:
  1. **DỪNG NGAY LẬP TỨC** (`FAIL-CLOSED`), chụp màn hình bằng chứng thực tế.
  2. Đánh dấu tài khoản sang trạng thái `BLOCKED` (hoặc cách ly vào Blacklist).
  3. Tuyệt đối **CẤM retry ngầm tự động**. Báo cáo ra giao diện/Telegram để người dùng kiểm tra nguồn mật khẩu.

---

## 2. Tiêu chuẩn Triển khai trên các Nền tảng

### A. Hotmail GPM (`batch_gpm_hotmail_password_login.py` & Supervisor)
1. **Bắt lỗi form ngay sau khi submit password**:
   - Kiểm tra các selector lỗi: `#passwordError`, `#usernameError`, `.alert-error`.
   - Nếu có text lỗi xuất hiện -> Dừng ngay, lưu screenshot, trả về `BLOCKED`.
2. **Bộ từ khóa Chặn Cứng (Hard Block Keywords)** trên body:
   - `"mật khẩu đó không đúng"`, `"mật khẩu không chính xác"`, `"that password is incorrect"`.
   - `"cố gắng đăng nhập quá nhiều lần"`, `"too many attempts"`, `"tài khoản đã bị khóa"`.
   - `"account has been locked"`, `"verify your email"`, `"xác minh email của bạn"`.
3. **Bộ lọc Supervisor (`batch_gpm_5profiles_supervisor.py`)**:
   - Trong `select_candidates()`: CẤM TUYỆT ĐỐI chọn các profile có status thuộc:
     `{"WAITING", "FAILED", "ERROR", "BLOCKED", "QUARANTINE"}`.
   - Khi `execute()` trả về `FAILED` hoặc `ERROR` -> tự động set status thành `BLOCKED`.

### B. Gmail GPM (`run_oauth_s7_pipeline.py` & Watchdog)
1. **Biến cờ `password_submitted`**:
   - Khi đã điền mật khẩu và bấm Tiếp theo/Enter 1 lần:
   - Nếu form nhập password vẫn hiển thị ở lần lặp tiếp theo -> Nhận diện ngay là sai pass hoặc form error -> Dừng ngay (`BLOCKED_WRONG_PASSWORD`), lưu screenshot, thoát luồng.
2. **Kiểm tra thông báo lỗi Google**:
   - `"mật khẩu sai"`, `"sai mật khẩu"`, `"wrong password"`, `"mật khẩu không chính xác"`.
   - `"quá nhiều lần"`, `"too many attempts"`, `"tài khoản của bạn đã bị vô hiệu hóa"`.
3. **Ghi nhận Blacklist tự động**:
   - Ghi tài khoản vào `oauth_pipeline_status.json` trong mục `wrong_password_or_checkpoint` để watchdog `post_evening_gpm_login_watchdog.py` bỏ qua vĩnh viễn trong các ca sau.

### C. TikTok ADB (`tiktok_login_v1.py` & `social_reg_v1.py`)
1. **Phát hiện dấu hiệu sai pass / rate limit từ UI XML**:
   - `"mat khau khong dung"`, `"mat khau khong chinh xac"`, `"sai mat khau"`.
   - `"incorrect password"`, `"wrong password"`, `"thu lai mat khau"`.
   - `"khong dung voi tai khoan"`, `"thu qua so lan"`, `"qua nhieu lan"`.
   - Khi gặp -> Chụp ảnh màn hình `wrong_pass_...`, gán issue `WRONG_TIKTOK_PASSWORD`, thoát khỏi hàm `drive_login_screens()`.
2. **Cờ chống điền lại mật khẩu (`password_submitted`)**:
   - Sau khi đã chạy `fill_password_and_login()` 1 lần:
   - Nếu round sau app vẫn rơi vào `PASSWORD_HINTS` -> CẤM điền lại lần 2, log `[AUTH_BLOCKED]`, chụp ảnh màn hình và thoát ngay.

---

## 3. Checklist Kiểm thử & Nghiệm thu
- [ ] Chạy `--dry-run` supervisor: các acc lỗi/blocked không xuất hiện trong danh sách `CANDIDATES`.
- [ ] Báo cáo định kỳ (6h / watchdog): có phần danh sách đỏ hiển thị cụ thể máy, email và lý do block.
- [ ] Không có tiến trình background nào tiếp tục spam đăng nhập vào tài khoản đang lỗi.
