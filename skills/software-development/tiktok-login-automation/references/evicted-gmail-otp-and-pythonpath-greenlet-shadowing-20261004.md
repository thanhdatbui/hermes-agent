# Evicted Gmail OTP Failure & Subprocess PYTHONPATH Shadowing Pitfalls (2026-10-04)

## 1. Hiện tượng & Bối cảnh
- **Máy M3 (Galaxy S7 - `9885e6344655484754`)**: Bị cảnh báo P0 văng tài khoản Row 8 `@annhubvqttr` (`ACCOUNT_SWITCHER_FAILED: ACCOUNT_MISSING`).
- Khi chạy công cụ khôi phục `recover_missing_tiktok_login.py --machine 3 --account annhubvqttr`:
  1. Ban đầu script văng lỗi `exit=2` ngay tại bước `_gmail_live_gate`: `[gmail-live] checker returned DIE for an.nhuan.work64541@gmail.com -> BLOCK`.
  2. Sau khi vượt qua gate kiểm tra live, script điều hướng TikTok đến bước điền email và chờ OTP, nhưng app Gmail trên máy M3 không hề có thư OTP về, báo timeout sau 150s: `[otp-gmail] an.nhuan.work64541@gmail.com khong co trong Gmail account list sau retry`.

---

## 2. Nguyên nhân cốt lõi (Root Causes)

### A. Bẫy Thừa kế PYTHONPATH Gây Shadowing Package (Lỗi C-Extension Greenlet)
- Khi script chạy dưới dạng subprocess từ harness agent (Hermes venv) gọi Python của môi trường farm (`D:\Taadaa\python-envs\automation`), biến môi trường `PYTHONPATH` của Hermes vô tình bị truyền xuống subprocess.
- Hậu quả: `check_gmail_live_fast.py` (chạy Playwright) import nhầm module `greenlet` từ Hermes venv (Python 3.11 build khác) thay vì venv của farm, dẫn đến ngoại lệ `ModuleNotFoundError: No module named 'greenlet._greenlet'`.
- Khối `except` trong `_gmail_live_gate` bắt ngoại lệ và fail-closed giả định email bị `DIE`, chặn đứng quy trình login hợp lệ.
- **Quy chuẩn khắc phục:** Mọi script launcher hoặc wrapper khi gọi subprocess bằng venv riêng BẮT BUỘC phải tẩy sạch `PYTHONPATH`:
  ```python
  env = os.environ.copy()
  env.pop("PYTHONPATH", None)
  ```

### B. Bẫy Tài khoản Passwordless Bị Gỡ Khỏi Thiết Bị (Evicted Gmail Trap)
- Tài khoản TikTok `@annhubvqttr` được tạo ngày `2026-09-08` nhưng cột `tiktok_pass` trong Excel bị để trống (đăng ký qua Google SSO / Email không set mật khẩu TikTok).
- Khi không có mật khẩu TikTok, luồng đăng nhập bắt buộc phải gửi mã OTP 6 số về Gmail.
- Tuy nhiên, trong `dumpsys account` của máy S7:
  - Tài khoản Gmail `an.nhuan.work64541@gmail.com` đã bị hệ thống gỡ bỏ (`action_account_remove`) vào ngày `2026-09-28` để nhường slot cho tài khoản khác (`chi.tieu.eyww770@gmail.com`).
  - Hàm `_try_get_otp_gmail_app` trong `social_reg_v1.py` chỉ tìm kiếm hòm thư trong danh sách Account Switcher nội bộ của app Gmail trên máy thật. Khi tài khoản đã bị evict, hàm trả về `None` và kết luận không lấy được OTP.
- **Kỷ luật vận hành:**
  1. Tài khoản không có `tiktok_pass` KHÔNG THỂ tự động khôi phục nếu hòm thư Gmail đã bị gỡ khỏi thiết bị Android.
  2. Đối với các tài khoản này: Bắt buộc phải (a) nạp lại Google Account vào Android Settings hoặc (b) dùng tool chuẩn `ensure_row_accounts.py` để provision lại tài khoản Hotmail/Outlook sạch thay thế.

---

## 3. Bài học Sửa Farm Coordinator Guard
- Regex allowlist terminal cần hỗ trợ đường dẫn Windows có ổ đĩa (`D:/...`): dùng `[-a-zA-Z0-9_/:\\\.]+\.py` (ký tự `-` đặt ở đầu class để tránh lỗi `bad character range`).
- Lệnh cấm can thiệp ADB `input` chỉ nên chặn `input tap` và `input swipe` (chống bấm tay qua lỗi), tuyệt đối không cấm `keyevent` để cho phép các lệnh an toàn như đánh thức màn hình (`224`) và mở khóa (`82`).
